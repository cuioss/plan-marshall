# SPDX-License-Identifier: FSL-1.1-ALv2
"""
Shared reader of the plugin registry, the executor version and the cache versions.

Three consumers ask the same question — "is the plugin registry pinned at the
version it should be?" — and each used to answer it from its own parser. This
module is the reader they share:

- the harness sync's Claude leg and its repin step (``marketplace/targets/``),
- the pin-trap detector (``pm-plugin-development:plugin-doctor``),
- the orchestrator's restart check (``plan-marshall:plan-orchestrator``).

What it reads
-------------
- **The registry** (``installed_plugins.json``), in the shape the plugin manager
  writes: ``{"plugins": {"{bundle}@{marketplace}": [scope entry, ...]}}``. Every
  scope entry of every key that belongs to this marketplace becomes one row.
- **The executor** (``.plan/execute-script.py``), for the value of its
  ``MARSHALL_VERSION`` assignment.
- **The cache** (one bundle directory holding version directories), for the
  newest version directory and for whether a version directory carries the
  ``.orphaned_at`` marker.

Where the stores live
---------------------
Every read function takes the path it reads, so a caller that already knows a
path passes it. The three ``default_*`` functions state where the stores are on
a machine for a caller that does not: the registry and the cache root under the
user's home directory, the executor under a checkout root.

The authoritative reference version, per caller
-----------------------------------------------
:func:`classify_parity` compares the registry rows against ONE reference version
that the caller supplies. Which store that reference comes from is the caller's
decision, and it is not the same store for every caller:

- **The sync** passes the version it wrote in this invocation. It just produced
  that version directory, so nothing on disk is a better witness.
- **The restart check** passes the executor's ``MARSHALL_VERSION``
  (:func:`read_executor_version`): the question it answers is whether a restarted
  session would load the version the executor was generated at.
- **The cache-root ``dist-manifest.json`` is never a reference.** It describes
  what was built, not what is pinned or what is loaded, and it is not read here.

Constraints on this module
--------------------------
- **Standard library only, and no import of a sibling module.** The module is
  also loaded by FILE LOCATION from ``marketplace/targets/``, where the
  ``script-shared`` directory is not on ``sys.path``; a sibling import would fail
  there.
- **No ``@dataclass``.** A module loaded by file location is not registered in
  ``sys.modules``, and the dataclass machinery looks its defining module up
  there. Rows are plain dicts and read results are plain tuples.
- **It writes nothing.** Every function is a read or a pure computation.
"""

import json
import re
from pathlib import Path

# The marketplace whose registry keys ("{bundle}@plan-marshall") this reader owns.
# Keys of every other marketplace are ignored.
MARKETPLACE_NAME = 'plan-marshall'

# The marker file whose EXISTENCE (never content) flags a version dir orphaned.
ORPHAN_MARKER_NAME = '.orphaned_at'

# ---------------------------------------------------------------------------
# The parity verdict set — closed, and declared ONCE. Every consumer imports
# these names; none restates the strings.
# ---------------------------------------------------------------------------
PARITY_IN_PARITY = 'in_parity'
PARITY_BEHIND = 'behind'
PARITY_AHEAD = 'ahead'
PARITY_UNREADABLE = 'unreadable'
PARITY_VERDICTS = (PARITY_IN_PARITY, PARITY_BEHIND, PARITY_AHEAD, PARITY_UNREADABLE)

# ---------------------------------------------------------------------------
# Registry read states. The non-ok states are kept distinct because they call
# for different operator action: a missing file, a corrupt file, and a file that
# simply holds no entry of this marketplace are three different facts.
# ---------------------------------------------------------------------------
REGISTRY_OK = 'ok'
REGISTRY_ABSENT = 'absent'
REGISTRY_IO_ERROR = 'io_error'
REGISTRY_NOT_JSON = 'not_json'
REGISTRY_NO_PLAN_MARSHALL_ENTRY = 'no_plan_marshall_entry'

# ---------------------------------------------------------------------------
# Executor read states. ``empty`` is the fresh-install sentinel the generator
# writes when no manifest existed yet: the assignment is present and names no
# version, which is neither a found version nor a missing assignment.
# ---------------------------------------------------------------------------
EXECUTOR_VERSION_FOUND = 'found'
EXECUTOR_VERSION_UNREADABLE = 'unreadable'
EXECUTOR_VERSION_NOT_FOUND = 'not_found'
EXECUTOR_VERSION_EMPTY = 'empty'

_DIGITS_RE = re.compile(r'\d+')
_VERSION_DIR_RE = re.compile(r'^\d+\.\d+')
_MARSHALL_VERSION_RE = re.compile(r'^MARSHALL_VERSION\s*=\s*([\'"])(.*?)\1\s*$', re.MULTILINE)


def default_registry_path() -> Path:
    """Where the plugin manager keeps the registry on this machine.

    The home directory is resolved on every call, never at import, so a caller
    that redirects it — a test pointing ``HOME`` at a fixture tree — is honoured.
    """
    return Path.home() / '.claude' / 'plugins' / 'installed_plugins.json'


def default_cache_root() -> Path:
    """The directory holding one cache directory per bundle of this marketplace.

    ``default_cache_root() / bundle`` is the ``bundle_dir`` that
    :func:`newest_cache_version` and :func:`is_orphan_marked` take. The home
    directory is resolved on every call, as in :func:`default_registry_path`.
    """
    return Path.home() / '.claude' / 'plugins' / 'cache' / MARKETPLACE_NAME


def default_executor_path(project_root: Path) -> Path:
    """Where the generated executor of the checkout at ``project_root`` lives."""
    return project_root / '.plan' / 'execute-script.py'


def version_key(version_name: str) -> tuple[int, ...]:
    """Parse a version name into a comparable integer tuple.

    Each run of digits, in document order: ``'0.1.1069'`` -> ``(0, 1, 1069)``,
    so ``0.1.1069`` sorts after ``0.1.999``. A name with no digits yields the
    empty tuple. The semantics match ``marketplace_bundles._version_sort_key``,
    which this module cannot import (see the module docstring).
    """
    return tuple(int(part) for part in _DIGITS_RE.findall(version_name))


def read_registry(registry_path: Path, marketplace: str = MARKETPLACE_NAME) -> tuple[str, list[dict[str, str | None]]]:
    """Read the plugin registry into one row per scope entry of ``marketplace``.

    Returns ``(state, rows)``. ``state`` is one of the ``REGISTRY_*`` constants;
    ``rows`` is non-empty exactly when the state is :data:`REGISTRY_OK`.

    Each row is a dict with four keys:

    - ``bundle`` — the registry key's part before ``@``;
    - ``scope`` — the entry's ``scope`` (``user`` / ``project`` / ...), or ``None``;
    - ``install_path_version`` — the last path segment of ``installPath``, or ``None``;
    - ``version`` — the entry's ``version`` field, or ``None``.

    A bundle installed in several scopes yields several rows, and they are never
    collapsed: two scope entries that disagree with each other are exactly the
    condition a consumer needs to see. A field that is absent, empty or not a
    string is ``None`` — reported as unknown rather than guessed.
    """
    try:
        text = registry_path.read_text(encoding='utf-8')
    except FileNotFoundError:
        return REGISTRY_ABSENT, []
    except (OSError, UnicodeDecodeError):
        # Bytes that are not UTF-8 are a file that exists and cannot be read.
        return REGISTRY_IO_ERROR, []
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return REGISTRY_NOT_JSON, []

    plugins = data.get('plugins') if isinstance(data, dict) else None
    rows: list[dict[str, str | None]] = []
    if isinstance(plugins, dict):
        for key, entries in plugins.items():
            bundle, separator, owner = key.rpartition('@')
            if not separator or owner != marketplace or not isinstance(entries, list):
                continue
            for entry in entries:
                if isinstance(entry, dict):
                    rows.append(_row(bundle, entry))
    if not rows:
        return REGISTRY_NO_PLAN_MARSHALL_ENTRY, []
    return REGISTRY_OK, rows


def _row(bundle: str, entry: dict) -> dict[str, str | None]:
    install_path = _text_or_none(entry.get('installPath'))
    return {
        'bundle': bundle,
        'scope': _text_or_none(entry.get('scope')),
        'install_path_version': Path(install_path).name if install_path is not None else None,
        'version': _text_or_none(entry.get('version')),
    }


def _text_or_none(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def read_executor_version(executor_path: Path) -> tuple[str, str | None]:
    """Read the value of the executor's ``MARSHALL_VERSION`` assignment.

    Returns ``(state, version)``. ``version`` is set only for
    :data:`EXECUTOR_VERSION_FOUND`. The other states are distinct facts:

    - :data:`EXECUTOR_VERSION_UNREADABLE` — the file is absent, could not be read,
      or is not UTF-8 text;
    - :data:`EXECUTOR_VERSION_NOT_FOUND` — it was read and carries no such assignment;
    - :data:`EXECUTOR_VERSION_EMPTY` — the assignment is present and empty, the
      sentinel of an executor generated before any manifest existed.
    """
    try:
        text = executor_path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        return EXECUTOR_VERSION_UNREADABLE, None
    match = _MARSHALL_VERSION_RE.search(text)
    if match is None:
        return EXECUTOR_VERSION_NOT_FOUND, None
    version = match.group(2)
    if not version:
        return EXECUTOR_VERSION_EMPTY, None
    return EXECUTOR_VERSION_FOUND, version


def newest_cache_version(bundle_dir: Path) -> str | None:
    """The newest version directory name under ``bundle_dir``, or ``None``.

    Newest is decided by :func:`version_key` alone. **The ``.orphaned_at`` marker
    is not consulted for selection**: it has a foreign co-producer (the plugin
    manager's own garbage collector), so no selection turns on it. Use
    :func:`is_orphan_marked` to report the marker separately. ``None`` means the
    directory is absent, unreadable, or holds no version-shaped subdirectory.
    """
    try:
        names = [d.name for d in bundle_dir.iterdir() if d.is_dir() and _VERSION_DIR_RE.match(d.name)]
    except OSError:
        return None
    if not names:
        return None
    return max(names, key=version_key)


def is_orphan_marked(bundle_dir: Path, version: str) -> bool:
    """Whether the ``version`` directory of ``bundle_dir`` carries ``.orphaned_at``.

    Only the marker's existence is read, never its content.
    """
    return (bundle_dir / version / ORPHAN_MARKER_NAME).exists()


def classify_parity(rows: list[dict[str, str | None]], reference_version: str | None) -> str:
    """Classify the registry rows against ``reference_version``.

    Returns exactly one of :data:`PARITY_VERDICTS`. Both pinned fields of every
    row — ``install_path_version`` and ``version`` — are compared, so a registry
    that disagrees with itself can never read as in parity.

    Precedence, strongest first:

    1. :data:`PARITY_UNREADABLE` when there is nothing to compare: no rows (every
       non-ok registry read state yields none), or no usable reference version.
    2. :data:`PARITY_BEHIND` when any field is older than the reference. A
       demonstrated lag wins over everything below, so entries that disagree in
       both directions are ``behind``.
    3. :data:`PARITY_UNREADABLE` when any field is unknown, or differs from the
       reference without being orderable against it. Nothing is behind, yet
       parity was not established.
    4. :data:`PARITY_AHEAD` when at least one field is newer and none is older.
    5. :data:`PARITY_IN_PARITY` only when every field equals the reference.
    """
    if not rows or not reference_version:
        return PARITY_UNREADABLE
    reference_key = version_key(reference_version)
    if not reference_key:
        return PARITY_UNREADABLE

    older = False
    newer = False
    unknown = False
    for row in rows:
        for pinned in (row.get('install_path_version'), row.get('version')):
            if pinned is None:
                unknown = True
            elif pinned == reference_version:
                continue
            elif version_key(pinned) < reference_key:
                older = True
            elif version_key(pinned) > reference_key:
                newer = True
            else:
                unknown = True

    if older:
        return PARITY_BEHIND
    if unknown:
        return PARITY_UNREADABLE
    if newer:
        return PARITY_AHEAD
    return PARITY_IN_PARITY


__all__ = [
    'EXECUTOR_VERSION_EMPTY',
    'EXECUTOR_VERSION_FOUND',
    'EXECUTOR_VERSION_NOT_FOUND',
    'EXECUTOR_VERSION_UNREADABLE',
    'MARKETPLACE_NAME',
    'ORPHAN_MARKER_NAME',
    'PARITY_AHEAD',
    'PARITY_BEHIND',
    'PARITY_IN_PARITY',
    'PARITY_UNREADABLE',
    'PARITY_VERDICTS',
    'REGISTRY_ABSENT',
    'REGISTRY_IO_ERROR',
    'REGISTRY_NOT_JSON',
    'REGISTRY_NO_PLAN_MARSHALL_ENTRY',
    'REGISTRY_OK',
    'classify_parity',
    'default_cache_root',
    'default_executor_path',
    'default_registry_path',
    'is_orphan_marked',
    'newest_cache_version',
    'read_executor_version',
    'read_registry',
    'version_key',
]

# SPDX-License-Identifier: FSL-1.1-ALv2
"""Claude plugin-cache sync — the Claude path of the ``/sync-harnesses`` engine.

Pipeline:

    marketplace/bundles/  →  target/claude/  →  ~/.claude/plugins/cache/plan-marshall/{bundle}/{version}/

This module consumes the multi-target generator output at
``target/claude/`` (or a worktree-local equivalent) and rsyncs each
emitted bundle into the host plugin cache. After a successful (non-error)
sync it also mirrors the top-level ``target/claude/dist-manifest.json``
into the plugin-cache ROOT (``{cache_root}/dist-manifest.json``, alongside
the versioned ``{bundle}/{version}/`` dirs) so the dist-branch versioning
feature's ``find_installed_manifest_path`` resolves the installed version
from ``base_path/dist-manifest.json`` in the meta-project's own
preflight/executor-regen context.

It is a library, not an entry point: the single sync engine
``marketplace/targets/sync.py`` loads it BY FILE LOCATION and drives it
through :func:`sync_cache`. It is deliberately stdlib-only and is never
reached through the ``marketplace.targets`` / ``claude`` packages, whose
``__init__`` modules import third-party dependencies (``yaml``) that a
bare ``python3`` with no project virtualenv does not carry. For the same
reason it defines no ``@dataclass``: a module loaded by file location is
not necessarily registered in ``sys.modules``, which ``dataclasses``
requires under postponed annotation evaluation.

Staleness guard
---------------

The guard refuses to sync when ``target/claude/`` is missing, contains no
bundles, or is stale relative to the worktree source tree. Staleness is
determined by a sentinel file ``target/claude/.emit-marker.json`` written
at the end of every successful emit by
``marketplace/targets/claude/target.py``. The sentinel carries a
``source_tree_fingerprint`` computed from git's native ``ls-files`` /
``hash-object`` primitives over ``marketplace/bundles/``; the guard
recomputes the same fingerprint and refuses on mismatch. Both sides use
the helper in ``marketplace/targets/claude/source_fingerprint.py`` so the
fingerprint algorithm cannot drift between emit and sync.

The bundle-set check (check 2 of :func:`_staleness_guard`) expects in
``target/claude/`` exactly the bundles the Claude emitter selects: those
whose own ``.claude-plugin/plugin.json`` admits ``claude`` through its
``targets`` declaration. The field absent means every target; the field
present means the listed targets only. A bundle scoped to other harnesses
is therefore never expected in the Claude tree, while a claude-admitting
bundle missing from it is still refused as ``stale``. See
:func:`_claude_admitting_bundles`.

The sentinel fingerprint is supplemented by a file-level content-hash
check (``_file_level_drift``): the emitter records a per-file hash
manifest of the emitted tree in the sentinel's ``file_hashes`` field, and
the guard re-hashes each live file under ``target/claude/`` and compares
it to the manifest. A manifest entry whose live file is gone (missing) or
hashes differently (diverged), or a live target file absent from the
manifest (extra), is named by path in the refusal message — turning an
opaque single-digest mismatch into a per-file diagnosis. The manifest is
the comparison baseline (not the raw ``marketplace/bundles/`` source)
because ``target/claude/`` is transformed generator output — expanded
agent variants, a variant-aware ``plugin.json``, a top-level
``marketplace.json`` — with no verbatim source counterpart. The check
reuses the shared ``hash_objects`` primitive so the manifest and the
live re-hash compute identically, hashing the gitignored
``target/claude/`` tree directly via ``git hash-object`` (which reads
arbitrary worktree bytes regardless of tracking).

The guard reports the failure that OCCURRED, not the failure it hunts
for. Its refusals are discriminated into two kinds (see
:class:`GuardRefusal`): ``stale`` — a probe ran and observed a staleness
condition, so the remedy is to regenerate the target tree — and
``probe_failed`` — a probe could not run at all (the helper would not
import, git would not answer, a bundle manifest could not be read), so
nothing was observed about the target tree and its freshness is unknown.
A ``probe_failed`` refusal never borrows the regenerate remedy, because
sending the operator to re-run a generator whose output may already be
current is a misreport, not a fix. Both kinds refuse (exit 2), and
``--skip-staleness-guard`` remains the deliberate override.

Result document (rendered by :func:`render`):

    status: success | partial | error
    cache_status: success | partial | error
    synced_count: N
    failed_count: M
    summary_message: "<human-readable summary>"
    guard_outcome: stale | probe_failed   # only on a guard refusal
    dry_run: true                         # only under --dry-run
    synced[N]{bundle,version,status}:
      bundle1,0.1.0,success
    failed[M]{bundle,error}:
      bundle3,"rsync exited 23"
    registry_parity:                      # only when the engine attached one
      ...
      entries[K]{bundle,scope,install_path_version,version,synced_version,orphan_marked}:
        bundle1,user,0.1.0,0.1.0,0.1.0,false
      verdict: in_parity | behind | ahead | unreadable

``guard_outcome`` is present only when the staleness guard refused; its
absence on every other path means no guard verdict was reached. Under
``--dry-run`` the guard and the bundle selection still run, nothing is
written, and every selected bundle's row carries the status ``dry_run``
(so ``synced_count`` stays 0 — nothing was synced).

Destination symlinks
--------------------

The sync never mirrors through a symbolic link it finds in the cache. A
``{cache_root}/{bundle}`` or ``{cache_root}/{bundle}/{version}`` that is a
link, a link inside a version directory at a path the bundle holds as a
real file or directory, and a linked ``{cache_root}/dist-manifest.json``
are all REFUSED — never followed, never replaced by a real entry. Every
selected bundle is checked before the first one is mirrored, so one
refusal fails the whole run with ``status: error`` (exit 1), ``synced``
empty, one ``failed`` row per refused path and a ``summary_message``
naming the first; the cache is left exactly as it was. ``--dry-run``
reports the same refusal. ``cache_root`` itself may be a link. The checks
are the shared ones in ``marketplace/targets/fs_safety.py``.

``cache_status`` is always present and is the outcome of the cache sync
alone. ``status`` equals it unless the engine lowered ``status`` for a
reason that is not a cache-sync failure — a plugin registry pinned behind
the synced version. The ``registry_parity`` block is always the LAST member
of the document and its ``verdict`` the last line of the block.

This module reads no plugin registry and writes none: :func:`sync_cache`
mirrors the cache and nothing else. The ``registry_parity`` block is
computed by the engine (``marketplace/targets/sync.py``) after
:func:`sync_cache` returns and attached to the result; :func:`render` and
:func:`as_dict` only carry it.

Exit codes (carried on :class:`CacheSyncResult`):

    0 on ``status: success`` or ``status: partial`` (partial means at
      least one bundle synced; the caller decides whether to treat that
      as a hard failure based on the failure table).
    1 on ``status: error`` (nothing synced, hard failure).
    2 on a staleness-guard refusal.

:func:`sync_cache` returns only these three. The engine replaces a ``0``
with ``3`` when the attached ``registry_parity`` verdict is ``behind``.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from types import ModuleType
from typing import Any, NamedTuple


class GuardRefusal(NamedTuple):
    """A guard refusal, discriminated by WHY the guard refused.

    Two kinds, and the distinction is the whole point of the type:

    * ``stale`` — the guard's probe RAN and observed a real staleness
      condition (missing sentinel, fingerprint mismatch, file-level
      drift). The remedy is to regenerate the target tree, so the
      message carries :func:`_regenerate_hint`.
    * ``probe_failed`` — the guard's probe could NOT run (the helper
      would not import, git would not answer, a bundle manifest could
      not be read). Nothing was observed about the target tree, so its
      freshness is UNKNOWN. A ``probe_failed`` message therefore says so
      plainly and carries the remedy for the probe's own fault — never
      the regenerate hint, which would send the operator to re-run a
      generator whose output may already be current.

    Collapsing the second kind into the first is the defect this type
    exists to prevent: a guard that reports the failure it hunts for
    instead of the failure that occurred.
    """

    kind: str
    message: str


class CacheSyncResult(NamedTuple):
    """The outcome of one Claude cache sync, before rendering.

    ``guard_outcome`` is set only on a staleness-guard refusal and
    carries the refusal KIND (``stale`` / ``probe_failed``); ``None`` on
    every other path means no guard verdict was reached.

    ``cache_status`` and ``registry_parity`` are never set by
    :func:`sync_cache`; the engine attaches them afterwards. A ``None``
    ``cache_status`` means ``status`` IS the cache-sync outcome, which is
    how :func:`render` and :func:`as_dict` report it. ``registry_parity``
    is a mapping whose ``entries`` member is a list of rows carrying the
    :data:`REGISTRY_PARITY_ENTRY_FIELDS` keys; ``None`` means the engine
    attached no block.
    """

    exit_code: int
    status: str
    summary_message: str
    synced: list[dict[str, str]]
    failed: list[dict[str, str]]
    guard_outcome: str | None = None
    dry_run: bool = False
    cache_status: str | None = None
    registry_parity: dict[str, Any] | None = None


def _stale(message: str) -> GuardRefusal:
    """Build a ``stale`` refusal — the probe ran and found staleness."""
    return GuardRefusal(kind='stale', message=message)


def _probe_failed(what: str, detail: str, remedy: str) -> GuardRefusal:
    """Build a ``probe_failed`` refusal — the probe could not run at all.

    The message states what could not run, why, that the target tree was
    consequently NOT checked, and the remedy for the probe's own fault.
    It deliberately does NOT carry :func:`_regenerate_hint` — borrowing
    the staleness remedy for a failure that observed no staleness is
    exactly the misreport this shape prevents.
    """
    return GuardRefusal(
        kind='probe_failed',
        message=(
            f'staleness_guard: could not run — {what} ({detail}). '
            'The target tree was NOT checked, so its freshness is unknown; '
            f'this is not a staleness verdict. {remedy}'
        ),
    )


def _resolve_repo_root_for_sentinel(source_root: Path) -> Path:
    """Resolve the repo root that the sentinel was written against.

    The emitter computes the fingerprint relative to
    ``marketplace_dir.parent`` (the project root that contains
    ``marketplace/``). When sync runs against
    ``{repo}/target/claude/`` the repo root is the grandparent of
    ``source_root``. The ``--from-worktree`` and ``--source`` flags can
    move the source root around; the guard pairs the sentinel's
    recompute against the directory tree that produced it, which is
    always two levels up from ``source_root`` for the canonical
    ``{repo}/target/claude/`` layout. Callers using ``--source`` for
    ad-hoc paths can still bypass the guard via
    ``--skip-staleness-guard``.
    """
    return source_root.parent.parent


#: Repo-relative location of the shared fingerprint helper.
SOURCE_FINGERPRINT_RELPATH = Path('marketplace') / 'targets' / 'claude' / 'source_fingerprint.py'

#: Module name the helper is loaded under. Deliberately NOT
#: ``marketplace.targets.claude.source_fingerprint`` — see
#: :func:`_load_source_fingerprint_module` for why the package path is
#: avoided entirely.
HELPER_MODULE_NAME = '_sync_harnesses_source_fingerprint'

#: Repo-relative location of the shared filesystem-safety checks, and the
#: module name they are loaded under — by file location, like the helper above.
FS_SAFETY_RELPATH = Path('marketplace') / 'targets' / 'fs_safety.py'
FS_SAFETY_MODULE_NAME = '_sync_harnesses_cache_fs_safety'


def _repo_root_from_script() -> Path:
    """Resolve the project root from this module's own location.

    ``marketplace/targets/claude/cache_sync.py`` -> the repo root is
    three parents up: parents[0]=claude, [1]=targets, [2]=marketplace,
    [3]=repo.
    """
    return Path(__file__).resolve().parents[3]


def _load_source_fingerprint_module() -> ModuleType:
    """Load the fingerprint helper BY FILE LOCATION, not by package path.

    The helper (``marketplace/targets/claude/source_fingerprint.py``) is
    stdlib-only — ``hashlib``, ``shutil``, ``subprocess``, ``pathlib``.
    Reaching it through the package path
    ``marketplace.targets.claude.source_fingerprint`` does NOT import
    only that file: Python must first execute
    ``marketplace/targets/__init__.py``, which imports every registered
    target sub-package to fire their ``register_target`` side effects,
    and those target modules pull in third-party dependencies (``yaml``).
    The sync engine is invoked as a standalone file under a bare
    ``python3`` with no project virtualenv, where those dependencies are
    absent — so the package route raises ``ModuleNotFoundError`` on a
    dependency the helper itself never needed.

    Loading the single file via ``importlib.util.spec_from_file_location``
    executes exactly that module and nothing else, which keeps the
    stdlib-only helper reachable under a bare interpreter.

    The loaded module is cached in ``sys.modules`` under
    :data:`HELPER_MODULE_NAME` so repeated calls (the fingerprint check
    and the file-level drift check) share one module object — and
    therefore one ``FingerprintError`` class, so ``except`` clauses match
    across both call sites.

    Raises:
        ImportError: the helper file is absent, has no loadable spec, or
            fails while executing. Every failure is normalised to
            ``ImportError`` so callers have one exception type to handle.
    """
    return _load_sibling_module(HELPER_MODULE_NAME, SOURCE_FINGERPRINT_RELPATH, 'fingerprint helper')


def _load_fs_safety_module() -> ModuleType:
    """Load the shared filesystem-safety checks BY FILE LOCATION.

    ``marketplace/targets/fs_safety.py`` is stdlib-only and imports nothing
    from the package, so it is reachable the same way as the fingerprint
    helper and for the same reason — see
    :func:`_load_source_fingerprint_module`.

    Raises:
        ImportError: the module file is absent, has no loadable spec, or
            fails while executing.
    """
    return _load_sibling_module(FS_SAFETY_MODULE_NAME, FS_SAFETY_RELPATH, 'filesystem-safety module')


def _load_sibling_module(module_name: str, relpath: Path, label: str) -> ModuleType:
    """Execute the file at repo-relative ``relpath`` as ``module_name``, once per process.

    The module is cached in ``sys.modules`` under ``module_name``; a module
    that fails while executing is not left there.

    Raises:
        ImportError: the file is absent, has no loadable spec, or fails
            while executing. ``label`` names the module in the message.
    """
    cached = sys.modules.get(module_name)
    if cached is not None:
        return cached

    module_path = _repo_root_from_script() / relpath
    if not module_path.is_file():
        raise ImportError(f'{label} not found at {module_path}')

    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f'no loadable module spec for {label} at {module_path}')

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as exc:  # normalised to ImportError below
        sys.modules.pop(module_name, None)
        raise ImportError(f'{label} at {module_path} failed to import: {exc}') from exc
    return module


def _import_source_fingerprint() -> tuple[Any, Any]:
    """Return ``(compute_source_tree_fingerprint, FingerprintError)``.

    Thin accessor over :func:`_load_source_fingerprint_module`; raises
    ``ImportError`` when the helper cannot be loaded.
    """
    module = _load_source_fingerprint_module()
    return module.compute_source_tree_fingerprint, module.FingerprintError


def _import_hash_objects() -> tuple[Any, Any]:
    """Return ``(hash_objects, FingerprintError)``.

    ``hash_objects`` hashes arbitrary worktree bytes via
    ``git hash-object --stdin-paths`` regardless of whether the paths are
    tracked — so it works on the gitignored ``target/claude/`` tree as
    well as the tracked ``marketplace/bundles/`` source. Thin accessor
    over :func:`_load_source_fingerprint_module`; raises ``ImportError``
    when the helper cannot be loaded.
    """
    module = _load_source_fingerprint_module()
    return module.hash_objects, module.FingerprintError


DEFAULT_CACHE_ROOT = Path.home() / '.claude' / 'plugins' / 'cache' / 'plan-marshall'
TARGET_SUBDIR = Path('target') / 'claude'
MARKETPLACE_SUBDIR = Path('marketplace') / 'bundles'

# Sentinel filename written at the end of every successful emit by the
# Claude target. See ``marketplace/targets/claude/target.py``.
EMIT_MARKER_FILENAME = '.emit-marker.json'

# Top-level manifest filename mirrored into the plugin-cache ROOT after a
# successful sync. The dist-branch versioning feature reads the installed
# version from ``base_path/dist-manifest.json``; for the meta-project's own
# preflight the base_path IS the cache root, so the manifest must ride into
# the cache root alongside the versioned ``{bundle}/{version}/`` dirs.
DIST_MANIFEST_FILENAME = 'dist-manifest.json'

#: Registry name of the Claude target — the value a bundle's ``targets``
#: declaration must contain for the Claude emitter to emit it. Mirrors
#: ``CLAUDE_TARGET_NAME`` in ``marketplace/targets/claude/emitter.py``,
#: restated here because that module is reachable only through the
#: package path this module must not import.
CLAUDE_TARGET_NAME = 'claude'

#: ``plugin.json`` field a bundle uses to declare the targets it ships to.
#: Mirrors ``TARGET_SCOPE_FIELD`` in ``marketplace/targets/component_targets.py``.
TARGET_SCOPE_FIELD = 'targets'

#: Status a bundle row carries under ``--dry-run``: selected, not synced.
DRY_RUN_ROW_STATUS = 'dry_run'

#: Columns of the ``registry_parity`` block's ``entries`` table, in order.
REGISTRY_PARITY_ENTRY_FIELDS: tuple[str, ...] = (
    'bundle',
    'scope',
    'install_path_version',
    'version',
    'synced_version',
    'orphan_marked',
)

#: Members of the ``registry_parity`` block that hold free text and are quoted.
REGISTRY_PARITY_TEXT_FIELDS: frozenset[str] = frozenset({'registry_path', 'reason', 'repin_message'})


def _read_version(plugin_json: Path) -> str:
    try:
        data = json.loads(plugin_json.read_text(encoding='utf-8'))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return 'unknown'
    if not isinstance(data, dict):
        return 'unknown'
    version = data.get('version')
    return version if isinstance(version, str) and version else 'unknown'


def render(result: CacheSyncResult) -> str:
    """Render the result document.

    ``guard_outcome`` is emitted only on a staleness-guard refusal and
    carries the refusal KIND (``stale`` / ``probe_failed``) so a consumer
    can tell "the target tree is stale" from "the guard could not run"
    without parsing prose. It is absent on every non-guard path, because
    no guard verdict was reached there — an absent field is honest about
    that, where a default value would not be.

    ``cache_status`` is always emitted. The ``registry_parity`` block,
    when the engine attached one, is emitted last.
    """
    synced_count = sum(1 for row in result.synced if row['status'] == 'success')
    summary = result.summary_message.replace('"', '\\"')
    lines = [
        f'status: {result.status}',
        f'cache_status: {_cache_status(result)}',
        f'synced_count: {synced_count}',
        f'failed_count: {len(result.failed)}',
        f'summary_message: "{summary}"',
    ]
    if result.guard_outcome is not None:
        lines.append(f'guard_outcome: {result.guard_outcome}')
    if result.dry_run:
        lines.append('dry_run: true')
    lines.append(f'synced[{len(result.synced)}]{{bundle,version,status}}:')
    for row in result.synced:
        lines.append(f'  {row["bundle"]},{row["version"]},{row["status"]}')
    if result.failed:
        lines.append(f'failed[{len(result.failed)}]{{bundle,error}}:')
        for row in result.failed:
            err = row['error'].replace('"', '\\"')
            lines.append(f'  {row["bundle"]},"{err}"')
    if result.registry_parity is not None:
        lines.extend(_render_registry_parity(result.registry_parity))
    return '\n'.join(lines) + '\n'


def _cache_status(result: CacheSyncResult) -> str:
    """The cache-sync outcome: the attached value, else ``status`` itself."""
    return result.cache_status if result.cache_status is not None else result.status


def _render_registry_parity(block: dict[str, Any]) -> list[str]:
    """Render the ``registry_parity`` block in the mapping's own key order.

    The engine builds the mapping with ``entries`` and ``verdict`` as its last
    two members, so the verdict is the last line of the document. ``entries``
    is rendered as a table; a free-text member is quoted; every other member
    is a bare token.
    """
    lines = ['registry_parity:']
    for key, value in block.items():
        if key == 'entries':
            lines.append(f'  entries[{len(value)}]{{{",".join(REGISTRY_PARITY_ENTRY_FIELDS)}}}:')
            for entry in value:
                lines.append('    ' + ','.join(_table_cell(entry[field]) for field in REGISTRY_PARITY_ENTRY_FIELDS))
        elif key in REGISTRY_PARITY_TEXT_FIELDS:
            text = str(value).replace('"', '\\"')
            lines.append(f'  {key}: "{text}"')
        else:
            lines.append(f'  {key}: {value}')
    return lines


def _table_cell(value: object) -> str:
    if isinstance(value, bool):
        return 'true' if value else 'false'
    return str(value)


def as_dict(result: CacheSyncResult) -> dict[str, Any]:
    """Return the result as a plain mapping carrying :func:`render`'s fields.

    The all-targets run of the sync engine nests each target's result in
    one aggregate document, which needs the fields as data rather than
    as rendered text. The field set and its conditional members
    (``guard_outcome``, ``dry_run``, ``failed``, ``registry_parity``)
    match :func:`render`.
    """
    data: dict[str, Any] = {
        'status': result.status,
        'cache_status': _cache_status(result),
        'synced_count': sum(1 for row in result.synced if row['status'] == 'success'),
        'failed_count': len(result.failed),
        'summary_message': result.summary_message,
    }
    if result.guard_outcome is not None:
        data['guard_outcome'] = result.guard_outcome
    if result.dry_run:
        data['dry_run'] = True
    data['synced'] = result.synced
    if result.failed:
        data['failed'] = result.failed
    if result.registry_parity is not None:
        data['registry_parity'] = result.registry_parity
    return data


def resolve_source_root(source: Path | None, from_worktree: Path | None) -> Path:
    """Resolve the emitted-tree root: explicit override, worktree, then cwd."""
    if source is not None:
        return source
    if from_worktree is not None:
        return from_worktree / TARGET_SUBDIR
    return Path.cwd() / TARGET_SUBDIR


def resolve_marketplace_root(from_worktree: Path | None) -> Path:
    """Resolve the ``marketplace/bundles/`` root the guard compares against."""
    if from_worktree is not None:
        return from_worktree / MARKETPLACE_SUBDIR
    return Path.cwd() / MARKETPLACE_SUBDIR


def _regenerate_hint() -> str:
    return 'Regenerate with `./pw generate-claude`.'


def _is_bundle_dir(path: Path) -> bool:
    """A directory is a bundle iff it carries its own ``.claude-plugin/plugin.json``.

    Filters out non-bundle directories that may live alongside bundle
    folders in the target tree — notably the top-level ``.claude-plugin/``
    directory that holds the marketplace.json registration manifest.
    """
    return path.is_dir() and (path / '.claude-plugin' / 'plugin.json').is_file()


def _bundle_manifest_probe_failed(manifest: Path, detail: str) -> GuardRefusal:
    """Build the ``probe_failed`` refusal for an unreadable bundle manifest."""
    return _probe_failed(
        f'the bundle-set probe could not read the `{TARGET_SCOPE_FIELD}` declaration in {manifest}',
        detail,
        f'Repair {manifest}, or re-run with --skip-staleness-guard to sync without the check.',
    )


def _bundle_admits_claude(manifest: Path) -> bool | GuardRefusal:
    """Whether the bundle owning ``manifest`` ships to the Claude target.

    Applies the same ``targets`` declaration predicate the Claude emitter
    applies (``bundle_emits_to`` in
    ``marketplace/targets/component_targets.py``), read with stdlib
    ``json`` because that module is reachable only through the package
    path:

    * field absent — the bundle ships to every target, so it is admitted;
    * field present — the bundle ships to the listed targets only. The
      value is a list of names, or a single string (which may list
      several names separated by commas).

    A manifest that cannot be read, is not a JSON object, or declares a
    value that is not a non-empty list of names yields a ``probe_failed``
    refusal naming the file. It is never resolved to an include or an
    exclude: either guess would report a verdict about a declaration
    nobody read.
    """
    try:
        data = json.loads(manifest.read_text(encoding='utf-8'))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return _bundle_manifest_probe_failed(manifest, str(exc))
    if not isinstance(data, dict):
        return _bundle_manifest_probe_failed(manifest, 'the manifest is not a JSON object')
    if TARGET_SCOPE_FIELD not in data:
        return True

    value = data[TARGET_SCOPE_FIELD]
    if isinstance(value, str):
        names = [token.strip() for token in value.split(',') if token.strip()]
    elif isinstance(value, list) and all(isinstance(item, str) for item in value):
        names = [item.strip() for item in value if item.strip()]
    else:
        return _bundle_manifest_probe_failed(
            manifest, f'`{TARGET_SCOPE_FIELD}` is {type(value).__name__}, not a list of target names'
        )
    if not names:
        return _bundle_manifest_probe_failed(manifest, f'`{TARGET_SCOPE_FIELD}` declares no target name')
    return CLAUDE_TARGET_NAME in names


def _claude_admitting_bundles(marketplace_root: Path) -> list[str] | GuardRefusal:
    """Return the sorted names of the source bundles the Claude emitter selects.

    This is the expected bundle set of ``target/claude/``. It is derived
    from the SOURCE declarations rather than read back from the emitted
    ``dist-manifest.json``: a set read from the emitted tree would be
    circular, and could never report a bundle that was added to source
    and not re-emitted. Returns a ``probe_failed`` refusal as soon as one
    bundle's manifest cannot be read — see :func:`_bundle_admits_claude`.
    """
    admitted: list[str] = []
    for bundle_dir in sorted(p for p in marketplace_root.iterdir() if _is_bundle_dir(p)):
        verdict = _bundle_admits_claude(bundle_dir / '.claude-plugin' / 'plugin.json')
        if isinstance(verdict, GuardRefusal):
            return verdict
        if verdict:
            admitted.append(bundle_dir.name)
    return admitted


def _relative_file_map(root: Path) -> dict[str, Path]:
    """Map every regular file under ``root`` to its ``root``-relative POSIX path.

    The map key is the path relative to ``root`` rendered with forward
    slashes so the source and target trees compare identically across
    platforms. Symlinks and non-regular entries are skipped — only the
    file bytes that ``rsync`` would mirror participate in the drift
    comparison. Returns an empty map when ``root`` is not a directory.
    """
    if not root.is_dir():
        return {}
    file_map: dict[str, Path] = {}
    try:
        for path in root.rglob('*'):
            if path.is_file() and not path.is_symlink():
                file_map[path.relative_to(root).as_posix()] = path
    except OSError:
        return file_map
    return file_map


def _file_level_drift(source_root: Path, file_hashes: dict[str, str]) -> GuardRefusal | None:
    """Return a :class:`GuardRefusal` naming per-file target drift, else None.

    Supplements the single ``source_tree_fingerprint`` sentinel with
    per-file granularity by comparing the emitted ``target/claude/`` tree
    against the per-file hash manifest the emitter recorded in the
    sentinel (``file_hashes`` — keyed by ``source_root``-relative POSIX
    path). ``target/claude/`` is TRANSFORMED generator output (expanded
    agent variants, a variant-aware ``plugin.json``, a top-level
    ``marketplace.json``), not a raw mirror of ``marketplace/bundles/`` —
    so the manifest, not the raw source tree, is the only correct
    comparison baseline. Three drift classes are detected and the specific
    offending paths are named in the refusal message:

    * **missing** — a manifest entry has no corresponding live file
      (an emitted file was deleted after the emit).
    * **diverged** — a manifest entry's live file hashes differently than
      recorded (the file's bytes were mutated after the emit).
    * **extra** — a live ``target/claude/`` file is absent from the
      manifest (a stray artefact appeared after the emit). The sentinel
      itself (``.emit-marker.json``) is always excluded — it carries the
      manifest and so can never be one of its own entries.

    Hashing delegates to the shared ``hash_objects`` primitive
    (``git hash-object``) so the live hashes are byte-identical to the
    manifest the emitter wrote with the same primitive; the live files are
    passed by ABSOLUTE path because ``git hash-object`` resolves a relative
    pathspec against the enclosing repo's worktree root (not the ``-C``
    directory), which would break when ``target/claude/`` lives inside a
    git repo — as it always does in production. ``git hash-object`` reads
    arbitrary worktree bytes and therefore works on the gitignored
    ``target/claude/`` tree. Returns ``None`` when every manifest entry
    matches its live file and the tree carries no extra file.

    When the check cannot RUN — the helper will not import, or ``git
    hash-object`` will not answer — it returns a ``probe_failed``
    refusal naming that fault. It does NOT return ``None``: a ``None``
    here is read by the caller as "the file-level check ran and found
    nothing", so returning it for a check that never ran would report a
    clean tree on no evidence and let the sync proceed as though the
    supplementary guard had passed. Refusing loudly, and saying which
    probe broke, is the honest outcome; ``--skip-staleness-guard``
    remains the deliberate override.
    """
    live_files = _relative_file_map(source_root)
    live_files.pop(EMIT_MARKER_FILENAME, None)

    missing = sorted(rel for rel in file_hashes if rel not in live_files)
    extra = sorted(rel for rel in live_files if rel not in file_hashes)

    try:
        hash_objects, _FingerprintError = _import_hash_objects()
    except ImportError as exc:
        return _probe_failed(
            'the file-level drift check failed to import the hashing helper',
            str(exc),
            'Repair the helper at '
            f'{SOURCE_FINGERPRINT_RELPATH.as_posix()}, or re-run with '
            '--skip-staleness-guard to sync without the check.',
        )

    common = sorted(set(file_hashes) & set(live_files))
    diverged: list[str] = []
    if common:
        abs_paths = [str(live_files[rel].resolve()) for rel in common]
        try:
            live_shas = hash_objects(source_root, abs_paths)
        except _FingerprintError as exc:
            return _probe_failed(
                'the file-level drift check could not hash the live target tree',
                str(exc),
                'The check needs a working `git` on PATH and a git work tree '
                f'containing {source_root}; re-run with --skip-staleness-guard '
                'to sync without the check.',
            )
        for rel, live_sha in zip(common, live_shas, strict=True):
            if live_sha != file_hashes[rel]:
                diverged.append(rel)

    if not (missing or extra or diverged):
        return None

    parts: list[str] = []
    if missing:
        parts.append(f'missing from target: {", ".join(missing)}')
    if extra:
        parts.append(f'extra in target: {", ".join(extra)}')
    if diverged:
        parts.append(f'content diverged: {", ".join(diverged)}')
    return _stale(
        'staleness_guard: target/claude/ drifted from its emit manifest at file level — '
        + '; '.join(parts)
        + f'. {_regenerate_hint()}'
    )


def _staleness_guard(source_root: Path, marketplace_root: Path) -> GuardRefusal | None:
    """Return a :class:`GuardRefusal` when sync must not proceed, else None.

    The refusal is discriminated: ``stale`` means a probe RAN and saw a
    staleness condition; ``probe_failed`` means a probe could NOT run, so
    nothing was observed about the target tree. The two carry different
    messages and different remedies, and neither is reported as the
    other — a guard must report the failure that occurred, not the
    failure it hunts for.

    Sentinel-based staleness check:

    1. ``source_root`` must exist and contain at least one bundle.
    2. Every source bundle the Claude emitter selects must also be
       present in ``source_root`` (catches "added a bundle, forgot to
       re-emit"). The expected set is the bundles under
       ``marketplace_root`` whose own ``.claude-plugin/plugin.json``
       admits ``claude`` through its ``targets`` declaration — field
       absent means every target, field present means the listed targets
       only — which is the predicate the emitter itself applies. A bundle
       scoped to other harnesses is never expected here. A bundle
       manifest that cannot be read is a ``probe_failed`` refusal naming
       the file, never a silent include or exclude.
    3. The sentinel file ``{source_root}/.emit-marker.json`` must exist
       and parse as JSON carrying a ``source_tree_fingerprint`` field.
    4. Recomputing the fingerprint against the worktree
       ``marketplace/bundles/`` (via the shared
       ``compute_source_tree_fingerprint`` helper in
       ``marketplace/targets/claude/source_fingerprint.py``) must match
       the sentinel's stored fingerprint. Mismatch -> source drifted
       since the last emit; refuse so callers regenerate before sync.
    5. File-level content-hash check (``_file_level_drift``): every file
       under ``target/claude/`` is compared against the per-file hash
       manifest the emitter recorded in the sentinel's ``file_hashes``
       field. A manifest entry whose live file is gone (missing) or hashes
       differently (diverged), or a live target file absent from the
       manifest (extra), is named in the refusal message. This supplements
       the single-sentinel fingerprint with per-file granularity so a
       localized target drift is reported by path rather than as an opaque
       digest mismatch. The manifest — not the raw ``marketplace/bundles/``
       tree — is the comparison baseline because ``target/claude/`` is
       transformed generator output, not a verbatim source mirror.
    """
    if not source_root.is_dir():
        return _stale(f'source root not found: {source_root}. {_regenerate_hint()}')
    bundles_in_source = sorted(p.name for p in source_root.iterdir() if _is_bundle_dir(p))
    if not bundles_in_source:
        return _stale(f'source root contains no bundles: {source_root}. {_regenerate_hint()}')

    if marketplace_root.is_dir():
        expected = _claude_admitting_bundles(marketplace_root)
        if isinstance(expected, GuardRefusal):
            return expected
        missing = [b for b in expected if b not in bundles_in_source]
        if missing:
            return _stale(
                'target/claude/ appears stale — bundles in marketplace/bundles/ that ship to the '
                f'claude target are missing from target output: {", ".join(missing)}. {_regenerate_hint()}'
            )

    sentinel_path = source_root / EMIT_MARKER_FILENAME
    if not sentinel_path.is_file():
        return _stale(
            f'staleness_guard: sentinel missing or unreadable at {sentinel_path} '
            f'— run finalize-step-deploy-target first. {_regenerate_hint()}'
        )
    try:
        sentinel = json.loads(sentinel_path.read_text(encoding='utf-8'))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return _stale(
            f'staleness_guard: sentinel missing or unreadable at {sentinel_path} ({exc}). {_regenerate_hint()}'
        )
    if not isinstance(sentinel, dict):
        return _stale(
            f'staleness_guard: sentinel missing or unreadable at {sentinel_path} '
            f'(the sentinel is not a JSON object). {_regenerate_hint()}'
        )
    stored_fingerprint = sentinel.get('source_tree_fingerprint')
    if not isinstance(stored_fingerprint, str) or not stored_fingerprint:
        return _stale(
            f'staleness_guard: sentinel at {sentinel_path} is missing source_tree_fingerprint. {_regenerate_hint()}'
        )

    try:
        compute_source_tree_fingerprint, FingerprintError = _import_source_fingerprint()
    except ImportError as exc:
        # The helper would not load, so the fingerprint was never
        # recomputed and nothing is known about the target tree. Report
        # THAT, without the regenerate hint — re-running the generator
        # fixes staleness, and no staleness was observed here.
        return _probe_failed(
            'the source-fingerprint probe failed to import its helper',
            str(exc),
            f'Repair the helper at {SOURCE_FINGERPRINT_RELPATH.as_posix()} or run the '
            'sync through the project environment; --skip-staleness-guard syncs '
            'without the check.',
        )

    repo_root = _resolve_repo_root_for_sentinel(source_root)
    try:
        live_fingerprint = compute_source_tree_fingerprint(repo_root)
    except FingerprintError as exc:
        # Same shape as the import failure: the recompute did not
        # produce a fingerprint, so there is nothing to compare and no
        # staleness verdict to report.
        return _probe_failed(
            'the source-fingerprint probe could not recompute the fingerprint',
            str(exc),
            f'The fingerprint needs a working `git` on PATH and a git work tree at '
            f'{repo_root}; --skip-staleness-guard syncs without the check.',
        )

    if live_fingerprint != stored_fingerprint:
        return _stale(
            'staleness_guard: source tree changed since last emit — '
            f're-run finalize-step-deploy-target. {_regenerate_hint()}'
        )

    file_hashes = sentinel.get('file_hashes')
    if isinstance(file_hashes, dict):
        file_drift = _file_level_drift(source_root, file_hashes)
        if file_drift is not None:
            return file_drift

    return None


def _destination_refusal(fs_safety: ModuleType, *, source_dir: Path, dest_dir: Path, cache_root: Path) -> str | None:
    """Return why ``dest_dir`` must not be mirrored into, or ``None`` when it may be.

    ``mkdir(exist_ok=True)`` accepts an existing link to a directory, and
    ``rsync --delete`` with a trailing slash then mirrors into the link's
    target, deleting what the bundle does not hold. Refused, each naming the
    offending path:

    * ``{cache_root}/{bundle}`` or ``{cache_root}/{bundle}/{version}`` that
      is a link, or resolves outside the resolved ``cache_root``; and
    * a link inside the version directory at a path the bundle holds as a
      real file or directory. ``rsync`` would replace such a link rather
      than write through it, and a link is not replaced either. A link the
      bundle itself ships as a link is left to ``rsync``, and so is a link
      the bundle no longer holds: ``--delete`` removes it as a link.

    The check only reads, and the bundle is walked top-down so the first link
    on the way to an entry is the one named.
    """
    try:
        fs_safety.refuse_escaping_output_dir(dest_dir.parent, cache_root)
        fs_safety.refuse_escaping_output_dir(dest_dir, cache_root)
        for root, dirnames, filenames in os.walk(source_dir):
            generated = Path(root)
            installed = dest_dir / generated.relative_to(source_dir)
            for name in sorted(dirnames + filenames):
                if not (generated / name).is_symlink():
                    fs_safety.refuse_symlink(installed / name)
    except ValueError as exc:
        return str(exc)
    return None


def _destination_refusals(source_root: Path, cache_root: Path, bundles: list[Path]) -> list[dict[str, str]] | str:
    """Return one ``{bundle, error}`` row per bundle whose destination is refused.

    A refused ``dist-manifest.json`` at the cache root is reported under
    :data:`DIST_MANIFEST_FILENAME` in place of a bundle name. A string is
    returned instead when the checks themselves could not be loaded — nothing
    was checked then, which is never reported as an empty list.
    """
    try:
        fs_safety = _load_fs_safety_module()
    except ImportError as exc:
        return str(exc)

    refusals: list[dict[str, str]] = []
    for bundle_dir in bundles:
        version = _read_version(bundle_dir / '.claude-plugin' / 'plugin.json')
        error = _destination_refusal(
            fs_safety, source_dir=bundle_dir, dest_dir=cache_root / bundle_dir.name / version, cache_root=cache_root
        )
        if error is not None:
            refusals.append({'bundle': bundle_dir.name, 'error': error})

    if (source_root / DIST_MANIFEST_FILENAME).is_file():
        try:
            fs_safety.refuse_symlink(cache_root / DIST_MANIFEST_FILENAME)
        except ValueError as exc:
            refusals.append({'bundle': DIST_MANIFEST_FILENAME, 'error': str(exc)})
    return refusals


def _rsync_bundle(*, source_dir: Path, dest_dir: Path) -> tuple[str, str]:
    """rsync one bundle. Returns (status, error_message).

    A ``dest_dir`` that is a link, or sits directly behind one, is failed
    without being created or mirrored into. :func:`sync_cache` refuses such a
    destination for the whole run before any bundle is mirrored; this repeats
    the check at the point of the write.
    """
    for candidate in (dest_dir.parent, dest_dir):
        if candidate.is_symlink():
            return 'failed', f'refusing to mirror into {dest_dir}: {candidate} is a symbolic link'
    if not shutil.which('rsync'):
        return 'failed', 'rsync not found on PATH'
    dest_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        'rsync',
        '-a',
        '--delete',
        f'{source_dir}/',
        f'{dest_dir}/',
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except (subprocess.TimeoutExpired, OSError) as exc:
        return 'failed', f'rsync exec error: {exc}'
    if result.returncode != 0:
        return 'failed', f'rsync exited {result.returncode}: {result.stderr.strip() or result.stdout.strip()}'
    return 'success', ''


def _copy_dist_manifest(source_root: Path, cache_root: Path) -> bool:
    """Mirror the top-level ``dist-manifest.json`` into the plugin-cache root.

    The dist-branch versioning feature reads the installed version from the
    resolved ``base_path`` — which for the meta-project's own preflight and
    executor-regen calls is the plugin-cache root
    (``~/.claude/plugins/cache/plan-marshall``). The per-bundle rsync only
    mirrors ``{cache_root}/{bundle}/{version}/`` and never populates the
    ``base_path/dist-manifest.json`` slot that ``find_installed_manifest_path``
    resolves, so the manifest must be copied into the cache root explicitly.
    This mirrors the documented design — the manifest "rides into the plugin
    cache on install".

    The copy targets the cache ROOT, alongside the versioned
    ``{bundle}/{version}/`` directories; the per-bundle ``rsync --delete``
    never touches the root, so the copied sentinel is not clobbered.

    Best-effort: an absent source manifest is a no-op (matching the
    fresh-install/empty-sentinel discipline elsewhere) and a copy error is
    swallowed, so a missing or unwritable manifest never converts a
    successful sync into a failure. Returns ``True`` only when the manifest
    was copied, ``False`` otherwise.

    A destination manifest that is a symbolic link is left exactly as it is —
    neither followed nor replaced. :func:`sync_cache` refuses the run before
    this point when it finds one; this repeats the check at the point of the
    write.
    """
    source_manifest = source_root / DIST_MANIFEST_FILENAME
    if not source_manifest.is_file():
        return False
    dest_manifest = cache_root / DIST_MANIFEST_FILENAME
    if dest_manifest.is_symlink():
        return False
    try:
        cache_root.mkdir(parents=True, exist_ok=True)
        dest_manifest.unlink(missing_ok=True)
        shutil.copyfile(source_manifest, dest_manifest)
    except OSError:
        return False
    return True


def _select_bundles(source_root: Path, only: str | None) -> list[Path]:
    if not source_root.is_dir():
        return []
    bundles = sorted(p for p in source_root.iterdir() if _is_bundle_dir(p))
    if only is not None:
        bundles = [b for b in bundles if b.name == only]
    return bundles


def sync_cache(
    *,
    source_root: Path,
    marketplace_root: Path,
    cache_root: Path,
    only_bundle: str | None = None,
    skip_staleness_guard: bool = False,
    dry_run: bool = False,
) -> CacheSyncResult:
    """Sync the emitted Claude tree at ``source_root`` into ``cache_root``.

    Args:
        source_root: The emitted ``target/claude/`` tree.
        marketplace_root: The ``marketplace/bundles/`` source tree the
            staleness guard compares the emitted tree against.
        cache_root: The plugin-cache root the bundles are mirrored into.
        only_bundle: Restrict the sync to the bundle of this name.
        skip_staleness_guard: Bypass the staleness guard entirely.
        dry_run: Run the guard and the bundle selection, write nothing.

    Returns:
        The sync outcome, carrying the exit code the engine returns.
    """
    if not skip_staleness_guard:
        refusal = _staleness_guard(source_root, marketplace_root)
        if refusal is not None:
            return CacheSyncResult(
                exit_code=2,
                status='error',
                summary_message=refusal.message,
                synced=[],
                failed=[],
                guard_outcome=refusal.kind,
                dry_run=dry_run,
            )

    bundles = _select_bundles(source_root, only_bundle)
    if not bundles:
        msg = f'no matching bundles in {source_root}' + (f' (filter: --bundles {only_bundle})' if only_bundle else '')
        return CacheSyncResult(exit_code=1, status='error', summary_message=msg, synced=[], failed=[], dry_run=dry_run)

    # Every destination is cleared of links before the first bundle is
    # mirrored, so a refused sync leaves the cache exactly as it was.
    refusals = _destination_refusals(source_root, cache_root, bundles)
    if isinstance(refusals, str):
        msg = f'claude cache sync could not start — the destination checks failed to load: {refusals}'
        return CacheSyncResult(exit_code=1, status='error', summary_message=msg, synced=[], failed=[], dry_run=dry_run)
    if refusals:
        more = f' (and {len(refusals) - 1} more refused, see failed)' if len(refusals) > 1 else ''
        msg = f'claude cache sync refused, nothing was synced: {refusals[0]["error"]}{more}'
        return CacheSyncResult(
            exit_code=1, status='error', summary_message=msg, synced=[], failed=refusals, dry_run=dry_run
        )

    if dry_run:
        planned = [
            {
                'bundle': bundle_dir.name,
                'version': _read_version(bundle_dir / '.claude-plugin' / 'plugin.json'),
                'status': DRY_RUN_ROW_STATUS,
            }
            for bundle_dir in bundles
        ]
        return CacheSyncResult(
            exit_code=0,
            status='success',
            summary_message=f'would sync {len(planned)} bundle(s) to {cache_root}',
            synced=planned,
            failed=[],
            dry_run=True,
        )

    synced: list[dict[str, str]] = []
    failed: list[dict[str, str]] = []

    def task(bundle_dir: Path) -> tuple[str, str, str, str]:
        version = _read_version(bundle_dir / '.claude-plugin' / 'plugin.json')
        dest = cache_root / bundle_dir.name / version
        status, error = _rsync_bundle(source_dir=bundle_dir, dest_dir=dest)
        return bundle_dir.name, version, status, error

    with ThreadPoolExecutor(max_workers=min(8, len(bundles))) as pool:
        futures = [pool.submit(task, b) for b in bundles]
        for fut in as_completed(futures):
            name, version, status, error = fut.result()
            synced.append({'bundle': name, 'version': version, 'status': status})
            if status != 'success':
                failed.append({'bundle': name, 'error': error or 'unknown error'})

    synced.sort(key=lambda row: row['bundle'])
    failed.sort(key=lambda row: row['bundle'])

    if not failed:
        status = 'success'
        message = f'synced {len(synced)} bundle(s) to {cache_root}'
        exit_code = 0
    elif len(failed) == len(bundles):
        status = 'error'
        message = f'all {len(failed)} bundle(s) failed'
        exit_code = 1
    else:
        status = 'partial'
        message = f'{len(synced) - len(failed)} succeeded, {len(failed)} failed'
        exit_code = 0

    # Mirror the top-level dist-manifest.json into the cache root after a
    # successful (non-error) sync so the meta-project's own preflight can
    # resolve the installed version from base_path/dist-manifest.json.
    if status != 'error':
        _copy_dist_manifest(source_root, cache_root)

    return CacheSyncResult(exit_code=exit_code, status=status, summary_message=message, synced=synced, failed=failed)

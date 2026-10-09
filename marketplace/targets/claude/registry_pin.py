#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Repin the plugin registry to the synced plugin-cache version (meta-project-only).

The harness sync moves the plugin CACHE forward: it writes a new
``{cache_root}/{bundle}/{version}/`` directory per bundle. It does not touch the
plugin REGISTRY (``installed_plugins.json``), which still names the previous
version — so a restarted session re-reads the same stale
pin and loads the same stale body. This script is the explicit, opt-in step that
closes that gap: it rewrites the registry's plan-marshall entries to the synced
version.

It is a DRY RUN unless ``--apply`` is passed. Without the flag it reads the
registry and the cache, prints what it would do per entry, and writes nothing.

Order of operations under ``--apply``
-------------------------------------
1. Remove ``.orphaned_at`` from each ``{bundle}/{target-version}`` directory an
   entry is pinned to once the run is over, so the directory the registry is
   about to name is not one the plugin manager's collector has scheduled for
   deletion.
2. Back the registry up, once, beside itself.
3. Rewrite ``installPath``, ``version`` and ``lastUpdated`` — and
   ``gitCommitSha`` when the cache-root ``dist-manifest.json`` names a
   ``source_sha``. The write goes through a temp file in the registry's own
   directory and an atomic ``os.replace``.
4. Re-read the registry and FAIL when any repinned entry is not at the target
   version.

Steps 2 and 3 are skipped when no entry needs a rewrite, so an already-pinned
registry is left byte-identical and gains no backup file.

What is never touched
---------------------
- Entries of any other marketplace: they are carried through the rewrite
  unchanged.
- Every ``.in_use`` file.
- An entry already NEWER than the target version. The repin never moves a pin
  backwards.
- A registry path that is a symbolic link. When an entry needs a rewrite the
  run is refused before step 1: the repin neither writes through the link nor
  replaces it. The dry run and a run with nothing to rewrite never write the
  registry; they read it through the link.
- Anything reached through a link inside the cache. When a ``{bundle}`` or
  ``{bundle}/{version}`` directory the run would act in is a symbolic link or
  resolves outside the resolved cache root, or its ``.orphaned_at`` marker is
  itself a link, the run is refused before step 1. The cache root itself may
  be a link.

Concurrency
-----------
The repin is a read-modify-write of a file Claude Code also writes, so the
window between reading the registry and replacing it is a check-then-act
hazard. Two mitigations are combined, per the TOCTOU menu in
``ref-code-quality/standards/code-organization.md``: the write is one atomic
``os.replace`` (a reader never sees a torn document), preceded by a re-read
that refuses to replace a registry whose bytes changed since it was read; and
the post-write gate of step 4 re-reads the result and fails loudly rather than
reporting a repin it cannot observe.

Result
------
A TOON document on stdout, on both paths: one ``entries`` row per plan-marshall
scope entry with its before and after versions and an ``action`` —

- ``report`` — dry run: the row states what an apply would do;
- ``repinned`` — the entry was rewritten and reads the target version;
- ``noop`` — the entry was left alone (already at the target, newer than it, or
  its bundle has no target version directory);
- ``failed`` — the entry should have been repinned and is not at the target.

The last field is ``registry_parity`` — the shared classifier's verdict over the
registry as it stands when the run ends: ``in_parity``, ``behind``, ``ahead`` or
``unreadable``.

Exit code: non-zero when the final verdict is ``behind`` or the run failed.

Constraints on this module
--------------------------
Standard library only, and nothing imported from the ``marketplace.targets``
package: it is run as a standalone file under a bare ``python3``. The
version ordering and the parity verdicts come from
``plan-marshall:script-shared``'s ``plugin_registry`` module, loaded BY FILE
LOCATION. No ``@dataclass`` is defined, because this module is itself loadable
by file location and is then not registered in ``sys.modules``.

Usage:
    python3 marketplace/targets/claude/registry_pin.py
    python3 marketplace/targets/claude/registry_pin.py --apply
    python3 marketplace/targets/claude/registry_pin.py --apply --target-version 0.1.1069
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from typing import Any

#: Repo-relative location of the shared registry reader.
PLUGIN_REGISTRY_RELPATH = (
    Path('marketplace') / 'bundles' / 'plan-marshall' / 'skills' / 'script-shared' / 'scripts' / 'plugin_registry.py'
)

#: Top-level manifest the sync mirrors into the cache root; read for ``source_sha``.
DIST_MANIFEST_FILENAME = 'dist-manifest.json'

DEFAULT_REGISTRY_PATH = Path.home() / '.claude' / 'plugins' / 'installed_plugins.json'

# Row actions (the closed set a result row carries).
ACTION_REPORT = 'report'
ACTION_REPINNED = 'repinned'
ACTION_NOOP = 'noop'
ACTION_FAILED = 'failed'

# Post-write gate outcomes.
GATE_PASSED = 'passed'
GATE_FAILED = 'failed'
GATE_NOT_RUN = 'not_run'

MODE_DRY_RUN = 'dry_run'
MODE_APPLY = 'apply'

#: How an unknown version is rendered in a result row.
UNKNOWN = 'unknown'


class RepinError(Exception):
    """The repin could not be carried out safely and was abandoned."""


def _load_plugin_registry() -> ModuleType:
    """Load the shared registry reader by file location.

    ``marketplace/targets/claude/registry_pin.py`` → the repo root is three
    parents up. The reader is stdlib-only and defines no dataclass, so it needs
    no ``sys.modules`` registration.

    Raises:
        ImportError: the reader file is absent or has no loadable spec.
    """
    reader_path = Path(__file__).resolve().parents[3] / PLUGIN_REGISTRY_RELPATH
    spec = importlib.util.spec_from_file_location('_registry_pin_plugin_registry', reader_path)
    if spec is None or spec.loader is None or not reader_path.is_file():
        raise ImportError(f'shared registry reader not found at {reader_path}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_registry = _load_plugin_registry()

DEFAULT_CACHE_ROOT = Path.home() / '.claude' / 'plugins' / 'cache' / _registry.MARKETPLACE_NAME


# ---------------------------------------------------------------------------
# Planning (pure reads)
# ---------------------------------------------------------------------------


def resolve_references(
    rows: list[dict[str, str | None]], cache_root: Path, target_version: str | None
) -> dict[str, str | None]:
    """Return the reference version per bundle.

    The explicit ``target_version`` when given; otherwise the newest version
    directory of the bundle's cache directory, or ``None`` when it has none.
    """
    references: dict[str, str | None] = {}
    for row in rows:
        bundle = str(row['bundle'])
        if bundle not in references:
            references[bundle] = target_version or _registry.newest_cache_version(cache_root / bundle)
    return references


def needs_repin(row: dict[str, str | None], reference: str | None, cache_root: Path) -> bool:
    """Whether ``row`` is to be rewritten to ``reference``.

    An entry is repinned only when its bundle has the reference version
    directory, it is not already at the reference in both pinned fields, and
    neither pinned field is NEWER than the reference — the repin never moves a
    pin backwards.
    """
    if reference is None or not (cache_root / str(row['bundle']) / reference).is_dir():
        return False
    pinned = (row['install_path_version'], row['version'])
    if all(value == reference for value in pinned):
        return False
    reference_key = _registry.version_key(reference)
    return not any(value is not None and _registry.version_key(value) > reference_key for value in pinned)


def overall_parity(rows: list[dict[str, str | None]], references: dict[str, str | None]) -> str:
    """Classify the whole registry: each bundle against its own reference.

    Every bundle is classified by the shared classifier; the per-bundle
    verdicts are combined in the classifier's own precedence — ``behind``, then
    ``unreadable``, then ``ahead``, then ``in_parity``.
    """
    verdicts = {
        _registry.classify_parity([row for row in rows if row['bundle'] == bundle], reference)
        for bundle, reference in references.items()
    }
    for verdict in (_registry.PARITY_BEHIND, _registry.PARITY_UNREADABLE, _registry.PARITY_AHEAD):
        if verdict in verdicts:
            return str(verdict)
    return str(_registry.PARITY_IN_PARITY) if verdicts else str(_registry.PARITY_UNREADABLE)


def _read_source_sha(cache_root: Path) -> str | None:
    """The ``source_sha`` the cache-root ``dist-manifest.json`` names, or ``None``."""
    try:
        data = json.loads((cache_root / DIST_MANIFEST_FILENAME).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None
    source_sha = data.get('source_sha') if isinstance(data, dict) else None
    return source_sha if isinstance(source_sha, str) and source_sha else None


# ---------------------------------------------------------------------------
# Apply steps (each one module-level, so the order is observable)
# ---------------------------------------------------------------------------


def _refuse_symlinked_registry(registry_path: Path) -> None:
    """Refuse to write a registry whose path is a symbolic link.

    Writing through the link would change a file somewhere else, and the
    atomic ``os.replace`` would not even do that: it replaces the link itself
    with a regular file and leaves the link's target stale. Neither is what
    whoever made the link asked for, so the repin stops instead.

    Raises:
        RepinError: ``registry_path`` is a symbolic link.
    """
    if registry_path.is_symlink():
        raise RepinError(
            f'the registry path {registry_path} is a symbolic link; '
            'the repin neither writes through a link nor replaces one, so nothing was written'
        )


def _refuse_linked_cache_dirs(cache_root: Path, pinned_dirs: dict[str, str]) -> None:
    """Refuse a ``{bundle}/{version}`` in ``pinned_dirs`` that is not a real directory of the cache.

    The marker removal and the ``installPath`` the rewrite records both go
    through ``{cache_root}/{bundle}/{version}``. A bundle or version directory
    that is a symbolic link, or that resolves outside the resolved cache root,
    would carry them out of the cache; a marker that is itself a link would be
    removed as a link someone placed there. The cache ROOT may be a link: it is
    the one location the caller named, and everything is judged relative to
    where it resolves.

    Raises:
        RepinError: a bundle directory, a version directory or a marker is a
            symbolic link, or a directory resolves outside the cache root.
    """
    resolved_root = cache_root.resolve()
    for bundle, version in sorted(pinned_dirs.items()):
        bundle_dir = cache_root / bundle
        version_dir = bundle_dir / version
        for path in (bundle_dir, version_dir, version_dir / _registry.ORPHAN_MARKER_NAME):
            if path.is_symlink():
                raise RepinError(
                    f'the cache path {path} is a symbolic link; '
                    'the repin does not act through a link, so nothing was written or removed'
                )
        for path in (bundle_dir, version_dir):
            resolved = path.resolve()
            if resolved == resolved_root or not resolved.is_relative_to(resolved_root):
                raise RepinError(
                    f'the cache path {path} resolves to {resolved}, outside the cache root {resolved_root}; '
                    'nothing was written or removed'
                )


def _remove_orphan_markers(cache_root: Path, pinned_dirs: dict[str, str]) -> int:
    """Remove ``.orphaned_at`` from each ``{bundle}/{version}`` in ``pinned_dirs``.

    Returns how many markers were removed. Nothing else in the directory is
    touched — in particular no ``.in_use`` file. The caller has already put
    ``pinned_dirs`` through :func:`_refuse_linked_cache_dirs`.
    """
    removed = 0
    for bundle, version in sorted(pinned_dirs.items()):
        marker = cache_root / bundle / version / _registry.ORPHAN_MARKER_NAME
        if marker.exists():
            marker.unlink()
            removed += 1
    return removed


def _backup_registry(registry_path: Path, original: bytes, stamp: str) -> Path:
    """Write ``original`` to a new backup file beside the registry and return its path.

    The backup is created exclusively: an existing file of the same name is
    never overwritten, a numeric suffix is appended instead.
    """
    base = registry_path.with_name(f'{registry_path.name}.repin-backup-{stamp}')
    candidate = base
    attempt = 1
    while True:
        try:
            with candidate.open('xb') as handle:
                handle.write(original)
            return candidate
        except FileExistsError:
            candidate = base.with_name(f'{base.name}-{attempt}')
            attempt += 1


def _replace_registry(registry_path: Path, original: bytes, document: Any) -> None:
    """Atomically replace the registry with ``document``.

    The new document is written to a temp file in the registry's own directory
    and moved into place with ``os.replace``. Immediately before the replace
    the registry is re-read: when its bytes are no longer ``original`` another
    writer got in between the read and now, and the replace is abandoned. So is
    a replace onto a path that has become a symbolic link in the meantime.

    Raises:
        RepinError: the registry changed since it was read, or its path is a
            symbolic link.
    """
    tmp = registry_path.with_name(f'.{registry_path.name}.{os.getpid()}.tmp')
    try:
        tmp.write_text(json.dumps(document, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        shutil.copymode(registry_path, tmp)
        if registry_path.read_bytes() != original:
            raise RepinError('the registry changed while it was being repinned; nothing was replaced')
        _refuse_symlinked_registry(registry_path)
        os.replace(tmp, registry_path)
    finally:
        tmp.unlink(missing_ok=True)


def _utc_stamp(now: datetime) -> str:
    return now.strftime('%Y%m%dT%H%M%SZ')


def _last_updated(now: datetime) -> str:
    return now.isoformat(timespec='milliseconds').replace('+00:00', 'Z')


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def _result_row(row: dict[str, str | None], after: dict[str, str | None], action: str) -> dict[str, str]:
    return {
        'bundle': str(row['bundle']),
        'scope': row['scope'] or UNKNOWN,
        'before_install_path_version': row['install_path_version'] or UNKNOWN,
        'before_version': row['version'] or UNKNOWN,
        'after_install_path_version': after['install_path_version'] or UNKNOWN,
        'after_version': after['version'] or UNKNOWN,
        'action': action,
    }


def _at(reference: str | None) -> dict[str, str | None]:
    return {'install_path_version': reference, 'version': reference}


def repin(
    *,
    registry_path: Path,
    cache_root: Path,
    target_version: str | None = None,
    apply: bool = False,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Report, or with ``apply`` carry out, the repin of the plugin registry.

    Args:
        registry_path: The plugin registry (``installed_plugins.json``).
        cache_root: The plugin-cache root holding ``{bundle}/{version}/`` dirs.
        target_version: The version to pin to; ``None`` pins each bundle to its
            newest cache version directory.
        apply: Write the registry. ``False`` is a dry run that writes nothing.
        now: The current time (injected for determinism).

    Returns:
        The result document as a dict; ``exit_code`` carries the process exit code.
    """
    moment = now or datetime.now(UTC)
    result: dict[str, Any] = {
        'status': 'success',
        'mode': MODE_APPLY if apply else MODE_DRY_RUN,
        'registry_path': str(registry_path),
        'cache_root': str(cache_root),
        'markers_removed': 0,
        'gate': GATE_NOT_RUN,
        'entries': [],
    }

    state, rows = _registry.read_registry(registry_path)
    result['registry_state'] = state
    references = resolve_references(rows, cache_root, target_version)
    plan = [needs_repin(row, references[str(row['bundle'])], cache_root) for row in rows]

    if not apply or not rows:
        result['entries'] = [
            _result_row(row, _at(references[str(row['bundle'])]) if planned else row, ACTION_REPORT)
            for row, planned in zip(rows, plan, strict=True)
        ]
        return _finish(result, overall_parity(rows, references))

    try:
        _apply(result, registry_path, cache_root, rows, references, plan, moment)
    except (OSError, ValueError, RepinError) as exc:
        result['status'] = 'error'
        result['message'] = str(exc)

    # Step 4 — the post-write gate: judge the registry as it now reads on disk.
    _, after_rows = _registry.read_registry(registry_path)
    aligned = len(after_rows) == len(rows)
    gate_failed = False
    for index, (row, planned) in enumerate(zip(rows, plan, strict=True)):
        after = after_rows[index] if aligned else {'install_path_version': None, 'version': None}
        if not planned:
            action = ACTION_NOOP
        elif (after['install_path_version'], after['version']) == (references[str(row['bundle'])],) * 2:
            action = ACTION_REPINNED
        else:
            action = ACTION_FAILED
            gate_failed = True
        result['entries'].append(_result_row(row, after, action))
    result['gate'] = GATE_FAILED if gate_failed or not aligned else GATE_PASSED
    if result['gate'] == GATE_FAILED and result['status'] == 'success':
        result['status'] = 'error'
        result['message'] = 'post-write gate failed: a repinned entry does not read the target version'
    return _finish(result, overall_parity(after_rows, references))


def _apply(
    result: dict[str, Any],
    registry_path: Path,
    cache_root: Path,
    rows: list[dict[str, str | None]],
    references: dict[str, str | None],
    plan: list[bool],
    moment: datetime,
) -> None:
    """Run apply steps 1–3 in order, recording their side effects on ``result``.

    Raises:
        RepinError: the registry changed while it was being read, an entry
            needs a rewrite and the registry path is a symbolic link, or a
            cache directory the run would act in is a link or lies outside
            the cache root.
    """
    original = registry_path.read_bytes()
    document = json.loads(original)
    # The shared reader's own walk, over the document's own dicts: the pairs
    # line up with ``rows`` index for index, and mutating an entry mutates
    # ``document``.
    pairs = list(_registry.iter_marketplace_entries(document))
    if [bundle for bundle, _ in pairs] != [row['bundle'] for row in rows]:
        raise RepinError('the registry changed while it was being read; nothing was written')
    if any(plan):
        # Refused before step 1, so a run that cannot write changes nothing at all.
        _refuse_symlinked_registry(registry_path)

    # Step 1 — un-orphan every directory an entry is pinned to after this run:
    # the ones about to be repinned, and the ones already at their reference.
    pinned_dirs: dict[str, str] = {}
    for row, planned in zip(rows, plan, strict=True):
        reference = references[str(row['bundle'])]
        if reference is not None and (planned or (row['install_path_version'], row['version']) == (reference,) * 2):
            pinned_dirs[str(row['bundle'])] = reference
    # Every directory this run would act in is judged before the first removal,
    # so a refused run leaves the cache and the registry as they were.
    _refuse_linked_cache_dirs(cache_root, pinned_dirs)
    result['markers_removed'] = _remove_orphan_markers(cache_root, pinned_dirs)

    if not any(plan):
        return

    # Step 2 — one backup, before the first byte of the registry changes.
    result['backup_path'] = str(_backup_registry(registry_path, original, _utc_stamp(moment)))

    # Step 3 — rewrite the planned entries and replace the registry atomically.
    source_sha = _read_source_sha(cache_root)
    for (bundle, entry), planned in zip(pairs, plan, strict=True):
        if not planned:
            continue
        reference = str(references[bundle])
        entry['installPath'] = str((cache_root / bundle / reference).resolve())
        entry['version'] = reference
        entry['lastUpdated'] = _last_updated(moment)
        if source_sha is not None:
            entry['gitCommitSha'] = source_sha
    _replace_registry(registry_path, original, document)


def _finish(result: dict[str, Any], parity: str) -> dict[str, Any]:
    """Attach the final verdict and the exit code it implies."""
    result['registry_parity'] = parity
    failed = result['status'] != 'success' or parity == _registry.PARITY_BEHIND
    result['exit_code'] = 1 if failed else 0
    return result


# ---------------------------------------------------------------------------
# Rendering and entry point
# ---------------------------------------------------------------------------

_ENTRY_FIELDS = (
    'bundle',
    'scope',
    'before_install_path_version',
    'before_version',
    'after_install_path_version',
    'after_version',
    'action',
)


def render(result: dict[str, Any]) -> str:
    """Render the result document as TOON, ``registry_parity`` last."""
    lines = [
        f'status: {result["status"]}',
        f'mode: {result["mode"]}',
        f'registry_path: {result["registry_path"]}',
        f'cache_root: {result["cache_root"]}',
        f'registry_state: {result["registry_state"]}',
        f'markers_removed: {result["markers_removed"]}',
        f'gate: {result["gate"]}',
    ]
    if 'backup_path' in result:
        lines.append(f'backup_path: {result["backup_path"]}')
    if 'message' in result:
        message = str(result['message']).replace('"', '\\"')
        lines.append(f'message: "{message}"')
    entries = result['entries']
    lines.append(f'entries[{len(entries)}]{{{",".join(_ENTRY_FIELDS)}}}:')
    for entry in entries:
        lines.append('  ' + ','.join(entry[field] for field in _ENTRY_FIELDS))
    lines.append(f'registry_parity: {result["registry_parity"]}')
    return '\n'.join(lines) + '\n'


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='Repin the plugin registry to the synced plugin-cache version (meta-project-only).',
        allow_abbrev=False,
    )
    parser.add_argument(
        '--apply',
        action='store_true',
        help='Write the registry. Without this flag the run is a dry run and writes nothing.',
    )
    parser.add_argument(
        '--target-version',
        default=None,
        help='Version to pin to (default: the newest cache version directory per bundle).',
    )
    parser.add_argument(
        '--cache-root',
        type=Path,
        default=DEFAULT_CACHE_ROOT,
        help='Plugin-cache root holding {bundle}/{version}/ directories.',
    )
    parser.add_argument(
        '--registry-path',
        type=Path,
        default=DEFAULT_REGISTRY_PATH,
        help='Plugin registry file (installed_plugins.json).',
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point — run one repin (or its dry run) and print the TOON result."""
    args = _build_parser().parse_args(argv if argv is not None else sys.argv[1:])
    result = repin(
        registry_path=args.registry_path,
        cache_root=args.cache_root,
        target_version=args.target_version,
        apply=args.apply,
    )
    sys.stdout.write(render(result))
    return int(result['exit_code'])


if __name__ == '__main__':
    raise SystemExit(main())

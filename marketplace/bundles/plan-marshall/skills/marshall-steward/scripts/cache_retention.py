#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Union-keep plugin-cache retention sweep for the ``upgrade`` verb.

``marshall-steward`` is a hybrid skill: an LLM workflow router
(``references/upgrade-flow.md``) over deterministic scripts. ``upgrade.py`` stays
a pure planner that only NAMES the ``cache-retention-sweep`` sub-step; the
destructive work lives here, behind the ``cache-retention-prune`` nested gate the
planner declares (nested gates are ``integrate``-invariant, so the apply still
prompts).

**The keep-set is a strict UNION, evaluated per bundle.** A version directory is
removed only when NO rule keeps it:

1. the ``N`` numerically-newest version dirs (``N`` =
   ``system.retention.plugin_cache_keep_versions``, default 5),
2. any dir younger than ``D`` days (``D`` =
   ``system.retention.plugin_cache_keep_days``, default 3),
3. the newest-on-disk dir — the version the highest-version-wins resolver
   actually selects,
4. the version named by ``marshal.json``'s ``system.provisioned_version``,
5. the version named by the cache-root ``dist-manifest.json``,
6. the version dir THIS process is executing from (``Path(__file__)``) — the
   script lives inside the cache it prunes, so self-deletion is a real failure
   mode, not a hypothetical.

Rules 3-6 pin **this project only**: the sweep enumerates no other project root
and never reads the build-server registry as a project inventory. The ``N``/``D``
union (rules 1-2) is the accepted cross-project safety margin.

``.orphaned_at`` is **advisory only** and is NEVER consulted as a keep-or-delete
oracle. The marker has saturated in practice (every version dir marked, none
live), so a marker-driven oracle would delete the live version on its first run.

The report distinguishes a silent no-op from a clean run: ``kept`` names the
FIRST keep-rule that fired for every retained dir and ``removed`` names every
removal with its age, so a run that removed nothing still explains why.

Subcommand:
    sweep  Report the keep/remove partition. Dry run by default; ``--apply``
           performs the unlink.

Usage:
    python3 cache_retention.py sweep
    python3 cache_retention.py sweep --apply
    python3 cache_retention.py sweep --cache-root /path/to/plugins/cache/plan-marshall

Output (TOON):
    status: success
    applied: false
    cache_root: /Users/x/.claude/plugins/cache/plan-marshall
    keep_versions: 5
    keep_days: 3
    knob_source: marshal.json
    swept_count: 58
    removed_count: 3
    kept[55]{bundle,version,reason}:
    ...
    removed[3]{bundle,version,age_days}:
    ...
    summary_message: ...

Exit 0 on success, 2 on argparse rejection.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import time
from pathlib import Path

# Bootstrap sys.path — this script may run before the executor sets up
# PYTHONPATH. Step 1: locate script-shared/scripts via an identity walk so the
# shared anchor helper is importable. Step 2: derive the skills root from it.
for _ancestor in Path(__file__).resolve().parents:
    if _ancestor.name == 'skills' and (_ancestor.parent / '.claude-plugin' / 'plugin.json').is_file():
        _shared_scripts = str(_ancestor / 'script-shared' / 'scripts')
        if _shared_scripts not in sys.path:
            sys.path.insert(0, _shared_scripts)
        break

from marketplace_bundles import _version_sort_key, resolve_skills_root  # noqa: E402
from marketplace_paths import get_plugin_cache_path  # noqa: E402

_SKILLS_DIR = resolve_skills_root(Path(__file__))
for _lib in ('ref-toon-format', 'tools-file-ops', 'tools-script-executor'):
    _lib_path = str(_SKILLS_DIR / _lib / 'scripts')
    if _lib_path not in sys.path:
        sys.path.insert(0, _lib_path)

from generate_executor import read_installed_manifest  # noqa: E402

# A cache version directory (``.../plan-marshall/0.1.1180/``).
_VERSION_DIR_RE = re.compile(r'^\d+\.\d+')

# Fallback knob values, applied verbatim when marshal.json is absent or its
# retention block is unreadable. They mirror
# ``manage-config``'s ``DEFAULT_SYSTEM_RETENTION`` seed.
DEFAULT_KEEP_VERSIONS = 5
DEFAULT_KEEP_DAYS = 3

_SECONDS_PER_DAY = 86400.0

# Keep-rule identifiers, in the evaluation order the union is reported with.
KEEP_NEWEST_N = 'newest_n'
KEEP_YOUNGER_THAN_D = 'younger_than_d_days'
KEEP_NEWEST_ON_DISK = 'newest_on_disk'
KEEP_PROVISIONED = 'provisioned_version'
KEEP_MANIFEST = 'manifest_version'
KEEP_SELF = 'executing_version'


def resolve_knobs(project_root: Path | None = None) -> tuple[int, int, str]:
    """Resolve ``(keep_versions, keep_days, source)`` from ``marshal.json``.

    Walks up from ``project_root`` (default: cwd) to the nearest
    ``.plan/marshal.json`` and reads ``system.retention``. Falls back to the
    ``5``/``3`` defaults — with a ``defaults`` source annotation — when the file
    is absent, unreadable, or the block carries no usable value, so a surprising
    keep-set is always diagnosable from the report.

    Args:
        project_root: Directory to start the upward walk from.

    Returns:
        ``(keep_versions, keep_days, source)`` where ``source`` is
        ``marshal.json`` or ``defaults``.
    """
    start = (project_root or Path.cwd()).resolve()
    for parent in (start, *start.parents):
        candidate = parent / '.plan' / 'marshal.json'
        if not candidate.is_file():
            continue
        try:
            data = json.loads(candidate.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            return DEFAULT_KEEP_VERSIONS, DEFAULT_KEEP_DAYS, 'defaults'
        retention = {}
        if isinstance(data, dict):
            system = data.get('system')
            if isinstance(system, dict) and isinstance(system.get('retention'), dict):
                retention = system['retention']
        keep_versions = retention.get('plugin_cache_keep_versions')
        keep_days = retention.get('plugin_cache_keep_days')
        resolved_versions = (
            keep_versions
            if isinstance(keep_versions, int) and not isinstance(keep_versions, bool)
            else DEFAULT_KEEP_VERSIONS
        )
        resolved_days = (
            keep_days if isinstance(keep_days, int) and not isinstance(keep_days, bool) else DEFAULT_KEEP_DAYS
        )
        return resolved_versions, resolved_days, str(candidate)
    return DEFAULT_KEEP_VERSIONS, DEFAULT_KEEP_DAYS, 'defaults'


def read_provisioned_version(project_root: Path | None = None) -> str:
    """Read ``system.provisioned_version`` from the nearest ``marshal.json``.

    Returns ``''`` when the file, the ``system`` block, or the field is absent.
    """
    start = (project_root or Path.cwd()).resolve()
    for parent in (start, *start.parents):
        candidate = parent / '.plan' / 'marshal.json'
        if not candidate.is_file():
            continue
        try:
            data = json.loads(candidate.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            return ''
        if isinstance(data, dict):
            system = data.get('system')
            if isinstance(system, dict):
                value = system.get('provisioned_version')
                if isinstance(value, str):
                    return value
        return ''
    return ''


def _version_dirs(bundle_dir: Path) -> list[Path]:
    """Return ``bundle_dir``'s version subdirectories (unfiltered by marker)."""
    try:
        children = list(bundle_dir.iterdir())
    except OSError:
        return []
    return [c for c in children if c.is_dir() and _VERSION_DIR_RE.match(c.name)]


def _age_days(path: Path, now: float) -> float:
    """Return ``path``'s age in days from its mtime (``0.0`` when unreadable)."""
    try:
        return max(0.0, (now - path.stat().st_mtime) / _SECONDS_PER_DAY)
    except OSError:
        return 0.0


def _executing_version_dir() -> Path | None:
    """Return the version dir this process executes from, or ``None``.

    The sweep runs from inside the very cache tree it prunes, so the executing
    version dir must be pinned unconditionally — self-deletion would remove the
    running script's own bundle.
    """
    here = Path(__file__).resolve()
    for ancestor in here.parents:
        if _VERSION_DIR_RE.match(ancestor.name):
            return ancestor
    return None


def _keep_reason(
    version_dir: Path,
    newest_n: set[str],
    keep_days: int,
    now: float,
    newest_on_disk: str,
    provisioned_version: str,
    manifest_version: str,
    executing_dir: Path | None,
) -> str | None:
    """Return the FIRST keep-rule that fires for ``version_dir``, else ``None``.

    The rules are independent and the keep-set is their UNION — no single rule's
    failure can cause a removal another rule keeps. ``.orphaned_at`` is never
    consulted.
    """
    name = version_dir.name
    if name in newest_n:
        return KEEP_NEWEST_N
    if _age_days(version_dir, now) < keep_days:
        return KEEP_YOUNGER_THAN_D
    if name == newest_on_disk:
        return KEEP_NEWEST_ON_DISK
    if provisioned_version and name == provisioned_version:
        return KEEP_PROVISIONED
    if manifest_version and name == manifest_version:
        return KEEP_MANIFEST
    if executing_dir is not None and version_dir.resolve() == executing_dir:
        return KEEP_SELF
    return None


def sweep(
    cache_root: Path | None,
    apply_changes: bool = False,
    project_root: Path | None = None,
) -> dict:
    """Compute (and optionally apply) the union-keep retention partition.

    Args:
        cache_root: Explicit plugin-cache root, or ``None`` to resolve it via the
            shared deployed-bundle cache resolver.
        apply_changes: When True, unlink every version dir no rule keeps. The
            default dry run mutates nothing.
        project_root: Directory to resolve ``marshal.json`` knobs and the
            provisioned version from. Defaults to cwd.

    Returns:
        The report dict — resolved knobs plus their source, the ``kept`` rows
        (each naming the first keep-rule that fired), the ``removed`` rows, and
        the aggregate counts.
    """
    if cache_root is None:
        cache_root = get_plugin_cache_path()
    keep_versions, keep_days, knob_source = resolve_knobs(project_root)
    if cache_root is None or not cache_root.is_dir():
        return {
            'status': 'error',
            'error': 'cache_root_unresolvable',
            'applied': False,
            'cache_root': str(cache_root) if cache_root is not None else '',
            'keep_versions': keep_versions,
            'keep_days': keep_days,
            'knob_source': knob_source,
            'swept_count': 0,
            'removed_count': 0,
            'kept': [],
            'removed': [],
            'summary_message': 'plugin-cache root could not be resolved; nothing was swept',
        }

    manifest_version = str(read_installed_manifest(cache_root).get('version', '') or '')
    provisioned_version = read_provisioned_version(project_root)
    executing_dir = _executing_version_dir()
    now = time.time()

    kept: list[dict] = []
    removed: list[dict] = []
    swept_count = 0

    bundle_dirs = sorted(d for d in cache_root.iterdir() if d.is_dir() and not d.name.startswith('.'))
    for bundle_dir in bundle_dirs:
        version_dirs = _version_dirs(bundle_dir)
        if not version_dirs:
            continue
        ordered = sorted(version_dirs, key=lambda d: _version_sort_key(d.name), reverse=True)
        newest_n = {d.name for d in ordered[:keep_versions]} if keep_versions > 0 else set()
        newest_on_disk = ordered[0].name
        for version_dir in ordered:
            swept_count += 1
            reason = _keep_reason(
                version_dir,
                newest_n,
                keep_days,
                now,
                newest_on_disk,
                provisioned_version,
                manifest_version,
                executing_dir,
            )
            if reason is not None:
                kept.append({'bundle': bundle_dir.name, 'version': version_dir.name, 'reason': reason})
                continue
            removed.append(
                {
                    'bundle': bundle_dir.name,
                    'version': version_dir.name,
                    'age_days': round(_age_days(version_dir, now), 2),
                }
            )
            if apply_changes:
                shutil.rmtree(version_dir, ignore_errors=True)

    verb = 'removed' if apply_changes else 'would remove'
    summary = (
        f'swept {swept_count} version dir(s) across {len(bundle_dirs)} bundle(s): '
        f'kept {len(kept)}, {verb} {len(removed)} '
        f'(keep_versions={keep_versions}, keep_days={keep_days}, source={knob_source})'
    )
    return {
        'status': 'success',
        'applied': apply_changes,
        'cache_root': str(cache_root),
        'keep_versions': keep_versions,
        'keep_days': keep_days,
        'knob_source': knob_source,
        'swept_count': swept_count,
        'removed_count': len(removed),
        'kept': kept,
        'removed': removed,
        'summary_message': summary,
    }


def cmd_sweep(args: argparse.Namespace) -> dict:
    """Handle the ``sweep`` subcommand."""
    cache_root = Path(args.cache_root).expanduser() if args.cache_root else None
    project_root = Path(args.project_root).expanduser() if args.project_root else None
    return sweep(cache_root, apply_changes=args.apply, project_root=project_root)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog='cache_retention',
        description='Union-keep plugin-cache retention sweep (dry run by default).',
        allow_abbrev=False,
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    sweep_parser = subparsers.add_parser(
        'sweep',
        help='Report the union-keep partition over the plugin cache. Dry run unless --apply.',
        allow_abbrev=False,
    )
    sweep_parser.add_argument(
        '--apply',
        action='store_true',
        help='Perform the unlink. Without this flag the sweep is a read-only dry run.',
    )
    sweep_parser.add_argument(
        '--cache-root',
        type=str,
        default=None,
        help=(
            'Explicit plugin-cache root to sweep. Defaults to the resolved '
            'deployed-bundle cache root for the active runtime target.'
        ),
    )
    sweep_parser.add_argument(
        '--project-root',
        type=str,
        default=None,
        help='Directory to resolve marshal.json retention knobs from. Defaults to the cwd.',
    )

    args = parser.parse_args(argv)

    if args.command == 'sweep':
        result = cmd_sweep(args)
    else:  # pragma: no cover - argparse enforces a valid subcommand
        parser.print_help()
        return 2

    from toon_parser import serialize_toon

    print(serialize_toon(result))
    return 0


if __name__ == '__main__':
    sys.exit(main())

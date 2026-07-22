#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Fail-closed plugin-cache freshness verdict emitter for the ``upgrade`` verb.

``marshall-steward`` is a hybrid skill: an LLM workflow router
(``references/upgrade-flow.md``) over deterministic decision-emitter scripts
(``determine_mode``, ``upgrade``). This script extends that model with the
consumer upgrade flow's cache-freshness gate — it emits a verdict and mutates
nothing.

The gate answers the one question ``generate_executor preflight`` structurally
cannot: **is the installed plugin cache current with the marketplace clone?**
Preflight compares the executor's stamp against a *local* manifest, so a cache
that is twenty versions behind upstream still reports ``fresh`` (executor and
cache agree with each other). This verb instead compares the two local surfaces
that genuinely diverge when a consumer never refreshed:

* the newest version dir under the plugin-cache root, and
* the ``version`` recorded in the marketplace-clone-root ``dist-manifest.json``,
  resolved by reusing the executor generator's manifest-resolution order
  (imported from ``generate_executor``, never re-implemented here).

The verdict is three-valued per ADR-009 and **never vacuously ``fresh``**:

* ``fresh``   — cache version >= clone-root manifest version.
* ``stale``   — cache version < clone-root manifest version.
* ``unknown`` — the cache root or the clone-root manifest could not be
  resolved, so no verdict can be substantiated.

``stale`` and ``unknown`` are distinct verdicts (a caller can tell "you are
behind" from "I cannot tell"), but BOTH set ``refuses_upgrade: true`` and both
name the exact operator commands to run. ``unknown`` is terminal: there is no
age-based, mtime-based, or otherwise-inferred fallback that downgrades it to a
guessed ``fresh``/``stale``. The verdict set is exactly these three values.

Subcommand:
    check  Emit the freshness verdict. ``--cache-root`` optionally overrides the
           resolved plugin-cache root (tests / alternate installs).

Usage:
    python3 cache_freshness.py check
    python3 cache_freshness.py check --cache-root /path/to/plugins/cache/plan-marshall

Output (TOON):
    status: success
    freshness: stale
    refuses_upgrade: true
    cache_version: 0.1.1180
    manifest_version: 0.1.1195
    cache_root: /Users/x/.claude/plugins/cache/plan-marshall
    manifest_path: /Users/x/.claude/plugins/marketplaces/plan-marshall/dist-manifest.json
    remediation: Run '/plugin marketplace update', then reinstall the plugin ...
    warning:

Exit 0 on success, 2 on argparse rejection.
"""

from __future__ import annotations

import argparse
import re
import sys
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

# The PLAN-08 manifest-resolution order, imported rather than re-implemented.
from generate_executor import (  # noqa: E402
    _version_tuple,
    find_installed_manifest_path,
    read_installed_manifest,
)

# A cache version directory (``.../plan-marshall/0.1.1180/``).
_VERSION_DIR_RE = re.compile(r'^\d+\.\d+')

# The remediation names the operator commands verbatim rather than describing
# them. It is a module constant so every refusing branch emits the identical
# string and a test can assert the literal commands.
REMEDIATION = (
    "Run '/plugin marketplace update' to refresh the marketplace clone, then reinstall the plugin "
    "('/plugin uninstall plan-marshall' followed by '/plugin install plan-marshall')."
)

FRESH = 'fresh'
STALE = 'stale'
UNKNOWN = 'unknown'


def newest_cache_version(cache_root: Path) -> str:
    """Return the newest version-dir name under ``cache_root``, or ``''``.

    The plugin cache is laid out as ``<cache_root>/<bundle>/<version>/``. Every
    bundle is versioned in lock-step by the target generator, so the newest
    version dir across all bundles IS the installed cache version. Ordering uses
    ``_version_sort_key`` — the same numeric tuple sort the bundle resolver uses
    — so ``0.1.9`` never shadows ``0.1.10``.

    Args:
        cache_root: The plugin-cache root directory.

    Returns:
        The newest version directory name, or ``''`` when the root carries none.
    """
    version_dirs: list[str] = []
    try:
        bundle_dirs = [d for d in cache_root.iterdir() if d.is_dir() and not d.name.startswith('.')]
    except OSError:
        return ''
    for bundle_dir in bundle_dirs:
        try:
            children = list(bundle_dir.iterdir())
        except OSError:
            continue
        version_dirs.extend(
            child.name for child in children if child.is_dir() and _VERSION_DIR_RE.match(child.name)
        )
    if not version_dirs:
        return ''
    return max(version_dirs, key=_version_sort_key)


def _unknown(reason: str, cache_root: Path | None, cache_version: str) -> dict:
    """Build the ``unknown`` verdict — refusing, never downgraded to a guess."""
    return {
        'status': 'success',
        'freshness': UNKNOWN,
        'refuses_upgrade': True,
        'cache_version': cache_version or UNKNOWN,
        'manifest_version': UNKNOWN,
        'cache_root': str(cache_root) if cache_root is not None else '',
        'manifest_path': '',
        'remediation': REMEDIATION,
        'warning': reason,
    }


def check_freshness(cache_root: Path | None) -> dict:
    """Compute the three-valued freshness verdict. Read-only; mutates nothing.

    Args:
        cache_root: Explicit plugin-cache root, or ``None`` to resolve it via
            the shared deployed-bundle cache resolver.

    Returns:
        The verdict dict — ``freshness`` is exactly one of ``fresh``, ``stale``,
        ``unknown``; ``refuses_upgrade`` is ``False`` only on ``fresh``.
    """
    if cache_root is None:
        cache_root = get_plugin_cache_path()
    if cache_root is None or not cache_root.is_dir():
        return _unknown(
            'plugin-cache root could not be resolved; cache freshness cannot be substantiated',
            cache_root,
            '',
        )

    cache_version = newest_cache_version(cache_root)
    if not cache_version:
        return _unknown(
            f'no version directory found under the plugin-cache root {cache_root}; '
            'cache freshness cannot be substantiated',
            cache_root,
            '',
        )

    manifest_path = find_installed_manifest_path(cache_root)
    manifest = read_installed_manifest(cache_root)
    manifest_version = str(manifest.get('version', '') or '')
    if manifest_path is None or not manifest_version:
        return _unknown(
            'marketplace-clone-root dist-manifest.json could not be resolved; '
            'cache freshness cannot be substantiated',
            cache_root,
            cache_version,
        )

    is_fresh = _version_tuple(cache_version) >= _version_tuple(manifest_version)
    return {
        'status': 'success',
        'freshness': FRESH if is_fresh else STALE,
        'refuses_upgrade': not is_fresh,
        'cache_version': cache_version,
        'manifest_version': manifest_version,
        'cache_root': str(cache_root),
        'manifest_path': str(manifest_path),
        'remediation': '' if is_fresh else REMEDIATION,
        'warning': '',
    }


def cmd_check(args: argparse.Namespace) -> dict:
    """Handle the ``check`` subcommand."""
    cache_root = Path(args.cache_root).expanduser() if args.cache_root else None
    return check_freshness(cache_root)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog='cache_freshness',
        description=(
            'Emit the fail-closed three-valued plugin-cache freshness verdict '
            '(fresh|stale|unknown) for the consumer upgrade flow.'
        ),
        allow_abbrev=False,
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    check_parser = subparsers.add_parser(
        'check',
        help='Emit the fresh|stale|unknown cache-freshness verdict. Read-only.',
        allow_abbrev=False,
    )
    check_parser.add_argument(
        '--cache-root',
        type=str,
        default=None,
        help=(
            'Explicit plugin-cache root to inspect. Defaults to the resolved '
            'deployed-bundle cache root for the active runtime target.'
        ),
    )

    args = parser.parse_args(argv)

    if args.command == 'check':
        result = cmd_check(args)
    else:  # pragma: no cover - argparse enforces a valid subcommand
        parser.print_help()
        return 2

    from toon_parser import serialize_toon

    print(serialize_toon(result))
    return 0


if __name__ == '__main__':
    sys.exit(main())

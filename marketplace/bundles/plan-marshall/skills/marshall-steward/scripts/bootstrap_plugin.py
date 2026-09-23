#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""
Bootstrap script for detecting and caching the plugin root path.

This script solves the chicken-and-egg problem of locating plugin scripts
before the executor is available. It detects the plugin installation path
and caches it in marshall-state.toon (inside the per-project plan-marshall
base directory) for subsequent use.

Note: The state file is separate from manage-config's marshal.json —
bootstrap state is needed before the executor/config system is available,
so it uses its own lightweight caching mechanism.

Usage:
    python3 bootstrap_plugin.py get-root [--target claude|opencode|antigravity] [--refresh]
    python3 bootstrap_plugin.py resolve --bundle <bundle> --path <path>

Subcommands:
    get-root              Return the plugin root path (detects if needed)
    resolve               Resolve a path relative to a bundle

Output (TOON format):
    get-root:
        plugin_root	/Users/user/.claude/plugins/cache/plan-marshall
        source	cached|detected
        target	claude|opencode|antigravity

    resolve:
        resolved_path	/Users/user/.claude/plugins/cache/plan-marshall/plan-marshall/1.0.0/skills/...

Environment:
    PLAN_BASE_DIR   Override the plan-marshall base directory (for testing)
    OPENCODE_CONFIG_DIR   Override the OpenCode config directory (for opencode target)
"""

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

# Bootstrap sys.path — this script runs before the executor sets up PYTHONPATH.
# Step 1: locate script-shared/scripts via identity walk so we can import the
# shared anchor helper. Step 2: use resolve_skills_root to derive _SKILLS_DIR.
for _ancestor in Path(__file__).resolve().parents:
    if _ancestor.name in ('skills', 'skill') and (
        (_ancestor.parent / '.claude-plugin' / 'plugin.json').is_file()
        or (_ancestor.parent / 'plugin.json').is_file()
        or (_ancestor.parent / 'opencode.json').is_file()
    ):
        for _cand_name in ('script-shared', 'plan-marshall-script-shared'):
            _shared_scripts = _ancestor / _cand_name / 'scripts'
            if _shared_scripts.is_dir():
                if str(_shared_scripts) not in sys.path:
                    sys.path.insert(0, str(_shared_scripts))
                break
        break

from marketplace_bundles import _version_sort_key, resolve_skills_root  # noqa: E402

_SKILLS_DIR = resolve_skills_root(Path(__file__))
for _lib in ('ref-toon-format', 'tools-file-ops'):
    _lib_path = _SKILLS_DIR / _lib / 'scripts'
    if not _lib_path.is_dir():
        _lib_path = _SKILLS_DIR / f'plan-marshall-{_lib}' / 'scripts'
    if _lib_path.is_dir() and str(_lib_path) not in sys.path:
        sys.path.insert(0, str(_lib_path))

from file_ops import get_base_dir, output_toon, safe_main  # noqa: E402

# Shared path resolution (from script-shared). The layout ops are the single
# source of target-resolved roots; this script consumes them rather than
# re-enumerating per-target paths.
from marketplace_paths import (  # noqa: E402
    _resolve_skill_root,
    get_bundle_cache_roots,
    get_project_skill_roots,
)

# Default plugin name to search for
PLUGIN_NAME = 'plan-marshall'

# Marker file that uniquely identifies our plugin
MARKER_FILE = '.claude-plugin/plugin.json'

# State file name
STATE_FILE = 'marshall-state.toon'


def get_state_file() -> Path:
    """Get the state file path inside the plan-marshall base directory."""
    return get_base_dir() / STATE_FILE


def read_state() -> dict[str, str]:
    """Read the state file if it exists."""
    state_file = get_state_file()
    if not state_file.exists():
        return {}

    state = {}
    for line in state_file.read_text().splitlines():
        if '\t' in line:
            key, value = line.split('\t', 1)
            state[key.strip()] = value.strip()
    return state


def write_state(state: dict[str, str]) -> None:
    """Write state to the state file."""
    state_file = get_state_file()
    state_file.parent.mkdir(parents=True, exist_ok=True)

    lines = [f'{key}\t{value}' for key, value in state.items()]
    state_file.write_text('\n'.join(lines) + '\n')


def read_runtime_target(cwd: str | None = None) -> str:
    """Read ``runtime.target`` from platform env vars or ``.plan/marshal.json``.

    Resolution cascade:

    1. **Env signal** — ``ANTIGRAVITY_AGENT`` → ``'antigravity'``,
       ``OPENCODE`` / ``OPENCODE_PID`` → ``'opencode'``,
       ``CLAUDE_CODE_SESSION_ID`` → ``'claude'``.
    2. **Config** — ``runtime.target`` from the nearest ``.plan/marshal.json``.
    3. **Default** — ``'claude'``.
    """
    import json as _json
    import os as _os

    # Tier 1: platform-injected env var (zero-cost, always present).
    if _os.environ.get('ANTIGRAVITY_AGENT'):
        return 'antigravity'
    if _os.environ.get('OPENCODE') or _os.environ.get('OPENCODE_PID'):
        return 'opencode'
    if _os.environ.get('CLAUDE_CODE_SESSION_ID'):
        return 'claude'

    # Tier 2: marshal.json config.
    start = Path(cwd).resolve() if cwd else Path.cwd().resolve()
    for parent in [start, *start.parents]:
        candidate = parent / '.plan' / 'marshal.json'
        if candidate.is_file():
            try:
                data = _json.loads(candidate.read_text(encoding='utf-8'))
                if isinstance(data, dict):
                    runtime = data.get('runtime')
                    if isinstance(runtime, dict):
                        target = runtime.get('target')
                        if isinstance(target, str) and target:
                            return target
            except (OSError, ValueError):
                pass
            return 'claude'
    return 'claude'


def detect_plugin_root(target: str | None = None) -> Path | None:
    """
    Detect the plugin root for the given target.

    For ``claude``: searches in ``~/.claude/plugins/cache/`` for
    directories containing a bundle with our marker file.

    For ``opencode``: walks the runtime-resolved project-local skill
    roots (``get_project_skill_roots`` — the platform-runtime ``layout
    skill-roots`` op) in priority order, returning the first root that
    contains at least one ``{PLUGIN_NAME}-*`` skill directory.

    For ``antigravity``: checks workspace-local (.agents/plugins/plan-marshall)
    and global (~/.gemini/config/plugins/plan-marshall) plugin directories.

    When ``target`` is ``None``, auto-detects via the env → config → default
    cascade in ``read_runtime_target()``.  If that auto-detected target
    resolves to ``claude`` and the primary Claude detector misses, a fallback
    probe tries the remaining detectors. An explicitly passed ``target``
    (including an explicit ``"claude"``) never falls back — the caller asked
    for a specific runtime and a different one's root must not be returned
    in its place.

    Args:
        target: Runtime target (``"claude"``, ``"opencode"``, or ``"antigravity"``).

    Returns:
        Path to plugin root, or ``None`` if not found.
    """
    auto_detected = target is None
    if target is None:
        target = read_runtime_target()

    if target == 'opencode':
        return _detect_opencode_root()
    if target == 'antigravity':
        return _detect_antigravity_root()

    # Primary: Claude detection.
    result = _detect_claude_root()
    if result:
        return result

    if not auto_detected:
        return None

    # Tier 3 fallback (auto-detected target only): probe other targets if
    # Claude root not found.
    return _detect_antigravity_root() or _detect_opencode_root()


def _detect_antigravity_root() -> Path | None:
    """Detect the plugin root in Antigravity locations.

    Probes workspace-local (<cwd>/.agents/plugins/plan-marshall) first,
    then global (~/.gemini/config/plugins/plan-marshall).
    """
    import os

    workspace_plugin = Path.cwd() / '.agents' / 'plugins' / PLUGIN_NAME
    if workspace_plugin.is_dir() and (
        (workspace_plugin / 'plugin.json').is_file() or (workspace_plugin / 'skills').is_dir()
    ):
        return workspace_plugin

    gemini_config = os.environ.get('GEMINI_CONFIG_DIR')
    global_base = Path(gemini_config).expanduser().resolve() if gemini_config else Path.home() / '.gemini' / 'config'
    global_plugin = global_base / 'plugins' / PLUGIN_NAME
    if global_plugin.is_dir() and ((global_plugin / 'plugin.json').is_file() or (global_plugin / 'skills').is_dir()):
        return global_plugin

    return None


def _detect_claude_root() -> Path | None:
    """Detect the plugin root in the Claude plugin cache.

    The cache base is derived from the runtime-resolved bundle-cache root
    (``get_bundle_cache_roots``) rather than a hardcoded ``~/.claude`` literal:
    the plugin-cache base is the parent of the plan-marshall cache root in the
    single-bundle install layout ``{base}/{plugin}/{bundle}/{version}/…``.
    """
    roots = get_bundle_cache_roots()
    if not roots:
        return None
    cache_base = Path(roots[0]).expanduser().parent

    if not cache_base.exists():
        return None

    for plugin_dir in cache_base.iterdir():
        if not plugin_dir.is_dir():
            continue

        for bundle_dir in plugin_dir.iterdir():
            if not bundle_dir.is_dir():
                continue

            for version_dir in bundle_dir.iterdir():
                if not version_dir.is_dir():
                    continue

                marker_path = version_dir / MARKER_FILE
                if marker_path.exists():
                    return plugin_dir

    return None


def _detect_opencode_root() -> Path | None:
    """Walk OpenCode skill roots for plan-marshall skills.

    Checks both project-local skill roots (``get_project_skill_roots``) and
    user-global discovery roots (``get_bundle_cache_roots``). Returns the
    first root that contains at least one directory matching
    ``{PLUGIN_NAME}-*``.
    """
    marker_prefix = f'{PLUGIN_NAME}-'

    base = Path.cwd()
    all_roots: list[str] = list(get_project_skill_roots())
    for r in get_bundle_cache_roots():
        if r not in all_roots:
            all_roots.append(r)

    for root in all_roots:
        try:
            root_path = _resolve_skill_root(root, base).resolve()
            if not root_path.is_dir():
                continue
            for entry in root_path.iterdir():
                if entry.is_dir() and entry.name.startswith(marker_prefix):
                    return root_path
        except (OSError, ValueError):
            continue

    return None


def get_plugin_root(refresh: bool = False, target: str | None = None) -> tuple[Path | None, str]:
    """
    Get the plugin root, using cache if available.

    Args:
        refresh: Force re-detection even if cached
        target: Runtime target (``"claude"``, ``"opencode"``, or ``"antigravity"``).
            When ``None``, auto-detects from ``marshal.json``.

    Returns:
        Tuple of (plugin_root_path, source) where source is ``'cached'``,
        ``'detected'``, or ``'not_found'``.
    """
    if target is None:
        target = read_runtime_target()

    if not refresh:
        state = read_state()
        cached_target = state.get('target')
        if 'plugin_root' in state and (cached_target == target or (cached_target is None and target == 'claude')):
            cached_path = Path(state['plugin_root'])
            # Verify it still exists
            if cached_path.exists():
                return cached_path, 'cached'

    # Detect plugin root
    plugin_root = detect_plugin_root(target=target)
    if plugin_root:
        # Cache for future use
        state = read_state()
        state['plugin_root'] = str(plugin_root)
        state['target'] = target
        state['detected_at'] = datetime.now(UTC).isoformat()
        write_state(state)
        return plugin_root, 'detected'

    return None, 'not_found'


def resolve_bundle_path(plugin_root: Path, bundle: str, relative_path: str) -> Path | None:
    """
    Resolve a path relative to a bundle.

    Args:
        plugin_root: The plugin root directory
        bundle: Bundle name (e.g., 'plan-marshall')
        relative_path: Path relative to bundle root (e.g., 'skills/manage-tasks/SKILL.md')

    Returns:
        Resolved absolute path, or None if not found
    """
    bundle_dir = plugin_root / bundle

    if not bundle_dir.exists():
        # Handle Antigravity flat plugin layout (plugin_root / skills / {bundle}-{skill} / ...)
        if (plugin_root / 'plugin.json').is_file():
            if relative_path.startswith('skills/'):
                parts = relative_path.split('/', 2)
                if len(parts) >= 2:
                    skill_name = parts[1]
                    rest = parts[2] if len(parts) > 2 else ''
                    cand = plugin_root / 'skills' / f'{bundle}-{skill_name}'
                    if rest:
                        cand = cand / rest
                    if cand.exists():
                        return cand
            elif (plugin_root / relative_path).exists():
                return plugin_root / relative_path

        # Handle OpenCode singular layout (plugin_root / skill / {bundle}-{skill} / ...)
        if (plugin_root / 'opencode.json').is_file() or (plugin_root / 'skill').is_dir():
            if relative_path.startswith('skills/'):
                parts = relative_path.split('/', 2)
                if len(parts) >= 2:
                    skill_name = parts[1]
                    rest = parts[2] if len(parts) > 2 else ''
                    cand = plugin_root / 'skill' / f'{bundle}-{skill_name}'
                    if rest:
                        cand = cand / rest
                    if cand.exists():
                        return cand
            elif (plugin_root / relative_path).exists():
                return plugin_root / relative_path

        return None

    # Select the NEWEST versioned directory that carries relative_path. The old
    # iterdir loop returned the lexically-first match, letting an older version
    # (e.g. '1.0.0') shadow the current one ('1.0.10'); mirror the newest-version
    # selection collect_script_dirs already uses via _version_sort_key.
    candidates = [
        version_dir
        for version_dir in bundle_dir.iterdir()
        if version_dir.is_dir() and (version_dir / relative_path).exists()
    ]
    if candidates:
        newest = max(candidates, key=lambda d: _version_sort_key(d.name))
        return newest / relative_path

    if (bundle_dir / relative_path).exists():
        return bundle_dir / relative_path

    return None


def cmd_get_root(args: argparse.Namespace) -> dict:
    """Handle the 'get-root' subcommand."""
    plugin_root, source = get_plugin_root(refresh=args.refresh, target=args.target)

    if plugin_root:
        return {
            'status': 'success',
            'plugin_root': str(plugin_root),
            'source': source,
            'target': args.target or read_runtime_target(),
        }
    else:
        target_hint = args.target or read_runtime_target()
        if target_hint == 'claude':
            hint = 'Ensure plan-marshall plugin is installed via Claude Code'
        elif target_hint == 'antigravity':
            hint = 'Ensure plan-marshall plugin is installed in ~/.gemini/config/plugins/plan-marshall or .agents/plugins/plan-marshall'
        else:
            hint = 'Ensure plan-marshall skills are deployed to an OpenCode discovery root'
        return {
            'status': 'error',
            'error': 'Plugin root not found',
            'target': target_hint,
            'hint': hint,
        }


def cmd_resolve(args: argparse.Namespace) -> dict:
    """Handle the 'resolve' subcommand."""
    target = getattr(args, 'target', None)
    if target is not None:
        plugin_root, _ = get_plugin_root(target=target)
    else:
        plugin_root, _ = get_plugin_root()

    if not plugin_root:
        return {'status': 'error', 'error': 'Plugin root not found'}

    resolved = resolve_bundle_path(plugin_root, args.bundle, args.path)

    if resolved:
        return {'status': 'success', 'resolved_path': str(resolved)}
    else:
        return {'status': 'error', 'error': f'Path not found: {args.bundle}/{args.path}'}


@safe_main
def main() -> int:
    parser = argparse.ArgumentParser(description='Bootstrap script for plugin root detection', allow_abbrev=False)
    parser.add_argument(
        '--target',
        choices=('claude', 'opencode', 'antigravity'),
        default=None,
        help=(
            'Runtime target. Auto-detected from .plan/marshal.json when omitted. '
            'Use "opencode" for OpenCode discovery roots, or "antigravity" for Antigravity roots.'
        ),
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    # get-root subcommand
    root_parser = subparsers.add_parser('get-root', help='Get the plugin root path', allow_abbrev=False)
    root_parser.add_argument('--refresh', action='store_true', help='Force re-detection even if cached')
    root_parser.add_argument(
        '--target',
        choices=('claude', 'opencode', 'antigravity'),
        default=argparse.SUPPRESS,
        help='Runtime target override',
    )

    # resolve subcommand
    resolve_parser = subparsers.add_parser('resolve', help='Resolve a path relative to a bundle', allow_abbrev=False)
    resolve_parser.add_argument('--bundle', required=True, help="Bundle name (e.g., 'plan-marshall')")
    resolve_parser.add_argument('--path', required=True, help='Path relative to bundle root')
    resolve_parser.add_argument(
        '--target',
        choices=('claude', 'opencode', 'antigravity'),
        default=argparse.SUPPRESS,
        help='Runtime target override',
    )

    args = parser.parse_args()

    if args.command == 'get-root':
        result = cmd_get_root(args)
    elif args.command == 'resolve':
        result = cmd_resolve(args)
    else:
        parser.print_help()
        return 0

    output_toon(result)
    return 0


if __name__ == '__main__':
    main()

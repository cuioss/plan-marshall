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
    python3 bootstrap_plugin.py get-root [--target claude|opencode] [--refresh]
    python3 bootstrap_plugin.py resolve --bundle <bundle> --path <path>

Subcommands:
    get-root              Return the plugin root path (detects if needed)
    resolve               Resolve a path relative to a bundle

Output (TOON format):
    get-root:
        plugin_root	/Users/user/.claude/plugins/cache/plan-marshall
        source	cached|detected
        target	claude|opencode

    resolve:
        resolved_path	/Users/user/.claude/plugins/cache/plan-marshall/plan-marshall/1.0.0/skills/...

Environment:
    PLAN_BASE_DIR   Override the plan-marshall base directory (for testing)
    OPENCODE_CONFIG_DIR   Override the OpenCode config directory (for opencode target)
"""

import argparse
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

# Bootstrap sys.path — this script runs before the executor sets up PYTHONPATH.
# Step 1: locate script-shared/scripts via identity walk so we can import the
# shared anchor helper. Step 2: use resolve_skills_root to derive _SKILLS_DIR.
for _ancestor in Path(__file__).resolve().parents:
    if _ancestor.name == 'skills' and (_ancestor.parent / '.claude-plugin' / 'plugin.json').is_file():
        _shared_scripts = str(_ancestor / 'script-shared' / 'scripts')
        if _shared_scripts not in sys.path:
            sys.path.insert(0, _shared_scripts)
        break

from marketplace_bundles import resolve_skills_root  # type: ignore[import-not-found]  # noqa: E402

_SKILLS_DIR = resolve_skills_root(Path(__file__))
for _lib in ('ref-toon-format', 'tools-file-ops'):
    _lib_path = str(_SKILLS_DIR / _lib / 'scripts')
    if _lib_path not in sys.path:
        sys.path.insert(0, _lib_path)

from file_ops import get_base_dir, output_toon, safe_main  # type: ignore[import-not-found]  # noqa: E402

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
    """Read ``runtime.target`` from the nearest ``.plan/marshal.json``.

    Walks up from ``cwd`` (or ``Path.cwd()``) to find the nearest
    ``.plan/marshal.json``, then extracts ``runtime.target``.

    Returns:
        Target string (``"claude"`` or ``"opencode"``), or ``"claude"``
        as fallback when the file is absent or malformed.
    """
    import json as _json

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

    For ``opencode``: walks the seven OpenCode discovery roots in
    priority order, returning the first root that contains at least
    one ``{PLUGIN_NAME}-*`` skill directory. Mirrors the 7-root
    resolver in ``tools-script-executor/scripts/generate_executor.py``.

    When ``target`` is ``None``, auto-detects by reading
    ``runtime.target`` from the nearest ``.plan/marshal.json``.

    Args:
        target: Runtime target (``"claude"`` or ``"opencode"``).

    Returns:
        Path to plugin root, or ``None`` if not found.
    """
    if target is None:
        target = read_runtime_target()

    if target == 'opencode':
        return _detect_opencode_root()

    return _detect_claude_root()


def _detect_claude_root() -> Path | None:
    """Detect the plugin root in the Claude plugin cache."""
    cache_base = Path.home() / '.claude' / 'plugins' / 'cache'

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
    """Walk the seven OpenCode discovery roots for plan-marshall skills.

    Returns the first root that contains at least one directory matching
    ``{PLUGIN_NAME}-*``.
    """
    try:
        home = Path.home()
    except (OSError, RuntimeError):
        return None

    env_config = os.environ.get('OPENCODE_CONFIG_DIR', '')
    roots: list[str] = [
        str(Path(env_config) / 'skills') if env_config else '',
        '.opencode/skills',
        '.claude/skills',
        '.agents/skills',
        str(home / '.config' / 'opencode' / 'skills'),
        str(home / '.claude' / 'skills'),
        str(home / '.agents' / 'skills'),
    ]

    marker_prefix = f'{PLUGIN_NAME}-'

    for root in roots:
        if not root:
            continue
        try:
            root_path = Path(root).resolve()
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
        target: Runtime target (``"claude"`` or ``"opencode"``).
            When ``None``, auto-detects from ``marshal.json``.

    Returns:
        Tuple of (plugin_root_path, source) where source is ``'cached'``,
        ``'detected'``, or ``'not_found'``.
    """
    if target is None:
        target = read_runtime_target()

    if not refresh:
        state = read_state()
        if 'plugin_root' in state:
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
        return None

    # Find versioned directory (usually 1.0.0)
    for version_dir in bundle_dir.iterdir():
        if version_dir.is_dir():
            resolved = version_dir / relative_path
            if resolved.exists():
                return resolved

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
        hint = (
            'Ensure plan-marshall plugin is installed via Claude Code'
            if target_hint == 'claude'
            else 'Ensure plan-marshall skills are deployed to an OpenCode discovery root'
        )
        return {
            'status': 'error',
            'error': 'Plugin root not found',
            'target': target_hint,
            'hint': hint,
        }


def cmd_resolve(args: argparse.Namespace) -> dict:
    """Handle the 'resolve' subcommand."""
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
        choices=('claude', 'opencode'),
        default=None,
        help=(
            'Runtime target. Auto-detected from .plan/marshal.json when omitted. '
            'Use "opencode" for OpenCode discovery roots.'
        ),
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    # get-root subcommand
    root_parser = subparsers.add_parser('get-root', help='Get the plugin root path', allow_abbrev=False)
    root_parser.add_argument('--refresh', action='store_true', help='Force re-detection even if cached')

    # resolve subcommand
    resolve_parser = subparsers.add_parser('resolve', help='Resolve a path relative to a bundle', allow_abbrev=False)
    resolve_parser.add_argument('--bundle', required=True, help="Bundle name (e.g., 'plan-marshall')")
    resolve_parser.add_argument('--path', required=True, help='Path relative to bundle root')

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

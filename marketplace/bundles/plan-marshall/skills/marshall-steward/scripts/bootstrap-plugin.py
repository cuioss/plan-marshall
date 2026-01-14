#!/usr/bin/env python3
"""
Bootstrap script for detecting and caching the plugin root path.

This script solves the chicken-and-egg problem of locating plugin scripts
before the executor is available. It detects the plugin installation path
and caches it in .plan/marshall-state.toon for subsequent use.

Usage:
    python3 bootstrap-plugin.py get-root [--refresh]
    python3 bootstrap-plugin.py resolve <bundle> <path>

Subcommands:
    get-root    Return the plugin root path (detects if needed)
    resolve     Resolve a path relative to a bundle

Output (TOON format):
    get-root:
        plugin_root	/Users/user/.claude/plugins/cache/plan-marshall
        source	cached|detected

    resolve:
        resolved_path	/Users/user/.claude/plugins/cache/plan-marshall/pm-workflow/1.0.0/skills/...

Environment:
    PLAN_BASE_DIR   Override .plan directory location (for testing)
"""

import argparse
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

# Default plugin name to search for
PLUGIN_NAME = 'plan-marshall'

# Marker file that uniquely identifies our plugin
MARKER_FILE = '.claude-plugin/plugin.json'

# State file name
STATE_FILE = 'marshall-state.toon'


def get_plan_dir() -> Path:
    """Get the .plan directory path, respecting PLAN_BASE_DIR override."""
    base = os.environ.get('PLAN_BASE_DIR', '.plan')
    return Path(base)


def get_state_file() -> Path:
    """Get the state file path."""
    return get_plan_dir() / STATE_FILE


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


def detect_plugin_root() -> Path | None:
    """
    Detect the plugin root by searching for the marker file.

    Searches in ~/.claude/plugins/cache/ for directories containing
    a bundle with our marker file.

    Returns:
        Path to plugin root, or None if not found
    """
    cache_base = Path.home() / '.claude' / 'plugins' / 'cache'

    if not cache_base.exists():
        return None

    # Search for plugin directories containing our marker
    for plugin_dir in cache_base.iterdir():
        if not plugin_dir.is_dir():
            continue

        # Check each bundle directory for the marker
        for bundle_dir in plugin_dir.iterdir():
            if not bundle_dir.is_dir():
                continue

            # Check versioned directories
            for version_dir in bundle_dir.iterdir():
                if not version_dir.is_dir():
                    continue

                marker_path = version_dir / MARKER_FILE
                if marker_path.exists():
                    # Found a valid bundle, return the plugin root
                    return plugin_dir

    return None


def get_plugin_root(refresh: bool = False) -> tuple[Path | None, str]:
    """
    Get the plugin root, using cache if available.

    Args:
        refresh: Force re-detection even if cached

    Returns:
        Tuple of (plugin_root_path, source) where source is 'cached' or 'detected'
    """
    if not refresh:
        state = read_state()
        if 'plugin_root' in state:
            cached_path = Path(state['plugin_root'])
            # Verify it still exists
            if cached_path.exists():
                return cached_path, 'cached'

    # Detect plugin root
    plugin_root = detect_plugin_root()
    if plugin_root:
        # Cache for future use
        state = read_state()
        state['plugin_root'] = str(plugin_root)
        state['detected_at'] = datetime.now(UTC).isoformat()
        write_state(state)
        return plugin_root, 'detected'

    return None, 'not_found'


def resolve_bundle_path(plugin_root: Path, bundle: str, relative_path: str) -> Path | None:
    """
    Resolve a path relative to a bundle.

    Args:
        plugin_root: The plugin root directory
        bundle: Bundle name (e.g., 'pm-workflow')
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


def cmd_get_root(args: argparse.Namespace) -> int:
    """Handle the 'get-root' subcommand."""
    plugin_root, source = get_plugin_root(refresh=args.refresh)

    if plugin_root:
        print(f'plugin_root\t{plugin_root}')
        print(f'source\t{source}')
        return 0
    else:
        print('error\tPlugin root not found')
        print('hint\tEnsure plan-marshall plugin is installed via Claude Code')
        return 1


def cmd_resolve(args: argparse.Namespace) -> int:
    """Handle the 'resolve' subcommand."""
    plugin_root, _ = get_plugin_root()

    if not plugin_root:
        print('error\tPlugin root not found')
        return 1

    resolved = resolve_bundle_path(plugin_root, args.bundle, args.path)

    if resolved:
        print(f'resolved_path\t{resolved}')
        return 0
    else:
        print(f'error\tPath not found: {args.bundle}/{args.path}')
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description='Bootstrap script for plugin root detection')
    subparsers = parser.add_subparsers(dest='command', required=True)

    # get-root subcommand
    root_parser = subparsers.add_parser('get-root', help='Get the plugin root path')
    root_parser.add_argument('--refresh', action='store_true', help='Force re-detection even if cached')

    # resolve subcommand
    resolve_parser = subparsers.add_parser('resolve', help='Resolve a path relative to a bundle')
    resolve_parser.add_argument('bundle', help="Bundle name (e.g., 'pm-workflow')")
    resolve_parser.add_argument('path', help='Path relative to bundle root')

    args = parser.parse_args()

    if args.command == 'get-root':
        return cmd_get_root(args)
    elif args.command == 'resolve':
        return cmd_resolve(args)
    else:
        parser.print_help()
        return 1


if __name__ == '__main__':
    sys.exit(main())

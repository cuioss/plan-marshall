#!/usr/bin/env python3
"""
Generate and manage execute-script.py with embedded script mappings.

Usage:
    python3 generate-executor.py generate [--force] [--dry-run] [--marketplace]
    python3 generate-executor.py verify
    python3 generate-executor.py drift [--marketplace]
    python3 generate-executor.py paths
    python3 generate-executor.py cleanup [--max-age-days N]

Subcommands:
    generate    Generate executor with script mappings
    verify      Verify existing executor is valid
    drift       Compare executor mappings with current marketplace state
    paths       Verify all mapped paths exist
    cleanup     Clean up old global logs

Context Detection:
    By default, operates in plugin-cache context (~/.claude/plugins/cache/plan-marshall/).
    Use --marketplace flag for marketplace development context (marketplace/bundles/).
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# ============================================================================
# CONFIGURATION
# ============================================================================

# Central configuration - single source of truth for plan directory name
# Can be overridden via environment variable for testing/alternative deployments
PLAN_DIR_NAME = os.environ.get('PLAN_DIR_NAME', '.plan')
PLAN_DIR = Path(PLAN_DIR_NAME)
EXECUTOR_PATH = PLAN_DIR / 'execute-script.py'
STATE_PATH = PLAN_DIR / 'marshall-state.toon'
LOGS_DIR = PLAN_DIR / 'logs'

# Path constants
MARKETPLACE_BUNDLES_PATH = 'marketplace/bundles'
CLAUDE_DIR = '.claude'
PLUGIN_CACHE_SUBPATH = 'plugins/cache/plan-marshall'

# Script-relative paths (resolved at runtime)
SCRIPT_DIR = Path(__file__).parent.resolve()
# Script is at: marketplace/bundles/plan-marshall/skills/tools-script-executor/scripts/
# So bundles directory is 5 levels up from script
_BUNDLES_FROM_SCRIPT = SCRIPT_DIR.parent.parent.parent.parent.parent


# ============================================================================
# PATH RESOLUTION (follows scan-marketplace-inventory.py pattern)
# ============================================================================


def _find_marketplace_path() -> Path | None:
    """Find marketplace/bundles directory relative to cwd or script.

    First checks cwd-based discovery (supports test fixtures),
    then falls back to script-relative path (works regardless of cwd).
    """
    # First try cwd-based discovery (allows tests to use fixture directories)
    if (Path.cwd() / MARKETPLACE_BUNDLES_PATH).is_dir():
        return Path.cwd() / MARKETPLACE_BUNDLES_PATH
    if (Path.cwd().parent / MARKETPLACE_BUNDLES_PATH).is_dir():
        return Path.cwd().parent / MARKETPLACE_BUNDLES_PATH
    # Fallback to script-relative path (works regardless of cwd)
    if _BUNDLES_FROM_SCRIPT.is_dir():
        return _BUNDLES_FROM_SCRIPT
    return None


def _get_plugin_cache_path() -> Path | None:
    """Get plugin cache path if it exists."""
    cache_path = Path.home() / CLAUDE_DIR / PLUGIN_CACHE_SUBPATH
    return cache_path if cache_path.is_dir() else None


def get_base_path(use_marketplace: bool = False) -> Path:
    """
    Determine base path based on context.

    By default (use_marketplace=False), tries plugin-cache first, then marketplace.
    This enables the script to work both in deployed context and development.

    Args:
        use_marketplace: If True, force marketplace context (development mode)

    Returns:
        Path to the bundles directory

    Raises:
        FileNotFoundError: If neither context is available
    """
    if use_marketplace:
        marketplace = _find_marketplace_path()
        if marketplace:
            return marketplace
        raise FileNotFoundError(f'{MARKETPLACE_BUNDLES_PATH} directory not found. Run from marketplace repo root.')

    # Default: plugin-cache first (common user case), then marketplace
    cache = _get_plugin_cache_path()
    if cache:
        return cache

    marketplace = _find_marketplace_path()
    if marketplace:
        return marketplace

    raise FileNotFoundError(
        f'Neither plugin cache ({Path.home() / CLAUDE_DIR / PLUGIN_CACHE_SUBPATH}) '
        f'nor {MARKETPLACE_BUNDLES_PATH} found. '
        f'Ensure plugin is installed or run from marketplace repo.'
    )


def _resolve_bundle_path(base_path: Path, bundle_name: str, subpath: str) -> Path:
    """Resolve path within a bundle, handling versioned cache structure.

    Tries versioned path first (plugin-cache with version dir), then non-versioned (marketplace).

    Args:
        base_path: Path to bundles directory (plugin-cache or marketplace)
        bundle_name: Name of the bundle (e.g., 'plan-marshall', 'pm-plugin-development')
        subpath: Path within the bundle (e.g., 'skills/foo/scripts/bar.py')
    """
    bundle_dir = base_path / bundle_name

    # Try versioned path first (plugin-cache structure: {bundle}/{version}/...)
    if bundle_dir.is_dir():
        for version_dir in bundle_dir.iterdir():
            if version_dir.is_dir() and not version_dir.name.startswith('.'):
                versioned = version_dir / subpath
                if versioned.exists():
                    return versioned

    # Fall back to non-versioned (marketplace structure: {bundle}/...)
    return bundle_dir / subpath


def _resolve_plan_marshall_path(base_path: Path, subpath: str) -> Path:
    """Resolve path within plan-marshall bundle, handling versioned cache structure.

    Tries versioned path first (plugin-cache with version dir), then non-versioned (marketplace).
    """
    return _resolve_bundle_path(base_path, 'plan-marshall', subpath)


def get_inventory_script(base_path: Path) -> Path:
    """Get path to inventory script based on context."""
    return _resolve_bundle_path(
        base_path, 'pm-plugin-development', 'skills/tools-marketplace-inventory/scripts/scan-marketplace-inventory.py'
    )


def get_templates_dir(base_path: Path) -> Path:
    """Get path to templates directory based on context."""
    return _resolve_plan_marshall_path(base_path, 'skills/tools-script-executor/templates')


def get_logging_scripts_dir(base_path: Path) -> Path:
    """Get path to logging scripts directory based on context."""
    return _resolve_plan_marshall_path(base_path, 'skills/manage-logging/scripts')


# ============================================================================
# SCRIPT DISCOVERY
# ============================================================================


def _build_pythonpath(base_path: Path) -> str:
    """Build PYTHONPATH from all skill script directories.

    This enables cross-skill imports for scripts called via subprocess.

    Args:
        base_path: Path to bundles directory (plugin-cache or marketplace)

    Returns:
        PYTHONPATH string with all skill script directories
    """
    script_dirs = []

    for bundle_dir in base_path.iterdir():
        if not bundle_dir.is_dir() or bundle_dir.name.startswith('.'):
            continue

        # Handle versioned structure (plugin-cache)
        # Check if bundle contains version directories
        has_version_dirs = any(
            d.is_dir() and not d.name.startswith('.') and (d / 'skills').is_dir() for d in bundle_dir.iterdir()
        )

        if has_version_dirs:
            # Plugin-cache structure: bundle/{version}/skills/...
            for version_dir in bundle_dir.iterdir():
                if version_dir.is_dir() and not version_dir.name.startswith('.'):
                    skills_dir = version_dir / 'skills'
                    if skills_dir.exists():
                        for skill_dir in skills_dir.iterdir():
                            if skill_dir.is_dir():
                                scripts_dir = skill_dir / 'scripts'
                                if scripts_dir.exists():
                                    script_dirs.append(str(scripts_dir))
        else:
            # Marketplace structure: bundle/skills/...
            skills_dir = bundle_dir / 'skills'
            if skills_dir.exists():
                for skill_dir in skills_dir.iterdir():
                    if skill_dir.is_dir():
                        scripts_dir = skill_dir / 'scripts'
                        if scripts_dir.exists():
                            script_dirs.append(str(scripts_dir))

    return os.pathsep.join(script_dirs)


def discover_scripts(base_path: Path) -> dict[str, str]:
    """
    Discover all scripts from bundles using inventory script.

    Args:
        base_path: Path to bundles directory (plugin-cache or marketplace)

    Returns:
        dict mapping notation to absolute path
    """
    inventory_script = get_inventory_script(base_path)

    if not inventory_script.exists():
        print(f'Error: Inventory script not found: {inventory_script}', file=sys.stderr)
        sys.exit(1)

    # Determine scope based on path
    scope = 'marketplace' if 'marketplace' in str(base_path) else 'plugin-cache'

    # Build PYTHONPATH to enable cross-skill imports (e.g., toon_parser)
    pythonpath = _build_pythonpath(base_path)
    env = os.environ.copy()
    if pythonpath:
        existing = env.get('PYTHONPATH', '')
        env['PYTHONPATH'] = f'{pythonpath}{os.pathsep}{existing}' if existing else pythonpath

    # Run inventory scan
    result = subprocess.run(
        [
            'python3',
            str(inventory_script),
            '--scope',
            scope,
            '--resource-types',
            'scripts',
            '--direct-result',
            '--format',
            'json',
        ],
        capture_output=True,
        text=True,
        env=env,
    )

    if result.returncode != 0:
        print(f'Error running inventory scan: {result.stderr}', file=sys.stderr)
        sys.exit(1)

    inventory = json.loads(result.stdout)

    # Build notation mappings
    mappings = {}

    bundles_raw = inventory.get('bundles', [])
    # Handle both dict (keyed by name) and list formats from inventory
    if isinstance(bundles_raw, dict):
        bundles = list(bundles_raw.values())
    else:
        bundles = bundles_raw

    for bundle in bundles:
        for script in bundle.get('scripts', []):
            notation = script.get('notation', '')
            path_formats = script.get('path_formats', {})
            abs_path = path_formats.get('absolute', '')

            if notation and abs_path:
                mappings[notation] = abs_path

    return mappings


def discover_scripts_fallback(base_path: Path) -> dict[str, str]:
    """
    Fallback script discovery using glob patterns.

    Args:
        base_path: Path to bundles directory (plugin-cache or marketplace)

    Returns:
        dict mapping notation to absolute path
    """
    mappings = {}

    for bundle_dir in base_path.iterdir():
        if not bundle_dir.is_dir():
            continue

        bundle_name = bundle_dir.name
        skills_dir = bundle_dir / 'skills'

        if not skills_dir.exists():
            continue

        for skill_dir in skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue

            skill_name = skill_dir.name
            scripts_dir = skill_dir / 'scripts'

            if not scripts_dir.exists():
                continue

            # Find the main script (usually {skill_name}.py or similar)
            for script_file in scripts_dir.glob('*.py'):
                # Skip __init__.py and test files
                if script_file.name.startswith('_') or 'test' in script_file.name.lower():
                    continue

                # Use three-part notation: bundle:skill:script
                notation = f'{bundle_name}:{skill_name}:{script_file.stem}'
                abs_path = str(script_file.resolve())
                mappings[notation] = abs_path

    return mappings


def discover_local_scripts(cwd: Path | None = None) -> dict[str, str]:
    """
    Discover scripts from .claude/skills/*/scripts/ in project root.

    Uses 'local:{skill}:{script}' notation to distinguish from marketplace.

    Args:
        cwd: Working directory to search from. Defaults to Path.cwd().

    Returns:
        dict mapping notation to absolute path
    """
    if cwd is None:
        cwd = Path.cwd()

    local_skills = cwd / '.claude' / 'skills'
    if not local_skills.is_dir():
        return {}

    mappings: dict[str, str] = {}

    for skill_dir in local_skills.iterdir():
        if not skill_dir.is_dir() or skill_dir.name.startswith('.'):
            continue

        skill_name = skill_dir.name
        scripts_dir = skill_dir / 'scripts'

        if not scripts_dir.exists():
            continue

        # Find .py files (skip private modules starting with _)
        for script_file in scripts_dir.glob('*.py'):
            if script_file.name.startswith('_'):
                continue
            if script_file.is_file():
                notation = f'local:{skill_name}:{script_file.stem}'
                abs_path = str(script_file.resolve())
                mappings[notation] = abs_path

    return mappings


# ============================================================================
# GENERATION
# ============================================================================


def generate_mappings_code(mappings: dict[str, str]) -> str:
    """Generate Python code for script mappings dict."""
    lines = []
    for notation, path in sorted(mappings.items()):
        lines.append(f'    "{notation}": "{path}",')
    return '\n'.join(lines)


def generate_executor(mappings: dict[str, str], base_path: Path, dry_run: bool = False) -> bool:
    """
    Generate execute-script.py with embedded mappings.

    Args:
        mappings: Script notation to path mappings
        base_path: Path to bundles directory for resolving template/logging paths
        dry_run: If True, show what would be generated without writing

    Returns:
        True if successful
    """
    templates_dir = get_templates_dir(base_path)
    executor_template = templates_dir / 'execute-script.py.template'

    if not executor_template.exists():
        print(f'Error: Template not found: {executor_template}', file=sys.stderr)
        return False

    template = executor_template.read_text()
    mappings_code = generate_mappings_code(mappings)

    # logging module location (unified logging skill)
    logging_scripts_dir = get_logging_scripts_dir(base_path)
    logging_dir = str(logging_scripts_dir.resolve())

    content = template.replace('{{SCRIPT_MAPPINGS}}', mappings_code)
    content = content.replace('{{LOGGING_DIR}}', logging_dir)
    content = content.replace('{{PLAN_DIR_NAME}}', PLAN_DIR_NAME)

    if dry_run:
        print('=== execute-script.py ===')
        print(content[:2000])
        print('... (truncated)')
        return True

    PLAN_DIR.mkdir(parents=True, exist_ok=True)
    EXECUTOR_PATH.write_text(content)
    return True


def compute_checksum(mappings: dict[str, str]) -> str:
    """Compute checksum of mappings for change detection."""
    content = json.dumps(mappings, sort_keys=True)
    return hashlib.md5(content.encode()).hexdigest()[:8]


def update_state(script_count: int, checksum: str, logs_cleaned: int) -> None:
    """Update marshall-state.toon with generation metadata."""
    timestamp = datetime.now().isoformat()
    content = f"""status\tgenerated\tscript_count\tchecksum\tlogs_cleaned
success\t{timestamp}\t{script_count}\t{checksum}\t{logs_cleaned}
"""
    STATE_PATH.write_text(content)


def cleanup_old_logs(max_age_days: int = 7) -> int:
    """
    Clean up old global logs.

    Returns:
        Number of logs deleted
    """
    import time

    deleted = 0
    cutoff = time.time() - (max_age_days * 86400)

    if not LOGS_DIR.exists():
        return 0

    for log_file in LOGS_DIR.glob('script-execution-*.log'):
        try:
            if log_file.stat().st_mtime < cutoff:
                log_file.unlink()
                deleted += 1
        except Exception:
            pass

    return deleted


# ============================================================================
# VERIFICATION
# ============================================================================


def verify_executor(base_path: Path | None = None) -> tuple[bool, int]:
    """
    Verify existing executor is valid.

    Args:
        base_path: Optional path to bundles directory for logging module verification.
                   If None, tries to auto-detect.

    Returns:
        (is_valid, script_count)
    """
    if not EXECUTOR_PATH.exists():
        print(f'Error: Executor not found: {EXECUTOR_PATH}', file=sys.stderr)
        return False, 0

    # Resolve base_path if not provided
    if base_path is None:
        try:
            base_path = get_base_path(use_marketplace=False)
        except FileNotFoundError as e:
            print(f'Error: {e}', file=sys.stderr)
            return False, 0

    logging_scripts_dir = get_logging_scripts_dir(base_path)
    logging_module = logging_scripts_dir / 'plan_logging.py'

    if not logging_module.exists():
        print(f'Error: Logging module not found: {logging_module}', file=sys.stderr)
        return False, 0

    # Try to import and validate using importlib.util for hyphenated filename
    try:
        executor_path = f'{PLAN_DIR_NAME}/execute-script.py'
        import_code = f"""
import importlib.util
spec = importlib.util.spec_from_file_location('executor', '{executor_path}')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
print(len(module.SCRIPTS))
"""
        result = subprocess.run(['python3', '-c', import_code.strip()], capture_output=True, text=True)
        if result.returncode != 0:
            print(f'Error validating executor: {result.stderr}', file=sys.stderr)
            return False, 0

        script_count = int(result.stdout.strip())
        print(f'Executor valid: {script_count} scripts mapped')

    except Exception as e:
        print(f'Error validating executor: {e}', file=sys.stderr)
        return False, 0

    # Verify logging module
    try:
        result = subprocess.run(
            [
                'python3',
                '-c',
                f"import sys; sys.path.insert(0, '{logging_scripts_dir}'); from plan_logging import log_script_execution; print('OK')",
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(f'Error validating logging module: {result.stderr}', file=sys.stderr)
            return False, 0

        print('Logging module valid')

    except Exception as e:
        print(f'Error validating logging module: {e}', file=sys.stderr)
        return False, 0

    return True, script_count


def get_executor_mappings() -> dict[str, str]:
    """
    Extract mappings from current executor.

    Returns:
        dict mapping notation to absolute path, or empty dict on error
    """
    try:
        executor_path = f'{PLAN_DIR_NAME}/execute-script.py'
        import_code = f"""
import importlib.util
import json
spec = importlib.util.spec_from_file_location('executor', '{executor_path}')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
print(json.dumps(module.SCRIPTS))
"""
        result = subprocess.run(['python3', '-c', import_code.strip()], capture_output=True, text=True)
        if result.returncode != 0:
            return {}

        mappings: dict[str, str] = json.loads(result.stdout.strip())
        return mappings

    except Exception:
        return {}


def check_paths_exist(mappings: dict[str, str]) -> tuple[list, list]:
    """
    Check if all mapped paths exist.

    Returns:
        (existing_notations, missing_tuples) where missing_tuples is [(notation, path), ...]
    """
    existing = []
    missing = []

    for notation, path in mappings.items():
        if Path(path).exists():
            existing.append(notation)
        else:
            missing.append((notation, path))

    return existing, missing


# ============================================================================
# COMMANDS
# ============================================================================


def cmd_generate(args):
    """Generate executor with embedded script mappings."""
    # Resolve base path
    try:
        base_path = get_base_path(use_marketplace=args.marketplace)
        context = 'marketplace' if args.marketplace else 'auto-detected'
        print(f'Using context: {context} ({base_path})')
    except FileNotFoundError as e:
        print(f'Error: {e}', file=sys.stderr)
        sys.exit(1)

    # Discover marketplace scripts
    print('Discovering marketplace scripts...')
    try:
        mappings = discover_scripts(base_path)
    except Exception as e:
        print(f'Falling back to glob discovery: {e}', file=sys.stderr)
        mappings = discover_scripts_fallback(base_path)

    marketplace_count = len(mappings)
    print(f'Found {marketplace_count} marketplace scripts')

    # Discover project-local scripts
    print('Discovering project-local scripts...')
    local_mappings = discover_local_scripts()
    local_count = len(local_mappings)
    if local_count > 0:
        mappings.update(local_mappings)
        print(f'Found {local_count} local scripts')

    print(f'Total: {len(mappings)} scripts ({marketplace_count} marketplace, {local_count} local)')

    if args.dry_run:
        print('\n=== Script Mappings ===')
        for notation, path in sorted(mappings.items()):
            print(f'  {notation} -> {path}')
        print()

    # Generate executor (uses logging skill from plan-marshall/logging)
    print('Generating executor...')
    if not generate_executor(mappings, base_path, dry_run=args.dry_run):
        sys.exit(1)

    if args.dry_run:
        print('\nDry run complete. No files written.')
        return

    # Cleanup old logs
    logs_cleaned = cleanup_old_logs()
    if logs_cleaned > 0:
        print(f'Cleaned up {logs_cleaned} old log files')

    # Update state
    checksum = compute_checksum(mappings)
    update_state(len(mappings), checksum, logs_cleaned)

    # Output summary in TOON format
    print('\nstatus\tscripts_discovered\texecutor_generated\tlogs_cleaned')
    print(f'success\t{len(mappings)}\t{EXECUTOR_PATH}\t{logs_cleaned}')


def cmd_verify(args):
    """Verify existing executor."""
    valid, count = verify_executor()
    if valid:
        print('\nstatus\tscript_count')
        print(f'ok\t{count}')
        sys.exit(0)
    else:
        print('\nstatus\tissues')
        print('error\tVerification failed')
        sys.exit(1)


def cmd_drift(args):
    """Compare executor mappings with current bundles state."""
    executor_mappings = get_executor_mappings()

    if not executor_mappings:
        print('Error: Could not read executor mappings', file=sys.stderr)
        sys.exit(1)

    # Resolve base path
    try:
        base_path = get_base_path(use_marketplace=args.marketplace)
        context = 'marketplace' if args.marketplace else 'auto-detected'
        print(f'Using context: {context} ({base_path})')
    except FileNotFoundError as e:
        print(f'Error: {e}', file=sys.stderr)
        sys.exit(1)

    # Get current bundles state using discover_scripts()
    try:
        current_mappings = discover_scripts(base_path)
    except SystemExit:
        print('Warning: Could not read bundles state', file=sys.stderr)
        current_mappings = {}

    # Find differences
    executor_set = set(executor_mappings.keys())
    current_set = set(current_mappings.keys())

    added = current_set - executor_set
    removed = executor_set - current_set
    changed = []

    for notation in executor_set & current_set:
        if executor_mappings[notation] != current_mappings.get(notation):
            changed.append(notation)

    # Report
    print(f'Executor scripts: {len(executor_mappings)}')
    print(f'Bundles scripts: {len(current_mappings)}')

    if added:
        print(f'\nAdded in bundles ({len(added)}):')
        for n in sorted(added):
            print(f'  + {n}')

    if removed:
        print(f'\nRemoved from bundles ({len(removed)}):')
        for n in sorted(removed):
            print(f'  - {n}')

    if changed:
        print(f'\nPath changed ({len(changed)}):')
        for n in sorted(changed):
            print(f'  ~ {n}')

    if added or removed or changed:
        print('\nstatus\tadded\tremoved\tchanged')
        print(f'drift\t{len(added)}\t{len(removed)}\t{len(changed)}')
    else:
        print('\nstatus\tadded\tremoved\tchanged')
        print('ok\t0\t0\t0')
    sys.exit(0)  # Status modeled in output, not exit code


def cmd_paths(args):
    """Verify all mapped paths exist."""
    mappings = get_executor_mappings()

    if not mappings:
        print('Error: Could not read executor mappings', file=sys.stderr)
        sys.exit(1)

    existing, missing = check_paths_exist(mappings)

    print(f'Total mappings: {len(mappings)}')
    print(f'Existing: {len(existing)}')
    print(f'Missing: {len(missing)}')

    if missing:
        print('\nMissing scripts:')
        for notation, path in missing:
            print(f'  {notation} -> {path}')

        print('\nstatus\texisting\tmissing')
        print(f'missing\t{len(existing)}\t{len(missing)}')
    else:
        print('\nstatus\texisting\tmissing')
        print(f'ok\t{len(existing)}\t0')
    sys.exit(0)  # Status modeled in output, not exit code


def cmd_cleanup(args):
    """Clean up old global logs."""
    deleted = cleanup_old_logs(max_age_days=args.max_age_days)
    print(f'Deleted {deleted} old log files')


# ============================================================================
# MAIN
# ============================================================================


def main():
    parser = argparse.ArgumentParser(
        description='Generate execute-script.py with embedded script mappings',
        epilog='By default uses plugin-cache context. Use --marketplace for development.',
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    # generate subcommand
    gen_parser = subparsers.add_parser('generate', help='Generate executor with script mappings')
    gen_parser.add_argument('--force', action='store_true', help='Force regeneration')
    gen_parser.add_argument('--dry-run', action='store_true', help='Show what would be generated')
    gen_parser.add_argument(
        '--marketplace', action='store_true', help='Use marketplace context (development mode) instead of plugin-cache'
    )
    gen_parser.set_defaults(func=cmd_generate)

    # verify subcommand
    verify_parser = subparsers.add_parser('verify', help='Verify existing executor')
    verify_parser.set_defaults(func=cmd_verify)

    # drift subcommand
    drift_parser = subparsers.add_parser('drift', help='Compare with current bundles state')
    drift_parser.add_argument(
        '--marketplace', action='store_true', help='Use marketplace context (development mode) instead of plugin-cache'
    )
    drift_parser.set_defaults(func=cmd_drift)

    # paths subcommand
    paths_parser = subparsers.add_parser('paths', help='Verify all mapped paths exist')
    paths_parser.set_defaults(func=cmd_paths)

    # cleanup subcommand
    cleanup_parser = subparsers.add_parser('cleanup', help='Clean up old global logs')
    cleanup_parser.add_argument('--max-age-days', type=int, default=7, help='Max age in days (default: 7)')
    cleanup_parser.set_defaults(func=cmd_cleanup)

    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
Generate and manage execute-script.py with embedded script mappings.

Usage:
    python3 generate_executor.py generate [--force] [--dry-run] [--marketplace]
    python3 generate_executor.py verify
    python3 generate_executor.py drift [--marketplace]
    python3 generate_executor.py paths
    python3 generate_executor.py cleanup [--max-age-days N]

Subcommands:
    generate    Generate executor with script mappings
    verify      Verify existing executor is valid
    drift       Compare executor mappings with current marketplace state
    paths       Verify all mapped paths exist
    cleanup     Clean up old logs

The executor is always written directly to ``<root>/.plan/execute-script.py``
(the tracked ``.plan/`` directory inside the main git checkout). There is no
shim-to-external-executor split — every documented call site
(``python3 .plan/execute-script.py …``) runs the real executor directly.

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
from datetime import UTC, datetime
from pathlib import Path

# Bootstrap sys.path — this script may run before the executor sets up PYTHONPATH
# (called directly during wizard Step 4 to generate the executor).
# Resolve shared library paths relative to this script's location in the plugin tree:
#   skills/tools-script-executor/scripts/ → skills/{lib}/scripts/
_SCRIPTS_DIR = Path(__file__).resolve().parent
_SKILLS_DIR = _SCRIPTS_DIR.parent.parent
for _lib in ('ref-toon-format', 'tools-file-ops', 'script-shared'):
    _lib_path = str(_SKILLS_DIR / _lib / 'scripts')
    if _lib_path not in sys.path:
        sys.path.insert(0, _lib_path)

# ============================================================================
# CONFIGURATION
# ============================================================================

# Repo-local tracked config directory name. The executor lives at
# ``{PLAN_DIR_NAME}/execute-script.py`` inside the main git checkout.
PLAN_DIR_NAME = os.environ.get('PLAN_DIR_NAME', '.plan')

# Script-relative paths (resolved at runtime)
SCRIPT_DIR = Path(__file__).parent.resolve()

# Shared path resolution (from script-shared)
from marketplace_bundles import (  # noqa: E402, I001
    build_pythonpath,
    collect_script_dirs,
    resolve_bundle_path,
)
from marketplace_paths import get_base_path as _shared_get_base_path  # noqa: E402, I001
from file_ops import get_base_dir as _get_plan_base_dir  # noqa: E402, I001
from file_ops import get_tracked_config_dir as _get_tracked_config_dir  # noqa: E402, I001


# Runtime-resolved locations. The executor lives at <root>/.plan/execute-script.py
# via get_tracked_config_dir(); state/logs live under get_base_dir() which is
# <root>/.plan/local/ (honouring PLAN_BASE_DIR for tests).
def executor_path() -> Path:
    """Real executor path: <root>/.plan/execute-script.py."""
    return _get_tracked_config_dir() / 'execute-script.py'


def state_path() -> Path:
    return _get_plan_base_dir() / 'marshall-state.toon'


def logs_dir() -> Path:
    return _get_plan_base_dir() / 'logs'

# ============================================================================
# PATH RESOLUTION (delegates to shared modules)
# ============================================================================


def get_base_path(use_marketplace: bool = False) -> Path:
    """Determine base path based on context.

    By default (use_marketplace=False), tries plugin-cache first, then marketplace.
    Delegates to shared marketplace_paths module.
    """
    scope = 'marketplace' if use_marketplace else 'cache-first'
    return _shared_get_base_path(scope)


def _resolve_bundle_path(base_path: Path, bundle_name: str, subpath: str) -> Path:
    """Resolve path within a bundle, handling versioned cache structure."""
    return resolve_bundle_path(base_path, bundle_name, subpath)


def _resolve_plan_marshall_path(base_path: Path, subpath: str) -> Path:
    """Resolve path within plan-marshall bundle."""
    return resolve_bundle_path(base_path, 'plan-marshall', subpath)


def get_inventory_script(base_path: Path) -> Path:
    """Get path to inventory script based on context."""
    return resolve_bundle_path(
        base_path, 'pm-plugin-development', 'skills/tools-marketplace-inventory/scripts/scan-marketplace-inventory.py'
    )


def get_templates_dir(base_path: Path) -> Path:
    """Get path to templates directory based on context."""
    return _resolve_plan_marshall_path(base_path, 'skills/tools-script-executor/templates')


def get_logging_scripts_dir(base_path: Path) -> Path:
    """Get path to logging scripts directory based on context."""
    return _resolve_plan_marshall_path(base_path, 'skills/manage-logging/scripts')


def get_shared_module_dirs(base_path: Path) -> list[Path]:
    """Get paths to shared module directories that must be on sys.path at executor level.

    Shared modules are skills whose scripts are imported by other scripts (e.g., plan_logging
    imports input_validation) but have no executable script notation in the SCRIPTS mapping.
    These directories must be added to sys.path before any executor-level imports.
    """
    shared_skills = [
        'skills/tools-file-ops/scripts',
        'skills/tools-input-validation/scripts',
        'skills/ref-toon-format/scripts',
    ]
    dirs = []
    for subpath in shared_skills:
        resolved = _resolve_plan_marshall_path(base_path, subpath)
        if resolved.is_dir():
            dirs.append(resolved.resolve())
    return dirs


# ============================================================================
# SCRIPT DISCOVERY
# ============================================================================


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
        sys.exit(2)

    # Determine scope based on path
    scope = 'marketplace' if 'marketplace' in str(base_path) else 'plugin-cache'

    # Build PYTHONPATH to enable cross-skill imports (e.g., toon_parser)
    pythonpath = build_pythonpath(base_path)
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
        sys.exit(2)

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

    Uses 'default-bundle:{skill}:{script}' notation — an internal key
    for collision avoidance in the SCRIPTS dict. This is not user-facing;
    the user-facing notation for project-level skills is 'project:{skill}'.

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
                notation = f'default-bundle:{skill_name}:{script_file.stem}'
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

    # Shared module directories (must be on sys.path before executor-level imports)
    shared_dirs = get_shared_module_dirs(base_path)
    shared_module_lines = (
        '\n'.join(f"sys.path.insert(0, '{d}')" for d in shared_dirs) if shared_dirs else '# (none detected)'
    )

    # Collect ALL script directories (including subdirectories of skills like script-shared
    # that have no registered scripts but contain importable modules).
    # These are injected as extra PYTHONPATH entries so subprocess-invoked scripts can
    # import from organized subdirectory layouts (e.g., script-shared/scripts/build/).
    all_script_dirs = collect_script_dirs(base_path)
    extra_dirs_code = ', '.join(f"'{d}'" for d in sorted({str(Path(d).resolve()) for d in all_script_dirs}))

    content = template.replace('{{SCRIPT_MAPPINGS}}', mappings_code)
    content = content.replace('{{LOGGING_DIR}}', logging_dir)
    content = content.replace('{{SHARED_MODULE_DIRS}}', shared_module_lines)
    content = content.replace('{{EXTRA_SCRIPT_DIRS}}', extra_dirs_code)
    content = content.replace('{{PLAN_DIR_NAME}}', PLAN_DIR_NAME)

    if dry_run:
        print('=== execute-script.py ===')
        print(content[:2000])
        print('... (truncated)')
        return True

    real_executor = executor_path()
    real_executor.parent.mkdir(parents=True, exist_ok=True)
    real_executor.write_text(content)
    return True


def compute_checksum(mappings: dict[str, str]) -> str:
    """Compute checksum of mappings for change detection."""
    content = json.dumps(mappings, sort_keys=True)
    return hashlib.md5(content.encode()).hexdigest()[:8]


def update_state(script_count: int, checksum: str, logs_cleaned: int) -> None:
    """Update marshall-state.toon with generation metadata."""
    timestamp = datetime.now(UTC).isoformat()
    content = f"""status\tgenerated\tscript_count\tchecksum\tlogs_cleaned
success\t{timestamp}\t{script_count}\t{checksum}\t{logs_cleaned}
"""
    target = state_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)


def cleanup_old_logs(max_age_days: int = 7) -> int:
    """
    Clean up old global logs.

    Returns:
        Number of logs deleted
    """
    import time

    deleted = 0
    cutoff = time.time() - (max_age_days * 86400)

    target_logs = logs_dir()
    if not target_logs.exists():
        return 0

    for log_file in target_logs.glob('script-execution-*.log'):
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
    real_executor = executor_path()
    if not real_executor.exists():
        print(f'Error: Executor not found: {real_executor}', file=sys.stderr)
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
        import_code = f"""
import importlib.util
spec = importlib.util.spec_from_file_location('executor', '{real_executor}')
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

    # Verify logging module (include shared module dirs for transitive imports)
    shared_dirs = get_shared_module_dirs(base_path)
    path_inserts = '; '.join(f"sys.path.insert(0, '{d}')" for d in shared_dirs)
    if path_inserts:
        path_inserts += '; '
    try:
        result = subprocess.run(
            [
                'python3',
                '-c',
                f"import sys; {path_inserts}sys.path.insert(0, '{logging_scripts_dir}'); from plan_logging import log_script_execution; print('OK')",
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
        real_executor = executor_path()
        import_code = f"""
import importlib.util
import json
spec = importlib.util.spec_from_file_location('executor', '{real_executor}')
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


def cmd_generate(args) -> dict:
    """Generate executor with embedded script mappings."""
    # Resolve base path
    try:
        base_path = get_base_path(use_marketplace=args.marketplace)
        context = 'marketplace' if args.marketplace else 'auto-detected'
        print(f'Using context: {context} ({base_path})')
    except FileNotFoundError as e:
        return {'status': 'error', 'error': str(e)}

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
        return {'status': 'error', 'error': 'Failed to generate executor'}

    if args.dry_run:
        print('\nDry run complete. No files written.')
        return {'status': 'success', 'scripts_discovered': len(mappings), 'dry_run': True}

    # Cleanup old logs
    logs_cleaned = cleanup_old_logs()
    if logs_cleaned > 0:
        print(f'Cleaned up {logs_cleaned} old log files')

    # Update state
    checksum = compute_checksum(mappings)
    update_state(len(mappings), checksum, logs_cleaned)

    result: dict = {
        'status': 'success',
        'scripts_discovered': len(mappings),
        'executor_generated': str(executor_path()),
        'logs_cleaned': logs_cleaned,
    }

    return result


def cmd_verify(args) -> dict:
    """Verify existing executor."""
    valid, count = verify_executor()
    if valid:
        return {'status': 'success', 'script_count': count}
    else:
        return {'status': 'error', 'error': 'Verification failed'}


def cmd_drift(args) -> dict:
    """Compare executor mappings with current bundles state."""
    executor_mappings = get_executor_mappings()

    if not executor_mappings:
        return {'status': 'error', 'error': 'Could not read executor mappings'}

    # Resolve base path
    try:
        base_path = get_base_path(use_marketplace=args.marketplace)
        context = 'marketplace' if args.marketplace else 'auto-detected'
        print(f'Using context: {context} ({base_path})')
    except FileNotFoundError as e:
        return {'status': 'error', 'error': str(e)}

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

    drift_status = 'drift' if (added or removed or changed) else 'ok'
    return {
        'status': 'success',
        'drift_status': drift_status,
        'executor_scripts': len(executor_mappings),
        'bundles_scripts': len(current_mappings),
        'added': len(added),
        'removed': len(removed),
        'changed': len(changed),
    }


def cmd_paths(args) -> dict:
    """Verify all mapped paths exist."""
    mappings = get_executor_mappings()

    if not mappings:
        return {'status': 'error', 'error': 'Could not read executor mappings'}

    existing, missing = check_paths_exist(mappings)

    return {
        'status': 'success',
        'paths_status': 'missing' if missing else 'ok',
        'total': len(mappings),
        'existing': len(existing),
        'missing': len(missing),
    }


def cmd_cleanup(args) -> dict:
    """Clean up old global logs."""
    deleted = cleanup_old_logs(max_age_days=args.max_age_days)
    return {'status': 'success', 'deleted': deleted}


# ============================================================================
# MAIN
# ============================================================================


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Generate execute-script.py with embedded script mappings',
        epilog='By default uses plugin-cache context. Use --marketplace for development.',
        allow_abbrev=False,
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    # generate subcommand
    gen_parser = subparsers.add_parser('generate', help='Generate executor with script mappings', allow_abbrev=False)
    gen_parser.add_argument('--force', action='store_true', help='Force regeneration')
    gen_parser.add_argument('--dry-run', action='store_true', help='Show what would be generated')
    gen_parser.add_argument(
        '--marketplace', action='store_true', help='Use marketplace context (development mode) instead of plugin-cache'
    )
    gen_parser.set_defaults(func=cmd_generate)

    # verify subcommand
    verify_parser = subparsers.add_parser('verify', help='Verify existing executor', allow_abbrev=False)
    verify_parser.set_defaults(func=cmd_verify)

    # drift subcommand
    drift_parser = subparsers.add_parser('drift', help='Compare with current bundles state', allow_abbrev=False)
    drift_parser.add_argument(
        '--marketplace', action='store_true', help='Use marketplace context (development mode) instead of plugin-cache'
    )
    drift_parser.set_defaults(func=cmd_drift)

    # paths subcommand
    paths_parser = subparsers.add_parser('paths', help='Verify all mapped paths exist', allow_abbrev=False)
    paths_parser.set_defaults(func=cmd_paths)

    # cleanup subcommand
    cleanup_parser = subparsers.add_parser('cleanup', help='Clean up old logs', allow_abbrev=False)
    cleanup_parser.add_argument('--max-age-days', type=int, default=7, help='Max age in days (default: 7)')
    cleanup_parser.set_defaults(func=cmd_cleanup)

    args = parser.parse_args()
    result = args.func(args)

    from toon_parser import serialize_toon  # type: ignore[import-not-found]

    print(serialize_toon(result))
    return 0


if __name__ == '__main__':
    from file_ops import safe_main  # type: ignore[import-not-found]

    safe_main(main)()

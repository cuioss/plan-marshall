#!/usr/bin/env python3
"""
Manage run-configuration.json - unified entry point.

Consolidated from:
- init-run-config.py -> init subcommand
- validate-run-config.py -> validate subcommand
- cleanup.py -> cleanup / cleanup-status subcommands

Provides operations for managing .plan/run-configuration.json files
including creation, validation, structure verification, and directory cleanup.

Output: TOON to stdout with operation results.
"""

import argparse
import json
from pathlib import Path
from typing import Any

from constants import VALID_WARNING_CATEGORIES  # type: ignore[import-not-found]
from file_ops import get_base_dir, output_toon, read_json, safe_main, write_json  # type: ignore[import-not-found]
from input_validation import check_field_type, check_required_fields  # type: ignore[import-not-found]

# Constants for timeout handling
SAFETY_MARGIN = 1.25  # Multiplier applied to persisted values on retrieval
HIGHER_WEIGHT = 0.80  # Weight given to higher value during update
MINIMUM_TIMEOUT_SECONDS = 120  # Floor for timeout values - prevents unreasonably short timeouts

# Architecture-refresh enums and defaults
ARCHITECTURE_REFRESH_TIER_0_VALUES = ('enabled', 'disabled')
ARCHITECTURE_REFRESH_TIER_0_DEFAULT = 'enabled'
ARCHITECTURE_REFRESH_TIER_1_VALUES = ('prompt', 'auto', 'disabled')
ARCHITECTURE_REFRESH_TIER_1_DEFAULT = 'prompt'

DEFAULT_STRUCTURE = {
    'version': 1,
    'commands': {},
    'maven': {
        'acceptable_warnings': {'transitive_dependency': [], 'plugin_compatibility': [], 'platform_specific': []}
    },
}


def _write_json_file(file_path: Path, data: dict) -> None:
    """Write JSON data to file atomically via file_ops."""
    write_json(file_path, data)


def _output_success(action: str, **kwargs: Any) -> dict:
    """Build success result dict."""
    result: dict[str, Any] = {'status': 'success', 'action': action}
    result.update(kwargs)
    return result


def _output_error(error: str) -> dict:
    """Build error result dict."""
    return {'status': 'error', 'error': 'config_error', 'message': error}


# =============================================================================
# Init Subcommand
# =============================================================================


def cmd_init(args: argparse.Namespace) -> dict:
    """Initialize run-configuration.json with base structure."""
    try:
        config_path = get_run_config_path()

        if config_path.exists() and not args.force:
            return _output_success(
                'skipped', path=str(config_path), reason='File already exists (use --force to overwrite)'
            )

        _write_json_file(config_path, DEFAULT_STRUCTURE)

        action = 'recreated' if args.force and config_path.exists() else 'created'
        return _output_success(action, path=str(config_path), structure=DEFAULT_STRUCTURE)

    except Exception as e:
        return _output_error(str(e))


# =============================================================================
# Validate Subcommand
# =============================================================================


def validate_run_config(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Validate run-configuration.json format."""
    checks: list[dict[str, Any]] = []

    # Check required fields
    required = ['version', 'commands']
    passed, missing = check_required_fields(data, required)
    checks.append(
        {'check': 'required_fields', 'passed': passed, 'fields': required, 'missing': missing if not passed else []}
    )

    # Check version is integer
    if 'version' in data:
        passed, msg = check_field_type(data, 'version', int)
        checks.append({'check': 'version_type', 'passed': passed, 'message': msg})

    # Check commands is object
    if 'commands' in data:
        passed, msg = check_field_type(data, 'commands', dict)
        checks.append({'check': 'commands_object', 'passed': passed, 'message': msg})

        # Validate command entries
        if passed:
            invalid_commands: list[str] = []
            for cmd_name, cmd_data in data['commands'].items():
                if not isinstance(cmd_data, dict):
                    invalid_commands.append(f'{cmd_name} (not an object)')

            if invalid_commands:
                checks.append({'check': 'command_entries', 'passed': False, 'invalid': invalid_commands})
            else:
                checks.append({'check': 'command_entries', 'passed': True, 'count': len(data['commands'])})

    # Check maven section if present
    if 'maven' in data:
        passed, msg = check_field_type(data, 'maven', dict)
        checks.append({'check': 'maven_object', 'passed': passed, 'message': msg})

    return checks


def cmd_validate(args: argparse.Namespace) -> dict:
    """Validate run-configuration.json format and structure."""
    try:
        file_path = Path(args.file)

        if not file_path.exists():
            return _output_error(f'File not found: {file_path}')

        # Parse JSON
        try:
            data = json.loads(file_path.read_text(encoding='utf-8'))
        except json.JSONDecodeError as e:
            return {
                'status': 'success',
                'valid': False,
                'file': str(file_path),
                'format': 'manage-run-config',
                'checks': [{'check': 'json_syntax', 'passed': False, 'error': str(e)}],
            }

        # Add JSON syntax check
        checks = [{'check': 'json_syntax', 'passed': True}]

        # Run validation
        checks.extend(validate_run_config(data))

        # Determine overall validity
        valid = all(c.get('passed', True) for c in checks)

        return {
            'status': 'success',
            'valid': valid,
            'file': str(file_path),
            'format': 'manage-run-config',
            'checks': checks,
        }

    except Exception as e:
        return _output_error(str(e))


# =============================================================================
# Timeout API (for direct Python calls)
# =============================================================================


def get_run_config_path(project_dir: str | None = None) -> Path:
    """Get path to run-configuration.json.

    Delegates to file_ops.get_base_dir() for consistent path resolution.

    Args:
        project_dir: Ignored. Kept for API compatibility.
    """
    return get_base_dir() / 'run-configuration.json'


def read_run_config(config_path: Path) -> dict[str, Any]:
    """Read run configuration file."""
    result: dict[str, Any] = read_json(config_path, {'version': 1, 'commands': {}})
    return result


def cmd_timeout_get(args: argparse.Namespace) -> dict:
    """Get timeout for a command with default fallback and minimum bound."""
    try:
        config_path = get_run_config_path()
        config = read_run_config(config_path)

        # Look up persisted timeout
        commands = config.get('commands', {})
        cmd_entry = commands.get(args.command, {})
        persisted = cmd_entry.get('timeout_seconds')

        if persisted is None:
            # No persisted value - use default
            timeout = args.default
        else:
            # Apply safety margin to persisted value
            timeout = int(persisted * SAFETY_MARGIN)

        # Enforce minimum bound
        return {
            'status': 'success',
            'command': args.command,
            'timeout_seconds': max(timeout, MINIMUM_TIMEOUT_SECONDS),
        }

    except Exception as e:
        return _output_error(str(e))


def compute_weighted_timeout(existing: int, new_duration: int) -> int:
    """Compute weighted timeout favoring higher value."""
    higher = max(existing, new_duration)
    lower = min(existing, new_duration)
    return int(HIGHER_WEIGHT * higher + (1 - HIGHER_WEIGHT) * lower)


def timeout_get(command_key: str, default: int, project_dir: str = '.') -> int:
    """Get timeout for a command.

    Returns max of MINIMUM_TIMEOUT_SECONDS and either default (if not persisted)
    or persisted * SAFETY_MARGIN. This ensures timeouts never go below a reasonable
    floor, preventing issues from cold/warm JVM timing differences.
    """
    config = read_run_config(get_run_config_path(project_dir))
    persisted = config.get('commands', {}).get(command_key, {}).get('timeout_seconds')
    timeout = default if persisted is None else int(persisted * SAFETY_MARGIN)
    return max(timeout, MINIMUM_TIMEOUT_SECONDS)


def timeout_set(command_key: str, duration: int, project_dir: str = '.') -> None:
    """Set timeout for a command with adaptive weighting."""
    config_path = get_run_config_path(project_dir)
    config = read_run_config(config_path)
    config.setdefault('commands', {}).setdefault(command_key, {})
    existing = config['commands'][command_key].get('timeout_seconds')
    config['commands'][command_key]['timeout_seconds'] = (
        duration if existing is None else compute_weighted_timeout(existing, duration)
    )
    _write_json_file(config_path, config)


# =============================================================================
# Warning Subcommands
# =============================================================================

# VALID_WARNING_CATEGORIES imported from constants


def get_acceptable_warnings(config: dict[str, Any], build_system: str = 'maven') -> dict[str, Any]:
    """Get acceptable_warnings section for a build system."""
    result: dict[str, Any] = config.get(build_system, {}).get('acceptable_warnings', {})
    return result


def cmd_warning_add(args: argparse.Namespace) -> dict:
    """Add a warning pattern to acceptable list."""
    try:
        config_path = get_run_config_path()
        config = read_run_config(config_path)

        category = args.category
        pattern = args.pattern
        build_system = args.build_system

        if category not in VALID_WARNING_CATEGORIES:
            return _output_error(f"Invalid category '{category}'. Valid: {VALID_WARNING_CATEGORIES}")

        # Ensure structure exists
        if build_system not in config:
            config[build_system] = {}
        if 'acceptable_warnings' not in config[build_system]:
            config[build_system]['acceptable_warnings'] = {cat: [] for cat in VALID_WARNING_CATEGORIES}

        warnings_list = config[build_system]['acceptable_warnings'].setdefault(category, [])

        if pattern in warnings_list:
            return _output_success('skipped', category=category, pattern=pattern, reason='Pattern already exists')

        warnings_list.append(pattern)
        _write_json_file(config_path, config)

        return _output_success('added', category=category, pattern=pattern, build_system=build_system)

    except Exception as e:
        return _output_error(str(e))


def cmd_warning_list(args: argparse.Namespace) -> dict:
    """List accepted warning patterns."""
    try:
        config_path = get_run_config_path()
        config = read_run_config(config_path)
        build_system = args.build_system

        warnings = get_acceptable_warnings(config, build_system)

        if args.category:
            if args.category not in VALID_WARNING_CATEGORIES:
                return _output_error(f"Invalid category '{args.category}'. Valid: {VALID_WARNING_CATEGORIES}")
            return {
                'status': 'success',
                'build_system': build_system,
                'category': args.category,
                'patterns': warnings.get(args.category, []),
            }
        else:
            return {
                'status': 'success',
                'build_system': build_system,
                'categories': {cat: warnings.get(cat, []) for cat in VALID_WARNING_CATEGORIES},
            }

    except Exception as e:
        return _output_error(str(e))


def cmd_warning_remove(args: argparse.Namespace) -> dict:
    """Remove a warning pattern from acceptable list."""
    try:
        config_path = get_run_config_path()
        config = read_run_config(config_path)

        category = args.category
        pattern = args.pattern
        build_system = args.build_system

        if category not in VALID_WARNING_CATEGORIES:
            return _output_error(f"Invalid category '{category}'. Valid: {VALID_WARNING_CATEGORIES}")

        warnings = get_acceptable_warnings(config, build_system)
        warnings_list = warnings.get(category, [])

        if pattern not in warnings_list:
            return _output_success('skipped', category=category, pattern=pattern, reason='Pattern not found')

        warnings_list.remove(pattern)
        _write_json_file(config_path, config)

        return _output_success('removed', category=category, pattern=pattern, build_system=build_system)

    except Exception as e:
        return _output_error(str(e))


# =============================================================================
# CLI Subcommands
# =============================================================================


def cmd_timeout_set(args: argparse.Namespace) -> dict:
    """Set timeout for a command with adaptive weighting."""
    try:
        config_path = get_run_config_path()
        config = read_run_config(config_path)

        command = args.command
        duration = args.duration

        # Ensure commands section exists
        if 'commands' not in config:
            config['commands'] = {}

        # Ensure command entry exists
        if command not in config['commands']:
            config['commands'][command] = {}

        cmd_entry = config['commands'][command]
        existing = cmd_entry.get('timeout_seconds')

        if existing is None:
            # No existing value - write directly
            cmd_entry['timeout_seconds'] = duration
            _write_json_file(config_path, config)

            return {
                'status': 'success',
                'command': command,
                'timeout_seconds': duration,
                'source': 'initial',
            }
        else:
            # Compute weighted value favoring higher
            new_timeout = compute_weighted_timeout(existing, duration)
            cmd_entry['timeout_seconds'] = new_timeout
            _write_json_file(config_path, config)

            return {
                'status': 'success',
                'command': command,
                'timeout_seconds': new_timeout,
                'previous_seconds': existing,
                'observed_seconds': duration,
                'source': 'computed',
            }

    except Exception as e:
        return {'status': 'error', 'error': str(e)}


# =============================================================================
# Architecture-Refresh Subcommands
# =============================================================================


def _invalid_value_error(value: str, allowed: tuple[str, ...]) -> dict:
    """Build invalid_value error response with allowed enum values."""
    return {
        'status': 'error',
        'error': 'invalid_value',
        'allowed': list(allowed),
        'message': f"Invalid value '{value}'. Allowed: {list(allowed)}",
    }


def _read_architecture_refresh_value(field: str, default: str) -> str:
    """Read an architecture_refresh field with default fallback.

    The architecture_refresh section is optional — defaults are applied when
    the section is absent so init does not need to materialise it.
    """
    config = read_run_config(get_run_config_path())
    section = config.get('architecture_refresh', {})
    value = section.get(field, default)
    return value if isinstance(value, str) else default


def _write_architecture_refresh_value(field: str, value: str) -> None:
    """Persist an architecture_refresh field, creating the section if needed."""
    config_path = get_run_config_path()
    config = read_run_config(config_path)
    config.setdefault('architecture_refresh', {})[field] = value
    _write_json_file(config_path, config)


def cmd_architecture_refresh_get_tier_0(args: argparse.Namespace) -> dict:
    """Get architecture_refresh.tier_0 (default 'enabled' when absent)."""
    del args  # unused — fixed-shape verb
    try:
        value = _read_architecture_refresh_value('tier_0', ARCHITECTURE_REFRESH_TIER_0_DEFAULT)
        return {'status': 'success', 'field': 'tier_0', 'value': value}
    except Exception as e:
        return _output_error(str(e))


def cmd_architecture_refresh_set_tier_0(args: argparse.Namespace) -> dict:
    """Set architecture_refresh.tier_0 with enum validation."""
    try:
        if args.value not in ARCHITECTURE_REFRESH_TIER_0_VALUES:
            return _invalid_value_error(args.value, ARCHITECTURE_REFRESH_TIER_0_VALUES)
        _write_architecture_refresh_value('tier_0', args.value)
        return {'status': 'success', 'field': 'tier_0', 'value': args.value}
    except Exception as e:
        return _output_error(str(e))


def cmd_architecture_refresh_get_tier_1(args: argparse.Namespace) -> dict:
    """Get architecture_refresh.tier_1 (default 'prompt' when absent)."""
    del args  # unused — fixed-shape verb
    try:
        value = _read_architecture_refresh_value('tier_1', ARCHITECTURE_REFRESH_TIER_1_DEFAULT)
        return {'status': 'success', 'field': 'tier_1', 'value': value}
    except Exception as e:
        return _output_error(str(e))


def cmd_architecture_refresh_set_tier_1(args: argparse.Namespace) -> dict:
    """Set architecture_refresh.tier_1 with enum validation."""
    try:
        if args.value not in ARCHITECTURE_REFRESH_TIER_1_VALUES:
            return _invalid_value_error(args.value, ARCHITECTURE_REFRESH_TIER_1_VALUES)
        _write_architecture_refresh_value('tier_1', args.value)
        return {'status': 'success', 'field': 'tier_1', 'value': args.value}
    except Exception as e:
        return _output_error(str(e))


# =============================================================================
# Cleanup Subcommands (delegates to cleanup.py functions)
# =============================================================================


def cmd_cleanup(args: argparse.Namespace) -> dict | None:
    """Execute cleanup based on retention settings (delegates to cleanup module)."""
    from _cmd_cleanup import cmd_clean

    return cmd_clean(args)


def cmd_cleanup_status(args: argparse.Namespace) -> dict | None:
    """Show cleanup status (delegates to cleanup module)."""
    from _cmd_cleanup import cmd_status

    return cmd_status(args)


# =============================================================================
# Main
# =============================================================================


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Manage run-configuration.json files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
        epilog="""
Examples:
  # Initialize in current project
  %(prog)s init

  # Force reinitialize (overwrites existing)
  %(prog)s init --force

  # Validate run configuration
  %(prog)s validate --file .plan/run-configuration.json

  # Get timeout for a command (with default)
  %(prog)s timeout get --command "ci:pr_checks" --default 300

  # Set/update timeout for a command
  %(prog)s timeout set --command "ci:pr_checks" --duration 180

  # Add acceptable warning pattern
  %(prog)s warning add --category transitive_dependency --pattern "uses transitive dependency"

  # List all acceptable warnings
  %(prog)s warning list

  # List warnings for specific category
  %(prog)s warning list --category plugin_compatibility

  # Remove warning pattern
  %(prog)s warning remove --category transitive_dependency --pattern "uses transitive dependency"

  # Get architecture-refresh tier-0 setting (default: enabled)
  %(prog)s architecture-refresh get-tier-0

  # Set architecture-refresh tier-0 (enabled|disabled)
  %(prog)s architecture-refresh set-tier-0 --value disabled

  # Get architecture-refresh tier-1 setting (default: prompt)
  %(prog)s architecture-refresh get-tier-1

  # Set architecture-refresh tier-1 (prompt|auto|disabled)
  %(prog)s architecture-refresh set-tier-1 --value auto

  # Clean .plan directories based on retention settings
  %(prog)s cleanup

  # Dry-run cleanup for a specific target
  %(prog)s cleanup --dry-run --target logs

  # Show cleanup status
  %(prog)s cleanup-status
""",
    )

    subparsers = parser.add_subparsers(dest='command', required=True, help='Operation to perform')

    # init command
    p_init = subparsers.add_parser('init', help='Initialize run-configuration.json', allow_abbrev=False)
    p_init.add_argument('--force', action='store_true', help='Overwrite existing file')
    p_init.set_defaults(func=cmd_init)

    # validate command
    p_validate = subparsers.add_parser(
        'validate', help='Validate run-configuration.json', allow_abbrev=False
    )
    p_validate.add_argument('--file', required=True, help='Path to run-configuration.json')
    p_validate.set_defaults(func=cmd_validate)

    # timeout command with subcommands
    p_timeout = subparsers.add_parser('timeout', help='Manage command timeouts', allow_abbrev=False)
    timeout_subparsers = p_timeout.add_subparsers(dest='timeout_command', required=True, help='Timeout operation')

    # timeout get
    p_timeout_get = timeout_subparsers.add_parser(
        'get', help='Get timeout for a command', allow_abbrev=False
    )
    p_timeout_get.add_argument('--command', required=True, help='Command identifier (e.g., "ci:pr_checks")')
    p_timeout_get.add_argument(
        '--default', type=int, required=True, help='Default timeout in seconds if no persisted value'
    )
    p_timeout_get.set_defaults(func=cmd_timeout_get)

    # timeout set
    p_timeout_set = timeout_subparsers.add_parser(
        'set', help='Set/update timeout for a command', allow_abbrev=False
    )
    p_timeout_set.add_argument('--command', required=True, help='Command identifier (e.g., "ci:pr_checks")')
    p_timeout_set.add_argument('--duration', type=int, required=True, help='Observed duration in seconds')
    p_timeout_set.set_defaults(func=cmd_timeout_set)

    # warning command with subcommands
    p_warning = subparsers.add_parser('warning', help='Manage acceptable warnings', allow_abbrev=False)
    warning_subparsers = p_warning.add_subparsers(dest='warning_command', required=True, help='Warning operation')

    # warning add
    p_warning_add = warning_subparsers.add_parser(
        'add', help='Add pattern to acceptable warnings', allow_abbrev=False
    )
    p_warning_add.add_argument('--category', required=True, choices=VALID_WARNING_CATEGORIES, help='Warning category')
    p_warning_add.add_argument('--pattern', required=True, help='Warning pattern to accept')
    p_warning_add.add_argument('--build-system', default='maven', help='Build system (default: maven)')
    p_warning_add.set_defaults(func=cmd_warning_add)

    # warning list
    p_warning_list = warning_subparsers.add_parser(
        'list', help='List acceptable warnings', allow_abbrev=False
    )
    p_warning_list.add_argument('--category', choices=VALID_WARNING_CATEGORIES, help='Filter by category (optional)')
    p_warning_list.add_argument('--build-system', default='maven', help='Build system (default: maven)')
    p_warning_list.set_defaults(func=cmd_warning_list)

    # warning remove
    p_warning_remove = warning_subparsers.add_parser(
        'remove', help='Remove pattern from acceptable warnings', allow_abbrev=False
    )
    p_warning_remove.add_argument(
        '--category', required=True, choices=VALID_WARNING_CATEGORIES, help='Warning category'
    )
    p_warning_remove.add_argument('--pattern', required=True, help='Warning pattern to remove')
    p_warning_remove.add_argument('--build-system', default='maven', help='Build system (default: maven)')
    p_warning_remove.set_defaults(func=cmd_warning_remove)

    # architecture-refresh command with subcommands
    p_arch = subparsers.add_parser(
        'architecture-refresh',
        help='Manage architecture_refresh tier knobs',
        allow_abbrev=False,
    )
    arch_subparsers = p_arch.add_subparsers(
        dest='architecture_refresh_command', required=True, help='Architecture-refresh operation'
    )

    # architecture-refresh get-tier-0
    p_arch_get_t0 = arch_subparsers.add_parser(
        'get-tier-0', help='Get architecture_refresh.tier_0 value', allow_abbrev=False
    )
    p_arch_get_t0.set_defaults(func=cmd_architecture_refresh_get_tier_0)

    # architecture-refresh set-tier-0
    p_arch_set_t0 = arch_subparsers.add_parser(
        'set-tier-0', help='Set architecture_refresh.tier_0 value', allow_abbrev=False
    )
    p_arch_set_t0.add_argument(
        '--value',
        required=True,
        choices=list(ARCHITECTURE_REFRESH_TIER_0_VALUES),
        help='Tier-0 value (enabled|disabled)',
    )
    p_arch_set_t0.set_defaults(func=cmd_architecture_refresh_set_tier_0)

    # architecture-refresh get-tier-1
    p_arch_get_t1 = arch_subparsers.add_parser(
        'get-tier-1', help='Get architecture_refresh.tier_1 value', allow_abbrev=False
    )
    p_arch_get_t1.set_defaults(func=cmd_architecture_refresh_get_tier_1)

    # architecture-refresh set-tier-1
    p_arch_set_t1 = arch_subparsers.add_parser(
        'set-tier-1', help='Set architecture_refresh.tier_1 value', allow_abbrev=False
    )
    p_arch_set_t1.add_argument(
        '--value',
        required=True,
        choices=list(ARCHITECTURE_REFRESH_TIER_1_VALUES),
        help='Tier-1 value (prompt|auto|disabled)',
    )
    p_arch_set_t1.set_defaults(func=cmd_architecture_refresh_set_tier_1)

    # cleanup command
    p_cleanup = subparsers.add_parser(
        'cleanup', help='Clean .plan directories based on retention settings', allow_abbrev=False
    )
    p_cleanup.add_argument('--dry-run', action='store_true', help='Show what would be deleted without deleting')
    p_cleanup.add_argument(
        '--target',
        choices=['all', 'temp', 'logs', 'archived-plans', 'memory'],
        default='all',
        help='Clean specific target only (default: all)',
    )
    p_cleanup.set_defaults(func=cmd_cleanup)

    # cleanup-status command
    p_cleanup_status = subparsers.add_parser(
        'cleanup-status', help='Show cleanup status and what would be cleaned', allow_abbrev=False
    )
    p_cleanup_status.set_defaults(func=cmd_cleanup_status)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Handle timeout subcommand
    if args.command == 'timeout':
        if not args.timeout_command:
            p_timeout.print_help()
            return 1

    # Handle warning subcommand
    if args.command == 'warning':
        if not args.warning_command:
            p_warning.print_help()
            return 1

    # Handle architecture-refresh subcommand
    if args.command == 'architecture-refresh':
        if not args.architecture_refresh_command:
            p_arch.print_help()
            return 1

    result = args.func(args)
    if result is not None:
        output_toon(result)
    return 0


@safe_main
def _main() -> int:
    return main()


if __name__ == '__main__':
    _main()

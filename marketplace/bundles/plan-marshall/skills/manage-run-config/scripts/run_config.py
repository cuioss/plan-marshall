#!/usr/bin/env python3
"""
Manage run-configuration.json - initialization and validation.

Consolidated from:
- init-run-config.py → init subcommand
- validate-run-config.py → validate subcommand

Provides operations for managing .plan/run-configuration.json files
including creation, validation, and structure verification.

Output: JSON to stdout with operation results.
"""

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

# Environment variables for path configuration (set by executor or test infrastructure)
_PLAN_DIR_NAME = os.environ.get('PLAN_DIR_NAME', '.plan')


# Constants for timeout handling
SAFETY_MARGIN = 1.25  # Multiplier applied to persisted values on retrieval
HIGHER_WEIGHT = 0.80  # Weight given to higher value during update
MINIMUM_TIMEOUT_SECONDS = 120  # Floor for timeout values - prevents unreasonably short timeouts

DEFAULT_STRUCTURE = {
    'version': 1,
    'commands': {},
    'maven': {
        'acceptable_warnings': {'transitive_dependency': [], 'plugin_compatibility': [], 'platform_specific': []}
    },
    'ci': {'authenticated_tools': [], 'verified_at': None},
    'profile_mappings': {},
    'extension_defaults': {},  # Internal config set by extensions (not user-visible)
}

# Valid canonical commands for profile mappings
VALID_PROFILE_CANONICALS = ['integration-tests', 'coverage', 'benchmark', 'quality-gate', 'skip']


def write_json_file(file_path: Path, data: dict) -> None:
    """Write JSON data to file atomically."""
    file_path.parent.mkdir(parents=True, exist_ok=True)

    fd, temp_path = tempfile.mkstemp(suffix='.json', prefix='.tmp_', dir=file_path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write('\n')
        os.replace(temp_path, file_path)
    except Exception:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise


def output_success(action: str, **kwargs) -> None:
    """Output success result as JSON."""
    result = {'success': True, 'action': action}
    result.update(kwargs)
    print(json.dumps(result, indent=2, ensure_ascii=False))


def output_error(error: str) -> None:
    """Output error result as JSON to stderr."""
    result = {'success': False, 'error': error}
    print(json.dumps(result, indent=2), file=sys.stderr)


# =============================================================================
# Init Subcommand
# =============================================================================


def cmd_init(args) -> int:
    """Initialize run-configuration.json with base structure."""
    try:
        config_path = get_run_config_path()

        if config_path.exists() and not args.force:
            output_success('skipped', path=str(config_path), reason='File already exists (use --force to overwrite)')
            return 0

        write_json_file(config_path, DEFAULT_STRUCTURE)

        action = 'recreated' if args.force and config_path.exists() else 'created'
        output_success(action, path=str(config_path), structure=DEFAULT_STRUCTURE)
        return 0

    except Exception as e:
        output_error(str(e))
        return 1


# =============================================================================
# Validate Subcommand
# =============================================================================


def check_required_fields(data: dict[str, Any], required: list[str]) -> tuple[bool, list[str]]:
    """Check if required fields exist."""
    missing = [f for f in required if f not in data]
    return len(missing) == 0, missing


def check_field_type(data: dict[str, Any], field: str, expected_type: type) -> tuple[bool, str]:
    """Check if field has expected type."""
    if field not in data:
        return False, f"Field '{field}' not found"

    actual = type(data[field])
    if actual != expected_type:
        return False, f'Expected {expected_type.__name__}, got {actual.__name__}'

    return True, f"Field '{field}' is {expected_type.__name__}"


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


def cmd_validate(args) -> int:
    """Validate run-configuration.json format and structure."""
    try:
        file_path = Path(args.file)

        if not file_path.exists():
            output_error(f'File not found: {file_path}')
            return 1

        # Parse JSON
        try:
            with open(file_path, encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            result = {
                'success': True,
                'valid': False,
                'file': str(file_path),
                'format': 'manage-run-config',
                'checks': [{'check': 'json_syntax', 'passed': False, 'error': str(e)}],
            }
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 0

        # Add JSON syntax check
        checks = [{'check': 'json_syntax', 'passed': True}]

        # Run validation
        checks.extend(validate_run_config(data))

        # Determine overall validity
        valid = all(c.get('passed', True) for c in checks)

        result = {'success': True, 'valid': valid, 'file': str(file_path), 'format': 'manage-run-config', 'checks': checks}
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    except Exception as e:
        output_error(str(e))
        return 1


# =============================================================================
# Timeout API (for direct Python calls)
# =============================================================================


def get_run_config_path(project_dir: str | None = None) -> Path:
    """Get path to run-configuration.json.

    Uses PLAN_BASE_DIR env var by default. Falls back to project_dir parameter
    or current directory if env var is not set.

    Args:
        project_dir: Override directory (for Python API backward compatibility).
                    Ignored if PLAN_BASE_DIR env var is set.
    """
    base = os.environ.get('PLAN_BASE_DIR')
    if base is None:
        base = project_dir if project_dir else '.'
    return Path(base).resolve() / _PLAN_DIR_NAME / 'run-configuration.json'


def read_run_config(config_path: Path) -> dict[str, Any]:
    """Read run configuration file."""
    if config_path.exists():
        with open(config_path, encoding='utf-8') as f:
            data: dict[str, Any] = json.load(f)
            return data
    return {'version': 1, 'commands': {}}


def output_toon(status: str, **fields) -> None:
    """Output result in TOON format."""
    print(f'status\t{status}')
    for key, value in fields.items():
        print(f'{key}\t{value}')


def cmd_timeout_get(args) -> int:
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
        print(max(timeout, MINIMUM_TIMEOUT_SECONDS))
        return 0

    except Exception as e:
        print(f'error: {e}', file=sys.stderr)
        return 1


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
    write_json_file(config_path, config)


# =============================================================================
# Warning Subcommands
# =============================================================================

VALID_WARNING_CATEGORIES = ['transitive_dependency', 'plugin_compatibility', 'platform_specific']


def get_acceptable_warnings(config: dict[str, Any], build_system: str = 'maven') -> dict[str, Any]:
    """Get acceptable_warnings section for a build system."""
    result: dict[str, Any] = config.get(build_system, {}).get('acceptable_warnings', {})
    return result


def cmd_warning_add(args) -> int:
    """Add a warning pattern to acceptable list."""
    try:
        config_path = get_run_config_path()
        config = read_run_config(config_path)

        category = args.category
        pattern = args.pattern
        build_system = args.build_system

        if category not in VALID_WARNING_CATEGORIES:
            output_error(f"Invalid category '{category}'. Valid: {VALID_WARNING_CATEGORIES}")
            return 1

        # Ensure structure exists
        if build_system not in config:
            config[build_system] = {}
        if 'acceptable_warnings' not in config[build_system]:
            config[build_system]['acceptable_warnings'] = {cat: [] for cat in VALID_WARNING_CATEGORIES}

        warnings_list = config[build_system]['acceptable_warnings'].setdefault(category, [])

        if pattern in warnings_list:
            output_success('skipped', category=category, pattern=pattern, reason='Pattern already exists')
            return 0

        warnings_list.append(pattern)
        write_json_file(config_path, config)

        output_success('added', category=category, pattern=pattern, build_system=build_system)
        return 0

    except Exception as e:
        output_error(str(e))
        return 1


def cmd_warning_list(args) -> int:
    """List accepted warning patterns."""
    try:
        config_path = get_run_config_path()
        config = read_run_config(config_path)
        build_system = args.build_system

        warnings = get_acceptable_warnings(config, build_system)

        if args.category:
            if args.category not in VALID_WARNING_CATEGORIES:
                output_error(f"Invalid category '{args.category}'. Valid: {VALID_WARNING_CATEGORIES}")
                return 1
            result = {
                'success': True,
                'build_system': build_system,
                'category': args.category,
                'patterns': warnings.get(args.category, []),
            }
        else:
            result = {
                'success': True,
                'build_system': build_system,
                'categories': {cat: warnings.get(cat, []) for cat in VALID_WARNING_CATEGORIES},
            }

        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    except Exception as e:
        output_error(str(e))
        return 1


def cmd_warning_remove(args) -> int:
    """Remove a warning pattern from acceptable list."""
    try:
        config_path = get_run_config_path()
        config = read_run_config(config_path)

        category = args.category
        pattern = args.pattern
        build_system = args.build_system

        if category not in VALID_WARNING_CATEGORIES:
            output_error(f"Invalid category '{category}'. Valid: {VALID_WARNING_CATEGORIES}")
            return 1

        warnings = get_acceptable_warnings(config, build_system)
        warnings_list = warnings.get(category, [])

        if pattern not in warnings_list:
            output_success('skipped', category=category, pattern=pattern, reason='Pattern not found')
            return 0

        warnings_list.remove(pattern)
        write_json_file(config_path, config)

        output_success('removed', category=category, pattern=pattern, build_system=build_system)
        return 0

    except Exception as e:
        output_error(str(e))
        return 1


# =============================================================================
# Profile Mapping Subcommands
# =============================================================================


def get_profile_mappings(config: dict[str, Any]) -> dict[str, Any]:
    """Get profile_mappings section from config."""
    result: dict[str, Any] = config.get('profile_mappings', {})
    return result


def cmd_profile_mapping_set(args) -> int:
    """Set a profile mapping (profile_id -> canonical command or 'skip')."""
    try:
        config_path = get_run_config_path()
        config = read_run_config(config_path)

        profile_id = args.profile_id
        canonical = args.canonical

        if canonical not in VALID_PROFILE_CANONICALS:
            output_error(f"Invalid canonical '{canonical}'. Valid: {VALID_PROFILE_CANONICALS}")
            return 1

        # Ensure profile_mappings section exists
        if 'profile_mappings' not in config:
            config['profile_mappings'] = {}

        previous = config['profile_mappings'].get(profile_id)
        config['profile_mappings'][profile_id] = canonical
        write_json_file(config_path, config)

        result = {
            'success': True,
            'action': 'updated' if previous else 'added',
            'profile_id': profile_id,
            'canonical': canonical,
        }
        if previous:
            result['previous'] = previous

        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    except Exception as e:
        output_error(str(e))
        return 1


def cmd_profile_mapping_get(args) -> int:
    """Get mapping for a specific profile."""
    try:
        config_path = get_run_config_path()
        config = read_run_config(config_path)

        profile_id = args.profile_id
        mappings = get_profile_mappings(config)
        canonical = mappings.get(profile_id)

        if canonical is None:
            result = {'success': True, 'profile_id': profile_id, 'mapped': False}
        else:
            result = {'success': True, 'profile_id': profile_id, 'mapped': True, 'canonical': canonical}

        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    except Exception as e:
        output_error(str(e))
        return 1


def cmd_profile_mapping_list(args) -> int:
    """List all profile mappings."""
    try:
        config_path = get_run_config_path()
        config = read_run_config(config_path)

        mappings = get_profile_mappings(config)

        # Optionally filter by canonical
        if args.canonical:
            filtered = {k: v for k, v in mappings.items() if v == args.canonical}
            result = {'success': True, 'filter': args.canonical, 'count': len(filtered), 'mappings': filtered}
        else:
            result = {'success': True, 'count': len(mappings), 'mappings': mappings}

        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    except Exception as e:
        output_error(str(e))
        return 1


def cmd_profile_mapping_remove(args) -> int:
    """Remove a profile mapping."""
    try:
        config_path = get_run_config_path()
        config = read_run_config(config_path)

        profile_id = args.profile_id
        mappings = get_profile_mappings(config)

        if profile_id not in mappings:
            output_success('skipped', profile_id=profile_id, reason='Mapping not found')
            return 0

        previous = config['profile_mappings'].pop(profile_id)
        write_json_file(config_path, config)

        output_success('removed', profile_id=profile_id, previous=previous)
        return 0

    except Exception as e:
        output_error(str(e))
        return 1


def cmd_profile_mapping_batch_set(args) -> int:
    """Set multiple profile mappings at once from JSON input."""
    try:
        config_path = get_run_config_path()
        config = read_run_config(config_path)

        # Parse mappings from JSON
        try:
            new_mappings = json.loads(args.mappings_json)
        except json.JSONDecodeError as e:
            output_error(f'Invalid JSON: {e}')
            return 1

        if not isinstance(new_mappings, dict):
            output_error('Mappings must be a JSON object')
            return 1

        # Validate all canonicals
        invalid: list[str] = []
        for profile_id, canonical in new_mappings.items():
            if canonical not in VALID_PROFILE_CANONICALS:
                invalid.append(f'{profile_id}:{canonical}')

        if invalid:
            output_error(f'Invalid canonicals: {invalid}. Valid: {VALID_PROFILE_CANONICALS}')
            return 1

        # Ensure profile_mappings section exists
        if 'profile_mappings' not in config:
            config['profile_mappings'] = {}

        # Apply mappings
        added = 0
        updated = 0
        for profile_id, canonical in new_mappings.items():
            if profile_id in config['profile_mappings']:
                updated += 1
            else:
                added += 1
            config['profile_mappings'][profile_id] = canonical

        write_json_file(config_path, config)

        result = {
            'success': True,
            'action': 'batch_set',
            'added': added,
            'updated': updated,
            'total': len(config['profile_mappings']),
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    except Exception as e:
        output_error(str(e))
        return 1


# Python API for profile mappings (for import by other scripts)
def profile_mapping_get(profile_id: str, project_dir: str = '.') -> str | None:
    """Get mapping for a profile. Returns canonical name or None if not mapped."""
    config = read_run_config(get_run_config_path(project_dir))
    mappings: dict[str, str] = config.get('profile_mappings', {})
    return mappings.get(profile_id)


def profile_mapping_get_all(project_dir: str = '.') -> dict[str, Any]:
    """Get all profile mappings."""
    config = read_run_config(get_run_config_path(project_dir))
    result: dict[str, Any] = config.get('profile_mappings', {})
    return result


def profile_mapping_set(profile_id: str, canonical: str, project_dir: str = '.') -> None:
    """Set a profile mapping."""
    if canonical not in VALID_PROFILE_CANONICALS:
        raise ValueError(f"Invalid canonical '{canonical}'. Valid: {VALID_PROFILE_CANONICALS}")
    config_path = get_run_config_path(project_dir)
    config = read_run_config(config_path)
    config.setdefault('profile_mappings', {})[profile_id] = canonical
    write_json_file(config_path, config)


# =============================================================================
# Extension Defaults Subcommands (Generic key-value in extension_defaults)
# =============================================================================


def get_extension_defaults(config: dict[str, Any]) -> dict[str, Any]:
    """Get extension_defaults section from config."""
    result: dict[str, Any] = config.get('extension_defaults', {})
    return result


def cmd_ext_defaults_get(args) -> int:
    """Get a value from extension_defaults by key."""
    try:
        config_path = get_run_config_path()
        config = read_run_config(config_path)

        key = args.key
        defaults = get_extension_defaults(config)
        value = defaults.get(key)

        if value is None:
            result = {'success': True, 'key': key, 'exists': False}
        else:
            result = {'success': True, 'key': key, 'exists': True, 'value': value}

        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    except Exception as e:
        output_error(str(e))
        return 1


def cmd_ext_defaults_set(args) -> int:
    """Set a value in extension_defaults (always overwrites)."""
    try:
        config_path = get_run_config_path()
        config = read_run_config(config_path)

        key = args.key
        # Parse value as JSON
        try:
            value = json.loads(args.value)
        except json.JSONDecodeError:
            # If not valid JSON, treat as string
            value = args.value

        # Ensure extension_defaults section exists
        if 'extension_defaults' not in config:
            config['extension_defaults'] = {}

        previous = config['extension_defaults'].get(key)
        config['extension_defaults'][key] = value
        write_json_file(config_path, config)

        result = {'success': True, 'action': 'updated' if previous is not None else 'added', 'key': key, 'value': value}
        if previous is not None:
            result['previous'] = previous

        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    except Exception as e:
        output_error(str(e))
        return 1


def cmd_ext_defaults_set_default(args) -> int:
    """Set a value in extension_defaults only if key doesn't exist (write-once)."""
    try:
        config_path = get_run_config_path()
        config = read_run_config(config_path)

        key = args.key
        defaults = get_extension_defaults(config)

        # Check if key already exists
        if key in defaults:
            result = {
                'success': True,
                'action': 'skipped',
                'key': key,
                'reason': 'Key already exists',
                'existing_value': defaults[key],
            }
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 0

        # Parse value as JSON
        try:
            value = json.loads(args.value)
        except json.JSONDecodeError:
            # If not valid JSON, treat as string
            value = args.value

        # Ensure extension_defaults section exists
        if 'extension_defaults' not in config:
            config['extension_defaults'] = {}

        config['extension_defaults'][key] = value
        write_json_file(config_path, config)

        result = {'success': True, 'action': 'added', 'key': key, 'value': value}
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    except Exception as e:
        output_error(str(e))
        return 1


def cmd_ext_defaults_list(args) -> int:
    """List all keys in extension_defaults."""
    try:
        config_path = get_run_config_path()
        config = read_run_config(config_path)

        defaults = get_extension_defaults(config)

        result = {'success': True, 'count': len(defaults), 'keys': list(defaults.keys()), 'values': defaults}
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    except Exception as e:
        output_error(str(e))
        return 1


def cmd_ext_defaults_remove(args) -> int:
    """Remove a key from extension_defaults."""
    try:
        config_path = get_run_config_path()
        config = read_run_config(config_path)

        key = args.key
        defaults = get_extension_defaults(config)

        if key not in defaults:
            output_success('skipped', key=key, reason='Key not found')
            return 0

        previous = config['extension_defaults'].pop(key)
        write_json_file(config_path, config)

        output_success('removed', key=key, previous=previous)
        return 0

    except Exception as e:
        output_error(str(e))
        return 1


# Python API for extension_defaults (for import by other scripts)
def ext_defaults_get(key: str, project_dir: str = '.') -> Any:
    """Get value from extension_defaults. Returns None if not found."""
    config = read_run_config(get_run_config_path(project_dir))
    return config.get('extension_defaults', {}).get(key)


def ext_defaults_set(key: str, value: Any, project_dir: str = '.') -> None:
    """Set value in extension_defaults (always overwrites)."""
    config_path = get_run_config_path(project_dir)
    config = read_run_config(config_path)
    config.setdefault('extension_defaults', {})[key] = value
    write_json_file(config_path, config)


def ext_defaults_set_default(key: str, value: Any, project_dir: str = '.') -> bool:
    """Set value in extension_defaults only if key doesn't exist.

    Returns True if value was set, False if key already existed.
    """
    config_path = get_run_config_path(project_dir)
    config = read_run_config(config_path)
    defaults = config.get('extension_defaults', {})

    if key in defaults:
        return False

    config.setdefault('extension_defaults', {})[key] = value
    write_json_file(config_path, config)
    return True


def ext_defaults_list(project_dir: str = '.') -> dict[str, Any]:
    """Get all extension_defaults as a dict."""
    config = read_run_config(get_run_config_path(project_dir))
    result: dict[str, Any] = config.get('extension_defaults', {})
    return result


# =============================================================================
# CLI Subcommands
# =============================================================================


def cmd_timeout_set(args) -> int:
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
            write_json_file(config_path, config)

            output_toon('success', command=command, timeout_seconds=duration, source='initial')
        else:
            # Compute weighted value favoring higher
            new_timeout = compute_weighted_timeout(existing, duration)
            cmd_entry['timeout_seconds'] = new_timeout
            write_json_file(config_path, config)

            output_toon(
                'success',
                command=command,
                timeout_seconds=new_timeout,
                previous_seconds=existing,
                observed_seconds=duration,
                source='computed',
            )

        return 0

    except Exception as e:
        output_toon('error', error=str(e))
        return 1


# =============================================================================
# Main
# =============================================================================


def main():
    parser = argparse.ArgumentParser(
        description='Manage run-configuration.json files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
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
""",
    )

    subparsers = parser.add_subparsers(dest='command', help='Operation to perform')

    # init command
    p_init = subparsers.add_parser('init', help='Initialize run-configuration.json')
    p_init.add_argument('--force', action='store_true', help='Overwrite existing file')
    p_init.set_defaults(func=cmd_init)

    # validate command
    p_validate = subparsers.add_parser('validate', help='Validate run-configuration.json')
    p_validate.add_argument('--file', required=True, help='Path to run-configuration.json')
    p_validate.set_defaults(func=cmd_validate)

    # timeout command with subcommands
    p_timeout = subparsers.add_parser('timeout', help='Manage command timeouts')
    timeout_subparsers = p_timeout.add_subparsers(dest='timeout_command', help='Timeout operation')

    # timeout get
    p_timeout_get = timeout_subparsers.add_parser('get', help='Get timeout for a command')
    p_timeout_get.add_argument('--command', required=True, help='Command identifier (e.g., "ci:pr_checks")')
    p_timeout_get.add_argument(
        '--default', type=int, required=True, help='Default timeout in seconds if no persisted value'
    )
    p_timeout_get.set_defaults(func=cmd_timeout_get)

    # timeout set
    p_timeout_set = timeout_subparsers.add_parser('set', help='Set/update timeout for a command')
    p_timeout_set.add_argument('--command', required=True, help='Command identifier (e.g., "ci:pr_checks")')
    p_timeout_set.add_argument('--duration', type=int, required=True, help='Observed duration in seconds')
    p_timeout_set.set_defaults(func=cmd_timeout_set)

    # warning command with subcommands
    p_warning = subparsers.add_parser('warning', help='Manage acceptable warnings')
    warning_subparsers = p_warning.add_subparsers(dest='warning_command', help='Warning operation')

    # warning add
    p_warning_add = warning_subparsers.add_parser('add', help='Add pattern to acceptable warnings')
    p_warning_add.add_argument('--category', required=True, choices=VALID_WARNING_CATEGORIES, help='Warning category')
    p_warning_add.add_argument('--pattern', required=True, help='Warning pattern to accept')
    p_warning_add.add_argument('--build-system', default='maven', help='Build system (default: maven)')
    p_warning_add.set_defaults(func=cmd_warning_add)

    # warning list
    p_warning_list = warning_subparsers.add_parser('list', help='List acceptable warnings')
    p_warning_list.add_argument('--category', choices=VALID_WARNING_CATEGORIES, help='Filter by category (optional)')
    p_warning_list.add_argument('--build-system', default='maven', help='Build system (default: maven)')
    p_warning_list.set_defaults(func=cmd_warning_list)

    # warning remove
    p_warning_remove = warning_subparsers.add_parser('remove', help='Remove pattern from acceptable warnings')
    p_warning_remove.add_argument(
        '--category', required=True, choices=VALID_WARNING_CATEGORIES, help='Warning category'
    )
    p_warning_remove.add_argument('--pattern', required=True, help='Warning pattern to remove')
    p_warning_remove.add_argument('--build-system', default='maven', help='Build system (default: maven)')
    p_warning_remove.set_defaults(func=cmd_warning_remove)

    # profile-mapping command with subcommands
    p_profile = subparsers.add_parser('profile-mapping', help='Manage profile mappings')
    profile_subparsers = p_profile.add_subparsers(dest='profile_command', help='Profile mapping operation')

    # profile-mapping set
    p_profile_set = profile_subparsers.add_parser('set', help='Set profile mapping')
    p_profile_set.add_argument('--profile-id', required=True, help='Profile identifier (e.g., "jfr", "benchmark")')
    p_profile_set.add_argument(
        '--canonical', required=True, choices=VALID_PROFILE_CANONICALS, help='Canonical command or "skip"'
    )
    p_profile_set.set_defaults(func=cmd_profile_mapping_set)

    # profile-mapping get
    p_profile_get = profile_subparsers.add_parser('get', help='Get profile mapping')
    p_profile_get.add_argument('--profile-id', required=True, help='Profile identifier')
    p_profile_get.set_defaults(func=cmd_profile_mapping_get)

    # profile-mapping list
    p_profile_list = profile_subparsers.add_parser('list', help='List profile mappings')
    p_profile_list.add_argument('--canonical', choices=VALID_PROFILE_CANONICALS, help='Filter by canonical (optional)')
    p_profile_list.set_defaults(func=cmd_profile_mapping_list)

    # profile-mapping remove
    p_profile_remove = profile_subparsers.add_parser('remove', help='Remove profile mapping')
    p_profile_remove.add_argument('--profile-id', required=True, help='Profile identifier')
    p_profile_remove.set_defaults(func=cmd_profile_mapping_remove)

    # profile-mapping batch-set
    p_profile_batch = profile_subparsers.add_parser('batch-set', help='Set multiple profile mappings')
    p_profile_batch.add_argument('--mappings-json', required=True, help='JSON object of profile_id:canonical mappings')
    p_profile_batch.set_defaults(func=cmd_profile_mapping_batch_set)

    # extension-defaults command with subcommands (generic key-value in extension_defaults)
    p_ext_defaults = subparsers.add_parser('extension-defaults', help='Manage extension defaults (generic key-value)')
    ext_defaults_subparsers = p_ext_defaults.add_subparsers(
        dest='ext_defaults_command', help='Extension defaults operation'
    )

    # extension-defaults get
    p_ext_defaults_get = ext_defaults_subparsers.add_parser('get', help='Get value by key')
    p_ext_defaults_get.add_argument('--key', required=True, help='Configuration key (e.g., "my_bundle.skip_profiles")')
    p_ext_defaults_get.set_defaults(func=cmd_ext_defaults_get)

    # extension-defaults set
    p_ext_defaults_set = ext_defaults_subparsers.add_parser('set', help='Set value (always overwrites)')
    p_ext_defaults_set.add_argument('--key', required=True, help='Configuration key')
    p_ext_defaults_set.add_argument(
        '--value', required=True, help='Value as JSON (e.g., \'["a", "b"]\' or \'"string"\' or \'123\')'
    )
    p_ext_defaults_set.set_defaults(func=cmd_ext_defaults_set)

    # extension-defaults set-default
    p_ext_defaults_set_default = ext_defaults_subparsers.add_parser(
        'set-default', help='Set value only if key does not exist (write-once)'
    )
    p_ext_defaults_set_default.add_argument('--key', required=True, help='Configuration key')
    p_ext_defaults_set_default.add_argument(
        '--value', required=True, help='Value as JSON (e.g., \'["a", "b"]\' or \'"string"\' or \'123\')'
    )
    p_ext_defaults_set_default.set_defaults(func=cmd_ext_defaults_set_default)

    # extension-defaults list
    p_ext_defaults_list = ext_defaults_subparsers.add_parser('list', help='List all extension defaults')
    p_ext_defaults_list.set_defaults(func=cmd_ext_defaults_list)

    # extension-defaults remove
    p_ext_defaults_remove = ext_defaults_subparsers.add_parser('remove', help='Remove a key')
    p_ext_defaults_remove.add_argument('--key', required=True, help='Configuration key to remove')
    p_ext_defaults_remove.set_defaults(func=cmd_ext_defaults_remove)

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

    # Handle profile-mapping subcommand
    if args.command == 'profile-mapping':
        if not args.profile_command:
            p_profile.print_help()
            return 1

    # Handle extension-defaults subcommand
    if args.command == 'extension-defaults':
        if not args.ext_defaults_command:
            p_ext_defaults.print_help()
            return 1

    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())

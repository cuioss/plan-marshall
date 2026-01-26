#!/usr/bin/env python3
"""
Manage config.toon files with schema validation and field-level access.

Provides typed configuration for plan execution with enum validation.

Usage:
    python3 manage-config.py read --plan-id my-plan
    python3 manage-config.py get --plan-id my-plan --field commit_strategy
    python3 manage-config.py set --plan-id my-plan --field commit_strategy --value per_deliverable
    python3 manage-config.py create --plan-id my-plan --domains java
    python3 manage-config.py get-domains --plan-id my-plan

Note: workflow_skills are resolved from marshal.json via plan-marshall-config resolve-workflow-skill.
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Any, cast

from _config_core import is_initialized, load_config  # type: ignore[import-not-found]
from file_ops import atomic_write_file, base_path  # type: ignore[import-not-found]
from plan_logging import log_entry  # type: ignore[import-not-found]
from toon_parser import parse_toon, serialize_toon  # type: ignore[import-not-found]

# Schema validation - enum fields
SCHEMA = {
    'commit_strategy': ['per_deliverable', 'per_plan', 'none'],
    'branch_strategy': ['feature', 'direct'],
}

# Structural validation (not enum)
REQUIRED_FIELDS = ['domains', 'commit_strategy']
OPTIONAL_FIELDS = ['create_pr', 'verification_required', 'verification_command', 'branch_strategy']

# Fallback defaults (used when marshal.json doesn't exist)
FALLBACK_DEFAULTS = {
    'commit_strategy': 'per_deliverable',
    'create_pr': True,
    'verification_required': True,
    'branch_strategy': 'feature',
}


def get_defaults() -> dict:
    """Get plan defaults from marshal.json, falling back to hardcoded defaults.

    Reads from .plan/marshal.json -> plan.defaults if available.
    Returns FALLBACK_DEFAULTS if marshal.json doesn't exist or lacks plan.defaults.
    """
    if not is_initialized():
        return FALLBACK_DEFAULTS.copy()

    try:
        marshal_config = load_config()
        plan_defaults = marshal_config.get('plan', {}).get('defaults', {})

        # Merge: marshal.json values override fallback defaults
        result = FALLBACK_DEFAULTS.copy()
        for key in FALLBACK_DEFAULTS:
            if key in plan_defaults:
                result[key] = plan_defaults[key]
        return result
    except (FileNotFoundError, ValueError, KeyError, OSError):
        # Config file missing or parse error - use fallback
        return FALLBACK_DEFAULTS.copy()


def validate_plan_id(plan_id: str) -> bool:
    """Validate plan_id is kebab-case with no special characters."""
    return bool(re.match(r'^[a-z][a-z0-9-]*$', plan_id))


def validate_domain(domain: str) -> bool:
    """Validate domain is a simple lowercase identifier with optional hyphens.

    Examples of valid domains: java, javascript, plan-marshall-plugin-dev
    """
    return bool(re.match(r'^[a-z][a-z0-9-]*$', domain))


def get_config_path(plan_id: str) -> Path:
    """Get the config.toon file path."""
    return cast(Path, base_path('plans', plan_id, 'config.toon'))


def read_config(plan_id: str) -> dict[Any, Any]:
    """Read config.toon for a plan."""
    path = get_config_path(plan_id)
    if not path.exists():
        return {}
    return cast(dict[Any, Any], parse_toon(path.read_text(encoding='utf-8')))


def write_config(plan_id: str, config: dict):
    """Write config.toon for a plan."""
    path = get_config_path(plan_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    content = '# Plan Configuration\n\n' + serialize_toon(config)
    atomic_write_file(path, content)


def validate_field(field: str, value: str) -> tuple[bool, list]:
    """Validate a field value against schema.

    For enum fields, validates against allowed values.
    For other fields, allows any value.
    """
    if field not in SCHEMA:
        return True, []  # Unknown fields are allowed
    valid_values = SCHEMA[field]
    return value in valid_values, valid_values


def get_nested_value(config: dict, field_path: str):
    """Get a nested value using dot notation.

    Args:
        config: Configuration dictionary
        field_path: Dot-separated path (e.g., 'workflow_skills.java.implementation')

    Returns:
        Value at path, or None if not found
    """
    parts = field_path.split('.')
    current = config
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current


def output_toon(data: dict):
    """Output TOON format to stdout."""
    print(serialize_toon(data))


def cmd_read(args):
    """Read entire config.toon."""
    if not validate_plan_id(args.plan_id):
        output_toon(
            {
                'status': 'error',
                'plan_id': args.plan_id,
                'error': 'invalid_plan_id',
                'message': f'Invalid plan_id format: {args.plan_id}',
            }
        )
        sys.exit(1)

    config = read_config(args.plan_id)
    if not config:
        output_toon(
            {'status': 'error', 'plan_id': args.plan_id, 'error': 'file_not_found', 'message': 'config.toon not found'}
        )
        sys.exit(1)

    output_toon({'status': 'success', 'plan_id': args.plan_id, 'config': config})


def cmd_get(args):
    """Get a specific field value.

    Supports nested field access via dot notation (e.g., workflow_skills.java.implementation).
    """
    if not validate_plan_id(args.plan_id):
        output_toon(
            {
                'status': 'error',
                'plan_id': args.plan_id,
                'error': 'invalid_plan_id',
                'message': f'Invalid plan_id format: {args.plan_id}',
            }
        )
        sys.exit(1)

    config = read_config(args.plan_id)
    if not config:
        output_toon(
            {'status': 'error', 'plan_id': args.plan_id, 'error': 'file_not_found', 'message': 'config.toon not found'}
        )
        sys.exit(1)

    # Support nested field access via dot notation
    if '.' in args.field:
        value = get_nested_value(config, args.field)
    else:
        value = config.get(args.field)

    if value is None:
        output_toon(
            {
                'status': 'error',
                'plan_id': args.plan_id,
                'field': args.field,
                'error': 'field_not_found',
                'message': f"Field '{args.field}' not found in config",
            }
        )
        sys.exit(1)

    output_toon({'status': 'success', 'plan_id': args.plan_id, 'field': args.field, 'value': value})


def cmd_set(args):
    """Set a specific field value."""
    if not validate_plan_id(args.plan_id):
        output_toon(
            {
                'status': 'error',
                'plan_id': args.plan_id,
                'error': 'invalid_plan_id',
                'message': f'Invalid plan_id format: {args.plan_id}',
            }
        )
        sys.exit(1)

    # Validate value against schema for enum fields
    is_valid, valid_values = validate_field(args.field, args.value)
    if not is_valid:
        output_toon(
            {
                'status': 'error',
                'plan_id': args.plan_id,
                'field': args.field,
                'error': 'invalid_value',
                'message': f"Invalid value '{args.value}' for field '{args.field}'",
                'valid_values': valid_values,
            }
        )
        sys.exit(1)

    config = read_config(args.plan_id)
    previous = config.get(args.field)
    config[args.field] = args.value
    write_config(args.plan_id, config)
    log_entry('work', args.plan_id, 'INFO', f'[MANAGE-CONFIG] Set {args.field}={args.value}')

    result = {'status': 'success', 'plan_id': args.plan_id, 'field': args.field, 'value': args.value}
    if previous is not None:
        result['previous'] = previous
    output_toon(result)


def cmd_get_multi(args):
    """Get multiple fields in one call."""
    if not validate_plan_id(args.plan_id):
        output_toon(
            {
                'status': 'error',
                'plan_id': args.plan_id,
                'error': 'invalid_plan_id',
                'message': f'Invalid plan_id format: {args.plan_id}',
            }
        )
        sys.exit(1)

    config = read_config(args.plan_id)
    if not config:
        output_toon(
            {'status': 'error', 'plan_id': args.plan_id, 'error': 'file_not_found', 'message': 'config.toon not found'}
        )
        sys.exit(1)

    # Parse requested fields
    fields = [f.strip() for f in args.fields.split(',') if f.strip()]

    result = {'status': 'success', 'plan_id': args.plan_id}

    # Add requested fields to result (only if they exist)
    for field in fields:
        if field in config:
            result[field] = config[field]

    output_toon(result)


def cmd_create(args):
    """Create config.toon with domains configuration.

    Note: workflow_skills are NOT stored in config.toon. They are resolved
    at runtime from marshal.json via plan-marshall-config resolve-workflow-skill.
    """
    if not validate_plan_id(args.plan_id):
        output_toon(
            {
                'status': 'error',
                'plan_id': args.plan_id,
                'error': 'invalid_plan_id',
                'message': f'Invalid plan_id format: {args.plan_id}',
            }
        )
        sys.exit(1)

    # Parse and validate domains
    domains = [d.strip() for d in args.domains.split(',') if d.strip()]
    if not domains:
        output_toon(
            {
                'status': 'error',
                'plan_id': args.plan_id,
                'error': 'invalid_domains',
                'message': 'At least one domain is required',
            }
        )
        sys.exit(1)

    for domain in domains:
        if not validate_domain(domain):
            output_toon(
                {
                    'status': 'error',
                    'plan_id': args.plan_id,
                    'error': 'invalid_domain',
                    'message': f'Invalid domain format: {domain}. Must be lowercase identifier (e.g., java, javascript, plan-marshall-plugin-dev)',
                }
            )
            sys.exit(1)

    # Check if already exists
    path = get_config_path(args.plan_id)
    if path.exists() and not args.force:
        output_toon(
            {
                'status': 'error',
                'plan_id': args.plan_id,
                'error': 'file_exists',
                'message': 'config.toon already exists. Use --force to overwrite.',
            }
        )
        sys.exit(1)

    # Get defaults from marshal.json (falls back to hardcoded if not available)
    defaults = get_defaults()

    # Build config with required fields
    commit_strategy = args.commit_strategy or defaults['commit_strategy']
    is_valid, valid_values = validate_field('commit_strategy', commit_strategy)
    if not is_valid:
        output_toon(
            {
                'status': 'error',
                'plan_id': args.plan_id,
                'field': 'commit_strategy',
                'error': 'invalid_value',
                'message': f"Invalid value '{commit_strategy}' for commit_strategy",
                'valid_values': valid_values,
            }
        )
        sys.exit(1)

    config = {
        'domains': domains,
        'commit_strategy': commit_strategy,
    }

    # Add optional finalize settings with defaults from marshal.json
    if args.create_pr is not None:
        config['create_pr'] = args.create_pr.lower() == 'true'
    else:
        config['create_pr'] = defaults['create_pr']

    if args.verification_required is not None:
        config['verification_required'] = args.verification_required.lower() == 'true'
    else:
        config['verification_required'] = defaults['verification_required']

    if args.verification_command:
        config['verification_command'] = args.verification_command

    branch_strategy = args.branch_strategy or defaults['branch_strategy']
    is_valid, valid_values = validate_field('branch_strategy', branch_strategy)
    if not is_valid:
        output_toon(
            {
                'status': 'error',
                'plan_id': args.plan_id,
                'field': 'branch_strategy',
                'error': 'invalid_value',
                'message': f"Invalid value '{branch_strategy}' for branch_strategy",
                'valid_values': valid_values,
            }
        )
        sys.exit(1)
    config['branch_strategy'] = branch_strategy

    write_config(args.plan_id, config)
    log_entry('work', args.plan_id, 'INFO', f'[MANAGE-CONFIG] Created config (domains: {",".join(domains)})')

    output_toon(
        {'status': 'success', 'plan_id': args.plan_id, 'file': 'config.toon', 'created': True, 'config': config}
    )


def cmd_get_domains(args):
    """Get the domains array from config.toon."""
    if not validate_plan_id(args.plan_id):
        output_toon(
            {
                'status': 'error',
                'plan_id': args.plan_id,
                'error': 'invalid_plan_id',
                'message': f'Invalid plan_id format: {args.plan_id}',
            }
        )
        sys.exit(1)

    config = read_config(args.plan_id)
    if not config:
        output_toon(
            {'status': 'error', 'plan_id': args.plan_id, 'error': 'file_not_found', 'message': 'config.toon not found'}
        )
        sys.exit(1)

    domains = config.get('domains', [])
    output_toon({'status': 'success', 'plan_id': args.plan_id, 'domains': domains, 'count': len(domains)})


def main():
    parser = argparse.ArgumentParser(description='Manage config.toon files with schema validation')
    subparsers = parser.add_subparsers(dest='command', required=True)

    # read
    read_parser = subparsers.add_parser('read', help='Read entire config')
    read_parser.add_argument('--plan-id', required=True, help='Plan identifier')
    read_parser.set_defaults(func=cmd_read)

    # get (supports nested field access via dot notation)
    get_parser = subparsers.add_parser('get', help='Get specific field (supports dot notation)')
    get_parser.add_argument('--plan-id', required=True, help='Plan identifier')
    get_parser.add_argument('--field', required=True, help='Field name (supports dot notation for nested access)')
    get_parser.set_defaults(func=cmd_get)

    # set
    set_parser = subparsers.add_parser('set', help='Set specific field')
    set_parser.add_argument('--plan-id', required=True, help='Plan identifier')
    set_parser.add_argument('--field', required=True, help='Field name')
    set_parser.add_argument('--value', required=True, help='Field value')
    set_parser.set_defaults(func=cmd_set)

    # get-multi
    get_multi_parser = subparsers.add_parser('get-multi', help='Get multiple fields in one call')
    get_multi_parser.add_argument('--plan-id', required=True, help='Plan identifier')
    get_multi_parser.add_argument(
        '--fields', required=True, help='Comma-separated field names (e.g., commit_strategy,branch_strategy)'
    )
    get_multi_parser.set_defaults(func=cmd_get_multi)

    # create
    create_parser = subparsers.add_parser('create', help='Create config.toon')
    create_parser.add_argument('--plan-id', required=True, help='Plan identifier')
    create_parser.add_argument(
        '--domains', required=True, help='Comma-separated list of domains (e.g., java or java,javascript)'
    )
    create_parser.add_argument(
        '--commit-strategy',
        choices=['per_deliverable', 'per_plan', 'none'],
        help='Commit strategy (default: per_deliverable, none=no commits)',
    )
    create_parser.add_argument('--create-pr', help='Create PR on finalize (default: true)')
    create_parser.add_argument('--verification-required', help='Require verification (default: true)')
    create_parser.add_argument('--verification-command', help='Verification command to run')
    create_parser.add_argument(
        '--branch-strategy', choices=['feature', 'direct'], help='Branch strategy (default: feature)'
    )
    create_parser.add_argument('--force', action='store_true', help='Overwrite existing config')
    create_parser.set_defaults(func=cmd_create)

    # get-domains
    gd_parser = subparsers.add_parser('get-domains', help='Get domains array from config')
    gd_parser.add_argument('--plan-id', required=True, help='Plan identifier')
    gd_parser.set_defaults(func=cmd_get_domains)

    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
Shared input validation module for plan-marshall scripts.

Provides validators for plan IDs, file paths, enum values, and skill notation.
All stdlib-only — no external dependencies.

Usage:
    from input_validation import (
        validate_plan_id,
        validate_relative_path,
        validate_enum,
        validate_skill_notation,
        is_valid_plan_id,
        is_valid_relative_path,
    )
"""

import re
import sys
from pathlib import Path

# --- Raising validators (for new code and argparse integration) ---


def validate_plan_id(plan_id: str) -> str:
    """Validate plan_id is kebab-case: starts with letter, then letters/digits/hyphens.

    Returns the validated value for chaining.
    Raises ValueError if invalid.
    """
    if not plan_id or not re.match(r'^[a-z][a-z0-9-]*$', plan_id):
        raise ValueError(f'Invalid plan_id format: {plan_id!r}. Must match ^[a-z][a-z0-9-]*$')
    return plan_id


def validate_relative_path(file_path: str) -> str:
    """Validate file path has no directory traversal or absolute paths.

    Rejects:
    - Absolute paths (starting with /)
    - Path traversal (.. anywhere in path components)
    - Empty paths

    Returns the validated value for chaining.
    Raises ValueError if invalid.
    """
    if not file_path:
        raise ValueError('File path must not be empty')
    if file_path.startswith('/'):
        raise ValueError(f'Absolute paths not allowed: {file_path!r}')
    # Check each path component for traversal
    parts = file_path.replace('\\', '/').split('/')
    for part in parts:
        if part == '..':
            raise ValueError(f'Path traversal not allowed: {file_path!r}')
    return file_path


def validate_enum(value: str, allowed: list, label: str) -> str:
    """Validate value is one of the allowed values.

    Returns the validated value for chaining.
    Raises ValueError if not in allowed list.
    """
    if value not in allowed:
        raise ValueError(f'Invalid {label}: {value!r}. Must be one of: {allowed}')
    return value


def validate_skill_notation(skill: str) -> str:
    """Validate skill notation is in bundle:skill format.

    Returns the validated value for chaining.
    Raises ValueError if invalid.
    """
    if not skill or ':' not in skill:
        raise ValueError(f'Invalid skill notation: {skill!r}. Must be in bundle:skill format')
    parts = skill.split(':')
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError(f'Invalid skill notation: {skill!r}. Must be in bundle:skill format')
    return skill


def validate_script_notation(notation: str) -> str:
    """Validate script notation is in bundle:skill:script format.

    Returns the validated value for chaining.
    Raises ValueError if invalid.
    """
    if not notation or ':' not in notation:
        raise ValueError(f'Invalid script notation: {notation!r}. Must be in bundle:skill:script format')
    parts = notation.split(':')
    if len(parts) != 3 or not all(parts):
        raise ValueError(f'Invalid script notation: {notation!r}. Must be in bundle:skill:script format')
    return notation


# --- Structural validators (shared by run_config, manage-memory, etc.) ---


def check_required_fields(data: dict, required: list[str]) -> tuple[bool, list[str]]:
    """Check if required fields exist in a dict.

    Returns (all_present, missing_fields).
    """
    missing = [f for f in required if f not in data]
    return len(missing) == 0, missing


def check_field_type(data: dict, field: str, expected_type: type) -> tuple[bool, str]:
    """Check if a field has the expected type.

    Returns (valid, message).
    """
    if field not in data:
        return False, f"Field '{field}' not found"

    actual = type(data[field])
    if actual != expected_type:
        return False, f'Expected {expected_type.__name__}, got {actual.__name__}'

    return True, f"Field '{field}' is {expected_type.__name__}"


# --- Argparse integration helpers ---


def require_valid_plan_id(args) -> str:
    """Validate plan_id from argparse args, exit with TOON error if invalid.

    Extracts args.plan_id, validates kebab-case format. On failure, prints
    a standard TOON error to stdout and calls sys.exit(1).

    Returns the validated plan_id string for chaining.

    Usage in command handlers:
        plan_id = require_valid_plan_id(args)
    """
    from toon_parser import serialize_toon

    plan_id: str = getattr(args, 'plan_id', None) or ''
    if not plan_id:
        print(serialize_toon({
            'status': 'error',
            'error': 'missing_plan_id',
            'message': 'plan_id is required',
        }))
        sys.exit(1)
    if not is_valid_plan_id(plan_id):
        print(serialize_toon({
            'status': 'error',
            'plan_id': plan_id,
            'error': 'invalid_plan_id',
            'message': f'Invalid plan_id format: {plan_id}',
        }))
        sys.exit(1)
    return plan_id


def require_plan_file(plan_id: str, *path_parts: str) -> Path:
    """Validate plan_id and check that a plan file exists, exit with TOON error if not.

    Combines plan_id validation, path construction, and existence check into
    one call. Eliminates the repeated 3-step pattern across manage-* scripts.

    Args:
        plan_id: Plan identifier (kebab-case)
        *path_parts: Additional path components after plans/{plan_id}/
            e.g. require_plan_file(plan_id, 'status.json')
            e.g. require_plan_file(plan_id)  # just checks plan dir exists

    Returns:
        Path to the validated file/directory.

    Usage:
        plan_dir = require_plan_file(plan_id)
        status_path = require_plan_file(plan_id, 'status.json')
    """
    from file_ops import base_path  # type: ignore[import-not-found]
    from toon_parser import serialize_toon

    if not is_valid_plan_id(plan_id):
        print(serialize_toon({
            'status': 'error',
            'plan_id': plan_id,
            'error': 'invalid_plan_id',
            'message': f'Invalid plan_id format: {plan_id}',
        }))
        sys.exit(1)

    target = base_path('plans', plan_id, *path_parts)
    if not target.exists():
        error_code = 'file_not_found' if path_parts else 'plan_not_found'
        file_desc = str(Path(*path_parts)) if path_parts else f'plan {plan_id}'
        print(serialize_toon({
            'status': 'error',
            'plan_id': plan_id,
            'error': error_code,
            'message': f'Not found: {file_desc}',
        }))
        sys.exit(1)

    return target


# --- Argparse builder helpers ---
# Reduce boilerplate for the --plan-id / --phase arguments repeated across 50+ subparsers.


def add_plan_id_arg(parser, required: bool = True) -> None:
    """Add the standard --plan-id argument to a parser or subparser."""
    parser.add_argument('--plan-id', required=required, help='Plan identifier (kebab-case)')


def add_phase_arg(parser, *, choices=None, required: bool = True) -> None:
    """Add the standard --phase argument to a parser or subparser.

    Args:
        parser: argparse parser or subparser
        choices: Sequence of valid phase values. Defaults to PHASES from constants.
        required: Whether the argument is required (default True)
    """
    if choices is None:
        from constants import PHASES  # type: ignore[import-not-found]
        choices = PHASES
    parser.add_argument('--phase', required=required, choices=choices, help='Phase name')


def add_boolean_arg(parser, name: str, *, help_text: str = '', default: bool = False) -> None:
    """Add a boolean argument with consistent true/false string parsing.

    Adds --{name} with type conversion from string 'true'/'false' to bool.
    Handles case-insensitive input.

    Args:
        parser: argparse parser or subparser
        name: Argument name (without --)
        help_text: Help string
        default: Default value
    """
    parser.add_argument(
        f'--{name}',
        type=lambda x: x.lower() in ('true', '1', 'yes'),
        default=default,
        help=help_text,
    )


# --- Bool companions (drop-in replacements for existing call sites) ---

def is_valid_plan_id(plan_id: str) -> bool:
    """Check if plan_id is valid kebab-case format.

    Drop-in replacement for the existing validate_plan_id() bool pattern.
    """
    try:
        validate_plan_id(plan_id)
        return True
    except ValueError:
        return False


def is_valid_relative_path(file_path: str) -> bool:
    """Check if file path is a valid relative path without traversal.

    Drop-in replacement for the existing validate_file_path() bool pattern.
    """
    try:
        validate_relative_path(file_path)
        return True
    except ValueError:
        return False

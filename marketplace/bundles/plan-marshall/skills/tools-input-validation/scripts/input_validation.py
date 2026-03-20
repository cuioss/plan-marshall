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

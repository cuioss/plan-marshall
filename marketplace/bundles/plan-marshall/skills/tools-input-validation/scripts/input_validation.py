#!/usr/bin/env python3
"""
Shared input validation module for plan-marshall scripts.

Provides validators for the canonical identifier vocabulary plus file paths,
enum values, and skill notation. All stdlib-only — no external dependencies.

Usage:
    from input_validation import (
        validate_plan_id,
        validate_lesson_id,
        validate_session_id,
        validate_task_number,
        validate_task_id,
        validate_component,
        validate_hash_id,
        validate_memory_id,
        validate_phase_id,
        validate_field_name,
        validate_module_name,
        validate_package_name,
        validate_domain_name,
        validate_resource_name,
        validate_relative_path,
        validate_enum,
        validate_skill_notation,
        is_valid_plan_id,
        is_valid_relative_path,
        # Lesson-ID reference scanner (live-anchored)
        scan_lesson_id_tokens,
        verify_lesson_ids_exist,
        verify_lesson_id_regex_against_inventory,
        LessonInventoryUnavailable,
        LessonRegexAnchoringError,
    )
"""

import re
import sys
from pathlib import Path

# --- Canonical identifier regexes (single source of truth) ---

PLAN_ID_RE = re.compile(r'^[a-z][a-z0-9-]*$')
LESSON_ID_RE = re.compile(r'^[0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9]{2}-[0-9]+$')
SESSION_ID_RE = re.compile(r'^[A-Za-z0-9_-]{1,128}$')
TASK_NUMBER_RE = re.compile(r'^[0-9]+$')
TASK_ID_RE = re.compile(r'^TASK-[0-9]+$')
COMPONENT_RE = re.compile(r'^[a-z0-9-]+(:[a-z0-9-]+)*$')
HASH_ID_RE = re.compile(r'^[a-f0-9]{4,}$')
MEMORY_ID_RE = re.compile(r'^[a-z0-9_-]+$')
# Phase enum — single source of truth. PHASE_ID_RE is derived from this tuple
# below, so adding/removing a phase only needs to change VALID_PHASES.
VALID_PHASES = (
    '1-init',
    '2-refine',
    '3-outline',
    '4-plan',
    '5-execute',
    '6-finalize',
)
PHASE_ID_RE = re.compile(f'^({"|".join(re.escape(p) for p in VALID_PHASES)})$')
FIELD_NAME_RE = re.compile(r'^[a-z][a-z0-9_]*$')
MODULE_NAME_RE = re.compile(r'^[a-z][a-z0-9_-]*$')
PACKAGE_NAME_RE = re.compile(r'^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)*$')
DOMAIN_NAME_RE = re.compile(r'^[a-z][a-z0-9-]*$')
RESOURCE_NAME_RE = re.compile(r'^[a-zA-Z0-9_-]+$')

# --- Raising validators (for new code and argparse integration) ---


def validate_plan_id(plan_id: str) -> str:
    """Validate plan_id is kebab-case: starts with letter, then letters/digits/hyphens.

    Returns the validated value for chaining.
    Raises ValueError if invalid.
    """
    if not plan_id or not PLAN_ID_RE.match(plan_id):
        raise ValueError(f'Invalid plan_id format: {plan_id!r}. Must match {PLAN_ID_RE.pattern}')
    return plan_id


def validate_lesson_id(lesson_id: str) -> str:
    """Validate lesson_id matches YYYY-MM-DD-HH-NNN (date-hour-counter).

    Examples: "2026-04-28-12-001", "2026-04-27-18-007".
    """
    if not lesson_id or not LESSON_ID_RE.match(lesson_id):
        raise ValueError(f'Invalid lesson_id format: {lesson_id!r}. Must match {LESSON_ID_RE.pattern}')
    return lesson_id


def validate_session_id(session_id: str) -> str:
    """Validate session_id is the Claude Code UUID-shape token.

    Allows letters, digits, underscore, hyphen; 1-128 chars.
    """
    if not session_id or not SESSION_ID_RE.match(session_id):
        raise ValueError(f'Invalid session_id format: {session_id!r}. Must match {SESSION_ID_RE.pattern}')
    return session_id


def validate_task_number(task_number: str) -> str:
    """Validate task_number is a non-negative integer string (e.g., "1", "12")."""
    if not task_number or not TASK_NUMBER_RE.match(task_number):
        raise ValueError(f'Invalid task_number format: {task_number!r}. Must match {TASK_NUMBER_RE.pattern}')
    return task_number


def validate_task_id(task_id: str) -> str:
    """Validate task_id is the canonical TASK-NNN form (e.g., "TASK-001")."""
    if not task_id or not TASK_ID_RE.match(task_id):
        raise ValueError(f'Invalid task_id format: {task_id!r}. Must match {TASK_ID_RE.pattern}')
    return task_id


def validate_component(component: str) -> str:
    """Validate component is colon-separated kebab-case (e.g., "plan-marshall:manage-tasks")."""
    if not component or not COMPONENT_RE.match(component):
        raise ValueError(f'Invalid component format: {component!r}. Must match {COMPONENT_RE.pattern}')
    return component


def validate_hash_id(hash_id: str) -> str:
    """Validate hash_id is a lowercase-hex string of >=4 chars (truncated SHA prefix)."""
    if not hash_id or not HASH_ID_RE.match(hash_id):
        raise ValueError(f'Invalid hash_id format: {hash_id!r}. Must match {HASH_ID_RE.pattern}')
    return hash_id


def validate_memory_id(memory_id: str) -> str:
    """Validate memory_id is lowercase letters/digits/underscore/hyphen."""
    if not memory_id or not MEMORY_ID_RE.match(memory_id):
        raise ValueError(f'Invalid memory_id format: {memory_id!r}. Must match {MEMORY_ID_RE.pattern}')
    return memory_id


def validate_phase_id(phase_id: str) -> str:
    """Validate phase_id is one of the canonical 6 phases (e.g., "3-outline")."""
    if not phase_id or not PHASE_ID_RE.match(phase_id):
        raise ValueError(f'Invalid phase_id format: {phase_id!r}. Must match {PHASE_ID_RE.pattern}')
    return phase_id


def validate_field_name(field_name: str) -> str:
    """Validate field_name is snake_case starting with a lowercase letter."""
    if not field_name or not FIELD_NAME_RE.match(field_name):
        raise ValueError(f'Invalid field_name format: {field_name!r}. Must match {FIELD_NAME_RE.pattern}')
    return field_name


def validate_module_name(module_name: str) -> str:
    """Validate module_name is kebab-or-snake starting with a lowercase letter."""
    if not module_name or not MODULE_NAME_RE.match(module_name):
        raise ValueError(f'Invalid module_name format: {module_name!r}. Must match {MODULE_NAME_RE.pattern}')
    return module_name


def validate_package_name(package_name: str) -> str:
    """Validate package_name is dotted snake_case (e.g., "foo.bar.baz")."""
    if not package_name or not PACKAGE_NAME_RE.match(package_name):
        raise ValueError(f'Invalid package_name format: {package_name!r}. Must match {PACKAGE_NAME_RE.pattern}')
    return package_name


def validate_domain_name(domain_name: str) -> str:
    """Validate domain_name is kebab-case starting with a lowercase letter."""
    if not domain_name or not DOMAIN_NAME_RE.match(domain_name):
        raise ValueError(f'Invalid domain_name format: {domain_name!r}. Must match {DOMAIN_NAME_RE.pattern}')
    return domain_name


def validate_resource_name(resource_name: str) -> str:
    """Validate resource_name (e.g., agent/skill/component name) is alphanumeric + _-."""
    if not resource_name or not RESOURCE_NAME_RE.match(resource_name):
        raise ValueError(f'Invalid resource_name format: {resource_name!r}. Must match {RESOURCE_NAME_RE.pattern}')
    return resource_name


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
    a standard TOON error to stdout and exits with code 0 (expected error).

    Returns the validated plan_id string for chaining.

    Usage in command handlers:
        plan_id = require_valid_plan_id(args)
    """
    from toon_parser import serialize_toon

    plan_id: str = getattr(args, 'plan_id', None) or ''
    if not plan_id:
        print(
            serialize_toon(
                {
                    'status': 'error',
                    'error': 'missing_plan_id',
                    'message': 'plan_id is required',
                }
            )
        )
        sys.exit(0)
    if not is_valid_plan_id(plan_id):
        print(
            serialize_toon(
                {
                    'status': 'error',
                    'plan_id': plan_id,
                    'error': 'invalid_plan_id',
                    'message': f'Invalid plan_id format: {plan_id}',
                }
            )
        )
        sys.exit(0)
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
        print(
            serialize_toon(
                {
                    'status': 'error',
                    'plan_id': plan_id,
                    'error': 'invalid_plan_id',
                    'message': f'Invalid plan_id format: {plan_id}',
                }
            )
        )
        sys.exit(0)

    target = base_path('plans', plan_id, *path_parts)
    if not target.exists():
        error_code = 'file_not_found' if path_parts else 'plan_not_found'
        file_desc = str(Path(*path_parts)) if path_parts else f'plan {plan_id}'
        print(
            serialize_toon(
                {
                    'status': 'error',
                    'plan_id': plan_id,
                    'error': error_code,
                    'message': f'Not found: {file_desc}',
                }
            )
        )
        sys.exit(0)

    return target


# --- Argparse builder helpers ---
# Reduce boilerplate for the --plan-id / --phase arguments repeated across 50+ subparsers.


def add_plan_id_arg(parser, required: bool = True) -> None:
    """Add the standard --plan-id argument to a parser or subparser.

    The argument is validated with the canonical PLAN_ID_RE (kebab-case)
    so malformed input is rejected at parse time. The ``type=`` validator
    cooperates with ``parse_args_with_toon_errors`` to emit the canonical
    ``status: error / error: invalid_plan_id`` TOON on stdout.
    """
    parser.add_argument(
        '--plan-id',
        required=required,
        type=validate_plan_id,
        help='Plan identifier (kebab-case)',
    )


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


def add_lesson_id_arg(parser, required: bool = True) -> None:
    """Add the standard --lesson-id argument to a parser or subparser."""
    parser.add_argument(
        '--lesson-id',
        required=required,
        type=validate_lesson_id,
        help='Lesson identifier (YYYY-MM-DD-HH-NNN)',
    )


def add_session_id_arg(parser, required: bool = True) -> None:
    """Add the standard --session-id argument to a parser or subparser."""
    parser.add_argument(
        '--session-id',
        required=required,
        type=validate_session_id,
        help='Claude Code session identifier',
    )


def _validate_task_number_int(raw: str) -> int:
    """Validator suitable for argparse ``type=`` that returns an ``int``.

    ``validate_task_number`` returns the original string for chaining, but
    every call site in the marketplace consumes ``args.task_number`` as an
    integer. Wrapping it here keeps the canonical regex check at the
    argparse boundary while preserving the pre-existing int contract.
    """
    validate_task_number(raw)
    return int(raw)


def add_task_number_arg(parser, required: bool = True) -> None:
    """Add the standard --task-number argument to a parser or subparser.

    The argument is validated with the canonical TASK_NUMBER_RE (non-negative
    integer string) and stored as ``int`` on the resulting Namespace.
    """
    parser.add_argument(
        '--task-number',
        required=required,
        type=_validate_task_number_int,
        help='Task number (non-negative integer)',
    )


def add_task_id_arg(parser, required: bool = True) -> None:
    """Add the standard --task-id argument to a parser or subparser."""
    parser.add_argument(
        '--task-id',
        required=required,
        type=validate_task_id,
        help='Task identifier (TASK-NNN)',
    )


def add_component_arg(parser, required: bool = True) -> None:
    """Add the standard --component argument to a parser or subparser."""
    parser.add_argument(
        '--component',
        required=required,
        type=validate_component,
        help='Component notation (bundle:skill[:script])',
    )


def add_hash_id_arg(parser, required: bool = True) -> None:
    """Add the standard --hash-id argument to a parser or subparser."""
    parser.add_argument(
        '--hash-id',
        required=required,
        type=validate_hash_id,
        help='Hash identifier (lowercase hex, >=4 chars)',
    )


def add_memory_id_arg(parser, required: bool = True) -> None:
    """Add the standard --memory-id argument to a parser or subparser."""
    parser.add_argument(
        '--memory-id',
        required=required,
        type=validate_memory_id,
        help='Memory identifier (lowercase letters/digits/_-)',
    )


def add_field_arg(parser, required: bool = True) -> None:
    """Add the standard --field argument to a parser or subparser."""
    parser.add_argument(
        '--field',
        required=required,
        type=validate_field_name,
        help='Field name (snake_case)',
    )


def add_module_arg(parser, required: bool = True) -> None:
    """Add the standard --module argument to a parser or subparser."""
    parser.add_argument(
        '--module',
        required=required,
        type=validate_module_name,
        help='Module name (kebab-or-snake)',
    )


def add_package_arg(parser, required: bool = True) -> None:
    """Add the standard --package argument to a parser or subparser."""
    parser.add_argument(
        '--package',
        required=required,
        type=validate_package_name,
        help='Package name (dotted snake_case)',
    )


def add_domain_arg(parser, required: bool = True) -> None:
    """Add the standard --domain argument to a parser or subparser."""
    parser.add_argument(
        '--domain',
        required=required,
        type=validate_domain_name,
        help='Domain name (kebab-case)',
    )


def add_name_arg(parser, required: bool = True) -> None:
    """Add the standard --name argument to a parser or subparser."""
    parser.add_argument(
        '--name',
        required=required,
        type=validate_resource_name,
        help='Resource name (alphanumeric + _-)',
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


def is_valid_lesson_id(lesson_id: str) -> bool:
    """Bool companion for validate_lesson_id."""
    try:
        validate_lesson_id(lesson_id)
        return True
    except ValueError:
        return False


def is_valid_session_id(session_id: str) -> bool:
    """Bool companion for validate_session_id."""
    try:
        validate_session_id(session_id)
        return True
    except ValueError:
        return False


def is_valid_task_number(task_number: str) -> bool:
    """Bool companion for validate_task_number."""
    try:
        validate_task_number(task_number)
        return True
    except ValueError:
        return False


def is_valid_task_id(task_id: str) -> bool:
    """Bool companion for validate_task_id."""
    try:
        validate_task_id(task_id)
        return True
    except ValueError:
        return False


def is_valid_component(component: str) -> bool:
    """Bool companion for validate_component."""
    try:
        validate_component(component)
        return True
    except ValueError:
        return False


def is_valid_hash_id(hash_id: str) -> bool:
    """Bool companion for validate_hash_id."""
    try:
        validate_hash_id(hash_id)
        return True
    except ValueError:
        return False


def is_valid_memory_id(memory_id: str) -> bool:
    """Bool companion for validate_memory_id."""
    try:
        validate_memory_id(memory_id)
        return True
    except ValueError:
        return False


def is_valid_phase_id(phase_id: str) -> bool:
    """Bool companion for validate_phase_id."""
    try:
        validate_phase_id(phase_id)
        return True
    except ValueError:
        return False


def is_valid_field_name(field_name: str) -> bool:
    """Bool companion for validate_field_name."""
    try:
        validate_field_name(field_name)
        return True
    except ValueError:
        return False


def is_valid_module_name(module_name: str) -> bool:
    """Bool companion for validate_module_name."""
    try:
        validate_module_name(module_name)
        return True
    except ValueError:
        return False


def is_valid_package_name(package_name: str) -> bool:
    """Bool companion for validate_package_name."""
    try:
        validate_package_name(package_name)
        return True
    except ValueError:
        return False


def is_valid_domain_name(domain_name: str) -> bool:
    """Bool companion for validate_domain_name."""
    try:
        validate_domain_name(domain_name)
        return True
    except ValueError:
        return False


def is_valid_resource_name(resource_name: str) -> bool:
    """Bool companion for validate_resource_name."""
    try:
        validate_resource_name(resource_name)
        return True
    except ValueError:
        return False


# --- Lesson-ID reference scanner (live-anchored) ---
#
# These helpers detect lesson-ID-shaped tokens in arbitrary text (typically
# task titles/descriptions) and verify them against the live
# ``manage-lessons`` inventory. They implement the runtime "live-anchor"
# discipline mandated by lesson 2026-04-29-10-001: the canonical
# ``LESSON_ID_RE`` shape MUST be re-asserted against actual repo data on
# first scanner use per process so a silent regex/ID-shape drift surfaces
# as a hard failure instead of producing a "no IDs match anything" false
# clean signal.
#
# Public surface:
#   - scan_lesson_id_tokens(text)               -> list[str]
#   - verify_lesson_ids_exist(tokens)           -> dict[str, bool]
#   - verify_lesson_id_regex_against_inventory()-> None  (raises on drift)
#
# Typed exceptions:
#   - LessonInventoryUnavailable: subprocess to manage-lessons failed; the
#       caller MUST treat this as a hard error (never silently degrade to
#       "all present").
#   - LessonRegexAnchoringError: live inventory has IDs but none match
#       LESSON_ID_RE — the regex shape has drifted from reality.

# Unanchored body of LESSON_ID_RE for embedded matching in prose. Derived
# from LESSON_ID_RE.pattern (single source of truth — no new regex literal
# is introduced) by stripping the ``^`` and ``$`` anchors. The token
# boundaries are enforced by the surrounding "no adjacent digit" lookbehinds
# below so we don't get partial matches like "12026-04-29-10-001".
_LESSON_ID_BODY = LESSON_ID_RE.pattern.lstrip('^').rstrip('$')
_LESSON_ID_EMBEDDED_RE = re.compile(r'(?<!\d)' + _LESSON_ID_BODY + r'(?!\d)')

# Per-process anchor-check cache. Set to True after the first successful
# (or no-op) anchor invocation so subsequent scanner calls don't re-spawn
# the manage-lessons subprocess.
_lesson_anchor_checked = False


class LessonInventoryUnavailable(RuntimeError):
    """Raised when ``manage-lessons list`` cannot be invoked or parsed.

    The caller MUST surface this — silently degrading to "all IDs present"
    would defeat the entire purpose of the reference scanner.
    """


class LessonRegexAnchoringError(RuntimeError):
    """Raised when the live inventory has IDs but none match LESSON_ID_RE.

    Indicates the canonical regex shape has drifted from the actual
    on-disk lesson-ID convention — a code/data integrity bug.
    """

    def __init__(self, regex: str, sample_ids: list[str]):
        self.regex = regex
        self.sample_ids = sample_ids
        super().__init__(
            f'LESSON_ID_RE ({regex!r}) does not match any of the {len(sample_ids)} '
            f'live lesson IDs (sample: {sample_ids[:3]!r}). The regex shape has '
            f'drifted from the live inventory — fix LESSON_ID_RE or correct the IDs.'
        )


def _list_live_lesson_ids() -> list[str]:
    """Invoke ``manage-lessons list`` and return every lesson ID in the inventory.

    Returns the raw ``id`` field from each row of the TOON ``lessons`` table,
    in inventory order. Raises ``LessonInventoryUnavailable`` if the
    subprocess fails to start, exits non-zero, or returns output that cannot
    be parsed as TOON.
    """
    import subprocess  # local import — keep module-import cost low for callers
    # that don't use the scanner.

    try:
        from toon_parser import parse_toon  # type: ignore[import-not-found]
    except ImportError as exc:
        raise LessonInventoryUnavailable(f'toon_parser is not importable: {exc}') from exc

    try:
        result = subprocess.run(
            [
                'python3',
                '.plan/execute-script.py',
                'plan-marshall:manage-lessons:manage-lessons',
                'list',
            ],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        raise LessonInventoryUnavailable(f'Failed to invoke manage-lessons list: {exc}') from exc

    if result.returncode != 0:
        raise LessonInventoryUnavailable(
            f'manage-lessons list exited {result.returncode}: {result.stderr.strip() or result.stdout.strip()!r}'
        )

    try:
        parsed = parse_toon(result.stdout)
    except Exception as exc:  # noqa: BLE001 — surface any parser failure
        raise LessonInventoryUnavailable(f'Failed to parse manage-lessons list output as TOON: {exc}') from exc

    rows = parsed.get('lessons')
    if rows is None:
        # Empty inventory or unexpected schema — return [] so the caller can
        # decide (anchor check treats this as no-op; existence check returns
        # all-False which is correct for an empty inventory).
        return []
    if not isinstance(rows, list):
        raise LessonInventoryUnavailable(f'manage-lessons list returned non-list lessons field: {type(rows).__name__}')

    ids: list[str] = []
    for row in rows:
        if isinstance(row, dict) and 'id' in row:
            ids.append(str(row['id']))
    return ids


def verify_lesson_id_regex_against_inventory() -> None:
    """Assert that LESSON_ID_RE matches at least one live lesson ID.

    Implements lesson 2026-04-29-10-001 at runtime: re-validates the
    canonical regex shape against actual repo data on first scanner use
    per process. Behavior:

    - Inventory empty → no-op (logged at WARNING via ``sys.stderr`` so
      the discrepancy is visible without making greenfield use a hard
      error). Marks the anchor as checked so we don't re-spawn the
      subprocess on every subsequent scanner call.
    - Inventory has IDs and at least one matches LESSON_ID_RE → success;
      caches the result for the rest of the process.
    - Inventory has IDs and NONE match LESSON_ID_RE → raises
      ``LessonRegexAnchoringError``. Does NOT cache so repeat invocations
      keep failing (the regex must be fixed).

    Re-raises ``LessonInventoryUnavailable`` from the underlying subprocess
    invocation; the caller decides whether to treat that as fatal (every
    documented call site here does).
    """
    global _lesson_anchor_checked
    if _lesson_anchor_checked:
        return

    ids = _list_live_lesson_ids()
    if not ids:
        # Greenfield repo or empty inventory — emit a one-time warning to
        # stderr so the live-anchor discipline is visible, then mark as
        # checked so we don't re-spawn for every scanner call.
        print(
            'WARNING: tools-input-validation lesson-ID anchor: live inventory '
            'is empty — anchor check is a no-op for this process.',
            file=sys.stderr,
        )
        _lesson_anchor_checked = True
        return

    matches = [lid for lid in ids if LESSON_ID_RE.match(lid)]
    if not matches:
        # Drift: live IDs exist but the regex matches none of them. Do NOT
        # cache — every scanner call should keep failing until the regex
        # (or the IDs) is corrected.
        raise LessonRegexAnchoringError(regex=LESSON_ID_RE.pattern, sample_ids=ids)

    _lesson_anchor_checked = True


def scan_lesson_id_tokens(text: str) -> list[str]:
    """Return every lesson-ID-shaped token embedded in ``text``.

    Matches the canonical 5-segment shape (``YYYY-MM-DD-HH-N+``) anywhere
    in the input — the embedded form uses non-digit boundaries so adjacent
    digits don't bleed into the match. Reuses the canonical
    ``LESSON_ID_RE`` body — no new regex literal is introduced.

    Triggers ``verify_lesson_id_regex_against_inventory()`` on first use
    per process; downstream callers MUST be prepared to handle
    ``LessonRegexAnchoringError`` and ``LessonInventoryUnavailable``.
    """
    verify_lesson_id_regex_against_inventory()
    if not text:
        return []
    return _LESSON_ID_EMBEDDED_RE.findall(text)


def verify_lesson_ids_exist(tokens) -> dict[str, bool]:
    """Return ``{token: present}`` for each token in ``tokens``.

    Looks up every token against the live ``manage-lessons list``
    inventory. Duplicates in the input are de-duplicated in the result.
    Raises ``LessonInventoryUnavailable`` when the subprocess fails —
    NEVER silently returns "all present", because that would defeat the
    entire purpose of the reference check.

    Triggers ``verify_lesson_id_regex_against_inventory()`` on first use
    per process; downstream callers MUST be prepared to handle
    ``LessonRegexAnchoringError`` and ``LessonInventoryUnavailable``.
    """
    verify_lesson_id_regex_against_inventory()

    unique = list({str(t) for t in tokens})
    if not unique:
        return {}

    inventory = set(_list_live_lesson_ids())
    return {token: token in inventory for token in unique}


# --- Argparse boundary helper: emit TOON errors for validator failures ---

# Map argument flag (--<id>) to canonical error code emitted on validation
# failure. Used by ``parse_args_with_toon_errors`` to translate argparse's
# default stderr-based error reporting into the TOON contract:
# ``status: error / error: invalid_<field>``.
_FLAG_TO_ERROR_CODE: dict[str, str] = {
    '--plan-id': 'invalid_plan_id',
    '--lesson-id': 'invalid_lesson_id',
    '--session-id': 'invalid_session_id',
    '--task-number': 'invalid_task_number',
    '--task-id': 'invalid_task_id',
    '--component': 'invalid_component',
    '--hash-id': 'invalid_hash_id',
    '--phase': 'invalid_phase',
    '--memory-id': 'invalid_memory_id',
    '--field': 'invalid_field',
    '--module': 'invalid_module',
    '--package': 'invalid_package',
    '--domain': 'invalid_domain',
    '--name': 'invalid_name',
}


def _iter_all_parsers(root):
    """Yield ``root`` plus every subparser registered (recursively).

    argparse subparsers are stored in their own ``ArgumentParser`` instances
    and have independent ``error`` methods. To intercept validator failures
    on subcommands, every subparser must also be patched.
    """
    yield root
    for action in getattr(root, '_actions', []):
        choices = getattr(action, 'choices', None)
        if isinstance(choices, dict):  # _SubParsersAction.choices is dict[str, ArgumentParser]
            for sub in choices.values():
                yield from _iter_all_parsers(sub)


def parse_args_with_toon_errors(parser):
    """Run ``parser.parse_args()`` and translate validator failures into TOON.

    When an argparse ``type=`` validator (e.g. ``validate_plan_id``) raises
    ``ValueError``, argparse converts the error into an ``ArgumentTypeError``
    and calls ``parser.error()``, which prints a stderr message and exits
    with code 2. That contract is incompatible with manage-* scripts, which
    must emit ``status: error / error: invalid_<field>`` TOON on stdout
    before any side-effects.

    This helper installs a one-shot ``parser.error`` override on the root
    parser AND every subparser registered under it. The override scans the
    formatted error message for any of the known identifier flags
    (``--plan-id``, ``--lesson-id``, …) and, when one matches, emits the
    canonical TOON error and exits with code 0. All other argparse errors
    (missing subcommand, unknown flag, etc.) fall through to the original
    behaviour.

    Returns the parsed ``argparse.Namespace`` on success.
    """
    from toon_parser import serialize_toon  # type: ignore[import-not-found]

    parsers = list(_iter_all_parsers(parser))
    originals = {id(p): p.error for p in parsers}

    def make_toon_error(orig):
        def toon_error(message: str):  # type: ignore[no-untyped-def]
            # argparse error messages for type-validator failures look like:
            #   "argument --plan-id: Invalid plan_id format: 'BAD!'. Must match ..."
            # We match only when the offending flag is the SUBJECT of the
            # error — i.e. the message starts with ``argument {flag}:``.
            # Generic argparse errors that incidentally mention a flag
            # (e.g. mutually-exclusive-group errors that name BOTH the
            # offending flag and another flag) must fall through to the
            # default handler so the contract is "this flag's value
            # failed canonical validation", not "any error mentioning
            # this flag".
            for flag, code in _FLAG_TO_ERROR_CODE.items():
                if message.startswith(f'argument {flag}:'):
                    print(
                        serialize_toon(
                            {
                                'status': 'error',
                                'error': code,
                                'message': message,
                            }
                        )
                    )
                    sys.exit(0)
            # Not an identifier-validator failure: defer to argparse default.
            orig(message)

        return toon_error

    for p in parsers:
        p.error = make_toon_error(originals[id(p)])  # type: ignore[method-assign]
    try:
        return parser.parse_args()
    finally:
        for p in parsers:
            p.error = originals[id(p)]  # type: ignore[method-assign]

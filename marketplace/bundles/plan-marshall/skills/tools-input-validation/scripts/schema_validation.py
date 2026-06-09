"""Schema validation for plan-marshall storage files.

Provides lightweight, field-constrained validation for JSON structures used
across skills. No external dependencies — uses Python stdlib only.

Beyond the original type-presence checks, the validators enforce four
additional constraint classes, each implemented by a small private helper that
mirrors the ``_check_field`` signature so the module stays stdlib-only:

- ``_check_no_extra_keys`` — ``additionalProperties: false`` semantics: reject
  any key not in the declared allowed-key set for a structure.
- ``_check_max_length`` — ``maxLength`` on string content fields.
- ``_check_max_items`` — ``maxItems`` on array fields.
- ``_check_enum`` — membership in a fixed value set.
- ``_check_pattern`` — match against a fixed regex shape.

Usage:
    from schema_validation import validate_status, validate_references, validate_task

    errors = validate_status(data)
    if errors:
        output_error('schema_violation', '; '.join(errors))
"""

import re
from typing import Any

# --- Constraint constants -------------------------------------------------
# Length caps for free-form string content fields. Generous enough that no
# legitimate value is rejected, tight enough to reject obviously malformed or
# adversarial payloads (e.g. an unbounded title injected into a stored record).
MAX_TITLE_LENGTH = 512
MAX_PLAN_ID_LENGTH = 128
MAX_PHASE_NAME_LENGTH = 64
MAX_STATUS_VALUE_LENGTH = 64
MAX_MESSAGE_LENGTH = 4096
MAX_FILE_PATH_LENGTH = 1024
MAX_HASH_ID_LENGTH = 128
MAX_TYPE_LENGTH = 64
MAX_SEVERITY_LENGTH = 32

# Item-count caps for array fields. A plan has at most six phases; a task's
# step list is bounded well below this cap in practice.
MAX_PHASES_ITEMS = 64
MAX_STEPS_ITEMS = 256

# Fixed-shape fields. Phase names follow ``{1-6}-{slug}`` (e.g. ``5-execute``);
# phase and task status values are drawn from a closed lifecycle vocabulary.
PHASE_NAME_RE = re.compile(r'^[1-6]-(init|refine|outline|plan|execute|finalize)$')
PHASE_STATUS_VALUES = ('pending', 'in_progress', 'done', 'blocked', 'completed', 'skipped')
TASK_STATUS_VALUES = ('pending', 'in_progress', 'done', 'blocked', 'failed', 'completed')

# Allowed-key sets per structure (``additionalProperties: false``). Each set is
# the union of the required fields and the known-optional fields that legitimate
# on-disk records carry, so tightening to strict-extra-keys does not reject any
# valid structure.
STATUS_ALLOWED_KEYS = frozenset({
    'plan_id', 'current_phase', 'phases',
    'title', 'short_description', 'created', 'updated', 'metadata',
})
REFERENCES_ALLOWED_KEYS = frozenset({
    'plan_id',
    'branch', 'base_branch', 'domains', 'scope_estimate', 'track',
    'affected_files', 'worktree_path',
})
TASK_ALLOWED_KEYS = frozenset({
    'task_id', 'title', 'status', 'steps',
    'number', 'domain', 'profile', 'skills', 'origin', 'deliverable',
    'depends_on', 'description', 'current_step', 'verification', 'metadata',
})
STEP_ALLOWED_KEYS = frozenset({
    'id', 'title',
    'number', 'target', 'status', 'intent', 'outcome',
})


def _check_field(data: dict, field: str, expected_type: type | tuple[type, ...], required: bool = True) -> list[str]:
    """Check a single field exists and has the correct type."""
    errors = []
    if field not in data:
        if required:
            errors.append(f"Missing required field: '{field}'")
    elif not isinstance(data[field], expected_type):
        if isinstance(expected_type, tuple):
            type_name = '/'.join(t.__name__ for t in expected_type)
        else:
            type_name = expected_type.__name__
        errors.append(f"Field '{field}' should be {type_name}, got {type(data[field]).__name__}")
    return errors


def _check_no_extra_keys(data: dict, allowed: frozenset[str], label: str) -> list[str]:
    """Reject any key not in the allowed set (``additionalProperties: false``)."""
    errors = []
    for key in sorted(k for k in data if k not in allowed):
        errors.append(f"Unexpected field in {label}: '{key}'")
    return errors


def _check_max_length(data: dict, field: str, max_length: int) -> list[str]:
    """Reject a present string field whose length exceeds ``max_length``."""
    value = data.get(field)
    if isinstance(value, str) and len(value) > max_length:
        return [f"Field '{field}' exceeds max length {max_length} (got {len(value)})"]
    return []


def _check_max_items(data: dict, field: str, max_items: int) -> list[str]:
    """Reject a present list field whose length exceeds ``max_items``."""
    value = data.get(field)
    if isinstance(value, list) and len(value) > max_items:
        return [f"Field '{field}' exceeds max items {max_items} (got {len(value)})"]
    return []


def _check_enum(data: dict, field: str, allowed: tuple[str, ...]) -> list[str]:
    """Reject a present string field whose value is not in ``allowed``."""
    value = data.get(field)
    if isinstance(value, str) and value not in allowed:
        return [f"Field '{field}' must be one of {'/'.join(allowed)}, got '{value}'"]
    return []


def _check_pattern(data: dict, field: str, pattern: re.Pattern[str]) -> list[str]:
    """Reject a present string field that does not match ``pattern``."""
    value = data.get(field)
    if isinstance(value, str) and not pattern.match(value):
        return [f"Field '{field}' does not match required pattern {pattern.pattern}, got '{value}'"]
    return []


def validate_status(data: Any) -> list[str]:
    """Validate status.json structure."""
    if not isinstance(data, dict):
        return ['status.json must be a JSON object']
    errors = []
    errors.extend(_check_no_extra_keys(data, STATUS_ALLOWED_KEYS, 'status.json'))
    errors.extend(_check_field(data, 'plan_id', str))
    errors.extend(_check_field(data, 'current_phase', str))
    errors.extend(_check_field(data, 'phases', list))
    errors.extend(_check_max_length(data, 'plan_id', MAX_PLAN_ID_LENGTH))
    errors.extend(_check_max_items(data, 'phases', MAX_PHASES_ITEMS))
    if 'phases' in data and isinstance(data['phases'], list):
        for i, phase in enumerate(data['phases']):
            if not isinstance(phase, dict):
                errors.append(f'phases[{i}] must be a dict')
                continue
            errors.extend(_check_field(phase, 'name', str))
            errors.extend(_check_field(phase, 'status', str))
            errors.extend(_check_max_length(phase, 'name', MAX_PHASE_NAME_LENGTH))
            errors.extend(_check_pattern(phase, 'name', PHASE_NAME_RE))
            errors.extend(_check_enum(phase, 'status', PHASE_STATUS_VALUES))
    return errors


def validate_references(data: Any) -> list[str]:
    """Validate references.json structure."""
    if not isinstance(data, dict):
        return ['references.json must be a JSON object']
    errors = []
    errors.extend(_check_no_extra_keys(data, REFERENCES_ALLOWED_KEYS, 'references.json'))
    errors.extend(_check_field(data, 'plan_id', str))
    errors.extend(_check_max_length(data, 'plan_id', MAX_PLAN_ID_LENGTH))
    return errors


def validate_task(data: Any) -> list[str]:
    """Validate TASK-*.json structure."""
    if not isinstance(data, dict):
        return ['Task file must be a JSON object']
    errors = []
    errors.extend(_check_no_extra_keys(data, TASK_ALLOWED_KEYS, 'task'))
    errors.extend(_check_field(data, 'task_id', str))
    errors.extend(_check_field(data, 'title', str))
    errors.extend(_check_field(data, 'status', str))
    errors.extend(_check_field(data, 'steps', list))
    errors.extend(_check_max_length(data, 'title', MAX_TITLE_LENGTH))
    errors.extend(_check_enum(data, 'status', TASK_STATUS_VALUES))
    errors.extend(_check_max_items(data, 'steps', MAX_STEPS_ITEMS))
    if 'steps' in data and isinstance(data['steps'], list):
        for i, step in enumerate(data['steps']):
            if not isinstance(step, dict):
                errors.append(f'steps[{i}] must be a dict')
                continue
            errors.extend(_check_no_extra_keys(step, STEP_ALLOWED_KEYS, f'steps[{i}]'))
            errors.extend(_check_field(step, 'id', str))
            errors.extend(_check_field(step, 'title', str))
            errors.extend(_check_max_length(step, 'title', MAX_TITLE_LENGTH))
    return errors


def validate_assessment(data: Any) -> list[str]:
    """Validate a single assessment record."""
    if not isinstance(data, dict):
        return ['Assessment must be a JSON object']
    errors = []
    errors.extend(_check_field(data, 'hash_id', str))
    errors.extend(_check_field(data, 'file_path', str))
    errors.extend(_check_field(data, 'certainty', str))
    errors.extend(_check_field(data, 'confidence', (int, float)))
    errors.extend(_check_max_length(data, 'hash_id', MAX_HASH_ID_LENGTH))
    errors.extend(_check_max_length(data, 'file_path', MAX_FILE_PATH_LENGTH))
    if 'certainty' in data and data['certainty'] not in ('CERTAIN_INCLUDE', 'CERTAIN_EXCLUDE', 'UNCERTAIN'):
        errors.append(f"Invalid certainty: '{data['certainty']}'")
    return errors


def validate_finding(data: Any) -> list[str]:
    """Validate a single finding record."""
    if not isinstance(data, dict):
        return ['Finding must be a JSON object']
    errors = []
    errors.extend(_check_field(data, 'hash_id', str))
    errors.extend(_check_field(data, 'type', str))
    errors.extend(_check_field(data, 'severity', str))
    errors.extend(_check_field(data, 'message', str))
    errors.extend(_check_max_length(data, 'hash_id', MAX_HASH_ID_LENGTH))
    errors.extend(_check_max_length(data, 'type', MAX_TYPE_LENGTH))
    errors.extend(_check_max_length(data, 'severity', MAX_SEVERITY_LENGTH))
    errors.extend(_check_max_length(data, 'message', MAX_MESSAGE_LENGTH))
    return errors

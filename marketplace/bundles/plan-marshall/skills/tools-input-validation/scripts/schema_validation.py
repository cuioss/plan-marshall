"""Schema validation for plan-marshall storage files.

Provides lightweight validation for JSON structures used across skills.
No external dependencies — uses Python stdlib only.

Usage:
    from schema_validation import validate_status, validate_references, validate_task

    errors = validate_status(data)
    if errors:
        output_error('schema_violation', '; '.join(errors))
"""

from typing import Any


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


def validate_status(data: Any) -> list[str]:
    """Validate status.json structure."""
    if not isinstance(data, dict):
        return ['status.json must be a JSON object']
    errors = []
    errors.extend(_check_field(data, 'plan_id', str))
    errors.extend(_check_field(data, 'current_phase', str))
    errors.extend(_check_field(data, 'phases', list))
    if 'phases' in data and isinstance(data['phases'], list):
        for i, phase in enumerate(data['phases']):
            if not isinstance(phase, dict):
                errors.append(f'phases[{i}] must be a dict')
                continue
            errors.extend(_check_field(phase, 'name', str))
            errors.extend(_check_field(phase, 'status', str))
    return errors


def validate_references(data: Any) -> list[str]:
    """Validate references.json structure."""
    if not isinstance(data, dict):
        return ['references.json must be a JSON object']
    errors = []
    errors.extend(_check_field(data, 'plan_id', str))
    return errors


def validate_task(data: Any) -> list[str]:
    """Validate TASK-*.json structure."""
    if not isinstance(data, dict):
        return ['Task file must be a JSON object']
    errors = []
    errors.extend(_check_field(data, 'task_id', str))
    errors.extend(_check_field(data, 'title', str))
    errors.extend(_check_field(data, 'status', str))
    errors.extend(_check_field(data, 'steps', list))
    if 'steps' in data and isinstance(data['steps'], list):
        for i, step in enumerate(data['steps']):
            if not isinstance(step, dict):
                errors.append(f'steps[{i}] must be a dict')
                continue
            errors.extend(_check_field(step, 'id', str))
            errors.extend(_check_field(step, 'title', str))
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
    return errors

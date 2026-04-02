#!/usr/bin/env python3
"""Tests for schema_validation.py shared module."""

import sys
from pathlib import Path

import pytest

# Import shared infrastructure — triggers PYTHONPATH setup for cross-skill imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from schema_validation import (  # type: ignore[import-not-found]  # noqa: E402, I001
    validate_assessment,
    validate_finding,
    validate_references,
    validate_status,
    validate_task,
)


# =============================================================================
# Test: validate_status
# =============================================================================


class TestValidateStatus:
    """Tests for status.json validation."""

    def test_valid_minimal(self):
        data = {
            'plan_id': 'my-plan',
            'current_phase': 'phase-1-init',
            'phases': [
                {'name': 'phase-1-init', 'status': 'completed'},
            ],
        }
        assert validate_status(data) == []

    def test_not_a_dict(self):
        errors = validate_status([1, 2, 3])
        assert errors == ['status.json must be a JSON object']

    def test_missing_plan_id(self):
        data = {'current_phase': 'phase-1-init', 'phases': []}
        errors = validate_status(data)
        assert "Missing required field: 'plan_id'" in errors

    def test_missing_current_phase(self):
        data = {'plan_id': 'p', 'phases': []}
        errors = validate_status(data)
        assert "Missing required field: 'current_phase'" in errors

    def test_missing_phases(self):
        data = {'plan_id': 'p', 'current_phase': 'x'}
        errors = validate_status(data)
        assert "Missing required field: 'phases'" in errors

    def test_wrong_type_plan_id(self):
        data = {'plan_id': 123, 'current_phase': 'x', 'phases': []}
        errors = validate_status(data)
        assert "Field 'plan_id' should be str, got int" in errors

    def test_wrong_type_phases(self):
        data = {'plan_id': 'p', 'current_phase': 'x', 'phases': 'not-a-list'}
        errors = validate_status(data)
        assert "Field 'phases' should be list, got str" in errors

    def test_invalid_phase_entry(self):
        data = {
            'plan_id': 'p',
            'current_phase': 'x',
            'phases': ['not-a-dict'],
        }
        errors = validate_status(data)
        assert 'phases[0] must be a dict' in errors

    def test_phase_missing_fields(self):
        data = {
            'plan_id': 'p',
            'current_phase': 'x',
            'phases': [{'name': 'init'}],
        }
        errors = validate_status(data)
        assert "Missing required field: 'status'" in errors


# =============================================================================
# Test: validate_references
# =============================================================================


class TestValidateReferences:
    """Tests for references.json validation."""

    def test_valid_minimal(self):
        assert validate_references({'plan_id': 'my-plan'}) == []

    def test_not_a_dict(self):
        errors = validate_references('string')
        assert errors == ['references.json must be a JSON object']

    def test_missing_plan_id(self):
        errors = validate_references({})
        assert "Missing required field: 'plan_id'" in errors

    def test_wrong_type_plan_id(self):
        errors = validate_references({'plan_id': None})
        assert "Field 'plan_id' should be str, got NoneType" in errors


# =============================================================================
# Test: validate_task
# =============================================================================


class TestValidateTask:
    """Tests for TASK-*.json validation."""

    def test_valid_minimal(self):
        data = {
            'task_id': 'TASK-001',
            'title': 'Implement feature',
            'status': 'pending',
            'steps': [
                {'id': 'step-1', 'title': 'Write code'},
            ],
        }
        assert validate_task(data) == []

    def test_not_a_dict(self):
        errors = validate_task(42)
        assert errors == ['Task file must be a JSON object']

    def test_missing_all_required(self):
        errors = validate_task({})
        assert len(errors) == 4
        assert "Missing required field: 'task_id'" in errors
        assert "Missing required field: 'title'" in errors
        assert "Missing required field: 'status'" in errors
        assert "Missing required field: 'steps'" in errors

    def test_invalid_step_entry(self):
        data = {
            'task_id': 'T1',
            'title': 'T',
            'status': 'pending',
            'steps': [99],
        }
        errors = validate_task(data)
        assert 'steps[0] must be a dict' in errors

    def test_step_missing_fields(self):
        data = {
            'task_id': 'T1',
            'title': 'T',
            'status': 'pending',
            'steps': [{'id': 's1'}],
        }
        errors = validate_task(data)
        assert "Missing required field: 'title'" in errors

    def test_extra_fields_ignored(self):
        """Extra fields should not cause errors."""
        data = {
            'task_id': 'T1',
            'title': 'T',
            'status': 'pending',
            'steps': [],
            'extra_stuff': True,
        }
        assert validate_task(data) == []


# =============================================================================
# Test: validate_assessment
# =============================================================================


class TestValidateAssessment:
    """Tests for assessment record validation."""

    def test_valid(self):
        data = {
            'hash_id': 'abc123',
            'file_path': 'src/Main.java',
            'certainty': 'CERTAIN_INCLUDE',
            'confidence': 0.95,
        }
        assert validate_assessment(data) == []

    def test_not_a_dict(self):
        errors = validate_assessment(None)
        assert errors == ['Assessment must be a JSON object']

    def test_missing_fields(self):
        errors = validate_assessment({})
        assert len(errors) == 4

    def test_invalid_certainty_value(self):
        data = {
            'hash_id': 'abc',
            'file_path': 'f.py',
            'certainty': 'MAYBE',
            'confidence': 0.5,
        }
        errors = validate_assessment(data)
        assert "Invalid certainty: 'MAYBE'" in errors

    def test_confidence_as_int(self):
        """Integer confidence values are valid."""
        data = {
            'hash_id': 'abc',
            'file_path': 'f.py',
            'certainty': 'UNCERTAIN',
            'confidence': 1,
        }
        assert validate_assessment(data) == []

    def test_wrong_type_confidence(self):
        data = {
            'hash_id': 'abc',
            'file_path': 'f.py',
            'certainty': 'UNCERTAIN',
            'confidence': 'high',
        }
        errors = validate_assessment(data)
        assert any('confidence' in e for e in errors)


# =============================================================================
# Test: validate_finding
# =============================================================================


class TestValidateFinding:
    """Tests for finding record validation."""

    def test_valid(self):
        data = {
            'hash_id': 'def456',
            'type': 'sonar',
            'severity': 'MAJOR',
            'message': 'Unused import',
        }
        assert validate_finding(data) == []

    def test_not_a_dict(self):
        errors = validate_finding([])
        assert errors == ['Finding must be a JSON object']

    def test_missing_all_fields(self):
        errors = validate_finding({})
        assert len(errors) == 4
        assert "Missing required field: 'hash_id'" in errors
        assert "Missing required field: 'type'" in errors
        assert "Missing required field: 'severity'" in errors
        assert "Missing required field: 'message'" in errors

    def test_wrong_type(self):
        data = {
            'hash_id': 123,
            'type': 'sonar',
            'severity': 'MAJOR',
            'message': 'msg',
        }
        errors = validate_finding(data)
        assert "Field 'hash_id' should be str, got int" in errors

#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for schema_validation.py shared module."""

from schema_validation import (  # type: ignore[import-not-found]  # noqa: I001
    MAX_MESSAGE_LENGTH,
    MAX_PHASES_ITEMS,
    MAX_PLAN_ID_LENGTH,
    MAX_STEPS_ITEMS,
    MAX_TITLE_LENGTH,
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
                {'name': '1-init', 'status': 'completed'},
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
            'phases': [{'name': '1-init'}],
        }
        errors = validate_status(data)
        assert "Missing required field: 'status'" in errors

    # --- New constraint coverage: additionalProperties: false ----------------

    def test_extra_top_level_key_rejected(self):
        """A key outside STATUS_ALLOWED_KEYS is rejected (additionalProperties: false)."""
        data = {
            'plan_id': 'p',
            'current_phase': '1-init',
            'phases': [],
            'unexpected_key': 'value',
        }
        errors = validate_status(data)
        assert "Unexpected field in status.json: 'unexpected_key'" in errors

    def test_known_optional_keys_allowed(self):
        """Known-optional keys (title, metadata, ...) do not trip the extra-key gate."""
        data = {
            'plan_id': 'p',
            'current_phase': '1-init',
            'phases': [{'name': '1-init', 'status': 'pending'}],
            'title': 'My plan',
            'short_description': 'desc',
            'created': '2026-01-01',
            'updated': '2026-01-02',
            'metadata': {'use_worktree': True},
        }
        assert validate_status(data) == []

    # --- New constraint coverage: maxLength ----------------------------------

    def test_plan_id_exceeds_max_length(self):
        data = {
            'plan_id': 'p' * (MAX_PLAN_ID_LENGTH + 1),
            'current_phase': '1-init',
            'phases': [],
        }
        errors = validate_status(data)
        assert any('plan_id' in e and 'max length' in e for e in errors)

    def test_plan_id_at_max_length_ok(self):
        data = {
            'plan_id': 'p' * MAX_PLAN_ID_LENGTH,
            'current_phase': '1-init',
            'phases': [],
        }
        assert validate_status(data) == []

    # --- New constraint coverage: maxItems -----------------------------------

    def test_phases_exceeds_max_items(self):
        data = {
            'plan_id': 'p',
            'current_phase': '1-init',
            'phases': [{'name': '1-init', 'status': 'pending'}] * (MAX_PHASES_ITEMS + 1),
        }
        errors = validate_status(data)
        assert any('phases' in e and 'max items' in e for e in errors)

    # --- New constraint coverage: enum (phase status) ------------------------

    def test_phase_status_invalid_enum(self):
        data = {
            'plan_id': 'p',
            'current_phase': '1-init',
            'phases': [{'name': '1-init', 'status': 'bogus'}],
        }
        errors = validate_status(data)
        assert any("Field 'status' must be one of" in e for e in errors)

    def test_phase_status_valid_enum_values(self):
        for value in ('pending', 'in_progress', 'done', 'blocked', 'completed', 'skipped'):
            data = {
                'plan_id': 'p',
                'current_phase': '1-init',
                'phases': [{'name': '1-init', 'status': value}],
            }
            assert validate_status(data) == []

    # --- New constraint coverage: pattern (phase name) -----------------------

    def test_phase_name_invalid_pattern(self):
        data = {
            'plan_id': 'p',
            'current_phase': '1-init',
            'phases': [{'name': 'init', 'status': 'pending'}],
        }
        errors = validate_status(data)
        assert any("Field 'name' does not match required pattern" in e for e in errors)

    def test_phase_name_valid_pattern_values(self):
        for value in ('1-init', '2-refine', '3-outline', '4-plan', '5-execute', '6-finalize'):
            data = {
                'plan_id': 'p',
                'current_phase': value,
                'phases': [{'name': value, 'status': 'pending'}],
            }
            assert validate_status(data) == []


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

    # --- New constraint coverage --------------------------------------------

    def test_extra_key_rejected(self):
        errors = validate_references({'plan_id': 'p', 'nope': 1})
        assert "Unexpected field in references.json: 'nope'" in errors

    def test_known_optional_keys_allowed(self):
        data = {
            'plan_id': 'p',
            'branch': 'feature/p',
            'base_branch': 'main',
            'domains': ['plan-marshall'],
            'scope_estimate': 'small',
            'track': 'standard',
            'affected_files': ['a.py'],
            'worktree_path': '/tmp/wt',
        }
        assert validate_references(data) == []

    def test_plan_id_exceeds_max_length(self):
        errors = validate_references({'plan_id': 'p' * (MAX_PLAN_ID_LENGTH + 1)})
        assert any('plan_id' in e and 'max length' in e for e in errors)


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

    # --- New constraint coverage: additionalProperties: false ----------------

    def test_extra_top_level_key_rejected(self):
        """Extra top-level keys are now rejected (additionalProperties: false)."""
        data = {
            'task_id': 'T1',
            'title': 'T',
            'status': 'pending',
            'steps': [],
            'extra_stuff': True,
        }
        errors = validate_task(data)
        assert "Unexpected field in task: 'extra_stuff'" in errors

    def test_known_optional_keys_allowed(self):
        """Known-optional task keys do not trip the extra-key gate."""
        data = {
            'task_id': 'T1',
            'title': 'T',
            'status': 'pending',
            'steps': [
                {'id': 's1', 'title': 'Step', 'number': 1, 'target': 'a.py',
                 'status': 'pending', 'intent': 'write', 'outcome': 'done'},
            ],
            'number': 1,
            'domain': 'plan-marshall',
            'profile': 'implementation',
            'skills': ['s'],
            'origin': 'plan',
            'deliverable': 1,
            'depends_on': [],
            'description': 'd',
            'current_step': 1,
            'verification': {},
            'metadata': {},
        }
        assert validate_task(data) == []

    def test_extra_step_key_rejected(self):
        """Extra keys inside a step are rejected (additionalProperties: false)."""
        data = {
            'task_id': 'T1',
            'title': 'T',
            'status': 'pending',
            'steps': [{'id': 's1', 'title': 'Step', 'rogue': 1}],
        }
        errors = validate_task(data)
        assert "Unexpected field in steps[0]: 'rogue'" in errors

    # --- New constraint coverage: maxLength ----------------------------------

    def test_title_exceeds_max_length(self):
        data = {
            'task_id': 'T1',
            'title': 't' * (MAX_TITLE_LENGTH + 1),
            'status': 'pending',
            'steps': [],
        }
        errors = validate_task(data)
        assert any("Field 'title'" in e and 'max length' in e for e in errors)

    def test_step_title_exceeds_max_length(self):
        data = {
            'task_id': 'T1',
            'title': 'T',
            'status': 'pending',
            'steps': [{'id': 's1', 'title': 't' * (MAX_TITLE_LENGTH + 1)}],
        }
        errors = validate_task(data)
        assert any("Field 'title'" in e and 'max length' in e for e in errors)

    # --- New constraint coverage: maxItems -----------------------------------

    def test_steps_exceeds_max_items(self):
        data = {
            'task_id': 'T1',
            'title': 'T',
            'status': 'pending',
            'steps': [{'id': 's', 'title': 't'}] * (MAX_STEPS_ITEMS + 1),
        }
        errors = validate_task(data)
        assert any("Field 'steps'" in e and 'max items' in e for e in errors)

    # --- New constraint coverage: enum (task status) -------------------------

    def test_status_invalid_enum(self):
        data = {
            'task_id': 'T1',
            'title': 'T',
            'status': 'bogus',
            'steps': [],
        }
        errors = validate_task(data)
        assert any("Field 'status' must be one of" in e for e in errors)

    def test_status_valid_enum_values(self):
        for value in ('pending', 'in_progress', 'done', 'blocked', 'failed', 'completed'):
            data = {
                'task_id': 'T1',
                'title': 'T',
                'status': value,
                'steps': [],
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

    # --- New constraint coverage: maxLength ----------------------------------

    def test_message_exceeds_max_length(self):
        data = {
            'hash_id': 'h',
            'type': 'sonar',
            'severity': 'MAJOR',
            'message': 'm' * (MAX_MESSAGE_LENGTH + 1),
        }
        errors = validate_finding(data)
        assert any("Field 'message'" in e and 'max length' in e for e in errors)

    def test_message_at_max_length_ok(self):
        data = {
            'hash_id': 'h',
            'type': 'sonar',
            'severity': 'MAJOR',
            'message': 'm' * MAX_MESSAGE_LENGTH,
        }
        assert validate_finding(data) == []

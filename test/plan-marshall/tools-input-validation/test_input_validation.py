#!/usr/bin/env python3
"""Tests for input_validation.py shared module."""

import pytest
from input_validation import (  # type: ignore[import-not-found]I001
    is_valid_component,
    is_valid_domain_name,
    is_valid_field_name,
    is_valid_hash_id,
    is_valid_lesson_id,
    is_valid_module_name,
    is_valid_package_name,
    is_valid_phase_id,
    is_valid_plan_id,
    is_valid_relative_path,
    is_valid_resource_name,
    is_valid_session_id,
    is_valid_task_id,
    is_valid_task_number,
    validate_component,
    validate_domain_name,
    validate_enum,
    validate_field_name,
    validate_hash_id,
    validate_lesson_id,
    validate_module_name,
    validate_package_name,
    validate_phase_id,
    validate_plan_id,
    validate_relative_path,
    validate_resource_name,
    validate_script_notation,
    validate_session_id,
    validate_skill_notation,
    validate_task_id,
    validate_task_number,
)

# =============================================================================
# Test: validate_plan_id / is_valid_plan_id
# =============================================================================


class TestValidatePlanId:
    """Tests for plan_id validation."""

    def test_valid_simple(self):
        assert validate_plan_id('my-plan') == 'my-plan'

    def test_valid_with_digits(self):
        assert validate_plan_id('plan123') == 'plan123'

    def test_valid_single_letter(self):
        assert validate_plan_id('a') == 'a'

    def test_valid_long_kebab(self):
        assert validate_plan_id('my-long-plan-name-42') == 'my-long-plan-name-42'

    def test_invalid_empty(self):
        with pytest.raises(ValueError, match='Invalid plan_id'):
            validate_plan_id('')

    def test_invalid_starts_with_digit(self):
        with pytest.raises(ValueError, match='Invalid plan_id'):
            validate_plan_id('1plan')

    def test_invalid_starts_with_hyphen(self):
        with pytest.raises(ValueError, match='Invalid plan_id'):
            validate_plan_id('-plan')

    def test_invalid_uppercase(self):
        with pytest.raises(ValueError, match='Invalid plan_id'):
            validate_plan_id('MyPlan')

    def test_invalid_underscore(self):
        with pytest.raises(ValueError, match='Invalid plan_id'):
            validate_plan_id('my_plan')

    def test_invalid_dot(self):
        with pytest.raises(ValueError, match='Invalid plan_id'):
            validate_plan_id('my.plan')

    def test_invalid_slash(self):
        with pytest.raises(ValueError, match='Invalid plan_id'):
            validate_plan_id('my/plan')

    def test_invalid_traversal(self):
        with pytest.raises(ValueError, match='Invalid plan_id'):
            validate_plan_id('../traversal')

    def test_invalid_space(self):
        with pytest.raises(ValueError, match='Invalid plan_id'):
            validate_plan_id('my plan')

    def test_invalid_unicode(self):
        with pytest.raises(ValueError, match='Invalid plan_id'):
            validate_plan_id('plän')

    def test_bool_valid(self):
        assert is_valid_plan_id('my-plan') is True

    def test_bool_invalid(self):
        assert is_valid_plan_id('../traversal') is False

    def test_bool_empty(self):
        assert is_valid_plan_id('') is False


# =============================================================================
# Test: validate_relative_path / is_valid_relative_path
# =============================================================================


class TestValidateRelativePath:
    """Tests for relative path validation."""

    def test_valid_simple(self):
        assert validate_relative_path('file.txt') == 'file.txt'

    def test_valid_nested(self):
        assert validate_relative_path('dir/subdir/file.txt') == 'dir/subdir/file.txt'

    def test_valid_dotfile(self):
        assert validate_relative_path('.gitignore') == '.gitignore'

    def test_valid_current_dir(self):
        assert validate_relative_path('./file.txt') == './file.txt'

    def test_invalid_empty(self):
        with pytest.raises(ValueError, match='must not be empty'):
            validate_relative_path('')

    def test_invalid_absolute(self):
        with pytest.raises(ValueError, match='Absolute paths not allowed'):
            validate_relative_path('/etc/passwd')

    def test_invalid_traversal_simple(self):
        with pytest.raises(ValueError, match='Path traversal not allowed'):
            validate_relative_path('../secret')

    def test_invalid_traversal_nested(self):
        with pytest.raises(ValueError, match='Path traversal not allowed'):
            validate_relative_path('sub/../../../etc/passwd')

    def test_invalid_traversal_mid_path(self):
        with pytest.raises(ValueError, match='Path traversal not allowed'):
            validate_relative_path('a/b/../../c')

    def test_invalid_traversal_backslash(self):
        with pytest.raises(ValueError, match='Path traversal not allowed'):
            validate_relative_path('sub\\..\\..\\etc')

    def test_valid_double_dot_in_filename(self):
        """Filenames containing '..' as part of the name (not a component) should still be caught."""
        # '..' as a path component is always rejected
        with pytest.raises(ValueError, match='Path traversal not allowed'):
            validate_relative_path('dir/../file')

    def test_bool_valid(self):
        assert is_valid_relative_path('dir/file.txt') is True

    def test_bool_invalid(self):
        assert is_valid_relative_path('../traversal') is False

    def test_bool_empty(self):
        assert is_valid_relative_path('') is False


# =============================================================================
# Test: validate_enum
# =============================================================================


class TestValidateEnum:
    """Tests for enum validation."""

    def test_valid(self):
        assert validate_enum('pending', ['pending', 'done', 'blocked'], 'status') == 'pending'

    def test_valid_last(self):
        assert validate_enum('blocked', ['pending', 'done', 'blocked'], 'status') == 'blocked'

    def test_invalid(self):
        with pytest.raises(ValueError, match='Invalid status'):
            validate_enum('unknown', ['pending', 'done', 'blocked'], 'status')

    def test_invalid_empty_value(self):
        with pytest.raises(ValueError, match='Invalid phase'):
            validate_enum('', ['init', 'execute'], 'phase')

    def test_case_sensitive(self):
        with pytest.raises(ValueError, match='Invalid status'):
            validate_enum('Pending', ['pending', 'done'], 'status')


# =============================================================================
# Test: validate_skill_notation
# =============================================================================


class TestValidateSkillNotation:
    """Tests for skill notation validation."""

    def test_valid(self):
        assert validate_skill_notation('plan-marshall:manage-files') == 'plan-marshall:manage-files'

    def test_valid_plugin(self):
        assert validate_skill_notation('pm-dev-java:java-core') == 'pm-dev-java:java-core'

    def test_invalid_no_colon(self):
        with pytest.raises(ValueError, match='Invalid skill notation'):
            validate_skill_notation('plan-marshall')

    def test_invalid_empty(self):
        with pytest.raises(ValueError, match='Invalid skill notation'):
            validate_skill_notation('')

    def test_invalid_empty_bundle(self):
        with pytest.raises(ValueError, match='Invalid skill notation'):
            validate_skill_notation(':manage-files')

    def test_invalid_empty_skill(self):
        with pytest.raises(ValueError, match='Invalid skill notation'):
            validate_skill_notation('plan-marshall:')

    def test_invalid_too_many_colons(self):
        with pytest.raises(ValueError, match='Invalid skill notation'):
            validate_skill_notation('a:b:c')


# =============================================================================
# Test: validate_script_notation
# =============================================================================


class TestValidateScriptNotation:
    """Tests for script notation validation (3-part bundle:skill:script)."""

    def test_valid(self):
        assert (
            validate_script_notation('plan-marshall:manage-files:manage-files')
            == 'plan-marshall:manage-files:manage-files'
        )

    def test_valid_different_bundle(self):
        assert validate_script_notation('pm-dev-java:build-maven:maven') == 'pm-dev-java:build-maven:maven'

    def test_invalid_no_colon(self):
        with pytest.raises(ValueError, match='Invalid script notation'):
            validate_script_notation('plan-marshall')

    def test_invalid_two_parts(self):
        with pytest.raises(ValueError, match='Invalid script notation'):
            validate_script_notation('plan-marshall:manage-files')

    def test_invalid_empty(self):
        with pytest.raises(ValueError, match='Invalid script notation'):
            validate_script_notation('')

    def test_invalid_empty_bundle(self):
        with pytest.raises(ValueError, match='Invalid script notation'):
            validate_script_notation(':manage-files:script')

    def test_invalid_empty_skill(self):
        with pytest.raises(ValueError, match='Invalid script notation'):
            validate_script_notation('plan-marshall::script')

    def test_invalid_empty_script(self):
        with pytest.raises(ValueError, match='Invalid script notation'):
            validate_script_notation('plan-marshall:manage-files:')

    def test_invalid_four_parts(self):
        with pytest.raises(ValueError, match='Invalid script notation'):
            validate_script_notation('a:b:c:d')


# =============================================================================
# 6-axis coverage for the canonical identifier vocabulary
# =============================================================================
#
# Per-validator: empty / path-separator / glob-meta / traversal / length / happy-path.
# `length` only applies to validators with a concrete upper bound; for the
# others the rejection comes from the regex itself (no bounded length probe is
# needed because the character class disallows the long input naturally).
# =============================================================================


_IDENTIFIER_VALIDATORS = [
    # (raising, bool, happy_path, error_label)
    (validate_lesson_id, is_valid_lesson_id, '2026-04-28-12-001', 'Invalid lesson_id'),
    (validate_session_id, is_valid_session_id, 'Abc123_session-9', 'Invalid session_id'),
    (validate_task_number, is_valid_task_number, '12', 'Invalid task_number'),
    (validate_task_id, is_valid_task_id, 'TASK-001', 'Invalid task_id'),
    (validate_component, is_valid_component, 'plan-marshall:manage-tasks', 'Invalid component'),
    (validate_hash_id, is_valid_hash_id, 'a1b2', 'Invalid hash_id'),
    (validate_phase_id, is_valid_phase_id, '3-outline', 'Invalid phase_id'),
    (validate_field_name, is_valid_field_name, 'modified_files', 'Invalid field_name'),
    (validate_module_name, is_valid_module_name, 'plan-marshall', 'Invalid module_name'),
    (validate_package_name, is_valid_package_name, 'foo.bar.baz', 'Invalid package_name'),
    (validate_domain_name, is_valid_domain_name, 'plan-marshall-plugin-dev', 'Invalid domain_name'),
    (validate_resource_name, is_valid_resource_name, 'manage-tasks_v2', 'Invalid resource_name'),
]


_REJECTION_AXES = [
    ('empty', ''),
    ('path-sep-fwd', 'a/b'),
    ('path-sep-back', 'a\\b'),
    ('glob-star', 'foo*bar'),
    ('glob-question', 'foo?bar'),
    ('glob-bracket-open', 'foo[bar'),
    ('glob-bracket-close', 'foo]bar'),
    ('traversal', '..'),
    ('traversal-slash', '../escape'),
    ('overlong', 'A' * 200),
]


@pytest.mark.parametrize(
    ('raising', 'bool_companion', 'happy_path', 'error_label'),
    _IDENTIFIER_VALIDATORS,
    ids=[v[3].split(' ', 1)[1] for v in _IDENTIFIER_VALIDATORS],
)
class TestIdentifierValidators:
    """6-axis coverage per canonical identifier validator."""

    def test_happy_path_returns_value(self, raising, bool_companion, happy_path, error_label):
        assert raising(happy_path) == happy_path
        assert bool_companion(happy_path) is True

    @pytest.mark.parametrize(('label', 'value'), _REJECTION_AXES, ids=[a[0] for a in _REJECTION_AXES])
    def test_rejection_axes(self, raising, bool_companion, happy_path, error_label, label, value):
        # Skip the `overlong` axis when the validator has no bounded length:
        # its character class still rejects the synthetic input via case-mismatch
        # (uppercase) for everything except resource_name, which legitimately
        # accepts long alphanumeric runs. Override here so the parametrize stays
        # one-shot.
        if label == 'overlong' and raising is validate_resource_name:
            value = value + '*'  # reintroduce a forbidden glob so overlong still rejects
        with pytest.raises(ValueError, match=error_label):
            raising(value)
        assert bool_companion(value) is False


# Validator-specific edge cases not covered by the generic 6-axis matrix.


class TestSessionIdLengthBound:
    def test_at_upper_bound(self):
        validate_session_id('A' * 128)

    def test_above_upper_bound(self):
        with pytest.raises(ValueError, match='Invalid session_id'):
            validate_session_id('A' * 129)


class TestPhaseIdEnum:
    @pytest.mark.parametrize(
        'phase',
        ['1-init', '2-refine', '3-outline', '4-plan', '5-execute', '6-finalize'],
    )
    def test_all_canonical_phases(self, phase):
        assert validate_phase_id(phase) == phase

    def test_unknown_phase_name(self):
        with pytest.raises(ValueError, match='Invalid phase_id'):
            validate_phase_id('7-publish')

    def test_uppercase_phase(self):
        with pytest.raises(ValueError, match='Invalid phase_id'):
            validate_phase_id('3-OUTLINE')


class TestComponentNotation:
    def test_three_part(self):
        assert validate_component('plan-marshall:manage-tasks:script') == 'plan-marshall:manage-tasks:script'

    def test_trailing_colon(self):
        with pytest.raises(ValueError, match='Invalid component'):
            validate_component('plan-marshall:')

    def test_uppercase_in_component(self):
        with pytest.raises(ValueError, match='Invalid component'):
            validate_component('Plan-Marshall:tasks')


class TestHashIdLowerBound:
    def test_three_chars_rejected(self):
        with pytest.raises(ValueError, match='Invalid hash_id'):
            validate_hash_id('abc')

    def test_uppercase_rejected(self):
        with pytest.raises(ValueError, match='Invalid hash_id'):
            validate_hash_id('AB12')


class TestPackageNameDots:
    def test_single_segment(self):
        assert validate_package_name('foo') == 'foo'

    def test_leading_dot_rejected(self):
        with pytest.raises(ValueError, match='Invalid package_name'):
            validate_package_name('.foo')

    def test_trailing_dot_rejected(self):
        with pytest.raises(ValueError, match='Invalid package_name'):
            validate_package_name('foo.')


class TestTaskIdAndNumber:
    def test_task_id_uppercase_required(self):
        with pytest.raises(ValueError, match='Invalid task_id'):
            validate_task_id('task-001')

    def test_task_number_no_negative(self):
        with pytest.raises(ValueError, match='Invalid task_number'):
            validate_task_number('-1')

    def test_task_number_no_leading_plus(self):
        with pytest.raises(ValueError, match='Invalid task_number'):
            validate_task_number('+12')

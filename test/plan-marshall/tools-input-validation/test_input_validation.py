#!/usr/bin/env python3
"""Tests for input_validation.py shared module."""

import sys
from pathlib import Path

import pytest

# Import shared infrastructure — triggers PYTHONPATH setup for cross-skill imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from input_validation import (  # type: ignore[import-not-found]  # noqa: E402, I001
    is_valid_plan_id,
    is_valid_relative_path,
    validate_enum,
    validate_plan_id,
    validate_relative_path,
    validate_skill_notation,
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

#!/usr/bin/env python3
"""
Tests for the manage-lessons.py script.

Tests subcommands:
- add: Create a new lesson
- get: Get a single lesson
- list: List lessons with filtering
- update: Update lesson metadata
- archive: Archive a lesson
- from-error: Create lesson from error context

Tier 2 (direct import) with 2 subprocess tests for CLI plumbing.
"""

import importlib.util
import json
from argparse import Namespace
from unittest.mock import patch

import pytest

from conftest import MARKETPLACE_ROOT, ScriptTestCase, run_script

# Script path for remaining subprocess (CLI plumbing) tests
SCRIPT_PATH = (
    MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'manage-lessons' / 'scripts' / 'manage-lessons.py'
)

# Tier 2 direct imports - load hyphenated module via importlib
_MANAGE_LESSONS_SCRIPT = str(SCRIPT_PATH)
_spec = importlib.util.spec_from_file_location('manage_lessons', _MANAGE_LESSONS_SCRIPT)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

cmd_add = _mod.cmd_add
cmd_get = _mod.cmd_get
cmd_list = _mod.cmd_list
cmd_update = _mod.cmd_update
cmd_archive = _mod.cmd_archive
cmd_from_error = _mod.cmd_from_error


# =============================================================================
# Tier 2: cmd_add
# =============================================================================


class TestCmdAdd:
    """Test cmd_add direct invocation."""

    def test_add_creates_lesson_file(self, tmp_path):
        """Should create a lesson file with correct metadata."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_add(
                Namespace(
                    component='test-component',
                    category='bug',
                    title='Test Lesson',
                    detail='This is a test lesson detail.',
                    bundle=None,
                )
            )

        assert result['status'] == 'success'
        assert result['component'] == 'test-component'
        assert result['category'] == 'bug'
        assert 'id' in result
        assert 'file' in result

    def test_add_with_invalid_category_fails(self, tmp_path):
        """Should fail when using invalid category."""
        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_add(
                Namespace(
                    component='test-component',
                    category='invalid-category',
                    title='Test',
                    detail='Detail',
                    bundle=None,
                )
            )

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_category'

    def test_add_with_bundle_reference(self, tmp_path):
        """Should accept optional bundle reference."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_add(
                Namespace(
                    component='test-component',
                    category='improvement',
                    title='Test Lesson',
                    detail='Detail',
                    bundle='pm-dev-java',
                )
            )

        assert result['status'] == 'success'


# =============================================================================
# Tier 2: cmd_list
# =============================================================================


class TestCmdList:
    """Test cmd_list direct invocation."""

    def test_list_empty_directory(self, tmp_path):
        """Should return empty list when no lessons exist."""
        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_list(Namespace(component=None, category=None, applied=None))

        assert result['status'] == 'success'
        assert result['total'] == 0
        assert result['filtered'] == 0

    def test_list_with_lessons(self, tmp_path):
        """Should list existing lessons."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        lesson_content = """id=2025-01-01-001
component=test-component
category=bug
applied=false
created=2025-01-01

# Test Lesson Title

This is the lesson body.
"""
        (lessons_dir / '2025-01-01-001.md').write_text(lesson_content)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_list(Namespace(component=None, category=None, applied=None))

        assert result['status'] == 'success'
        assert result['total'] == 1
        assert result['filtered'] == 1

    def test_list_filter_by_component(self, tmp_path):
        """Should filter lessons by component."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        lesson1 = """id=2025-01-01-001
component=component-a
category=bug
applied=false
created=2025-01-01

# Lesson A
"""
        lesson2 = """id=2025-01-01-002
component=component-b
category=bug
applied=false
created=2025-01-01

# Lesson B
"""
        (lessons_dir / '2025-01-01-001.md').write_text(lesson1)
        (lessons_dir / '2025-01-01-002.md').write_text(lesson2)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_list(Namespace(component='component-a', category=None, applied=None))

        assert result['status'] == 'success'
        assert result['total'] == 2
        assert result['filtered'] == 1

    def test_list_filter_by_category(self, tmp_path):
        """Should filter lessons by category."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        lesson1 = """id=2025-01-01-001
component=test
category=bug
applied=false
created=2025-01-01

# Bug Lesson
"""
        lesson2 = """id=2025-01-01-002
component=test
category=improvement
applied=false
created=2025-01-01

# Improvement Lesson
"""
        (lessons_dir / '2025-01-01-001.md').write_text(lesson1)
        (lessons_dir / '2025-01-01-002.md').write_text(lesson2)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_list(Namespace(component=None, category='bug', applied=None))

        assert result['status'] == 'success'
        assert result['filtered'] == 1


# =============================================================================
# Tier 2: cmd_get
# =============================================================================


class TestCmdGet:
    """Test cmd_get direct invocation."""

    def test_get_existing_lesson(self, tmp_path):
        """Should return lesson details."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        lesson_content = """id=2025-01-01-001
component=test-component
category=bug
applied=false
created=2025-01-01

# Test Lesson Title

This is the lesson body.
"""
        (lessons_dir / '2025-01-01-001.md').write_text(lesson_content)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_get(Namespace(id='2025-01-01-001'))

        assert result['status'] == 'success'
        assert result['component'] == 'test-component'
        assert result['category'] == 'bug'
        assert result['title'] == 'Test Lesson Title'

    def test_get_nonexistent_lesson(self, tmp_path):
        """Should return error for non-existent lesson."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_get(Namespace(id='nonexistent-id'))

        assert result['status'] == 'error'
        assert result['error'] == 'not_found'


# =============================================================================
# Tier 2: cmd_update
# =============================================================================


class TestCmdUpdate:
    """Test cmd_update direct invocation."""

    def test_update_applied_status(self, tmp_path):
        """Should update applied status."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        lesson_content = """id=2025-01-01-001
component=test-component
category=bug
applied=false
created=2025-01-01

# Test Lesson

Body.
"""
        (lessons_dir / '2025-01-01-001.md').write_text(lesson_content)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_update(
                Namespace(id='2025-01-01-001', applied=True, component=None, category=None)
            )

        assert result['status'] == 'success'
        assert result['field'] == 'applied'
        assert result['value'] == 'true'

        # Verify file was updated
        updated_content = (lessons_dir / '2025-01-01-001.md').read_text()
        assert 'applied=true' in updated_content

    def test_update_nonexistent_lesson_fails(self, tmp_path):
        """Should fail when updating non-existent lesson."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_update(
                Namespace(id='nonexistent', applied=True, component=None, category=None)
            )

        assert result['status'] == 'error'
        assert result['error'] == 'not_found'


# =============================================================================
# Tier 2: cmd_archive
# =============================================================================


class TestCmdArchive:
    """Test cmd_archive direct invocation."""

    def test_archive_moves_and_marks_applied(self, tmp_path):
        """Should set applied=true and move to archived-lessons."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        lesson_content = """id=2025-01-01-001
component=test-component
category=bug
applied=false
created=2025-01-01

# Test Lesson

Body content.
"""
        (lessons_dir / '2025-01-01-001.md').write_text(lesson_content)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_archive(Namespace(id='2025-01-01-001', applied=True))

        assert result['status'] == 'success'

        # Original should be removed
        assert not (lessons_dir / '2025-01-01-001.md').exists()

        # Archived file should exist with applied=true
        archived = tmp_path / 'archived-lessons' / '2025-01-01-001.md'
        assert archived.exists()
        archived_content = archived.read_text()
        assert 'applied=true' in archived_content
        assert '# Test Lesson' in archived_content

    def test_archive_with_applied_false(self, tmp_path):
        """Should archive with applied=false when specified."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        lesson_content = """id=2025-01-01-001
component=test-component
category=bug
applied=false
created=2025-01-01

# Test Lesson

Body content.
"""
        (lessons_dir / '2025-01-01-001.md').write_text(lesson_content)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_archive(Namespace(id='2025-01-01-001', applied=False))

        assert result['status'] == 'success'

        archived = tmp_path / 'archived-lessons' / '2025-01-01-001.md'
        archived_content = archived.read_text()
        assert 'applied=false' in archived_content

    def test_archive_nonexistent_lesson_fails(self, tmp_path):
        """Should fail when archiving non-existent lesson."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_archive(Namespace(id='nonexistent', applied=True))

        assert result['status'] == 'error'
        assert result['error'] == 'not_found'


# =============================================================================
# Tier 2: cmd_from_error
# =============================================================================


class TestCmdFromError:
    """Test cmd_from_error direct invocation."""

    def test_from_error_creates_lesson(self, tmp_path):
        """Should create lesson from error context JSON."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        error_context = json.dumps(
            {
                'component': 'maven-build',
                'error': 'Build failed due to missing dependency',
                'solution': 'Add the missing dependency to pom.xml',
            }
        )

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_from_error(Namespace(context=error_context))

        assert result['status'] == 'success'
        assert result['created_from'] == 'error_context'

    def test_from_error_invalid_json_fails(self, tmp_path):
        """Should fail with invalid JSON context."""
        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_from_error(Namespace(context='not valid json'))

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_json'


# =============================================================================
# Tier 3: CLI plumbing (subprocess) - kept for end-to-end coverage
# =============================================================================


class TestCliPlumbingAdd(ScriptTestCase):
    """Subprocess test for add subcommand CLI plumbing."""

    bundle = 'plan-marshall'
    skill = 'manage-lessons'
    script = 'manage-lessons.py'

    def test_cli_add_creates_lesson(self):
        """Should create a lesson via CLI and produce TOON output."""
        lessons_dir = self.temp_dir / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(self.temp_dir)}):
            result = run_script(
                SCRIPT_PATH,
                'add',
                '--component',
                'test-component',
                '--category',
                'bug',
                '--title',
                'Test Lesson',
                '--detail',
                'This is a test lesson detail.',
            )

        self.assert_success(result)
        self.assertIn('status: success', result.stdout)
        self.assertIn('component: test-component', result.stdout)
        self.assertIn('category: bug', result.stdout)

    def test_cli_invalid_category_rejected_by_argparse(self):
        """Should reject invalid category at argparse level."""
        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(self.temp_dir)}):
            result = run_script(
                SCRIPT_PATH,
                'add',
                '--component',
                'test-component',
                '--category',
                'invalid-category',
                '--title',
                'Test',
                '--detail',
                'Detail',
            )

        self.assert_failure(result)
        self.assertIn('invalid choice', result.stderr)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

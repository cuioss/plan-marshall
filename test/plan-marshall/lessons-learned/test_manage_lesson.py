#!/usr/bin/env python3
"""
Tests for the manage-lesson.py script.

Tests subcommands:
- add: Create a new lesson
- get: Get a single lesson
- list: List lessons with filtering
- update: Update lesson metadata
- from-error: Create lesson from error context
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch
from datetime import datetime

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import ScriptTestCase, run_script, MARKETPLACE_ROOT


# Script path to manage-lesson.py
SCRIPT_PATH = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'lessons-learned' / 'scripts' / 'manage-lesson.py'


class TestManageLessonAdd(ScriptTestCase):
    """Test manage-lesson.py add subcommand."""

    bundle = 'plan-marshall'
    skill = 'lessons-learned'
    script = 'manage-lesson.py'

    def test_add_creates_lesson_file(self):
        """Should create a lesson file with correct metadata."""
        lessons_dir = self.temp_dir / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(self.temp_dir)}):
            result = run_script(
                SCRIPT_PATH,
                'add',
                '--component', 'test-component',
                '--category', 'bug',
                '--title', 'Test Lesson',
                '--detail', 'This is a test lesson detail.'
            )

        self.assert_success(result)
        self.assertIn('status: success', result.stdout)
        self.assertIn('component: test-component', result.stdout)
        self.assertIn('category: bug', result.stdout)

    def test_add_with_invalid_category_fails(self):
        """Should fail when using invalid category."""
        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(self.temp_dir)}):
            result = run_script(
                SCRIPT_PATH,
                'add',
                '--component', 'test-component',
                '--category', 'invalid-category',
                '--title', 'Test',
                '--detail', 'Detail'
            )

        self.assert_failure(result)
        # argparse rejects invalid choices before our code runs
        self.assertTrue('invalid choice' in result.stderr or 'invalid_category' in result.stdout)

    def test_add_with_bundle_reference(self):
        """Should accept optional bundle reference."""
        lessons_dir = self.temp_dir / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(self.temp_dir)}):
            result = run_script(
                SCRIPT_PATH,
                'add',
                '--component', 'test-component',
                '--category', 'improvement',
                '--title', 'Test Lesson',
                '--detail', 'Detail',
                '--bundle', 'pm-dev-java'
            )

        self.assert_success(result)
        self.assertIn('status: success', result.stdout)


class TestManageLessonList(ScriptTestCase):
    """Test manage-lesson.py list subcommand."""

    bundle = 'plan-marshall'
    skill = 'lessons-learned'
    script = 'manage-lesson.py'

    def test_list_empty_directory(self):
        """Should return empty list when no lessons exist."""
        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(self.temp_dir)}):
            result = run_script(SCRIPT_PATH, 'list')

        self.assert_success(result)
        self.assertIn('status: success', result.stdout)
        self.assertIn('total: 0', result.stdout)
        self.assertIn('filtered: 0', result.stdout)

    def test_list_with_lessons(self):
        """Should list existing lessons."""
        lessons_dir = self.temp_dir / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        # Create a test lesson file
        lesson_content = """id=2025-01-01-001
component=test-component
category=bug
applied=false
created=2025-01-01

# Test Lesson Title

This is the lesson body.
"""
        (lessons_dir / '2025-01-01-001.md').write_text(lesson_content)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(self.temp_dir)}):
            result = run_script(SCRIPT_PATH, 'list')

        self.assert_success(result)
        self.assertIn('total: 1', result.stdout)
        self.assertIn('filtered: 1', result.stdout)

    def test_list_filter_by_component(self):
        """Should filter lessons by component."""
        lessons_dir = self.temp_dir / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        # Create lessons with different components
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

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(self.temp_dir)}):
            result = run_script(SCRIPT_PATH, 'list', '--component', 'component-a')

        self.assert_success(result)
        self.assertIn('total: 2', result.stdout)
        self.assertIn('filtered: 1', result.stdout)

    def test_list_filter_by_category(self):
        """Should filter lessons by category."""
        lessons_dir = self.temp_dir / 'lessons-learned'
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

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(self.temp_dir)}):
            result = run_script(SCRIPT_PATH, 'list', '--category', 'bug')

        self.assert_success(result)
        self.assertIn('filtered: 1', result.stdout)


class TestManageLessonGet(ScriptTestCase):
    """Test manage-lesson.py get subcommand."""

    bundle = 'plan-marshall'
    skill = 'lessons-learned'
    script = 'manage-lesson.py'

    def test_get_existing_lesson(self):
        """Should return lesson details."""
        lessons_dir = self.temp_dir / 'lessons-learned'
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

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(self.temp_dir)}):
            result = run_script(SCRIPT_PATH, 'get', '--id', '2025-01-01-001')

        self.assert_success(result)
        self.assertIn('status: success', result.stdout)
        self.assertIn('component: test-component', result.stdout)
        self.assertIn('category: bug', result.stdout)
        self.assertIn('title: Test Lesson Title', result.stdout)

    def test_get_nonexistent_lesson(self):
        """Should return error for non-existent lesson."""
        lessons_dir = self.temp_dir / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(self.temp_dir)}):
            result = run_script(SCRIPT_PATH, 'get', '--id', 'nonexistent-id')

        self.assert_failure(result)
        self.assertIn('not_found', result.stdout)


class TestManageLessonUpdate(ScriptTestCase):
    """Test manage-lesson.py update subcommand."""

    bundle = 'plan-marshall'
    skill = 'lessons-learned'
    script = 'manage-lesson.py'

    def test_update_applied_status(self):
        """Should update applied status."""
        lessons_dir = self.temp_dir / 'lessons-learned'
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

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(self.temp_dir)}):
            result = run_script(
                SCRIPT_PATH,
                'update',
                '--id', '2025-01-01-001',
                '--applied', 'true'
            )

        self.assert_success(result)
        self.assertIn('field: applied', result.stdout)
        self.assertIn('value: true', result.stdout)

        # Verify file was updated
        updated_content = (lessons_dir / '2025-01-01-001.md').read_text()
        self.assertIn('applied=true', updated_content)

    def test_update_nonexistent_lesson_fails(self):
        """Should fail when updating non-existent lesson."""
        lessons_dir = self.temp_dir / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(self.temp_dir)}):
            result = run_script(
                SCRIPT_PATH,
                'update',
                '--id', 'nonexistent',
                '--applied', 'true'
            )

        self.assert_failure(result)
        self.assertIn('not_found', result.stdout)


class TestManageLessonFromError(ScriptTestCase):
    """Test manage-lesson.py from-error subcommand."""

    bundle = 'plan-marshall'
    skill = 'lessons-learned'
    script = 'manage-lesson.py'

    def test_from_error_creates_lesson(self):
        """Should create lesson from error context JSON."""
        lessons_dir = self.temp_dir / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        error_context = json.dumps({
            'component': 'maven-build',
            'error': 'Build failed due to missing dependency',
            'solution': 'Add the missing dependency to pom.xml'
        })

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(self.temp_dir)}):
            result = run_script(
                SCRIPT_PATH,
                'from-error',
                '--context', error_context
            )

        self.assert_success(result)
        self.assertIn('status: success', result.stdout)
        self.assertIn('created_from: error_context', result.stdout)

    def test_from_error_invalid_json_fails(self):
        """Should fail with invalid JSON context."""
        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(self.temp_dir)}):
            result = run_script(
                SCRIPT_PATH,
                'from-error',
                '--context', 'not valid json'
            )

        self.assert_failure(result)
        self.assertIn('invalid_json', result.stdout)


if __name__ == '__main__':
    import unittest
    unittest.main()

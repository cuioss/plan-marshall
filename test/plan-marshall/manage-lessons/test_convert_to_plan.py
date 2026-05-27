#!/usr/bin/env python3
"""Tests for the ``convert-to-plan`` subcommand of manage-lessons.py.

``cmd_convert_to_plan`` moves a lesson file from the global lessons-learned
directory into a plan-local directory (``plans/{plan_id}/lesson-{id}.md``).
Tests cover the happy path, missing-source error, on-the-fly plan-directory
creation, and path-traversal rejection on both ``lesson_id`` and ``plan_id``.
"""

from argparse import Namespace
from unittest.mock import patch

from _lessons_helpers import cmd_convert_to_plan


class TestCmdConvertToPlan:
    """Test cmd_convert_to_plan direct invocation."""

    def test_convert_to_plan_moves_file(self, tmp_path):
        """Should move lesson file from lessons-learned into plan directory."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        lesson_content = """id=2025-01-01-001
component=test-component
category=bug
created=2025-01-01

# Test Lesson

Body content here.
"""
        source = lessons_dir / '2025-01-01-001.md'
        source.write_text(lesson_content)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_convert_to_plan(Namespace(lesson_id='2025-01-01-001', plan_id='my-plan'))

        assert result['status'] == 'success'
        assert result['lesson_id'] == '2025-01-01-001'
        assert result['plan_id'] == 'my-plan'

        # Source file no longer exists
        assert not source.exists()

        # Destination exists with identical content
        destination = tmp_path / 'plans' / 'my-plan' / 'lesson-2025-01-01-001.md'
        assert destination.exists()
        assert destination.read_text() == lesson_content

    def test_convert_to_plan_missing_source(self, tmp_path):
        """Should return error when source lesson does not exist."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_convert_to_plan(Namespace(lesson_id='nonexistent-id', plan_id='my-plan'))

        assert result['status'] == 'error'
        assert result['error'] == 'not_found'

    def test_convert_to_plan_creates_plan_dir_if_missing(self, tmp_path):
        """Should create the plan directory on the fly when it does not exist."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        lesson_content = """id=2025-01-01-001
component=test-component
category=bug
created=2025-01-01

# Test Lesson

Body.
"""
        (lessons_dir / '2025-01-01-001.md').write_text(lesson_content)

        plan_dir = tmp_path / 'plans' / 'fresh-plan'
        assert not plan_dir.exists()

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_convert_to_plan(Namespace(lesson_id='2025-01-01-001', plan_id='fresh-plan'))

        assert result['status'] == 'success'
        assert plan_dir.exists()
        assert (plan_dir / 'lesson-2025-01-01-001.md').exists()

    def test_convert_to_plan_rejects_path_traversal(self, tmp_path):
        """Should reject identifiers containing path separators or traversal sequences."""
        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            for bad_id in ('../escape', 'sub/dir', 'back\\slash'):
                result = cmd_convert_to_plan(Namespace(lesson_id=bad_id, plan_id='p'))
                assert result['status'] == 'error'
                assert result['error'] == 'invalid_id'

            for bad_plan in ('../escape', 'sub/dir', 'back\\slash'):
                result = cmd_convert_to_plan(Namespace(lesson_id='good-id', plan_id=bad_plan))
                assert result['status'] == 'error'
                assert result['error'] == 'invalid_id'

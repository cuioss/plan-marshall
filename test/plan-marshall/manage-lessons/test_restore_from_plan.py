#!/usr/bin/env python3
"""Tests for the ``restore-from-plan`` subcommand of manage-lessons.py.

``cmd_restore_from_plan`` is the inverse of ``cmd_convert_to_plan``: it
moves every ``lesson-*.md`` file in a plan directory back into the global
``lessons-learned/`` tree. Tests cover round-trip preservation, multi-file
restore, idempotent no-op cases (missing plan dir, no lesson files), the
destination-exists guard that refuses to clobber, and path-traversal
rejection on ``plan_id``.
"""

from argparse import Namespace
from unittest.mock import patch

import pytest
from _lessons_helpers import cmd_convert_to_plan, cmd_restore_from_plan


class TestCmdRestoreFromPlan:
    """Test cmd_restore_from_plan direct invocation."""

    def test_round_trip_convert_then_restore_preserves_content(self, tmp_path):
        """convert-to-plan + restore-from-plan should be a no-op on lesson content."""
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
            convert = cmd_convert_to_plan(Namespace(lesson_id='2025-01-01-001', plan_id='my-plan'))
            assert convert['status'] == 'success'

            # File now lives in the plan dir
            assert not source.exists()
            assert (tmp_path / 'plans' / 'my-plan' / 'lesson-2025-01-01-001.md').exists()

            restore = cmd_restore_from_plan(Namespace(plan_id='my-plan'))

        assert restore['status'] == 'success'
        assert restore['plan_id'] == 'my-plan'
        assert restore['restored_count'] == 1
        assert len(restore['restored_lessons']) == 1
        assert restore['restored_lessons'][0]['lesson_id'] == '2025-01-01-001'

        # Round-trip: source path holds the original content again
        assert source.exists()
        assert source.read_text() == lesson_content

        # Plan dir no longer holds the lesson file
        assert not (tmp_path / 'plans' / 'my-plan' / 'lesson-2025-01-01-001.md').exists()

    def test_restore_from_plan_restores_all_lesson_files(self, tmp_path):
        """When the plan dir contains multiple lesson-*.md files, all are restored."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        plan_dir = tmp_path / 'plans' / 'multi-plan'
        plan_dir.mkdir(parents=True)

        ids = ('2025-02-01-001', '2025-02-01-002', '2025-02-01-003')
        for lesson_id in ids:
            (plan_dir / f'lesson-{lesson_id}.md').write_text(
                f'id={lesson_id}\ncomponent=test\ncategory=bug\ncreated=2025-02-01\n\n'
                f'# Lesson {lesson_id}\n\nBody.\n'
            )

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_restore_from_plan(Namespace(plan_id='multi-plan'))

        assert result['status'] == 'success'
        assert result['plan_id'] == 'multi-plan'
        assert result['restored_count'] == 3
        restored_ids = sorted(item['lesson_id'] for item in result['restored_lessons'])
        assert restored_ids == list(ids)

        # All files moved to lessons-learned/
        for lesson_id in ids:
            assert (lessons_dir / f'{lesson_id}.md').exists()
            assert not (plan_dir / f'lesson-{lesson_id}.md').exists()

    def test_restore_from_plan_no_lesson_file(self, tmp_path):
        """Should return idempotent no-op when plan dir has no lesson-*.md."""
        plan_dir = tmp_path / 'plans' / 'empty-plan'
        plan_dir.mkdir(parents=True)
        # Add an unrelated file to ensure only lesson-*.md is matched
        (plan_dir / 'request.md').write_text('not a lesson')

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_restore_from_plan(Namespace(plan_id='empty-plan'))

        assert result['status'] == 'success'
        assert result['plan_id'] == 'empty-plan'
        assert result['action'] == 'no_lesson_file'

    def test_restore_from_plan_missing_plan_dir(self, tmp_path):
        """Should return idempotent no-op when plan dir does not exist."""
        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_restore_from_plan(Namespace(plan_id='ghost-plan'))

        assert result['status'] == 'success'
        assert result['action'] == 'no_lesson_file'

    def test_restore_from_plan_destination_exists(self, tmp_path):
        """Should refuse to clobber a pre-existing file in lessons-learned/."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        # Pre-existing file at the destination
        (lessons_dir / '2025-01-01-001.md').write_text('pre-existing')

        plan_dir = tmp_path / 'plans' / 'my-plan'
        plan_dir.mkdir(parents=True)
        (plan_dir / 'lesson-2025-01-01-001.md').write_text('plan-local body')

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_restore_from_plan(Namespace(plan_id='my-plan'))

        assert result['status'] == 'error'
        assert result['error'] == 'destination_exists'
        assert result['lesson_id'] == '2025-01-01-001'

        # No clobber occurred — both files remain in place
        assert (lessons_dir / '2025-01-01-001.md').read_text() == 'pre-existing'
        assert (plan_dir / 'lesson-2025-01-01-001.md').read_text() == 'plan-local body'

    @pytest.mark.parametrize('bad_plan', ('../escape', 'sub/dir', 'back\\slash'))
    def test_restore_from_plan_rejects_path_traversal(self, tmp_path, bad_plan):
        """Should reject plan_id containing path separators or traversal sequences."""
        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_restore_from_plan(Namespace(plan_id=bad_plan))

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_id'

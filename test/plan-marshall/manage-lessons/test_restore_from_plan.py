#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``restore-from-plan`` subcommand of manage-lessons.py.

``cmd_restore_from_plan`` is the inverse of ``cmd_convert_to_plan``: it
moves every ``lesson-*.md`` file in a plan directory back into the global
``lessons-learned/`` tree.

The verb reports THREE distinguishable outcomes, and the suite keeps the two
zeros separately covered because telling them apart is the whole contract:

- ``restored`` — files moved (round-trip and multi-file cases).
- ``no_lesson_file`` — the plan directory resolved, was scanned, and held none.
- ``plan_dir_unresolved`` — the directory could not be resolved under the
  main-anchored plans root, so it was never scanned. Non-benign, returned as
  ``status: error``.

Tests also cover the destination-exists guard that refuses to clobber, and
path-traversal rejection on ``plan_id``.
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
        """A plan dir that EXISTS and holds no lesson-*.md is the benign zero.

        The counterpart to ``test_restore_from_plan_missing_plan_dir`` below:
        this directory was genuinely resolved and scanned, so ``no_lesson_file``
        is a truthful report. Keeping the two cases separate is what proves the
        verb distinguishes its two zeros rather than collapsing them.
        """
        plan_dir = tmp_path / 'plans' / 'empty-plan'
        plan_dir.mkdir(parents=True)
        # Add an unrelated file to ensure only lesson-*.md is matched
        (plan_dir / 'request.md').write_text('not a lesson')

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_restore_from_plan(Namespace(plan_id='empty-plan'))

        assert result['status'] == 'success'
        assert result['plan_id'] == 'empty-plan'
        assert result['action'] == 'no_lesson_file'
        # The full documented field set rides every branch, including this one.
        assert result['store_resolution'] == 'override'
        assert result['restored_count'] == 0
        assert result['restored_lessons'] == []

    def test_restore_from_plan_missing_plan_dir(self, tmp_path):
        """A plan dir that does NOT exist is the non-benign zero, not no_lesson_file.

        The verb never scanned anything, so it cannot claim the plan carries no
        lesson. Reporting this as ``no_lesson_file`` is precisely the fail-open
        the three-state contract closes: "I could not look" must not render as
        "I looked and it was empty".
        """
        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_restore_from_plan(Namespace(plan_id='ghost-plan'))

        assert result['status'] == 'error'
        assert result['error'] == 'plan_dir_unresolved'
        assert result['action'] == 'plan_dir_unresolved'
        # The store itself resolved fine — it simply does not hold this plan.
        assert result['store_resolution'] == 'override'
        assert result['restored_count'] == 0
        assert result['restored_lessons'] == []

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

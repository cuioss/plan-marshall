#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``list-stalled`` subcommand of manage-lessons.py.

``cmd_list_stalled`` is a deterministic, read-only scanner: it globs
``plans/*/lesson-*.md`` to find plan directories still holding a relocated
lesson, reads each owning ``status.json``, and classifies a plan as STALLED
when its ``metadata.plan_source`` matches the lesson-id pattern AND its
current phase (one of ``5-execute`` / ``6-finalize``) has not reached
``done``. Tests cover the stalled-in-5-execute and stalled-in-6-finalize
positives, the completed-plan and non-lesson-sourced negatives, the empty
corpus, the canonical ``restore_command`` shape, missing/corrupt
status.json skip-without-crash, multi-lesson consolidation, and the
read-only invariant.
"""

import json
from argparse import Namespace
from unittest.mock import patch

from _lessons_helpers import cmd_list_stalled


def _write_lesson_plan(tmp_path, plan_id, lesson_ids, plan_source,
                       current_phase, phase_status):
    """Create a plan dir holding relocated lesson files plus a status.json.

    ``plan_source`` is written verbatim into ``metadata.plan_source`` so
    tests can exercise both lesson-id-shaped and non-lesson-id values. The
    ``phases`` list carries a single row for ``current_phase`` with the
    supplied ``phase_status`` (mirroring the real status.json shape).
    """
    plan_dir = tmp_path / 'plans' / plan_id
    plan_dir.mkdir(parents=True, exist_ok=True)

    for lesson_id in lesson_ids:
        (plan_dir / f'lesson-{lesson_id}.md').write_text(
            f'id={lesson_id}\ncomponent=test\ncategory=bug\ncreated=2025-01-01\n\n'
            f'# Lesson {lesson_id}\n\nBody.\n'
        )

    status = {
        'plan_id': plan_id,
        'current_phase': current_phase,
        'phases': [{'name': current_phase, 'status': phase_status}],
        'metadata': {'plan_source': plan_source},
    }
    (plan_dir / 'status.json').write_text(json.dumps(status))
    return plan_dir


class TestCmdListStalled:
    """Test cmd_list_stalled direct invocation."""

    def test_stalled_in_5_execute_is_reported(self, tmp_path):
        """A lesson-sourced plan stalled in 5-execute is reported."""
        _write_lesson_plan(
            tmp_path, 'stalled-exec', ['2025-01-01-12-001'],
            plan_source='2025-01-01-12-001',
            current_phase='5-execute', phase_status='in_progress',
        )

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_list_stalled(Namespace())

        assert result['status'] == 'success'
        assert result['stalled_count'] == 1
        plan = result['stalled_plans'][0]
        assert plan['plan_id'] == 'stalled-exec'
        assert plan['plan_source'] == '2025-01-01-12-001'
        assert plan['current_phase'] == '5-execute'
        assert plan['phase_status'] == 'in_progress'
        assert plan['lesson_ids'] == ['2025-01-01-12-001']

    def test_stalled_in_6_finalize_is_reported(self, tmp_path):
        """A lesson-sourced plan stalled in 6-finalize is reported."""
        _write_lesson_plan(
            tmp_path, 'stalled-final', ['2025-02-02-09-002'],
            plan_source='2025-02-02-09-002',
            current_phase='6-finalize', phase_status='in_progress',
        )

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_list_stalled(Namespace())

        assert result['status'] == 'success'
        assert result['stalled_count'] == 1
        plan = result['stalled_plans'][0]
        assert plan['plan_id'] == 'stalled-final'
        assert plan['current_phase'] == '6-finalize'

    def test_completed_lesson_sourced_plan_is_not_reported(self, tmp_path):
        """A lesson-sourced plan whose current phase is done is NOT reported."""
        _write_lesson_plan(
            tmp_path, 'done-plan', ['2025-03-03-10-003'],
            plan_source='2025-03-03-10-003',
            current_phase='6-finalize', phase_status='done',
        )

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_list_stalled(Namespace())

        assert result['status'] == 'success'
        assert result['stalled_count'] == 0
        assert result['stalled_plans'] == []

    def test_non_lesson_sourced_plan_is_not_reported(self, tmp_path):
        """A plan whose plan_source is not lesson-id-shaped is NOT reported."""
        # plan_source is a non-lesson-id value; despite carrying a relocated
        # lesson file and a stalled phase, it is out of scope for detection.
        _write_lesson_plan(
            tmp_path, 'feature-plan', ['2025-04-04-11-004'],
            plan_source='some-feature-request',
            current_phase='5-execute', phase_status='in_progress',
        )

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_list_stalled(Namespace())

        assert result['status'] == 'success'
        assert result['stalled_count'] == 0
        assert result['stalled_plans'] == []

    def test_empty_corpus_returns_zero(self, tmp_path):
        """An empty plans corpus returns stalled_count: 0."""
        (tmp_path / 'plans').mkdir(parents=True)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_list_stalled(Namespace())

        assert result['status'] == 'success'
        assert result['stalled_count'] == 0
        assert result['stalled_plans'] == []

    def test_missing_plans_root_returns_zero(self, tmp_path):
        """A plans root that does not exist returns stalled_count: 0."""
        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_list_stalled(Namespace())

        assert result['status'] == 'success'
        assert result['stalled_count'] == 0

    def test_restore_command_is_canonical_invocation(self, tmp_path):
        """restore_command is the exact restore-from-plan invocation."""
        _write_lesson_plan(
            tmp_path, 'cmd-plan', ['2025-05-05-13-005'],
            plan_source='2025-05-05-13-005',
            current_phase='5-execute', phase_status='in_progress',
        )

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_list_stalled(Namespace())

        plan = result['stalled_plans'][0]
        assert plan['restore_command'] == (
            'python3 .plan/execute-script.py '
            'plan-marshall:manage-lessons:manage-lessons '
            'restore-from-plan --plan-id cmd-plan'
        )

    def test_missing_status_json_is_skipped_without_crash(self, tmp_path):
        """A plan dir with a relocated lesson but no status.json is skipped."""
        plan_dir = tmp_path / 'plans' / 'no-status'
        plan_dir.mkdir(parents=True)
        (plan_dir / 'lesson-2025-06-06-14-006.md').write_text('id=x\n\n# L\n\nB.\n')

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_list_stalled(Namespace())

        assert result['status'] == 'success'
        assert result['stalled_count'] == 0

    def test_corrupt_status_json_is_skipped_without_crash(self, tmp_path):
        """A plan dir whose status.json is unparseable is skipped."""
        plan_dir = tmp_path / 'plans' / 'corrupt-status'
        plan_dir.mkdir(parents=True)
        (plan_dir / 'lesson-2025-07-07-15-007.md').write_text('id=x\n\n# L\n\nB.\n')
        (plan_dir / 'status.json').write_text('{ this is not valid json ')

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_list_stalled(Namespace())

        assert result['status'] == 'success'
        assert result['stalled_count'] == 0

    def test_multiple_lessons_reports_all_ids(self, tmp_path):
        """A plan consolidating several lesson-*.md reports all ids sorted."""
        ids = ['2025-08-08-16-008', '2025-08-08-16-009', '2025-08-08-16-010']
        _write_lesson_plan(
            tmp_path, 'multi-lesson', ids,
            plan_source='2025-08-08-16-008',
            current_phase='5-execute', phase_status='in_progress',
        )

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_list_stalled(Namespace())

        assert result['stalled_count'] == 1
        assert result['stalled_plans'][0]['lesson_ids'] == sorted(ids)

    def test_read_only_does_not_mutate_lesson_or_plan(self, tmp_path):
        """The scan never moves, deletes, or rewrites lesson files or plan dirs."""
        plan_dir = _write_lesson_plan(
            tmp_path, 'readonly-plan', ['2025-09-09-17-011'],
            plan_source='2025-09-09-17-011',
            current_phase='5-execute', phase_status='in_progress',
        )
        lesson_file = plan_dir / 'lesson-2025-09-09-17-011.md'
        before = lesson_file.read_text()

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            cmd_list_stalled(Namespace())

        assert lesson_file.exists()
        assert lesson_file.read_text() == before

    def test_mixed_corpus_reports_only_stalled(self, tmp_path):
        """Mixed corpus: only the stalled lesson-sourced plans are reported."""
        _write_lesson_plan(
            tmp_path, 'a-stalled', ['2025-10-10-18-012'],
            plan_source='2025-10-10-18-012',
            current_phase='5-execute', phase_status='in_progress',
        )
        _write_lesson_plan(
            tmp_path, 'b-done', ['2025-10-10-18-013'],
            plan_source='2025-10-10-18-013',
            current_phase='6-finalize', phase_status='done',
        )
        _write_lesson_plan(
            tmp_path, 'c-feature', ['2025-10-10-18-014'],
            plan_source='not-a-lesson-id',
            current_phase='5-execute', phase_status='in_progress',
        )

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_list_stalled(Namespace())

        assert result['stalled_count'] == 1
        assert result['stalled_plans'][0]['plan_id'] == 'a-stalled'

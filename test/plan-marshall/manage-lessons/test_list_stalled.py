#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``list-stalled`` subcommand of manage-lessons.py.

``cmd_list_stalled`` is a deterministic, read-only scanner: it globs
``plans/*/lesson-*.md`` to find plan directories still holding a relocated
lesson, reads each owning ``status.json``, and classifies a plan as STALLED
when its current phase (one of ``5-execute`` / ``6-finalize``) has not reached
``done``.

**The candidate population is the observable lesson file alone.**
``metadata.plan_source`` is REPORTED on each row as context but classifies
nothing: gating on it would exclude every ``convert-to-plan``-carried plan
(whose ``plan_source`` is unset), which is exactly the population the verb
exists to find.

**Every zero states which kind of zero it is.** The suite asserts all three
separately: an unresolvable store (``store_unresolved`` error), an absent
plans root (non-faulting ``plans_root_state: missing``), and a genuine
scanned-and-clean result (``plans_root_state: present`` with
``scanned_plan_count`` set).

The verb needs BOTH the plans root and the lessons corpus, so the unresolvable
arm is covered from either side: the discriminator must report the resolution
of the store that actually failed, never the sibling that happened to resolve,
because the documented consumer branches on that one field.

Tests cover the stalled-in-5-execute and stalled-in-6-finalize positives, the
completed-plan negative, the unset-``plan_source`` positive, the three zeros,
the duplication direction (a carried id already in the active corpus), the
unclassifiable-plan surfacing, the canonical ``restore_command`` shape,
multi-lesson consolidation, and the read-only invariant.
"""

import json
from argparse import Namespace
from unittest.mock import patch

from _lessons_helpers import cmd_list_stalled


def _write_lesson_plan(tmp_path, plan_id, lesson_ids, plan_source,
                       current_phase, phase_status):
    """Create a plan dir holding relocated lesson files plus a status.json.

    ``plan_source`` is written verbatim into ``metadata.plan_source`` so tests
    can exercise lesson-id-shaped, non-lesson-id, and unset values — none of
    which affect membership, since the population is derived from the lesson
    file's presence. The ``phases`` list carries a single row for
    ``current_phase`` with the supplied ``phase_status`` (mirroring the real
    status.json shape).
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

    def test_plan_with_unset_plan_source_is_reported(self, tmp_path):
        """A plan carrying a lesson file IS reported even with plan_source unset.

        This is the ``convert-to-plan``-carried shape: the relocation writes the
        lesson file but no ``metadata.plan_source``. A population gated on a
        lesson-id-shaped ``plan_source`` would discard exactly these plans and
        then report a clean zero over the remainder — so the population is
        derived from the observable file instead.
        """
        _write_lesson_plan(
            tmp_path, 'feature-plan', ['2025-04-04-11-004'],
            plan_source='',
            current_phase='5-execute', phase_status='in_progress',
        )

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_list_stalled(Namespace())

        assert result['status'] == 'success'
        assert result['stalled_count'] == 1
        plan = result['stalled_plans'][0]
        assert plan['plan_id'] == 'feature-plan'
        # plan_source is reported as context, and classifies nothing.
        assert plan['plan_source'] == ''
        assert plan['lesson_ids'] == ['2025-04-04-11-004']

    def test_non_lesson_id_plan_source_is_still_reported(self, tmp_path):
        """A non-lesson-id-shaped plan_source does not exclude a carried lesson."""
        _write_lesson_plan(
            tmp_path, 'request-plan', ['2025-04-04-11-005'],
            plan_source='some-feature-request',
            current_phase='5-execute', phase_status='in_progress',
        )

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_list_stalled(Namespace())

        assert result['stalled_count'] == 1
        assert result['stalled_plans'][0]['plan_source'] == 'some-feature-request'

    def test_empty_corpus_is_a_scanned_clean_zero(self, tmp_path):
        """An existing-but-empty plans root is the SCANNED zero, not a blind one."""
        (tmp_path / 'plans').mkdir(parents=True)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_list_stalled(Namespace())

        assert result['status'] == 'success'
        assert result['stalled_count'] == 0
        assert result['stalled_plans'] == []
        # The discriminators are what make this zero trustworthy.
        assert result['plans_root_state'] == 'present'
        assert result['scanned_plan_count'] == 0
        assert result['store_resolution'] == 'override'
        # The field rides every branch, empty when both stores resolved.
        assert result['unresolved_store'] == ''

    def test_missing_plans_root_reports_could_not_look(self, tmp_path):
        """An absent plans root reports missing — it is NOT a scanned zero.

        Non-faulting by design (a sweep is never aborted by it), so the
        discriminator rides the payload rather than the status. A bare
        ``stalled_count: 0`` here would be indistinguishable from a genuinely
        clean corpus.
        """
        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_list_stalled(Namespace())

        assert result['status'] == 'success'
        assert result['plans_root_state'] == 'missing'
        assert result['stalled_count'] == 0
        assert result['scanned_plan_count'] == 0
        # ``missing`` is an ASSERTION about a resolved store's plans root, so it
        # is reachable only when both stores resolved. The could-not-resolve
        # case is the distinct ``unknown``.
        assert result['store_resolution'] == 'override'
        assert result['unresolved_store'] == ''

    def test_unresolved_lessons_corpus_is_not_reported_as_a_resolved_store(
        self, tmp_path, monkeypatch
    ):
        """The discriminator names the store that FAILED, not the one that resolved.

        The verb needs both stores, and here the plans root resolves while the
        lessons corpus does not. Reporting the plans store emits
        ``store_resolution: override`` — a RESOLVED value — next to
        ``error: store_unresolved``, a real ``plans_root``, and a
        ``plans_root_state`` asserting the plans root is absent when nothing
        established that.

        It matters because the documented consumer
        (``finalize-step-lessons-housekeeping`` Step 2) uses this verb purely
        as the LESSONS-corpus substrate probe and branches on
        ``store_resolution == 'unresolved'`` to take its "corpus unresolved —
        nothing read" exit. A resolved value here walks it straight past that
        exit and into a reconciliation against a corpus it never reached.
        """
        import _lessons_query

        (tmp_path / 'plans').mkdir(parents=True)
        real_resolve = _lessons_query.resolve_lesson_store

        def _only_plans_resolves(subpath='lessons-learned'):
            if str(subpath) == 'plans':
                return real_resolve(subpath)
            return _lessons_query.LessonStore(
                None, 'unresolved', 'cannot resolve the lessons corpus (test stub)'
            )

        monkeypatch.setattr(_lessons_query, 'resolve_lesson_store', _only_plans_resolves)
        monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))

        result = cmd_list_stalled(Namespace())

        assert result['status'] == 'error'
        assert result['error'] == 'store_unresolved'
        # The three fields must agree with each other and with the error.
        assert result['store_resolution'] == 'unresolved'
        assert result['plans_root_state'] == 'unknown'
        assert result['unresolved_store'] == 'lessons'
        assert result['stalled_count'] == 0
        assert result['scanned_plan_count'] == 0
        # Both values come from the closed vocabularies consumers assert on.
        assert result['plans_root_state'] in _lessons_query.PLANS_ROOT_STATES
        assert result['unresolved_store'] in _lessons_query.UNRESOLVED_STORES

    def test_unresolved_plans_root_names_the_plans_store(self, tmp_path, monkeypatch):
        """The mirror arm: when the PLANS store fails, that is what is named.

        Keeps ``unresolved_store`` from being a constant that happens to read
        correctly on one arm — the two arms must disagree, or the field carries
        no information.
        """
        import _lessons_query

        real_resolve = _lessons_query.resolve_lesson_store

        def _only_lessons_resolves(subpath='lessons-learned'):
            if str(subpath) == 'plans':
                return _lessons_query.LessonStore(
                    None, 'unresolved', 'cannot resolve the plans root (test stub)'
                )
            return real_resolve(subpath)

        monkeypatch.setattr(_lessons_query, 'resolve_lesson_store', _only_lessons_resolves)
        monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))

        result = cmd_list_stalled(Namespace())

        assert result['status'] == 'error'
        assert result['store_resolution'] == 'unresolved'
        assert result['plans_root_state'] == 'unknown'
        assert result['unresolved_store'] == 'plans'
        assert result['unresolved_store'] in _lessons_query.UNRESOLVED_STORES

    def test_duplicate_carried_lesson_is_reported_separately(self, tmp_path):
        """A carried id already in the active corpus is its own outcome.

        The inverse direction of an absence: restoring this plan would fail with
        ``destination_exists``, so it must be reported distinctly rather than
        folded into (or hidden behind) the stalled count.
        """
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        (lessons_dir / '2025-11-11-19-015.md').write_text('id=2025-11-11-19-015\n\n# L\n\nB.\n')

        _write_lesson_plan(
            tmp_path, 'dup-plan', ['2025-11-11-19-015'],
            plan_source='2025-11-11-19-015',
            current_phase='5-execute', phase_status='in_progress',
        )

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_list_stalled(Namespace())

        assert result['duplicate_count'] == 1
        duplicate = result['duplicate_lessons'][0]
        assert duplicate['plan_id'] == 'dup-plan'
        assert duplicate['lesson_id'] == '2025-11-11-19-015'
        # The two lists are independent views correlated by plan_id.
        assert result['stalled_count'] == 1
        assert result['stalled_plans'][0]['plan_id'] == 'dup-plan'

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

    def test_missing_status_json_is_surfaced_not_silently_skipped(self, tmp_path):
        """A carried lesson whose plan has no status.json is surfaced as unclassifiable.

        It cannot be confirmed stalled OR cleared, so dropping it out of the
        population would be the same could-not-look-reports-benign collapse at
        row granularity — the plan would simply vanish from the report.
        """
        plan_dir = tmp_path / 'plans' / 'no-status'
        plan_dir.mkdir(parents=True)
        (plan_dir / 'lesson-2025-06-06-14-006.md').write_text('id=x\n\n# L\n\nB.\n')

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_list_stalled(Namespace())

        assert result['status'] == 'success'
        assert result['stalled_count'] == 0
        assert result['unclassifiable_count'] == 1
        row = result['unclassifiable_plans'][0]
        assert row['plan_id'] == 'no-status'
        assert row['reason'] == 'status_json_missing'
        assert row['lesson_ids'] == ['2025-06-06-14-006']
        # It WAS counted in the scanned population — it is not invisible.
        assert result['scanned_plan_count'] == 1

    def test_corrupt_status_json_is_surfaced_not_silently_skipped(self, tmp_path):
        """A plan whose status.json is unparseable is surfaced with its reason."""
        plan_dir = tmp_path / 'plans' / 'corrupt-status'
        plan_dir.mkdir(parents=True)
        (plan_dir / 'lesson-2025-07-07-15-007.md').write_text('id=x\n\n# L\n\nB.\n')
        (plan_dir / 'status.json').write_text('{ this is not valid json ')

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_list_stalled(Namespace())

        assert result['status'] == 'success'
        assert result['stalled_count'] == 0
        assert result['unclassifiable_count'] == 1
        assert result['unclassifiable_plans'][0]['reason'] == 'status_json_unreadable'

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

    def test_mixed_corpus_reports_every_stalled_plan(self, tmp_path):
        """Mixed corpus: the terminal-phase guard is the ONLY exclusion.

        ``b-done`` is excluded because its phase reached ``done`` — that
        classification is unchanged. ``c-feature`` IS reported: its
        ``plan_source`` is not lesson-id-shaped, which no longer excludes
        anything, so only the phase guard narrows the set.
        """
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

        assert result['stalled_count'] == 2
        reported = sorted(plan['plan_id'] for plan in result['stalled_plans'])
        assert reported == ['a-stalled', 'c-feature']
        assert result['scanned_plan_count'] == 3

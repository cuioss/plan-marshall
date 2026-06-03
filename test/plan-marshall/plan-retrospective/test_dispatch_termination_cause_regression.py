"""End-to-end regression tests for the dispatch-loop correctness fixes.

Lesson ``2026-05-10-15-001`` shipped two structural fixes for the
phase-5-execute dispatch loop:

D1 (Defect 1): The loop must drive on ``pending_count > 0`` rather than
on a single ``task_complete`` return — TASK-001 added
``manage-tasks loop-exit-guard`` as the script-level enforcement of the
"pending > 0 → must continue" invariant.

D2 (Defect 2): ``manage-metrics record-dispatch-boundary`` no longer
overloads ``unknown`` as the fallback ``termination_cause``. The
canonical clean-exit value is ``clean_exit_queue_empty``, and the
retrospective rule emits a warning if the legacy ``unknown`` token ever
appears in a recorded boundary file (which only happens on
pre-migration plans).

These tests replay recorded multi-task fixtures end-to-end against the
production scripts:

* ``test_loop_exit_guard_blocks_premature_transition`` — exercises the
  D1 loop-exit guard against a three-task fixture with TASK-001 done
  and TASK-002/TASK-003 pending, then against an all-done fixture.

* ``test_dispatch_termination_cause_clean_exit_replay`` — replays a
  three-row boundary file written in the new format
  (``clean_exit_queue_empty``) through ``analyze-logs.py``, asserting
  the counters that drive the LLM rule emit exactly one info-severity
  distribution row and zero warning rows.

* ``test_dispatch_termination_cause_legacy_unknown_warning`` — replays
  a legacy boundary file (``unknown`` token) and asserts the warning
  precondition (``unknown_count > 0``) is met.

The boundary-cause tests pin the fact extractor in ``analyze-logs.py``
that drives the LLM rule defined in
``plan-retrospective/references/logging-gap-analysis.md``. The LLM rule
itself is emitted by the retrospective synthesis step at runtime; the
deterministic regression here is the data shape the rule consumes.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Sibling _plan_retrospective_fixtures.py / conftest.py rely on the existing
# sys.path setup pattern used by the other retrospective tests.
sys.path.insert(0, str(Path(__file__).parent))

from conftest import MARKETPLACE_ROOT, get_script_path, run_script  # noqa: E402

ANALYZE_LOGS = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'plan-retrospective' / 'scripts' / 'analyze-logs.py'
MANAGE_TASKS = get_script_path('plan-marshall', 'manage-tasks', 'manage-tasks.py')

# Canonical fixture directory for this regression. Two sub-trees:
#   - ``plan/`` — three-task plan with TASK-001 done, TASK-002/TASK-003
#     pending and a new-format boundary file (three
#     ``clean_exit_queue_empty`` rows). Drives both (a) the pending
#     loop-exit-guard branch and (b) the new-format dispatch-cause
#     extractor assertions.
#   - ``legacy/`` — single-row boundary file carrying the literal
#     ``unknown`` token (pre-migration data). Drives the legacy-warning
#     dispatch-cause assertion.
FIXTURES_DIR = Path(__file__).parent / 'fixtures' / 'dispatch-loop-replay'


# =============================================================================
# Helpers
# =============================================================================


def _stage_plan(tmp_path: Path, monkeypatch, plan_id: str) -> Path:
    """Materialize the ``plan/`` fixture sub-tree into
    ``tmp_path/base/plans/{plan_id}`` and set ``PLAN_BASE_DIR``.

    Layout adjustment: the fixture stores TASK-*.json files under
    ``plan/work/tasks/`` for cohesion with the other ``work/`` artifacts
    (boundary TOON, etc.), but the production plan layout expects them
    directly under ``<plan_dir>/tasks/``. This helper flattens the copy
    so the staged plan matches the production shape that
    ``manage-tasks`` and ``analyze-logs`` read.
    """
    import shutil

    base = tmp_path / 'base'
    plan_dir = base / 'plans' / plan_id
    src = FIXTURES_DIR / 'plan'
    shutil.copytree(src, plan_dir)

    # Move work/tasks/* into tasks/ to match the production plan layout.
    work_tasks = plan_dir / 'work' / 'tasks'
    if work_tasks.exists():
        target_tasks = plan_dir / 'tasks'
        target_tasks.mkdir(exist_ok=True)
        for task_file in work_tasks.glob('TASK-*.json'):
            shutil.move(str(task_file), target_tasks / task_file.name)
        work_tasks.rmdir()

    monkeypatch.setenv('PLAN_BASE_DIR', str(base))
    return plan_dir


def _mark_all_tasks_done(plan_dir: Path) -> None:
    """Rewrite every task file under ``plan_dir/tasks/`` to ``status=done``.

    Used to flip the staged three-task fixture into an all-done state for
    the loop-exit-guard ``success`` branch without duplicating the
    fixture tree.
    """
    tasks_dir = plan_dir / 'tasks'
    for task_file in sorted(tasks_dir.glob('TASK-*.json')):
        data = json.loads(task_file.read_text(encoding='utf-8'))
        data['status'] = 'done'
        task_file.write_text(json.dumps(data, indent=2), encoding='utf-8')


# =============================================================================
# (a) Loop-exit guard regression
# =============================================================================


class TestLoopExitGuardBlocksPrematureTransition:
    """``manage-tasks loop-exit-guard`` must refuse to greenlight a phase
    transition while any pending task remains, regardless of whether the
    head of the queue has been claimed.
    """

    def test_pending_queue_returns_continue_with_ids(self, tmp_path, monkeypatch):
        """Three-task fixture, TASK-001 done, TASK-002/TASK-003 pending.

        The guard MUST emit ``status: continue`` with ``pending_count: 2``
        and ``pending_ids: [2, 3]`` — never ``status: success`` while
        pending tasks remain. This is the script-level enforcement of
        the D1 invariant; the test fails if any future refactor drops
        the ``continue`` branch or mis-orders the ID list.
        """
        plan_id = 'loop-exit-guard-pending'
        _stage_plan(tmp_path, monkeypatch, plan_id)

        result = run_script(MANAGE_TASKS, 'loop-exit-guard', '--plan-id', plan_id)
        assert result.success, result.stderr
        data = result.toon()

        assert data['status'] == 'continue', (
            f'Pending queue must trigger status=continue (the script-level '
            f'enforcement of the D1 "pending > 0 → must continue" invariant); '
            f'got status={data.get("status")!r}'
        )
        assert int(data['pending_count']) == 2
        # TOON parser keeps the list intact as ints.
        assert list(data['pending_ids']) == [2, 3], (
            f'pending_ids must be deterministic ascending order; got {data["pending_ids"]!r}'
        )

    def test_empty_queue_returns_success_with_zero_count(self, tmp_path, monkeypatch):
        """All-done fixture: every task in the fixture has status=done.

        The guard MUST emit ``status: success`` with ``pending_count: 0``
        and an empty ``pending_ids`` list — the only state in which the
        orchestrator is allowed to transition out of phase-5-execute.
        """
        plan_id = 'loop-exit-guard-all-done'
        plan_dir = _stage_plan(tmp_path, monkeypatch, plan_id)
        _mark_all_tasks_done(plan_dir)

        result = run_script(MANAGE_TASKS, 'loop-exit-guard', '--plan-id', plan_id)
        assert result.success, result.stderr
        data = result.toon()

        assert data['status'] == 'success'
        assert int(data['pending_count']) == 0
        # Empty list — TOON parsers represent absent/empty consistently.
        pending_ids = data.get('pending_ids') or []
        assert list(pending_ids) == [], (
            f'pending_ids must be empty when the queue is genuinely empty; got {pending_ids!r}'
        )


# =============================================================================
# (b) clean_exit_queue_empty replay — new-format boundary file
# =============================================================================


class TestDispatchTerminationCauseCleanExitReplay:
    """Replay a recorded three-row boundary file in the new format and pin
    the fact-extractor counters that drive the LLM rule.

    The LLM rule (``DISPATCH_TERMINATION_CAUSE`` in
    ``plan-retrospective/references/logging-gap-analysis.md``) emits:

    * One ``info``-severity finding with the per-cause distribution
      (driven by ``clean_exit_queue_empty_count`` and friends).
    * A ``warning``-severity finding when ``unknown_count > 0``.

    On new-format data, ``unknown_count`` MUST be zero so the warning
    branch is skipped, while ``clean_exit_queue_empty_count`` MUST
    surface the row count so the info branch fires exactly once.
    """

    def test_three_clean_exit_rows_surface_via_analyze_logs(self, tmp_path, monkeypatch):
        plan_id = 'dispatch-cause-clean-exit'
        plan_dir = _stage_plan(tmp_path, monkeypatch, plan_id)
        # The ``plan/`` fixture ships with the new-format boundary file at
        # ``work/metrics-dispatch-boundaries-5-execute.toon`` — analyze-logs
        # needs logs/ and references.json too. Materialize minimal stubs so
        # the unrelated branches of ``cmd_run`` stay quiet.
        (plan_dir / 'logs').mkdir(exist_ok=True)
        (plan_dir / 'logs' / 'work.log').write_text('', encoding='utf-8')
        (plan_dir / 'logs' / 'decision.log').write_text('', encoding='utf-8')
        (plan_dir / 'logs' / 'script-execution.log').write_text('', encoding='utf-8')
        (plan_dir / 'references.json').write_text(
            json.dumps({'modified_files': []}), encoding='utf-8'
        )

        result = run_script(ANALYZE_LOGS, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()

        # `dispatch_boundaries` is now a top-level per-phase-keyed dict
        # (lesson 2026-05-20-12-002 generalised the prior phase-5-only
        # nested fragment).
        boundaries = data['dispatch_boundaries']['5-execute']

        # Precondition for the LLM rule — the artifact exists.
        present = boundaries['present']
        assert str(present).lower() == 'true', (
            f'dispatch_boundaries.present must be True when the boundary file is '
            f'staged; got {present!r}'
        )

        # New-format clean-exit counter — three rows in the fixture.
        assert int(boundaries['clean_exit_queue_empty_count']) == 3, (
            f'clean_exit_queue_empty_count must equal the number of rows '
            f'(3 in this fixture); got {boundaries["clean_exit_queue_empty_count"]!r}. '
            f'This regression means the canonical clean-exit token is being '
            f'silently dropped, which would defeat the info-severity '
            f'distribution finding emitted by the retrospective rule.'
        )

        # Zero warning rows on new-format data — the unknown branch must
        # stay quiet so the rule does NOT fire a false-positive warning.
        assert int(boundaries['unknown_count']) == 0, (
            f'unknown_count must be 0 on new-format data — any nonzero value '
            f'means the recorder regressed to the overloaded-fallback defect '
            f'or the fixture leaked a legacy row; got '
            f'{boundaries["unknown_count"]!r}.'
        )


# =============================================================================
# (c) legacy unknown replay — pre-migration boundary file
# =============================================================================


class TestDispatchTerminationCauseLegacyUnknownWarning:
    """Replay the legacy single-row boundary file and assert the warning
    precondition is met.

    The retrospective rule fires a ``warning``-severity finding when
    ``unknown_count > 0`` so post-merge recurrence of the
    overloaded-fallback defect is surfaced in the audit trail. The
    legacy fixture pins the assertion that even a single ``unknown``
    row is enough to flip the precondition.
    """

    def test_legacy_unknown_row_surfaces_as_warning_precondition(self, tmp_path, monkeypatch):
        plan_id = 'dispatch-cause-legacy'
        # Legacy fixture lives at fixtures/dispatch-loop-replay/legacy/ —
        # not under the ``pending/plan/`` subdir, so stage it via a
        # direct file write rather than the helper. This matches the
        # fixture layout enumerated in the task description.
        import shutil

        base = tmp_path / 'base'
        plan_dir = base / 'plans' / plan_id
        plan_dir.mkdir(parents=True)
        src_work = FIXTURES_DIR / 'legacy' / 'work'
        shutil.copytree(src_work, plan_dir / 'work')
        # Minimal logs/ tree so analyze-logs.cmd_run() does not error on
        # missing files — the boundary fixture is the only signal the
        # test cares about.
        (plan_dir / 'logs').mkdir()
        (plan_dir / 'logs' / 'work.log').write_text('', encoding='utf-8')
        (plan_dir / 'logs' / 'decision.log').write_text('', encoding='utf-8')
        (plan_dir / 'logs' / 'script-execution.log').write_text('', encoding='utf-8')
        # references.json must exist with an empty modified_files list so
        # the unrelated ARTIFACT-missing branch in cmd_run stays quiet.
        (plan_dir / 'references.json').write_text(
            json.dumps({'modified_files': []}), encoding='utf-8'
        )
        monkeypatch.setenv('PLAN_BASE_DIR', str(base))

        result = run_script(ANALYZE_LOGS, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()

        # `dispatch_boundaries` is now a top-level per-phase-keyed dict
        # (lesson 2026-05-20-12-002 generalised the prior phase-5-only
        # nested fragment).
        boundaries = data['dispatch_boundaries']['5-execute']

        # Precondition for the LLM warning branch — the artifact exists.
        present = boundaries['present']
        assert str(present).lower() == 'true', (
            f'dispatch_boundaries.present must be True when the legacy boundary '
            f'file is staged; got {present!r}'
        )

        # The whole point of the warning rule — a single ``unknown`` row
        # is enough to flip the precondition.
        assert int(boundaries['unknown_count']) > 0, (
            f'unknown_count must be >0 on legacy data — the warning branch '
            f'of the LLM rule only fires when the precondition is met. '
            f'A zero count here means the legacy detector regressed; got '
            f'{boundaries["unknown_count"]!r}.'
        )
        # No clean-exit rows in the legacy fixture; the info-severity
        # distribution row still fires (driven by the total row count),
        # but the clean-exit counter MUST stay at zero so the
        # distribution accurately reflects the legacy state.
        assert int(boundaries['clean_exit_queue_empty_count']) == 0

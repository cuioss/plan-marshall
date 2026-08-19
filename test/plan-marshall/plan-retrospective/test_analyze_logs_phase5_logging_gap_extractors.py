# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for ``analyze-logs.py``."""


from __future__ import annotations

import json

from _analyze_logs_fixtures import SCRIPT_PATH, _analyze_logs
from _plan_retrospective_fixtures import setup_live_plan  # noqa: E402

from conftest import run_script  # noqa: E402

# =============================================================================
# Phase-5 logging-gap fact extractors
# =============================================================================


class TestPhase5LoggingGapExtractors:
    """Pin down the three phase-5-execute fact extractors.

    The extractors are pure counting/pairing — never judging. These tests
    therefore assert the shape of the returned dicts on (a) clean fixtures
    and (b) fixtures that mirror the gap pattern (missing OUTCOME, ghost
    dispatches, no dispatch-boundary file).
    """

    # ------------------------------------------------------------------
    # pair_outcome_emissions
    # ------------------------------------------------------------------

    def test_pair_outcome_emissions_clean(self):
        """Clean fixture: every Completed has a paired [OUTCOME]."""
        lines = [
            '[2026-05-08T14:00:00Z] [INFO] [abc] [MANAGE-TASKS] Completed TASK-001',
            '[2026-05-08T14:00:01Z] [INFO] [def] [OUTCOME] (plan-marshall:phase-5-execute) '
            'Completed TASK-001: Title (3 steps)',
            '[2026-05-08T14:01:00Z] [INFO] [ghi] [MANAGE-TASKS] Completed TASK-002',
            '[2026-05-08T14:01:01Z] [INFO] [jkl] [OUTCOME] (plan-marshall:phase-5-execute) '
            'Completed TASK-002: Other (1 steps)',
        ]
        result = _analyze_logs.pair_outcome_emissions(lines)
        assert result['paired'] == 2
        assert result['unpaired_completed'] == []
        assert result['unpaired_outcome'] == []

    def test_pair_outcome_emissions_regression_missing_outcome(self):
        """A task closed with no [OUTCOME] line lands in ``unpaired_completed``.

        The pairing is pure counting — it never judges. The residue is what
        matters downstream: ``unpaired_completed`` is the evidence that a
        dispatch closed a task without emitting its outcome, so an inflated
        ``paired`` count would report clean logging discipline over a phase that
        lost records.
        """
        lines = [
            '[2026-05-08T14:00:00Z] [INFO] [abc] [MANAGE-TASKS] Completed TASK-001',
            '[2026-05-08T14:00:01Z] [INFO] [def] [OUTCOME] (plan-marshall:phase-5-execute) '
            'Completed TASK-001: Title (3 steps)',
            '[2026-05-08T14:01:00Z] [INFO] [ghi] [MANAGE-TASKS] Completed TASK-002',
            # ``TASK-002`` closes with no [OUTCOME] line — the gap under test.
        ]
        result = _analyze_logs.pair_outcome_emissions(lines)
        assert result['paired'] == 1
        assert result['unpaired_completed'] == ['TASK-002']
        assert result['unpaired_outcome'] == []

    # ------------------------------------------------------------------
    # cluster_dispatches
    # ------------------------------------------------------------------

    # ``inferred_dispatches`` counts time-separated MARKER clusters. Only the
    # two literal `Starting` / `Re-entering execute phase` lines contribute a
    # timestamp; every other line carrying the `plan-marshall:phase-5-execute`
    # caller tag is inert. The pre-fix substring admission inflated the count
    # roughly 6x-18x on real logs, and the consuming RE_ENTRY_COVERAGE rule then
    # reported a logging-discipline regression that did not exist.

    @staticmethod
    def _marker(ts: str, kind: str = 'Starting') -> str:
        return (
            f'[{ts}] [INFO] [abc] '
            f'[STATUS] (plan-marshall:phase-5-execute) {kind} execute phase — 3 tasks pending'
        )

    @staticmethod
    def _noise(ts: str, task: str = 'TASK-001') -> str:
        """A phase-5-tagged NON-marker line — inert for clustering."""
        return (
            f'[{ts}] [INFO] [def] '
            f'[OUTCOME] (plan-marshall:phase-5-execute) Completed {task}: x (1 steps)'
        )

    def test_cluster_dispatches_single_cluster(self):
        """Markers within `gap_threshold_s` of each other form one cluster."""
        work = [
            self._marker('2026-05-08T14:00:00Z'),
            self._marker('2026-05-08T14:00:10Z', 'Re-entering'),
            self._noise('2026-05-08T14:00:20Z', 'TASK-002'),
        ]
        result = _analyze_logs.cluster_dispatches(work, [], gap_threshold_s=30.0)
        assert result['inferred_dispatches'] == 1
        assert result['starting_markers'] == 1
        assert result['re_entering_markers'] == 1

    def test_cluster_dispatches_regression_ghost_re_entry(self):
        """Two marker clusters split by a >30s gap, only one Re-entering marker.

        Rewritten to marker-derived semantics: the second cluster is delimited by
        a real marker line, NOT by an unrelated `[OUTCOME]` line. Under the
        pre-fix substring admission this population's `[OUTCOME]` line alone
        produced the second cluster, which is exactly the fabricated boundary the
        fix removes.
        """
        work = [
            self._marker('2026-05-08T14:00:00Z'),
            self._noise('2026-05-08T14:00:10Z'),
            # 5-minute gap, then a genuine second dispatch marker.
            self._marker('2026-05-08T14:05:10Z', 'Re-entering'),
            self._noise('2026-05-08T14:05:20Z', 'TASK-002'),
        ]
        result = _analyze_logs.cluster_dispatches(work, [], gap_threshold_s=30.0)
        assert result['inferred_dispatches'] == 2
        assert result['starting_markers'] == 1
        assert result['re_entering_markers'] == 1

    def test_cluster_dispatches_ignores_non_marker_phase_5_lines(self):
        """Regression: N markers plus M >> N spaced-out phase-5-tagged non-marker
        lines must yield exactly N, not N + M.

        Each `[OUTCOME]` line below is more than the 30s gap threshold from its
        neighbours, so under the pre-fix substring admission every one of them
        opened its own cluster.
        """
        work = [
            self._marker('2026-05-08T14:00:00Z'),
            self._marker('2026-05-08T14:30:00Z', 'Re-entering'),
        ]
        for minute in range(1, 11):
            work.append(self._noise(f'2026-05-08T15:{minute:02d}:00Z', f'TASK-{minute:03d}'))

        result = _analyze_logs.cluster_dispatches(work, [], gap_threshold_s=30.0)
        assert result['inferred_dispatches'] == 2, (
            'Only the two literal marker lines delimit a dispatch — the ten '
            'spaced-out phase-5-tagged [OUTCOME] lines must contribute nothing.'
        )
        assert result['starting_markers'] == 1
        assert result['re_entering_markers'] == 1

    def test_cluster_dispatches_zero_markers_yields_zero(self):
        """A log of nothing but phase-5-tagged non-marker lines infers 0 dispatches."""
        work = [
            self._noise('2026-05-08T14:00:00Z', 'TASK-001'),
            self._noise('2026-05-08T14:10:00Z', 'TASK-002'),
            self._noise('2026-05-08T14:20:00Z', 'TASK-003'),
        ]
        result = _analyze_logs.cluster_dispatches(work, [], gap_threshold_s=30.0)
        assert result['inferred_dispatches'] == 0
        assert result['starting_markers'] == 0
        assert result['re_entering_markers'] == 0

    def test_cluster_dispatches_script_log_lines_are_a_no_op(self):
        """A non-marker script-log line leaves every output unchanged — the
        parameter is kept in the signature purely for caller stability."""
        work = [self._marker('2026-05-08T14:00:00Z')]
        script = [
            '[2026-05-08T14:00:05Z] [INFO] [xyz] '
            'plan-marshall:manage-tasks:manage-tasks next (0.12s)',
        ]
        with_script = _analyze_logs.cluster_dispatches(work, script, gap_threshold_s=30.0)
        without_script = _analyze_logs.cluster_dispatches(work, [], gap_threshold_s=30.0)
        assert with_script == without_script
        assert with_script['inferred_dispatches'] == 1

    def test_cluster_dispatches_marker_shaped_script_log_line_is_a_no_op(self):
        """A MARKER-SHAPED line in the script log must NOT move
        ``inferred_dispatches``.

        The sibling test above only exercises a non-marker script-log line, so it
        passes whether or not the script log is scanned. This one places a real
        marker line — more than ``gap_threshold_s`` from the work-log marker, so
        it would open its own cluster if admitted — into ``script_log_lines``.
        Admitting it would raise ``inferred_dispatches`` to 2 while
        ``starting_markers`` / ``re_entering_markers`` (computed from
        ``work_log_lines`` alone) stayed at 1 / 0: a dispatch fact no marker count
        can corroborate, which is exactly the false verdict the consuming
        RE_ENTRY_COVERAGE rule would report as a logging-discipline regression.
        """
        work = [self._marker('2026-05-08T14:00:00Z')]
        script = [self._marker('2026-05-08T14:30:00Z', 'Re-entering')]

        result = _analyze_logs.cluster_dispatches(work, script, gap_threshold_s=30.0)

        assert result == _analyze_logs.cluster_dispatches(work, [], gap_threshold_s=30.0)
        assert result['inferred_dispatches'] == 1
        assert result['starting_markers'] == 1
        assert result['re_entering_markers'] == 0

    # ------------------------------------------------------------------
    # detect_outcome_for_diffed_tasks
    # ------------------------------------------------------------------

    def test_detect_outcome_for_diffed_tasks_clean(self, tmp_path):
        """Every done task has a matching [OUTCOME] — no missing entries."""
        plan_dir = tmp_path / 'plans' / 'clean'
        (plan_dir / 'tasks').mkdir(parents=True)
        (plan_dir / 'tasks' / 'TASK-001.json').write_text(
            json.dumps({'number': 1, 'title': 'A', 'status': 'done'}),
            encoding='utf-8',
        )
        (plan_dir / 'tasks' / 'TASK-002.json').write_text(
            json.dumps({'number': 2, 'title': 'B', 'status': 'done'}),
            encoding='utf-8',
        )

        lines = [
            '[2026-05-08T14:00:01Z] [INFO] [abc] [OUTCOME] (plan-marshall:phase-5-execute) '
            'Completed TASK-001: A (1 steps)',
            '[2026-05-08T14:00:02Z] [INFO] [def] [OUTCOME] (plan-marshall:phase-5-execute) '
            'Completed TASK-002: B (1 steps)',
        ]
        result = _analyze_logs.detect_outcome_for_diffed_tasks(lines, plan_dir)
        assert result['tasks_with_diff_no_outcome'] == []

    def test_detect_outcome_for_diffed_tasks_regression(self, tmp_path):
        """A ``done`` task with no [OUTCOME] line is flagged; a pending one is not.

        The selector is ``status: done``, not a git diff, even though the
        function and its ``tasks_with_diff_no_outcome`` key both say *diff*: the
        per-task SHA range is not persisted anywhere stable, so the extractor
        uses ``done`` as a deliberately over-inclusive proxy and the LLM rule
        applies the diff guard downstream.

        The status filter is the load-bearing half. A task that was never closed
        has no outcome to emit, so flagging it would report a logging gap for
        work that simply has not finished — noise that makes the real gaps
        unreadable.
        """
        plan_dir = tmp_path / 'plans' / 'gap'
        (plan_dir / 'tasks').mkdir(parents=True)
        (plan_dir / 'tasks' / 'TASK-001.json').write_text(
            json.dumps({'number': 1, 'title': 'A', 'status': 'done'}),
            encoding='utf-8',
        )
        (plan_dir / 'tasks' / 'TASK-002.json').write_text(
            json.dumps({'number': 2, 'title': 'B', 'status': 'done'}),
            encoding='utf-8',
        )
        # Task pending — never closed; should NOT be flagged as missing-outcome.
        (plan_dir / 'tasks' / 'TASK-003.json').write_text(
            json.dumps({'number': 3, 'title': 'C', 'status': 'pending'}),
            encoding='utf-8',
        )

        lines = [
            '[2026-05-08T14:00:01Z] [INFO] [abc] [OUTCOME] (plan-marshall:phase-5-execute) '
            'Completed TASK-001: A (1 steps)',
            # No [OUTCOME] for ``TASK-002`` → flagged.
        ]
        result = _analyze_logs.detect_outcome_for_diffed_tasks(lines, plan_dir)
        assert result['tasks_with_diff_no_outcome'] == ['TASK-002']

    # ------------------------------------------------------------------
    # read_dispatch_boundaries_per_phase
    # ------------------------------------------------------------------

    def test_read_dispatch_boundaries_per_phase_absent(self, tmp_path):
        """Plans with no boundary artifacts return an empty per-phase dict."""
        plan_dir = tmp_path / 'plans' / 'no-boundary'
        plan_dir.mkdir(parents=True)
        result = _analyze_logs.read_dispatch_boundaries_per_phase(plan_dir)
        assert result == {}

    def test_read_dispatch_boundaries_per_phase_present(self, tmp_path):
        """Glob discovers every per-phase artifact and keys the result by phase name.

        The reader globs the artifacts rather than reading a single phase-5
        path, so phase-4-plan and phase-6-finalize dispatches are accounted for
        too; a single-path reader reports those phases as having no boundaries
        rather than as unmeasured. The per-file shape (``present``, ``rows``,
        ``unknown_count``, ``clean_exit_queue_empty_count``) is unchanged.
        """
        plan_dir = tmp_path / 'plans' / 'with-boundary'
        (plan_dir / 'work').mkdir(parents=True)
        # Phase-5-execute artifact — preserves the legacy single-phase shape.
        (plan_dir / 'work' / 'metrics-dispatch-boundaries-5-execute.toon').write_text(
            'plan_id: with-boundary\n'
            'phase: 5-execute\n'
            'rows[]{timestamp,termination_cause,total_tokens,tool_uses,duration_ms}:\n'
            '2026-05-08T14:00:00Z,voluntary_checkpoint,100,2,1000\n'
            '2026-05-08T14:01:00Z,unknown,200,4,2000\n'
            '2026-05-08T14:02:00Z,clean_exit_queue_empty,300,6,3000\n',
            encoding='utf-8',
        )
        # Phase-4-plan artifact — a non-phase-5 dispatch surface.
        (plan_dir / 'work' / 'metrics-dispatch-boundaries-4-plan.toon').write_text(
            'plan_id: with-boundary\n'
            'phase: 4-plan\n'
            'rows[]{timestamp,termination_cause,total_tokens,tool_uses,duration_ms}:\n'
            '2026-05-08T14:00:00Z,task_batch_complete,500,10,5000\n',
            encoding='utf-8',
        )
        # Phase-6-finalize artifact — per-step recorder.
        (plan_dir / 'work' / 'metrics-dispatch-boundaries-6-finalize.toon').write_text(
            'plan_id: with-boundary\n'
            'phase: 6-finalize\n'
            'rows[]{timestamp,termination_cause,total_tokens,tool_uses,duration_ms}:\n'
            '2026-05-08T14:00:00Z,step_complete,600,12,6000\n'
            '2026-05-08T14:01:00Z,step_complete,700,14,7000\n',
            encoding='utf-8',
        )

        result = _analyze_logs.read_dispatch_boundaries_per_phase(plan_dir)
        # All three phases surface as top-level keys.
        assert set(result.keys()) == {'4-plan', '5-execute', '6-finalize'}

        # Phase-5-execute counters carry through verbatim from the legacy parser.
        p5 = result['5-execute']
        assert p5['present'] is True
        assert len(p5['rows']) == 3
        assert p5['rows'][0]['termination_cause'] == 'voluntary_checkpoint'
        assert p5['unknown_count'] == 1
        assert p5['clean_exit_queue_empty_count'] == 1

        # Phase-4-plan boundary row.
        p4 = result['4-plan']
        assert p4['present'] is True
        assert len(p4['rows']) == 1
        assert p4['rows'][0]['termination_cause'] == 'task_batch_complete'

        # Phase-6-finalize per-step rows.
        p6 = result['6-finalize']
        assert p6['present'] is True
        assert len(p6['rows']) == 2
        assert all(r['termination_cause'] == 'step_complete' for r in p6['rows'])

    # ------------------------------------------------------------------
    # Integration: cmd_run end-to-end
    # ------------------------------------------------------------------

    def test_cmd_run_surfaces_phase5_logging_gaps_and_top_level_dispatch_boundaries(
        self, tmp_path, monkeypatch
    ):
        """End-to-end: cmd_run emits phase5_logging_gaps (three extractors) and
        a top-level dispatch_boundaries per-phase dict.

        ``dispatch_boundaries`` is a top-level fragment rather than a sub-key of
        ``phase5_logging_gaps``, so the compile-report renderer can emit a
        dedicated section keyed by phase.
        """
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)

        # Add a tasks/ dir + boundary artifacts for all three phases.
        (plan_dir / 'tasks').mkdir(parents=True, exist_ok=True)
        (plan_dir / 'tasks' / 'TASK-001.json').write_text(
            json.dumps({'number': 1, 'title': 'A', 'status': 'done'}),
            encoding='utf-8',
        )
        (plan_dir / 'work').mkdir(parents=True, exist_ok=True)
        (plan_dir / 'work' / 'metrics-dispatch-boundaries-5-execute.toon').write_text(
            'plan_id: ' + plan_id + '\n'
            'phase: 5-execute\n'
            'rows[]{timestamp,termination_cause,total_tokens,tool_uses,duration_ms}:\n'
            '2026-05-08T14:00:00Z,unknown,100,2,1000\n',
            encoding='utf-8',
        )
        (plan_dir / 'work' / 'metrics-dispatch-boundaries-4-plan.toon').write_text(
            'plan_id: ' + plan_id + '\n'
            'phase: 4-plan\n'
            'rows[]{timestamp,termination_cause,total_tokens,tool_uses,duration_ms}:\n'
            '2026-05-08T14:00:00Z,task_batch_complete,500,10,5000\n',
            encoding='utf-8',
        )
        (plan_dir / 'work' / 'metrics-dispatch-boundaries-6-finalize.toon').write_text(
            'plan_id: ' + plan_id + '\n'
            'phase: 6-finalize\n'
            'rows[]{timestamp,termination_cause,total_tokens,tool_uses,duration_ms}:\n'
            '2026-05-08T14:00:00Z,step_complete,600,12,6000\n',
            encoding='utf-8',
        )

        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()

        # phase5_logging_gaps keeps the three extractor sub-keys (the prior
        # ``dispatch_boundaries`` sub-key has been hoisted out — see below).
        gaps = data['phase5_logging_gaps']
        assert 'outcome_pairing' in gaps
        assert 'dispatch_clustering' in gaps
        assert 'outcome_for_diffed_tasks' in gaps
        assert 'dispatch_boundaries' not in gaps

        # Top-level dispatch_boundaries surfaces every phase artifact discovered
        # by the glob.
        boundaries = data['dispatch_boundaries']
        for phase in ('4-plan', '5-execute', '6-finalize'):
            assert phase in boundaries, f'expected {phase} key in dispatch_boundaries'

    def test_cmd_run_dispatch_boundaries_empty_when_no_artifacts(self, tmp_path, monkeypatch):
        """When no boundary artifacts exist the top-level key is an empty dict
        (vs. absent) — the compile-report renderer's gate distinguishes the
        two states.
        """
        plan_id, _ = setup_live_plan(tmp_path, monkeypatch)
        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()
        # Key is present and empty (per the generalised reader contract).
        assert 'dispatch_boundaries' in data
        # The TOON parser may render an empty dict as an empty-string-like or
        # empty-iterable value — accept any falsy representation.
        boundaries = data['dispatch_boundaries']
        if isinstance(boundaries, dict):
            assert boundaries == {}
        else:
            assert not boundaries

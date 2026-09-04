# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for ``analyze-logs.py``.

Its sections, in order:

* Phase-5 logging-gap fact extractors
* read_dispatch_boundaries_per_phase
* Integration: cmd_run end-to-end
"""


from __future__ import annotations

import json

from _analyze_logs_fixtures import SCRIPT_PATH, _analyze_logs
from _plan_retrospective_fixtures import setup_live_plan

from conftest import run_script

# =============================================================================
# Phase-5 logging-gap fact extractors
# =============================================================================




class TestReadDispatchBoundariesPerPhase:
    """Phase-5 logging-gap extractors — reading the per-phase dispatch-boundary artifacts."""

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


class TestCmdRunSurfacesPhase5Gaps:
    """Phase-5 logging-gap extractors — ``cmd_run`` surfacing the gaps and the boundaries together."""

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

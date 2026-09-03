#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-metrics.py CLI script.

Scope: recording a termination cause into its per-phase artifact — the phase-4-plan,
phase-5 and phase-6-finalize paths, and the rejection an invalid cause earns.
"""


import pytest
from _manage_metrics_fixtures import (
    ns_record_dispatch_boundary,
    raw_ns,
)
from _manage_metrics_module_fixtures import (
    _NEW_TERMINATION_CAUSES_WITH_PHASE,
    _UNSEEDED_PLAN_IDS,
    _seed_guarded_plan_dirs,
    cmd_record_dispatch_boundary,
    manage_metrics,
)


class TestRecordDispatchBoundaryAcceptsNewCauses:
    """cmd_record_dispatch_boundary accepts each of the 5 new termination causes."""

    @pytest.mark.parametrize(
        'cause,phase',
        _NEW_TERMINATION_CAUSES_WITH_PHASE,
        ids=[c for c, _ in _NEW_TERMINATION_CAUSES_WITH_PHASE],
    )
    def test_new_cause_records_row_to_per_phase_artifact(self, plan_context, cause, phase):
        """Each new termination cause produces a successful record and a per-phase artifact file."""
        plan_id = f'rdb-new-{cause.replace("_", "-")}'
        # Seed status.json so cmd_record_dispatch_boundary's require_plan_exists
        # guard accepts the plan (lesson 2026-05-15-X: orphan-plan-dir guard).
        pdir = plan_context.plan_dir_for(plan_id)
        (pdir / 'status.json').write_text('{}', encoding='utf-8')
        result = cmd_record_dispatch_boundary(
            ns_record_dispatch_boundary(
                plan_id,
                phase,
                termination_cause=cause,
                total_tokens=1234,
                tool_uses=5,
                duration_ms=6789,
            )
        )

        assert result['status'] == 'success', result
        assert result['termination_cause'] == cause
        assert result['phase'] == phase
        assert result['total_tokens'] == 1234
        assert result['tool_uses'] == 5
        assert result['duration_ms'] == 6789
        assert result['rows_recorded'] == 1

        # Verify the per-phase artifact file exists at the expected path.
        artifact = pdir / 'work' / f'metrics-dispatch-boundaries-{phase}.toon'
        assert artifact.exists(), f'expected {artifact} to be created'
        content = artifact.read_text(encoding='utf-8')
        assert f'phase: {phase}' in content
        # Each row is "<timestamp>,<cause>,<total>,<tools>,<duration>"; the cause
        # token must appear on the data line.
        assert f',{cause},1234,5,6789' in content

    def test_phase_6_finalize_artifact_path_is_used_for_finalize_causes(self, plan_context):
        """The three phase-6-finalize causes all land in the 6-finalize artifact file."""
        plan_id = 'rdb-phase6-grouped'
        pdir = plan_context.plan_dir_for(plan_id)
        (pdir / 'status.json').write_text('{}', encoding='utf-8')
        for cause in ('step_complete', 'blocked_user_review', 'blocked_session_restart'):
            result = cmd_record_dispatch_boundary(
                ns_record_dispatch_boundary(plan_id, '6-finalize', termination_cause=cause)
            )
            assert result['status'] == 'success'

        artifact = pdir / 'work' / 'metrics-dispatch-boundaries-6-finalize.toon'
        assert artifact.exists()
        content = artifact.read_text(encoding='utf-8')
        assert ',step_complete,' in content
        assert ',blocked_user_review,' in content
        assert ',blocked_session_restart,' in content
        # Three data rows were appended into the same file.
        data_lines = [
            line for line in content.splitlines()
            if line and not line.startswith(('plan_id:', 'phase:', 'rows[]'))
        ]
        assert len(data_lines) == 3

    def test_phase_4_plan_artifact_path_is_used_for_plan_causes(self, plan_context):
        """The two phase-4-plan causes both land in the 4-plan artifact file."""
        plan_id = 'rdb-phase4-grouped'
        pdir = plan_context.plan_dir_for(plan_id)
        (pdir / 'status.json').write_text('{}', encoding='utf-8')
        for cause in ('task_batch_complete', 'agent_returned'):
            result = cmd_record_dispatch_boundary(
                ns_record_dispatch_boundary(plan_id, '4-plan', termination_cause=cause)
            )
            assert result['status'] == 'success'

        artifact = pdir / 'work' / 'metrics-dispatch-boundaries-4-plan.toon'
        assert artifact.exists()
        content = artifact.read_text(encoding='utf-8')
        assert ',task_batch_complete,' in content
        assert ',agent_returned,' in content
        data_lines = [
            line for line in content.splitlines()
            if line and not line.startswith(('plan_id:', 'phase:', 'rows[]'))
        ]
        assert len(data_lines) == 2


class TestRecordDispatchBoundaryAcceptsBudgetYield:
    """budget_yield is the phase-5 budget-bounded dispatch loop's yield signal.

    The phase-5-execute envelope yields to the orchestrator at a TASK boundary
    when the per-task budget reserve is exhausted; the orchestrator records that
    yield via record-dispatch-boundary with termination_cause=budget_yield. The
    cause lands in the 5-execute artifact file.
    """

    def test_budget_yield_records_row_to_phase_5_artifact(self, plan_context):
        """budget_yield is accepted and recorded into the 5-execute boundary artifact."""
        plan_id = 'rdb-budget-yield'
        pdir = plan_context.plan_dir_for(plan_id)
        (pdir / 'status.json').write_text('{}', encoding='utf-8')
        result = cmd_record_dispatch_boundary(
            ns_record_dispatch_boundary(
                plan_id,
                '5-execute',
                termination_cause='budget_yield',
                total_tokens=119000,
                tool_uses=42,
                duration_ms=300000,
            )
        )

        assert result['status'] == 'success', result
        assert result['termination_cause'] == 'budget_yield'
        assert result['phase'] == '5-execute'
        assert result['total_tokens'] == 119000
        assert result['rows_recorded'] == 1

        artifact = pdir / 'work' / 'metrics-dispatch-boundaries-5-execute.toon'
        assert artifact.exists(), f'expected {artifact} to be created'
        content = artifact.read_text(encoding='utf-8')
        assert 'phase: 5-execute' in content
        assert ',budget_yield,119000,42,300000' in content

    def test_budget_yield_appends_alongside_other_phase_5_causes(self, plan_context):
        """budget_yield rows coexist with other 5-execute causes in the same artifact."""
        plan_id = 'rdb-budget-yield-mixed'
        pdir = plan_context.plan_dir_for(plan_id)
        (pdir / 'status.json').write_text('{}', encoding='utf-8')
        for cause in ('budget_yield', 'clean_exit_queue_empty'):
            result = cmd_record_dispatch_boundary(
                ns_record_dispatch_boundary(plan_id, '5-execute', termination_cause=cause)
            )
            assert result['status'] == 'success'

        artifact = pdir / 'work' / 'metrics-dispatch-boundaries-5-execute.toon'
        content = artifact.read_text(encoding='utf-8')
        assert ',budget_yield,' in content
        assert ',clean_exit_queue_empty,' in content
        data_lines = [
            line for line in content.splitlines()
            if line and not line.startswith(('plan_id:', 'phase:', 'rows[]'))
        ]
        assert len(data_lines) == 2


class TestRecordDispatchBoundaryRejectsInvalidCause:
    """An unknown termination_cause still surfaces the structured error."""

    def test_invalid_cause_returns_invalid_termination_cause_error(self, plan_context):
        """An unknown cause produces status=error with error=invalid_termination_cause."""
        result = cmd_record_dispatch_boundary(
            raw_ns(
                'record-dispatch-boundary',
                plan_id='rdb-invalid-cause',
                phase='6-finalize',
                termination_cause='not_a_real_cause',
            )
        )
        assert result['status'] == 'error'
        assert result['error'] == 'invalid_termination_cause'
        assert 'not_a_real_cause' in str(result.get('message', ''))

    def test_legacy_unknown_value_still_rejected(self, plan_context):
        """The value 'unknown' is not a valid termination cause and is rejected.

        It is not in the parser's ``choices``, so the CLI refuses it outright;
        this pins that the handler refuses it too, for the programmatic callers
        that reach ``cmd_record_dispatch_boundary`` with no parser in front.
        """
        result = cmd_record_dispatch_boundary(
            raw_ns(
                'record-dispatch-boundary',
                plan_id='rdb-legacy-unknown',
                phase='6-finalize',
                termination_cause='unknown',
            )
        )
        assert result['status'] == 'error'
        assert result['error'] == 'invalid_termination_cause'


class TestRecordDispatchBoundaryLegacyCausesStillPass:
    """The 5 legacy termination causes continue to record successfully."""

    @pytest.mark.parametrize(
        'cause',
        [
            'voluntary_checkpoint',
            'task_complete_returned_verbatim',
            'harness_cancellation',
            'error',
            'clean_exit_queue_empty',
        ],
    )
    def test_legacy_cause_records_row(self, plan_context, cause):
        """Each legacy termination cause still produces a successful record."""
        plan_id = f'rdb-legacy-{cause.replace("_", "-")}'
        pdir = plan_context.plan_dir_for(plan_id)
        (pdir / 'status.json').write_text('{}', encoding='utf-8')
        result = cmd_record_dispatch_boundary(
            ns_record_dispatch_boundary(plan_id, '5-execute', termination_cause=cause)
        )
        assert result['status'] == 'success'
        assert result['termination_cause'] == cause
        artifact = pdir / 'work' / 'metrics-dispatch-boundaries-5-execute.toon'
        assert artifact.exists()
        assert f',{cause},' in artifact.read_text(encoding='utf-8')

#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-metrics.py CLI script."""


import pytest
from _manage_metrics_fixtures import (
    ns_record_dispatch_boundary,
    raw_ns,
)
from _manage_metrics_module_fixtures import (
    _NEW_TERMINATION_CAUSES_WITH_PHASE,
    _UNSEEDED_PLAN_IDS,
    cmd_record_dispatch_boundary,
    manage_metrics,
)


@pytest.fixture(autouse=True)
def _seed_guarded_plan_dirs(plan_context, monkeypatch):
    """Auto-seed ``status.json`` at the require_plan_exists chokepoint.

    The patched guard resolves the plan dir via the real ``get_plan_dir`` and, for
    any plan_id NOT registered as unseeded, writes the ``status.json`` sentinel
    before delegating to the genuine ``require_plan_exists``. This keeps every
    positive test's happy path intact without per-test seeding, while the
    negative tests (which call ``_register_unseeded``) still exercise the real
    ``plan_not_found`` failure.
    """
    _UNSEEDED_PLAN_IDS.clear()
    real_require = manage_metrics.require_plan_exists
    real_get_plan_dir = manage_metrics.get_plan_dir

    def _seeding_require(plan_id):
        if plan_id not in _UNSEEDED_PLAN_IDS:
            plan_dir = real_get_plan_dir(plan_id)
            plan_dir.mkdir(parents=True, exist_ok=True)
            sentinel = plan_dir / 'status.json'
            if not sentinel.is_file():
                sentinel.write_text('{}', encoding='utf-8')
        return real_require(plan_id)

    monkeypatch.setattr(manage_metrics, 'require_plan_exists', _seeding_require)
    return plan_context


class TestDispatchTerminationCausesEnum:
    """Structural assertions on the DISPATCH_TERMINATION_CAUSES tuple."""

    def test_enum_contains_exactly_twelve_values(self):
        """The enum extends to exactly 12 entries — the legacy 5, the phase-6/phase-4
        extension (5), the budget_yield phase-5 dispatch-loop signal, plus
        returned_with_findings (the productive-loop-back member)."""
        assert len(manage_metrics.DISPATCH_TERMINATION_CAUSES) == 12

    def test_enum_contains_returned_with_findings_cause(self):
        """The productive-non-completion member is present.

        A findings-bearing loop-back is a success of the dispatched step and a
        non-completion of the loop; before this member the dispatch ledger had no
        token for it and such returns fell through to `error`. RED before the
        member was added.
        """
        assert 'returned_with_findings' in manage_metrics.DISPATCH_TERMINATION_CAUSES

    def test_enum_preserves_legacy_five_values(self):
        """The legacy 5 entries remain present so prior callers do not break."""
        legacy = {
            'voluntary_checkpoint',
            'task_complete_returned_verbatim',
            'harness_cancellation',
            'error',
            'clean_exit_queue_empty',
        }
        assert legacy.issubset(set(manage_metrics.DISPATCH_TERMINATION_CAUSES))

    def test_enum_contains_phase_6_finalize_causes(self):
        """The three phase-6-finalize outcomes are present in the extended enum."""
        phase6 = {'step_complete', 'blocked_user_review', 'blocked_session_restart'}
        assert phase6.issubset(set(manage_metrics.DISPATCH_TERMINATION_CAUSES))

    def test_enum_contains_phase_4_plan_causes(self):
        """The two phase-4-plan outcomes are present in the extended enum."""
        phase4 = {'task_batch_complete', 'agent_returned'}
        assert phase4.issubset(set(manage_metrics.DISPATCH_TERMINATION_CAUSES))

    def test_enum_contains_budget_yield_cause(self):
        """The phase-5 budget-bounded dispatch loop's yield signal is present."""
        assert 'budget_yield' in manage_metrics.DISPATCH_TERMINATION_CAUSES

    def test_enum_has_no_duplicate_values(self):
        """Every termination cause is distinct — budget_yield is additive, not a rename."""
        causes = manage_metrics.DISPATCH_TERMINATION_CAUSES
        assert len(causes) == len(set(causes))


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

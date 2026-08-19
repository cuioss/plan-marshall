#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-metrics.py CLI script."""


import pytest
from _manage_metrics_fixtures import (
    ns_accumulate,
    ns_end_phase,
    ns_phase_boundary,
    ns_start_phase,
)
from _manage_metrics_module_fixtures import (
    _UNSEEDED_PLAN_IDS,
    _pin_start_time_to_past,
    _write_dispatch_boundaries,
    cmd_accumulate_agent_usage,
    cmd_end_phase,
    cmd_start_phase,
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


class TestRetrospectiveTokensAccumulatorCarry:
    """retrospective_tokens flows accumulate-agent-usage → accumulator file → end-phase / phase-boundary.

    The plan-retrospective dispatches under
    `--phase phase-6-finalize`, so its spend is otherwise folded silently into the
    [6-finalize] total. The finalize retrospective step seeds the per-phase
    accumulator with `accumulate-agent-usage --retrospective-tokens`; the
    end-of-phase recorder (cmd_end_phase / cmd_phase_boundary) then reads it back
    as a fallback when its own explicit flag is omitted. These assertions cover
    the full producer (accumulate) → recorder (end-phase / phase-boundary) carry.
    """

    def test_accumulate_records_retrospective_tokens(self, plan_context):
        """accumulate-agent-usage --retrospective-tokens lands in the accumulator file and result."""
        result = cmd_accumulate_agent_usage(
            ns_accumulate('retro-accum-create', '6-finalize', total_tokens=10000, retrospective_tokens=4000)
        )
        assert result['status'] == 'success'
        assert result['retrospective_tokens'] == 4000
        assert result['total_tokens'] == 10000

        acc_path = (
            plan_context.plan_dir_for('retro-accum-create') / 'work' / 'metrics-accumulator-6-finalize.toon'
        )
        content = acc_path.read_text()
        assert 'retrospective_tokens: 4000' in content

    def test_accumulate_sums_retrospective_tokens_across_calls(self, plan_context):
        """Repeated retrospective_tokens contributions sum like the other accumulator fields."""
        cmd_accumulate_agent_usage(
            ns_accumulate('retro-accum-sum', '6-finalize', retrospective_tokens=1500)
        )
        result = cmd_accumulate_agent_usage(
            ns_accumulate('retro-accum-sum', '6-finalize', retrospective_tokens=2500)
        )
        assert result['retrospective_tokens'] == 4000

    def test_accumulate_omitted_retrospective_tokens_stays_zero(self, plan_context):
        """A call without --retrospective-tokens leaves the running total at zero."""
        result = cmd_accumulate_agent_usage(
            ns_accumulate('retro-accum-omit', '6-finalize', total_tokens=500)
        )
        assert result['retrospective_tokens'] == 0

    def test_end_phase_reads_retrospective_tokens_from_accumulator(self, plan_context):
        """end-phase without --retrospective-tokens pulls it from the accumulator file."""
        cmd_start_phase(ns_start_phase('retro-ep-fallback', '6-finalize'))
        cmd_accumulate_agent_usage(
            ns_accumulate('retro-ep-fallback', '6-finalize', total_tokens=8000, retrospective_tokens=3000)
        )
        _pin_start_time_to_past('retro-ep-fallback', '6-finalize')

        result = cmd_end_phase(ns_end_phase('retro-ep-fallback', '6-finalize'))

        assert result['status'] == 'success'
        assert result['retrospective_tokens'] == 3000
        metrics = (
            plan_context.plan_dir_for('retro-ep-fallback') / 'work' / 'metrics.toon'
        ).read_text()
        assert 'retrospective_tokens: 3000' in metrics

    def test_end_phase_explicit_retrospective_tokens_overrides_accumulator(self, plan_context):
        """An explicit --retrospective-tokens flag wins over the accumulator value."""
        cmd_start_phase(ns_start_phase('retro-ep-override', '6-finalize'))
        cmd_accumulate_agent_usage(
            ns_accumulate('retro-ep-override', '6-finalize', retrospective_tokens=999)
        )
        _pin_start_time_to_past('retro-ep-override', '6-finalize')

        result = cmd_end_phase(
            ns_end_phase('retro-ep-override', '6-finalize', retrospective_tokens=5000)
        )

        assert result['retrospective_tokens'] == 5000
        metrics = (
            plan_context.plan_dir_for('retro-ep-override') / 'work' / 'metrics.toon'
        ).read_text()
        assert 'retrospective_tokens: 5000' in metrics

    def test_end_phase_no_accumulator_no_flag_omits_retrospective_tokens(self, plan_context):
        """Without an accumulator value and without the flag, the field never appears."""
        cmd_start_phase(ns_start_phase('retro-ep-absent', '6-finalize'))
        result = cmd_end_phase(ns_end_phase('retro-ep-absent', '6-finalize', total_tokens=1000))

        assert result['status'] == 'success'
        assert 'retrospective_tokens' not in result
        metrics = (
            plan_context.plan_dir_for('retro-ep-absent') / 'work' / 'metrics.toon'
        ).read_text()
        assert 'retrospective_tokens' not in metrics

    def test_end_phase_zero_accumulator_omits_retrospective_tokens(self, plan_context):
        """When the accumulator carries retrospective_tokens=0, end-phase omits the field.

        The documentation states the field should be absent when no retrospective ran.
        A zero accumulator value must not be written (it is indistinguishable from
        'no retrospective ran').
        """
        cmd_start_phase(ns_start_phase('retro-ep-zero', '6-finalize'))
        cmd_accumulate_agent_usage(
            ns_accumulate('retro-ep-zero', '6-finalize', total_tokens=5000, retrospective_tokens=0)
        )
        _pin_start_time_to_past('retro-ep-zero', '6-finalize')

        result = cmd_end_phase(ns_end_phase('retro-ep-zero', '6-finalize'))

        assert result['status'] == 'success'
        assert 'retrospective_tokens' not in result
        metrics = (
            plan_context.plan_dir_for('retro-ep-zero') / 'work' / 'metrics.toon'
        ).read_text()
        assert 'retrospective_tokens' not in metrics

    def test_phase_boundary_reads_retrospective_tokens_from_accumulator(self, plan_context):
        """phase-boundary closes the prev phase reading retrospective_tokens from its accumulator."""
        cmd_start_phase(ns_start_phase('retro-pb-fallback', '6-finalize'))
        cmd_accumulate_agent_usage(
            ns_accumulate('retro-pb-fallback', '6-finalize', total_tokens=7000, retrospective_tokens=2200)
        )
        _pin_start_time_to_past('retro-pb-fallback', '6-finalize')

        result = manage_metrics.cmd_phase_boundary(
            ns_phase_boundary('retro-pb-fallback', prev_phase='6-finalize', next_phase='6-finalize')
        )

        assert result['status'] == 'success'
        metrics = (
            plan_context.plan_dir_for('retro-pb-fallback') / 'work' / 'metrics.toon'
        ).read_text()
        assert 'retrospective_tokens: 2200' in metrics

    def test_phase_boundary_explicit_retrospective_tokens_overrides_accumulator(self, plan_context):
        """An explicit --retrospective-tokens flag on phase-boundary wins over the accumulator."""
        cmd_start_phase(ns_start_phase('retro-pb-override', '5-execute'))
        cmd_accumulate_agent_usage(
            ns_accumulate('retro-pb-override', '5-execute', retrospective_tokens=111)
        )
        _pin_start_time_to_past('retro-pb-override', '5-execute')

        result = manage_metrics.cmd_phase_boundary(
            ns_phase_boundary(
                'retro-pb-override',
                prev_phase='5-execute',
                next_phase='6-finalize',
                retrospective_tokens=6000,
            )
        )

        assert result['status'] == 'success'
        metrics = (
            plan_context.plan_dir_for('retro-pb-override') / 'work' / 'metrics.toon'
        ).read_text()
        assert 'retrospective_tokens: 6000' in metrics

    def test_phase_boundary_zero_accumulator_omits_retrospective_tokens(self, plan_context):
        """When the accumulator carries retrospective_tokens=0, phase-boundary omits the field.

        Symmetric with test_end_phase_zero_accumulator_omits_retrospective_tokens: a zero
        accumulator value must not be written to the closed phase row.
        """
        cmd_start_phase(ns_start_phase('retro-pb-zero', '6-finalize'))
        cmd_accumulate_agent_usage(
            ns_accumulate('retro-pb-zero', '6-finalize', total_tokens=4000, retrospective_tokens=0)
        )
        _pin_start_time_to_past('retro-pb-zero', '6-finalize')

        result = manage_metrics.cmd_phase_boundary(
            ns_phase_boundary('retro-pb-zero', prev_phase='6-finalize', next_phase='6-finalize')
        )

        assert result['status'] == 'success'
        metrics = (
            plan_context.plan_dir_for('retro-pb-zero') / 'work' / 'metrics.toon'
        ).read_text()
        assert 'retrospective_tokens' not in metrics


class TestClampWorkedToWall:
    """Direct, timing-independent coverage of _clamp_worked_to_wall.

    The end-phase integration tests pin start_time to the past so the clamp is a
    no-op (the back-to-back wall span is machine-dependent). These unit tests cover
    the clamp's three branches deterministically by passing phase_data explicitly.
    """

    def test_clamps_down_when_wall_span_smaller_than_worked(self):
        """When the wall span is shorter than the worked window, clamp to the wall span."""
        clamped = manage_metrics._clamp_worked_to_wall({'duration_seconds': 1.0}, 4000)
        assert clamped == 1000

    def test_returns_worked_when_wall_span_larger(self):
        """When the wall span exceeds the worked window, return the worked value unchanged."""
        clamped = manage_metrics._clamp_worked_to_wall({'duration_seconds': 600.0}, 4000)
        assert clamped == 4000

    def test_returns_worked_when_duration_seconds_absent(self):
        """Without a recorded wall span, the clamp never bounds the worked value."""
        clamped = manage_metrics._clamp_worked_to_wall({}, 4000)
        assert clamped == 4000


# =============================================================================
# Test: _reconcile_accumulator_into_phase (Tier 2 - direct call)
# =============================================================================


class TestReconcileAccumulatorIntoPhase:
    """Direct, deterministic coverage of _reconcile_accumulator_into_phase.

    The helper folds a phase's durable on-disk accumulator totals into its
    metrics row in place, with explicit-wins precedence: a field already present
    on the row (recorded by end-phase / phase-boundary) is NEVER overwritten, and
    only a truthy accumulator value backfills an absent field. These unit tests
    pass phase_data and accumulator dicts explicitly so every branch is exercised
    without touching the filesystem; TestGenerateReconcilesAccumulator covers the
    cmd_generate integration path.
    """

    def test_backfills_all_three_fields_into_unclosed_row(self):
        """An unclosed row (wall span only) is backfilled from the accumulator."""
        # duration_seconds=600 keeps the folded-duration clamp a deterministic no-op.
        phase_data = {'duration_seconds': 600}
        manage_metrics._reconcile_accumulator_into_phase(
            phase_data, {'total_tokens': 12345, 'tool_uses': 7, 'duration_ms': 60000}
        )
        assert phase_data['total_tokens'] == 12345
        assert phase_data['tool_uses'] == 7
        assert phase_data['agent_duration_ms'] == 60000
        assert phase_data['agent_duration_seconds'] == 60.0

    def test_explicit_total_tokens_is_not_overwritten(self):
        """A row that already carries total_tokens keeps its own value (explicit-wins)."""
        phase_data = {'total_tokens': 50000}
        manage_metrics._reconcile_accumulator_into_phase(phase_data, {'total_tokens': 999})
        assert phase_data['total_tokens'] == 50000

    def test_explicit_tool_uses_is_not_overwritten(self):
        """A row that already carries tool_uses keeps its own value (explicit-wins)."""
        phase_data = {'tool_uses': 30}
        manage_metrics._reconcile_accumulator_into_phase(phase_data, {'tool_uses': 9})
        assert phase_data['tool_uses'] == 30

    def test_explicit_agent_duration_ms_is_not_overwritten(self):
        """A row with agent_duration_ms is untouched — agent_duration_seconds is not added."""
        phase_data = {'duration_seconds': 600, 'agent_duration_ms': 300000}
        manage_metrics._reconcile_accumulator_into_phase(phase_data, {'duration_ms': 99999})
        assert phase_data['agent_duration_ms'] == 300000
        assert 'agent_duration_seconds' not in phase_data

    def test_empty_accumulator_is_a_noop(self):
        """An absent/empty accumulator leaves the row unchanged."""
        phase_data = {'duration_seconds': 600}
        manage_metrics._reconcile_accumulator_into_phase(phase_data, {})
        assert phase_data == {'duration_seconds': 600}

    def test_zero_accumulator_values_are_not_backfilled(self):
        """Falsy accumulator values (zero) never backfill — indistinguishable from absent."""
        phase_data = {'duration_seconds': 600}
        manage_metrics._reconcile_accumulator_into_phase(
            phase_data, {'total_tokens': 0, 'tool_uses': 0, 'duration_ms': 0}
        )
        assert 'total_tokens' not in phase_data
        assert 'tool_uses' not in phase_data
        assert 'agent_duration_ms' not in phase_data

    def test_partial_backfill_only_absent_fields(self):
        """Only the absent fields are folded; present fields win."""
        phase_data = {'duration_seconds': 600, 'total_tokens': 50000}
        manage_metrics._reconcile_accumulator_into_phase(
            phase_data, {'total_tokens': 999, 'tool_uses': 7}
        )
        assert phase_data['total_tokens'] == 50000  # explicit wins
        assert phase_data['tool_uses'] == 7  # absent → folded

    def test_duration_clamped_to_wall_span_during_fold(self):
        """A folded duration_ms is clamped to the row's wall span."""
        phase_data = {'duration_seconds': 1.0}
        manage_metrics._reconcile_accumulator_into_phase(phase_data, {'duration_ms': 4000})
        assert phase_data['agent_duration_ms'] == 1000
        assert phase_data['agent_duration_seconds'] == 1.0

    def test_duration_unclamped_when_wall_span_absent(self):
        """Without a recorded wall span the folded duration flows through unclamped."""
        phase_data: dict = {}
        manage_metrics._reconcile_accumulator_into_phase(phase_data, {'duration_ms': 4000})
        assert phase_data['agent_duration_ms'] == 4000
        assert phase_data['agent_duration_seconds'] == 4.0


class TestReadDispatchBoundaryTotals:
    """Direct coverage of the _read_dispatch_boundary_totals reader.

    The reader returns ``(sum, rows_counted)``: the sum alone cannot state its own
    coverage, and the row count is what lets the reconciliation mark the measure
    partial and refuse it the maximum.
    """

    def test_sums_total_tokens_column_across_rows(self, plan_context):
        """The reader sums the total_tokens column (position 2) across all data rows."""
        _write_dispatch_boundaries(plan_context, 'db-read-sum', '5-execute', [1_000_000, 1_000_000])
        assert manage_metrics._read_dispatch_boundary_totals('db-read-sum', '5-execute') == (
            2_000_000,
            2,
        )

    def test_absent_file_returns_zero(self, plan_context):
        """A missing boundary file reads as (0, 0) — the caller's clean no-op signal."""
        assert manage_metrics._read_dispatch_boundary_totals('db-read-absent', '5-execute') == (0, 0)

    def test_header_and_malformed_rows_are_skipped(self, plan_context):
        """Header lines and a short/malformed data row are skipped, not summed or fatal."""
        path = manage_metrics._dispatch_boundary_path('db-read-malformed', '5-execute')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            'plan_id: db-read-malformed\n'
            'phase: 5-execute\n'
            'rows[]{timestamp,termination_cause,total_tokens}:\n'
            '2026-05-08T14:00:11Z,budget_yield,500\n'
            'too,short\n'
            '2026-05-08T14:01:11Z,budget_yield,not_an_int,x,y\n'
            '2026-05-08T14:02:11Z,budget_yield,700\n',
            encoding='utf-8',
        )
        # Only the two well-formed integer rows (500 + 700) contribute — and the
        # row count reports 2, not the 4 lines the file holds, so a malformed row
        # cannot inflate the measure's apparent coverage.
        assert manage_metrics._read_dispatch_boundary_totals('db-read-malformed', '5-execute') == (
            1200,
            2,
        )

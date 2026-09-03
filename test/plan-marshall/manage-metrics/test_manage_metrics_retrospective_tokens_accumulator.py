#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-metrics.py CLI script.

Its sections, in order:

* accumulate-agent-usage (Tier 2 - direct import)
* end-phase accumulator fallback (Tier 2 - direct import)
"""


from _manage_metrics_fixtures import (
    ns_accumulate,
    ns_end_phase,
    ns_phase_boundary,
    ns_start_phase,
    raw_ns,
)
from _manage_metrics_module_fixtures import (
    _UNSEEDED_PLAN_IDS,
    _pin_start_time_to_past,
    _seed_guarded_plan_dirs,
    cmd_accumulate_agent_usage,
    cmd_end_phase,
    cmd_start_phase,
    manage_metrics,
)

# =============================================================================
# Test: accumulate-agent-usage (Tier 2 - direct import)
# =============================================================================


class TestAccumulateAgentUsage:
    """Cover the accumulate-agent-usage subcommand: file create, sum, isolate."""

    def test_creates_file_when_absent(self, plan_context):
        """First call creates the per-phase accumulator file with the supplied totals."""
        result = cmd_accumulate_agent_usage(
            ns_accumulate('accum-create', '6-finalize', total_tokens=12345, tool_uses=7, duration_ms=8000)
        )
        assert result['status'] == 'success'
        assert result['phase'] == '6-finalize'
        assert result['total_tokens'] == 12345
        assert result['tool_uses'] == 7
        assert result['duration_ms'] == 8000
        assert result['samples'] == 1

        acc_path = plan_context.plan_dir_for('accum-create') / 'work' / 'metrics-accumulator-6-finalize.toon'
        assert acc_path.exists(), 'Accumulator file should be created on first call'
        content = acc_path.read_text()
        assert 'plan_id: accum-create' in content
        assert 'phase: 6-finalize' in content
        assert 'total_tokens: 12345' in content
        assert 'tool_uses: 7' in content
        assert 'duration_ms: 8000' in content
        assert 'samples: 1' in content

    def test_sums_across_calls(self, plan_context):
        """Repeated calls sum the totals and increment the samples counter."""
        cmd_accumulate_agent_usage(
            ns_accumulate('accum-sum', '6-finalize', total_tokens=100, tool_uses=2, duration_ms=1000)
        )
        cmd_accumulate_agent_usage(
            ns_accumulate('accum-sum', '6-finalize', total_tokens=250, tool_uses=5, duration_ms=2500)
        )
        result = cmd_accumulate_agent_usage(
            ns_accumulate('accum-sum', '6-finalize', total_tokens=50, duration_ms=500)
        )
        assert result['total_tokens'] == 400
        assert result['tool_uses'] == 7  # third call omitted tool_uses → unchanged
        assert result['duration_ms'] == 4000
        assert result['samples'] == 3

    def test_phase_isolation(self, plan_context):
        """5-execute and 6-finalize accumulators do not collide."""
        cmd_accumulate_agent_usage(ns_accumulate('accum-iso', '5-execute', total_tokens=1000, tool_uses=10))
        cmd_accumulate_agent_usage(ns_accumulate('accum-iso', '6-finalize', total_tokens=2000, tool_uses=20))

        five = (plan_context.plan_dir_for('accum-iso') / 'work' / 'metrics-accumulator-5-execute.toon').read_text()
        six = (plan_context.plan_dir_for('accum-iso') / 'work' / 'metrics-accumulator-6-finalize.toon').read_text()
        assert 'total_tokens: 1000' in five
        assert 'tool_uses: 10' in five
        assert 'total_tokens: 2000' in six
        assert 'tool_uses: 20' in six

    def test_invalid_phase_rejected(self, plan_context):
        """Unknown phase names produce a structured error response."""
        result = cmd_accumulate_agent_usage(
            raw_ns(
                'accumulate-agent-usage',
                plan_id='accum-bad',
                phase='not-a-phase',
                total_tokens=1,
                tool_uses=None,
                duration_ms=None,
                retrospective_tokens=None,
            )
        )
        assert result['status'] == 'error'
        assert result['error'] == 'invalid_phase'

    def test_omitted_flags_leave_existing_totals_unchanged(self, plan_context):
        """A no-flag call still increments samples but leaves totals untouched."""
        cmd_accumulate_agent_usage(
            ns_accumulate('accum-noop', '6-finalize', total_tokens=42, tool_uses=3, duration_ms=999)
        )
        result = cmd_accumulate_agent_usage(ns_accumulate('accum-noop', '6-finalize'))
        assert result['total_tokens'] == 42
        assert result['tool_uses'] == 3
        assert result['duration_ms'] == 999
        assert result['samples'] == 2


# =============================================================================
# Test: end-phase accumulator fallback (Tier 2 - direct import)
# =============================================================================

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

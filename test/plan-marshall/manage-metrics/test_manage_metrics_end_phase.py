#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-metrics.py CLI script.

Its sections, in order:

* start-phase (Tier 2 - direct import)
* end-phase (Tier 2 - direct import)
* end-phase accumulator fallback (Tier 2 - direct import)
* generate (Tier 2 - direct import)
"""


import pytest
from _manage_metrics_fixtures import (
    ns_accumulate,
    ns_end_phase,
    ns_generate,
    ns_start_phase,
    raw_ns,
)
from _manage_metrics_module_fixtures import (  # noqa: F401 — a fixture is used by NAME, not by reference
    _UNSEEDED_PLAN_IDS,
    _phase_breakdown_header,
    _pin_start_time_to_past,
    _seed_guarded_plan_dirs,
    cmd_accumulate_agent_usage,
    cmd_end_phase,
    cmd_generate,
    cmd_start_phase,
    manage_metrics,
)

# =============================================================================
# Test: start-phase (Tier 2 - direct import)
# =============================================================================


def test_start_phase_records_timestamp(plan_context):
    """start-phase creates metrics.toon with phase start timestamp."""
    result = cmd_start_phase(ns_start_phase('metrics-start-01', '1-init'))
    assert result['status'] == 'success'
    assert result['phase'] == '1-init'
    assert 'start_time' in result

    # Verify file was written
    metrics_file = plan_context.plan_dir_for('metrics-start-01') / 'work' / 'metrics.toon'
    assert metrics_file.exists(), 'metrics.toon should be created'
    content = metrics_file.read_text()
    assert '[1-init]' in content
    assert 'start_time:' in content


def test_start_phase_invalid_phase(plan_context):
    """start-phase rejects invalid phase names."""
    result = cmd_start_phase(
        raw_ns('start-phase', plan_id='metrics-start-02', phase='invalid')
    )
    assert result['status'] == 'error'
    assert 'Invalid phase' in str(result.get('message', ''))


def test_start_phase_invalid_plan_id(plan_context):
    """start-phase rejects invalid plan IDs (sys.exit(1) from require_valid_plan_id)."""
    with pytest.raises(SystemExit) as exc_info:
        cmd_start_phase(ns_start_phase('../escape', '1-init'))
    assert exc_info.value.code == 0


def test_start_phase_multiple_phases(plan_context):
    """start-phase can record multiple phases."""
    cmd_start_phase(ns_start_phase('metrics-start-03', '1-init'))
    cmd_start_phase(ns_start_phase('metrics-start-03', '2-refine'))

    metrics_file = plan_context.plan_dir_for('metrics-start-03') / 'work' / 'metrics.toon'
    content = metrics_file.read_text()
    assert '[1-init]' in content
    assert '[2-refine]' in content


# =============================================================================
# Test: end-phase (Tier 2 - direct import)
# =============================================================================


def test_end_phase_computes_duration(plan_context):
    """end-phase computes wall-clock duration from start/end."""
    cmd_start_phase(ns_start_phase('metrics-end-01', '1-init'))
    result = cmd_end_phase(ns_end_phase('metrics-end-01', '1-init'))
    assert result['status'] == 'success'
    assert 'duration_seconds' in result
    assert float(str(result['duration_seconds'])) >= 0


def test_end_phase_with_token_data(plan_context):
    """end-phase stores token data from Task agent notifications."""
    cmd_start_phase(ns_start_phase('metrics-end-02', '1-init'))
    # Pin start_time to the past so the wall span deterministically exceeds the
    # forwarded worked window — _clamp_worked_to_wall is then a no-op and the
    # forwarded 181681 ms flows through unclamped (the back-to-back wall span is
    # machine-dependent; see _pin_start_time_to_past).
    _pin_start_time_to_past('metrics-end-02', '1-init')
    result = cmd_end_phase(
        ns_end_phase('metrics-end-02', '1-init', total_tokens=25514, duration_ms=181681, tool_uses=23)
    )
    assert result['status'] == 'success'
    assert result['total_tokens'] == 25514

    # Verify stored in metrics.toon
    metrics_file = plan_context.plan_dir_for('metrics-end-02') / 'work' / 'metrics.toon'
    content = metrics_file.read_text()
    assert 'total_tokens: 25514' in content
    assert 'tool_uses: 23' in content
    assert 'agent_duration_ms: 181681' in content


def test_end_phase_without_start(plan_context):
    """end-phase works even if start-phase wasn't called (no duration computed from timestamps)."""
    result = cmd_end_phase(ns_end_phase('metrics-end-03', '2-refine', total_tokens=1000))
    assert result['status'] == 'success'
    # No duration_seconds since no start_time
    assert 'duration_seconds' not in result


def test_end_phase_no_optional_args(plan_context):
    """end-phase works without optional token data."""
    cmd_start_phase(ns_start_phase('metrics-end-04', '3-outline'))
    result = cmd_end_phase(ns_end_phase('metrics-end-04', '3-outline'))
    assert result['status'] == 'success'
    assert 'total_tokens' not in result


# =============================================================================
# Test: end-phase accumulator fallback (Tier 2 - direct import)
# =============================================================================


class TestEndPhaseAccumulatorFallback:
    """end-phase reads the per-phase accumulator file when explicit flags are omitted."""

    def test_reads_accumulator_when_flags_absent(self, plan_context):
        """end-phase without flags pulls totals from work/metrics-accumulator-{phase}.toon."""
        cmd_start_phase(ns_start_phase('ep-fallback', '6-finalize'))
        cmd_accumulate_agent_usage(
            ns_accumulate('ep-fallback', '6-finalize', total_tokens=5000, tool_uses=12, duration_ms=60000)
        )
        # Pin start_time so the clamp is a deterministic no-op (see _pin_start_time_to_past).
        _pin_start_time_to_past('ep-fallback', '6-finalize')

        result = cmd_end_phase(ns_end_phase('ep-fallback', '6-finalize'))

        assert result['status'] == 'success'
        assert result['total_tokens'] == 5000
        assert result.get('accumulator_used') is True

        metrics = (plan_context.plan_dir_for('ep-fallback') / 'work' / 'metrics.toon').read_text()
        assert 'total_tokens: 5000' in metrics
        assert 'tool_uses: 12' in metrics
        # Accumulator's worked window (60000 ms) flows through unclamped.
        assert 'agent_duration_ms: 60000' in metrics

    def test_explicit_flags_override_accumulator(self, plan_context):
        """Explicitly passed flags always win — accumulator does not double-count."""
        cmd_start_phase(ns_start_phase('ep-override', '6-finalize'))
        cmd_accumulate_agent_usage(
            ns_accumulate('ep-override', '6-finalize', total_tokens=999, tool_uses=99, duration_ms=99999)
        )

        result = cmd_end_phase(
            ns_end_phase('ep-override', '6-finalize', total_tokens=12345, tool_uses=42, duration_ms=8000)
        )

        assert result['total_tokens'] == 12345
        # accumulator_used flips only when the flag was absent
        assert result.get('accumulator_used') is None or result.get('accumulator_used') is False

    def test_partial_explicit_flags_use_accumulator_for_missing(self, plan_context):
        """end-phase fills only the omitted fields from the accumulator."""
        cmd_start_phase(ns_start_phase('ep-partial', '6-finalize'))
        cmd_accumulate_agent_usage(
            ns_accumulate('ep-partial', '6-finalize', total_tokens=7777, tool_uses=20, duration_ms=4000)
        )
        # Pin start_time so the clamp is a deterministic no-op (see _pin_start_time_to_past).
        _pin_start_time_to_past('ep-partial', '6-finalize')

        # Pass only --total-tokens; --tool-uses / --duration-ms must come from accumulator.
        result = cmd_end_phase(ns_end_phase('ep-partial', '6-finalize', total_tokens=10000))

        assert result['total_tokens'] == 10000
        metrics = (plan_context.plan_dir_for('ep-partial') / 'work' / 'metrics.toon').read_text()
        assert 'total_tokens: 10000' in metrics
        assert 'tool_uses: 20' in metrics
        # Accumulator's worked window (4000 ms) flows through unclamped.
        assert 'agent_duration_ms: 4000' in metrics

    def test_no_accumulator_no_flags_records_timestamps_only(self, plan_context):
        """When neither accumulator nor flags are present, end-phase records timestamps only."""
        cmd_start_phase(ns_start_phase('ep-bare', '6-finalize'))
        result = cmd_end_phase(ns_end_phase('ep-bare', '6-finalize'))
        assert result['status'] == 'success'
        assert 'total_tokens' not in result

        metrics = (plan_context.plan_dir_for('ep-bare') / 'work' / 'metrics.toon').read_text()
        # No token data should be present, but end_time should be recorded
        assert 'end_time' in metrics
        assert 'total_tokens' not in metrics


# =============================================================================
# Test: generate (Tier 2 - direct import)
# =============================================================================


def test_generate_creates_metrics_md(plan_context):
    """generate creates metrics.md with the three-column phase breakdown table."""
    # Record two phases
    cmd_start_phase(ns_start_phase('metrics-gen-01', '1-init'))
    cmd_end_phase(ns_end_phase('metrics-gen-01', '1-init', total_tokens=25000, tool_uses=20))
    cmd_start_phase(ns_start_phase('metrics-gen-01', '2-refine'))
    cmd_end_phase(ns_end_phase('metrics-gen-01', '2-refine'))

    # Generate report
    result = cmd_generate(ns_generate('metrics-gen-01'))
    assert result['status'] == 'success'
    assert result['phases_recorded'] == 2
    assert result['total_tokens'] == 25000
    # Pre-formatted display fields are populated alongside the raw values.
    assert isinstance(result['total_worked_formatted'], str)
    assert isinstance(result['total_wall_formatted'], str)
    assert isinstance(result['total_idle_formatted'], str)
    assert result['total_tokens_formatted'] == '25K'

    # Verify metrics.md content
    md_path = plan_context.plan_dir_for('metrics-gen-01') / 'metrics.md'
    assert md_path.exists(), 'metrics.md should be created'
    md_content = md_path.read_text()
    assert '# Metrics: metrics-gen-01' in md_content
    assert '## Phase Breakdown' in md_content
    # Header is padded to uniform per-column width; check for the column names rather
    # than the exact unpadded string.
    assert '| Phase' in md_content
    assert '| Worked' in md_content
    assert '| Reported (wall)' in md_content
    assert '| Idle' in md_content
    assert '| Tokens' in md_content and '| Tool Uses' in md_content
    # The legacy single Duration column is gone.
    assert '| Duration ' not in md_content
    assert '1-init' in md_content
    assert '2-refine' in md_content
    assert '25,000' in md_content
    assert '**Total**' in md_content


def test_generate_three_column_header_order(plan_context):
    """The Phase Breakdown header lists the columns in their contract order.

    Worked, Reported (wall), Idle come first, then the two work measures, then
    the derived-cost column — which is last precisely because it is not a work
    measure and must not read as one.

    The Tokens header is asserted as a LITERAL, not read back from
    ``_TOKENS_COLUMN_HEADER``: the rendered string is a reader-facing contract,
    and deriving the expectation from the constant under test would assert only
    that the code equals itself.
    """
    cmd_start_phase(ns_start_phase('metrics-gen-cols', '1-init'))
    cmd_end_phase(ns_end_phase('metrics-gen-cols', '1-init', total_tokens=1000, tool_uses=3))
    cmd_generate(ns_generate('metrics-gen-cols'))

    header = _phase_breakdown_header((plan_context.plan_dir_for('metrics-gen-cols') / 'metrics.md').read_text())
    cols = [c.strip() for c in header.strip('|').split('|')]
    assert cols == [
        'Phase',
        'Worked',
        'Reported (wall)',
        'Idle',
        'Tokens (dispatched unless marked)',
        'Tool Uses',
        'Billing (cost)',
    ]


def test_generate_worked_rollup_uses_max_not_sum(plan_context):
    """Worked time = max(agent_duration_ms, subagent_duration_ms) — never additive.

    The prior additive formula double-counted the orchestrator/subagent overlap
    span (the orchestrator is awaiting the subagent return, not doing
    independent compute) and could produce ``Worked > Reported (wall)``,
    breaking the per-phase ``Worked <= wall`` invariant and forcing Idle to
    clamp to zero. The max(...) form lets the longer attribution subsume the
    shorter overlap.
    """
    # Seed metrics.toon directly so the exact field set is deterministic.
    # wall = 120s; agent = 60s; subagent = 90s. With the additive formula
    # this would yield worked=150s > wall=120s (invariant violation). With
    # max(...), worked=90s and the invariant holds.
    manage_metrics.write_metrics(
        'metrics-gen-worked',
        {
            'phases': {
                '5-execute': {
                    'duration_seconds': 120,
                    'agent_duration_ms': 60000,
                    'subagent_duration_ms': 90000,
                },
            },
        },
    )

    result = cmd_generate(ns_generate('metrics-gen-worked'))
    assert result['status'] == 'success'
    # worked = max(60s, 90s) = 90s; wall = 120s; idle = 30s.
    assert result['total_worked_seconds'] == 90.0
    assert result['total_wall_seconds'] == 120.0
    assert result['total_idle_seconds'] == 30.0
    toon = (plan_context.plan_dir_for('metrics-gen-worked') / 'work' / 'metrics.toon').read_text()
    assert 'idle_duration_ms: 30000' in toon


def test_generate_idle_residual_and_zero_clamp(plan_context):
    """idle_duration_ms = max(0, wall_clock - worked), including the zero-clamp branch."""
    # Phase with idle time: wall-clock (300s) > worked (agent 100s + subagent 50s).
    manage_metrics.write_metrics(
        'metrics-gen-idle',
        {
            'phases': {
                '5-execute': {
                    'duration_seconds': 300,
                    'agent_duration_ms': 100000,
                    'subagent_duration_ms': 50000,
                },
            },
        },
    )

    result = cmd_generate(ns_generate('metrics-gen-idle'))
    assert result['status'] == 'success'
    toon = (plan_context.plan_dir_for('metrics-gen-idle') / 'work' / 'metrics.toon').read_text()
    # worked = max(100000, 50000) = 100000 ms; wall = 300000 ms; idle = 200000 ms.
    assert 'idle_duration_ms: 200000' in toon
    assert result['total_idle_seconds'] == 200.0
    assert result['total_worked_seconds'] == 100.0
    assert result['total_wall_seconds'] == 300.0

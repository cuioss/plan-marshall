#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-metrics.py CLI script."""


import pytest
from _manage_metrics_fixtures import (
    ns_accumulate,
    ns_end_phase,
    ns_enrich,
    ns_generate,
    ns_start_phase,
    raw_ns,
)
from _manage_metrics_module_fixtures import (
    _UNSEEDED_PLAN_IDS,
    SCRIPT_PATH,
    _pin_start_time_to_past,
    cmd_accumulate_agent_usage,
    cmd_end_phase,
    cmd_enrich,
    cmd_generate,
    cmd_start_phase,
    manage_metrics,
)

from conftest import run_script  # noqa: I001


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


def test_generate_total_row_sums_three_columns_independently(plan_context):
    """The Total row sums Worked, Reported (wall), and Idle independently."""
    manage_metrics.write_metrics(
        'metrics-gen-total',
        {
            'phases': {
                '1-init': {'duration_seconds': 200, 'agent_duration_ms': 120000},
                '2-refine': {'duration_seconds': 100, 'agent_duration_ms': 40000},
            },
        },
    )

    result = cmd_generate(ns_generate('metrics-gen-total'))
    assert result['status'] == 'success'
    # worked total = 120 + 40 = 160 s; wall total = 200 + 100 = 300 s;
    # idle total = (200-120) + (100-40) = 80 + 60 = 140 s.
    assert result['total_worked_seconds'] == 160.0
    assert result['total_wall_seconds'] == 300.0
    assert result['total_idle_seconds'] == 140.0


def test_generate_no_data(plan_context):
    """generate returns error when no metrics data exists."""
    result = cmd_generate(ns_generate('metrics-gen-02'))
    assert result['status'] == 'error'
    assert 'No metrics data' in str(result.get('message', ''))


def test_generate_all_six_phases(plan_context):
    """generate handles all 6 phases."""
    phases = ['1-init', '2-refine', '3-outline', '4-plan', '5-execute', '6-finalize']
    for phase in phases:
        cmd_start_phase(ns_start_phase('metrics-gen-03', phase))
        cmd_end_phase(ns_end_phase('metrics-gen-03', phase))

    result = cmd_generate(ns_generate('metrics-gen-03'))
    assert result['status'] == 'success'
    assert result['phases_recorded'] == 6

    md_content = (plan_context.plan_dir_for('metrics-gen-03') / 'metrics.md').read_text()
    for phase in phases:
        assert phase in md_content


# =============================================================================
# Test: enrich (Tier 2 - direct import)
# =============================================================================


def test_enrich_missing_transcript(plan_context):
    """enrich returns gracefully when transcript is not found."""
    result = cmd_enrich(ns_enrich('metrics-enrich-01', 'nonexistent-session-id'))
    assert result['status'] == 'success'
    assert result.get('enriched') is False


def test_enrich_with_unknown_session(plan_context):
    """enrich handles unknown session ID gracefully."""
    result = cmd_enrich(ns_enrich('metrics-enrich-02', 'test-session-abc123'))
    # Will be 'not found' since session doesn't exist in ~/.claude
    assert result['status'] == 'success'


# =============================================================================
# Test: format_duration (via generate output) (Tier 2 - direct import)
# =============================================================================


def test_format_duration_seconds(plan_context):
    """Duration under 60s shows as seconds."""
    cmd_start_phase(ns_start_phase('metrics-fmt-01', '1-init'))
    cmd_end_phase(ns_end_phase('metrics-fmt-01', '1-init'))
    cmd_generate(ns_generate('metrics-fmt-01'))
    md_content = (plan_context.plan_dir_for('metrics-fmt-01') / 'metrics.md').read_text()
    # Should contain some duration string (likely very small since start/end are near-instant)
    assert '1-init' in md_content


# =============================================================================
# CLI Plumbing Tests (Tier 3 - subprocess, retained for end-to-end coverage)
# =============================================================================


def test_cli_start_phase_roundtrip(plan_context):
    """CLI plumbing: start-phase subcommand produces TOON output via subprocess."""
    from toon_parser import parse_toon

    # The subprocess runs the REAL require_plan_exists guard (the autouse
    # in-process monkeypatch does not reach a child process), so the plan must
    # carry a status.json sentinel on disk before the call.
    (plan_context.plan_dir_for('cli-plumb-01') / 'status.json').write_text('{}', encoding='utf-8')
    result = run_script(SCRIPT_PATH, 'start-phase', '--plan-id', 'cli-plumb-01', '--phase', '1-init')
    assert result.success, f'Script failed: {result.stderr}'
    parsed = parse_toon(result.stdout)
    assert parsed['status'] == 'success'
    assert parsed['phase'] == '1-init'


def test_cli_generate_roundtrip(plan_context):
    """CLI plumbing: generate subcommand produces TOON output via subprocess."""
    from toon_parser import parse_toon

    # Seed the status.json sentinel on disk: the subprocess runs the real
    # require_plan_exists guard (the autouse monkeypatch is in-process only).
    (plan_context.plan_dir_for('cli-plumb-02') / 'status.json').write_text('{}', encoding='utf-8')
    run_script(SCRIPT_PATH, 'start-phase', '--plan-id', 'cli-plumb-02', '--phase', '1-init')
    run_script(SCRIPT_PATH, 'end-phase', '--plan-id', 'cli-plumb-02', '--phase', '1-init')
    result = run_script(SCRIPT_PATH, 'generate', '--plan-id', 'cli-plumb-02')
    assert result.success, f'Script failed: {result.stderr}'
    parsed = parse_toon(result.stdout)
    assert parsed['status'] == 'success'
    assert parsed['phases_recorded'] == 1


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

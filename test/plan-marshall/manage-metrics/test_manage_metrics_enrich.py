#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-metrics.py CLI script.

Its sections, in order:

* enrich (Tier 2 - direct import)
* enrich delegates to the platform-runtime normalized-tokens op
* total_tokens population labelling
* format_duration (via generate output) (Tier 2 - direct import)
* CLI Plumbing Tests (Tier 3 - subprocess, retained for end-to-end coverage)
"""


from _manage_metrics_fixtures import (
    ns_end_phase,
    ns_enrich,
    ns_generate,
    ns_start_phase,
)
from _manage_metrics_module_fixtures import (
    _ENRICH_TWO_PHASE_METRICS,
    _INLINE_BUCKET,
    _INLINE_SUM,
    _UNSEEDED_PLAN_IDS,
    SCRIPT_PATH,
    _patch_runtime_op,
    _phase_row,
    _run_enrich_with_buckets,
    _seed_guarded_plan_dirs,
    cmd_end_phase,
    cmd_enrich,
    cmd_generate,
    cmd_start_phase,
    manage_metrics,
)

from conftest import run_script

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
# Test: enrich delegates to the platform-runtime normalized-tokens op
# =============================================================================

class TestEnrichDelegatesToRuntimeOp:
    """cmd_enrich consumes the runtime op's normalized per-phase numbers."""

    def test_persists_normalized_four_fields_and_billing_total(self, plan_context, monkeypatch):
        """A success op response is persisted into the plan's metrics phase row."""
        plan_dir = plan_context.plan_dir_for('enrich-delegate-01')
        manage_metrics.write_metrics(
            'enrich-delegate-01',
            {'plan_id': 'enrich-delegate-01'},
        )
        # Seed the phase window the op will be handed.
        (plan_dir / 'work').mkdir(parents=True, exist_ok=True)
        (plan_dir / 'work' / 'metrics.toon').write_text(
            _ENRICH_TWO_PHASE_METRICS.format(plan_id='enrich-delegate-01'), encoding='utf-8'
        )

        per_phase = {
            '5-execute': {
                'input': 1000,
                'output': 200,
                'cache_read': 10000,
                'cache_creation': 400,
                'input_tokens': 1000,
                'output_tokens': 200,
                'cache_read_input_tokens': 10000,
                'cache_creation_input_tokens': 400,
                'billing_weighted_total': 2700,
                'total': 2700,
                'subagent_total_tokens': 7000,
                'subagent_tool_uses': 6,
                'subagent_duration_ms': 30000,
                'subagent_samples': 1,
            }
        }
        _patch_runtime_op(
            monkeypatch,
            status='success',
            per_phase=per_phase,
            counters={
                'message_count': 4,
                'subagent_phases_attributed': 1,
                'subagent_calls_attributed': 1,
                'subagent_transcripts_walked': 1,
                'four_field_phases_attributed': 1,
            },
        )

        result = cmd_enrich(ns_enrich('enrich-delegate-01', 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'))

        assert result['status'] == 'success'
        assert result['enriched'] is True
        assert result['message_count'] == 4
        assert result['subagent_transcripts_walked'] == 1
        assert result['four_field_phases_attributed'] == 1

        five = manage_metrics.read_metrics_raw('enrich-delegate-01')['phases']['5-execute']
        assert five['input_tokens'] == 1000
        assert five['output_tokens'] == 200
        assert five['cache_read_input_tokens'] == 10000
        assert five['cache_creation_input_tokens'] == 400
        assert five['billing_weighted_total'] == 2700
        assert five['subagent_total_tokens'] == 7000
        assert five['subagent_tool_uses'] == 6
        assert five['subagent_duration_ms'] == 30000
        assert five['subagent_samples'] == 1

    def test_noop_response_degrades_gracefully(self, plan_context, monkeypatch):
        """A `no-op` op response (no transcript) yields enriched=False, no persistence."""
        manage_metrics.write_metrics('enrich-delegate-02', {'plan_id': 'enrich-delegate-02'})
        _patch_runtime_op(monkeypatch, status='no-op', per_phase=None, counters={})

        result = cmd_enrich(ns_enrich('enrich-delegate-02', 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'))

        assert result['status'] == 'success'
        assert result['enriched'] is False
        # No four-field data should have been written.
        phases = manage_metrics.read_metrics_raw('enrich-delegate-02').get('phases', {})
        five = phases.get('5-execute', {})
        assert 'input_tokens' not in five

    def test_op_invocation_failure_degrades_gracefully(self, plan_context, monkeypatch):
        """When the subprocess raises, cmd_enrich reports enriched=False (no crash)."""
        manage_metrics.write_metrics('enrich-delegate-03', {'plan_id': 'enrich-delegate-03'})

        def _raise(*args, **kwargs):  # deliberately unannotated: it accepts whatever the patched call passes
            raise OSError('boom')

        monkeypatch.setattr(manage_metrics.subprocess, 'run', _raise)

        result = cmd_enrich(ns_enrich('enrich-delegate-03', 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'))

        assert result['status'] == 'success'
        assert result['enriched'] is False

    def test_non_dict_phase_bucket_is_skipped_without_raising(self, plan_context, monkeypatch):
        """A non-dict per-phase bucket value is skipped, not crashed on (TypeError guard)."""
        plan_dir = plan_context.plan_dir_for('enrich-delegate-04')
        manage_metrics.write_metrics('enrich-delegate-04', {'plan_id': 'enrich-delegate-04'})
        (plan_dir / 'work').mkdir(parents=True, exist_ok=True)
        (plan_dir / 'work' / 'metrics.toon').write_text(
            _ENRICH_TWO_PHASE_METRICS.format(plan_id='enrich-delegate-04'), encoding='utf-8'
        )

        # A malformed op sidecar: one valid bucket and one non-dict bucket value.
        per_phase = {
            '5-execute': {
                'input_tokens': 50,
                'output_tokens': 10,
                'billing_weighted_total': 60,
                'total': 60,
            },
            '6-finalize': 'not-a-dict',
        }
        _patch_runtime_op(
            monkeypatch,
            status='success',
            per_phase=per_phase,
            counters={'message_count': 1},
        )

        # Must not raise on the non-dict bucket.
        result = cmd_enrich(ns_enrich('enrich-delegate-04', 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'))

        assert result['status'] == 'success'
        phases = manage_metrics.read_metrics_raw('enrich-delegate-04')['phases']
        # The valid bucket was persisted; the non-dict bucket was skipped.
        assert phases['5-execute']['input_tokens'] == 50
        assert 'input_tokens' not in phases.get('6-finalize', {})


# =============================================================================
# total_tokens population labelling
# =============================================================================

def test_enrich_labels_a_zero_dispatch_phase_as_inline(plan_context, monkeypatch):
    """The inline fold still happens — and the row says so, twice.

    The folded figure lands in `total_tokens` (so the phase stays countable) AND
    under its own population-honest name `inline_main_context_tokens`, with
    `total_tokens_population: inline` naming which population `total_tokens`
    measures here. Reading the figure ONLY through the dispatched-population
    field is what the second record removes.
    """
    plan_id = 'population-inline-only'
    cmd_start_phase(ns_start_phase(plan_id, '1-init'))
    cmd_end_phase(ns_end_phase(plan_id, '1-init'))

    assert _run_enrich_with_buckets(plan_id, monkeypatch, {'1-init': _INLINE_BUCKET})['enriched']

    row = _phase_row(plan_id, '1-init')
    assert row['total_tokens'] == _INLINE_SUM
    assert row['inline_main_context_tokens'] == _INLINE_SUM
    assert row['total_tokens_population'] == manage_metrics.POPULATION_INLINE


def test_enrich_labels_a_dispatched_plus_inline_phase_as_mixed(plan_context, monkeypatch):
    """A mixed phase keeps its dispatched total and records the inline part apart.

    `total_tokens` stays byte-identical (explicit-wins), the inline spend is a
    separate field of a different population, and the row reads `mixed` so a
    consumer knows the dispatched figure does NOT cover the whole phase.
    """
    plan_id = 'population-mixed'
    cmd_start_phase(ns_start_phase(plan_id, '6-finalize'))
    cmd_end_phase(ns_end_phase(plan_id, '6-finalize', total_tokens=88000))

    _run_enrich_with_buckets(plan_id, monkeypatch, {'6-finalize': _INLINE_BUCKET})

    row = _phase_row(plan_id, '6-finalize')
    assert row['total_tokens'] == 88000, 'the dispatched total must never be overwritten'
    assert row['inline_main_context_tokens'] == _INLINE_SUM
    assert row['total_tokens_population'] == manage_metrics.POPULATION_MIXED


def test_enrich_labels_a_dispatch_only_phase_as_dispatched(plan_context, monkeypatch):
    """No inline attribution → the row is labelled dispatched and carries no inline field."""
    plan_id = 'population-dispatched'
    cmd_start_phase(ns_start_phase(plan_id, '5-execute'))
    cmd_end_phase(ns_end_phase(plan_id, '5-execute', total_tokens=42000))

    _run_enrich_with_buckets(
        plan_id, monkeypatch, {'5-execute': {'cache_read_input_tokens': 250000}}
    )

    row = _phase_row(plan_id, '5-execute')
    assert row['total_tokens'] == 42000
    assert 'inline_main_context_tokens' not in row
    assert row['total_tokens_population'] == manage_metrics.POPULATION_DISPATCHED


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

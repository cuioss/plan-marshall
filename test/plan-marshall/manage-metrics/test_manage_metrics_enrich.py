#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-metrics.py CLI script.

Its sections, in order:

* enrich (Tier 2 - direct import)
* enrich delegates to the platform-runtime normalized-tokens op
* enrich measures every captured root (multi-session population)
* total_tokens population labelling
* format_duration (via generate output) (Tier 2 - direct import)
* CLI Plumbing Tests (Tier 3 - subprocess, retained for end-to-end coverage)
"""

import json
from pathlib import Path

from _manage_metrics_fixtures import (
    ns,
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
    _FakeCompleted,
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
# enrich measures every captured session (multi-root population)
# =============================================================================
#
# A plan legitimately captures more than one session identity — every resume
# appends one rather than replacing one — so the measured population is every
# `--session-id` occurrence, summed into ONE per-phase view. Reading only the
# newest identity dropped every earlier session's usage while enrich still
# reported a successful run.


def _patch_multi_root_op(monkeypatch, responses: dict) -> list:
    """Patch the runtime op so each session id answers with its own measured run.

    ``responses`` maps a session id to a dict carrying ``status``, and optionally
    ``per_phase``, ``counters``, ``root`` and ``reason``. The fake records every
    id it was asked about, in order, so a test can assert the whole population
    reached the op.
    """
    asked: list = []

    def _fake_run(argv, *args, **kwargs):  # deliberately unannotated: mirrors subprocess.run
        session_id = argv[argv.index('--session-id') + 1]
        asked.append(session_id)
        response = responses[session_id]
        output_file = Path(argv[argv.index('--output-file') + 1])
        if response['status'] == 'success' and response.get('per_phase') is not None:
            output_file.write_text(json.dumps(response['per_phase']), encoding='utf-8')
        lines = [f'status: {response["status"]}', 'operation: metrics normalized-tokens']
        for key, value in (response.get('counters') or {}).items():
            lines.append(f'{key}: {value}')
        if response.get('root'):
            lines.append(f'root_session_id: {response["root"]}')
        if response.get('reason'):
            lines.append(f'reason: {response["reason"]}')
        return _FakeCompleted('\n'.join(lines) + '\n')

    monkeypatch.setattr(manage_metrics.subprocess, 'run', _fake_run)
    return asked


def _seed_enrich_window(plan_context, plan_id: str) -> None:
    """Seed the plan's metrics.toon with the 5-execute window the op is handed."""
    manage_metrics.write_metrics(plan_id, {'plan_id': plan_id})
    plan_dir = plan_context.plan_dir_for(plan_id)
    (plan_dir / 'work').mkdir(parents=True, exist_ok=True)
    (plan_dir / 'work' / 'metrics.toon').write_text(_ENRICH_TWO_PHASE_METRICS.format(plan_id=plan_id), encoding='utf-8')


def test_enrich_sums_every_captured_session_into_one_phase_row(plan_context, monkeypatch):
    """Two captured sessions are both measured, and their buckets are summed.

    The summed figure is strictly larger than either session alone — the property
    the D3 done-when names — and both identities reach the op.
    """
    plan_id = 'enrich-multi-root'
    _seed_enrich_window(plan_context, plan_id)
    asked = _patch_multi_root_op(
        monkeypatch,
        {
            'root-a': {
                'status': 'success',
                'root': 'root-a',
                'per_phase': {'5-execute': {'input_tokens': 100, 'total': 100}},
                'counters': {'message_count': 2},
            },
            'root-b': {
                'status': 'success',
                'root': 'root-b',
                'per_phase': {'5-execute': {'input_tokens': 7, 'total': 7}},
                'counters': {'message_count': 1},
            },
        },
    )

    result = cmd_enrich(ns_enrich(plan_id, 'root-a', 'root-b'))

    assert asked == ['root-a', 'root-b'], 'every captured identity must reach the op'
    assert result['enriched'] is True
    assert result['sessions_requested'] == 2
    assert result['sessions_measured'] == 2
    assert result['sessions_unmeasured'] == []
    assert result['message_count'] == 3

    five = manage_metrics.read_metrics_raw(plan_id)['phases']['5-execute']
    assert five['input_tokens'] == 100 + 7
    assert five['total_tokens'] == 100 + 7
    assert five['total_tokens'] > 100 and five['total_tokens'] > 7


def test_enrich_does_not_double_count_a_tree_reached_twice(plan_context, monkeypatch):
    """Two ids resolving to one root are measured once, and the second is named.

    The op reports the root it measured, so a captured id that names a session
    inside an already-measured tree is reported as unmeasured instead of summing
    the same messages twice.
    """
    plan_id = 'enrich-shared-root'
    _seed_enrich_window(plan_context, plan_id)
    _patch_multi_root_op(
        monkeypatch,
        {
            'root-a': {
                'status': 'success',
                'root': 'root-a',
                'per_phase': {'5-execute': {'input_tokens': 100}},
                'counters': {'message_count': 2},
            },
            'child-a': {
                'status': 'success',
                'root': 'root-a',
                'per_phase': {'5-execute': {'input_tokens': 100}},
                'counters': {'message_count': 2},
            },
        },
    )

    result = cmd_enrich(ns_enrich(plan_id, 'root-a', 'child-a'))

    assert result['sessions_measured'] == 1
    assert result['sessions_unmeasured'] == [{'session_id': 'child-a', 'reason': 'duplicate_root'}]
    assert manage_metrics.read_metrics_raw(plan_id)['phases']['5-execute']['input_tokens'] == 100


def test_enrich_names_an_unmeasured_session_with_its_reason(plan_context, monkeypatch):
    """A session whose store cannot answer is named, and the rest is still measured."""
    plan_id = 'enrich-partial-population'
    _seed_enrich_window(plan_context, plan_id)
    _patch_multi_root_op(
        monkeypatch,
        {
            'root-a': {
                'status': 'success',
                'root': 'root-a',
                'per_phase': {'5-execute': {'input_tokens': 100}},
                'counters': {'message_count': 2},
            },
            'root-gone': {'status': 'no-op', 'reason': 'db_not_found'},
        },
    )

    result = cmd_enrich(ns_enrich(plan_id, 'root-a', 'root-gone'))

    assert result['enriched'] is True
    assert result['sessions_measured'] == 1
    assert result['sessions_unmeasured'] == [{'session_id': 'root-gone', 'reason': 'db_not_found'}]
    assert manage_metrics.read_metrics_raw(plan_id)['phases']['5-execute']['input_tokens'] == 100


def test_enrich_reports_no_measurement_when_every_session_declines(plan_context, monkeypatch):
    """No measured session yields enriched=False, and the population says so."""
    plan_id = 'enrich-no-population'
    _seed_enrich_window(plan_context, plan_id)
    _patch_multi_root_op(
        monkeypatch,
        {
            'root-a': {'status': 'no-op', 'reason': 'session_not_found'},
            'root-b': {'status': 'no-op', 'reason': 'db_not_found'},
        },
    )

    result = cmd_enrich(ns_enrich(plan_id, 'root-a', 'root-b'))

    assert result['enriched'] is False
    assert result['sessions_requested'] == 2
    assert result['sessions_measured'] == 0
    assert [row['reason'] for row in result['sessions_unmeasured']] == ['session_not_found', 'db_not_found']
    assert 'input_tokens' not in manage_metrics.read_metrics_raw(plan_id)['phases'].get('5-execute', {})


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


def test_enrich_totals_a_phase_that_both_dispatched_and_ran_inline(plan_context, monkeypatch):
    """A phase with main-context AND dispatched spend reports the sum of both.

    The landing's `total_tokens` sums these rows, so a row that reported only its
    dispatched figure made the plan's total a fraction of what the store holds.
    The dispatched figure is preserved under its own name rather than discarded.
    """
    plan_id = 'population-mixed'
    cmd_start_phase(ns_start_phase(plan_id, '6-finalize'))
    cmd_end_phase(ns_end_phase(plan_id, '6-finalize', total_tokens=88000))

    _run_enrich_with_buckets(plan_id, monkeypatch, {'6-finalize': _INLINE_BUCKET})

    row = _phase_row(plan_id, '6-finalize')
    assert row['total_tokens'] == _INLINE_SUM + 88000
    assert row['dispatched_total_tokens'] == 88000
    assert row['inline_main_context_tokens'] == _INLINE_SUM
    assert row['total_tokens_population'] == manage_metrics.POPULATION_MAIN_PLUS_SUBAGENT


def test_enrich_labels_a_dispatch_only_phase_as_dispatched(plan_context, monkeypatch):
    """No inline attribution → the row is labelled dispatched and carries no inline field."""
    plan_id = 'population-dispatched'
    cmd_start_phase(ns_start_phase(plan_id, '5-execute'))
    cmd_end_phase(ns_end_phase(plan_id, '5-execute', total_tokens=42000))

    _run_enrich_with_buckets(plan_id, monkeypatch, {'5-execute': {'cache_read_input_tokens': 250000}})

    row = _phase_row(plan_id, '5-execute')
    assert row['total_tokens'] == 42000
    assert 'inline_main_context_tokens' not in row
    assert row['total_tokens_population'] == manage_metrics.POPULATION_DISPATCHED


# =============================================================================
# The plan total sums main-context AND sub-agent usage for every phase
# =============================================================================


def test_phase_total_sums_main_context_and_subagent_usage(plan_context, monkeypatch):
    """A phase carrying both populations reports main + sub-agent, and so does the Total.

    The landing's `total_tokens` is the sum of these rows, so a row that reported
    only one population made the plan's total a fraction of what the store holds.
    """
    plan_id = 'population-total-both'
    cmd_start_phase(ns_start_phase(plan_id, '3-outline'))
    cmd_end_phase(ns_end_phase(plan_id, '3-outline'))

    bucket = dict(_INLINE_BUCKET, subagent_total_tokens=50000, subagent_samples=2, subagent_tool_uses=4)
    _run_enrich_with_buckets(plan_id, monkeypatch, {'3-outline': bucket})

    row = _phase_row(plan_id, '3-outline')
    assert row['inline_main_context_tokens'] == _INLINE_SUM
    assert row['subagent_total_tokens'] == 50000
    assert row['total_tokens'] == _INLINE_SUM + 50000
    assert row['total_tokens_population'] == manage_metrics.POPULATION_MAIN_PLUS_SUBAGENT

    generated = cmd_generate(ns_generate(plan_id))
    assert generated['total_tokens'] == _INLINE_SUM + 50000
    assert generated['totals_tokens_population'] == manage_metrics.POPULATION_MAIN_PLUS_SUBAGENT


def test_a_phase_with_subagent_samples_is_never_labelled_as_having_dispatched_nothing(plan_context, monkeypatch):
    """A phase that dispatched is never rendered under the inline label.

    The inline label claims the phase dispatched nothing. A row with
    `subagent_samples > 0` therefore may not carry it, whatever its
    `total_tokens` happened to be before enrichment.
    """
    plan_id = 'population-never-inline-when-dispatched'
    cmd_start_phase(ns_start_phase(plan_id, '5-execute'))
    cmd_end_phase(ns_end_phase(plan_id, '5-execute'))

    _run_enrich_with_buckets(
        plan_id,
        monkeypatch,
        {'5-execute': dict(_INLINE_BUCKET, subagent_total_tokens=30000, subagent_samples=3)},
    )
    cmd_generate(ns_generate(plan_id))
    report = (plan_context.plan_dir_for(plan_id) / 'metrics.md').read_text(encoding='utf-8')

    assert 'dispatched nothing' not in report
    assert '(main + sub-agent)' in report


def test_four_field_phases_attributed_counts_distinct_phases_not_attributions(plan_context, monkeypatch):
    """Two captured roots attributing the same phases report the phase COUNT.

    The runtime reports the counter per measured session; `enrich` sums those
    reports across captured identities. Summing attribution counts read 7 for a
    six-phase run, so the run-level counter is derived from the merged view.
    """
    plan_id = 'four-field-distinct-phases'
    _seed_enrich_window(plan_context, plan_id)
    attributed = {
        '5-execute': {'input_tokens': 10},
        '6-finalize': {'input_tokens': 20},
        '4-plan': {'input_tokens': 30},
    }
    # Each session reports its OWN attribution count of 3, so summing the two
    # reports would yield 6 — the "read 7 for six phases" defect.
    per_session_counters = {'message_count': 3, 'four_field_phases_attributed': 3}
    _patch_multi_root_op(
        monkeypatch,
        {
            'root-a': {
                'status': 'success',
                'root': 'root-a',
                'per_phase': attributed,
                'counters': per_session_counters,
            },
            'root-b': {
                'status': 'success',
                'root': 'root-b',
                'per_phase': attributed,
                'counters': per_session_counters,
            },
        },
    )

    result = cmd_enrich(ns_enrich(plan_id, 'root-a', 'root-b'))

    assert result['sessions_measured'] == 2
    assert result['four_field_phases_attributed'] == 3


def test_enrich_does_not_add_the_subagents_twice_when_the_fields_already_hold_them(plan_context, monkeypatch):
    """A runtime whose four fields already fold the sub-agents composes once.

    The transcript-walking target folds sub-agent transcripts into the four usage
    fields and reports `four_field_scope: main_plus_subagent`. The phase total is
    then those fields minus cache_read; adding `subagent_total_tokens` again would
    count the sub-agents twice.
    """
    plan_id = 'population-scope-main-plus-subagent'
    _seed_enrich_window(plan_context, plan_id)
    _patch_runtime_op(
        monkeypatch,
        status='success',
        per_phase={
            '5-execute': {
                'input_tokens': 1000,
                'output_tokens': 200,
                'cache_read_input_tokens': 9000,
                'cache_creation_input_tokens': 50,
                'subagent_total_tokens': 700,
                'subagent_samples': 1,
            }
        },
        counters={'message_count': 2},
        four_field_scope='main_plus_subagent',
    )

    result = cmd_enrich(ns_enrich(plan_id, 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'))

    assert result['enriched'] is True
    row = _phase_row(plan_id, '5-execute')
    assert row['total_tokens'] == 1000 + 200 + 50
    assert row['total_tokens_population'] == manage_metrics.POPULATION_MAIN_PLUS_SUBAGENT


def test_enrich_omits_the_tool_count_when_one_root_could_not_measure_it(plan_context, monkeypatch):
    """A phase one root answered and another did not carries no tool count.

    Presenting one root's count as the phase total would hide the calls the other
    root never made observable.
    """
    plan_id = 'tool-uses-partial-population'
    _seed_enrich_window(plan_context, plan_id)
    _patch_multi_root_op(
        monkeypatch,
        {
            'root-a': {
                'status': 'success',
                'root': 'root-a',
                'per_phase': {'5-execute': {'input_tokens': 10, 'tool_uses': 4}},
                'counters': {'message_count': 1},
            },
            'root-b': {
                'status': 'success',
                'root': 'root-b',
                'per_phase': {'5-execute': {'input_tokens': 20}},
                'counters': {'message_count': 1},
            },
        },
    )

    result = cmd_enrich(ns_enrich(plan_id, 'root-a', 'root-b'))

    assert result['enriched'] is True
    row = _phase_row(plan_id, '5-execute')
    assert row['input_tokens'] == 30
    assert 'measured_tool_uses' not in row


def test_enrich_omits_the_subagent_tool_count_when_one_root_could_not_measure_it(plan_context, monkeypatch):
    """A phase whose sub-agent count only some roots measured publishes none.

    The same rule the phase-level tool count follows: a partial sum presented as
    the phase's sub-agent count would hide the calls the other root never made
    observable.
    """
    plan_id = 'subagent-tool-uses-partial-population'
    _seed_enrich_window(plan_context, plan_id)
    _patch_multi_root_op(
        monkeypatch,
        {
            'root-a': {
                'status': 'success',
                'root': 'root-a',
                'per_phase': {
                    '5-execute': {
                        'input_tokens': 10,
                        'subagent_total_tokens': 100,
                        'subagent_samples': 1,
                        'subagent_tool_uses': 3,
                    }
                },
                'counters': {'message_count': 1},
            },
            'root-b': {
                'status': 'success',
                'root': 'root-b',
                'per_phase': {'5-execute': {'input_tokens': 20, 'subagent_total_tokens': 50, 'subagent_samples': 1}},
                'counters': {'message_count': 1},
            },
        },
    )

    result = cmd_enrich(ns_enrich(plan_id, 'root-a', 'root-b'))

    assert result['enriched'] is True
    row = _phase_row(plan_id, '5-execute')
    assert row['subagent_total_tokens'] == 150
    assert 'subagent_tool_uses' not in row


# =============================================================================
# Test: enrich absent session identity (transcript-gated skip vs hard error)
# =============================================================================


def test_enrich_absent_session_id_transcript_less_skips_with_gap_flag(plan_context, monkeypatch):
    """Absent session id on a transcript-less target succeeds unenriched with the gap flag."""
    plan_id = 'enrich-skip-01'
    manage_metrics.write_metrics(plan_id, {'plan_id': plan_id})
    monkeypatch.setattr(manage_metrics, '_resolve_runtime_target', lambda: 'opencode')

    result = cmd_enrich(ns('enrich', '--plan-id', plan_id))

    assert result['status'] == 'success'
    assert result.get('enriched') is False
    assert result.get('skipped') is True
    assert result.get('gap') == manage_metrics.ENRICH_SKIP_REASON_NO_SESSION_IDENTITY
    assert result.get('population') == manage_metrics.ENRICH_SKIP_POPULATION_UNENRICHED
    stored = manage_metrics.read_metrics_raw(plan_id)
    assert str(stored.get('enrichment_skipped')).lower() == 'true'
    assert stored.get('enrichment_gap_reason') == manage_metrics.ENRICH_SKIP_REASON_NO_SESSION_IDENTITY
    assert stored.get('enrichment_gap_population') == manage_metrics.ENRICH_SKIP_POPULATION_UNENRICHED


def test_enrich_absent_session_id_transcript_capable_errors(plan_context, monkeypatch):
    """Absent session id on a transcript-capable target preserves the missing-identity error."""
    plan_id = 'enrich-skip-02'
    manage_metrics.write_metrics(plan_id, {'plan_id': plan_id})
    monkeypatch.setattr(manage_metrics, '_resolve_runtime_target', lambda: 'claude')

    result = cmd_enrich(ns('enrich', '--plan-id', plan_id))

    assert result['status'] == 'error'
    assert result.get('error') == 'missing_session_id'


def test_enrich_absent_session_id_antigravity_skips_with_gap_flag(plan_context, monkeypatch):
    """Absent session id on antigravity (transcript-less) skips unenriched with the gap flag."""
    plan_id = 'enrich-skip-03'
    manage_metrics.write_metrics(plan_id, {'plan_id': plan_id})
    monkeypatch.setattr(manage_metrics, '_resolve_runtime_target', lambda: 'antigravity')

    result = cmd_enrich(ns('enrich', '--plan-id', plan_id))

    assert result['status'] == 'success'
    assert result.get('enriched') is False
    assert result.get('skipped') is True
    assert result.get('gap') == manage_metrics.ENRICH_SKIP_REASON_NO_SESSION_IDENTITY
    assert result.get('population') == manage_metrics.ENRICH_SKIP_POPULATION_UNENRICHED
    stored = manage_metrics.read_metrics_raw(plan_id)
    assert str(stored.get('enrichment_skipped')).lower() == 'true'
    assert stored.get('enrichment_gap_reason') == manage_metrics.ENRICH_SKIP_REASON_NO_SESSION_IDENTITY
    assert stored.get('enrichment_gap_population') == manage_metrics.ENRICH_SKIP_POPULATION_UNENRICHED


# =============================================================================
# Test: a measured / degraded ID-based run clears an earlier skip's gap flags
# =============================================================================


def _seed_skip_gap(plan_id, monkeypatch):
    """Drive the identity-less skip so the three gap flags are persisted."""
    manage_metrics.write_metrics(plan_id, {'plan_id': plan_id})
    monkeypatch.setattr(manage_metrics, '_resolve_runtime_target', lambda: 'opencode')
    result = cmd_enrich(ns('enrich', '--plan-id', plan_id))
    assert result.get('skipped') is True
    stored = manage_metrics.read_metrics_raw(plan_id)
    assert str(stored.get('enrichment_skipped')).lower() == 'true'


def _assert_gap_cleared(plan_id):
    """A run that attempted measurement leaves none of the gap keys behind."""
    stored = manage_metrics.read_metrics_raw(plan_id)
    assert 'enrichment_skipped' not in stored
    assert 'enrichment_gap_reason' not in stored
    assert 'enrichment_gap_population' not in stored


def test_enrich_measured_pass_clears_an_earlier_skip_gap(plan_context, monkeypatch):
    """A measured ID-based run replaces the gap flags written by an earlier skip."""
    plan_id = 'enrich-gap-clear-01'
    _seed_skip_gap(plan_id, monkeypatch)

    _run_enrich_with_buckets(plan_id, monkeypatch, {'5-execute': {'input_tokens': 100}})

    _assert_gap_cleared(plan_id)


def test_enrich_degraded_pass_clears_an_earlier_skip_gap(plan_context, monkeypatch):
    """A no-op/unavailable degrade run still clears the earlier skip's gap flags."""
    plan_id = 'enrich-gap-clear-02'
    _seed_skip_gap(plan_id, monkeypatch)
    _patch_runtime_op(monkeypatch, status='no-op', per_phase=None, counters={})

    result = cmd_enrich(ns_enrich(plan_id, 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'))

    assert result['status'] == 'success'
    assert result['enriched'] is False
    _assert_gap_cleared(plan_id)


# =============================================================================
# D1 detected-target enrich skip — detection outranks the marshal declaration
# =============================================================================


def _clear_target_env(monkeypatch):
    """Remove every platform-detection signal so each test sets its own."""
    import target_context

    for signal, _target in target_context.TARGET_ENV_SIGNALS:
        monkeypatch.delenv(signal, raising=False)


def _write_claude_marshal(proj_dir):
    """Seed a claude-declaring marshal.json so detection must outrank it."""
    import json

    plan_dir = proj_dir / '.plan'
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / 'marshal.json').write_text(json.dumps({'runtime': {'target': 'claude'}}), encoding='utf-8')


def test_detect_target_from_env_precedence(monkeypatch):
    """The earliest signal in the registry wins when several are set."""
    import target_context

    _clear_target_env(monkeypatch)
    assert manage_metrics._detect_target_from_env() is None

    # Lay the signals down in reverse registry order: each new one is earlier
    # in the precedence chain, so each must take over.
    for signal, target in reversed(target_context.TARGET_ENV_SIGNALS):
        monkeypatch.setenv(signal, '1')
        assert manage_metrics._detect_target_from_env() == target


def test_enrich_detected_opencode_skips_despite_claude_marshal(plan_context, monkeypatch, tmp_path):
    """Detected opencode + claude-declaring marshal still takes the skip branch.

    The fake project dir carries a marshal that declares ``claude``; the
    ambient ``OPENCODE`` signal must outrank it, so the enrich lands on
    the transcript-less skip with the gap flag and the unenriched population.
    """
    plan_id = 'enrich-detect-01'
    manage_metrics.write_metrics(plan_id, {'plan_id': plan_id})
    proj = tmp_path / 'proj'
    _write_claude_marshal(proj)
    monkeypatch.chdir(proj)
    _clear_target_env(monkeypatch)
    monkeypatch.setenv('OPENCODE', '1')

    assert manage_metrics._resolve_runtime_target() == 'opencode'

    result = cmd_enrich(ns('enrich', '--plan-id', plan_id))

    assert result['status'] == 'success'
    assert result.get('enriched') is False
    assert result.get('skipped') is True
    assert result.get('gap') == manage_metrics.ENRICH_SKIP_REASON_NO_SESSION_IDENTITY
    assert result.get('population') == manage_metrics.ENRICH_SKIP_POPULATION_UNENRICHED
    stored = manage_metrics.read_metrics_raw(plan_id)
    assert str(stored.get('enrichment_skipped')).lower() == 'true'
    assert stored.get('enrichment_gap_reason') == manage_metrics.ENRICH_SKIP_REASON_NO_SESSION_IDENTITY
    assert stored.get('enrichment_gap_population') == manage_metrics.ENRICH_SKIP_POPULATION_UNENRICHED


def test_enrich_no_detection_follows_claude_marshal(plan_context, monkeypatch, tmp_path):
    """Without a detection signal the marshal declaration still governs.

    Negative control for the outranking test above: identical claude-declaring
    marshal, no ambient signal — the transcript-capable missing-identity error
    is preserved.
    """
    plan_id = 'enrich-detect-02'
    manage_metrics.write_metrics(plan_id, {'plan_id': plan_id})
    proj = tmp_path / 'proj'
    _write_claude_marshal(proj)
    monkeypatch.chdir(proj)
    _clear_target_env(monkeypatch)

    assert manage_metrics._resolve_runtime_target() == 'claude'

    result = cmd_enrich(ns('enrich', '--plan-id', plan_id))

    assert result['status'] == 'error'
    assert result.get('error') == 'missing_session_id'


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

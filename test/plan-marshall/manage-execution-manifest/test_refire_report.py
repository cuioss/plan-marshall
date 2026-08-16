#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``refire-report`` subcommand of manage-execution-manifest.py.

A finalize step can fire many times in one run: the dispatcher's HEAD-advance
re-entry check re-fires every head-dependent step whose recorded SHA is
superseded, and each of the pipeline's HEAD-advancing events supersedes every
verdict recorded before it. Reducing that count needs an instrument that can
count it, and the instrument must not be a new emitter — ``record-step`` already
appends one ``execution_log[]`` row per firing, for dispatched AND inline steps
alike. This verb derives the count from those existing rows.

These tests pin the derivation and, just as importantly, its two coverage
boundaries:

- ``refires`` is ``max(0, firings - 1)`` per step, so a step that fired once
  reports zero re-fires and a step that fired seven reports six;
- a ``skipped`` row is counted separately and NEVER folded into ``firings`` — a
  skip is precisely the outcome a preserved verdict produces, so folding it in
  would make the instrument unable to measure the thing it exists to measure;
- the token column is a FLOOR (inline steps record zeros by contract), and the
  payload carries a ``token_population`` field saying so rather than presenting a
  bare number that merely looks comparable;
- ``--phase`` restricts the derivation, so a finalize figure is not inflated by
  phase-5 rows;
- rows are ordered worst-offender-first so the report reads as a diagnosis.
"""

from argparse import Namespace

import pytest

from conftest import get_script_path, load_script_module, run_script

# Script path for subprocess (CLI plumbing) tests.
SCRIPT_PATH = get_script_path('plan-marshall', 'manage-execution-manifest', 'manage-execution-manifest.py')


_mem = load_script_module(
    'plan-marshall', 'manage-execution-manifest', 'manage-execution-manifest.py', module_name='_mem_refire_script'
)
cmd_compose = _mem.cmd_compose
cmd_record_step = _mem.cmd_record_step
cmd_refire_report = _mem.cmd_refire_report
summarize_refires = _mem.summarize_refires
DEFAULT_PHASE_6_STEPS = _mem.DEFAULT_PHASE_6_STEPS

# Quiet down the best-effort decision-log writes so tests don't depend on a
# running executor / a resolvable plan log dir.
_mem._log_decision = lambda *a, **kw: None
_mem._log_record_step = lambda *a, **kw: None


# =============================================================================
# Namespace helpers
# =============================================================================


def _compose_ns(plan_id: str) -> Namespace:
    return Namespace(
        plan_id=plan_id,
        change_type='feature',
        track='complex',
        scope_estimate='multi_module',
        recipe_key=None,
        affected_files_count=5,
        phase_5_steps='quality-gate,module-tests',
        phase_6_steps=','.join(DEFAULT_PHASE_6_STEPS),
        commit_and_push=None,
    )


def _record_ns(
    plan_id: str,
    step_id: str,
    phase: str = '6-finalize',
    outcome: str = 'executed',
    total_tokens: int = 0,
    tool_uses: int = 0,
    duration_ms: int = 0,
) -> Namespace:
    return Namespace(
        plan_id=plan_id,
        step_id=step_id,
        phase=phase,
        outcome=outcome,
        total_tokens=total_tokens,
        tool_uses=tool_uses,
        duration_ms=duration_ms,
    )


def _report_ns(plan_id: str, phase: str | None = '6-finalize') -> Namespace:
    return Namespace(plan_id=plan_id, phase=phase)


def _row(step_id: str, phase: str = '6-finalize', outcome: str = 'executed', **kw) -> dict:
    return {
        'step_id': step_id,
        'phase': phase,
        'outcome': outcome,
        'total_tokens': kw.get('total_tokens', 0),
        'tool_uses': kw.get('tool_uses', 0),
        'duration_ms': kw.get('duration_ms', 0),
        'timestamp': '2026-01-01T00:00:00+00:00',
    }


# =============================================================================
# The pure derivation
# =============================================================================


def test_a_single_firing_reports_no_refire():
    steps, totals = summarize_refires([_row('push')])

    assert steps[0]['firings'] == 1
    assert steps[0]['refires'] == 0
    assert totals['refires'] == 0


def test_seven_firings_report_six_refires():
    """The observed shape: the first firing is owed, every later one is a re-fire."""
    steps, totals = summarize_refires([_row('pre-submission-self-review')] * 7)

    assert steps[0]['firings'] == 7
    assert steps[0]['refires'] == 6
    assert totals['firings'] == 7
    assert totals['refires'] == 6


def test_skipped_rows_are_never_counted_as_firings():
    """A skip is what a preserved verdict produces — counting it blinds the instrument."""
    rows = [
        _row('pre-push-quality-gate'),
        _row('pre-push-quality-gate', outcome='skipped'),
        _row('pre-push-quality-gate', outcome='skipped'),
    ]

    steps, totals = summarize_refires(rows)

    assert steps[0]['firings'] == 1
    assert steps[0]['refires'] == 0
    assert steps[0]['skipped'] == 2
    assert totals['skipped'] == 2


def test_error_rows_are_counted_separately_from_firings():
    rows = [_row('ci-verify'), _row('ci-verify', outcome='error')]

    steps, _totals = summarize_refires(rows)

    assert steps[0]['firings'] == 1
    assert steps[0]['errors'] == 1
    assert steps[0]['refires'] == 0


def test_phase_filter_excludes_other_phases():
    rows = [
        _row('quality-gate', phase='5-execute'),
        _row('quality-gate', phase='5-execute'),
        _row('push', phase='6-finalize'),
    ]

    steps, totals = summarize_refires(rows, phase='6-finalize')

    assert [s['step_id'] for s in steps] == ['push']
    assert totals['firings'] == 1


def test_rows_are_ordered_worst_offender_first():
    rows = (
        [_row('push')]
        + [_row('pre-submission-self-review')] * 7
        + [_row('finalize-step-plugin-doctor')] * 3
    )

    steps, _totals = summarize_refires(rows)

    assert [s['step_id'] for s in steps] == [
        'pre-submission-self-review',
        'finalize-step-plugin-doctor',
        'push',
    ]


def test_token_attribution_sums_across_firings():
    rows = [
        _row('sonar-roundtrip', total_tokens=100, tool_uses=2, duration_ms=10),
        _row('sonar-roundtrip', total_tokens=250, tool_uses=5, duration_ms=30),
    ]

    steps, totals = summarize_refires(rows)

    assert steps[0]['total_tokens'] == 350
    assert steps[0]['tool_uses'] == 7
    assert steps[0]['duration_ms'] == 40
    assert totals['total_tokens'] == 350


def test_malformed_rows_are_skipped_rather_than_crashing():
    """The log is append-only history; one bad row must not deny the whole report."""
    rows = [_row('push'), 'not-a-dict', {'phase': '6-finalize'}]

    steps, totals = summarize_refires(rows)

    assert [s['step_id'] for s in steps] == ['push']
    assert totals['steps'] == 1


@pytest.mark.parametrize('junk', ['not-a-number', None, [], {}, '12x'])
def test_non_numeric_metrics_contribute_zero_rather_than_raising(junk):
    """Metric coercion follows the same tolerance the row filter already has.

    ``execution_log[]`` is append-only history parsed back from TOON, so a legacy
    or hand-edited row can carry a non-numeric metric. Letting that raise would
    deny the whole plan's report over one bad row — a total outage of the
    instrument where a diagnosable gap was intended. The row still counts as a
    firing; only its unusable metric contributes ``0``.
    """
    rows = [_row('push', total_tokens=junk, tool_uses=junk, duration_ms=junk)]

    steps, totals = summarize_refires(rows)

    assert steps[0]['firings'] == 1
    assert steps[0]['total_tokens'] == 0
    assert steps[0]['tool_uses'] == 0
    assert steps[0]['duration_ms'] == 0
    assert totals['total_tokens'] == 0


def test_a_bad_metric_does_not_suppress_a_good_row():
    """The bad row is tolerated WITHOUT losing the rest of the report."""
    rows = [
        _row('push', total_tokens='junk'),
        _row('ci-verify', total_tokens=500),
    ]

    steps, totals = summarize_refires(rows)

    assert totals['steps'] == 2
    assert totals['total_tokens'] == 500


# =============================================================================
# The command over real plan state
# =============================================================================


def test_report_over_recorded_rows(plan_context):
    cmd_compose(_compose_ns('refire-plan'))
    for _ in range(3):
        cmd_record_step(_record_ns('refire-plan', 'pre-push-quality-gate', total_tokens=0))
    cmd_record_step(_record_ns('refire-plan', 'push'))

    result = cmd_refire_report(_report_ns('refire-plan'))

    assert result is not None
    assert result['status'] == 'success'
    assert result['phase'] == '6-finalize'
    assert result['totals']['refires'] == 2
    assert result['steps'][0]['step_id'] == 'pre-push-quality-gate'
    assert result['steps'][0]['refires'] == 2


def test_report_names_its_token_population(plan_context):
    """A bare number that merely looks comparable is worse than none."""
    cmd_compose(_compose_ns('refire-pop'))
    cmd_record_step(_record_ns('refire-pop', 'push'))

    result = cmd_refire_report(_report_ns('refire-pop'))

    assert result is not None
    assert 'FLOOR' in result['token_population']
    assert 'inline' in result['token_population']


def test_report_on_a_manifest_with_no_execution_log(plan_context):
    """A composed-but-unrun plan reports zeroes, not an error."""
    cmd_compose(_compose_ns('refire-empty'))

    result = cmd_refire_report(_report_ns('refire-empty'))

    assert result is not None
    assert result['status'] == 'success'
    assert result['execution_log_rows'] == 0
    assert result['steps'] == []
    assert result['totals']['refires'] == 0


def test_report_rejects_an_unknown_phase(plan_context):
    cmd_compose(_compose_ns('refire-badphase'))

    result = cmd_refire_report(_report_ns('refire-badphase', phase='9-nope'))

    assert result is not None
    assert result['status'] == 'error'
    assert result['error'] == 'invalid_phase'


def test_report_without_a_phase_covers_every_phase(plan_context):
    cmd_compose(_compose_ns('refire-allphase'))
    cmd_record_step(_record_ns('refire-allphase', 'quality-gate', phase='5-execute'))
    cmd_record_step(_record_ns('refire-allphase', 'push', phase='6-finalize'))

    result = cmd_refire_report(_report_ns('refire-allphase', phase=None))

    assert result is not None
    assert result['phase'] == 'all'
    assert result['totals']['steps'] == 2


def test_cli_roundtrip_reports_file_not_found_for_a_missing_manifest(plan_context):
    """CLI plumbing: the verb is reachable through the executor entry point."""
    result = run_script(SCRIPT_PATH, 'refire-report', '--plan-id', 'no-such-plan')

    assert 'file_not_found' in result.stdout

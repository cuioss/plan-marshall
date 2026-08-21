#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the `record-dispatch-boundary` subcommand of manage_metrics."""


from __future__ import annotations

import itertools
from datetime import UTC, datetime, timedelta

from _manage_metrics_fixtures import (
    ns_generate,
    ns_start_phase,
)
from _manage_metrics_record_dispatch_boundary_fixtures import (
    SCRIPT_PATH,
    _boundary_path,
    _data_rows,
    _ns,
    _seed_status_json,
    cmd_record_dispatch_boundary,
    manage_metrics,
)

from conftest import run_script

# =============================================================================
# Boundary-measure coverage: rows_recorded and the partiality verdict
# =============================================================================
#
# The boundary sum cannot state its own coverage. A file holding three of a
# phase's five dispatches sums to a smaller-but-honest-looking figure that is
# indistinguishable from a complete one, so the reader returns the row count
# alongside the sum and the reconciliation refuses a PARTIAL measure the maximum.

def test_reader_returns_the_row_count_alongside_the_sum(plan_context):
    """`_read_dispatch_boundary_totals` reports how many rows it summed."""
    plan_dir = plan_context.plan_dir_for('disp-rows')
    _seed_status_json(plan_dir)
    for tokens in (1000, 2000, 3000):
        cmd_record_dispatch_boundary(_ns('disp-rows', total_tokens=tokens))

    total, rows = manage_metrics._read_dispatch_boundary_totals('disp-rows', '5-execute')

    assert total == 6000
    assert rows == 3


def test_reader_reports_zero_rows_for_an_absent_file(plan_context):
    """An absent boundary file is a clean no-op in both halves of the return."""
    plan_context.plan_dir_for('disp-absent')

    assert manage_metrics._read_dispatch_boundary_totals('disp-absent', '5-execute') == (0, 0)


def test_generate_persists_the_recorded_row_count(plan_context):
    """`generate` writes `dispatch_boundary_rows_recorded` next to the sum."""
    plan_dir = plan_context.plan_dir_for('disp-persist')
    _seed_status_json(plan_dir)
    cmd_record_dispatch_boundary(_ns('disp-persist', total_tokens=1000))
    cmd_record_dispatch_boundary(_ns('disp-persist', total_tokens=2000))
    manage_metrics.cmd_start_phase(ns_start_phase('disp-persist', '5-execute'))
    manage_metrics.cmd_generate(ns_generate('disp-persist'))

    row = manage_metrics.read_metrics_raw('disp-persist')['phases']['5-execute']

    assert row['dispatch_boundary_total'] == 3000
    assert row['dispatch_boundary_rows_recorded'] == 2


def test_fewer_rows_than_dispatches_marks_the_measure_partial():
    """Coverage below `subagent_samples` is PARTIAL — the sum is a floor."""
    row = {'dispatch_boundary_rows_recorded': 3, 'subagent_samples': 5}

    assert manage_metrics._boundary_measure_is_partial(row) is True


def test_full_coverage_is_not_partial():
    """Matched control: a boundary file covering every dispatch is complete."""
    row = {'dispatch_boundary_rows_recorded': 5, 'subagent_samples': 5}

    assert manage_metrics._boundary_measure_is_partial(row) is False


def test_missing_reference_count_is_undecidable_not_partial():
    """An un-enriched row has no reference count, so coverage is undecidable.

    Undecidable must NOT read as partial: doing so would refuse the maximum on
    every un-enriched plan and lose the accumulator-under-count recovery the
    reconciliation exists for.
    """
    assert manage_metrics._boundary_measure_is_partial(
        {'dispatch_boundary_rows_recorded': 3}
    ) is None
    assert manage_metrics._boundary_measure_is_partial({'subagent_samples': 5}) is None


# =============================================================================
# (e) Missing required flags cause non-zero exit before any file write
# =============================================================================


def test_missing_required_flag_rejected_subprocess_no_file_written(plan_context):
    """Omitting --termination-cause rejects the run before any file write."""
    result = run_script(
        SCRIPT_PATH,
        'record-dispatch-boundary',
        '--plan-id',
        'disp-missing-cause',
        '--phase',
        '5-execute',
    )
    assert result.returncode != 0, 'argparse rejection MUST yield non-zero exit'
    assert not _boundary_path(plan_context.plan_dir_for('disp-missing-cause'), '5-execute').exists()


# =============================================================================
# (a) First invocation creates the artifact file with one row
# =============================================================================


def test_first_invocation_creates_file_with_one_row(plan_context):
    """The first record-dispatch-boundary call writes the header and exactly one data row."""
    plan_dir = plan_context.plan_dir_for('disp-first')
    _seed_status_json(plan_dir)
    result = cmd_record_dispatch_boundary(
        _ns(
            'disp-first',
            phase='5-execute',
            termination_cause='voluntary_checkpoint',
            total_tokens=12345,
            tool_uses=10,
            duration_ms=60000,
        )
    )

    assert result['status'] == 'success'
    assert result['phase'] == '5-execute'
    assert result['termination_cause'] == 'voluntary_checkpoint'
    assert result['total_tokens'] == 12345
    assert result['tool_uses'] == 10
    assert result['duration_ms'] == 60000
    assert result['rows_recorded'] == 1
    assert result['dispatch_boundary_file'] == 'work/metrics-dispatch-boundaries-5-execute.toon'

    path = _boundary_path(plan_dir, '5-execute')
    assert path.exists()
    content = path.read_text(encoding='utf-8')

    # Header lines present — the 9-column schema (legacy five columns followed
    # by the four appended per-dispatch context-load columns).
    assert 'plan_id: disp-first' in content
    assert 'phase: 5-execute' in content
    expected_header = (
        'rows[]{timestamp,termination_cause,total_tokens,tool_uses,duration_ms,'
        'input_tokens,output_tokens,cache_read_input_tokens,'
        'cache_creation_input_tokens}:'
    )
    assert expected_header in content

    # Exactly one data row — legacy five columns positionally unchanged, the
    # four appended context-load columns each carrying the `unmeasured` literal
    # because no flag supplied them. They are NOT `0`: the caller forwarded no
    # `message.usage` figures, and a `0` would assert a measurement never taken.
    rows = _data_rows(content)
    assert len(rows) == 1
    assert (
        ',voluntary_checkpoint,12345,10,60000,unmeasured,unmeasured,unmeasured,unmeasured'
        in rows[0]
    )
    assert ',voluntary_checkpoint,12345,10,60000,0,0,0,0' not in rows[0]
    # The unmeasured columns are ABSENT from the result, and named as such.
    for column in (
        'input_tokens',
        'output_tokens',
        'cache_read_input_tokens',
        'cache_creation_input_tokens',
    ):
        assert column not in result, column
    assert result['unmeasured_context_load_columns'] == (
        'input_tokens,output_tokens,cache_read_input_tokens,cache_creation_input_tokens'
    )


# =============================================================================
# (b) Subsequent invocations append rows in order with monotonic timestamps
# =============================================================================


def test_subsequent_invocations_append_rows_in_order_with_monotonic_timestamps(
    plan_context, monkeypatch
):
    """Successive invocations append rows in chronological order, header preserved."""
    plan_dir = plan_context.plan_dir_for('disp-append')
    _seed_status_json(plan_dir)

    # The row timestamp has iso-second granularity, so this test used to sleep
    # 1.05 s between invocations to make monotonicity observable. Inject a
    # monotonically advancing clock at the module's timestamp seam instead:
    # each call returns a timestamp one second later, which is deterministic
    # and costs no wall-clock time.
    ticks = itertools.count()

    def _advancing_now_utc_iso():
        moment = datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC) + timedelta(seconds=next(ticks))
        return moment.strftime('%Y-%m-%dT%H:%M:%SZ')

    monkeypatch.setattr(manage_metrics, 'now_utc_iso', _advancing_now_utc_iso)

    cmd_record_dispatch_boundary(
        _ns('disp-append', termination_cause='voluntary_checkpoint', total_tokens=100)
    )
    cmd_record_dispatch_boundary(
        _ns('disp-append', termination_cause='task_complete_returned_verbatim', total_tokens=200)
    )
    result = cmd_record_dispatch_boundary(
        _ns('disp-append', termination_cause='harness_cancellation', total_tokens=300)
    )

    assert result['rows_recorded'] == 3

    path = _boundary_path(plan_dir)
    content = path.read_text(encoding='utf-8')
    rows = _data_rows(content)
    assert len(rows) == 3

    # Order preserved by termination_cause column
    assert ',voluntary_checkpoint,100,' in rows[0]
    assert ',task_complete_returned_verbatim,200,' in rows[1]
    assert ',harness_cancellation,300,' in rows[2]

    # Timestamps strictly non-decreasing across appended rows
    timestamps = [row.split(',', 1)[0] for row in rows]
    assert timestamps == sorted(timestamps), (
        f'Timestamps not monotonic across appended rows: {timestamps}'
    )

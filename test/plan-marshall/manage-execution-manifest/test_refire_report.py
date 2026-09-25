# SPDX-License-Identifier: FSL-1.1-ALv2
"""Behavior-cluster tests carved from test_refire_report.py: a."""

#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_refire_report_fixtures import _row, summarize_refires

# =============================================================================
# The pure derivation
# =============================================================================


def test_a_single_firing_reports_no_refire():
    steps, totals = summarize_refires([_row('push')])

    assert steps[0]['firings'] == 1
    assert steps[0]['refires'] == 0
    assert totals['refires'] == 0



def test_a_completed_run_reports_zero_in_all_three_columns():
    """The matched control — a reader that counted every row would pass alone."""
    steps, totals = summarize_refires([_row('gate')])

    assert steps[0]['firings'] == 1
    assert (steps[0]['loop_backs'], steps[0]['failures'], steps[0]['errors']) == (0, 0, 0)
    assert (totals['loop_backs'], totals['failures'], totals['errors']) == (0, 0, 0)



def test_a_fully_measured_row_reports_no_unmeasured_columns():
    """The matched control — a reader that counted everything would pass alone."""
    rows = [_row('push', total_tokens=100, tool_uses=2, duration_ms=10)]

    steps, totals = summarize_refires(rows)

    assert steps[0]['unmeasured_columns'] == 0
    assert steps[0]['unrecognised_columns'] == 0
    assert totals['unmeasured_columns'] == 0



def test_a_boolean_cell_is_unrecognised_and_contributes_nothing():
    """⛔ `bool` subclasses `int`, so an unguarded `int(value)` reads `True` as a
    MEASURED `1` — a fabricated measurement of exactly the kind the three-state
    read exists to remove, and the more dangerous failure because it is silent.

    Reachable rather than theoretical: `execution_log[]` is parsed back from
    TOON, which yields a Python `bool` for a bare `true`, so a legacy or
    hand-edited row can carry one. Asserting the CONTRIBUTION as well as the
    state is what makes this fail against the defect — a reader that classified
    the cell correctly but still summed `1` would pass on the state alone.

    The sibling reader `_ledger_reconciliation.read_token_column` has guarded
    this since it was written; this pins the pair so the two cannot drift apart
    again.
    """
    rows = [_row('push', total_tokens=True, tool_uses=0, duration_ms=0)]

    steps, totals = summarize_refires(rows)

    assert steps[0]['unrecognised_columns'] == 1
    assert steps[0]['unmeasured_columns'] == 0
    assert steps[0]['total_tokens'] == 0
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

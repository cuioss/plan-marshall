# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_execution_manifest_refire_report_fixtures import _row, summarize_refires


def test_the_three_non_completion_outcomes_are_counted_apart():
    """⛔ A productive loop-back must never land in the error column.

    Summing loop-backs, negative verdicts and raised dispatches into one number
    is what made a thorough gate read as a defective one: the more rounds a
    self-review filed findings for, the worse any error-counting analysis
    graded its plan. One row of each proves the three columns are disjoint.
    """
    rows = [
        _row('gate', outcome='loop_back'),
        _row('gate', outcome='failed'),
        _row('gate', outcome='error'),
    ]

    steps, totals = summarize_refires(rows)

    assert steps[0]['loop_backs'] == 1
    assert steps[0]['failures'] == 1
    assert steps[0]['errors'] == 1
    assert steps[0]['firings'] == 0
    assert totals['loop_backs'] == 1
    assert totals['failures'] == 1
    assert totals['errors'] == 1

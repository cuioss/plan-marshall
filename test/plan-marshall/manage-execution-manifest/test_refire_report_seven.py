# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_execution_manifest_refire_report_fixtures import _row, summarize_refires


def test_seven_firings_report_six_refires():
    """The observed shape: the first firing is owed, every later one is a re-fire."""
    steps, totals = summarize_refires([_row('pre-submission-self-review')] * 7)

    assert steps[0]['firings'] == 7
    assert steps[0]['refires'] == 6
    assert totals['firings'] == 7
    assert totals['refires'] == 6

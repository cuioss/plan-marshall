# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_execution_manifest_refire_report_fixtures import _row, pytest, summarize_refires


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

# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_execution_manifest_refire_report_fixtures import _row, summarize_refires


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

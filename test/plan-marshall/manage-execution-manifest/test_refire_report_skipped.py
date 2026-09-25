# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_refire_report_fixtures import _row, summarize_refires


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

# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_refire_report_fixtures import _row, summarize_refires


def test_error_rows_are_counted_separately_from_firings():
    rows = [_row('ci-verify'), _row('ci-verify', outcome='error')]

    steps, _totals = summarize_refires(rows)

    assert steps[0]['firings'] == 1
    assert steps[0]['errors'] == 1
    assert steps[0]['refires'] == 0

# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_refire_report_fixtures import _row, summarize_refires


def test_rows_are_ordered_worst_offender_first():
    rows = [_row('push')] + [_row('pre-submission-self-review')] * 7 + [_row('finalize-step-plugin-doctor')] * 3

    steps, _totals = summarize_refires(rows)

    assert [s['step_id'] for s in steps] == [
        'pre-submission-self-review',
        'finalize-step-plugin-doctor',
        'push',
    ]

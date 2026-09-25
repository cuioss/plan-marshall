# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_refire_report_fixtures import _row, summarize_refires


def test_malformed_rows_are_skipped_rather_than_crashing():
    """The log is append-only history; one bad row must not deny the whole report."""
    rows = [_row('push'), 'not-a-dict', {'phase': '6-finalize'}]

    steps, totals = summarize_refires(rows)

    assert [s['step_id'] for s in steps] == ['push']
    assert totals['steps'] == 1

# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_refire_report_fixtures import _row, summarize_refires


def test_phase_filter_excludes_other_phases():
    rows = [
        _row('quality-gate', phase='5-execute'),
        _row('quality-gate', phase='5-execute'),
        _row('push', phase='6-finalize'),
    ]

    steps, totals = summarize_refires(rows, phase='6-finalize')

    assert [s['step_id'] for s in steps] == ['push']
    assert totals['firings'] == 1

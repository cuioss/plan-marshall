# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_refire_report_fixtures import _mem, _row, summarize_refires


def test_an_unmeasured_column_is_counted_not_summed_as_zero():
    """The writer's ``unmeasured`` token contributes nothing AND is counted.

    Reading the sum alone cannot distinguish "these steps spent nothing" from
    "nobody measured what these steps spent", which is exactly the fabricated
    total the token exists to remove. The per-state counts are what make the
    floor's SIZE readable rather than merely asserted in prose.
    """
    rows = [_row('push', total_tokens=_mem.UNMEASURED_COLUMN_TOKEN, tool_uses=0, duration_ms=0)]

    steps, totals = summarize_refires(rows)

    assert steps[0]['total_tokens'] == 0
    assert steps[0]['unmeasured_columns'] == 1
    assert steps[0]['unrecognised_columns'] == 0
    assert totals['unmeasured_columns'] == 1



def test_an_unreadable_cell_is_counted_as_unrecognised_not_unmeasured():
    """The third state is reported as itself rather than folded into a neighbour."""
    rows = [_row('push', total_tokens='12x', tool_uses=0, duration_ms=0)]

    steps, _totals = summarize_refires(rows)

    assert steps[0]['unrecognised_columns'] == 1
    assert steps[0]['unmeasured_columns'] == 0

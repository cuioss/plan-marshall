# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_record_step_fixtures import _record_ns


def test_the_parser_supplies_none_not_zero_for_an_omitted_flag(plan_context):
    """The discriminator lives in the PARSER's default, so it is pinned there.

    ``default=0`` would make an omitted flag reach the handler byte-identical to
    an explicit ``0``, and no care in the handler could recover the distinction.
    The handler test above cannot see that regression — it would keep passing
    while every omitted column silently became a measured zero.
    """
    omitted = _record_ns(plan_id='rec-parser', step_id='verify:quality-gate')
    supplied = _record_ns(plan_id='rec-parser', step_id='verify:quality-gate', total_tokens=0)

    assert omitted.total_tokens is None
    assert omitted.tool_uses is None
    assert omitted.duration_ms is None
    assert supplied.total_tokens == 0

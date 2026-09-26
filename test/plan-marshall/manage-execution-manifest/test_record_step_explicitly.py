# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_execution_manifest_record_step_fixtures import (
    EXECUTION_LOG_KEY,
    _compose,
    _record_ns,
    cmd_record_step,
    read_manifest,
)


def test_explicitly_passed_zero_is_a_measured_zero(plan_context):
    """``--total-tokens 0`` is a MEASUREMENT and is stored as the integer ``0``.

    A skipped step genuinely consumed nothing, and its caller says so by passing
    the flag. Nothing about that row may read as unmeasured.
    """
    _compose('rec-measured-zero')

    result = cmd_record_step(
        _record_ns(
            plan_id='rec-measured-zero',
            step_id='verify:quality-gate',
            outcome='skipped',
            total_tokens=0,
            tool_uses=0,
            duration_ms=0,
        )
    )

    assert result is not None
    assert result['total_tokens'] == 0
    assert result['tool_uses'] == 0
    assert result['duration_ms'] == 0
    entry = read_manifest('rec-measured-zero')[EXECUTION_LOG_KEY][0]
    assert entry['total_tokens'] == 0
    assert entry['tool_uses'] == 0
    assert entry['duration_ms'] == 0

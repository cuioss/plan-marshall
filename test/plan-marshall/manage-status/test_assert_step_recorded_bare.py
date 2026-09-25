# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_status_assert_step_recorded_fixtures import (
    _assert_args,
    _make_plan,
    cmd_assert_step_recorded,
    read_status,
    write_status,
)

# =============================================================================
# Near-miss orphan key -> step_record_mismatched_key
# =============================================================================


def test_only_bare_orphan_present_returns_mismatched_key(plan_context):
    """(2) When only a bare/mis-keyed orphan terminal record is present under a
    different key, --require-terminal returns step_record_mismatched_key carrying
    the orphan key and its outcome."""
    plan_id = 'assert-mismatch-orphan'
    _make_plan(plan_id)
    status = read_status(plan_id)
    status.setdefault('metadata', {})['phase_steps'] = {
        '6-finalize': {'plan-retrospective': {'outcome': 'done', 'display_detail': None}}
    }
    write_status(plan_id, status)

    result = cmd_assert_step_recorded(
        _assert_args(plan_id, '6-finalize', 'plan-marshall:plan-retrospective', require_terminal=True)
    )

    assert result['status'] == 'error'
    assert result['error'] == 'step_record_mismatched_key'
    assert result['recorded'] is False
    assert result['outcome'] is None
    assert result['orphan_key'] == 'plan-retrospective'
    assert result['orphan_outcome'] == 'done'
    assert result['phase'] == '6-finalize'
    assert result['step'] == 'plan-marshall:plan-retrospective'

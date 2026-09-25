# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_status_assert_step_recorded_fixtures import (
    _assert_args,
    _make_plan,
    cmd_assert_step_recorded,
    pytest,
    read_status,
    write_status,
)


@pytest.mark.parametrize('orphan_outcome', ['done', 'skipped', 'loop_back', 'failed'])
def test_near_miss_orphan_outcome_preserved(plan_context, orphan_outcome):
    """The mismatched-key verdict surfaces the orphan's actual terminal outcome,
    not a hard-coded 'done'. Every member of VALID_OUTCOMES under a near-miss key
    must round-trip through orphan_outcome."""
    plan_id = f'assert-near-miss-{orphan_outcome.replace("_", "-")}'
    _make_plan(plan_id)
    status = read_status(plan_id)
    status.setdefault('metadata', {})['phase_steps'] = {
        '6-finalize': {'plan-retrospective': {'outcome': orphan_outcome, 'display_detail': None}}
    }
    write_status(plan_id, status)

    result = cmd_assert_step_recorded(
        _assert_args(plan_id, '6-finalize', 'plan-marshall:plan-retrospective', require_terminal=True)
    )

    assert result['status'] == 'error'
    assert result['error'] == 'step_record_mismatched_key'
    assert result['orphan_key'] == 'plan-retrospective'
    assert result['orphan_outcome'] == orphan_outcome



def test_near_miss_message_names_both_keys(plan_context):
    """The mismatched-key message must name both the queried step_id and the
    near-miss orphan key so the dispatcher can report the mis-keying."""
    plan_id = 'assert-near-miss-message'
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
    assert 'plan-marshall:plan-retrospective' in result['message']
    assert 'plan-retrospective' in result['message']

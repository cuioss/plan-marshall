# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_status_assert_step_recorded_fixtures import (
    _assert_args,
    _make_plan,
    cmd_assert_step_recorded,
    read_status,
    write_status,
)


def test_orphan_present_without_require_terminal_does_not_flip_recorded(plan_context):
    """(4) Without --require-terminal, a present orphan under a different key does
    not flip recorded for the queried key — the default path reports the queried
    key absent without escalation."""
    plan_id = 'assert-mismatch-default'
    _make_plan(plan_id)
    status = read_status(plan_id)
    status.setdefault('metadata', {})['phase_steps'] = {
        '6-finalize': {'plan-retrospective': {'outcome': 'done', 'display_detail': None}}
    }
    write_status(plan_id, status)

    result = cmd_assert_step_recorded(
        _assert_args(plan_id, '6-finalize', 'plan-marshall:plan-retrospective', require_terminal=False)
    )

    assert result['status'] == 'success'
    assert result['recorded'] is False
    assert result['outcome'] is None
    assert 'orphan_key' not in result

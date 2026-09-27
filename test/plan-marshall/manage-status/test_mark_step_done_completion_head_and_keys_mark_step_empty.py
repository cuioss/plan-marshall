# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_status_mark_step_done_completion_head_and_keys_fixtures import _args, _make_plan, cmd_mark_step_done


def test_mark_step_empty_phase(plan_context):
    """Empty phase is rejected with invalid_argument."""
    plan_id = 'mark-step-empty-phase'
    _make_plan(plan_id)
    result = cmd_mark_step_done(_args(plan_id, '', 'step-a', 'done'))

    assert result['status'] == 'error'
    assert result['error'] == 'invalid_argument'


def test_mark_step_empty_step(plan_context):
    """Empty step is rejected with invalid_argument."""
    plan_id = 'mark-step-empty-step'
    _make_plan(plan_id)
    result = cmd_mark_step_done(_args(plan_id, '1-init', '', 'done'))

    assert result['status'] == 'error'
    assert result['error'] == 'invalid_argument'

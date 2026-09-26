# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_status_mark_step_done_fixtures import _args, _make_plan, cmd_mark_step_done, read_status


def test_mark_step_idempotent_when_facts_match(plan_context):
    """Re-call with identical outcome+detail+facts is a no-op (no file rewrite)."""
    plan_id = 'mark-step-facts-idempotent'
    _make_plan(plan_id)
    cmd_mark_step_done(
        _args(
            plan_id,
            '6-finalize',
            'push',
            'done',
            display_detail='pushed',
            fact=['work_performed=true'],
        )
    )

    updated_before = read_status(plan_id)['updated']

    second = cmd_mark_step_done(
        _args(
            plan_id,
            '6-finalize',
            'push',
            'done',
            display_detail='pushed',
            fact=['work_performed=true'],
        )
    )

    assert second['status'] == 'success'
    assert second['changed'] is False
    assert second['facts'] == {'work_performed': 'true'}
    assert 'previous_outcome' not in second

    assert read_status(plan_id)['updated'] == updated_before

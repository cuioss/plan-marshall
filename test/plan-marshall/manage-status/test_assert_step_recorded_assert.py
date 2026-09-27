# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_status_assert_step_recorded_fixtures import (
    _assert_args,
    _make_plan,
    _seed_step,
    cmd_assert_step_recorded,
    read_status,
)


def test_assert_does_not_mutate_status(plan_context):
    """The verb is read-only: the persisted status.json is byte-identical after a call."""
    plan_id = 'assert-no-mutation'
    _make_plan(plan_id)
    _seed_step(plan_id, '1-init', 'step-a', 'done')

    before = read_status(plan_id)
    cmd_assert_step_recorded(_assert_args(plan_id, '1-init', 'step-a', require_terminal=True))
    cmd_assert_step_recorded(_assert_args(plan_id, '1-init', 'step-missing'))
    after = read_status(plan_id)

    assert before == after

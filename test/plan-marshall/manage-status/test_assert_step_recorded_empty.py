# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_status_assert_step_recorded_fixtures import _assert_args, _make_plan, cmd_assert_step_recorded


def test_empty_phase_returns_invalid_argument(plan_context):
    """Empty phase is rejected with invalid_argument before reading metadata."""
    plan_id = 'assert-empty-phase'
    _make_plan(plan_id)
    result = cmd_assert_step_recorded(_assert_args(plan_id, '', 'step-a'))

    assert result['status'] == 'error'
    assert result['error'] == 'invalid_argument'


def test_empty_step_returns_invalid_argument(plan_context):
    """Empty step is rejected with invalid_argument before reading metadata."""
    plan_id = 'assert-empty-step'
    _make_plan(plan_id)
    result = cmd_assert_step_recorded(_assert_args(plan_id, '1-init', ''))

    assert result['status'] == 'error'
    assert result['error'] == 'invalid_argument'

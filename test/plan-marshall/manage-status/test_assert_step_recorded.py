# SPDX-License-Identifier: FSL-1.1-ALv2
"""Behavior-cluster tests carved from test_assert_step_recorded.py: phase."""

#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_status_assert_step_recorded_fixtures import _assert_args, _make_plan, _seed_step, cmd_assert_step_recorded


def test_phase_absent_returns_not_recorded(plan_context):
    """A phase with no recorded steps reports recorded=false."""
    plan_id = 'assert-absent-phase'
    _make_plan(plan_id)
    _seed_step(plan_id, '1-init', 'step-a', 'done')

    result = cmd_assert_step_recorded(_assert_args(plan_id, '6-finalize', 'push'))

    assert result['status'] == 'success'
    assert result['recorded'] is False
    assert result['outcome'] is None


def test_phase_absent_with_require_terminal_returns_error(plan_context):
    """--require-terminal on a phase with no steps escalates to step_record_missing."""
    plan_id = 'assert-absent-phase-require'
    _make_plan(plan_id)
    _seed_step(plan_id, '1-init', 'step-a', 'done')

    result = cmd_assert_step_recorded(_assert_args(plan_id, '6-finalize', 'push', require_terminal=True))

    assert result['status'] == 'error'
    assert result['error'] == 'step_record_missing'
    assert result['recorded'] is False

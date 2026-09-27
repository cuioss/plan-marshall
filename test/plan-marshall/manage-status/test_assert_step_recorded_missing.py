# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_status_assert_step_recorded_fixtures import _assert_args, cmd_assert_step_recorded

# =============================================================================
# Error paths
# =============================================================================


def test_missing_plan_returns_none(plan_context):
    """Missing plan: require_status emits TOON and returns None."""
    result = cmd_assert_step_recorded(_assert_args('nonexistent-plan', '1-init', 'step-a'))
    assert result is None

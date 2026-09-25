# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_status_assert_step_recorded_fixtures import _assert_args, _make_plan, _seed_step, cmd_assert_step_recorded


def test_non_positive_floor_is_rejected(plan_context):
    """A --min-firing-count below 1 is an invalid argument, not a silent legacy check."""
    plan_id = 'assert-bad-floor'
    _make_plan(plan_id)
    _seed_step(plan_id, '6-finalize', 'push', 'done')

    result = cmd_assert_step_recorded(
        _assert_args(plan_id, '6-finalize', 'push', require_terminal=True, min_firing_count=0)
    )

    assert result['status'] == 'error'
    assert result['error'] == 'invalid_argument'

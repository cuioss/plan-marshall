# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_status_assert_step_recorded_fixtures import _assert_args, _make_plan, _seed_step, cmd_assert_step_recorded


def test_fresh_record_satisfies_the_floor_and_reports_its_count(plan_context):
    """A record at the guarded floor passes and publishes its firing count."""
    plan_id = 'assert-fresh-firing'
    _make_plan(plan_id)
    _seed_step(plan_id, '6-finalize', 'push', 'done')

    result = cmd_assert_step_recorded(
        _assert_args(plan_id, '6-finalize', 'push', require_terminal=True, min_firing_count=1)
    )

    assert result['status'] == 'success'
    assert result['recorded'] is True
    assert result['outcome'] == 'done'
    assert result['firing_count'] == 1

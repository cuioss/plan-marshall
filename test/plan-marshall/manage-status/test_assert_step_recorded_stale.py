# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_status_assert_step_recorded_fixtures import _assert_args, _make_plan, _seed_step, cmd_assert_step_recorded

# =============================================================================
# --min-firing-count: the record must come from the guarded firing or later
# =============================================================================


def test_stale_prior_firing_record_fails_the_floor(plan_context):
    """A first-firing record does not satisfy a second-firing guard."""
    plan_id = 'assert-stale-firing'
    _make_plan(plan_id)
    _seed_step(plan_id, '6-finalize', 'push', 'done')

    result = cmd_assert_step_recorded(
        _assert_args(plan_id, '6-finalize', 'push', require_terminal=True, min_firing_count=2)
    )

    assert result['status'] == 'error'
    assert result['error'] == 'step_record_missing'
    assert result['recorded'] is False
    assert result['expected_firing_count'] == 2
    assert result['observed_firing_count'] == 1
    assert result['finding_type'] == 'missing-yield'

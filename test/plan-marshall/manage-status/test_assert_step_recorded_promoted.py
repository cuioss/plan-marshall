# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_status_assert_step_recorded_fixtures import (
    _assert_args,
    _make_plan,
    _real_head,
    _seed_step,
    cmd_assert_step_recorded,
)


def test_promoted_alias_record_matches_bare_query(plan_context):
    """Record via ``plan-marshall:automatic-review`` then assert via bare
    ``automatic-review`` → recorded (the promoted-alias map reconciles both)."""
    plan_id = 'assert-canon-promoted-alias'
    _make_plan(plan_id)
    # ``automatic-review`` declares head_dependent: true, so the seed carries an
    # anchor. What this case pins is the promoted-alias key reconciliation, not
    # the anchor — but without it the production verb refuses the seed and there
    # would be no record to query.
    _seed_step(
        plan_id,
        '6-finalize',
        'plan-marshall:automatic-review',
        'done',
        head_at_completion=_real_head(),
    )

    result = cmd_assert_step_recorded(_assert_args(plan_id, '6-finalize', 'automatic-review', require_terminal=True))

    assert result['status'] == 'success'
    assert result['recorded'] is True
    assert result['outcome'] == 'done'

# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_status_mark_step_done_fixtures import _args, _make_plan, cmd_mark_step_done


def test_mark_step_fact_value_may_contain_equals_sign(plan_context):
    """Only the FIRST '=' separates key from value, so a value may contain '='."""
    plan_id = 'mark-step-facts-equals'
    _make_plan(plan_id)
    result = cmd_mark_step_done(
        _args(plan_id, '6-finalize', 'push', 'done', display_detail='test detail', fact=['detail=a=b'])
    )

    assert result['status'] == 'success'
    assert result['facts'] == {'detail': 'a=b'}

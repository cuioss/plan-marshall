# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_status_mark_step_done_fixtures import (
    _args,
    _make_plan,
    cmd_mark_step_done,
    pytest,
    read_status,
)


@pytest.mark.parametrize(
    ('bad_token', 'plan_id'),
    [
        ('work_performed', 'mark-step-facts-bad-no-separator'),  # no '=' separator at all
        ('=noop', 'mark-step-facts-bad-empty-key'),  # empty key
    ],
    ids=['no_separator', 'empty_key'],
)
def test_mark_step_rejects_malformed_fact_token(plan_context, bad_token, plan_id):
    """A malformed --fact token is named in an invalid_fact error, never dropped."""
    _make_plan(plan_id)
    result = cmd_mark_step_done(
        _args(plan_id, '6-finalize', 'push', 'done', display_detail='test detail', fact=[bad_token])
    )

    assert result['status'] == 'error'
    assert result['error'] == 'invalid_fact'
    assert result['offending_token'] == bad_token
    assert bad_token in result['message']

    # The rejection happens before any write.
    persisted = read_status(plan_id)
    assert 'phase_steps' not in persisted.get('metadata', {})

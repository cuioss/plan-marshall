# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_status_mark_step_done_fixtures import _args, _make_plan, cmd_mark_step_done, read_status


def test_mark_step_malformed_fact_rejected_even_alongside_valid_facts(plan_context):
    """One malformed token rejects the whole call — valid siblings are not partially applied."""
    plan_id = 'mark-step-facts-bad-mixed'
    _make_plan(plan_id)
    result = cmd_mark_step_done(
        _args(plan_id, '6-finalize', 'push', 'done', display_detail='test detail', fact=['action=noop', 'bogus'])
    )

    assert result['status'] == 'error'
    assert result['error'] == 'invalid_fact'
    assert result['offending_token'] == 'bogus'

    persisted = read_status(plan_id)
    assert 'phase_steps' not in persisted.get('metadata', {})

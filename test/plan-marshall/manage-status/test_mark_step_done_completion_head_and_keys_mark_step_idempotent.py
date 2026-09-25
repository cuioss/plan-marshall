# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_status_mark_step_done_completion_head_and_keys_fixtures import (
    _args,
    _make_plan,
    _real_head,
    cmd_mark_step_done,
    read_status,
)


def test_mark_step_idempotent_when_head_at_completion_matches(plan_context):
    """Re-call with same outcome+display_detail+head_at_completion is a no-op."""
    plan_id = 'mark-step-head-idempotent'
    sha = _real_head()
    _make_plan(plan_id)
    cmd_mark_step_done(
        _args(
            plan_id,
            '6-finalize',
            'pre-push-quality-gate',
            'done',
            display_detail='gate green',
            head_at_completion=sha,
        )
    )

    persisted_before = read_status(plan_id)
    updated_before = persisted_before['updated']

    second = cmd_mark_step_done(
        _args(
            plan_id,
            '6-finalize',
            'pre-push-quality-gate',
            'done',
            display_detail='gate green',
            head_at_completion=sha,
        )
    )

    assert second['status'] == 'success'
    assert second['changed'] is False
    assert second['head_at_completion'] == sha
    assert 'previous_outcome' not in second

    persisted_after = read_status(plan_id)
    # No file rewrite: updated timestamp unchanged.
    assert persisted_after['updated'] == updated_before
    assert persisted_after['metadata']['phase_steps']['6-finalize']['pre-push-quality-gate'] == {
        'outcome': 'done',
        'display_detail': 'gate green',
        'head_at_completion': sha,
    }

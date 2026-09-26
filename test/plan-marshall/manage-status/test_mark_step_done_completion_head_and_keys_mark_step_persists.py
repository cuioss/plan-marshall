# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_status_mark_step_done_completion_head_and_keys_fixtures import (
    _args,
    _make_plan,
    _real_head,
    cmd_mark_step_done,
    read_status,
)

# =============================================================================
# head_at_completion field
# =============================================================================


def test_mark_step_persists_head_at_completion_on_first_call(plan_context):
    """--head-at-completion is persisted as a third key alongside outcome+display_detail."""
    plan_id = 'mark-step-head-first'
    sha = _real_head()
    _make_plan(plan_id)
    result = cmd_mark_step_done(
        _args(
            plan_id,
            '6-finalize',
            'pre-push-quality-gate',
            'done',
            display_detail='gate green',
            head_at_completion=sha,
        )
    )

    assert result['status'] == 'success'
    assert result['changed'] is True
    assert result['head_at_completion'] == sha
    assert result['outcome'] == 'done'
    assert result['display_detail'] == 'gate green'

    persisted = read_status(plan_id)
    assert persisted['metadata']['phase_steps']['6-finalize']['pre-push-quality-gate'] == {
        'outcome': 'done',
        'display_detail': 'gate green',
        'head_at_completion': sha,
    }

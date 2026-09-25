# SPDX-License-Identifier: FSL-1.1-ALv2
"""Behavior-cluster tests carved from test_mark_step_done_completion_head_and_keys.py: mark step failed."""

#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_status_mark_step_done_completion_head_and_keys_fixtures import (
    _args,
    _make_plan,
    _real_head,
    cmd_mark_step_done,
    read_status,
)


def test_mark_step_failed_then_done_with_force(plan_context):
    """After a 'failed' marker, dispatcher can re-fire and overwrite with 'done' under --force.

    ``automatic-review`` declares ``head_dependent: true``, so every ``done``
    call here supplies ``--head-at-completion`` — the real dispatcher does too.
    The anchor is incidental to what this test pins (conflict detection, then
    the ``--force`` overwrite), but it must be present for the call to reach
    those branches at all: the head-anchor guard is request validation and fires
    before any state is read.
    """
    plan_id = 'mark-step-failed-then-done'
    _make_plan(plan_id)
    sha = _real_head()
    cmd_mark_step_done(_args(plan_id, '6-finalize', 'automatic-review', 'failed', display_detail='timeout'))

    # Without --force, a different outcome on an existing step is a conflict.
    conflict = cmd_mark_step_done(
        _args(
            plan_id,
            '6-finalize',
            'automatic-review',
            'done',
            display_detail='retry green',
            head_at_completion=sha,
        )
    )
    assert conflict['status'] == 'error'
    assert conflict['error'] == 'conflict'
    assert conflict['existing_outcome'] == 'failed'
    assert conflict['requested_outcome'] == 'done'

    # With --force, the retry overwrite succeeds.
    retry = cmd_mark_step_done(
        _args(
            plan_id,
            '6-finalize',
            'automatic-review',
            'done',
            force=True,
            display_detail='retry green',
            head_at_completion=sha,
        )
    )
    assert retry['status'] == 'success'
    assert retry['changed'] is True
    assert retry['outcome'] == 'done'
    assert retry['previous_outcome'] == 'failed'

    persisted = read_status(plan_id)
    # The superseded `failed` firing survives the forced retry.
    assert persisted['metadata']['phase_steps']['6-finalize']['automatic-review'] == {
        'outcome': 'done',
        'display_detail': 'retry green',
        'head_at_completion': sha,
        'firing_count': 2,
        'prior_firings': [{'outcome': 'failed'}],
    }

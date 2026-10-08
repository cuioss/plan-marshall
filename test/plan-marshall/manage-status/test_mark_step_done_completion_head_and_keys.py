# SPDX-License-Identifier: FSL-1.1-ALv2
"""Behavior-cluster tests carved from test_mark_step_done_completion_head_and_keys.py: mark step failed."""

import pytest
from _manage_status_mark_step_done_completion_head_and_keys_fixtures import (
    _args,
    _make_plan,
    _real_head,
    cmd_mark_step_done,
    read_status,
)


@pytest.mark.parametrize('force', [False, True])
def test_mark_step_failed_then_done_with_force(plan_context, force):
    """After a 'failed' marker, the dispatcher's retry records 'done' — forced or not.

    ``failed`` to ``done`` is a transition a retried step takes on its ordinary
    path, so the unforced write succeeds; ``--force`` admits every transition,
    so the forced form succeeds identically.

    ``automatic-review`` declares ``head_dependent: true``, so every ``done``
    call here supplies ``--head-at-completion`` — the real dispatcher does too.
    The anchor is incidental to what this test pins (the retry overwrite), but
    it must be present for the call to reach that branch at all: the
    head-anchor guard is request validation and fires before any state is read.
    """
    plan_id = f'mark-step-failed-then-done-{"forced" if force else "unforced"}'
    _make_plan(plan_id)
    sha = _real_head()
    cmd_mark_step_done(_args(plan_id, '6-finalize', 'automatic-review', 'failed', display_detail='timeout'))

    retry = cmd_mark_step_done(
        _args(
            plan_id,
            '6-finalize',
            'automatic-review',
            'done',
            force=force,
            display_detail='retry green',
            head_at_completion=sha,
        )
    )
    assert retry['status'] == 'success'
    assert retry['changed'] is True
    assert retry['outcome'] == 'done'
    assert retry['previous_outcome'] == 'failed'

    persisted = read_status(plan_id)
    # The superseded `failed` firing survives the retry.
    assert persisted['metadata']['phase_steps']['6-finalize']['automatic-review'] == {
        'outcome': 'done',
        'display_detail': 'retry green',
        'head_at_completion': sha,
        'firing_count': 2,
        'prior_firings': [{'outcome': 'failed'}],
    }

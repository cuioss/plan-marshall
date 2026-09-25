# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_status_mark_step_done_completion_head_and_keys_fixtures import (
    _args,
    _make_plan,
    _tmp_repo_two_heads,
    cmd_mark_step_done,
    read_status,
)


def test_mark_step_head_at_completion_change_overwrites_without_force(plan_context, tmp_path, monkeypatch):
    """Re-call with same outcome+display_detail but different SHA is a 'changed' overwrite, no --force.

    The two anchors come from a throwaway two-commit repo pinned as cwd —
    never from the caller checkout's `HEAD~1`, which does not exist in CI's
    depth-1 checkout.
    """
    plan_id = 'mark-step-head-overwrite'
    sha_new, sha_old = _tmp_repo_two_heads(tmp_path, monkeypatch)
    _make_plan(plan_id)
    cmd_mark_step_done(
        _args(
            plan_id,
            '6-finalize',
            'pre-push-quality-gate',
            'done',
            display_detail='gate green',
            head_at_completion=sha_old,
        )
    )

    # Same outcome and display_detail, different SHA, no --force.
    second = cmd_mark_step_done(
        _args(
            plan_id,
            '6-finalize',
            'pre-push-quality-gate',
            'done',
            display_detail='gate green',
            head_at_completion=sha_new,
        )
    )

    assert second['status'] == 'success'
    assert second['changed'] is True
    assert second['outcome'] == 'done'
    assert second['display_detail'] == 'gate green'
    assert second['head_at_completion'] == sha_new
    assert second['previous_outcome'] == 'done'
    assert second['previous_display_detail'] == 'gate green'
    assert second['previous_head_at_completion'] == sha_old

    persisted = read_status(plan_id)
    # A HEAD-only refresh is a re-fire of the same outcome, so the trail records
    # the superseded `done` — the outcome repeats, the firing does not.
    assert persisted['metadata']['phase_steps']['6-finalize']['pre-push-quality-gate'] == {
        'outcome': 'done',
        'display_detail': 'gate green',
        'head_at_completion': sha_new,
        'firing_count': 2,
        'prior_firings': [{'outcome': 'done'}],
    }

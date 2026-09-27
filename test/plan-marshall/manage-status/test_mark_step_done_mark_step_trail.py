# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_status_mark_step_done_fixtures import (
    _args,
    _make_plan,
    _tmp_repo_two_heads,
    cmd_mark_step_done,
    read_status,
)


def test_mark_step_trail_is_append_only_across_a_fourth_firing(plan_context, tmp_path, monkeypatch):
    """A later firing EXTENDS the trail rather than rewriting it.

    Pins the append-only property directly: the trail observed after firing 3 is
    a strict prefix of the one observed after firing 4.

    The terminal `done` anchor comes from a throwaway two-commit repo pinned
    as cwd — never from the caller checkout's `HEAD~1`, which does not exist
    in CI's depth-1 checkout.
    """
    plan_id = 'mark-step-firings-append'
    _make_plan(plan_id)
    _, old_sha = _tmp_repo_two_heads(tmp_path, monkeypatch)

    # Every call's status is asserted: a refused write (e.g. the head-anchor
    # refusal on a `done`) writes NOTHING, which would silently leave the
    # assertions below reading an earlier firing.
    for call in (
        _args(
            plan_id,
            '6-finalize',
            'ci-verify',
            'loop_back',
            display_detail='r1',
            loop_back_target='5-execute',
        ),
        _args(plan_id, '6-finalize', 'ci-verify', 'failed', force=True, display_detail='r2'),
        _args(plan_id, '6-finalize', 'ci-verify', 'skipped', force=True, display_detail='r3'),
    ):
        assert cmd_mark_step_done(call)['status'] == 'success'
    after_three = list(read_status(plan_id)['metadata']['phase_steps']['6-finalize']['ci-verify']['prior_firings'])

    fourth = cmd_mark_step_done(
        _args(
            plan_id,
            '6-finalize',
            'ci-verify',
            'done',
            force=True,
            display_detail='r4',
            head_at_completion=old_sha,
        )
    )
    assert fourth['status'] == 'success', fourth
    entry = read_status(plan_id)['metadata']['phase_steps']['6-finalize']['ci-verify']

    assert after_three == [
        {'outcome': 'loop_back', 'loop_back_target': '5-execute'},
        {'outcome': 'failed'},
    ]
    assert entry['prior_firings'][: len(after_three)] == after_three
    assert entry['prior_firings'][-1] == {'outcome': 'skipped'}
    assert entry['firing_count'] == 4

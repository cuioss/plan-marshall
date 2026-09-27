# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_status_mark_step_done_fixtures import (
    _args,
    _make_plan,
    _real_head,
    cmd_mark_step_done,
    read_status,
)

# =============================================================================
# Firing history (firing_count / prior_firings)
#
# A finalize step can fire more than once — the ordinary shape is `loop_back`,
# re-fire, `done`. The write is `phase_entry[step] = new_entry`, so before this
# the earlier firings were echoed in the `previous_*` return fields and then
# discarded: a reader of `status.metadata.phase_steps` could not tell a step
# that succeeded first time from one that looped back twice before succeeding.
#
# The keys are ADDITIVE siblings — `outcome` still means the LATEST firing, the
# entry stays a dict, nothing is nested under a history key — which is what
# leaves the `phase_steps_complete` handshake hash unperturbed.
# =============================================================================


def test_mark_step_thrice_fired_step_retains_every_firing(plan_context):
    """`loop_back` → `loop_back` → `done` keeps all three firings.

    RED against pre-fix code, where the entry carried only the final `done` and
    both loop-backs (with their targets) were lost on the write.
    """
    plan_id = 'mark-step-firings-three'
    _make_plan(plan_id)

    cmd_mark_step_done(
        _args(
            plan_id,
            '6-finalize',
            'automatic-review',
            'loop_back',
            display_detail='findings round 1',
            loop_back_target='5-execute',
        )
    )
    cmd_mark_step_done(
        _args(
            plan_id,
            '6-finalize',
            'automatic-review',
            'loop_back',
            force=True,
            display_detail='findings round 2',
            loop_back_target='6-finalize',
        )
    )
    # `automatic-review` declares `head_dependent: true`, so its terminal `done`
    # must carry the SHA — a `done` with no anchor is refused and nothing is
    # written, which would leave this test asserting against the SECOND firing.
    third = cmd_mark_step_done(
        _args(
            plan_id,
            '6-finalize',
            'automatic-review',
            'done',
            force=True,
            display_detail='clean',
            head_at_completion=_real_head(),
        )
    )
    assert third['status'] == 'success', third

    entry = read_status(plan_id)['metadata']['phase_steps']['6-finalize']['automatic-review']

    # `outcome` still means the LATEST firing, and keeps its historical meaning.
    assert entry['outcome'] == 'done'
    assert entry['display_detail'] == 'clean'
    assert entry['head_at_completion'] == _real_head()
    # A `done` outcome carries no loop_back_target — the key is absent, not stale.
    assert 'loop_back_target' not in entry

    # Both superseded firings survive, oldest first, each naming its own target.
    assert entry['firing_count'] == 3
    assert entry['prior_firings'] == [
        {'outcome': 'loop_back', 'loop_back_target': '5-execute'},
        {'outcome': 'loop_back', 'loop_back_target': '6-finalize'},
    ]

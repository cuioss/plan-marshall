#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the mark-step-done subcommand of manage-status."""


import pytest
from _mark_step_done_fixtures import _args, _make_plan, cmd_mark_step_done, read_status

from conftest import load_script_module

# =============================================================================
# Structured step facts (--fact KEY=VALUE)
#
# The facts dict is what makes a step record answer structured questions that
# its display_detail prose cannot. These cases pin the persistence shape, the
# omit-when-absent legacy guarantee, accumulation across repeated flags, the
# malformed-token rejection, and facts-only change detection.
# =============================================================================

def test_mark_step_facts_only_change_reports_changed_true(plan_context):
    """Changing ONLY the facts is a 'changed' overwrite, echoed via previous_facts.

    This is the anti-swallow guard: without facts in the idempotency comparison a
    facts-only re-call would report changed: false and silently discard the new
    values.
    """
    plan_id = 'mark-step-facts-only-change'
    _make_plan(plan_id)
    cmd_mark_step_done(
        _args(
            plan_id,
            '6-finalize',
            'finalize-step-sync-baseline',
            'done',
            display_detail='same detail',
            fact=['action=noop'],
        )
    )

    second = cmd_mark_step_done(
        _args(
            plan_id,
            '6-finalize',
            'finalize-step-sync-baseline',
            'done',
            display_detail='same detail',
            fact=['action=rebased'],
        )
    )

    assert second['status'] == 'success'
    assert second['changed'] is True
    assert second['outcome'] == 'done'
    assert second['display_detail'] == 'same detail'
    assert second['facts'] == {'action': 'rebased'}
    assert second['previous_facts'] == {'action': 'noop'}

    persisted = read_status(plan_id)
    entry = persisted['metadata']['phase_steps']['6-finalize']['finalize-step-sync-baseline']
    assert entry['facts'] == {'action': 'rebased'}


def test_mark_step_adding_facts_to_a_factless_record_reports_changed_true(plan_context):
    """Going from no facts to facts is a change, with previous_facts echoed as None."""
    plan_id = 'mark-step-facts-added'
    _make_plan(plan_id)
    cmd_mark_step_done(_args(plan_id, '6-finalize', 'push', 'done', display_detail='pushed'))

    second = cmd_mark_step_done(
        _args(
            plan_id,
            '6-finalize',
            'push',
            'done',
            display_detail='pushed',
            fact=['work_performed=true'],
        )
    )

    assert second['status'] == 'success'
    assert second['changed'] is True
    assert second['facts'] == {'work_performed': 'true'}
    assert second['previous_facts'] is None

    persisted = read_status(plan_id)
    assert persisted['metadata']['phase_steps']['6-finalize']['push']['facts'] == {
        'work_performed': 'true'
    }


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

def test_phase_steps_complete_capture_is_unaffected_by_the_firing_keys(
    monkeypatch: pytest.MonkeyPatch,
):
    """The `phase_steps_complete` invariant hash is identical with and without the trail.

    The load-bearing constraint on the shape: the capture rejects a bare-string
    entry, requires `outcome == 'done'`, and hashes only the sorted required step
    NAMES. Two entries that differ ONLY by the added sibling keys must therefore
    produce the SAME hash — asserted here against the REAL capture, not asserted
    of the design.
    """
    invariants = load_script_module(
        'plan-marshall', 'plan-marshall', '_invariants.py', '_mark_step_invariants'
    )
    # Pin a one-step required set so the capture reaches its hash rather than
    # short-circuiting on an unrelated phase roster.
    monkeypatch.setattr(invariants, '_resolve_required_steps_path', lambda _phase: 'stub')
    monkeypatch.setattr(invariants, '_parse_required_steps', lambda _path: ['step-a'])
    monkeypatch.setattr(invariants, '_read_manifest_steps', lambda _pid, _phase: {'step-a'})

    plain = {
        'phase_steps': {
            '6-finalize': {'step-a': {'outcome': 'done', 'display_detail': 'x'}}
        }
    }
    with_history = {
        'phase_steps': {
            '6-finalize': {
                'step-a': {
                    'outcome': 'done',
                    'display_detail': 'x',
                    'firing_count': 3,
                    'prior_firings': [
                        {'outcome': 'loop_back', 'loop_back_target': '5-execute'},
                        {'outcome': 'loop_back', 'loop_back_target': '6-finalize'},
                    ],
                }
            }
        }
    }

    plain_hash = invariants._capture_phase_steps_complete('pid', plain, '6-finalize')
    history_hash = invariants._capture_phase_steps_complete('pid', with_history, '6-finalize')

    # Guard the guard: a capture that returned None for both would make the
    # equality below vacuously true.
    assert isinstance(plain_hash, str) and plain_hash
    assert history_hash == plain_hash

#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the mark-step-done subcommand of manage-status."""


import pytest
from _mark_step_done_fixtures import _args, _make_plan, cmd_mark_step_done, read_status, write_status

# =============================================================================
# Stale legacy-key duplicate migration
#
# A pre-migration run may have persisted a ``default:``-prefixed key directly.
# A later canonical write must locate that stale key via the canonicalized
# fallback scan (so the conflict check fires against the true existing outcome)
# AND pop it on write, so a legacy-vs-canonical duplicate never survives.
# =============================================================================

def test_mark_step_conflict_fires_against_stale_legacy_key(plan_context):
    """A differing-outcome write over a stale ``default:push`` key raises conflict.

    Before the fix the stale key was invisible to ``get('push')``, so the conflict
    check was silently bypassed and a divergent duplicate was written. The fallback
    scan now surfaces the true existing outcome so the conflict fires.
    """
    plan_id = 'mark-step-legacy-conflict'
    _make_plan(plan_id)
    status = read_status(plan_id)
    status.setdefault('metadata', {})['phase_steps'] = {
        '6-finalize': {'default:push': {'outcome': 'done', 'display_detail': 'kept'}}
    }
    write_status(plan_id, status)

    result = cmd_mark_step_done(_args(plan_id, '6-finalize', 'push', 'skipped'))

    assert result['status'] == 'error'
    assert result['error'] == 'conflict'
    assert result['existing_outcome'] == 'done'
    assert result['requested_outcome'] == 'skipped'

    # No divergent duplicate written — the stale legacy entry is untouched.
    persisted = read_status(plan_id)
    phase_steps = persisted['metadata']['phase_steps']['6-finalize']
    assert phase_steps == {'default:push': {'outcome': 'done', 'display_detail': 'kept'}}
    assert 'push' not in phase_steps


def test_mark_step_force_overwrites_stale_legacy_key_without_duplicate(plan_context):
    """A ``--force`` differing-outcome write over a stale ``default:push`` key pops it.

    The final-write branch pops the located stale key before storing the new
    canonical entry, so the force overwrite leaves exactly one canonical entry.
    """
    plan_id = 'mark-step-legacy-force'
    _make_plan(plan_id)
    status = read_status(plan_id)
    status.setdefault('metadata', {})['phase_steps'] = {
        '6-finalize': {'default:push': {'outcome': 'done', 'display_detail': 'old'}}
    }
    write_status(plan_id, status)

    result = cmd_mark_step_done(
        _args(plan_id, '6-finalize', 'push', 'skipped', force=True, display_detail='new')
    )

    assert result['status'] == 'success'
    assert result['changed'] is True
    assert result['previous_outcome'] == 'done'

    persisted = read_status(plan_id)
    phase_steps = persisted['metadata']['phase_steps']['6-finalize']
    assert phase_steps == {
        'push': {
            'outcome': 'skipped',
            'display_detail': 'new',
            'firing_count': 2,
            'prior_firings': [{'outcome': 'done'}],
        }
    }
    assert 'default:push' not in phase_steps


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
            plan_id, '6-finalize', 'automatic-review', 'loop_back',
            display_detail='findings round 1', loop_back_target='5-execute',
        )
    )
    cmd_mark_step_done(
        _args(
            plan_id, '6-finalize', 'automatic-review', 'loop_back', force=True,
            display_detail='findings round 2', loop_back_target='6-finalize',
        )
    )
    # `automatic-review` declares `head_dependent: true`, so its terminal `done`
    # must carry the SHA — a `done` with no anchor is refused and nothing is
    # written, which would leave this test asserting against the SECOND firing.
    third = cmd_mark_step_done(
        _args(
            plan_id, '6-finalize', 'automatic-review', 'done', force=True,
            display_detail='clean', head_at_completion='c' * 40,
        )
    )
    assert third['status'] == 'success', third

    entry = read_status(plan_id)['metadata']['phase_steps']['6-finalize']['automatic-review']

    # `outcome` still means the LATEST firing, and keeps its historical meaning.
    assert entry['outcome'] == 'done'
    assert entry['display_detail'] == 'clean'
    assert entry['head_at_completion'] == 'c' * 40
    # A `done` outcome carries no loop_back_target — the key is absent, not stale.
    assert 'loop_back_target' not in entry

    # Both superseded firings survive, oldest first, each naming its own target.
    assert entry['firing_count'] == 3
    assert entry['prior_firings'] == [
        {'outcome': 'loop_back', 'loop_back_target': '5-execute'},
        {'outcome': 'loop_back', 'loop_back_target': '6-finalize'},
    ]


def test_mark_step_single_firing_writes_the_historical_record_shape(plan_context):
    """One firing produces a byte-identical historical entry — no new keys.

    The matched negative control for the test above: without it, an
    unconditional history stamp would satisfy the positive assertions while
    changing every record in the corpus.
    """
    plan_id = 'mark-step-firings-one'
    _make_plan(plan_id)

    cmd_mark_step_done(
        _args(plan_id, '6-finalize', 'push', 'done', display_detail='pushed')
    )

    entry = read_status(plan_id)['metadata']['phase_steps']['6-finalize']['push']
    assert entry == {'outcome': 'done', 'display_detail': 'pushed'}
    assert 'firing_count' not in entry
    assert 'prior_firings' not in entry


def test_mark_step_unchanged_recall_appends_no_firing(plan_context):
    """An idempotent re-call reports `changed: false` and grows no trail.

    Guards the append against firing on a no-op write, which would inflate
    `firing_count` on every retry of an already-recorded step.
    """
    plan_id = 'mark-step-firings-idempotent'
    _make_plan(plan_id)

    cmd_mark_step_done(
        _args(plan_id, '6-finalize', 'push', 'done', display_detail='pushed')
    )
    second = cmd_mark_step_done(
        _args(plan_id, '6-finalize', 'push', 'done', display_detail='pushed')
    )

    assert second['changed'] is False
    entry = read_status(plan_id)['metadata']['phase_steps']['6-finalize']['push']
    assert entry == {'outcome': 'done', 'display_detail': 'pushed'}
    assert 'prior_firings' not in entry


def test_mark_step_trail_is_append_only_across_a_fourth_firing(plan_context):
    """A later firing EXTENDS the trail rather than rewriting it.

    Pins the append-only property directly: the trail observed after firing 3 is
    a strict prefix of the one observed after firing 4.
    """
    plan_id = 'mark-step-firings-append'
    _make_plan(plan_id)

    # Every call's status is asserted: a refused write (e.g. the head-anchor
    # refusal on a `done`) writes NOTHING, which would silently leave the
    # assertions below reading an earlier firing.
    for call in (
        _args(
            plan_id, '6-finalize', 'ci-verify', 'loop_back',
            display_detail='r1', loop_back_target='5-execute',
        ),
        _args(plan_id, '6-finalize', 'ci-verify', 'failed', force=True, display_detail='r2'),
        _args(plan_id, '6-finalize', 'ci-verify', 'skipped', force=True, display_detail='r3'),
    ):
        assert cmd_mark_step_done(call)['status'] == 'success'
    after_three = list(
        read_status(plan_id)['metadata']['phase_steps']['6-finalize']['ci-verify'][
            'prior_firings'
        ]
    )

    fourth = cmd_mark_step_done(
        _args(
            plan_id, '6-finalize', 'ci-verify', 'done', force=True,
            display_detail='r4', head_at_completion='d' * 40,
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


# =============================================================================
# Structured step facts (--fact KEY=VALUE)
#
# The facts dict is what makes a step record answer structured questions that
# its display_detail prose cannot. These cases pin the persistence shape, the
# omit-when-absent legacy guarantee, accumulation across repeated flags, the
# malformed-token rejection, and facts-only change detection.
# =============================================================================


def test_mark_step_persists_facts_into_the_record(plan_context):
    """A single --fact is parsed into a facts dict persisted on the entry."""
    plan_id = 'mark-step-facts-single'
    _make_plan(plan_id)
    result = cmd_mark_step_done(
        _args(
            plan_id,
            '6-finalize',
            'finalize-step-sync-baseline',
            'done',
            display_detail='no-op rebase',
            fact=['action=noop'],
        )
    )

    assert result['status'] == 'success'
    assert result['changed'] is True
    assert result['facts'] == {'action': 'noop'}

    persisted = read_status(plan_id)
    assert persisted['metadata']['phase_steps']['6-finalize']['finalize-step-sync-baseline'] == {
        'outcome': 'done',
        'display_detail': 'no-op rebase',
        'facts': {'action': 'noop'},
    }


def test_mark_step_multiple_fact_flags_accumulate_into_one_dict(plan_context):
    """Repeated --fact flags accumulate into a single dict on the record."""
    plan_id = 'mark-step-facts-multi'
    _make_plan(plan_id)
    result = cmd_mark_step_done(
        _args(
            plan_id,
            '6-finalize',
            'finalize-step-sync-baseline',
            'done',
            fact=['action=noop', 'upstream_commit_count=0', 'work_performed=true'],
        )
    )

    assert result['status'] == 'success'
    assert result['facts'] == {
        'action': 'noop',
        'upstream_commit_count': '0',
        'work_performed': 'true',
    }

    persisted = read_status(plan_id)
    entry = persisted['metadata']['phase_steps']['6-finalize']['finalize-step-sync-baseline']
    assert entry['facts'] == {
        'action': 'noop',
        'upstream_commit_count': '0',
        'work_performed': 'true',
    }


def test_mark_step_fact_value_may_contain_equals_sign(plan_context):
    """Only the FIRST '=' separates key from value, so a value may contain '='."""
    plan_id = 'mark-step-facts-equals'
    _make_plan(plan_id)
    result = cmd_mark_step_done(
        _args(plan_id, '6-finalize', 'push', 'done', fact=['detail=a=b'])
    )

    assert result['status'] == 'success'
    assert result['facts'] == {'detail': 'a=b'}


def test_mark_step_omits_facts_key_when_flag_absent(plan_context):
    """Caller omitting --fact produces the byte-identical historical record shape."""
    plan_id = 'mark-step-facts-omitted'
    _make_plan(plan_id)
    result = cmd_mark_step_done(_args(plan_id, '1-init', 'step-a', 'done', display_detail='legacy'))

    assert result['status'] == 'success'
    # The result echoes the field as None, but persistence omits the key entirely.
    assert result['facts'] is None

    persisted = read_status(plan_id)
    entry = persisted['metadata']['phase_steps']['1-init']['step-a']
    assert entry == {'outcome': 'done', 'display_detail': 'legacy'}
    assert 'facts' not in entry


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
        _args(plan_id, '6-finalize', 'push', 'done', fact=[bad_token])
    )

    assert result['status'] == 'error'
    assert result['error'] == 'invalid_fact'
    assert result['offending_token'] == bad_token
    assert bad_token in result['message']

    # The rejection happens before any write.
    persisted = read_status(plan_id)
    assert 'phase_steps' not in persisted.get('metadata', {})


def test_mark_step_malformed_fact_rejected_even_alongside_valid_facts(plan_context):
    """One malformed token rejects the whole call — valid siblings are not partially applied."""
    plan_id = 'mark-step-facts-bad-mixed'
    _make_plan(plan_id)
    result = cmd_mark_step_done(
        _args(plan_id, '6-finalize', 'push', 'done', fact=['action=noop', 'bogus'])
    )

    assert result['status'] == 'error'
    assert result['error'] == 'invalid_fact'
    assert result['offending_token'] == 'bogus'

    persisted = read_status(plan_id)
    assert 'phase_steps' not in persisted.get('metadata', {})


def test_mark_step_idempotent_when_facts_match(plan_context):
    """Re-call with identical outcome+detail+facts is a no-op (no file rewrite)."""
    plan_id = 'mark-step-facts-idempotent'
    _make_plan(plan_id)
    cmd_mark_step_done(
        _args(
            plan_id,
            '6-finalize',
            'push',
            'done',
            display_detail='pushed',
            fact=['work_performed=true'],
        )
    )

    updated_before = read_status(plan_id)['updated']

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
    assert second['changed'] is False
    assert second['facts'] == {'work_performed': 'true'}
    assert 'previous_outcome' not in second

    assert read_status(plan_id)['updated'] == updated_before

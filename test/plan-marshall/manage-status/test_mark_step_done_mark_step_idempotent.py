#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the mark-step-done subcommand of manage-status."""


from _mark_step_done_fixtures import _args, _make_plan, cmd_mark_step_done, read_status


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

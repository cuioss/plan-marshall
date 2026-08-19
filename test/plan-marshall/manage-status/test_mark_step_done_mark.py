#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the mark-step-done subcommand of manage-status."""


import pytest
from _mark_step_done_fixtures import _args, _make_plan, cmd_mark_step_done, read_status, write_status


def test_mark_step_rejects_legacy_bare_string_entry(plan_context):
    """A seeded bare-string entry must be rejected with legacy_string_entry error."""
    plan_id = 'mark-step-legacy'
    _make_plan(plan_id)
    status = read_status(plan_id)
    status.setdefault('metadata', {})['phase_steps'] = {'1-init': {'step-a': 'done'}}
    write_status(plan_id, status)

    result = cmd_mark_step_done(_args(plan_id, '1-init', 'step-a', 'done', display_detail='ignored'))

    assert result['status'] == 'error'
    assert result['error'] == 'legacy_string_entry'
    assert result['existing_outcome'] == 'done'
    assert result['requested_outcome'] == 'done'
    assert result['phase'] == '1-init'
    assert result['step'] == 'step-a'

    persisted = read_status(plan_id)
    assert persisted['metadata']['phase_steps']['1-init']['step-a'] == 'done'


# =============================================================================
# Multi-phase / multi-step coexistence
# =============================================================================


def test_mark_step_multi_phase_and_multi_step(plan_context):
    """Independent phases and steps should coexist in phase_steps."""
    plan_id = 'mark-step-multi'
    _make_plan(plan_id)

    cmd_mark_step_done(_args(plan_id, '1-init', 'step-a', 'done'))
    cmd_mark_step_done(_args(plan_id, '1-init', 'step-b', 'skipped'))
    cmd_mark_step_done(_args(plan_id, '2-refine', 'clarify', 'done', display_detail='clarified'))
    cmd_mark_step_done(_args(plan_id, '3-outline', 'draft', 'done'))

    persisted = read_status(plan_id)
    phase_steps = persisted['metadata']['phase_steps']

    assert phase_steps['1-init'] == {
        'step-a': {'outcome': 'done', 'display_detail': None},
        'step-b': {'outcome': 'skipped', 'display_detail': None},
    }
    assert phase_steps['2-refine'] == {
        'clarify': {'outcome': 'done', 'display_detail': 'clarified'},
    }
    assert phase_steps['3-outline'] == {
        'draft': {'outcome': 'done', 'display_detail': None},
    }


# =============================================================================
# Error paths
# =============================================================================


def test_mark_step_missing_plan(plan_context):
    """Missing plan: require_status emits TOON and returns None."""
    result = cmd_mark_step_done(_args('nonexistent-plan', '1-init', 'step-a', 'done'))
    assert result is None


def test_mark_step_invalid_outcome(plan_context):
    """Invalid outcome value returns invalid_outcome error without writing."""
    plan_id = 'mark-step-bad-outcome'
    _make_plan(plan_id)
    result = cmd_mark_step_done(_args(plan_id, '1-init', 'step-a', 'bogus'))

    assert result['status'] == 'error'
    assert result['error'] == 'invalid_outcome'

    persisted = read_status(plan_id)
    assert 'phase_steps' not in persisted.get('metadata', {})


def test_mark_step_failed_idempotent(plan_context):
    """Re-marking a step 'failed' with same detail is a no-op (changed=False)."""
    plan_id = 'mark-step-failed-idempotent'
    _make_plan(plan_id)
    cmd_mark_step_done(
        _args(plan_id, '6-finalize', 'automatic-review', 'failed', display_detail='timeout')
    )

    second = cmd_mark_step_done(
        _args(plan_id, '6-finalize', 'automatic-review', 'failed', display_detail='timeout')
    )

    assert second['status'] == 'success'
    assert second['changed'] is False
    assert second['outcome'] == 'failed'


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
    sha = 'b' * 40
    cmd_mark_step_done(
        _args(plan_id, '6-finalize', 'automatic-review', 'failed', display_detail='timeout')
    )

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


def test_mark_step_empty_phase(plan_context):
    """Empty phase is rejected with invalid_argument."""
    plan_id = 'mark-step-empty-phase'
    _make_plan(plan_id)
    result = cmd_mark_step_done(_args(plan_id, '', 'step-a', 'done'))

    assert result['status'] == 'error'
    assert result['error'] == 'invalid_argument'


def test_mark_step_empty_step(plan_context):
    """Empty step is rejected with invalid_argument."""
    plan_id = 'mark-step-empty-step'
    _make_plan(plan_id)
    result = cmd_mark_step_done(_args(plan_id, '1-init', '', 'done'))

    assert result['status'] == 'error'
    assert result['error'] == 'invalid_argument'


def test_mark_step_invalid_plan_id(plan_context):
    """Invalid plan_id format triggers require_valid_plan_id exit."""
    with pytest.raises(SystemExit):
        cmd_mark_step_done(_args('Invalid_Plan', '1-init', 'step-a', 'done'))


# =============================================================================
# head_at_completion field
# =============================================================================


def test_mark_step_persists_head_at_completion_on_first_call(plan_context):
    """--head-at-completion is persisted as a third key alongside outcome+display_detail."""
    plan_id = 'mark-step-head-first'
    sha = 'abc1234567890abcdef1234567890abcdef1234'
    _make_plan(plan_id)
    result = cmd_mark_step_done(
        _args(
            plan_id,
            '6-finalize',
            'pre-push-quality-gate',
            'done',
            head_at_completion=sha,
        )
    )

    assert result['status'] == 'success'
    assert result['changed'] is True
    assert result['head_at_completion'] == sha
    assert result['outcome'] == 'done'
    assert result['display_detail'] is None

    persisted = read_status(plan_id)
    assert persisted['metadata']['phase_steps']['6-finalize']['pre-push-quality-gate'] == {
        'outcome': 'done',
        'display_detail': None,
        'head_at_completion': sha,
    }


def test_mark_step_idempotent_when_head_at_completion_matches(plan_context):
    """Re-call with same outcome+display_detail+head_at_completion is a no-op."""
    plan_id = 'mark-step-head-idempotent'
    sha = 'deadbeefcafebabe0123456789abcdef01234567'
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

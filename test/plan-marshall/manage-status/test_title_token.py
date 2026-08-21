#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the field-only ``title-token`` verb of manage-status.py:
set and clear arbitration, argument rejection, and the absence of rendering."""


from argparse import Namespace

from _title_token_fixtures import (
    SCRIPT_PATH,
    _clear,
    _read_status,
    _set,
    cmd_create,
)

from conftest import run_script

# =============================================================================
# arbitration: open SET (last writer wins), owner-scoped CLEAR
# =============================================================================

def test_clear_from_a_foreign_owner_is_a_reported_no_op(plan_context):
    """A ``clear`` from an owner that does not own the live record leaves it
    intact and reports the refusal — this is what stops a lock release from
    clobbering a live build bracket."""
    cmd_create(Namespace(plan_id='tt-arb-foreign', title='Test', phases='1-init', force=False))
    _set('tt-arb-foreign', 'build-busy', owner='build-hook')

    result = _clear('tt-arb-foreign', owner='merge-lock')

    assert result['status'] == 'success'
    assert result['cleared'] is False
    assert result['reason'] == 'foreign_owner'
    stored = _read_status(plan_context, 'tt-arb-foreign')['title_token']
    assert stored['state'] == 'build-busy'
    assert stored['owner'] == 'build-hook'


def test_clear_from_the_recording_owner_removes_the_record(plan_context):
    """The recorded owner CAN clear its own token."""
    cmd_create(Namespace(plan_id='tt-arb-own', title='Test', phases='1-init', force=False))
    _set('tt-arb-own', 'build-busy', owner='build-hook')

    result = _clear('tt-arb-own', owner='build-hook')

    assert result['cleared'] is True
    assert result['reason'] == 'owned'
    assert 'title_token' not in _read_status(plan_context, 'tt-arb-own')


def test_lock_clear_does_not_clear_a_foreign_build_busy_but_does_clear_its_own(plan_context):
    """The asymmetry end to end: a merge-lock clear leaves a build-hook token
    alone, and the same clear removes a merge-lock-owned token."""
    plan_id = 'tt-arb-asymmetry'
    cmd_create(Namespace(plan_id=plan_id, title='Test', phases='1-init', force=False))

    _set(plan_id, 'build-busy', owner='build-hook')
    _clear(plan_id, owner='merge-lock')
    assert _read_status(plan_context, plan_id)['title_token']['owner'] == 'build-hook'

    _set(plan_id, 'lock-owned', owner='merge-lock')
    _clear(plan_id, owner='merge-lock')
    assert 'title_token' not in _read_status(plan_context, plan_id)


# =============================================================================
# clear: removes the field, idempotent when unset
# =============================================================================

def test_clear_removes_title_token_field(plan_context):
    """``title-token clear`` removes a previously-set title_token field."""
    cmd_create(Namespace(plan_id='tt-clear', title='Test', phases='1-init', force=False))
    _set('tt-clear', 'lock-owned')

    result = _clear('tt-clear')

    assert result['status'] == 'success'
    assert result['title_token'] is None
    assert result['cleared'] is True

    stored = _read_status(plan_context, 'tt-clear')
    assert 'title_token' not in stored


def test_clear_is_idempotent_when_unset(plan_context):
    """``title-token clear`` is a no-op when no title_token field exists."""
    cmd_create(Namespace(plan_id='tt-clear-noop', title='Test', phases='1-init', force=False))

    result = _clear('tt-clear-noop')

    assert result['status'] == 'success'
    assert result['title_token'] is None
    assert result['cleared'] is False
    assert result['reason'] == 'absent'

    stored = _read_status(plan_context, 'tt-clear-noop')
    assert 'title_token' not in stored


def test_clear_twice_is_idempotent(plan_context):
    """Clearing twice in a row leaves the field absent and reports cleared=False."""
    cmd_create(Namespace(plan_id='tt-clear-twice', title='Test', phases='1-init', force=False))
    _set('tt-clear-twice', 'lock-waiting')

    first = _clear('tt-clear-twice')
    second = _clear('tt-clear-twice')

    assert first['cleared'] is True
    assert second['cleared'] is False
    assert second['title_token'] is None

    stored = _read_status(plan_context, 'tt-clear-twice')
    assert 'title_token' not in stored


# =============================================================================
# argparse: invalid --state / --owner is rejected with exit code 2
# =============================================================================

def test_clear_invalid_owner_rejected_by_argparse():
    """``title-token clear --owner <bad>`` is likewise rejected at parse time."""
    result = run_script(
        SCRIPT_PATH,
        'title-token',
        'clear',
        '--plan-id',
        'tt-argparse-clear-owner',
        '--owner',
        'not-a-valid-owner',
    )
    assert result.returncode == 2


# =============================================================================
# no rendering: the verb writes no title-body.txt artifact
# =============================================================================

def test_clear_writes_no_title_body_artifact(plan_context):
    """``clear`` persists only status.json — no title-body.txt rendering."""
    cmd_create(Namespace(plan_id='tt-no-render-clear', title='Test', phases='1-init', force=False))
    _set('tt-no-render-clear', 'lock-owned')
    _clear('tt-no-render-clear')

    plan_dir = plan_context.plan_dir_for('tt-no-render-clear')
    assert not (plan_dir / 'title-body.txt').exists()

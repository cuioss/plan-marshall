#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the field-only ``title-token`` verb of manage-status.py.

Its sections, in order:

* Guard: the state and owner vocabularies are exactly the documented sets
* staleness: read-side, age-based, clearable by ANY owner
* set: each of the two states writes status.title_token
* arbitration: open SET (last writer wins), owner-scoped CLEAR
* argparse: invalid --state / --owner is rejected with exit code 2
* no rendering: the verb writes no title-body.txt artifact
* phase writers: NO title-token sweep — staleness is resolved read-side
"""


from argparse import Namespace
from datetime import UTC, datetime, timedelta

from _title_token_fixtures import (
    _PHASES,
    EXPECTED_OWNERS,
    EXPECTED_STATES,
    SCRIPT_PATH,
    TITLE_TOKEN_OWNERS,
    TITLE_TOKEN_STALE_AFTER_SECONDS,
    TITLE_TOKEN_STATES,
    _read_status,
    _set,
    cmd_create,
    cmd_set_phase,
    cmd_title_token,
    title_token_is_stale,
)

from conftest import run_script

# =============================================================================
# Guard: the state and owner vocabularies are exactly the documented sets
# =============================================================================


def test_title_token_states_are_the_three_documented_states():
    """``TITLE_TOKEN_STATES`` is exactly the two lock-coordination phase states
    plus the orchestration-busy ``build-busy`` state."""
    assert TITLE_TOKEN_STATES == EXPECTED_STATES


def test_title_token_owners_are_the_three_documented_owners():
    """``TITLE_TOKEN_OWNERS`` is exactly the three writers of the token: the
    build-hook render assist, the merge-lock machinery, and an explicit CLI
    invocation."""
    assert TITLE_TOKEN_OWNERS == EXPECTED_OWNERS


# =============================================================================
# staleness: read-side, age-based, clearable by ANY owner
# =============================================================================


def test_title_token_is_stale_predicate_boundaries():
    """The predicate is age-based with the documented threshold, and treats
    every structurally-unusable record as stale (fail-safe)."""
    now = datetime.now(UTC)
    fresh = {
        'owner': 'cli',
        'state': 'build-busy',
        'set_at': (now - timedelta(seconds=TITLE_TOKEN_STALE_AFTER_SECONDS - 60)).strftime(
            '%Y-%m-%dT%H:%M:%SZ'
        ),
    }
    aged = {
        'owner': 'cli',
        'state': 'build-busy',
        'set_at': (now - timedelta(seconds=TITLE_TOKEN_STALE_AFTER_SECONDS + 60)).strftime(
            '%Y-%m-%dT%H:%M:%SZ'
        ),
    }

    assert title_token_is_stale(fresh, now=now) is False
    assert title_token_is_stale(aged, now=now) is True
    # Structurally unusable records read as stale rather than raising.
    assert title_token_is_stale(None, now=now) is True
    assert title_token_is_stale('build-busy', now=now) is True
    assert title_token_is_stale({'owner': 'cli', 'state': 'build-busy'}, now=now) is True
    assert title_token_is_stale({'owner': 'cli', 'state': 'nonsense', 'set_at': fresh['set_at']}, now=now) is True
    assert title_token_is_stale({'owner': 'cli', 'state': 'build-busy', 'set_at': 'not-a-date'}, now=now) is True


# =============================================================================
# set: each of the two states writes status.title_token
# =============================================================================


def test_set_lock_waiting_writes_structured_record(plan_context):
    """``title-token set --state lock-waiting`` persists the structured record."""
    cmd_create(Namespace(plan_id='tt-lock-waiting', title='Test', phases='1-init', force=False))
    result = _set('tt-lock-waiting', 'lock-waiting', owner='merge-lock')

    assert result['status'] == 'success'
    assert result['title_token']['state'] == 'lock-waiting'
    assert result['title_token']['owner'] == 'merge-lock'

    stored = _read_status(plan_context, 'tt-lock-waiting')['title_token']
    assert stored['state'] == 'lock-waiting'
    assert stored['owner'] == 'merge-lock'


def test_set_lock_owned_writes_structured_record(plan_context):
    """``title-token set --state lock-owned`` persists the structured record."""
    cmd_create(Namespace(plan_id='tt-lock-owned', title='Test', phases='1-init', force=False))
    result = _set('tt-lock-owned', 'lock-owned', owner='merge-lock')

    assert result['status'] == 'success'
    assert result['title_token']['state'] == 'lock-owned'

    stored = _read_status(plan_context, 'tt-lock-owned')['title_token']
    assert stored['state'] == 'lock-owned'
    assert stored['owner'] == 'merge-lock'


def test_set_build_busy_writes_structured_record(plan_context):
    """``title-token set --state build-busy`` persists the structured record.

    build-busy is the orchestration-busy state — written by the build-hook
    render assist for the duration of a build Bash call. manage-status persists
    it field-only, identically to the lock states; the 🔨 icon-slot override is
    applied downstream by ``manage-terminal-title``.
    """
    cmd_create(Namespace(plan_id='tt-build-busy', title='Test', phases='1-init', force=False))
    result = _set('tt-build-busy', 'build-busy', owner='build-hook')

    assert result['status'] == 'success'
    assert result['title_token']['state'] == 'build-busy'
    assert result['title_token']['owner'] == 'build-hook'

    stored = _read_status(plan_context, 'tt-build-busy')['title_token']
    assert stored['state'] == 'build-busy'
    assert stored['owner'] == 'build-hook'


def test_set_record_carries_the_three_documented_keys(plan_context):
    """The persisted record carries exactly ``owner`` / ``state`` / ``set_at``.

    Pinning the key SET (not just individual reads) is what makes a silent
    shape drift — a dropped ``set_at``, a renamed ``owner`` — fail here rather
    than surface later as an un-ageable token.
    """
    cmd_create(Namespace(plan_id='tt-record-keys', title='Test', phases='1-init', force=False))
    _set('tt-record-keys', 'build-busy', owner='build-hook')

    stored = _read_status(plan_context, 'tt-record-keys')['title_token']
    assert set(stored) == {'owner', 'state', 'set_at'}
    # set_at is a parseable UTC instant, which is what the staleness rule reads.
    parsed = datetime.fromisoformat(stored['set_at'].replace('Z', '+00:00'))
    assert abs((datetime.now(UTC) - parsed).total_seconds()) < 120


def test_set_defaults_to_the_cli_owner(plan_context):
    """A ``set`` with no explicit owner is recorded as the ``cli`` writer."""
    cmd_create(Namespace(plan_id='tt-default-owner', title='Test', phases='1-init', force=False))
    cmd_title_token(Namespace(plan_id='tt-default-owner', token_verb='set', state='lock-owned'))

    stored = _read_status(plan_context, 'tt-default-owner')['title_token']
    assert stored['owner'] == 'cli'


# =============================================================================
# arbitration: open SET (last writer wins), owner-scoped CLEAR
# =============================================================================


def test_set_from_a_foreign_owner_replaces_the_record_wholesale(plan_context):
    """A ``set`` from ANY owner replaces the record — last writer wins, and the
    record always names its CURRENT owner (never the previous one)."""
    cmd_create(Namespace(plan_id='tt-arb-set', title='Test', phases='1-init', force=False))
    _set('tt-arb-set', 'lock-waiting', owner='merge-lock')
    _set('tt-arb-set', 'build-busy', owner='build-hook')

    stored = _read_status(plan_context, 'tt-arb-set')['title_token']
    assert stored['state'] == 'build-busy'
    assert stored['owner'] == 'build-hook'


# =============================================================================
# argparse: invalid --state / --owner is rejected with exit code 2
# =============================================================================


def test_set_invalid_state_rejected_by_argparse():
    """``title-token set --state <bad>`` is rejected by argparse (exit code 2)."""
    result = run_script(
        SCRIPT_PATH,
        'title-token',
        'set',
        '--plan-id',
        'tt-argparse',
        '--state',
        'not-a-valid-state',
    )
    assert result.returncode == 2


def test_set_invalid_owner_rejected_by_argparse():
    """``title-token set --owner <bad>`` is rejected by argparse (exit code 2).

    The owner vocabulary is a closed set exactly as the state vocabulary is, so
    an out-of-enum owner must be refused at parse time rather than silently
    recorded and later un-clearable.
    """
    result = run_script(
        SCRIPT_PATH,
        'title-token',
        'set',
        '--plan-id',
        'tt-argparse-owner',
        '--state',
        'build-busy',
        '--owner',
        'not-a-valid-owner',
    )
    assert result.returncode == 2


def test_set_build_busy_accepted_by_argparse(plan_context):
    """``title-token set --state build-busy --owner build-hook`` is accepted.

    The ``--state`` / ``--owner`` choices are derived from
    ``sorted(TITLE_TOKEN_STATES)`` / ``sorted(TITLE_TOKEN_OWNERS)``, so this
    end-to-end CLI run proves both values reach their choices lists — the
    positive counterpart to the rejection cases above. A created plan is
    required so the command body runs to a clean (exit 0) success rather than
    aborting on a missing status.json.
    """
    cmd_create(Namespace(plan_id='tt-argparse-build-busy', title='Test', phases='1-init', force=False))
    result = run_script(
        SCRIPT_PATH,
        'title-token',
        'set',
        '--plan-id',
        'tt-argparse-build-busy',
        '--state',
        'build-busy',
        '--owner',
        'build-hook',
    )
    assert result.returncode == 0

    stored = _read_status(plan_context, 'tt-argparse-build-busy')['title_token']
    assert stored['state'] == 'build-busy'
    assert stored['owner'] == 'build-hook'


# =============================================================================
# no rendering: the verb writes no title-body.txt artifact
# =============================================================================


def test_set_writes_no_title_body_artifact(plan_context):
    """``set`` persists only status.title_token — no title-body.txt rendering."""
    cmd_create(Namespace(plan_id='tt-no-render', title='Test', phases='1-init', force=False))
    _set('tt-no-render', 'lock-waiting')

    plan_dir = plan_context.plan_dir_for('tt-no-render')
    assert not (plan_dir / 'title-body.txt').exists()


# =============================================================================
# phase writers: NO title-token sweep — staleness is resolved read-side
# =============================================================================

def test_set_phase_performs_no_title_token_sweep(plan_context):
    """``cmd_set_phase`` sweeps nothing on either a forward move or a backward
    loop-back re-entry — same contract as ``cmd_transition``."""
    plan_id = 'tt-set-phase-build-busy'
    cmd_create(Namespace(plan_id=plan_id, title='Test', phases=_PHASES, force=False))

    # Forward move: 1-init -> 3-outline.
    _set(plan_id, 'build-busy', owner='build-hook')
    cmd_set_phase(Namespace(plan_id=plan_id, phase='3-outline'))
    stored = _read_status(plan_context, plan_id)
    assert stored['current_phase'] == '3-outline'
    assert stored['title_token']['state'] == 'build-busy'

    # Backward loop-back: 3-outline -> 2-refine.
    cmd_set_phase(Namespace(plan_id=plan_id, phase='2-refine'))
    stored = _read_status(plan_context, plan_id)
    assert stored['current_phase'] == '2-refine'
    assert stored['title_token']['state'] == 'build-busy'

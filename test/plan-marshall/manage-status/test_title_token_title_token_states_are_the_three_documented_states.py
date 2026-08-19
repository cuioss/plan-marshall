#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the field-only ``title-token`` verb of manage-status.py.

The ``title-token`` verb persists a structured ``{owner, state, set_at}``
record into ``status.title_token`` and performs NO rendering — the composition
(glyph vocabulary + ``{icon} {body}`` assembly) lives in
``manage-terminal-title``. These tests cover:

- ``set`` writes the record for each of the three ``TITLE_TOKEN_STATES``,
  stamped with the caller's owner and a fresh ``set_at``.
- Last-writer arbitration: a ``set`` from ANY owner replaces the record
  wholesale, while ``clear`` is OWNER-SCOPED — a foreign clear is a reported
  no-op.
- Aged-token staleness: a record older than
  ``TITLE_TOKEN_STALE_AFTER_SECONDS`` reads as absent and may be cleared by
  ANY owner. Staleness is READ-side — the phase writers perform no sweep.
- ``clear`` removes the ``title_token`` field, and is idempotent when the
  field is already absent.
- An invalid ``--state`` / ``--owner`` is rejected by argparse (exit code 2)
  before the command body runs.
- The verb writes NO ``title-body.txt`` rendering artifact — manage-status is
  field-only.

The record shape, owner vocabulary, arbitration rule, and staleness threshold
are specified in
``manage-terminal-title/standards/terminal-title-architecture.md``
§ Channel Delivery Contract ruling (c).
"""


from argparse import Namespace
from datetime import UTC, datetime, timedelta

from _title_token_fixtures import (
    EXPECTED_OWNERS,
    EXPECTED_STATES,
    TITLE_TOKEN_OWNERS,
    TITLE_TOKEN_STALE_AFTER_SECONDS,
    TITLE_TOKEN_STATES,
    _age_token,
    _clear,
    _read_status,
    _set,
    cmd_create,
    cmd_title_token,
    read_title_token,
    title_token_is_stale,
)

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


def test_read_title_token_hides_a_stale_record_without_mutating_it():
    """``read_title_token`` is the read-side accessor: a stale record reads as
    absent, and the underlying status dict is left UNTOUCHED (staleness is a
    read-side property, so no writer has to sweep)."""
    aged_at = (datetime.now(UTC) - timedelta(seconds=TITLE_TOKEN_STALE_AFTER_SECONDS + 60)).strftime(
        '%Y-%m-%dT%H:%M:%SZ'
    )
    status = {'title_token': {'owner': 'cli', 'state': 'build-busy', 'set_at': aged_at}}

    assert read_title_token(status) is None
    assert status['title_token']['state'] == 'build-busy'


def test_any_owner_may_clear_a_stale_token(plan_context):
    """A stranded token self-heals: once aged past the threshold, ANY owner may
    clear it, so a dead process cannot leak a glyph indefinitely."""
    plan_id = 'tt-stale-clear'
    cmd_create(Namespace(plan_id=plan_id, title='Test', phases='1-init', force=False))
    _set(plan_id, 'build-busy', owner='build-hook')
    _age_token(plan_context, plan_id, TITLE_TOKEN_STALE_AFTER_SECONDS + 60)

    result = _clear(plan_id, owner='merge-lock')

    assert result['cleared'] is True
    assert result['reason'] == 'stale'
    assert 'title_token' not in _read_status(plan_context, plan_id)


def test_a_fresh_foreign_token_is_still_protected(plan_context):
    """The staleness escape hatch does NOT weaken ownership while the token is
    live — the positive control for the stale-clear case above."""
    plan_id = 'tt-stale-fresh-control'
    cmd_create(Namespace(plan_id=plan_id, title='Test', phases='1-init', force=False))
    _set(plan_id, 'build-busy', owner='build-hook')
    _age_token(plan_context, plan_id, TITLE_TOKEN_STALE_AFTER_SECONDS - 60)

    result = _clear(plan_id, owner='merge-lock')

    assert result['cleared'] is False
    assert result['reason'] == 'foreign_owner'

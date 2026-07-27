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

import json
import subprocess
from argparse import Namespace
from datetime import UTC, datetime, timedelta
from pathlib import Path

from conftest import get_script_path, load_script_module, run_script

# Script path for the argparse-rejection CLI test.
SCRIPT_PATH = get_script_path('plan-marshall', 'manage-status', 'manage-status.py')

_lifecycle = load_script_module('plan-marshall', 'manage-status', '_cmd_lifecycle.py', '_status_cmd_lifecycle')
_query = load_script_module('plan-marshall', 'manage-status', '_status_query.py', '_status_cmd_query')
_core = load_script_module('plan-marshall', 'manage-status', '_status_core.py', '_status_cmd_core')

cmd_create = _lifecycle.cmd_create
cmd_archive = _lifecycle.cmd_archive
cmd_transition = _lifecycle.cmd_transition
cmd_title_token = _query.cmd_title_token
cmd_set_phase = _query.cmd_set_phase
TITLE_TOKEN_STATES = _core.TITLE_TOKEN_STATES
TITLE_TOKEN_OWNERS = _core.TITLE_TOKEN_OWNERS
TITLE_TOKEN_STALE_AFTER_SECONDS = _core.TITLE_TOKEN_STALE_AFTER_SECONDS
title_token_is_stale = _core.title_token_is_stale
read_title_token = _core.read_title_token

# A multi-phase plan whose adjacent transitions never reach the 6-finalize
# blocking boundary, so cmd_transition performs a plain phase advance (no
# strict-verify guard) — the surface the phase-writer tests exercise.
_PHASES = '1-init,2-refine,3-outline'

# The three canonical title-token states: the two lock-coordination phases
# (lock-waiting / lock-owned) plus the orchestration-busy state (build-busy).
# Asserted explicitly here so a silent change to TITLE_TOKEN_STATES surfaces
# as a test failure rather than passing vacuously.
EXPECTED_STATES = frozenset({'lock-waiting', 'lock-owned', 'build-busy'})

# The three owners that may write a title token, likewise asserted explicitly.
EXPECTED_OWNERS = frozenset({'build-hook', 'merge-lock', 'cli'})


def _read_status(plan_context, plan_id):
    """Read the on-disk status.json for ``plan_id`` as a dict."""
    status_file = plan_context.plan_dir_for(plan_id) / 'status.json'
    return json.loads(status_file.read_text(encoding='utf-8'))


def _set(plan_id, state, owner='cli'):
    """Invoke ``title-token set`` for ``plan_id`` as ``owner``."""
    return cmd_title_token(
        Namespace(plan_id=plan_id, token_verb='set', state=state, owner=owner)
    )


def _clear(plan_id, owner='cli'):
    """Invoke ``title-token clear`` for ``plan_id`` as ``owner``."""
    return cmd_title_token(Namespace(plan_id=plan_id, token_verb='clear', owner=owner))


def _age_token(plan_context, plan_id, seconds):
    """Backdate the stored token's ``set_at`` by ``seconds``, in place."""
    status_file = plan_context.plan_dir_for(plan_id) / 'status.json'
    status = json.loads(status_file.read_text(encoding='utf-8'))
    aged = datetime.now(UTC) - timedelta(seconds=seconds)
    status['title_token']['set_at'] = aged.strftime('%Y-%m-%dT%H:%M:%SZ')
    status_file.write_text(json.dumps(status), encoding='utf-8')


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


def test_clear_writes_no_title_body_artifact(plan_context):
    """``clear`` persists only status.json — no title-body.txt rendering."""
    cmd_create(Namespace(plan_id='tt-no-render-clear', title='Test', phases='1-init', force=False))
    _set('tt-no-render-clear', 'lock-owned')
    _clear('tt-no-render-clear')

    plan_dir = plan_context.plan_dir_for('tt-no-render-clear')
    assert not (plan_dir / 'title-body.txt').exists()


# =============================================================================
# archive: cmd_archive pops title_token before writing the archived status.json
# =============================================================================
#
# An archived plan has no live session driving its terminal title, so any
# in-flight title_token (a lock state) left behind would persist a stale lock
# glyph in the archived snapshot. cmd_archive must pop the field
# token-agnostically — a single pop covers every TITLE_TOKEN_STATES value.
# This test asserts the field is absent from the archived status.json after
# archiving with a pre-set merge token.


def _read_archived_status(result):
    """Read the archived status.json from a cmd_archive result dict."""
    archived_status_path = Path(result['archived_to']) / 'status.json'
    assert archived_status_path.exists(), (
        f'archived status.json missing at {archived_status_path} — '
        f'either move failed or archived_to points to wrong path'
    )
    return json.loads(archived_status_path.read_text(encoding='utf-8'))


def test_archive_pops_merge_lock_title_token(plan_context):
    """cmd_archive must pop a pre-set merge-lock title_token before archiving."""
    plan_id = 'tt-archive-merge-token'
    cmd_create(Namespace(plan_id=plan_id, title='Test', phases='1-init', force=False))
    # A merge-lock token represents an in-flight lock state held by the now-gone
    # live session.
    _set(plan_id, 'lock-owned', owner='merge-lock')

    result = cmd_archive(Namespace(plan_id=plan_id, dry_run=False))

    assert result['status'] == 'success', f'archive failed: {result}'
    archived_status = _read_archived_status(result)
    assert 'title_token' not in archived_status, (
        f"Expected title_token absent from archived status.json after archiving "
        f"with a pre-set merge token, but found "
        f"{archived_status.get('title_token')!r}. cmd_archive must pop "
        f"title_token before write_status/shutil.move."
    )


def test_archive_pops_build_busy_title_token(plan_context):
    """cmd_archive must pop a pre-set build-busy title_token before archiving.

    A build-busy token left behind on an archived plan would persist a stale
    🔨 build glyph in the archived snapshot — the same stale-glyph hazard the
    lock-token variant guards against. cmd_archive's pop is owner- AND
    token-agnostic, so a single pop covers every record regardless of which
    writer owns it: an archived plan holds no live coordination state worth
    arbitrating over. This is the one sanctioned exception to the owner-scoped
    clear.
    """
    plan_id = 'tt-archive-build-busy-token'
    cmd_create(Namespace(plan_id=plan_id, title='Test', phases='1-init', force=False))
    # An in-flight build-busy token represents an orchestration build state held
    # by the now-gone live session, owned by a writer that is NOT the archiver.
    _set(plan_id, 'build-busy', owner='build-hook')

    result = cmd_archive(Namespace(plan_id=plan_id, dry_run=False))

    assert result['status'] == 'success', f'archive failed: {result}'
    archived_status = _read_archived_status(result)
    assert 'title_token' not in archived_status, (
        f"Expected title_token absent from archived status.json after archiving "
        f"with a pre-set build-busy token, but found "
        f"{archived_status.get('title_token')!r}. cmd_archive must pop "
        f"title_token before write_status/shutil.move."
    )


# =============================================================================
# phase writers: NO title-token sweep — staleness is resolved read-side
# =============================================================================
#
# The phase writers deliberately clear NOTHING. A transition-side sweep only
# fires when a phase happens to change, so a token stranded by a killed process
# could outlive it indefinitely — the sweep looked like a safety net while
# leaving the actual hazard open. Staleness is therefore a READ-side property:
# every reader resolves it through the aged-token predicate, so a stranded
# token self-heals on the next read regardless of whether any phase moves.


def test_transition_performs_no_title_token_sweep(plan_context):
    """``cmd_transition`` leaves a live build-busy token exactly as it found it.

    A transition is not a title-token event. The token survives the phase write
    unmodified; it is the aged-token READ predicate, not this writer, that
    retires a stranded token.
    """
    plan_id = 'tt-transition-build-busy'
    cmd_create(Namespace(plan_id=plan_id, title='Test', phases=_PHASES, force=False))
    _set(plan_id, 'build-busy', owner='build-hook')

    result = cmd_transition(Namespace(plan_id=plan_id, completed='1-init'))

    assert result['status'] == 'success', f'transition failed: {result}'
    stored = _read_status(plan_context, plan_id)
    assert stored['current_phase'] == '2-refine'
    assert stored['title_token']['state'] == 'build-busy'
    assert stored['title_token']['owner'] == 'build-hook'


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


def test_lock_tokens_preserved_across_transition_and_set_phase(plan_context):
    """A live lock token survives both phase writers untouched — the live
    coordination signal is not weakened by a phase change."""
    # lock-owned survives cmd_transition.
    plan_id = 'tt-lock-owned-preserved'
    cmd_create(Namespace(plan_id=plan_id, title='Test', phases=_PHASES, force=False))
    _set(plan_id, 'lock-owned', owner='merge-lock')
    cmd_transition(Namespace(plan_id=plan_id, completed='1-init'))
    stored = _read_status(plan_context, plan_id)
    assert stored['title_token']['state'] == 'lock-owned'

    # lock-waiting survives cmd_set_phase.
    plan_id = 'tt-lock-waiting-preserved'
    cmd_create(Namespace(plan_id=plan_id, title='Test', phases=_PHASES, force=False))
    _set(plan_id, 'lock-waiting', owner='merge-lock')
    cmd_set_phase(Namespace(plan_id=plan_id, phase='2-refine'))
    stored = _read_status(plan_context, plan_id)
    assert stored['title_token']['state'] == 'lock-waiting'


def test_killed_detached_build_busy_token_ages_out_without_any_phase_change(plan_context):
    """Killed-detached-build repro, re-pinned to the mechanism that actually
    closes it: arm build-busy, let the clear never fire, and take NO phase
    action at all. The token must still read as absent once it ages past the
    threshold — which is precisely what the retired phase-boundary sweep could
    not deliver, because a plan that never transitions never swept.
    """
    plan_id = 'tt-killed-detached-build'
    cmd_create(Namespace(plan_id=plan_id, title='Test', phases=_PHASES, force=False))
    _set(plan_id, 'build-busy', owner='build-hook')
    armed = _read_status(plan_context, plan_id)
    assert armed['title_token']['state'] == 'build-busy'

    _age_token(plan_context, plan_id, TITLE_TOKEN_STALE_AFTER_SECONDS + 60)

    stranded = _read_status(plan_context, plan_id)
    assert read_title_token(stranded) is None, (
        'A killed detached build left build-busy armed and the aged-token read '
        'predicate failed to retire it.'
    )


# =============================================================================
# drive seam: the state settle reports no delivery, because it delivers nothing
# =============================================================================
#
# ``_drive_repaint`` delegates a ``session push-title-token`` to platform-runtime
# through the executor. That seam BINDS AND PERSISTS — it does not repaint: the
# direct /dev/tty write is deleted, so the paired repaint is deferred to the next
# hook render event. The seam consequently has NO delivery outcome to report and
# writes NO non-delivery work-log entry: the only reply it can receive is the
# ordinary ``no_title_state`` nothing-to-settle case, which stays at DEBUG. The
# seam never alters the command's status or exit code.


def _log_entry_spy():
    """Build a ``log_entry`` spy plus the list it appends each call to.

    Returns ``(calls, spy)`` where ``spy`` matches ``plan_logging.log_entry``'s
    signature and records ``(log_type, plan_id, level, message)`` per call. The
    caller installs the spy in the namespace the code under test resolves
    ``log_entry`` from — ``_core`` for the direct drive-seam unit tests, or
    ``_lifecycle._drive_*.__globals__`` for the cmd_archive integration test —
    so the substitution reaches the instance actually called.
    """
    calls: list[tuple[str, str, str, str]] = []

    def spy(log_type, plan_id, level, message, store='plans'):
        calls.append((log_type, plan_id, level, message))

    return calls, spy


def _read_work_log(plan_context, plan_id):
    """Return the plan's persisted work.log text (empty string when absent)."""
    log_file = plan_context.plan_dir_for(plan_id) / 'logs' / 'work.log'
    if not log_file.exists():
        return ''
    return log_file.read_text(encoding='utf-8')


def _repaint_reply(**fields):
    """Build a CompletedProcess carrying a push-title-token TOON reply."""
    lines = ['status: success', 'operation: session push-title-token']
    lines += [f'{key}: {value}' for key, value in fields.items()]
    return subprocess.CompletedProcess(
        args=[], returncode=0, stdout='\n'.join(lines) + '\n', stderr=''
    )


def test_archive_releases_no_session_binding(plan_context, monkeypatch):
    """``cmd_archive`` fires NO teardown delegation at all.

    The retired test asserted the archive fired a teardown "exactly once" —
    it asserted the SEAM FIRED, never that the terminal ever RECEIVED anything,
    and the behaviour it pinned is now wrong outright. Archive must release no
    binding: the terminal ✅ state it just persisted is delivered by the next
    hook render, and that render can only resolve the plan while the binding
    still exists. Releasing here would destroy the delivery route for the very
    state the archive wrote.

    The assertion is therefore inverted and made about the DELIVERED effect:
    every executor delegation the archive makes is captured, and none of them
    may be a session teardown.
    """
    calls: list[tuple[str, ...]] = []
    monkeypatch.setitem(
        _lifecycle._surface_drive.__globals__,
        '_run_executor',
        lambda notation, *cli_args: calls.append((notation, *cli_args)),
    )

    plan_id = 'tt-archive-teardown'
    cmd_create(Namespace(plan_id=plan_id, title='Test', phases='1-init', force=False))
    result = cmd_archive(Namespace(plan_id=plan_id, dry_run=False))

    assert result['status'] == 'success'
    teardown_calls = [c for c in calls if c[1:] == ('session', 'teardown')]
    assert teardown_calls == [], (
        'archive released a session binding — the terminal state it just '
        'persisted can no longer be delivered'
    )
    # The plan directory really moved.
    assert Path(result['archived_to']).is_dir()


def test_repaint_persists_nothing_when_delegate_reports_no_title_state(monkeypatch):
    """``no_title_state`` is the ordinary nothing-to-settle case — no persisted entry."""
    monkeypatch.setattr(
        _core,
        '_run_executor',
        lambda *_args: _repaint_reply(plan_id='tt-repaint-nostate', reason='no_title_state'),
    )
    calls, spy = _log_entry_spy()
    monkeypatch.setattr(_core, 'log_entry', spy)

    _core._drive_repaint('tt-repaint-nostate')

    assert calls == []


def test_repaint_persists_nothing_on_a_settled_state(monkeypatch):
    """A settled state (no ``reason``) persists no entry either.

    Together with the ``no_title_state`` case above this pins the seam's whole
    reply space: it has no delivery verdict to report, so NO reply shape can
    make it write a non-delivery entry.
    """
    monkeypatch.setattr(
        _core,
        '_run_executor',
        lambda *_args: _repaint_reply(plan_id='tt-repaint-ok'),
    )
    calls, spy = _log_entry_spy()
    monkeypatch.setattr(_core, 'log_entry', spy)

    _core._drive_repaint('tt-repaint-ok')

    assert calls == []


def test_repaint_persists_nothing_when_delegate_was_skipped(monkeypatch):
    """A skipped spawn (``_run_executor`` returned None) persists no entry."""
    monkeypatch.setattr(_core, '_run_executor', lambda *_args: None)
    calls, spy = _log_entry_spy()
    monkeypatch.setattr(_core, 'log_entry', spy)

    _core._drive_repaint('tt-repaint-skipped')

    assert calls == []


def test_transition_writes_no_repaint_non_delivery_entry(plan_context, monkeypatch):
    """A real ``current_phase`` transition writes NO title non-delivery entry.

    The end-to-end counterpart of the unit tests above, exercising the real
    ``log_entry`` file write through ``cmd_transition`` -> ``_surface_drive`` ->
    ``_drive_repaint``. The seam settles state and defers the repaint to the
    next render event, so it has no delivery verdict to report — a persisted
    "not delivered" entry would be asserting a channel outcome this layer
    cannot observe.
    """
    plan_id = 'tt-transition-nondelivery'
    cmd_create(Namespace(plan_id=plan_id, title='Test', phases=_PHASES, force=False))

    # Both drive-seam delegates (bind, then settle) route through this executor
    # stub. Patched AFTER cmd_create so the creation-time drive seam does not
    # write a spurious entry.
    monkeypatch.setitem(
        _lifecycle._surface_drive.__globals__,
        '_run_executor',
        lambda *_args: _repaint_reply(plan_id=plan_id, reason='no_title_state'),
    )

    result = cmd_transition(Namespace(plan_id=plan_id, completed='1-init'))

    assert result['status'] == 'success'
    work_log = _read_work_log(plan_context, plan_id)
    assert 'not delivered' not in work_log
    assert 'no_controlling_tty' not in work_log


# =============================================================================
# drive seam: the archive-time teardown seam is GONE
# =============================================================================
#
# ``_drive_teardown`` and its non-delivery reporting existed to release the
# session binding at archive time. Archive now deliberately releases NO binding
# (the terminal state it persists is delivered by the next hook render, which
# resolves the plan only through that binding), so the seam has no caller and
# was removed outright rather than left in place as an unreachable helper.
#
# The tests that certified its two-half ``reset`` / ``unbound`` reporting went
# with it: they asserted a ``reset`` outcome that production can never produce
# in this runtime, so they could only ever have passed against a mock.


def test_teardown_drive_seam_is_removed():
    """The dead teardown seam and its parse helpers are gone from the module.

    A dead private helper is invisible at its own call site — there is none —
    so this names it explicitly. If a future change re-introduces an
    archive-time binding release, it fails here first, next to the comment
    explaining why archive must not release.
    """
    for removed in ('_drive_teardown', '_teardown_non_delivery_reason', '_parse_drive_reply'):
        assert not hasattr(_core, removed), (
            f'{removed} is back — archive must release no session binding'
        )


def test_crashing_delegate_leaves_transition_outcome_unchanged(plan_context, monkeypatch):
    """A delegate that crashes outright never changes the status-write outcome.

    ``_surface_drive`` is fully exception-swallowing, so a raising delegate must
    leave ``cmd_transition`` returning ``status: success`` with the phase advanced
    exactly as it would with a healthy seam.
    """

    def _boom(*_args):
        raise RuntimeError('delegate exploded')

    # Patch the seam's own module globals so the substitution reaches the
    # _status_core instance cmd_transition actually calls into.
    monkeypatch.setitem(_lifecycle._surface_drive.__globals__, '_run_executor', _boom)

    plan_id = 'tt-repaint-crash'
    cmd_create(Namespace(plan_id=plan_id, title='Test', phases=_PHASES, force=False))
    result = cmd_transition(Namespace(plan_id=plan_id, completed='1-init'))

    assert result['status'] == 'success'
    stored = _read_status(plan_context, plan_id)
    assert stored['current_phase'] == '2-refine'

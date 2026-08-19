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
from pathlib import Path

from _title_token_fixtures import (
    _PHASES,
    SCRIPT_PATH,
    TITLE_TOKEN_STALE_AFTER_SECONDS,
    _age_token,
    _clear,
    _lifecycle,
    _read_archived_status,
    _read_status,
    _set,
    cmd_archive,
    cmd_create,
    cmd_set_phase,
    cmd_transition,
    read_title_token,
)

from conftest import run_script

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

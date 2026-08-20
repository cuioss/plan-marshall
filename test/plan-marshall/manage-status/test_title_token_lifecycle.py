#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for how a ``title-token`` record behaves across a plan's lifecycle:
phase writes, age-based staleness, archival, and the state-settle drive seam."""


from argparse import Namespace
from datetime import UTC, datetime, timedelta
from pathlib import Path

from _title_token_fixtures import (
    _PHASES,
    TITLE_TOKEN_STALE_AFTER_SECONDS,
    _age_token,
    _clear,
    _lifecycle,
    _read_archived_status,
    _read_status,
    _read_work_log,
    _repaint_reply,
    _set,
    cmd_archive,
    cmd_create,
    cmd_set_phase,
    cmd_transition,
    read_title_token,
)

# =============================================================================
# phase writers: NO title-token sweep — staleness is resolved read-side
# =============================================================================

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
# staleness: read-side, age-based, clearable by ANY owner
# =============================================================================

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
# archive: cmd_archive pops title_token before writing the archived status.json
# =============================================================================

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
# drive seam: the state settle reports no delivery, because it delivers nothing
# =============================================================================

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

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

from _title_token_fixtures import (
    _PHASES,
    _core,
    _lifecycle,
    _log_entry_spy,
    _read_status,
    _read_work_log,
    _repaint_reply,
    cmd_create,
    cmd_transition,
)


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

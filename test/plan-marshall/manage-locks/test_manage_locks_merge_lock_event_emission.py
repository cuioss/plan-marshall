#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: F811 — tests take the imported fixture as a parameter
"""Tests for the unified ``manage-locks/merge_lock.py`` — the single main-anchored
merge-to-main serializer fronted by a FIFO admission queue.

Its sections, in order:

* Fixtures
* [LOCK] event emission (best-effort, OUTSIDE the O_EXCL window)
"""


from __future__ import annotations

from argparse import Namespace
from pathlib import Path

import pytest
from _manage_locks_merge_lock_fixtures import (  # noqa: F401 — a fixture is used by NAME, not by reference
    _locks_core,
    _make_live_plan,
    _read_lock_log,
    _stub_title_tokens,
    _TokenRecorder,
    isolated_base,  # noqa: F401 — a fixture is used by NAME, not by reference
    merge_lock,
)

# =============================================================================
# Fixtures
# =============================================================================


# =============================================================================
# [LOCK] event emission (best-effort, OUTSIDE the O_EXCL window)
# =============================================================================


class TestLockEventEmission:
    """Each merge-lock lifecycle point emits a ``[LOCK]`` event into the SINGLE
    main-anchored global lock-event log via the shared
    :func:`_locks_core.log_lock_event`: ``acquired`` on a fresh O_EXCL create,
    ``reclaimed`` on a stale-reclaim re-create (carrying the reclaimed-from
    holder), ``blocked`` on a blocked admission (carrying holder/waiter), and
    ``released`` on the real os.unlink. ``check`` and the foreign / already-free
    release noops emit nothing. Every emission is best-effort and OUTSIDE the
    atomic window — a logging failure never breaks the lock action.

    The ``isolated_base`` fixture stages PLAN_BASE_DIR at ``<tmp>/main/.plan/local``
    so the lock-event log resolves to the per-test ``<tmp>/main/.plan/logs`` dir."""

    def test_acquire_emits_lock_acquired(self, isolated_base: dict) -> None:
        merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))

        content = _read_lock_log()
        # lock_id is the holder plan_id; the family is `merge`.
        assert '[LOCK] (merge:acquired) plan-a' in content

    def test_reclaim_emits_lock_reclaimed_with_reclaimed_from(self, isolated_base: dict) -> None:
        """A reclaim of a dead holder's lock emits ``reclaimed`` carrying the
        reclaimed-from holder for correlation."""
        # plan-dead acquires but never gets a plan dir → dead → reclaimable. It is
        # dequeued so plan-b becomes the FIFO front and reclaims.
        merge_lock.run_acquire(Namespace(plan_id='plan-dead', timeout=5.0))
        merge_lock._dequeue_fifo('plan-dead')

        result = merge_lock.run_acquire(Namespace(plan_id='plan-b', timeout=5.0))
        assert result['reclaimed'] is True

        content = _read_lock_log()
        assert '[LOCK] (merge:reclaimed) plan-b' in content
        # The reclaimed-from holder is carried as a correlation field.
        assert 'reclaimed_from: plan-dead' in content

    def test_blocked_acquire_emits_lock_blocked_with_holder_and_waiter(
        self, isolated_base: dict
    ) -> None:
        """A blocked admission against a LIVE holder emits ``blocked`` carrying the
        blocking holder and the waiter."""
        merge_lock.run_acquire(Namespace(plan_id='plan-live', timeout=5.0))
        _make_live_plan(isolated_base['base'], 'plan-live')

        result = merge_lock.run_acquire(Namespace(plan_id='plan-b', timeout=0.3))
        assert result['status'] == 'blocked'

        content = _read_lock_log()
        assert '[LOCK] (merge:blocked) plan-b' in content
        assert 'holder: plan-live' in content
        assert 'waiter: plan-b' in content

    def test_release_emits_lock_released(self, isolated_base: dict) -> None:
        merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        result = merge_lock.run_release(Namespace(plan_id='plan-a'))
        assert result['action'] == 'released'

        content = _read_lock_log()
        assert '[LOCK] (merge:released) plan-a' in content

    def test_check_emits_no_lock_event(self, isolated_base: dict) -> None:
        """``check`` is a non-mutating read — it changes no ownership and emits
        nothing into the lock-event timeline."""
        merge_lock.run_check(Namespace(plan_id='plan-a'))

        assert _read_lock_log() == ''

    def test_already_free_release_emits_no_lock_event(self, isolated_base: dict) -> None:
        """An already-free release noop removed no lock this caller held — it
        emits nothing (only the real ``released`` branch emits)."""
        result = merge_lock.run_release(Namespace(plan_id='plan-a'))
        assert result['action'] == 'noop'

        assert '[LOCK] (merge:released)' not in _read_lock_log()

    def test_foreign_holder_release_emits_no_lock_event(self, isolated_base: dict) -> None:
        """A foreign-holder release noop leaves the lock intact and changes no
        ownership — it emits no ``released`` event."""
        merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))

        result = merge_lock.run_release(Namespace(plan_id='plan-b'))
        assert result['action'] == 'noop'

        content = _read_lock_log()
        # plan-a's acquire emitted; plan-b's foreign-holder noop did NOT emit a
        # released event.
        assert '[LOCK] (merge:released)' not in content

    def test_lock_event_lands_in_main_anchored_log_not_worktree(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The [LOCK] event lands in the MAIN-anchored global log even when cwd is
        pinned to a worktree — asserted via the PLAN_BASE_DIR override, not a
        worktree path. A worktree-relative .plan/logs dir must hold no lock log."""
        main_base = tmp_path / 'main' / '.plan' / 'local'
        (main_base / 'plans').mkdir(parents=True)
        monkeypatch.setenv('PLAN_BASE_DIR', str(main_base))

        worktree = tmp_path / 'worktrees' / 'some-plan'
        (worktree / '.plan' / 'local').mkdir(parents=True)
        monkeypatch.chdir(worktree)

        merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))

        content = _read_lock_log()
        assert '[LOCK] (merge:acquired) plan-a' in content
        # No lock-event log under the worktree-relative .plan/logs.
        assert not (worktree / '.plan' / 'logs').exists()

    def test_log_failure_never_breaks_acquire(
        self, isolated_base: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A [LOCK]-emission failure NEVER aborts the lock acquire — the emission
        is best-effort, with the swallow try/except INSIDE ``log_lock_event``
        itself. Make the REAL ``log_lock_event``'s internal resolver raise (the
        seam ``_resolve_lock_log_path`` on the shared core) and assert the
        function swallows it and the acquire still succeeds with the lock file
        created. Patching the bare ``log_lock_event`` name would (correctly) NOT
        be swallowed — the call sites invoke it directly — so the realistic
        failure is one inside the helper's own try/except."""
        def _raising_resolver() -> object:
            raise OSError('log dir gone')

        monkeypatch.setattr(_locks_core, '_resolve_lock_log_path', _raising_resolver)

        result = merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))

        assert result['status'] == 'success'
        assert result['action'] == 'acquired'
        assert isolated_base['lock_path'].is_file()

    def test_log_failure_never_breaks_release(
        self, isolated_base: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Symmetric on the RELEASE side: a [LOCK]-emission failure (the real
        helper's internal resolver raising, swallowed by its own try/except)
        NEVER aborts the lock release — the lock file is still removed."""
        merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        assert isolated_base['lock_path'].is_file()

        def _raising_resolver() -> object:
            raise OSError('log dir gone')

        monkeypatch.setattr(_locks_core, '_resolve_lock_log_path', _raising_resolver)

        result = merge_lock.run_release(Namespace(plan_id='plan-a'))

        assert result['status'] == 'success'
        assert result['action'] == 'released'
        assert not isolated_base['lock_path'].exists()

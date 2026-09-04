#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2

"""Tests for ``manage-locks/build_queue.py`` — the bounded-``k``-slot build-queue
concurrency limiter with a FIFO waiting queue.

Its sections, in order:

* CLI argparse plumbing
* [LOCK] event emission (best-effort, AFTER rmw_json commits)
"""


from __future__ import annotations

from argparse import Namespace
from pathlib import Path

import pytest
from _build_queue_fixtures import (
    SCRIPT_PATH,
    _init_git_repo,
    _locks_core,
    _make_live_plan,
    _read_lock_log,
    _read_queue,
    _set_max_slots,
    build_queue,
    isolated_base,
)

from conftest import run_script

# =============================================================================
# CLI argparse plumbing
# =============================================================================


class TestCli:
    def test_acquire_requires_plan_id(self) -> None:
        result = run_script(SCRIPT_PATH, 'acquire')
        assert result.returncode != 0
        assert '--plan-id' in result.stderr or '--plan-id' in result.stdout

    def test_release_requires_plan_id_and_id(self) -> None:
        result = run_script(SCRIPT_PATH, 'release', '--plan-id', 'plan-a')
        assert result.returncode != 0
        assert '--id' in result.stderr or '--id' in result.stdout


# =============================================================================
# [LOCK] event emission (best-effort, AFTER rmw_json commits)
# =============================================================================


class TestLockEventEmission:
    """Each build-queue lifecycle outcome emits a ``[LOCK]`` event into the SINGLE
    main-anchored global lock-event log via the shared
    :func:`_locks_core.log_lock_event`, always AFTER ``rmw_json`` commits:
    ``acquire`` emits ``acquired`` on an admitted outcome and ``blocked`` on a
    blocked outcome (carrying active/waiting counts; the waiter on a block is the
    acquiring plan_id); ``release`` emits ``released`` on a real release and ALSO
    ``acquired`` for a FIFO-promoted waiter. A no-op release emits nothing. The
    ``lock_id`` is the admission id ``{plan_id}:{uuid4}``. A logging failure is
    swallowed and cannot affect admission/release.

    The ``isolated_base`` fixture stages PLAN_BASE_DIR at ``<tmp>/main/.plan/local``
    so the lock-event log resolves to the per-test ``<tmp>/main/.plan/logs`` dir."""

    def test_admitted_acquire_emits_lock_acquired(self, isolated_base: dict) -> None:
        acq = build_queue.run_acquire(Namespace(plan_id='plan-a'))
        assert acq['admission'] == 'admitted'

        content = _read_lock_log()
        # lock_id is the admission id {plan_id}:{uuid4}; family is `build`.
        assert f'[LOCK] (build:acquired) {acq["id"]}' in content
        # Capacity counts are carried as correlation fields.
        assert 'active_count: 1' in content
        assert 'waiting_count: 0' in content

    def test_blocked_acquire_emits_lock_blocked_with_waiter(self, isolated_base: dict) -> None:
        _set_max_slots(isolated_base['base'], 1)
        _make_live_plan(isolated_base['base'], 'plan-held')
        build_queue.run_acquire(Namespace(plan_id='plan-held'))

        _make_live_plan(isolated_base['base'], 'plan-b')
        blk = build_queue.run_acquire(Namespace(plan_id='plan-b'))
        assert blk['admission'] == 'blocked'

        content = _read_lock_log()
        assert f'[LOCK] (build:blocked) {blk["id"]}' in content
        # The waiter on a block is the acquiring plan_id.
        assert 'waiter: plan-b' in content
        assert 'active_count: 1' in content
        assert 'waiting_count: 1' in content

    def test_release_emits_lock_released(self, isolated_base: dict) -> None:
        acq = build_queue.run_acquire(Namespace(plan_id='plan-a'))
        rel = build_queue.run_release(Namespace(plan_id='plan-a', id=acq['id']))
        assert rel['action'] == 'released'

        content = _read_lock_log()
        assert f'[LOCK] (build:released) {acq["id"]}' in content

    def test_release_with_fifo_promote_emits_released_and_promoted_acquired(
        self, isolated_base: dict
    ) -> None:
        """A release that frees a slot AND FIFO-promotes a waiter emits BOTH a
        ``released`` for the released id and an ``acquired`` for the promoted id —
        the promotion is recorded in the same main-anchored timeline."""
        _set_max_slots(isolated_base['base'], 1)
        for name in ('plan-held', 'plan-w1'):
            _make_live_plan(isolated_base['base'], name)
        held = build_queue.run_acquire(Namespace(plan_id='plan-held'))
        wait = build_queue.run_acquire(Namespace(plan_id='plan-w1'))
        assert wait['admission'] == 'blocked'

        rel = build_queue.run_release(Namespace(plan_id='plan-held', id=held['id']))
        assert rel['promoted'] == wait['id']

        content = _read_lock_log()
        assert f'[LOCK] (build:released) {held["id"]}' in content
        # The promoted waiter's slot was just granted → an `acquired` event.
        assert f'[LOCK] (build:acquired) {wait["id"]}' in content

    def test_noop_release_emits_no_lock_event(self, isolated_base: dict) -> None:
        """A no-op release of an absent id changed no state — it emits nothing."""
        rel = build_queue.run_release(Namespace(plan_id='plan-a', id='plan-a:ghost-uuid'))
        assert rel['action'] == 'noop'

        assert _read_lock_log() == ''

    def test_lock_event_lands_in_main_anchored_log_not_worktree(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The [LOCK] event lands in the MAIN-anchored global log even when cwd is
        pinned to a worktree — asserted via the PLAN_BASE_DIR override, not a
        worktree path. A worktree-relative .plan/logs dir must hold no lock log.
        The queue itself is machine-global (home_root()), isolated here via
        PLAN_MARSHALL_HOME; the lock log stays main-anchored (PLAN_BASE_DIR)."""
        main_repo = tmp_path / 'main'
        main_base = main_repo / '.plan' / 'local'
        (main_base / 'plans').mkdir(parents=True)
        home = tmp_path / 'home'
        home.mkdir()
        monkeypatch.setenv('PLAN_BASE_DIR', str(main_base))
        monkeypatch.setenv('PLAN_MARSHALL_HOME', str(home))
        monkeypatch.setattr(build_queue, 'main_checkout_root', lambda: main_repo)

        worktree = tmp_path / 'worktrees' / 'some-plan'
        (worktree / '.plan' / 'local').mkdir(parents=True)
        monkeypatch.chdir(worktree)

        acq = build_queue.run_acquire(Namespace(plan_id='plan-a'))

        content = _read_lock_log()
        assert f'[LOCK] (build:acquired) {acq["id"]}' in content
        assert not (worktree / '.plan' / 'logs').exists()

    def test_log_failure_never_breaks_acquire(
        self, isolated_base: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A [LOCK]-emission failure NEVER aborts the slot acquire — the emission
        is best-effort, with the swallow try/except INSIDE ``log_lock_event``
        itself, and fires AFTER rmw_json commits. Make the REAL helper's internal
        resolver raise (the seam ``_resolve_lock_log_path`` on the shared core);
        the function swallows it and the acquire still succeeds with the slot
        persisted. Patching the bare ``log_lock_event`` name would (correctly) NOT
        be swallowed — the call site invokes it directly — so the realistic
        failure is one inside the helper's own try/except."""
        def _raising_resolver() -> object:
            raise OSError('log dir gone')

        monkeypatch.setattr(_locks_core, '_resolve_lock_log_path', _raising_resolver)

        result = build_queue.run_acquire(Namespace(plan_id='plan-a'))

        assert result['status'] == 'success'
        assert result['admission'] == 'admitted'
        # The slot was persisted despite the emission raising.
        state = _read_queue(isolated_base['queue_path'])
        assert [e['id'] for e in state['active']] == [result['id']]

    def test_log_failure_never_breaks_release(
        self, isolated_base: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Symmetric on the RELEASE side: a [LOCK]-emission failure (the real
        helper's internal resolver raising, swallowed by its own try/except)
        NEVER aborts the slot release — the slot is still freed."""
        acq = build_queue.run_acquire(Namespace(plan_id='plan-a'))

        def _raising_resolver() -> object:
            raise OSError('log dir gone')

        monkeypatch.setattr(_locks_core, '_resolve_lock_log_path', _raising_resolver)

        result = build_queue.run_release(Namespace(plan_id='plan-a', id=acq['id']))

        assert result['status'] == 'success'
        assert result['action'] == 'released'
        # The slot was freed despite the emission raising.
        state = _read_queue(isolated_base['queue_path'])
        assert state['active'] == []

#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for integrate_into_main.py — the bounded move-back admission and its dequeue.

Contract under test:

* **Bounded admission wait** — the move-back acquire forwards a bounded
  ``wait_seconds`` that sits below the merge lock's own per-call ceiling.
* **Dequeue on every refused acquire** — an acquire that takes no lock, whether it
  returns ``status: blocked`` once the bound lapses or ``status: error`` from any
  attempt, is followed by a dequeue from the merge FIFO queue. A foreign holder's
  lock is left intact, and the surfaced payload carries ``dequeued`` reporting
  whether the dequeue landed. An error on a later attempt of the same wait can
  follow an earlier attempt's enqueue, so an error is dequeued exactly like a block.
* **A failed dequeue is reported, never masked** — a release that raises or that
  answers anything but ``status: success`` yields ``dequeued: false`` beside the
  acquire payload.

Isolation: every test runs against an isolated main + worktree tree staged under
``tmp_path``. Stub merge locks stand in for the primitive where only the routing
is under test; the real ``merge_lock`` runs where the queue state itself is the
claim, against the staged main through ``PLAN_BASE_DIR``.
"""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path
from typing import Any

import pytest

from conftest import load_script_module

integrate_into_main = load_script_module(
    'plan-marshall', 'workflow-integration-git', 'integrate_into_main.py', 'integrate_into_main'
)

_PLAN_ID = 'sample-plan'
_FOREIGN_PLAN_ID = 'foreign-plan'


# =============================================================================
# Stub merge locks
# =============================================================================


class _ScriptedMergeLock:
    """Stub merge_lock whose acquire and release answer canned payloads.

    ``release_result`` is returned by ``run_release`` unless ``release_raises`` is
    set, in which case the release raises instead. Every call is counted.
    """

    def __init__(
        self,
        acquire_result: dict[str, Any] | None = None,
        *,
        release_result: dict[str, Any] | None = None,
        release_raises: bool = False,
    ) -> None:
        self.acquire_result = acquire_result or {'status': 'success', 'action': 'acquired'}
        self.release_result = release_result or {'status': 'success', 'action': 'noop'}
        self.release_raises = release_raises
        self.acquired = 0
        self.released = 0
        self.acquire_wait_seconds: list[object] = []

    def run_acquire(self, args: Namespace) -> dict:
        self.acquired += 1
        self.acquire_wait_seconds.append(getattr(args, 'wait_seconds', 'absent'))
        return {**self.acquire_result, 'plan_id': args.plan_id}

    def run_release(self, args: Namespace) -> dict:
        self.released += 1
        if self.release_raises:
            raise OSError('simulated dequeue failure')
        return {**self.release_result, 'plan_id': args.plan_id}


_BLOCKED = {
    'status': 'blocked',
    'admission': 'blocked',
    'blocked_reason': 'lock_held_by_live_holder',
    'blocking_plan_id': _FOREIGN_PLAN_ID,
    'timed_out': True,
    'waited_seconds': 0,
}

_ERROR = {'status': 'error', 'error_code': 'NOT_FOUND', 'error': 'simulated queue read-modify-write failure'}


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def isolated_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    """Stage main + a worktree holding the plan dir (the move-in already ran).

    The DESTINATION resolves through the REAL ``resolve_main_anchored_path`` via
    ``PLAN_BASE_DIR`` at the staged main ``.plan/local``; the SOURCE worktree-path
    seam is stubbed to the staged worktree. cwd is pinned to main.
    """
    main = tmp_path / 'main'
    main_local = main / '.plan' / 'local'
    (main_local / 'plans').mkdir(parents=True)

    worktree_path = tmp_path / 'worktrees' / _PLAN_ID
    wt_plan_dir = worktree_path / '.plan' / 'local' / 'plans' / _PLAN_ID
    wt_plan_dir.mkdir(parents=True)
    (wt_plan_dir / 'status.json').write_text('{}\n')

    monkeypatch.chdir(main)
    monkeypatch.setenv('PLAN_BASE_DIR', str(main_local))
    monkeypatch.setattr(integrate_into_main, '_resolve_worktree_path_for_plan', lambda pid: (worktree_path, None))

    return {
        'main': main,
        'main_plan_dir': main_local / 'plans' / _PLAN_ID,
        'wt_plan_dir': wt_plan_dir,
    }


def _use_lock(monkeypatch: pytest.MonkeyPatch, lock: Any) -> Any:
    monkeypatch.setattr(integrate_into_main, '_load_merge_lock', lambda: lock)
    return lock


def _real_merge_lock_with_foreign_holder(env: dict, name: str) -> tuple[Any, Path]:
    """Load the real merge_lock and have a live foreign plan hold the lock.

    The foreign plan's dir exists on main, so it is neither reclaimed as stale nor
    pruned from the FIFO queue — it stays the front and the holder.
    """
    real_merge_lock = integrate_into_main._load_module_by_path(name, integrate_into_main._MERGE_LOCK_PATH)
    foreign_plan_dir = env['main'] / '.plan' / 'local' / 'plans' / _FOREIGN_PLAN_ID
    foreign_plan_dir.mkdir(parents=True)
    (foreign_plan_dir / 'status.json').write_text('{}\n')
    held = real_merge_lock.run_acquire(Namespace(plan_id=_FOREIGN_PLAN_ID, set_title_token=False))
    assert held['action'] == 'acquired', held
    return real_merge_lock, real_merge_lock._resolve_main_lock_path()


def _queued(real_merge_lock: Any) -> list[str]:
    return [entry['plan_id'] for entry in real_merge_lock._queue_waiting(real_merge_lock._read_store())]


# =============================================================================
# The bounded wait
# =============================================================================


class TestBoundedAdmissionWait:
    def test_acquire_forwards_the_bounded_wait(self, isolated_env: dict, monkeypatch: pytest.MonkeyPatch) -> None:
        lock = _use_lock(monkeypatch, _ScriptedMergeLock())

        integrate_into_main.run_integrate_into_main(Namespace(plan_id=_PLAN_ID))

        assert lock.acquire_wait_seconds == [integrate_into_main._MOVE_BACK_ACQUIRE_WAIT_SECONDS]

    def test_bound_sits_below_the_merge_lock_ceiling(self) -> None:
        real_merge_lock = integrate_into_main._load_module_by_path(
            'merge_lock_real_under_integrate_admission_ceiling', integrate_into_main._MERGE_LOCK_PATH
        )
        assert 0 < integrate_into_main._MOVE_BACK_ACQUIRE_WAIT_SECONDS <= real_merge_lock._ACQUIRE_WAIT_CEILING_SECONDS


# =============================================================================
# Dequeue on a refused acquire — real merge_lock
# =============================================================================


class TestRefusedAcquireDequeuesTheRealQueue:
    def test_foreign_holder_blocks_then_plan_is_dequeued(
        self, isolated_env: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A foreign live holder outlasts the bound: integrate surfaces ``blocked``
        with ``timed_out``, its own FIFO entry is gone, the foreign lock is
        untouched, and the plan dir never left the worktree."""
        env = isolated_env
        real_merge_lock, lock_path = _real_merge_lock_with_foreign_holder(env, 'merge_lock_real_admission_blocked')
        _use_lock(monkeypatch, real_merge_lock)
        monkeypatch.setattr(integrate_into_main, '_MOVE_BACK_ACQUIRE_WAIT_SECONDS', 0.05)

        result = integrate_into_main.run_integrate_into_main(Namespace(plan_id=_PLAN_ID))

        assert result['status'] == 'blocked', result
        assert result['timed_out'] is True, result
        assert result['blocking_plan_id'] == _FOREIGN_PLAN_ID, result
        assert result['dequeued'] is True, result
        queued = _queued(real_merge_lock)
        assert _PLAN_ID not in queued, queued
        assert _FOREIGN_PLAN_ID in queued, queued
        assert lock_path.read_text(encoding='utf-8').strip() == _FOREIGN_PLAN_ID
        assert (env['wt_plan_dir'] / 'status.json').is_file()
        assert not env['main_plan_dir'].exists()

    def test_error_after_an_earlier_enqueue_in_the_same_wait_is_dequeued(
        self, isolated_env: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Attempt 1 enqueues and is blocked; attempt 2's queue read-modify-write
        raises, so the acquire returns ``status: error``. The entry attempt 1 left is
        dequeued anyway, ``dequeued: true`` is reported, and the foreign lock stays."""
        env = isolated_env
        real_merge_lock, lock_path = _real_merge_lock_with_foreign_holder(env, 'merge_lock_real_admission_error')
        _use_lock(monkeypatch, real_merge_lock)
        # A long bound with a short pace guarantees a second attempt inside one wait.
        monkeypatch.setattr(integrate_into_main, '_MOVE_BACK_ACQUIRE_WAIT_SECONDS', 30.0)
        monkeypatch.setattr(real_merge_lock, '_DEFAULT_ACQUIRE_WAIT_INTERVAL_SECONDS', 0.01)

        real_enqueue = real_merge_lock._enqueue_fifo
        queued_when_attempt_2_failed: list[list[str]] = []

        def enqueue_then_fail(plan_id: str, ts: float) -> dict[str, Any]:
            if not queued_when_attempt_2_failed and plan_id in _queued(real_merge_lock):
                queued_when_attempt_2_failed.append(_queued(real_merge_lock))
                raise TimeoutError('simulated merge-queue guard timeout')
            enqueued: dict[str, Any] = real_enqueue(plan_id, ts)
            return enqueued

        monkeypatch.setattr(real_merge_lock, '_enqueue_fifo', enqueue_then_fail)

        result = integrate_into_main.run_integrate_into_main(Namespace(plan_id=_PLAN_ID))

        # Non-vacuity: the failing attempt really did follow an enqueue of this plan.
        assert queued_when_attempt_2_failed, 'attempt 2 never ran, so the error path was not exercised'
        assert _PLAN_ID in queued_when_attempt_2_failed[0]
        assert result['status'] == 'error', result
        assert result['dequeued'] is True, result
        queued = _queued(real_merge_lock)
        assert _PLAN_ID not in queued, queued
        assert _FOREIGN_PLAN_ID in queued, queued
        assert lock_path.read_text(encoding='utf-8').strip() == _FOREIGN_PLAN_ID
        assert (env['wt_plan_dir'] / 'status.json').is_file()
        assert not env['main_plan_dir'].exists()


# =============================================================================
# Dequeue on a refused acquire — the reported outcome
# =============================================================================


class TestRefusedAcquireReportsTheDequeue:
    @pytest.mark.parametrize('acquire_result', [_BLOCKED, _ERROR], ids=['blocked', 'error'])
    def test_successful_dequeue_is_reported(
        self, isolated_env: dict, monkeypatch: pytest.MonkeyPatch, acquire_result: dict
    ) -> None:
        lock = _use_lock(monkeypatch, _ScriptedMergeLock(acquire_result))

        result = integrate_into_main.run_integrate_into_main(Namespace(plan_id=_PLAN_ID))

        assert result['status'] == acquire_result['status'], result
        assert result['dequeued'] is True, result
        assert lock.released == 1
        assert (isolated_env['wt_plan_dir'] / 'status.json').is_file()

    @pytest.mark.parametrize('acquire_result', [_BLOCKED, _ERROR], ids=['blocked', 'error'])
    def test_dequeue_that_raises_is_reported_not_masked(
        self, isolated_env: dict, monkeypatch: pytest.MonkeyPatch, acquire_result: dict
    ) -> None:
        lock = _use_lock(monkeypatch, _ScriptedMergeLock(acquire_result, release_raises=True))

        result = integrate_into_main.run_integrate_into_main(Namespace(plan_id=_PLAN_ID))

        assert result['status'] == acquire_result['status'], result
        assert result['dequeued'] is False, result
        assert lock.released == 1

    @pytest.mark.parametrize('acquire_result', [_BLOCKED, _ERROR], ids=['blocked', 'error'])
    def test_dequeue_answering_non_success_is_reported_as_not_dequeued(
        self, isolated_env: dict, monkeypatch: pytest.MonkeyPatch, acquire_result: dict
    ) -> None:
        """A release that returns without raising but answers ``status: error`` did
        not prove the entry gone, so ``dequeued`` is false and the acquire payload —
        not the release's — is what is surfaced."""
        release_error = {'status': 'error', 'error': 'simulated dequeue refusal'}
        lock = _use_lock(monkeypatch, _ScriptedMergeLock(acquire_result, release_result=release_error))

        result = integrate_into_main.run_integrate_into_main(Namespace(plan_id=_PLAN_ID))

        assert result['status'] == acquire_result['status'], result
        assert result['dequeued'] is False, result
        assert result.get('error') == acquire_result.get('error'), result
        assert lock.released == 1

    def test_already_held_grant_is_never_dequeued(self, isolated_env: dict, monkeypatch: pytest.MonkeyPatch) -> None:
        """A reentrant ``already_held`` grant is a success: no dequeue, no release."""
        lock = _use_lock(monkeypatch, _ScriptedMergeLock({'status': 'success', 'action': 'already_held'}))

        result = integrate_into_main.run_integrate_into_main(Namespace(plan_id=_PLAN_ID))

        assert result['status'] == 'success', result
        assert 'dequeued' not in result
        assert lock.released == 0

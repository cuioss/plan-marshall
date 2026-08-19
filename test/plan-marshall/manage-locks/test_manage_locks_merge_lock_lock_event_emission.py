#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the unified ``manage-locks/merge_lock.py`` — the single main-anchored
merge-to-main serializer fronted by a FIFO admission queue.

Contract under test (lock-reconciliation-analysis.md §4 behavioural-equivalence
criteria + §5 massive-parallel-concurrency invariants (ii) + (iv); the FIFO
merge-queue admission layer + its canonical contract in manage-locks/SKILL.md;
ADR-002):

* **Atomic acquire** — ``acquire`` creates the lock file via ``O_EXCL`` and
  records the holder ``plan_id`` in the file contents.
* **FIFO admission (fairness)** — ``acquire`` first FIFO-enqueues ``--plan-id``
  into ``merge-queue.json``; ONLY the FIFO-front plan (the oldest entry by
  admit-``ts``) is admission-eligible. A non-front plan returns
  ``admission: blocked`` WITHOUT attempting the ``O_EXCL`` create — it never
  contends the kernel race — even when the lock file is FREE.
* **Idempotent re-poll position preservation** — a plan already in the queue
  KEEPS its FIFO position on re-poll; it is never re-appended to the back, so a
  plan polling repeatedly never loses priority to a later-arriving plan.
* **Release advances the front** — ``release`` dequeues ``--plan-id`` from
  ``merge-queue.json`` so the next FIFO entry becomes the front and is admitted
  on its next re-poll.
* **No double-grant** — exactly one of N concurrent ``acquire`` calls holds the
  lock; the rest return ``status: blocked``. Two plans never both hold the lock.
* **``blocked`` still escalates** — a blocked admission returns ``status: blocked``
  + ``blocking_plan_id`` (when a foreign live holder holds the lock) +
  ``waiting_count``, so the Pre-Merge Gate's poll/backoff loop and last-resort
  orchestrator escalation fire. ``blocked`` is NOT a hard error (no ``error_code``).
* **Stale reclamation** — a lock whose recorded holder has no live plan dir (on
  main OR in its worktree) is reclaimable (``reclaimed: true``) by the FIFO-front
  plan; a lock whose holder IS live is NOT reclaimable.
* **Idempotent release** — ``release`` removes the lock so the next acquire
  succeeds; release is idempotent (already-free / foreign-holder → no-op success,
  the foreign holder's lock left intact) and ALWAYS dequeues the FIFO entry.
* **``check`` holder read** — ``check`` returns ``{free}`` when no lock file
  exists and ``{held, holder_plan_id}`` when one does, without creating or
  mutating the lock, and never touching the FIFO queue.
* **Holder liveness via the shared core** — liveness is the imported
  :func:`_locks_core.holder_is_dead`, NOT a re-implemented copy; both main and
  worktree paths are consulted.
* **Main-anchored resolution (the single exception)** — both the lock AND the
  FIFO queue resolve to the MAIN checkout regardless of caller cwd, even when cwd
  is pinned to a worktree fixture.

Real-parallel obligations (§5 (ii) + (iv)): the no-double-grant invariant (ii) and
the dead-holder-reclaim-without-evicting-a-live-holder invariant (iv) are BOTH
asserted under REAL spawned-subprocess contention — N processes racing the SAME
main-anchored ``merge.lock`` + ``merge-queue.json`` via the CLI entry point — not
sequential calls. A sequential test can never exercise the kernel ``O_EXCL`` race
window (ii), the FIFO enqueue read-modify-write race, nor the interleave between
the stale-holder unlink and the atomic re-create (iv).

Isolation (test-isolation lessons): every test runs against an isolated
``PLAN_BASE_DIR`` staged under ``tmp_path`` so the suite never contends for the
real ``.plan/merge.lock`` / ``.plan/merge-queue.json`` under ``-n auto``. Under
``PLAN_BASE_DIR`` the lock resolves to ``<PLAN_BASE_DIR>/merge.lock``, the queue
to ``<PLAN_BASE_DIR>/merge-queue.json``, and holder plan dirs to
``<PLAN_BASE_DIR>/plans/{holder}``.

Filename note: this file is named ``test_manage_locks_merge_lock.py`` rather than
``test_merge_lock.py`` because pytest's default ``prepend`` import mode requires
unique test-module basenames across the suite.
"""


from __future__ import annotations

# The shared core owns the [LOCK]-log resolver and the best-effort emission
# swallow. ``merge_lock`` does ``from _locks_core import log_lock_event``, so the
# function closes over the _locks_core module that ``merge_lock`` imported — that
# SAME module instance is recovered from the function's ``__module__`` (NOT a
# fresh ``load_script_module`` copy, which would be a different instance whose
# patches ``merge_lock`` never sees).
from argparse import Namespace
from pathlib import Path

import pytest
from _manage_locks_merge_lock_fixtures import (
    _locks_core,
    _make_live_plan,
    _read_lock_log,
    _TokenRecorder,
    merge_lock,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def isolated_base(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    """Stage an isolated PLAN_BASE_DIR under tmp_path.

    Layout::

        tmp_path/main/.plan/local/                  (PLAN_BASE_DIR — main stand-in)
        tmp_path/main/.plan/local/plans/            (holder plan dirs resolve here)
        tmp_path/main/.plan/local/merge.lock        (the O_EXCL lock resolves here)
        tmp_path/main/.plan/local/merge-queue.json  (the FIFO queue resolves here)

    Sets PLAN_BASE_DIR to the main stand-in so the lock resolves to
    ``<base>/merge.lock``, the FIFO queue to ``<base>/merge-queue.json``, and
    ``holder_is_dead(holder)`` resolves the holder plan dir to
    ``<base>/plans/{holder}``.
    """
    base = tmp_path / 'main' / '.plan' / 'local'
    (base / 'plans').mkdir(parents=True)
    monkeypatch.setenv('PLAN_BASE_DIR', str(base))
    return {
        'base': base,
        'lock_path': base / 'merge.lock',
        'queue_path': base / 'merge-queue.json',
    }


@pytest.fixture(autouse=True)
def _stub_title_tokens(monkeypatch: pytest.MonkeyPatch) -> _TokenRecorder:
    """Autouse: stub the three best-effort title-token seams for EVERY test so the
    direct ``run_acquire`` / ``run_release`` unit tests never spawn the real
    executor subprocess (the token surface is best-effort and out-of-scope for the
    lock-correctness assertions). Tests that care about the token surface request
    this fixture by name and assert on the recorder.

    The CLI-subprocess concurrency tests run in a SEPARATE spawned process where
    this monkeypatch does not apply — there the real best-effort wrappers run and
    swallow any executor failure, exactly as in production.
    """
    recorder = _TokenRecorder()
    recorder.install(monkeypatch)
    return recorder


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

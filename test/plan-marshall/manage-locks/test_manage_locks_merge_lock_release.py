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

import json
import time
from argparse import Namespace
from pathlib import Path

import pytest
from _manage_locks_merge_lock_fixtures import _make_live_plan, _TokenRecorder, _waiting_plan_ids, merge_lock

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
# Release
# =============================================================================


class TestRelease:
    def test_release_removes_lock(self, isolated_base: dict) -> None:
        merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        assert isolated_base['lock_path'].is_file()

        result = merge_lock.run_release(Namespace(plan_id='plan-a'))
        assert result['status'] == 'success'
        assert result['action'] == 'released'
        assert not isolated_base['lock_path'].exists()

    def test_release_when_free_is_noop_success(self, isolated_base: dict) -> None:
        result = merge_lock.run_release(Namespace(plan_id='plan-a'))
        assert result['status'] == 'success'
        assert result['action'] == 'noop'

    def test_release_twice_is_idempotent_noop(self, isolated_base: dict) -> None:
        """A second release (after the lock is already freed) is a no-op success —
        a crashed-and-retried finalize must not error on the second release."""
        merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        first = merge_lock.run_release(Namespace(plan_id='plan-a'))
        assert first['action'] == 'released'

        second = merge_lock.run_release(Namespace(plan_id='plan-a'))
        assert second['status'] == 'success'
        assert second['action'] == 'noop'

    def test_release_foreign_holder_is_noop_and_leaves_lock_intact(self, isolated_base: dict) -> None:
        """A caller that is not the recorded holder must not remove the lock."""
        merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))

        result = merge_lock.run_release(Namespace(plan_id='plan-b'))
        assert result['status'] == 'success'
        assert result['action'] == 'noop'
        assert result['holder'] == 'plan-a'
        # The foreign holder's lock is left intact.
        assert isolated_base['lock_path'].is_file()
        assert isolated_base['lock_path'].read_text(encoding='utf-8').strip() == 'plan-a'

    def test_release_dequeues_even_when_caller_never_held_the_lock(self, isolated_base: dict) -> None:
        """A plan that gave up waiting (never held the lock) must STILL be dequeued
        from the FIFO queue on release — otherwise its stale entry would wedge the
        front. The foreign-holder release noop leaves the lock intact but removes
        the caller's own waiting entry so the front can advance."""
        base = isolated_base['base']
        for name in ('front', 'waiter'):
            _make_live_plan(base, name)
        merge_lock.run_acquire(Namespace(plan_id='front', timeout=5.0))
        merge_lock.run_acquire(Namespace(plan_id='waiter', timeout=5.0))
        assert _waiting_plan_ids(isolated_base['queue_path']) == ['front', 'waiter']

        # The waiter gives up: it releases though it never held the lock.
        rel = merge_lock.run_release(Namespace(plan_id='waiter'))
        assert rel['action'] == 'noop'
        # The front holder's lock is intact, but the waiter is gone from the queue.
        assert isolated_base['lock_path'].read_text(encoding='utf-8').strip() == 'front'
        assert _waiting_plan_ids(isolated_base['queue_path']) == ['front']


# =============================================================================
# check — non-blocking holder read (never touches the FIFO queue)
# =============================================================================


class TestCheck:
    def test_check_free_when_no_lock_file(self, isolated_base: dict) -> None:
        result = merge_lock.run_check(Namespace(plan_id='plan-a'))
        assert result['status'] == 'free'
        # check never creates the lock file.
        assert not isolated_base['lock_path'].exists()

    def test_check_held_reports_holder(self, isolated_base: dict) -> None:
        merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))

        result = merge_lock.run_check(Namespace(plan_id='plan-b'))
        assert result['status'] == 'held'
        assert result['holder_plan_id'] == 'plan-a'

    def test_check_reports_self_held(self, isolated_base: dict) -> None:
        """check reports the global lock state, including a self-held lock."""
        merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))

        result = merge_lock.run_check(Namespace(plan_id='plan-a'))
        assert result['status'] == 'held'
        assert result['holder_plan_id'] == 'plan-a'

    def test_check_does_not_mutate_lock(self, isolated_base: dict) -> None:
        merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        before = isolated_base['lock_path'].read_text(encoding='utf-8')

        merge_lock.run_check(Namespace(plan_id='plan-b'))

        after = isolated_base['lock_path'].read_text(encoding='utf-8')
        assert before == after

    def test_check_does_not_touch_the_fifo_queue(self, isolated_base: dict) -> None:
        """``check`` is a pure holder read — it never enqueues the querying plan or
        otherwise mutates ``merge-queue.json``."""
        # No acquire yet: check against a free lock must not create the queue.
        merge_lock.run_check(Namespace(plan_id='plan-a'))
        assert not isolated_base['queue_path'].exists()

        # With a held lock, check by a third plan must not enqueue that plan.
        merge_lock.run_acquire(Namespace(plan_id='holder', timeout=5.0))
        before = _waiting_plan_ids(isolated_base['queue_path'])
        merge_lock.run_check(Namespace(plan_id='observer'))
        assert _waiting_plan_ids(isolated_base['queue_path']) == before
        assert 'observer' not in _waiting_plan_ids(isolated_base['queue_path'])


# =============================================================================
# Stale reclamation (liveness via the shared _locks_core.holder_is_dead)
# =============================================================================


class TestStaleReclamation:
    def test_dead_holder_lock_is_reclaimed(self, isolated_base: dict) -> None:
        """A lock whose holder has no live plan dir is reclaimable by the front."""
        # plan-dead acquires but its plan dir is NEVER created → dead holder. It
        # is dequeued so the next acquirer becomes the FIFO front.
        merge_lock.run_acquire(Namespace(plan_id='plan-dead', timeout=5.0))
        merge_lock._dequeue_fifo('plan-dead')

        # plan-b acquires: it is the front, observes the held lock, finds the
        # holder dead, reclaims.
        result = merge_lock.run_acquire(Namespace(plan_id='plan-b', timeout=5.0))
        assert result['status'] == 'success'
        assert result['action'] == 'acquired'
        assert result['holder'] == 'plan-b'
        assert result['reclaimed'] is True
        assert isolated_base['lock_path'].read_text(encoding='utf-8').strip() == 'plan-b'

    def test_live_holder_lock_is_not_reclaimed(self, isolated_base: dict) -> None:
        """A lock whose holder IS live is NOT reclaimable (serializes/blocks)."""
        merge_lock.run_acquire(Namespace(plan_id='plan-live', timeout=5.0))
        _make_live_plan(isolated_base['base'], 'plan-live')

        result = merge_lock.run_acquire(Namespace(plan_id='plan-b', timeout=0.3))
        assert result['status'] == 'blocked'
        assert result['blocking_plan_id'] == 'plan-live'

    def test_liveness_uses_shared_core_predicate(self, isolated_base: dict) -> None:
        """Liveness is the imported shared-core predicate, exercised through the
        observable acquire behaviour. A ghost holder (no plan dir) is dead
        (reclaimable) once it is dequeued so the next plan is the front."""
        # A holder whose plan dir is missing is dead → reclaimable.
        merge_lock.run_acquire(Namespace(plan_id='ghost', timeout=5.0))
        merge_lock._dequeue_fifo('ghost')
        result = merge_lock.run_acquire(Namespace(plan_id='plan-b', timeout=5.0))
        assert result['action'] == 'acquired'
        assert result['reclaimed'] is True

    def test_dead_waiter_is_pruned_from_the_fifo_front(self, isolated_base: dict) -> None:
        """A crashed waiter whose plan dir is gone is pruned from the FIFO queue so
        its stale entry never wedges the front. A live plan behind a dead front
        entry is promoted to the front and admitted."""
        base = isolated_base['base']
        # 'crashed' is enqueued at the front but has NO plan dir → dead waiter.
        # 'live' is enqueued behind it and IS live.
        _make_live_plan(base, 'live')
        isolated_base['queue_path'].write_text(
            json.dumps({'waiting': [
                {'plan_id': 'crashed', 'ts': 1.0},
                {'plan_id': 'live', 'ts': 2.0},
            ]}),
            encoding='utf-8',
        )

        # 'live' polls: the dead 'crashed' front entry is pruned, promoting 'live'
        # to the front → admitted.
        result = merge_lock.run_acquire(Namespace(plan_id='live', timeout=5.0))
        assert result['admission'] == 'admitted'
        assert result['holder'] == 'live'
        # The dead waiter is gone from the queue.
        assert 'crashed' not in _waiting_plan_ids(isolated_base['queue_path'])

    def test_worktree_resident_holder_is_not_reclaimed(self, isolated_base: dict) -> None:
        """A holder whose plan dir has been MOVED into its worktree (executing or
        mid-finalize, absent on the main checkout) is LIVE and MUST NOT be
        reclaimed. Checking only the main checkout would steal the lock from an
        actively-finalizing session and break serialization."""
        base = isolated_base['base']
        # plan-wt holds the lock and its plan dir lives ONLY in the worktree.
        merge_lock.run_acquire(Namespace(plan_id='plan-wt', timeout=5.0))
        (base / 'worktrees' / 'plan-wt' / '.plan' / 'local' / 'plans' / 'plan-wt').mkdir(parents=True)
        # A concurrent acquirer must serialize (block), NOT reclaim.
        result = merge_lock.run_acquire(Namespace(plan_id='plan-b', timeout=0.3))
        assert result['status'] == 'blocked'
        assert result['blocking_plan_id'] == 'plan-wt'

    def test_timeout_zero_is_non_blocking(self, isolated_base: dict) -> None:
        """``--timeout 0`` is a valid non-blocking try: against a live holder it
        blocks IMMEDIATELY (acquire never waits internally for the queue case)."""
        merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        _make_live_plan(isolated_base['base'], 'plan-a')
        start = time.monotonic()
        result = merge_lock.run_acquire(Namespace(plan_id='plan-b', timeout=0))
        elapsed = time.monotonic() - start
        assert result['status'] == 'blocked'
        assert result['blocking_plan_id'] == 'plan-a'
        # Non-blocking: returns essentially instantly (no internal wait loop).
        assert elapsed < 5.0

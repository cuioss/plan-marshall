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

import time
from argparse import Namespace
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from _manage_locks_merge_lock_fixtures import (
    SCRIPT_PATH,
    _make_live_plan,
    _TokenRecorder,
    _waiting_plan_ids,
    merge_lock,
)
from toon_parser import parse_toon

from conftest import run_script

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
# No double-merge — concurrent serialization (one wins, the others block)
# =============================================================================


class TestNoDoubleMerge:
    def test_second_acquire_against_live_holder_blocks(self, isolated_base: dict) -> None:
        """A live holder blocks the second acquire — it serializes and returns the
        structured ``blocked`` payload (NOT a hard error), distinct from the
        former TIMEOUT error outcome."""
        # plan-a acquires and is live (its plan dir exists).
        merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        _make_live_plan(isolated_base['base'], 'plan-a')

        # plan-b cannot acquire while plan-a holds it → blocked.
        result = merge_lock.run_acquire(Namespace(plan_id='plan-b', timeout=0.3))
        assert result['status'] == 'blocked'
        assert result['blocking_plan_id'] == 'plan-a'
        # blocked is NOT a hard error — no error_code is set.
        assert result.get('error_code') is None

    def test_acquire_succeeds_after_holder_releases(self, isolated_base: dict) -> None:
        """After the holder releases, the next acquire wins (serialized handoff)."""
        merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        _make_live_plan(isolated_base['base'], 'plan-a')

        rel = merge_lock.run_release(Namespace(plan_id='plan-a'))
        assert rel['status'] == 'success'
        assert rel['action'] == 'released'

        result = merge_lock.run_acquire(Namespace(plan_id='plan-b', timeout=5.0))
        assert result['status'] == 'success'
        assert result['action'] == 'acquired'
        assert result['holder'] == 'plan-b'

    @pytest.mark.xdist_group(name="manage_locks_contention")
    def test_concurrent_acquire_admits_exactly_one_under_real_contention(
        self, isolated_base: dict
    ) -> None:
        """§5 (ii): N spawned subprocesses race the SAME main-anchored merge.lock +
        merge-queue.json via the CLI entry point. EXACTLY ONE returns
        ``status: success/acquired``; every other returns ``status: blocked``. Two
        plans never both hold the lock — under the FIFO layer only the front plan
        is admission-eligible AND the kernel O_EXCL race is the final k=1 arbiter,
        so the no-double-merge property holds. This is the make-or-break property
        and MUST run under genuine process-level contention, not sequential calls.

        Runs under ``PLAN_BASE_DIR`` isolation (no contention for the real
        ``.plan/merge.lock``) and is stable under ``pytest-xdist`` ``-n auto`` with
        widened load-sensitive margins (``--timeout 30`` legacy compat flag,
        ``timeout=90`` outer subprocess kill budget) — matching the hardened
        sibling reclamation races."""
        base = isolated_base['base']
        n = 8
        # Each contender's plan dir is live, so a held lock is NEVER reclaimed —
        # FIFO admission + the kernel O_EXCL race are the sole arbiters.
        for i in range(n):
            _make_live_plan(base, f'race-{i}')

        env_overrides = {'PLAN_BASE_DIR': str(base)}

        def _acquire(i: int):
            return run_script(
                SCRIPT_PATH,
                'acquire',
                '--plan-id',
                f'race-{i}',
                '--timeout',
                '30',
                env_overrides=env_overrides,
                timeout=90,
            )

        with ThreadPoolExecutor(max_workers=n) as pool:
            results = list(pool.map(_acquire, range(n)))

        # The script emits TOON, not JSON — parse with the TOON parser.
        parsed = [parse_toon(r.stdout) for r in results]
        winners = [p for p in parsed if p.get('status') == 'success']
        blocked = [p for p in parsed if p.get('status') == 'blocked']

        # Exactly one winner; the rest blocked — never two holders.
        assert len(winners) == 1, parsed
        assert len(blocked) == n - 1, parsed
        # The single winner's plan_id is what the lock file records.
        assert isolated_base['lock_path'].read_text(encoding='utf-8').strip() == winners[0]['holder']
        # Every blocked result's queue depth reflects all N contenders enqueued.
        for p in blocked:
            assert p['waiting_count'] >= 1, p

    @pytest.mark.xdist_group(name="manage_locks_contention")
    def test_concurrent_then_drained_serves_every_plan_exactly_once(
        self, isolated_base: dict
    ) -> None:
        """N contenders race once (one admitted, the rest blocked into the FIFO
        queue), then the queue is drained in-process: each release advances the
        next front, and every one of the N plans is admitted exactly once with no
        plan served twice and none lost. This pins the no-double-grant + no-lost
        FIFO entry property end-to-end across the contention + drain lifecycle."""
        base = isolated_base['base']
        n = 6
        for i in range(n):
            _make_live_plan(base, f'p-{i}')

        env_overrides = {'PLAN_BASE_DIR': str(base)}

        def _acquire(i: int):
            return run_script(
                SCRIPT_PATH, 'acquire', '--plan-id', f'p-{i}', '--timeout', '30',
                env_overrides=env_overrides, timeout=90,
            )

        with ThreadPoolExecutor(max_workers=n) as pool:
            results = list(pool.map(_acquire, range(n)))
        parsed = [parse_toon(r.stdout) for r in results]
        winners = [p for p in parsed if p.get('status') == 'success']
        assert len(winners) == 1, parsed

        # Every contender enqueued exactly once — the FIFO queue holds all N.
        queued = _waiting_plan_ids(isolated_base['queue_path'])
        assert sorted(queued) == sorted(f'p-{i}' for i in range(n)), queued
        assert len(queued) == n

        # Drain the queue: release the current front, then the next front polls and
        # is admitted, until every plan has been served. Collect the serving order.
        served: list[str] = [winners[0]['holder']]
        current = winners[0]['holder']
        for _ in range(n - 1):
            merge_lock.run_release(Namespace(plan_id=current))
            front = _waiting_plan_ids(isolated_base['queue_path'])[0]
            admitted = merge_lock.run_acquire(Namespace(plan_id=front, timeout=5.0))
            assert admitted['admission'] == 'admitted', admitted
            served.append(front)
            current = front

        # Every plan served exactly once — no double-grant, no lost entry.
        assert sorted(served) == sorted(f'p-{i}' for i in range(n)), served
        assert len(set(served)) == n
        # The serving order is the FIFO arrival order recorded in the queue.
        assert served == queued, (served, queued)


# =============================================================================
# Reentrant per plan-id — a same-plan-id re-acquire is granted without blocking
# =============================================================================


class TestReentrantAcquire:
    """The self-holder short-circuit: when the lock is already held by the SAME
    ``plan_id``, a re-acquire returns ``status: success`` with ``action:
    already_held`` IMMEDIATELY — no second ``O_EXCL`` create, no staleness
    evaluation, no FIFO churn. This is the fix for the finalize auto-merge
    self-deadlock (``branch-cleanup`` holds the lock, then ``integrate_into_main``
    re-acquires it under the same ``plan_id``). The reentrant grant is NOT an
    independent second acquisition: release stays idempotent and holder-scoped, so
    the single real ``os.unlink`` fires once when the holder releases."""

    def test_same_plan_id_reacquire_is_already_held_success(self, isolated_base: dict) -> None:
        """A re-acquire for the SAME plan-id (already the live holder) returns a
        success with ``action: already_held`` rather than blocking or reclaiming."""
        # plan-a acquires the lock and is live (its plan dir exists), so the
        # holder is NOT dead.
        merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        _make_live_plan(isolated_base['base'], 'plan-a')

        # The same plan-a re-acquires — granted reentrantly, not blocked.
        result = merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        assert result['status'] == 'success'
        assert result['action'] == 'already_held'
        assert result['admission'] == 'admitted'
        assert result['holder'] == 'plan-a'
        # A reentrant grant is not a fresh acquire and not a reclaim.
        assert result['reclaimed'] is False
        # The lock file is unchanged — still recording plan-a, never re-created.
        assert isolated_base['lock_path'].read_text(encoding='utf-8').strip() == 'plan-a'

    def test_reentrant_reacquire_does_not_block(self, isolated_base: dict) -> None:
        """The self-holder short-circuit returns IMMEDIATELY — even a ``timeout: 0``
        re-acquire (which would block instantly against a FOREIGN holder) succeeds
        for the same plan-id, proving it short-circuited before the FIFO layer."""
        merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        _make_live_plan(isolated_base['base'], 'plan-a')

        start = time.monotonic()
        # timeout=0 is the non-blocking try: a foreign holder would `blocked`
        # immediately; a self-holder must short-circuit to success.
        result = merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=0))
        elapsed = time.monotonic() - start
        assert result['status'] == 'success'
        assert result['action'] == 'already_held'
        # The reentrant grant returns essentially instantly — far under any budget.
        assert elapsed < 1.0

    def test_reentrant_grant_does_not_enqueue_into_fifo(self, isolated_base: dict) -> None:
        """The reentrant short-circuit fires BEFORE the FIFO enqueue — a self-holder
        re-acquire must not churn the queue with a duplicate entry. The acquiring
        plan keeps its single FIFO entry from the first acquire, unchanged."""
        merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        _make_live_plan(isolated_base['base'], 'plan-a')
        before = _waiting_plan_ids(isolated_base['queue_path'])

        result = merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        assert result['action'] == 'already_held'
        # The reentrant grant reports waiting_count 0 (it did not touch the queue)
        # and leaves the persisted FIFO state exactly as the first acquire left it.
        assert result['waiting_count'] == 0
        assert _waiting_plan_ids(isolated_base['queue_path']) == before

    def test_reentrant_reacquire_then_single_release_frees_lock(self, isolated_base: dict) -> None:
        """The reentrant grant must NOT be an independent second acquisition: after a
        self-holder re-acquire, ONE release removes the single underlying lock file
        (release is idempotent and holder-scoped — the single ``os.unlink`` fires
        once), and the next acquire by a different plan succeeds."""
        merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        _make_live_plan(isolated_base['base'], 'plan-a')

        # Reentrant re-acquire by the same holder — no second lock file created.
        reentrant = merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        assert reentrant['action'] == 'already_held'

        # A single release frees the one underlying lock file.
        rel = merge_lock.run_release(Namespace(plan_id='plan-a'))
        assert rel['status'] == 'success'
        assert rel['action'] == 'released'
        assert not isolated_base['lock_path'].exists()

        # The lock is now genuinely free — a different plan can acquire it.
        other = merge_lock.run_acquire(Namespace(plan_id='plan-b', timeout=5.0))
        assert other['status'] == 'success'
        assert other['action'] == 'acquired'
        assert other['holder'] == 'plan-b'

    def test_foreign_live_holder_still_blocks(self, isolated_base: dict) -> None:
        """Cross-plan mutual exclusion is preserved: a FOREIGN live holder still
        blocks. The reentrant short-circuit only fires for the SAME plan-id. plan-b
        acquiring against a live plan-a holder still returns ``blocked``."""
        merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        _make_live_plan(isolated_base['base'], 'plan-a')

        result = merge_lock.run_acquire(Namespace(plan_id='plan-b', timeout=0.3))
        assert result['status'] == 'blocked'
        assert result['blocking_plan_id'] == 'plan-a'
        # The lock still records the live foreign holder, never reentrantly granted.
        assert isolated_base['lock_path'].read_text(encoding='utf-8').strip() == 'plan-a'

    def test_reentrant_grant_does_not_surface_lock_owned_token(
        self, isolated_base: dict, _stub_title_tokens: _TokenRecorder
    ) -> None:
        """The reentrant ``already_held`` short-circuit returns before any title-token
        surface — the lock-owned 🔒 glyph was already set on the FIRST acquire, so the
        re-acquire surfaces no NEW token (it neither re-creates the lock nor blocks)."""
        merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        _make_live_plan(isolated_base['base'], 'plan-a')
        _stub_title_tokens.set_states.clear()
        _stub_title_tokens.pushed_icons.clear()

        result = merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        assert result['action'] == 'already_held'
        # No new token of any kind — neither lock-owned (no re-create) nor
        # lock-waiting (not blocked).
        assert _stub_title_tokens.set_states == []
        assert _stub_title_tokens.pushed_icons == []

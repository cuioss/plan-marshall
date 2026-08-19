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
# Live-worktree guard (D3) — refuse auto-reclaim of a mid-recovery holder
# =============================================================================
#
# A holder judged dead-by-plan-dir-absence (its plan dir is in NEITHER main NOR
# its worktree's .plan) may still be MID-RECOVERY — its worktree DIRECTORY is on
# disk (an interrupted finalize move-back moved the plan dir out but left the
# worktree). The acquire path evaluates the `holder_has_live_worktree` guard
# BEFORE the auto-reclaim branch and REFUSES to reclaim such a holder, returning
# a `blocked` payload carrying `stale_holder_live_worktree: true` so the existing
# branch-cleanup budget-exhaustion escalation asks the operator to confirm rather
# than the primitive force-releasing a mid-recovery holder. No new grant path is
# opened — the reclaim is refused, not attempted.


class TestLiveWorktreeGuard:
    def test_plan_dir_dead_but_live_worktree_holder_is_not_reclaimed(self, isolated_base: dict) -> None:
        """A plan-dir-dead holder whose worktree DIRECTORY is still on disk is
        NOT auto-reclaimed: acquire returns `blocked` with the
        `stale_holder_live_worktree` discriminator and leaves the lock intact."""
        base = isolated_base['base']
        # 'mid-recovery' holds the lock. Its plan dir exists in NEITHER main NOR
        # its worktree's .plan (holder_is_dead True), but its worktree carries a
        # genuine git-worktree marker (an interrupted move-back left the git
        # plumbing intact) → holder_has_live_worktree True.
        merge_lock.run_acquire(Namespace(plan_id='mid-recovery', timeout=5.0))
        # Drop it from the FIFO queue so 'plan-b' becomes the genuine front and
        # reaches the holder-inspection / guard code below.
        merge_lock._dequeue_fifo('mid-recovery')
        worktree = base / 'worktrees' / 'mid-recovery'
        worktree.mkdir(parents=True, exist_ok=True)
        (worktree / '.git').write_text(
            'gitdir: /main/.git/worktrees/mid-recovery\n', encoding='utf-8'
        )

        result = merge_lock.run_acquire(Namespace(plan_id='plan-b', timeout=5.0))

        assert result['status'] == 'blocked'
        assert result['admission'] == 'blocked'
        assert result['stale_holder_live_worktree'] is True
        assert result['blocking_plan_id'] == 'mid-recovery'
        # The lock file was NOT reclaimed/recreated — it still records the
        # original mid-recovery holder (no new grant path opened).
        assert isolated_base['lock_path'].read_text(encoding='utf-8').strip() == 'mid-recovery'

    def test_plan_dir_dead_and_worktree_absent_still_reclaims(self, isolated_base: dict) -> None:
        """Guard boundary: a GENUINELY-dead holder (plan dir AND worktree both
        absent) is still reclaimed exactly as before — the guard does not block
        the ordinary reclaim path, and the discriminator is absent."""
        merge_lock.run_acquire(Namespace(plan_id='fully-dead', timeout=5.0))
        merge_lock._dequeue_fifo('fully-dead')
        # No worktree directory for 'fully-dead' → holder_has_live_worktree False.

        result = merge_lock.run_acquire(Namespace(plan_id='plan-b', timeout=5.0))

        assert result['status'] == 'success'
        assert result['action'] == 'acquired'
        assert result['reclaimed'] is True
        assert 'stale_holder_live_worktree' not in result
        assert isolated_base['lock_path'].read_text(encoding='utf-8').strip() == 'plan-b'

    def test_ordinary_foreign_live_holder_block_omits_discriminator(self, isolated_base: dict) -> None:
        """A normal foreign-live-holder block (the holder's plan dir exists) must
        NOT carry the guard discriminator — the field is present ONLY on the
        refuse-auto-reclaim path."""
        merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        _make_live_plan(isolated_base['base'], 'plan-a')

        result = merge_lock.run_acquire(Namespace(plan_id='plan-b', timeout=0.3))

        assert result['status'] == 'blocked'
        assert result['blocking_plan_id'] == 'plan-a'
        assert 'stale_holder_live_worktree' not in result

    def test_prune_retains_live_worktree_waiter(self, isolated_base: dict) -> None:
        """`_prune_dead_waiting` retains a dead-by-plan-dir waiter whose worktree
        directory is still on disk (mid-recovery), while still dropping a waiter
        that is both plan-dir-dead AND worktree-absent."""
        base = isolated_base['base']
        _make_live_plan(base, 'live')  # alive by plan dir
        # 'mid-recovery' is plan-dir-dead but carries a genuine git-worktree marker
        # → a real mid-recovery worktree that must be retained.
        _mid_recovery = base / 'worktrees' / 'mid-recovery'
        _mid_recovery.mkdir(parents=True, exist_ok=True)
        (_mid_recovery / '.git').write_text(
            'gitdir: /main/.git/worktrees/mid-recovery\n', encoding='utf-8'
        )

        waiting = [
            {'plan_id': 'live', 'ts': 1.0},
            {'plan_id': 'mid-recovery', 'ts': 2.0},
            {'plan_id': 'fully-dead', 'ts': 3.0},
        ]

        pruned_ids = [e['plan_id'] for e in merge_lock._prune_dead_waiting(waiting)]

        assert 'live' in pruned_ids
        # Retained despite being plan-dir-dead — its worktree is still present.
        assert 'mid-recovery' in pruned_ids
        # Genuinely gone (plan dir AND worktree absent) → pruned.
        assert 'fully-dead' not in pruned_ids

    def test_live_worktree_waiter_not_pruned_from_fifo_front(self, isolated_base: dict) -> None:
        """End-to-end: a mid-recovery waiter (plan-dir-dead, live worktree) at the
        FIFO front is NOT pruned during an acquire, so a later live waiter behind
        it does not jump the queue."""
        base = isolated_base['base']
        # 'mid-recovery' is plan-dir-dead but carries a genuine git-worktree marker
        # (real mid-recovery worktree) → retained at the FIFO front.
        _mid_recovery = base / 'worktrees' / 'mid-recovery'
        _mid_recovery.mkdir(parents=True, exist_ok=True)
        (_mid_recovery / '.git').write_text(
            'gitdir: /main/.git/worktrees/mid-recovery\n', encoding='utf-8'
        )
        _make_live_plan(base, 'behind')
        isolated_base['queue_path'].write_text(
            json.dumps({'waiting': [
                {'plan_id': 'mid-recovery', 'ts': 1.0},
                {'plan_id': 'behind', 'ts': 2.0},
            ]}),
            encoding='utf-8',
        )

        # 'behind' polls: the mid-recovery front is RETAINED (live worktree), so
        # 'behind' stays non-front → blocked, and the front is unchanged.
        result = merge_lock.run_acquire(Namespace(plan_id='behind', timeout=5.0))
        assert result['admission'] == 'blocked'
        assert _waiting_plan_ids(isolated_base['queue_path']) == ['mid-recovery', 'behind']

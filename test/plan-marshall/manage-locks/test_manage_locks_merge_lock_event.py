#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the unified ``manage-locks/merge_lock.py`` — the single main-anchored
merge-to-main serializer fronted by a FIFO admission queue.
"""


from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

import pytest
from _manage_locks_merge_lock_fixtures import (
    _locks_core,
    _make_live_plan,
    _read_lock_log,
    _TokenRecorder,
    _waiting_plan_ids,
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

#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2

"""Tests for the unified ``manage-locks/merge_lock.py`` — the single main-anchored
merge-to-main serializer fronted by a FIFO admission queue.

Its sections, in order:

* Fixtures
* Live-worktree guard (D3) — refuse auto-reclaim of a mid-recovery holder
* CLI argparse plumbing
* Bounded waiting acquire (--wait-seconds) — pacing between whole attempts
"""

from __future__ import annotations

import json
from argparse import Namespace

import pytest
from _manage_locks_merge_lock_fixtures import (
    SCRIPT_PATH,
    _make_live_plan,
    _stub_title_tokens,
    _TokenRecorder,
    _waiting_plan_ids,
    isolated_base,
    merge_lock,
)
from toon_parser import parse_toon

from conftest import run_script

# =============================================================================
# Fixtures
# =============================================================================


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
        merge_lock.run_acquire(Namespace(plan_id='mid-recovery'))
        # Drop it from the FIFO queue so 'plan-b' becomes the genuine front and
        # reaches the holder-inspection / guard code below.
        merge_lock._dequeue_fifo('mid-recovery')
        worktree = base / 'worktrees' / 'mid-recovery'
        worktree.mkdir(parents=True, exist_ok=True)
        (worktree / '.git').write_text('gitdir: /main/.git/worktrees/mid-recovery\n', encoding='utf-8')

        result = merge_lock.run_acquire(Namespace(plan_id='plan-b'))

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
        merge_lock.run_acquire(Namespace(plan_id='fully-dead'))
        merge_lock._dequeue_fifo('fully-dead')
        # No worktree directory for 'fully-dead' → holder_has_live_worktree False.

        result = merge_lock.run_acquire(Namespace(plan_id='plan-b'))

        assert result['status'] == 'success'
        assert result['action'] == 'acquired'
        assert result['reclaimed'] is True
        assert 'stale_holder_live_worktree' not in result
        assert isolated_base['lock_path'].read_text(encoding='utf-8').strip() == 'plan-b'

    def test_ordinary_foreign_live_holder_block_omits_discriminator(self, isolated_base: dict) -> None:
        """A normal foreign-live-holder block (the holder's plan dir exists) must
        NOT carry the guard discriminator — the field is present ONLY on the
        refuse-auto-reclaim path."""
        merge_lock.run_acquire(Namespace(plan_id='plan-a'))
        _make_live_plan(isolated_base['base'], 'plan-a')

        result = merge_lock.run_acquire(Namespace(plan_id='plan-b'))

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
        (_mid_recovery / '.git').write_text('gitdir: /main/.git/worktrees/mid-recovery\n', encoding='utf-8')

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
        (_mid_recovery / '.git').write_text('gitdir: /main/.git/worktrees/mid-recovery\n', encoding='utf-8')
        _make_live_plan(base, 'behind')
        isolated_base['queue_path'].write_text(
            json.dumps(
                {
                    'waiting': [
                        {'plan_id': 'mid-recovery', 'ts': 1.0},
                        {'plan_id': 'behind', 'ts': 2.0},
                    ]
                }
            ),
            encoding='utf-8',
        )

        # 'behind' polls: the mid-recovery front is RETAINED (live worktree), so
        # 'behind' stays non-front → blocked, and the front is unchanged.
        result = merge_lock.run_acquire(Namespace(plan_id='behind'))
        assert result['admission'] == 'blocked'
        assert _waiting_plan_ids(isolated_base['queue_path']) == ['mid-recovery', 'behind']


# =============================================================================
# CLI argparse plumbing
# =============================================================================


class TestCli:
    def test_acquire_requires_plan_id(self) -> None:
        result = run_script(SCRIPT_PATH, 'acquire')
        assert result.returncode != 0
        assert '--plan-id' in result.stderr or '--plan-id' in result.stdout

    def test_check_requires_plan_id(self) -> None:
        result = run_script(SCRIPT_PATH, 'check')
        assert result.returncode != 0
        assert '--plan-id' in result.stderr or '--plan-id' in result.stdout

    def test_release_requires_plan_id(self) -> None:
        result = run_script(SCRIPT_PATH, 'release')
        assert result.returncode != 0
        assert '--plan-id' in result.stderr or '--plan-id' in result.stdout

    def test_acquire_accepts_no_title_token_flag(self, isolated_base: dict) -> None:
        """The ``--no-title-token`` flag is a valid acquire argument (it maps to
        ``set_title_token=False``) — argparse accepts it and the acquire succeeds."""
        env_overrides = {'PLAN_BASE_DIR': str(isolated_base['base'])}
        result = run_script(
            SCRIPT_PATH,
            'acquire',
            '--plan-id',
            'plan-a',
            '--no-title-token',
            env_overrides=env_overrides,
        )
        assert result.returncode == 0, result.stderr
        parsed = parse_toon(result.stdout)
        assert parsed['status'] == 'success'
        assert parsed['action'] == 'acquired'

    def test_release_accepts_no_title_token_flag(self, isolated_base: dict) -> None:
        """The ``--no-title-token`` flag is a valid release argument matching a
        ``--no-title-token`` acquire — argparse accepts it and the release succeeds."""
        env_overrides = {'PLAN_BASE_DIR': str(isolated_base['base'])}
        run_script(
            SCRIPT_PATH,
            'acquire',
            '--plan-id',
            'plan-a',
            '--no-title-token',
            env_overrides=env_overrides,
        )
        result = run_script(
            SCRIPT_PATH,
            'release',
            '--plan-id',
            'plan-a',
            '--no-title-token',
            env_overrides=env_overrides,
        )
        assert result.returncode == 0, result.stderr
        parsed = parse_toon(result.stdout)
        assert parsed['status'] == 'success'
        assert parsed['action'] == 'released'

    def test_acquire_rejects_removed_timeout_flag(self, isolated_base: dict) -> None:
        """The legacy ``--timeout`` flag is removed: argparse rejects it (exit 2)
        before the handler runs, so neither the lock nor the FIFO queue is touched."""
        env_overrides = {'PLAN_BASE_DIR': str(isolated_base['base'])}

        result = run_script(
            SCRIPT_PATH,
            'acquire',
            '--plan-id',
            'plan-a',
            '--timeout',
            '0',
            env_overrides=env_overrides,
        )

        assert result.returncode == 2, result.stdout
        assert '--timeout' in result.stderr
        assert not isolated_base['lock_path'].exists()
        assert not isolated_base['queue_path'].exists()

    def test_acquire_help_documents_wait_seconds_and_no_timeout(self) -> None:
        """``acquire --help`` documents the bounded wait and makes no claim that
        acquire never waits; the removed ``--timeout`` flag is absent."""
        result = run_script(SCRIPT_PATH, 'acquire', '--help')

        assert result.returncode == 0, result.stderr
        help_text = ' '.join(result.stdout.split()).lower()
        assert '--wait-seconds' in help_text
        assert '--interval-seconds' in help_text
        assert '--timeout' not in help_text
        assert 'no longer wait' not in help_text

    def test_acquire_default_is_a_single_attempt_reporting_no_wait(self, isolated_base: dict) -> None:
        """Without ``--wait-seconds`` the CLI makes one attempt and reports that it
        waited for nothing."""
        env_overrides = {'PLAN_BASE_DIR': str(isolated_base['base'])}

        result = run_script(SCRIPT_PATH, 'acquire', '--plan-id', 'plan-a', env_overrides=env_overrides)

        assert result.returncode == 0, result.stderr
        parsed = parse_toon(result.stdout)
        assert parsed['admission'] == 'admitted'
        assert parsed['waited_seconds'] == 0
        assert parsed['timed_out'] is False

    def test_acquire_rejects_negative_wait_seconds_at_the_cli(self, isolated_base: dict) -> None:
        """An invalid ``--wait-seconds`` reaches the handler and is refused there
        before the store is touched."""
        env_overrides = {'PLAN_BASE_DIR': str(isolated_base['base'])}

        result = run_script(
            SCRIPT_PATH, 'acquire', '--plan-id', 'plan-a', '--wait-seconds', '-1', env_overrides=env_overrides
        )

        parsed = parse_toon(result.stdout)
        assert parsed['status'] == 'error'
        assert not isolated_base['lock_path'].exists()
        assert not isolated_base['queue_path'].exists()


# =============================================================================
# Bounded waiting acquire (--wait-seconds) — pacing between whole attempts
# =============================================================================


class _FakeClock:
    """A monotonic clock that only moves when the injected ``sleep`` is called.

    ``on_sleep`` runs on every pause, AFTER the clock advanced — the seam a test
    uses to change the world between two attempts (release the holder), exactly
    where a real concurrent session would.
    """

    def __init__(self, on_sleep=None) -> None:
        self.now = 1000.0
        self.sleeps: list[float] = []
        self._on_sleep = on_sleep

    def clock(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds
        if self._on_sleep is not None:
            self._on_sleep(len(self.sleeps))


def _hold_live_lock(isolated_base: dict, holder: str) -> None:
    """Make ``holder`` the live lock holder and drop it from the FIFO queue, so the
    next acquirer is the front and meets a live foreign holder."""
    merge_lock.run_acquire(Namespace(plan_id=holder))
    _make_live_plan(isolated_base['base'], holder)
    merge_lock._dequeue_fifo(holder)


class TestWaitingAcquire:
    def test_admitted_as_soon_as_the_front_holder_releases_during_the_wait(self, isolated_base: dict) -> None:
        _hold_live_lock(isolated_base, 'plan-a')
        fake = _FakeClock(on_sleep=lambda _count: merge_lock.run_release(Namespace(plan_id='plan-a')))

        result = merge_lock.run_acquire(
            Namespace(plan_id='plan-b', wait_seconds=60.0, interval_seconds=5.0),
            sleep=fake.sleep,
            clock=fake.clock,
        )

        assert result['status'] == 'success'
        assert result['admission'] == 'admitted'
        assert result['action'] == 'acquired'
        assert result['timed_out'] is False
        assert result['waited_seconds'] == 5
        # One pause between the blocked attempt and the admitted one — no more.
        assert fake.sleeps == [5.0]
        assert isolated_base['lock_path'].read_text(encoding='utf-8').strip() == 'plan-b'

    def test_bound_lapse_returns_the_blocked_discriminator_with_waited_seconds(self, isolated_base: dict) -> None:
        _hold_live_lock(isolated_base, 'plan-a')
        fake = _FakeClock()

        result = merge_lock.run_acquire(
            Namespace(plan_id='plan-b', wait_seconds=12.0, interval_seconds=5.0),
            sleep=fake.sleep,
            clock=fake.clock,
        )

        assert result['status'] == 'blocked'
        assert result['admission'] == 'blocked'
        assert result['blocked_reason'] == merge_lock.BLOCKED_LOCK_HELD_BY_LIVE_HOLDER
        assert result['blocking_plan_id'] == 'plan-a'
        assert result['timed_out'] is True
        assert result['waited_seconds'] == 12
        # The last pause is cut to the remaining bound, so the call ends on the bound.
        assert fake.sleeps == [5.0, 5.0, 2.0]
        assert isolated_base['lock_path'].read_text(encoding='utf-8').strip() == 'plan-a'

    def test_wait_is_clamped_to_the_per_call_ceiling(self, isolated_base: dict) -> None:
        _hold_live_lock(isolated_base, 'plan-a')
        fake = _FakeClock()

        result = merge_lock.run_acquire(
            Namespace(plan_id='plan-b', wait_seconds=100_000.0, interval_seconds=60.0),
            sleep=fake.sleep,
            clock=fake.clock,
        )

        assert result['timed_out'] is True
        assert result['waited_seconds'] == int(merge_lock._ACQUIRE_WAIT_CEILING_SECONDS)
        assert sum(fake.sleeps) == merge_lock._ACQUIRE_WAIT_CEILING_SECONDS

    def test_reentrant_acquire_with_wait_returns_already_held_without_waiting(self, isolated_base: dict) -> None:
        merge_lock.run_acquire(Namespace(plan_id='plan-a'))
        fake = _FakeClock()

        result = merge_lock.run_acquire(
            Namespace(plan_id='plan-a', wait_seconds=60.0, interval_seconds=5.0),
            sleep=fake.sleep,
            clock=fake.clock,
        )

        assert result['status'] == 'success'
        assert result['action'] == 'already_held'
        assert result['timed_out'] is False
        assert result['waited_seconds'] == 0
        assert fake.sleeps == []

    @pytest.mark.parametrize(
        ('wait_seconds', 'interval_seconds'),
        [
            (-1.0, 5.0),
            (float('nan'), 5.0),
            (float('inf'), 5.0),
            (60.0, 0.0),
            (60.0, -5.0),
            (60.0, float('nan')),
            (60.0, float('inf')),
        ],
    )
    def test_invalid_wait_or_interval_is_refused_before_the_store_is_touched(
        self, isolated_base: dict, wait_seconds: float, interval_seconds: float
    ) -> None:
        fake = _FakeClock()

        result = merge_lock.run_acquire(
            Namespace(plan_id='plan-a', wait_seconds=wait_seconds, interval_seconds=interval_seconds),
            sleep=fake.sleep,
            clock=fake.clock,
        )

        assert result['status'] == 'error'
        assert result['error_code'] == merge_lock.ErrorCode.INVALID_INPUT
        assert fake.sleeps == []
        assert not isolated_base['lock_path'].exists()
        assert not isolated_base['queue_path'].exists()

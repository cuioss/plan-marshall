#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: F811 — tests take the imported fixture as a parameter
"""Tests for the unified ``manage-locks/merge_lock.py`` — the single main-anchored
merge-to-main serializer fronted by a FIFO admission queue.

Its sections, in order:

* Fixtures
* Live-worktree guard (D3) — refuse auto-reclaim of a mid-recovery holder
* CLI argparse plumbing
"""


from __future__ import annotations

import json
from argparse import Namespace

from _manage_locks_merge_lock_fixtures import (  # noqa: F401 — a fixture is used by NAME, not by reference
    SCRIPT_PATH,
    _make_live_plan,
    _stub_title_tokens,
    _TokenRecorder,
    _waiting_plan_ids,
    isolated_base,  # noqa: F401 — a fixture is used by NAME, not by reference
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
            SCRIPT_PATH, 'acquire', '--plan-id', 'plan-a', '--no-title-token',
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
            SCRIPT_PATH, 'acquire', '--plan-id', 'plan-a', '--no-title-token',
            env_overrides=env_overrides,
        )
        result = run_script(
            SCRIPT_PATH, 'release', '--plan-id', 'plan-a', '--no-title-token',
            env_overrides=env_overrides,
        )
        assert result.returncode == 0, result.stderr
        parsed = parse_toon(result.stdout)
        assert parsed['status'] == 'success'
        assert parsed['action'] == 'released'

    def test_acquire_accepts_legacy_timeout_flag(self, isolated_base: dict) -> None:
        """The legacy ``--timeout`` flag is still accepted for call-site
        compatibility (acquire no longer waits internally, but the flag must parse)."""
        env_overrides = {'PLAN_BASE_DIR': str(isolated_base['base'])}
        result = run_script(
            SCRIPT_PATH, 'acquire', '--plan-id', 'plan-a', '--timeout', '0',
            env_overrides=env_overrides,
        )
        assert result.returncode == 0, result.stderr
        parsed = parse_toon(result.stdout)
        assert parsed['status'] == 'success'
        assert parsed['admission'] == 'admitted'

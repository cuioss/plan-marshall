#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: F811
"""Tests for the unified ``manage-locks/merge_lock.py`` — the single main-anchored
merge-to-main serializer fronted by a FIFO admission queue.
"""


from __future__ import annotations

from argparse import Namespace
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from _manage_locks_merge_lock_fixtures import (
    SCRIPT_PATH,
    _make_live_plan,
    # Fixtures — resolved by pytest, not referenced by name:
    _stub_title_tokens,  # noqa: F401
    isolated_base,  # noqa: F401
    merge_lock,
)
from toon_parser import parse_toon

from conftest import run_script

# =============================================================================
# §5 (iv) — dead-holder reclaim WITHOUT evicting a live holder, under REAL
# spawned-process contention (the make-or-break liveness-under-races property)
# =============================================================================


class TestConcurrentReclamation:
    """§5 (iv): a crashed/dead holder is reclaimed without ever evicting a LIVE
    holder, asserted under REAL spawned-subprocess contention via the CLI entry
    point. Sequential reclaim tests (``TestStaleReclamation``) cannot exercise the
    interleave window between the dead-holder remove and the re-create, so these
    process-level races are the load-bearing concurrency obligation for the merge
    mutex's reclamation path."""

    @pytest.mark.xdist_group(name="manage_locks_contention")
    def test_concurrent_acquire_against_dead_holder_admits_exactly_one_reclaimer(
        self, isolated_base: dict
    ) -> None:
        """A dead-holder lock file + N live concurrent acquirers racing the SAME
        main-anchored merge.lock → EXACTLY ONE returns ``status: success``; every
        other returns ``status: blocked``. No second acquirer ever wins (FIFO
        admission + the kernel ``O_EXCL`` re-create after the stale unlink admit
        one), and the lock file ends up recording the single winner. The winner's
        ``reclaimed`` flag may be either True or False depending on which of the two
        equivalent dead-holder acquire paths it took under the race."""
        base = isolated_base['base']
        lock_path = isolated_base['lock_path']

        # Pre-stage a DEAD holder: a lock file whose holder has NO live plan dir
        # (neither on main nor in a worktree) → reclaimable by construction. The
        # dead holder is NOT in the FIFO queue, so the racing live acquirers
        # contend for the front among themselves.
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        lock_path.write_text('dead-holder\n', encoding='utf-8')

        n = 8
        # Every contender's plan dir is live, so once one reclaims, the rest find a
        # LIVE holder and serialize (block) — they must NOT also reclaim.
        for i in range(n):
            _make_live_plan(base, f'reclaim-{i}')

        env_overrides = {'PLAN_BASE_DIR': str(base)}

        def _acquire(i: int):
            return run_script(
                SCRIPT_PATH,
                'acquire',
                '--plan-id',
                f'reclaim-{i}',
                '--timeout',
                '30',
                env_overrides=env_overrides,
                timeout=90,
            )

        with ThreadPoolExecutor(max_workers=n) as pool:
            results = list(pool.map(_acquire, range(n)))

        parsed = [parse_toon(r.stdout) for r in results]
        winners = [p for p in parsed if p.get('status') == 'success']
        blocked = [p for p in parsed if p.get('status') == 'blocked']

        # Exactly one reclaimer wins; the rest block — no double-grant of the
        # reclaimed k=1 mutex.
        assert len(winners) == 1, parsed
        assert len(blocked) == n - 1, parsed
        # The single winner took the dead holder's slot. Under genuine N-way
        # contention the winner may report `reclaimed: True` (it ran the
        # decide-dead → unlink → re-create path itself) OR `reclaimed: False` (a
        # racing process unlinked the stale file a beat earlier, so this winner's
        # plain initial O_EXCL create succeeded against the now-free path). Both
        # are correct dead-holder-reclaim outcomes.
        assert winners[0]['reclaimed'] in (True, False), winners[0]
        # The lock file records the single reclaimer, and the dead holder is gone.
        recorded = lock_path.read_text(encoding='utf-8').strip()
        assert recorded == winners[0]['holder']
        assert recorded != 'dead-holder'

    @pytest.mark.xdist_group(name="manage_locks_contention")
    def test_concurrent_acquire_never_evicts_a_live_holder(self, isolated_base: dict) -> None:
        """A LIVE holder holds the lock while N concurrent acquirers race it → NONE
        win, ALL block, and the live holder's lock is never reclaimed or evicted.
        This is the other half of §5 (iv): reclamation must NEVER steal a slot from a
        live holder under contention."""
        base = isolated_base['base']
        lock_path = isolated_base['lock_path']

        # A LIVE holder owns the lock (its plan dir exists → NOT reclaimable). It is
        # dequeued from the FIFO queue so the racing contenders form the queue.
        merge_lock.run_acquire(Namespace(plan_id='live-holder', timeout=5.0))
        _make_live_plan(base, 'live-holder')
        merge_lock._dequeue_fifo('live-holder')

        n = 8
        for i in range(n):
            _make_live_plan(base, f'contender-{i}')

        env_overrides = {'PLAN_BASE_DIR': str(base)}

        def _acquire(i: int):
            return run_script(
                SCRIPT_PATH,
                'acquire',
                '--plan-id',
                f'contender-{i}',
                '--timeout',
                '30',
                env_overrides=env_overrides,
                timeout=90,
            )

        with ThreadPoolExecutor(max_workers=n) as pool:
            results = list(pool.map(_acquire, range(n)))

        parsed = [parse_toon(r.stdout) for r in results]
        winners = [p for p in parsed if p.get('status') == 'success']
        blocked = [p for p in parsed if p.get('status') == 'blocked']

        # NO contender ever evicts the live holder — all block, none acquire.
        assert winners == [], parsed
        assert len(blocked) == n, parsed
        # The live holder's lock survives unchanged across the whole race.
        assert lock_path.read_text(encoding='utf-8').strip() == 'live-holder'
        # Every blocked contender names the live holder as the blocker.
        for p in blocked:
            assert p['blocking_plan_id'] == 'live-holder', p

    @pytest.mark.xdist_group(name="manage_locks_contention")
    def test_concurrent_reclaim_admits_exactly_one_across_repeated_trials(
        self, isolated_base: dict
    ) -> None:
        """Hardened regression for the stale-reclaim TOCTOU double-grant (D1 fix).

        The single-shot ``test_concurrent_acquire_against_dead_holder_admits_exactly_one_reclaimer``
        exercises the dead-holder N-way race ONCE — it catches the double-grant
        only when that one trial happens to hit the narrow interleave window.
        Before the D1 atomic-eviction fix the race could produce TWO winners
        (the canonical ``assert 2 == 1`` failure) whenever two reclaimers both
        decided the holder dead and the second's blind ``os.unlink(path)`` evicted
        the first's freshly-installed LIVE holder. Under repetition that flake
        surfaces reliably.

        This test re-runs the SAME dead-holder reclaim race under repeated trials,
        re-staging the dead holder and clearing the FIFO queue per trial, and
        asserts on EVERY trial that EXACTLY ONE acquirer wins and the remaining
        ``n-1`` block — turning the stochastic single-shot check into a
        deterministic-under-repetition regression guard. It runs under
        ``PLAN_BASE_DIR`` isolation and is stable under ``pytest-xdist`` ``-n auto``
        with widened load-sensitive margins (``--timeout 30`` legacy compat flag,
        ``timeout=90`` outer subprocess kill budget).
        """
        base = isolated_base['base']
        lock_path = isolated_base['lock_path']
        queue_path = isolated_base['queue_path']
        env_overrides = {'PLAN_BASE_DIR': str(base)}

        n = 8
        trials = 10

        # Live contender plan dirs are stable across trials — staged once.
        for i in range(n):
            _make_live_plan(base, f'reclaim-{i}')

        def _acquire(i: int):
            return run_script(
                SCRIPT_PATH,
                'acquire',
                '--plan-id',
                f'reclaim-{i}',
                '--timeout',
                '30',
                env_overrides=env_overrides,
                timeout=90,
            )

        for trial in range(trials):
            # Re-stage the DEAD holder for this trial and clear the FIFO queue so
            # each trial starts from the same dead-holder-held, empty-queue state
            # the race must arbitrate.
            lock_path.parent.mkdir(parents=True, exist_ok=True)
            lock_path.write_text('dead-holder\n', encoding='utf-8')
            if queue_path.exists():
                queue_path.unlink()

            with ThreadPoolExecutor(max_workers=n) as pool:
                results = list(pool.map(_acquire, range(n)))

            parsed = [parse_toon(r.stdout) for r in results]
            winners = [p for p in parsed if p.get('status') == 'success']
            blocked = [p for p in parsed if p.get('status') == 'blocked']

            # The make-or-break invariant on EVERY trial: exactly one winner, the
            # rest blocked — never the ``assert 2 == 1`` double-grant. The trial
            # index is folded into the assertion message so a regression names the
            # offending trial.
            assert len(winners) == 1, (trial, parsed)
            assert len(blocked) == n - 1, (trial, parsed)
            # The lock file records the single winner, and the dead holder is gone.
            recorded = lock_path.read_text(encoding='utf-8').strip()
            assert recorded == winners[0]['holder'], (trial, recorded, winners)
            assert recorded != 'dead-holder', (trial, recorded)

            # Release the winner's lock so the next trial starts from a clean
            # dead-holder-held state rather than the prior winner's live lock.
            merge_lock.run_release(Namespace(plan_id=winners[0]['holder']))


# =============================================================================
# Main-anchored resolution (the single deliberate exception)
# =============================================================================


class TestMainAnchoredResolution:
    def test_lock_resolves_to_main_even_when_cwd_is_a_worktree(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Under PLAN_BASE_DIR (the main-checkout stand-in), the lock resolves to
        ``<base>/merge.lock`` regardless of the process cwd — pinning cwd into a
        worktree fixture does NOT redirect the lock to a worktree-relative path."""
        main_base = tmp_path / 'main' / '.plan' / 'local'
        (main_base / 'plans').mkdir(parents=True)
        monkeypatch.setenv('PLAN_BASE_DIR', str(main_base))

        # A worktree fixture with its own .plan/local — cwd is pinned here.
        worktree = tmp_path / 'worktrees' / 'some-plan'
        (worktree / '.plan' / 'local').mkdir(parents=True)
        monkeypatch.chdir(worktree)

        resolved = merge_lock._resolve_main_lock_path()
        # Resolves to MAIN's base, NOT the worktree-relative .plan/local.
        assert resolved == main_base / 'merge.lock'
        assert worktree / '.plan' / 'local' / 'merge.lock' != resolved

    def test_queue_resolves_to_main_even_when_cwd_is_a_worktree(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The FIFO merge-queue resolves to ``<base>/merge-queue.json`` against the
        MAIN checkout regardless of the process cwd — same main-anchored contract
        as the lock file, so all sessions contend for one shared queue."""
        main_base = tmp_path / 'main' / '.plan' / 'local'
        (main_base / 'plans').mkdir(parents=True)
        monkeypatch.setenv('PLAN_BASE_DIR', str(main_base))

        worktree = tmp_path / 'worktrees' / 'some-plan'
        (worktree / '.plan' / 'local').mkdir(parents=True)
        monkeypatch.chdir(worktree)

        resolved = merge_lock._resolve_merge_queue_path()
        assert resolved == main_base / 'merge-queue.json'
        assert worktree / '.plan' / 'local' / 'merge-queue.json' != resolved

    def test_acquire_writes_to_main_base_from_worktree_cwd(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        main_base = tmp_path / 'main' / '.plan' / 'local'
        (main_base / 'plans').mkdir(parents=True)
        monkeypatch.setenv('PLAN_BASE_DIR', str(main_base))

        worktree = tmp_path / 'worktrees' / 'some-plan'
        (worktree / '.plan' / 'local').mkdir(parents=True)
        monkeypatch.chdir(worktree)

        result = merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        assert result['status'] == 'success'
        # The lock AND the queue landed under MAIN's base, not the worktree.
        assert (main_base / 'merge.lock').is_file()
        assert (main_base / 'merge-queue.json').is_file()
        assert not (worktree / '.plan' / 'local' / 'merge.lock').exists()
        assert not (worktree / '.plan' / 'local' / 'merge-queue.json').exists()

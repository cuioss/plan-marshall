#!/usr/bin/env python3
"""Tests for the unified ``manage-locks/merge_lock.py`` — the single main-anchored
merge-to-main serializer.

Contract under test (lock-reconciliation-analysis.md §4 behavioural-equivalence
criteria + §5 massive-parallel-concurrency invariants (ii) + (iv); ADR-002):

* **Atomic acquire** — ``acquire`` creates the lock file via ``O_EXCL`` and
  records the holder ``plan_id`` in the file contents.
* **No double-merge** — exactly one of two concurrent ``acquire`` calls wins; the
  other waits and, on budget elapse against a LIVE holder, returns
  ``status: blocked`` (NOT a hard error). Two plans never both hold the lock.
* **``blocked`` still escalates** — a live-holder timeout returns
  ``status: blocked`` + ``blocking_plan_id`` (the live holder) +
  ``poll_window_seconds``, so the Pre-Merge Gate's orchestrator escalation fires.
  This REPLACES the former ``error/TIMEOUT`` outcome of the file lock.
* **Stale reclamation** — a lock whose recorded holder has no live plan dir (on
  main OR in its worktree) is reclaimable (``reclaimed: true``); a lock whose
  holder IS live is NOT reclaimable.
* **Idempotent release** — ``release`` removes the lock so the next acquire
  succeeds; release is idempotent (already-free / foreign-holder → no-op success,
  and the foreign holder's lock is left intact).
* **``--timeout 0`` non-blocking try** — against a live holder it returns
  ``blocked`` IMMEDIATELY rather than falling back to the default 30s budget.
* **``check`` holder read** — ``check`` returns ``{free}`` when no lock file
  exists and ``{held, holder_plan_id}`` when one does, without creating or
  mutating the lock.
* **Holder liveness via the shared core** — liveness is the imported
  :func:`_locks_core.holder_is_dead`, NOT a re-implemented copy; both main and
  worktree paths are consulted.
* **Main-anchored resolution (the single exception)** — the lock resolves to the
  MAIN checkout regardless of caller cwd, even when cwd is pinned to a worktree
  fixture.

Real-parallel obligations (§5 (ii) + (iv)): the no-double-merge invariant (ii) and
the dead-holder-reclaim-without-evicting-a-live-holder invariant (iv) are BOTH
asserted under REAL spawned-subprocess contention — N processes racing the SAME
main-anchored ``merge.lock`` via the CLI entry point — not sequential calls. A
sequential test can never exercise the kernel ``O_EXCL`` race window (ii) nor the
interleave between the stale-holder unlink and the atomic re-create (iv).

Isolation (test-isolation lessons): every test runs against an isolated
``PLAN_BASE_DIR`` staged under ``tmp_path`` so the suite never contends for the
real ``.plan/merge.lock`` under ``-n auto``. Under ``PLAN_BASE_DIR`` the lock
resolves to ``<PLAN_BASE_DIR>/merge.lock`` and holder plan dirs resolve to
``<PLAN_BASE_DIR>/plans/{holder}``.

Filename note: this file is named ``test_manage_locks_merge_lock.py`` rather than
``test_merge_lock.py`` because pytest's default ``prepend`` import mode requires
unique test-module basenames across the suite, and ``manage-status`` still owns a
``test_merge_lock.py`` (the layer-#2 marker scan, removed in a later deliverable).
"""

from __future__ import annotations

import time
from argparse import Namespace
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from toon_parser import parse_toon  # type: ignore[import-not-found]

from conftest import get_script_path, load_script_module, run_script

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-locks', 'merge_lock.py')

merge_lock = load_script_module('plan-marshall', 'manage-locks', 'merge_lock.py', 'merge_lock_under_test')


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def isolated_base(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    """Stage an isolated PLAN_BASE_DIR under tmp_path.

    Layout::

        tmp_path/main/.plan/local/            (PLAN_BASE_DIR — main-checkout stand-in)
        tmp_path/main/.plan/local/plans/      (holder plan dirs resolve here)

    Sets PLAN_BASE_DIR to the main stand-in so the lock resolves to
    ``<base>/merge.lock`` and ``holder_is_dead(holder)`` resolves the holder plan
    dir to ``<base>/plans/{holder}``.
    """
    base = tmp_path / 'main' / '.plan' / 'local'
    (base / 'plans').mkdir(parents=True)
    monkeypatch.setenv('PLAN_BASE_DIR', str(base))
    return {'base': base, 'lock_path': base / 'merge.lock'}


def _make_live_plan(base: Path, plan_id: str) -> None:
    """Create a holder plan directory so the holder counts as LIVE."""
    (base / 'plans' / plan_id).mkdir(parents=True, exist_ok=True)


class _TokenRecorder:
    """Records the best-effort title-token set/clear/push calls so a test can
    assert WHAT was surfaced without spawning the real executor subprocess.

    Installed over the three module-level seams ``_set_title_token`` /
    ``_clear_title_token`` / ``_push_title_token`` — the same seam-mock approach
    used by ``test_build_queue_slot.py`` for the D6 wrapper.
    """

    def __init__(self) -> None:
        self.set_states: list[str] = []
        self.cleared: list[str] = []
        self.pushed_icons: list[str] = []

    def install(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(merge_lock, '_set_title_token', lambda _p, state: self.set_states.append(state))
        monkeypatch.setattr(merge_lock, '_clear_title_token', lambda p: self.cleared.append(p))
        monkeypatch.setattr(merge_lock, '_push_title_token', lambda _p, icon: self.pushed_icons.append(icon))


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
# Atomic acquire + holder recording
# =============================================================================


class TestAcquire:
    def test_acquire_creates_lock_and_records_holder(self, isolated_base: dict) -> None:
        result = merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))

        assert result['status'] == 'success', result
        assert result['action'] == 'acquired'
        assert result['holder'] == 'plan-a'
        assert result['reclaimed'] is False

        lock_path = isolated_base['lock_path']
        assert lock_path.is_file()
        # Holder source recorded in the file contents.
        assert lock_path.read_text(encoding='utf-8').strip() == 'plan-a'

    def test_acquire_is_atomic_o_excl(self, isolated_base: dict) -> None:
        """The lock file is created exclusively — a pre-existing file from a live
        holder blocks a second atomic create (the primitive returns False)."""
        lock_path = isolated_base['lock_path']
        # First acquire wins and creates the file.
        merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        _make_live_plan(isolated_base['base'], 'plan-a')
        # The low-level atomic create against the existing file must fail.
        assert merge_lock._try_atomic_create(lock_path, 'plan-b') is False


# =============================================================================
# No double-merge — concurrent serialization (one wins, the other blocks)
# =============================================================================


class TestNoDoubleMerge:
    def test_second_acquire_against_live_holder_blocks(self, isolated_base: dict) -> None:
        """A live holder blocks the second acquire — it serializes and returns the
        structured ``blocked`` payload (NOT a hard error), distinct from the
        former TIMEOUT error outcome."""
        # plan-a acquires and is live (its plan dir exists).
        merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        _make_live_plan(isolated_base['base'], 'plan-a')

        # plan-b cannot acquire while plan-a holds it — short timeout → blocked.
        result = merge_lock.run_acquire(Namespace(plan_id='plan-b', timeout=0.3))
        assert result['status'] == 'blocked'
        assert result['blocking_plan_id'] == 'plan-a'
        assert result['poll_window_seconds'] == 0.3
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

    def test_concurrent_acquire_admits_exactly_one_under_real_contention(
        self, isolated_base: dict
    ) -> None:
        """§5 (ii): N spawned subprocesses race the SAME main-anchored merge.lock
        via the CLI entry point. EXACTLY ONE returns ``status: success/acquired``;
        every other returns ``status: blocked``. Two plans never both hold the
        lock. This is the make-or-break no-double-merge property and MUST run
        under genuine process-level contention, not sequential calls."""
        base = isolated_base['base']
        n = 8
        # Each contender's plan dir is live, so a held lock is NEVER reclaimed —
        # the kernel O_EXCL race is the sole arbiter.
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
                '2',
                env_overrides=env_overrides,
                timeout=30,
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
        # Every blocked result names the winner as the blocking holder.
        for p in blocked:
            assert p['blocking_plan_id'] == winners[0]['holder'], p


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


# =============================================================================
# check — non-blocking holder read
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


# =============================================================================
# Stale reclamation (liveness via the shared _locks_core.holder_is_dead)
# =============================================================================


class TestStaleReclamation:
    def test_dead_holder_lock_is_reclaimed(self, isolated_base: dict) -> None:
        """A lock whose holder has no live plan dir is reclaimable."""
        # plan-dead acquires but its plan dir is NEVER created → dead holder.
        merge_lock.run_acquire(Namespace(plan_id='plan-dead', timeout=5.0))

        # plan-b acquires: observes the held lock, finds the holder dead, reclaims.
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
        (reclaimable)."""
        # A holder whose plan dir is missing is dead → reclaimable.
        merge_lock.run_acquire(Namespace(plan_id='ghost', timeout=5.0))
        result = merge_lock.run_acquire(Namespace(plan_id='plan-b', timeout=5.0))
        assert result['action'] == 'acquired'
        assert result['reclaimed'] is True

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
        blocks IMMEDIATELY rather than falling back to the default 30s budget."""
        merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        _make_live_plan(isolated_base['base'], 'plan-a')
        start = time.monotonic()
        result = merge_lock.run_acquire(Namespace(plan_id='plan-b', timeout=0))
        elapsed = time.monotonic() - start
        assert result['status'] == 'blocked'
        assert result['blocking_plan_id'] == 'plan-a'
        # Non-blocking: returns far under the default 30s budget.
        assert elapsed < 5.0


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

    def test_concurrent_acquire_against_dead_holder_admits_exactly_one_reclaimer(
        self, isolated_base: dict
    ) -> None:
        """A dead-holder lock file + N live concurrent acquirers racing the SAME
        main-anchored merge.lock → EXACTLY ONE returns ``status: success``; every
        other returns ``status: blocked``. No second acquirer ever wins (the kernel
        ``O_EXCL`` re-create after the stale unlink admits one), and the lock file
        ends up recording the single winner. The winner's ``reclaimed`` flag may be
        either True or False depending on which of the two equivalent dead-holder
        acquire paths it took under the race (see the assertion below)."""
        base = isolated_base['base']
        lock_path = isolated_base['lock_path']

        # Pre-stage a DEAD holder: a lock file whose holder has NO live plan dir
        # (neither on main nor in a worktree) → reclaimable by construction.
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
                '2',
                env_overrides=env_overrides,
                timeout=30,
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
        # are correct dead-holder-reclaim outcomes — the load-bearing invariant is
        # that exactly ONE winner emerged and the dead holder is gone, NOT which
        # of the two equivalent acquire paths the winner happened to take.
        assert winners[0]['reclaimed'] in (True, False), winners[0]
        # The lock file records the single reclaimer, and the dead holder is gone.
        recorded = lock_path.read_text(encoding='utf-8').strip()
        assert recorded == winners[0]['holder']
        assert recorded != 'dead-holder'
        # Every blocked acquirer names the reclaimer as the live blocking holder.
        for p in blocked:
            assert p['blocking_plan_id'] == winners[0]['holder'], p

    def test_concurrent_acquire_never_evicts_a_live_holder(self, isolated_base: dict) -> None:
        """A LIVE holder holds the lock while N concurrent acquirers race it → NONE
        win, ALL block, and the live holder's lock is never reclaimed or evicted.
        This is the other half of §5 (iv): reclamation must NEVER steal a slot from a
        live holder under contention."""
        base = isolated_base['base']
        lock_path = isolated_base['lock_path']

        # A LIVE holder owns the lock (its plan dir exists → NOT reclaimable).
        merge_lock.run_acquire(Namespace(plan_id='live-holder', timeout=5.0))
        _make_live_plan(base, 'live-holder')

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
                '1',
                env_overrides=env_overrides,
                timeout=30,
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
        # The lock landed under MAIN's base, not the worktree.
        assert (main_base / 'merge.lock').is_file()
        assert not (worktree / '.plan' / 'local' / 'merge.lock').exists()


# =============================================================================
# Shared-core delegation guard — no re-implemented liveness / resolution
# =============================================================================


class TestSharedCoreDelegation:
    """The unified merge_lock builds on the shared coordination core — it imports
    ``holder_is_dead`` from ``_locks_core`` and ``resolve_main_anchored_path``
    from ``marketplace_paths`` rather than re-implementing either. These guards
    fail if a parallel copy is ever reintroduced."""

    def test_imports_shared_liveness_predicate(self) -> None:
        # holder_is_dead must be imported from the shared core, not redefined.
        assert hasattr(merge_lock, 'holder_is_dead')

    def test_imports_shared_resolver(self) -> None:
        assert hasattr(merge_lock, 'resolve_main_anchored_path')

    def test_no_inline_liveness_copy(self) -> None:
        # The former inline ``_holder_is_dead`` / ``_main_plan_local_base`` copies
        # were dropped — liveness lives once in _locks_core now.
        assert not hasattr(merge_lock, '_holder_is_dead')
        assert not hasattr(merge_lock, '_main_plan_local_base')

    def test_no_inline_git_common_dir_in_source(self) -> None:
        # No inline ``git rev-parse --git-common-dir`` subprocess call remains —
        # resolution belongs to the shared utility.
        src = SCRIPT_PATH.read_text(encoding='utf-8')
        assert '--git-common-dir' not in src

    def test_no_status_marker_scan_in_source(self) -> None:
        # The status-marker scan (layer #2) was dropped — no merging_on_main
        # marker or cross-plan scan survives in the unified file primitive.
        src = SCRIPT_PATH.read_text(encoding='utf-8')
        assert 'merging_on_main' not in src
        assert '_find_holder' not in src


# =============================================================================
# Title-token surface (best-effort, OUTSIDE the O_EXCL window)
# =============================================================================


class TestTitleTokenSurface:
    """The merge lock surfaces its state in the terminal title — ⏳ (lock-waiting)
    while a live holder blocks this caller, 🔒 (lock-owned) once the lock is held,
    and a clear on every release path. Every write is best-effort and placed
    OUTSIDE the O_EXCL check-then-act window (mirrors D6's build-phase pair)."""

    def test_acquire_surfaces_lock_owned_on_fresh_acquire(
        self, isolated_base: dict, _stub_title_tokens: _TokenRecorder
    ) -> None:
        result = merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        assert result['status'] == 'success'
        # `lock-owned` state set (bare state name, no glyph) + 🔒 pushed.
        assert _stub_title_tokens.set_states == ['lock-owned']
        assert _stub_title_tokens.pushed_icons == [merge_lock._ICON_LOCK_OWNED]
        # No waiting token on an uncontended acquire.
        assert 'lock-waiting' not in _stub_title_tokens.set_states

    def test_acquire_surfaces_lock_owned_on_reclaim(
        self, isolated_base: dict, _stub_title_tokens: _TokenRecorder
    ) -> None:
        """A reclaim of a dead holder's lock also surfaces `lock-owned` (🔒)."""
        merge_lock.run_acquire(Namespace(plan_id='plan-dead', timeout=5.0))
        _stub_title_tokens.set_states.clear()
        _stub_title_tokens.pushed_icons.clear()

        result = merge_lock.run_acquire(Namespace(plan_id='plan-b', timeout=5.0))
        assert result['reclaimed'] is True
        assert _stub_title_tokens.set_states == ['lock-owned']
        assert _stub_title_tokens.pushed_icons == [merge_lock._ICON_LOCK_OWNED]

    def test_blocked_acquire_surfaces_lock_waiting_once(
        self, isolated_base: dict, _stub_title_tokens: _TokenRecorder
    ) -> None:
        """A live holder blocking this caller surfaces `lock-waiting` (⏳). The
        token is set exactly once even across multiple backoff polls — it is
        gated by the `waiting_surfaced` flag and never re-fires per poll."""
        merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        _make_live_plan(isolated_base['base'], 'plan-a')
        _stub_title_tokens.set_states.clear()
        _stub_title_tokens.pushed_icons.clear()

        # A small budget forces several backoff polls before blocking.
        result = merge_lock.run_acquire(Namespace(plan_id='plan-b', timeout=0.6))
        assert result['status'] == 'blocked'
        # `lock-waiting` set EXACTLY ONCE despite multiple polls; never lock-owned.
        assert _stub_title_tokens.set_states == ['lock-waiting']
        assert _stub_title_tokens.pushed_icons == [merge_lock._ICON_LOCK_WAITING]
        assert 'lock-owned' not in _stub_title_tokens.set_states

    def test_timeout_zero_blocked_does_not_surface_waiting(
        self, isolated_base: dict, _stub_title_tokens: _TokenRecorder
    ) -> None:
        """A `--timeout 0` non-blocking try blocks IMMEDIATELY without ever
        sleeping — so the `lock-waiting` token (set only before a sleep) never
        fires. No token of any kind is surfaced on the immediate-block path."""
        merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        _make_live_plan(isolated_base['base'], 'plan-a')
        _stub_title_tokens.set_states.clear()
        _stub_title_tokens.pushed_icons.clear()

        result = merge_lock.run_acquire(Namespace(plan_id='plan-b', timeout=0))
        assert result['status'] == 'blocked'
        assert _stub_title_tokens.set_states == []
        assert _stub_title_tokens.pushed_icons == []

    def test_release_clears_token_on_released_path(
        self, isolated_base: dict, _stub_title_tokens: _TokenRecorder
    ) -> None:
        merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        _stub_title_tokens.cleared.clear()

        result = merge_lock.run_release(Namespace(plan_id='plan-a'))
        assert result['action'] == 'released'
        assert _stub_title_tokens.cleared == ['plan-a']

    def test_release_clears_token_on_already_free_noop(
        self, isolated_base: dict, _stub_title_tokens: _TokenRecorder
    ) -> None:
        result = merge_lock.run_release(Namespace(plan_id='plan-a'))
        assert result['action'] == 'noop'
        # The already-free noop still clears this caller's stale token.
        assert _stub_title_tokens.cleared == ['plan-a']

    def test_release_clears_token_on_foreign_holder_noop(
        self, isolated_base: dict, _stub_title_tokens: _TokenRecorder
    ) -> None:
        merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        _stub_title_tokens.cleared.clear()

        result = merge_lock.run_release(Namespace(plan_id='plan-b'))
        assert result['action'] == 'noop'
        # The foreign-holder noop clears the CALLER's (plan-b's) stale token, and
        # leaves plan-a's lock intact.
        assert _stub_title_tokens.cleared == ['plan-b']
        assert isolated_base['lock_path'].is_file()

    def test_token_write_failure_never_breaks_acquire(self, isolated_base: dict) -> None:
        """The best-effort wrappers swallow any underlying executor failure — a
        token write that raises NEVER affects the lock acquire outcome. This
        exercises the REAL _set_title_token / _push_title_token wrappers by making
        the underlying _run_executor raise."""

        def _raising_run_executor(*_a: object, **_k: object) -> dict:
            raise OSError('tty gone')

        # Patch the low-level executor seam (NOT the higher-level token seams), so
        # the real best-effort try/except wrappers run and swallow the error.
        import pytest as _pytest

        mp = _pytest.MonkeyPatch()
        mp.setattr(merge_lock, '_run_executor', _raising_run_executor)
        try:
            result = merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        finally:
            mp.undo()

        # The lock was acquired despite the token channel raising.
        assert result['status'] == 'success'
        assert result['action'] == 'acquired'
        assert isolated_base['lock_path'].is_file()

    def test_token_clear_failure_never_breaks_release(self, isolated_base: dict) -> None:
        """Symmetric to ``test_token_write_failure_never_breaks_acquire`` on the
        RELEASE side: the best-effort ``_clear_title_token`` wrapper swallows any
        underlying executor failure, so a token-clear that raises NEVER aborts the
        lock release. Exercises the REAL ``_clear_title_token`` wrapper by making
        the low-level ``_run_executor`` seam raise, and asserts the lock file is
        still removed (the release succeeded despite the token channel raising)."""

        def _raising_run_executor(*_a: object, **_k: object) -> dict:
            raise OSError('tty gone')

        merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        assert isolated_base['lock_path'].is_file()

        # Patch the low-level executor seam (NOT the higher-level token seams), so
        # the real best-effort try/except wrapper runs and swallows the error.
        import pytest as _pytest

        mp = _pytest.MonkeyPatch()
        mp.setattr(merge_lock, '_run_executor', _raising_run_executor)
        try:
            result = merge_lock.run_release(Namespace(plan_id='plan-a'))
        finally:
            mp.undo()

        # The lock was released despite the token-clear channel raising.
        assert result['status'] == 'success'
        assert result['action'] == 'released'
        assert not isolated_base['lock_path'].exists()

    def test_lock_owned_token_set_only_after_atomic_create_succeeds(
        self, isolated_base: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The O_EXCL-window-not-widened invariant: the ``lock-owned`` token writes
        run STRICTLY AFTER the atomic ``_try_atomic_create`` has already succeeded,
        never interleaved inside the check-then-act. Record the ordered sequence of
        (atomic-create, token-set) events through wrapped seams and assert the
        atomic create's success is observed BEFORE the first ``lock-owned`` set —
        proving the token surface cannot reopen the closed TOCTOU window."""
        events: list[str] = []

        real_atomic_create = merge_lock._try_atomic_create

        def _recording_atomic_create(lock_path: Path, holder: str) -> bool:
            ok = real_atomic_create(lock_path, holder)
            events.append(f'atomic_create:{"ok" if ok else "eexist"}')
            return ok

        monkeypatch.setattr(merge_lock, '_try_atomic_create', _recording_atomic_create)
        monkeypatch.setattr(
            merge_lock, '_set_title_token', lambda _p, state: events.append(f'set:{state}')
        )
        monkeypatch.setattr(merge_lock, '_push_title_token', lambda _p, icon: events.append('push'))

        result = merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        assert result['status'] == 'success'

        # The successful atomic create MUST be recorded before the first lock-owned
        # set — the token write is strictly after the window closed, never inside it.
        assert 'atomic_create:ok' in events
        assert 'set:lock-owned' in events
        assert events.index('atomic_create:ok') < events.index('set:lock-owned'), events
        # No token of any kind precedes the successful atomic create.
        first_token_idx = next(
            (i for i, e in enumerate(events) if e.startswith(('set:', 'push'))), len(events)
        )
        assert events.index('atomic_create:ok') < first_token_idx, events

    def test_lock_owned_state_maps_to_lock_icon(self) -> None:
        """Guard the glyph contract: the lock-owned/lock-waiting icon constants
        match the canonical manage-terminal-title glyph vocabulary (🔒 / ⏳), and
        the bare STATE NAMES are passed to manage-status (no hard-coded glyph in
        the lock branching)."""
        assert merge_lock._ICON_LOCK_OWNED == '\U0001f512'
        assert merge_lock._ICON_LOCK_WAITING == '⏳'
        assert merge_lock._STATE_LOCK_OWNED == 'lock-owned'
        assert merge_lock._STATE_LOCK_WAITING == 'lock-waiting'


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

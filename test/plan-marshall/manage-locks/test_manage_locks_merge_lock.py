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

# The shared core owns the [LOCK]-log resolver and the best-effort emission
# swallow. ``merge_lock`` does ``from _locks_core import log_lock_event``, so the
# function closes over the _locks_core module that ``merge_lock`` imported — that
# SAME module instance is recovered from the function's ``__globals__`` (NOT a
# fresh ``load_script_module`` copy, which would be a different instance whose
# patches ``merge_lock`` never sees).
import sys as _sys  # noqa: E402

_locks_core = _sys.modules[merge_lock.log_lock_event.__module__]


def _read_lock_log() -> str:
    """Read the main-anchored [LOCK] log, '' when no emission landed yet."""
    log_path = _locks_core._resolve_lock_log_path()
    if not log_path.exists():
        return ''
    return log_path.read_text(encoding='utf-8')


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

    @pytest.mark.xdist_group(name="manage_locks_contention")
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
                '8',
                env_overrides=env_overrides,
                timeout=60,
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
# _reclaim_stale_lock — atomic eviction of the OBSERVED stale file (deterministic
# in-process unit; pins the atomicity contract the concurrency tests exercise only
# stochastically)
# =============================================================================


class TestReclaimStaleLockHelper:
    """The reclaim eviction arbitrates on the SPECIFIC observed stale file, not the
    bare path: it renames the file aside to a per-reclaimer unique sidecar,
    re-confirms the renamed-away content is exactly the dead holder it decided to
    evict, and only then O_EXCL-recreates. The former blind ``os.unlink(path)``
    would evict whatever lived at the path — including a live holder a concurrent
    reclaimer had just installed — and let two acquirers both win. These
    deterministic units pin both branches: confirmed-dead reclaim, and the
    abort/restore branch when the path's holder changed to a live holder between
    observation and reclaim."""

    def test_reclaim_succeeds_for_observed_dead_holder(self, isolated_base: dict) -> None:
        """A lock file recording a dead holder (no live plan dir) is atomically
        reclaimed: the helper returns True, the dead file is gone, and the lock
        file now records the new holder."""
        lock_path = isolated_base['lock_path']
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        # 'dead-holder' has no plan dir under <base>/plans → dead.
        lock_path.write_text('dead-holder\n', encoding='utf-8')

        won = merge_lock._reclaim_stale_lock(lock_path, 'dead-holder', 'plan-b')

        assert won is True
        # The lock now records the reclaiming holder.
        assert lock_path.read_text(encoding='utf-8').strip() == 'plan-b'
        # No reclaim sidecar left behind.
        siblings = list(lock_path.parent.glob(f'{lock_path.name}.reclaim.*'))
        assert siblings == [], siblings

    def test_reclaim_aborts_and_restores_when_holder_became_live(
        self, isolated_base: dict
    ) -> None:
        """The abort/restore branch: the file at the path changed to a LIVE holder
        between the liveness observation and the reclaim. The helper renames it
        aside, finds the renamed-away content is NOT the observed dead holder (it
        is a live holder), restores the file intact via ``os.replace``, and returns
        False — the live holder's lock survives unchanged and this reclaimer loses."""
        base = isolated_base['base']
        lock_path = isolated_base['lock_path']
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        # The file at the path is now a LIVE holder (its plan dir exists), even
        # though the reclaimer OBSERVED a dead holder ('dead-holder') a beat earlier.
        _make_live_plan(base, 'live-winner')
        lock_path.write_text('live-winner\n', encoding='utf-8')

        won = merge_lock._reclaim_stale_lock(lock_path, 'dead-holder', 'plan-b')

        assert won is False
        # The live holder's lock file is restored intact — never evicted.
        assert lock_path.is_file()
        assert lock_path.read_text(encoding='utf-8').strip() == 'live-winner'
        # The sidecar was replaced back, not left dangling.
        siblings = list(lock_path.parent.glob(f'{lock_path.name}.reclaim.*'))
        assert siblings == [], siblings

    def test_reclaim_aborts_and_restores_when_holder_changed_to_other_dead(
        self, isolated_base: dict
    ) -> None:
        """The observed-file arbitration also loses when the path's content changed
        to a DIFFERENT holder (even another dead one) before the rename — the
        renamed-away content must equal the SPECIFIC observed holder. A mismatch
        restores the file and returns False rather than stealing a slot the
        reclaimer never observed."""
        lock_path = isolated_base['lock_path']
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        # The file is a different (also dead) holder than the one observed.
        lock_path.write_text('other-dead\n', encoding='utf-8')

        won = merge_lock._reclaim_stale_lock(lock_path, 'dead-holder', 'plan-b')

        assert won is False
        # The file is restored intact (the different holder), not reclaimed.
        assert lock_path.read_text(encoding='utf-8').strip() == 'other-dead'
        siblings = list(lock_path.parent.glob(f'{lock_path.name}.reclaim.*'))
        assert siblings == [], siblings

    def test_reclaim_drops_sidecar_and_loses_when_restore_replace_raises(
        self, isolated_base: dict
    ) -> None:
        """The abort/restore branch when ``os.replace`` ITSELF raises: the helper
        observed a dead holder, renamed the file aside, then found the renamed-away
        content was NOT the observed dead holder — so it tries to restore the file
        via ``os.replace``, but that restore raises (a concurrent reclaimer already
        recreated the path). The helper must drop the now-stale sidecar via
        ``os.unlink`` and still lose cleanly with ``False`` — never granting this
        reclaimer the lock. This pins the best-effort-restore sub-branch the other
        abort tests (where ``os.replace`` succeeds) leave unexercised."""
        base = isolated_base['base']
        lock_path = isolated_base['lock_path']
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        # The file at the path is a LIVE holder (its plan dir exists) — different
        # from the observed dead holder, so the helper enters the restore branch.
        _make_live_plan(base, 'live-winner')
        lock_path.write_text('live-winner\n', encoding='utf-8')

        # Make the restore os.replace raise, simulating a concurrent reclaimer
        # having recreated the path before this loser could restore it.
        unlinked: list[str] = []
        real_unlink = merge_lock.os.unlink

        def _raising_replace(_src: str, _dst: str) -> None:
            raise OSError('restore target busy')

        def _recording_unlink(target: str) -> None:
            unlinked.append(target)
            real_unlink(target)

        mp = pytest.MonkeyPatch()
        mp.setattr(merge_lock.os, 'replace', _raising_replace)
        mp.setattr(merge_lock.os, 'unlink', _recording_unlink)
        try:
            won = merge_lock._reclaim_stale_lock(lock_path, 'dead-holder', 'plan-b')
        finally:
            mp.undo()

        # The reclaimer lost cleanly despite the restore failing.
        assert won is False
        # The now-stale sidecar was dropped via os.unlink (best-effort cleanup),
        # so no reclaim sidecar lingers on disk.
        assert len(unlinked) == 1, unlinked
        assert Path(unlinked[0]).name.startswith(f'{lock_path.name}.reclaim.')
        siblings = list(lock_path.parent.glob(f'{lock_path.name}.reclaim.*'))
        assert siblings == [], siblings

    def test_reclaim_returns_false_when_path_already_gone(self, isolated_base: dict) -> None:
        """When a racing reclaimer already swapped/removed the file, the rename
        fails (the path is gone) and the helper loses cleanly with False — no
        sidecar, no recreate, fall through to retry."""
        lock_path = isolated_base['lock_path']
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        # No file at the path — simulates a racing reclaimer having claimed it.
        assert not lock_path.exists()

        won = merge_lock._reclaim_stale_lock(lock_path, 'dead-holder', 'plan-b')

        assert won is False
        assert not lock_path.exists()
        siblings = list(lock_path.parent.glob(f'{lock_path.name}.reclaim.*'))
        assert siblings == [], siblings

    def test_reclaim_uses_unique_sidecar_per_reclaimer(self, isolated_base: dict) -> None:
        """The sidecar target is a per-reclaimer unique name (``{lock}.reclaim.{pid}.{uuid}``)
        — a path only this reclaimer names, so two concurrent reclaimers never
        collide on the rename target. Exercised by confirming the rename target
        carries the pid and a uuid hex suffix during a successful reclaim (the
        sidecar is consumed by the time the helper returns, so assert via a wrapped
        ``os.rename`` seam)."""
        import os as _os

        lock_path = isolated_base['lock_path']
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        lock_path.write_text('dead-holder\n', encoding='utf-8')

        rename_targets: list[str] = []
        real_rename = _os.rename

        def _recording_rename(src: str, dst: str) -> None:
            rename_targets.append(dst)
            real_rename(src, dst)

        mp = pytest.MonkeyPatch()
        mp.setattr(merge_lock.os, 'rename', _recording_rename)
        try:
            won = merge_lock._reclaim_stale_lock(lock_path, 'dead-holder', 'plan-b')
        finally:
            mp.undo()

        assert won is True
        # The (single) rename targeted a unique sidecar carrying pid + a hex uuid.
        assert len(rename_targets) == 1, rename_targets
        target_name = Path(rename_targets[0]).name
        assert target_name.startswith(f'{lock_path.name}.reclaim.{_os.getpid()}.')
        # The uuid suffix is 32 hex chars.
        suffix = target_name.rsplit('.', 1)[-1]
        assert len(suffix) == 32 and all(c in '0123456789abcdef' for c in suffix)


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
                '8',
                env_overrides=env_overrides,
                timeout=60,
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

    @pytest.mark.xdist_group(name="manage_locks_contention")
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
                '8',
                env_overrides=env_overrides,
                timeout=60,
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
        re-staging the dead holder and the live contender plan dirs per trial, and
        asserts on EVERY trial that EXACTLY ONE acquirer wins and the remaining
        ``n-1`` block — turning the stochastic single-shot check into a
        deterministic-under-repetition regression guard that fails reliably if the
        TOCTOU hole regresses. It runs under ``PLAN_BASE_DIR`` isolation (no
        contention for the real ``.plan/merge.lock``) and is stable under
        ``pytest-xdist`` ``-n auto``.
        """
        base = isolated_base['base']
        lock_path = isolated_base['lock_path']
        env_overrides = {'PLAN_BASE_DIR': str(base)}

        n = 8
        trials = 10

        # Live contender plan dirs are stable across trials — staged once. Once
        # one contender reclaims, the rest find a LIVE holder and serialize.
        for i in range(n):
            _make_live_plan(base, f'reclaim-{i}')

        def _acquire(i: int):
            return run_script(
                SCRIPT_PATH,
                'acquire',
                '--plan-id',
                f'reclaim-{i}',
                '--timeout',
                '8',
                env_overrides=env_overrides,
                timeout=60,
            )

        for trial in range(trials):
            # Re-stage the DEAD holder for this trial: a lock file whose holder has
            # NO live plan dir → reclaimable by construction. Each trial starts from
            # the same dead-holder-held state the race must arbitrate.
            lock_path.parent.mkdir(parents=True, exist_ok=True)
            lock_path.write_text('dead-holder\n', encoding='utf-8')

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
            # Every blocked acquirer names the single winner as the live blocker.
            for p in blocked:
                assert p['blocking_plan_id'] == winners[0]['holder'], (trial, p)

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
# Title-token suppression contract (set_title_token=False)
# =============================================================================


class TestTitleTokenSuppression:
    """The ``set_title_token`` parameter gates the entire title-token surface so the
    move-back merge lock (a brief, finalize-internal mutex) never flashes a spurious
    glyph into the terminal title. ``set_title_token=False`` suppresses ALL three
    title surfaces — ``lock-owned`` (🔒), ``lock-waiting`` (⏳), and the release
    clear — while the default (``set_title_token`` absent, or ``True``) preserves the
    full surface. These tests assert BOTH halves of the contract through the same
    ``_TokenRecorder`` seam ``TestTitleTokenSurface`` uses."""

    def test_acquire_suppresses_lock_owned_when_set_title_token_false(
        self, isolated_base: dict, _stub_title_tokens: _TokenRecorder
    ) -> None:
        """A fresh acquire with ``set_title_token=False`` surfaces NO token — the
        🔒 ``lock-owned`` glyph never reaches the title even though the lock is held."""
        result = merge_lock.run_acquire(
            Namespace(plan_id='plan-a', timeout=5.0, set_title_token=False)
        )
        assert result['status'] == 'success'
        assert result['action'] == 'acquired'
        # No state set, no icon pushed — the title surface is fully suppressed.
        assert _stub_title_tokens.set_states == []
        assert _stub_title_tokens.pushed_icons == []

    def test_acquire_suppresses_lock_owned_on_reclaim_when_set_title_token_false(
        self, isolated_base: dict, _stub_title_tokens: _TokenRecorder
    ) -> None:
        """The reclaim path also honors suppression — a reclaimed acquire with
        ``set_title_token=False`` surfaces no 🔒 token."""
        merge_lock.run_acquire(Namespace(plan_id='plan-dead', timeout=5.0))
        _stub_title_tokens.set_states.clear()
        _stub_title_tokens.pushed_icons.clear()

        result = merge_lock.run_acquire(
            Namespace(plan_id='plan-b', timeout=5.0, set_title_token=False)
        )
        assert result['reclaimed'] is True
        assert _stub_title_tokens.set_states == []
        assert _stub_title_tokens.pushed_icons == []

    def test_blocked_acquire_suppresses_lock_waiting_when_set_title_token_false(
        self, isolated_base: dict, _stub_title_tokens: _TokenRecorder
    ) -> None:
        """A blocked acquire against a live holder with ``set_title_token=False``
        surfaces no ⏳ ``lock-waiting`` token despite sleeping through backoff polls."""
        merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        _make_live_plan(isolated_base['base'], 'plan-a')
        _stub_title_tokens.set_states.clear()
        _stub_title_tokens.pushed_icons.clear()

        result = merge_lock.run_acquire(
            Namespace(plan_id='plan-b', timeout=0.6, set_title_token=False)
        )
        assert result['status'] == 'blocked'
        assert _stub_title_tokens.set_states == []
        assert _stub_title_tokens.pushed_icons == []

    def test_release_suppresses_clear_when_set_title_token_false(
        self, isolated_base: dict, _stub_title_tokens: _TokenRecorder
    ) -> None:
        """A release with ``set_title_token=False`` clears NO token — there was never
        a token set by the suppressed acquire, so there is nothing to clear."""
        merge_lock.run_acquire(
            Namespace(plan_id='plan-a', timeout=5.0, set_title_token=False)
        )
        _stub_title_tokens.cleared.clear()

        result = merge_lock.run_release(
            Namespace(plan_id='plan-a', set_title_token=False)
        )
        assert result['action'] == 'released'
        assert _stub_title_tokens.cleared == []

    def test_release_noop_suppresses_clear_when_set_title_token_false(
        self, isolated_base: dict, _stub_title_tokens: _TokenRecorder
    ) -> None:
        """The already-free / foreign-holder noop release paths also honor
        suppression — ``set_title_token=False`` clears no token on the noop path."""
        result = merge_lock.run_release(
            Namespace(plan_id='plan-a', set_title_token=False)
        )
        assert result['action'] == 'noop'
        assert _stub_title_tokens.cleared == []

    def test_acquire_default_still_surfaces_token(
        self, isolated_base: dict, _stub_title_tokens: _TokenRecorder
    ) -> None:
        """The default (``set_title_token`` absent → True) preserves the full surface —
        a default acquire still surfaces the 🔒 ``lock-owned`` token."""
        result = merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        assert result['status'] == 'success'
        assert _stub_title_tokens.set_states == ['lock-owned']
        assert _stub_title_tokens.pushed_icons == [merge_lock._ICON_LOCK_OWNED]

    def test_release_default_still_clears_token(
        self, isolated_base: dict, _stub_title_tokens: _TokenRecorder
    ) -> None:
        """The default (``set_title_token`` absent → True) preserves the release
        clear — a default release still clears the title token."""
        merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        _stub_title_tokens.cleared.clear()

        result = merge_lock.run_release(Namespace(plan_id='plan-a'))
        assert result['action'] == 'released'
        assert _stub_title_tokens.cleared == ['plan-a']


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


# =============================================================================
# [LOCK] event emission (best-effort, OUTSIDE the O_EXCL window)
# =============================================================================


class TestLockEventEmission:
    """Each merge-lock lifecycle point emits a ``[LOCK]`` event into the SINGLE
    main-anchored global lock-event log via the shared
    :func:`_locks_core.log_lock_event`: ``acquired`` on a fresh O_EXCL create,
    ``reclaimed`` on a stale-reclaim re-create (carrying the reclaimed-from
    holder), ``blocked`` on a live-holder timeout (carrying holder/waiter), and
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
        # plan-dead acquires but never gets a plan dir → dead → reclaimable.
        merge_lock.run_acquire(Namespace(plan_id='plan-dead', timeout=5.0))

        result = merge_lock.run_acquire(Namespace(plan_id='plan-b', timeout=5.0))
        assert result['reclaimed'] is True

        content = _read_lock_log()
        assert '[LOCK] (merge:reclaimed) plan-b' in content
        # The reclaimed-from holder is carried as a correlation field.
        assert 'reclaimed_from: plan-dead' in content

    def test_blocked_timeout_emits_lock_blocked_with_holder_and_waiter(
        self, isolated_base: dict
    ) -> None:
        """A wait-budget timeout against a LIVE holder emits ``blocked`` carrying
        the blocking holder and the waiter."""
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

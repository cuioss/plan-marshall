#!/usr/bin/env python3
"""Tests for merge_lock.py — the single main-anchored cooperative merge lock.

Contract under test (solution_outline.md §15, ADR-002):

* **Atomic acquire** — ``acquire`` creates the lock file via ``O_EXCL`` and
  records the holder ``plan_id`` in the file contents.
* **Concurrent serialization** — when the lock is held by a LIVE holder, a
  second ``acquire`` with a short timeout fails (``TIMEOUT``); after the holder
  releases, the next acquire succeeds. Exactly one holder at a time.
* **Holder-source recorded** — the lock file contents carry the acquiring
  ``plan_id``.
* **Release frees** — ``release`` removes the lock so the next acquire succeeds;
  release is idempotent (already-free / foreign-holder → no-op success).
* **Stale reclamation** — a lock whose recorded holder has no live plan
  directory is reclaimable; a lock whose holder IS live is NOT reclaimable.
* **Main-anchored resolution (the single exception)** — the lock resolves to the
  MAIN checkout regardless of caller cwd, even when cwd is pinned to a worktree
  fixture.

Isolation (test-isolation lessons): every test runs against an isolated
``PLAN_BASE_DIR`` staged under ``tmp_path`` so the suite never contends for the
real ``.plan/merge.lock`` under ``-n auto``. Under ``PLAN_BASE_DIR`` the lock
resolves to ``<PLAN_BASE_DIR>/merge.lock`` and holder plan dirs resolve to
``<PLAN_BASE_DIR>/plans/{holder}``.
"""

from __future__ import annotations

import importlib.util
import time
from argparse import Namespace
from pathlib import Path

import pytest

from conftest import get_script_path, run_script

SCRIPT_PATH = get_script_path('plan-marshall', 'workflow-integration-git', 'merge_lock.py')

_spec = importlib.util.spec_from_file_location('merge_lock', SCRIPT_PATH)
assert _spec is not None and _spec.loader is not None
merge_lock = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(merge_lock)


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
    ``<base>/merge.lock`` and ``get_plan_dir(holder)`` resolves to
    ``<base>/plans/{holder}``.
    """
    base = tmp_path / 'main' / '.plan' / 'local'
    (base / 'plans').mkdir(parents=True)
    monkeypatch.setenv('PLAN_BASE_DIR', str(base))
    return {'base': base, 'lock_path': base / 'merge.lock'}


def _make_live_plan(base: Path, plan_id: str) -> None:
    """Create a holder plan directory so the holder counts as LIVE."""
    (base / 'plans' / plan_id).mkdir(parents=True, exist_ok=True)


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
# Concurrent serialization (one wins)
# =============================================================================


class TestConcurrentSerialization:
    def test_second_acquire_against_live_holder_times_out(self, isolated_base: dict) -> None:
        """A live holder blocks the second acquire — it serializes (times out)."""
        # plan-a acquires and is live (its plan dir exists).
        merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        _make_live_plan(isolated_base['base'], 'plan-a')

        # plan-b cannot acquire while plan-a holds it — short timeout → TIMEOUT.
        result = merge_lock.run_acquire(Namespace(plan_id='plan-b', timeout=0.3))
        assert result['status'] == 'error'
        assert result.get('error_code') == merge_lock.ErrorCode.TIMEOUT
        assert result['holder'] == 'plan-a'

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
# Stale reclamation
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
        """A lock whose holder IS live is NOT reclaimable (serializes/times out)."""
        merge_lock.run_acquire(Namespace(plan_id='plan-live', timeout=5.0))
        _make_live_plan(isolated_base['base'], 'plan-live')

        result = merge_lock.run_acquire(Namespace(plan_id='plan-b', timeout=0.3))
        assert result['status'] == 'error'
        assert result.get('error_code') == merge_lock.ErrorCode.TIMEOUT

    def test_holder_is_dead_predicate(self, isolated_base: dict) -> None:
        # Empty / unresolvable holder is dead (corrupt lock is reclaimable).
        assert merge_lock._holder_is_dead('') is True
        # Holder with no plan dir is dead.
        assert merge_lock._holder_is_dead('ghost') is True
        # Holder with a live plan dir is alive.
        _make_live_plan(isolated_base['base'], 'alive')
        assert merge_lock._holder_is_dead('alive') is False

    def test_worktree_resident_holder_is_not_reclaimed(self, isolated_base: dict) -> None:
        """A holder whose plan dir has been MOVED into its worktree (executing or
        mid-finalize, absent on the main checkout) is LIVE and MUST NOT be
        reclaimed. Regression for the premature-reclamation bug (PR #556 review,
        finding a58aaa): checking only the main checkout would steal the lock
        from an actively-finalizing session and break serialization."""
        base = isolated_base['base']
        # plan-wt holds the lock and its plan dir lives ONLY in the worktree.
        merge_lock.run_acquire(Namespace(plan_id='plan-wt', timeout=5.0))
        (base / 'worktrees' / 'plan-wt' / '.plan' / 'local' / 'plans' / 'plan-wt').mkdir(parents=True)
        assert merge_lock._holder_is_dead('plan-wt') is False
        # A concurrent acquirer must serialize (time out), NOT reclaim.
        result = merge_lock.run_acquire(Namespace(plan_id='plan-b', timeout=0.3))
        assert result['status'] == 'error'
        assert result.get('error_code') == merge_lock.ErrorCode.TIMEOUT
        assert result['holder'] == 'plan-wt'

    def test_timeout_zero_is_non_blocking(self, isolated_base: dict) -> None:
        """``--timeout 0`` is a valid non-blocking try: against a live holder it
        fails IMMEDIATELY rather than falling back to the default 30s budget.
        Regression for the `or`-falsy-trap (PR #556 review, finding 8786e0) —
        the bug would block ~30s here."""
        merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        _make_live_plan(isolated_base['base'], 'plan-a')
        start = time.monotonic()
        result = merge_lock.run_acquire(Namespace(plan_id='plan-b', timeout=0))
        elapsed = time.monotonic() - start
        assert result['status'] == 'error'
        assert result.get('error_code') == merge_lock.ErrorCode.TIMEOUT
        # Non-blocking: returns far under the default 30s budget the bug imposed.
        assert elapsed < 5.0


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
# CLI argparse plumbing
# =============================================================================


class TestCli:
    def test_acquire_requires_plan_id(self) -> None:
        result = run_script(SCRIPT_PATH, 'acquire')
        assert result.returncode != 0
        assert '--plan-id' in result.stderr or '--plan-id' in result.stdout

    def test_release_requires_plan_id(self) -> None:
        result = run_script(SCRIPT_PATH, 'release')
        assert result.returncode != 0
        assert '--plan-id' in result.stderr or '--plan-id' in result.stdout

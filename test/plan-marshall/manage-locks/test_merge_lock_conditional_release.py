#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for ``merge_lock.py`` fail-closed conditional release (``--require-stale``).

Contract under test (D1 — Main-anchored fail-closed staleness verdict and
conditional merge-lock release):

* **Removes only on ``stale``** — ``release --require-stale`` removes the lock ONLY
  when the recorded holder's main-anchored ``holder_staleness`` verdict is
  ``stale`` (main-anchored-dead AND no live worktree).
* **Fail-closed on ``fresh``** — a holder alive on main, alive in a (sibling)
  worktree, or mid-recovery (live worktree marker) yields ``fresh`` → the release
  REFUSES (``status: refused``, ``reason: holder_not_provably_dead``) with NO
  ``os.unlink``; the lock is left intact. This is the #948 sibling-worktree shape.
* **Fail-closed on ``unknown``** — when the main-anchored base cannot be resolved
  the verdict is ``unknown`` → the release REFUSES (ADR-009: evidence-absent is
  never treated as death).
* **Observed-file eviction arbitration** — the stale removal goes through the
  per-reclaimer sidecar rename + re-confirm (:func:`_evict_stale_lock`), never a
  blind ``os.unlink``, so a holder that goes live in the TOCTOU window (its file
  content changed) is not force-released.
* **Plain release unaffected** — without ``--require-stale`` the self-holder
  release removes the lock (holder == caller) and a foreign holder's lock is left
  intact — the existing behaviour is unchanged.
* **``check`` surfaces the verdict** — the non-mutating ``check`` action carries a
  ``staleness`` field on the ``held`` branch.

Isolation mirrors ``test_manage_locks_merge_lock.py``: every test runs against an
isolated ``PLAN_BASE_DIR`` staged under ``tmp_path`` so the lock, the FIFO queue,
and holder plan dirs resolve there rather than the real ``.plan`` tree.
"""

from __future__ import annotations

import sys as _sys
from argparse import Namespace
from pathlib import Path

import pytest

from conftest import load_script_module

merge_lock = load_script_module(
    'plan-marshall', 'manage-locks', 'merge_lock.py', 'merge_lock_conditional_under_test'
)

# The shared core owns holder_staleness / _main_plan_local_base; recover the SAME
# _locks_core instance merge_lock imported (not a fresh load_script_module copy)
# so a monkeypatch on its resolver is the one merge_lock's holder_staleness sees.
_locks_core = _sys.modules[merge_lock.holder_staleness.__module__]


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def isolated_base(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    """Stage an isolated PLAN_BASE_DIR under tmp_path (main stand-in).

    The lock resolves to ``<base>/merge.lock``, the FIFO queue to
    ``<base>/merge-queue.json``, holder plan dirs to ``<base>/plans/{holder}``,
    and holder worktrees to ``<base>/worktrees/{holder}``.
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
def _stub_title_tokens(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stub the three best-effort title-token seams so the conditional-release unit
    tests never spawn the real executor subprocess (the token surface is
    best-effort and out-of-scope for the lock-correctness assertions)."""
    monkeypatch.setattr(merge_lock, '_set_title_token', lambda _p, _state: None)
    monkeypatch.setattr(merge_lock, '_clear_title_token', lambda _p: None)
    monkeypatch.setattr(merge_lock, '_push_title_token', lambda _p, icon=None: None)


def _write_lock(lock_path: Path, holder: str) -> None:
    """Stage a held lock file recording ``holder`` (mirrors _try_atomic_create)."""
    lock_path.write_text(holder + '\n', encoding='utf-8')


def _make_live_plan(base: Path, plan_id: str) -> None:
    """Create a holder plan dir on main so the holder counts as LIVE (fresh)."""
    (base / 'plans' / plan_id).mkdir(parents=True, exist_ok=True)


def _make_worktree_live_plan(base: Path, plan_id: str) -> None:
    """Move the holder's plan dir into its worktree (executing) — the #948 shape."""
    (base / 'worktrees' / plan_id / '.plan' / 'local' / 'plans' / plan_id).mkdir(parents=True)


def _make_git_worktree(base: Path, plan_id: str) -> None:
    """Stage a genuine git-worktree marker (mid-recovery, plan dir moved out)."""
    worktree = base / 'worktrees' / plan_id
    worktree.mkdir(parents=True, exist_ok=True)
    (worktree / '.git').write_text(f'gitdir: /main/.git/worktrees/{plan_id}\n', encoding='utf-8')


def _release_require_stale(plan_id: str) -> dict:
    result: dict = merge_lock.run_release(Namespace(plan_id=plan_id, require_stale=True))
    return result


# =============================================================================
# release --require-stale — removes ONLY on a stale verdict
# =============================================================================


class TestConditionalReleaseStale:
    def test_removes_lock_when_holder_is_stale(self, isolated_base: dict) -> None:
        # Holder dead: no plan dir on main, no worktree, no live worktree marker
        # → verdict stale → the conditional release removes the lock.
        lock_path = isolated_base['lock_path']
        _write_lock(lock_path, 'dead-holder')

        result = _release_require_stale('dead-holder')

        assert result['status'] == 'success'
        assert result['action'] == 'released'
        assert result['staleness'] == 'stale'
        assert result['reclaimed_from'] == 'dead-holder'
        assert not lock_path.exists()

    def test_recovery_release_evicts_a_foreign_stale_holder(self, isolated_base: dict) -> None:
        # The recovery recipe: the CALLER releases a FOREIGN holder's stale lock
        # under its plan_id. A genuinely-dead foreign holder is evicted.
        lock_path = isolated_base['lock_path']
        _write_lock(lock_path, 'foreign-dead')

        result = _release_require_stale('foreign-dead')

        assert result['action'] == 'released'
        assert not lock_path.exists()


# =============================================================================
# release --require-stale — fail-closed on fresh / unknown
# =============================================================================


class TestConditionalReleaseFailClosed:
    def test_refuses_when_holder_alive_on_main(self, isolated_base: dict) -> None:
        # Holder alive on main → fresh → refuse fail-closed, lock left intact.
        base = isolated_base['base']
        lock_path = isolated_base['lock_path']
        _make_live_plan(base, 'live-holder')
        _write_lock(lock_path, 'live-holder')

        result = _release_require_stale('live-holder')

        assert result['status'] == 'refused'
        assert result['reason'] == 'holder_not_provably_dead'
        assert result['staleness'] == 'fresh'
        assert result['holder'] == 'live-holder'
        # No os.unlink — the live holder keeps its lock.
        assert lock_path.is_file()
        assert lock_path.read_text(encoding='utf-8').strip() == 'live-holder'

    def test_refuses_when_holder_alive_in_sibling_worktree(self, isolated_base: dict) -> None:
        # The #948 shape: the holder's plan dir lives in its (sibling) worktree —
        # absent on main, but ALIVE. A cwd-scoped enumeration would read it absent;
        # the main-anchored verdict is fresh → refuse, lock intact.
        base = isolated_base['base']
        lock_path = isolated_base['lock_path']
        _make_worktree_live_plan(base, 'wt-holder')
        _write_lock(lock_path, 'wt-holder')

        result = _release_require_stale('wt-holder')

        assert result['status'] == 'refused'
        assert result['staleness'] == 'fresh'
        assert lock_path.is_file()

    def test_refuses_when_holder_is_mid_recovery(self, isolated_base: dict) -> None:
        # dead-by-plan-dir but a genuine git-worktree marker is present →
        # mid-recovery → fresh → refuse (an interrupted move-back is not stale).
        base = isolated_base['base']
        lock_path = isolated_base['lock_path']
        _make_git_worktree(base, 'mid-rec-holder')
        _write_lock(lock_path, 'mid-rec-holder')

        result = _release_require_stale('mid-rec-holder')

        assert result['status'] == 'refused'
        assert result['staleness'] == 'fresh'
        assert lock_path.is_file()

    def test_refuses_when_verdict_unknown(self, isolated_base: dict, monkeypatch) -> None:
        # When the main-anchored base cannot be resolved the verdict is 'unknown'
        # (ADR-009 — evidence-absent is never treated as death) → refuse. Force the
        # underlying resolver to raise so holder_staleness returns 'unknown'; the
        # lock path itself still resolves (via marketplace_paths, not this seam).
        lock_path = isolated_base['lock_path']
        _write_lock(lock_path, 'any-holder')

        def _boom():
            raise RuntimeError('main-anchored base unresolvable')

        monkeypatch.setattr(_locks_core, '_main_plan_local_base', _boom)

        result = _release_require_stale('any-holder')

        assert result['status'] == 'refused'
        assert result['reason'] == 'holder_not_provably_dead'
        assert result['staleness'] == 'unknown'
        assert lock_path.is_file()

    def test_noop_success_when_no_lock_file(self, isolated_base: dict) -> None:
        # Nothing to release → idempotent noop success (no refusal, no unlink).
        result = _release_require_stale('dead-holder')

        assert result['status'] == 'success'
        assert result['action'] == 'noop'
        assert not isolated_base['lock_path'].exists()


# =============================================================================
# Observed-file eviction arbitration (_evict_stale_lock) — no blind unlink
# =============================================================================


class TestEvictStaleLockArbitration:
    def test_evicts_confirmed_stale_holder(self, isolated_base: dict) -> None:
        # The observed holder is exactly the recorded, still-stale holder → the
        # sidecar arbitration removes the lock and returns True.
        lock_path = isolated_base['lock_path']
        _write_lock(lock_path, 'dead-holder')

        assert merge_lock._evict_stale_lock(lock_path, 'dead-holder') is True
        assert not lock_path.exists()

    def test_refuses_when_observed_holder_mismatches_current_file(self, isolated_base: dict) -> None:
        # A concurrent reclaimer installed a DIFFERENT holder before this eviction
        # claimed the file: the renamed-away content ('other-holder') is not the
        # observed holder we decided to evict, so the sidecar is restored intact and
        # the eviction loses cleanly (False) — no blind unlink of the wrong file.
        lock_path = isolated_base['lock_path']
        _write_lock(lock_path, 'other-holder')

        assert merge_lock._evict_stale_lock(lock_path, 'stale-observed') is False
        # The lock is restored intact — the observed-file arbitration refused.
        assert lock_path.is_file()
        assert lock_path.read_text(encoding='utf-8').strip() == 'other-holder'

    def test_loses_cleanly_when_lock_already_gone(self, isolated_base: dict) -> None:
        # The path is already gone (a racing reclaimer claimed it a beat earlier) →
        # the rename raises FileNotFoundError → lose cleanly (False).
        lock_path = isolated_base['lock_path']
        assert not lock_path.exists()

        assert merge_lock._evict_stale_lock(lock_path, 'dead-holder') is False


# =============================================================================
# Plain release (no --require-stale) — the self-holder path is unaffected
# =============================================================================


class TestPlainReleaseUnaffected:
    def test_self_holder_release_still_removes_lock(self, isolated_base: dict) -> None:
        # The unconditional self-holder release (finalize's path) is unchanged: a
        # caller that IS the recorded holder removes the lock regardless of staleness.
        base = isolated_base['base']
        lock_path = isolated_base['lock_path']
        _make_live_plan(base, 'plan-a')  # holder is alive — plain release still frees it
        _write_lock(lock_path, 'plan-a')

        result = merge_lock.run_release(Namespace(plan_id='plan-a'))

        assert result['status'] == 'success'
        assert result['action'] == 'released'
        assert not lock_path.exists()

    def test_plain_foreign_holder_release_is_noop_not_refused(self, isolated_base: dict) -> None:
        # Without --require-stale a foreign holder's lock is a NOOP (not a staleness
        # refusal) and is left intact — the pre-existing behaviour.
        base = isolated_base['base']
        lock_path = isolated_base['lock_path']
        _make_live_plan(base, 'plan-a')
        _write_lock(lock_path, 'plan-a')

        result = merge_lock.run_release(Namespace(plan_id='plan-b'))

        assert result['status'] == 'success'
        assert result['action'] == 'noop'
        assert result['holder'] == 'plan-a'
        assert lock_path.is_file()


# =============================================================================
# check — surfaces the staleness verdict on the held branch
# =============================================================================


class TestCheckSurfacesStaleness:
    def test_check_held_reports_stale_verdict(self, isolated_base: dict) -> None:
        # A held lock whose holder is dead-with-no-worktree surfaces staleness=stale.
        _write_lock(isolated_base['lock_path'], 'dead-holder')

        result = merge_lock.run_check(Namespace(plan_id='querier'))

        assert result['status'] == 'held'
        assert result['holder_plan_id'] == 'dead-holder'
        assert result['staleness'] == 'stale'

    def test_check_held_reports_fresh_verdict(self, isolated_base: dict) -> None:
        # A held lock whose holder is alive on main surfaces staleness=fresh.
        base = isolated_base['base']
        _make_live_plan(base, 'live-holder')
        _write_lock(isolated_base['lock_path'], 'live-holder')

        result = merge_lock.run_check(Namespace(plan_id='querier'))

        assert result['status'] == 'held'
        assert result['staleness'] == 'fresh'

    def test_check_free_has_no_staleness_field(self, isolated_base: dict) -> None:
        # No lock file → free; there is no holder to evaluate, so no staleness field.
        result = merge_lock.run_check(Namespace(plan_id='querier'))

        assert result['status'] == 'free'
        assert 'staleness' not in result

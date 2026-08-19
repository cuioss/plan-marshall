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

from argparse import Namespace
from pathlib import Path

import pytest
from _manage_locks_merge_lock_fixtures import SCRIPT_PATH, _make_live_plan, _TokenRecorder, merge_lock

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
# Shared-core delegation guard — no re-implemented liveness / resolution / rmw
# =============================================================================


class TestSharedCoreDelegation:
    """The unified merge_lock builds on the shared coordination core — it imports
    ``holder_is_dead`` and ``rmw_json`` from ``_locks_core`` and
    ``resolve_main_anchored_path`` from ``marketplace_paths`` rather than
    re-implementing any. These guards fail if a parallel copy is ever
    reintroduced."""

    def test_imports_shared_liveness_predicate(self) -> None:
        # holder_is_dead must be imported from the shared core, not redefined.
        assert hasattr(merge_lock, 'holder_is_dead')

    def test_imports_shared_rmw_json(self) -> None:
        # The FIFO enqueue/dequeue runs through the shared rmw_json, not a
        # re-implemented serialized read-modify-write.
        assert hasattr(merge_lock, 'rmw_json')

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
    on a blocked admission, 🔒 (lock-owned) once the lock is held, and a clear on
    every release path. Every write is best-effort and placed OUTSIDE the O_EXCL
    check-then-act window (mirrors D6's build-phase pair)."""

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
        merge_lock._dequeue_fifo('plan-dead')
        _stub_title_tokens.set_states.clear()
        _stub_title_tokens.pushed_icons.clear()

        result = merge_lock.run_acquire(Namespace(plan_id='plan-b', timeout=5.0))
        assert result['reclaimed'] is True
        assert _stub_title_tokens.set_states == ['lock-owned']
        assert _stub_title_tokens.pushed_icons == [merge_lock._ICON_LOCK_OWNED]

    def test_blocked_acquire_surfaces_lock_waiting(
        self, isolated_base: dict, _stub_title_tokens: _TokenRecorder
    ) -> None:
        """A blocked admission against a live holder surfaces `lock-waiting` (⏳),
        never `lock-owned`. The token fires on the blocked return path — acquire no
        longer sleeps internally, so the surface is gated on the blocked outcome,
        not on a backoff poll."""
        merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        _make_live_plan(isolated_base['base'], 'plan-a')
        _stub_title_tokens.set_states.clear()
        _stub_title_tokens.pushed_icons.clear()

        result = merge_lock.run_acquire(Namespace(plan_id='plan-b', timeout=0.6))
        assert result['status'] == 'blocked'
        assert _stub_title_tokens.set_states == ['lock-waiting']
        assert _stub_title_tokens.pushed_icons == [merge_lock._ICON_LOCK_WAITING]
        assert 'lock-owned' not in _stub_title_tokens.set_states

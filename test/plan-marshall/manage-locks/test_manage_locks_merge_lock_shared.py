#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the unified ``manage-locks/merge_lock.py`` — the single main-anchored
merge-to-main serializer fronted by a FIFO admission queue.
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

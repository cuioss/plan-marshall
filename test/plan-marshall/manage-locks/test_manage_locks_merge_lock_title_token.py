#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the unified ``manage-locks/merge_lock.py`` — the single main-anchored
merge-to-main serializer fronted by a FIFO admission queue.
"""


from __future__ import annotations

from argparse import Namespace
from pathlib import Path

import pytest
from _manage_locks_merge_lock_fixtures import (
    _REAL_CLEAR_TITLE_TOKEN,
    _REAL_SET_TITLE_TOKEN,
    SCRIPT_PATH,
    _make_live_plan,
    _TokenRecorder,
    merge_lock,
)

from conftest import load_script_module

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


# =============================================================================
# Live-worktree reclaim guard — orphaned shell auto-reclaims, genuine
# mid-recovery worktree stays protected (strengthened holder_has_live_worktree)
# =============================================================================

class TestTitleTokenOwnerScoping:
    """The lock title surface writes and clears under the ``merge-lock`` owner.

    Ownership is what keeps this surface and a concurrent build bracket from
    clobbering each other: the lock's writes are stamped, and its clear is
    owner-scoped so a foreign live token survives it. Because the arbitration
    itself lives in ``manage-status``, the contract this surface owes is the
    constructed ARGV — the owner flag must actually reach the wire, which is why
    these assertions are made at the lowest subprocess primitive
    (``_run_executor``) rather than against a higher-level stub.
    """

    def test_set_stamps_the_merge_lock_owner_on_the_wire(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: list[tuple] = []
        monkeypatch.setattr(
            merge_lock, '_run_executor', lambda notation, *args: calls.append((notation, args))
        )

        _REAL_SET_TITLE_TOKEN('plan-a', merge_lock._STATE_LOCK_OWNED)

        assert calls[0][1] == (
            'title-token', 'set', '--plan-id', 'plan-a',
            '--state', 'lock-owned', '--owner', 'merge-lock',
        )

    def test_clear_is_scoped_to_the_merge_lock_owner_on_the_wire(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The clear carries ``--owner merge-lock``, so manage-status refuses it
        against a live ``build-hook``-owned token.

        Without the flag the clear would default to the ``cli`` owner and could
        neither retire this surface's own token nor be refused correctly — the
        flag's presence is the whole mechanism, so it is asserted explicitly.
        """
        calls: list[tuple] = []
        monkeypatch.setattr(
            merge_lock, '_run_executor', lambda notation, *args: calls.append((notation, args))
        )

        _REAL_CLEAR_TITLE_TOKEN('plan-a')

        assert calls[0][1] == (
            'title-token', 'clear', '--plan-id', 'plan-a', '--owner', 'merge-lock',
        )

    def test_owner_constant_is_in_the_manage_status_vocabulary(self) -> None:
        """The owner this surface stamps must be a member of the closed
        ``TITLE_TOKEN_OWNERS`` vocabulary manage-status validates against — an
        out-of-vocabulary owner would be argparse-rejected at every write."""
        core = load_script_module(
            'plan-marshall', 'manage-status', '_status_core.py', '_status_core_for_lock_owner'
        )
        assert merge_lock._TITLE_TOKEN_OWNER in core.TITLE_TOKEN_OWNERS


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
        merge_lock._dequeue_fifo('plan-dead')
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
        surfaces no ⏳ ``lock-waiting`` token."""
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

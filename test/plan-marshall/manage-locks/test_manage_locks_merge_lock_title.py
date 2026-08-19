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

# The shared core owns the [LOCK]-log resolver and the best-effort emission
# swallow. ``merge_lock`` does ``from _locks_core import log_lock_event``, so the
# function closes over the _locks_core module that ``merge_lock`` imported — that
# SAME module instance is recovered from the function's ``__module__`` (NOT a
# fresh ``load_script_module`` copy, which would be a different instance whose
# patches ``merge_lock`` never sees).
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
from toon_parser import parse_toon

from conftest import load_script_module, run_script

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

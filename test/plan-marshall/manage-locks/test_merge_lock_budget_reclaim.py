#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for ``merge_lock.py`` budget-aware reclaim (``budget-reclaim``).

Contract under test (PLAN-06 D2 — the waiter-side reclaim for the
orchestrator-layer ``merge_hold_budget_seconds`` bound):

* **Nothing to reclaim** — no lock file yields ``status: success``,
  ``action: nothing_to_reclaim`` (a concurrently-released lock is not an
  error).
* **Not due** — elapsed (``now - hold_start``) below budget yields
  ``status: success``, ``action: not_due``; the holder keeps its budget and
  the waiter keeps polling. The holder is NOT consulted beyond the verdict
  report.
* **Reclaims only a provably stale holder past budget** — elapsed at/past
  budget with a main-anchored-dead holder evicts through the observed-file
  sidecar arbitration (reusing the ``release --require-stale`` core) and
  dequeues the holder from the FIFO front.
* **Fail-closed on ``fresh`` past budget** — a live holder past budget is
  REFUSED (``status: refused``, ``reason: holder_not_provably_dead``) with
  NO unlink; the live-but-slow case belongs to the orchestrator's
  release + re-enqueue + escalate path, never to this verb.
* **Caller bugs refused before the lock is touched** — a non-finite or
  negative ``--hold-start`` (``invalid_hold_start``) and a non-finite or
  non-positive ``--hold-budget-seconds`` (``invalid_hold_budget``) return
  ``status: error`` and leave an existing lock intact.
* **Budget audit fields** — every branch carries ``elapsed_seconds`` and
  ``hold_budget_seconds`` so the caller can audit the budget arithmetic.

Isolation mirrors ``test_merge_lock_conditional_release.py``: every test runs
against an isolated ``PLAN_BASE_DIR`` staged under ``tmp_path`` so the lock,
the FIFO queue, and holder plan dirs resolve there rather than the real
``.plan`` tree.
"""

from __future__ import annotations

import time
from argparse import Namespace
from pathlib import Path

import pytest
from _manage_locks_fixtures import _make_live_plan, _write_lock

from conftest import load_script_module

merge_lock = load_script_module('plan-marshall', 'manage-locks', 'merge_lock.py', 'merge_lock_budget_under_test')


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def isolated_base(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    """Stage an isolated PLAN_BASE_DIR under tmp_path (main stand-in)."""
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
    """Stub the title-token seams (budget-reclaim suppresses the surface, but
    the stubs keep the unit tests off the real executor regardless)."""
    monkeypatch.setattr(merge_lock, '_set_title_token', lambda _p, _state: None)
    monkeypatch.setattr(merge_lock, '_clear_title_token', lambda _p: None)
    monkeypatch.setattr(merge_lock, '_push_title_token', lambda _p, icon=None: None)


def _reclaim(plan_id: str, hold_start: float, hold_budget_seconds: float) -> dict:
    result: dict = merge_lock.run_budget_reclaim(
        Namespace(plan_id=plan_id, hold_start=hold_start, hold_budget_seconds=hold_budget_seconds)
    )
    return result


# =============================================================================
# No lock / inside budget — no eviction
# =============================================================================


class TestBudgetReclaimNoOpBranches:
    def test_nothing_to_reclaim_when_lock_free(self, isolated_base: dict) -> None:
        result = _reclaim('waiter', time.time() - 7200.0, 3600.0)

        assert result['status'] == 'success'
        assert result['action'] == 'nothing_to_reclaim'
        assert result['hold_budget_seconds'] == 3600.0

    def test_not_due_inside_budget(self, isolated_base: dict) -> None:
        # A live holder inside its budget keeps it — the waiter keeps polling.
        base = isolated_base['base']
        lock_path = isolated_base['lock_path']
        _make_live_plan(base, 'slow-holder')
        _write_lock(lock_path, 'slow-holder')

        result = _reclaim('waiter', time.time(), 3600.0)

        assert result['status'] == 'success'
        assert result['action'] == 'not_due'
        assert result['holder'] == 'slow-holder'
        assert result['elapsed_seconds'] < 3600.0
        assert lock_path.exists()


# =============================================================================
# Past budget — stale reclaims, fresh refuses
# =============================================================================


class TestBudgetReclaimPastBudget:
    def test_reclaims_stale_holder_past_budget(self, isolated_base: dict) -> None:
        # Holder dead (no plan dir anywhere) and hold 3700s past a 3600s
        # budget → evicted through the shared stale-eviction core.
        lock_path = isolated_base['lock_path']
        _write_lock(lock_path, 'dead-holder')

        result = _reclaim('waiter', time.time() - 3700.0, 3600.0)

        assert result['status'] == 'success'
        assert result['action'] == 'released'
        assert result['reclaimed_from'] == 'dead-holder'
        assert result['elapsed_seconds'] >= 3600.0
        assert result['hold_budget_seconds'] == 3600.0
        assert not lock_path.exists()

    def test_refuses_fresh_holder_past_budget(self, isolated_base: dict) -> None:
        # A LIVE holder past budget is never force-released by this verb —
        # the live-but-slow case belongs to the orchestrator's release +
        # re-enqueue + escalate path.
        base = isolated_base['base']
        lock_path = isolated_base['lock_path']
        _make_live_plan(base, 'slow-live-holder')
        _write_lock(lock_path, 'slow-live-holder')

        result = _reclaim('waiter', time.time() - 7200.0, 3600.0)

        assert result['status'] == 'refused'
        assert result['reason'] == 'holder_not_provably_dead'
        assert result['elapsed_seconds'] >= 3600.0
        assert lock_path.exists()


# =============================================================================
# Caller bugs — refused before the lock is touched
# =============================================================================


class TestBudgetReclaimInvalidInput:
    def test_negative_hold_start_is_refused_and_leaves_lock_intact(self, isolated_base: dict) -> None:
        lock_path = isolated_base['lock_path']
        _write_lock(lock_path, 'dead-holder')

        result = _reclaim('waiter', -1.0, 3600.0)

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_hold_start'
        # The audit fields ride every branch, including refusals.
        assert result['elapsed_seconds'] == 0.0
        assert result['hold_budget_seconds'] == 3600.0
        assert lock_path.exists()

    def test_non_positive_budget_is_refused_and_leaves_lock_intact(self, isolated_base: dict) -> None:
        lock_path = isolated_base['lock_path']
        _write_lock(lock_path, 'dead-holder')

        result = _reclaim('waiter', time.time() - 10.0, 0.0)

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_hold_budget'
        assert result['elapsed_seconds'] >= 0.0
        assert result['hold_budget_seconds'] == 0.0
        assert lock_path.exists()

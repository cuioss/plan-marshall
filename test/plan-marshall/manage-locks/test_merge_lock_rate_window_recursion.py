#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``merge_lock.py`` ``rate-window`` verbs — the cross-plan claim on
ONE review bot's rate window, co-tenanting the merge-lock store.
"""


from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from _merge_lock_rate_window_fixtures import _claim, _make_live_plan, _read_store, _release

# =============================================================================
# Fixtures and helpers
# =============================================================================


@pytest.fixture
def isolated_base(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    """Stage an isolated PLAN_BASE_DIR under tmp_path.

    Mirrors ``test_manage_locks_merge_lock_*.py``'s fixture: the rate-window state
    lives in the SAME main-anchored store the FIFO admission queue uses, so both
    resolve to ``<base>/merge-queue.json``.
    """
    base = tmp_path / 'main' / '.plan' / 'local'
    (base / 'plans').mkdir(parents=True)
    monkeypatch.setenv('PLAN_BASE_DIR', str(base))
    return {
        'base': base,
        'lock_path': base / 'merge.lock',
        'queue_path': base / 'merge-queue.json',
    }


# =============================================================================
# Claim
# =============================================================================


class TestRateWindowClaim:
    def test_claim_records_holder_expiry_and_attempt(self, isolated_base: dict) -> None:
        result = _claim('plan-a')

        assert result['status'] == 'success', result
        assert result['action'] == 'claimed'
        assert result['bot_kind'] == 'coderabbit'
        assert result['pr_number'] == 42
        assert result['attempts'] == 1
        assert result['attempts_remaining'] == result['attempt_cap'] - 1
        assert result['seconds_remaining'] > 0

        record = _read_store(isolated_base['queue_path'])['rate_windows']['coderabbit']
        assert record['holder'] == 'plan-a'
        assert record['pr_number'] == 42
        assert record['attempts'] == 1

    def test_self_holder_reclaim_renews_in_place(self, isolated_base: dict) -> None:
        """Idempotent for the self-holder: no contention, no second record."""
        _make_live_plan(isolated_base['base'], 'plan-a')
        _claim('plan-a')

        second = _claim('plan-a')

        assert second['status'] == 'success', second
        assert second['action'] == 'renewed'
        assert second['reclaimed_from'] is None
        windows = _read_store(isolated_base['queue_path'])['rate_windows']
        assert list(windows) == ['coderabbit']
        assert windows['coderabbit']['holder'] == 'plan-a'

    def test_foreign_live_holder_with_open_window_blocks(self, isolated_base: dict) -> None:
        _make_live_plan(isolated_base['base'], 'plan-a')
        _claim('plan-a')

        blocked = _claim('plan-b')

        assert blocked['status'] == 'blocked', blocked
        assert blocked['reason'] == 'window_held_by_other_plan'
        assert blocked['holder'] == 'plan-a'
        assert blocked['seconds_remaining'] > 0
        # No mutation: plan-a still holds it.
        assert _read_store(isolated_base['queue_path'])['rate_windows']['coderabbit']['holder'] == 'plan-a'

    def test_dead_holder_is_reclaimed(self, isolated_base: dict) -> None:
        """holder_is_dead reclamation — plan-a never had a plan dir, so it is dead."""
        _claim('plan-a')

        reclaimed = _claim('plan-b')

        assert reclaimed['status'] == 'success', reclaimed
        assert reclaimed['action'] == 'reclaimed'
        assert reclaimed['reclaimed_from'] == 'plan-a'
        assert _read_store(isolated_base['queue_path'])['rate_windows']['coderabbit']['holder'] == 'plan-b'

    def test_expired_window_is_reclaimable_even_from_a_live_holder(self, isolated_base: dict) -> None:
        """The WINDOW, not the plan, is what the claim guards."""
        _make_live_plan(isolated_base['base'], 'plan-a')
        _claim('plan-a', window_seconds=-1.0)

        reclaimed = _claim('plan-b')

        assert reclaimed['status'] == 'success', reclaimed
        assert reclaimed['action'] == 'reclaimed'
        assert reclaimed['reclaimed_from'] == 'plan-a'

    def test_concurrent_claims_produce_exactly_one_holder(self, isolated_base: dict) -> None:
        """TOCTOU: the rmw_json critical section admits exactly one claimer."""
        plan_ids = [f'plan-{n}' for n in 'abcdef']
        for plan_id in plan_ids:
            _make_live_plan(isolated_base['base'], plan_id)

        with ThreadPoolExecutor(max_workers=len(plan_ids)) as pool:
            results = list(pool.map(_claim, plan_ids))

        successes = [r for r in results if r['status'] == 'success']
        blocked = [r for r in results if r['status'] == 'blocked']
        assert len(successes) == 1, results
        assert len(blocked) == len(plan_ids) - 1, results
        stored_holder = _read_store(isolated_base['queue_path'])['rate_windows']['coderabbit']['holder']
        assert stored_holder == successes[0]['holder']


# =============================================================================
# Recursion cap
# =============================================================================


class TestRecursionCap:
    def test_attempt_past_the_cap_is_refused_with_an_explicit_verdict(self, isolated_base: dict) -> None:
        _make_live_plan(isolated_base['base'], 'plan-a')
        cap = _claim('plan-a')['attempt_cap']

        for _ in range(cap - 1):
            assert _claim('plan-a')['status'] == 'success'

        refused = _claim('plan-a')

        assert refused['status'] == 'refused', refused
        assert refused['reason'] == 'recovery_cap_exhausted'
        assert refused['attempts'] == cap
        assert refused['attempt_cap'] == cap

    def test_refusal_mutates_nothing(self, isolated_base: dict) -> None:
        _make_live_plan(isolated_base['base'], 'plan-a')
        cap = _claim('plan-a')['attempt_cap']
        for _ in range(cap - 1):
            _claim('plan-a')
        before = _read_store(isolated_base['queue_path'])['rate_windows']['coderabbit']

        _claim('plan-a')

        assert _read_store(isolated_base['queue_path'])['rate_windows']['coderabbit'] == before

    def test_cap_survives_release_and_reclaim(self, isolated_base: dict) -> None:
        """Releasing between attempts must NOT reset the cap — the recovery
        sequence releases the window after every generated event, so a
        release-resets-counter would make the cap vacuous."""
        _make_live_plan(isolated_base['base'], 'plan-a')
        cap = _claim('plan-a')['attempt_cap']
        _release('plan-a')
        for _ in range(cap - 1):
            assert _claim('plan-a')['status'] == 'success'
            _release('plan-a')

        refused = _claim('plan-a')

        assert refused['status'] == 'refused', refused
        assert refused['reason'] == 'recovery_cap_exhausted'

    def test_cap_is_scoped_per_pr(self, isolated_base: dict) -> None:
        _make_live_plan(isolated_base['base'], 'plan-a')
        cap = _claim('plan-a', pr_number=42)['attempt_cap']
        for _ in range(cap - 1):
            _claim('plan-a', pr_number=42)
        assert _claim('plan-a', pr_number=42)['status'] == 'refused'

        other_pr = _claim('plan-a', pr_number=43)

        assert other_pr['status'] == 'success', other_pr
        assert other_pr['attempts'] == 1

#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: F811 — tests take the imported fixture as a parameter
"""Tests for the ``merge_lock.py`` ``rate-window`` verbs — the cross-plan claim on
ONE review bot's rate window, co-tenanting the merge-lock store.

Its sections, in order:

* Fixtures and helpers
* Claim
* Check (non-mutating) — the observable the recovery sequence polls
* Release
"""


from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from _merge_lock_rate_window_fixtures import (  # noqa: F401 — used by name, not by reference
    _check,
    _claim,
    _make_live_plan,
    _read_store,
    _release,
    isolated_base,
)

# =============================================================================
# Fixtures and helpers
# =============================================================================


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
# Check (non-mutating) — the observable the recovery sequence polls
# =============================================================================


class TestRateWindowCheck:
    def test_check_on_unclaimed_bot_reports_free(self, isolated_base: dict) -> None:
        result = _check('plan-a')

        assert result['status'] == 'free', result
        assert result['holder'] is None
        assert result['attempts'] == 0
        assert not isolated_base['queue_path'].exists()

    def test_unclaimed_check_carries_the_same_field_set_as_a_claimed_one(
        self, isolated_base: dict
    ) -> None:
        """Schema parity, derived from the claimed-branch population rather than a
        hand-listed key set: a consumer polling ``expired`` / ``seconds_remaining``
        must not KeyError just because the window was never claimed. The
        SKILL.md ``rate-window check`` contract lists those fields
        unconditionally."""
        unclaimed = _check('plan-a')
        _claim('plan-a')
        claimed = _check('plan-a')

        assert set(unclaimed) == set(claimed), unclaimed
        assert unclaimed['expired'] is True
        assert unclaimed['seconds_remaining'] == 0.0
        assert unclaimed['expires_at'] is None

    def test_check_does_not_mutate_the_store(self, isolated_base: dict) -> None:
        _claim('plan-a')
        before = _read_store(isolated_base['queue_path'])

        _check('plan-b')

        assert _read_store(isolated_base['queue_path']) == before

    def test_open_window_reports_not_expired_so_the_trigger_stays_gated(self, isolated_base: dict) -> None:
        """The trigger-comment fallback is reachable only after the window elapses.
        While the claim is unexpired, the observable the recovery sequence polls
        says so — a premature trigger has no branch to enter."""
        _claim('plan-a')

        result = _check('plan-a')

        assert result['status'] == 'held', result
        assert result['expired'] is False
        assert result['seconds_remaining'] > 0

    def test_elapsed_window_reports_expired(self, isolated_base: dict) -> None:
        _claim('plan-a', window_seconds=-1.0)

        result = _check('plan-a')

        assert result['status'] == 'free', result
        assert result['expired'] is True
        assert result['seconds_remaining'] == 0.0


# =============================================================================
# Release
# =============================================================================


class TestRateWindowRelease:
    def test_release_clears_the_holder_but_retains_the_attempt_count(self, isolated_base: dict) -> None:
        _claim('plan-a')

        result = _release('plan-a')

        assert result['status'] == 'success', result
        assert result['action'] == 'released'
        assert result['attempts'] == 1
        record = _read_store(isolated_base['queue_path'])['rate_windows']['coderabbit']
        assert record['holder'] == ''
        assert record['attempts'] == 1

    def test_release_of_an_unclaimed_window_is_a_noop(self, isolated_base: dict) -> None:
        result = _release('plan-a')

        assert result['status'] == 'success', result
        assert result['action'] == 'noop'
        assert result['holder'] is None

    def test_release_never_drops_a_foreign_holder(self, isolated_base: dict) -> None:
        _make_live_plan(isolated_base['base'], 'plan-a')
        _claim('plan-a')

        result = _release('plan-b')

        assert result['action'] == 'noop', result
        assert result['holder'] == 'plan-a'
        assert _read_store(isolated_base['queue_path'])['rate_windows']['coderabbit']['holder'] == 'plan-a'

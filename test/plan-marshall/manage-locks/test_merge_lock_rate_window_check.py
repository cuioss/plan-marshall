#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``merge_lock.py`` ``rate-window`` verbs — the cross-plan claim on
ONE review bot's rate window, co-tenanting the merge-lock store.
"""


from __future__ import annotations

import json
import time
from argparse import Namespace
from pathlib import Path

import pytest
from _merge_lock_rate_window_fixtures import (
    _check,
    _claim,
    _make_live_plan,
    _read_store,
    _release,
    merge_lock,
)

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


# =============================================================================
# Store co-tenancy — shares the STORE, never the MUTEX
# =============================================================================


class TestStoreIsolationFromTheMergeMutex:
    def test_claim_leaves_the_waiting_fifo_and_merge_lock_untouched(self, isolated_base: dict) -> None:
        """The converse of the sibling-key-preservation regression: a rate-window
        claim must not create, read, reclaim, or release ``merge.lock``, and must
        not mutate the ``waiting`` FIFO list."""
        merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        _make_live_plan(isolated_base['base'], 'plan-a')
        waiting_before = _read_store(isolated_base['queue_path'])['waiting']
        lock_before = isolated_base['lock_path'].read_text(encoding='utf-8')

        _claim('plan-b')
        _release('plan-b')

        store = _read_store(isolated_base['queue_path'])
        assert store['waiting'] == waiting_before
        assert isolated_base['lock_path'].read_text(encoding='utf-8') == lock_before
        # ...and the claim's own key landed alongside, not instead of, `waiting`.
        assert 'rate_windows' in store

    def test_claim_does_not_block_on_a_foreign_merge_lock_holder(self, isolated_base: dict) -> None:
        """A bot cooldown can never stall behind the merge serializer, and vice
        versa: plan-b claims a window while plan-a holds the merge mutex."""
        merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        _make_live_plan(isolated_base['base'], 'plan-a')

        result = _claim('plan-b')

        assert result['status'] == 'success', result
        assert isolated_base['lock_path'].read_text(encoding='utf-8').strip() == 'plan-a'


# =============================================================================
# Degraded-state tolerance
# =============================================================================


class TestDegradedState:
    @pytest.mark.parametrize('junk', ['not-a-mapping', 42, ['a', 'b']])
    def test_corrupt_rate_windows_value_is_rebuilt(self, isolated_base: dict, junk: object) -> None:
        isolated_base['queue_path'].write_text(
            json.dumps({'waiting': [], 'rate_windows': junk}), encoding='utf-8'
        )

        result = _claim('plan-a')

        assert result['status'] == 'success', result
        assert result['attempts'] == 1

    def test_malformed_record_fields_degrade_to_defaults(self, isolated_base: dict) -> None:
        isolated_base['queue_path'].write_text(
            json.dumps(
                {
                    'rate_windows': {
                        'coderabbit': {
                            'holder': 'plan-a',
                            'pr_number': 'not-an-int',
                            'expires_at': 'not-a-number',
                            'attempts': 'not-an-int',
                        }
                    }
                }
            ),
            encoding='utf-8',
        )

        result = _check('plan-b')

        assert result['status'] == 'free', result
        assert result['pr_number'] is None
        assert result['attempts'] == 0

    def test_corrupt_store_does_not_crash_the_merge_path(self, isolated_base: dict) -> None:
        isolated_base['queue_path'].write_text(
            json.dumps({'waiting': 'junk', 'rate_windows': 'junk'}), encoding='utf-8'
        )

        result = merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))

        assert result['status'] == 'success', result
        assert result['admission'] == 'admitted'


# =============================================================================
# Window expiry is wall-clock derived
# =============================================================================


def test_expires_at_is_derived_from_the_supplied_window_length(isolated_base: dict) -> None:
    before = time.time()

    result = _claim('plan-a', window_seconds=900.0)

    assert result['expires_at'] >= before + 900.0
    assert result['seconds_remaining'] <= 900.0

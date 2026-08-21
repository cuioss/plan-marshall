#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: F811 — tests take the imported fixture as a parameter
"""Tests for the ``merge_lock.py`` ``rate-window`` verbs — the cross-plan claim on
ONE review bot's rate window, co-tenanting the merge-lock store.
"""


from __future__ import annotations

import json
import time
from argparse import Namespace

import pytest
from _merge_lock_rate_window_fixtures import (  # noqa: F401 — a fixture is used by NAME, not by reference
    _check,
    _claim,
    _make_live_plan,
    _read_store,
    _release,
    isolated_base,
    merge_lock,
)

# =============================================================================
# Fixtures and helpers
# =============================================================================


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

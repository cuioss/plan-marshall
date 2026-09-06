#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2

"""Tests for the ``merge_lock.py`` ``rate-window`` verbs — the cross-plan claim on
ONE review bot's rate window, co-tenanting the merge-lock store.
"""


from __future__ import annotations

import json
import time
from argparse import Namespace

import pytest
from _merge_lock_rate_window_fixtures import (
    SCRIPT_PATH,
    _check,
    _claim,
    _make_live_plan,
    _read_store,
    _release,
    isolated_base,
    merge_lock,
)
from toon_parser import parse_toon

from conftest import run_script

# =============================================================================
# Fixtures and helpers
# =============================================================================


# =============================================================================
# Recursion cap
# =============================================================================


class TestRecursionCap:
    def test_sixth_attempt_is_admitted_and_the_seventh_is_refused(self, isolated_base: dict) -> None:
        """The shipped budget is SIX recovery attempts per ``(bot_kind, pr_number)``.

        The ordinals are stated as literals rather than derived from the returned
        ``attempt_cap``, and that is the point of the test: every sibling test in
        this class derives its bound from whatever the code ships, so all of them
        pass against ANY cap — including a cap too small for the recovery sequence
        to ever complete. Only a test that names the number can fail when the
        number is wrong, which is why this one carries the boundary and the others
        carry the semantics.
        """
        _make_live_plan(isolated_base['base'], 'plan-a')

        admitted = [_claim('plan-a') for _ in range(6)]

        assert [r['status'] for r in admitted] == ['success'] * 6, admitted
        assert admitted[-1]['attempts'] == 6
        assert admitted[-1]['attempt_cap'] == 6
        assert admitted[-1]['attempts_remaining'] == 0

        before = _read_store(isolated_base['queue_path'])['rate_windows']['coderabbit']
        seventh = _claim('plan-a')

        assert seventh['status'] == 'refused', seventh
        assert seventh['reason'] == 'recovery_cap_exhausted'
        assert seventh['attempts'] == 6
        assert seventh['attempt_cap'] == 6
        assert _read_store(isolated_base['queue_path'])['rate_windows']['coderabbit'] == before

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

        result = _check('plan-b', pr_number=42)

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
# CLI surface — what the SHIPPED command line decides
# =============================================================================
#
# Every test above drives `run_rate_window` with a hand-built Namespace, which
# bypasses argparse entirely: it asserts the SEMANTICS of whatever cap it passes
# in, and passes just as happily against a shipped default of 2 as of 6. The
# default a caller actually gets when it omits the flag is decided by the parser
# and is observable ONLY through the real entry point, so these tests go through
# the CLI.


class TestRateWindowCli:
    def test_shipped_attempt_cap_default_is_six(self, isolated_base: dict) -> None:
        """Omitting ``--attempt-cap`` must yield a budget of SIX.

        The literal is the assertion. The recursion cap exists to let the
        automatic-review recovery sequence run to completion before it escalates,
        so a default too small silently strands that sequence — and no
        cap-derived test above can see it, because each derives its bound from
        the shipped value and would agree with any number at all.
        """
        result = run_script(
            SCRIPT_PATH, 'rate-window', 'claim',
            '--plan-id', 'plan-a', '--bot-kind', 'coderabbit', '--pr-number', '42',
            env_overrides={'PLAN_BASE_DIR': str(isolated_base['base'])},
        )

        assert result.returncode == 0, result.stderr
        parsed = parse_toon(result.stdout)
        assert parsed['status'] == 'success', parsed
        assert parsed['attempt_cap'] == 6, parsed
        assert parsed['attempts_remaining'] == 5, parsed

    def test_help_advertises_attempt_cap_and_its_default(self) -> None:
        """``--help`` is the surface an operator reads before choosing a cap."""
        result = run_script(SCRIPT_PATH, 'rate-window', '--help')

        assert result.returncode == 0, result.stderr
        # argparse hard-wraps help text at the terminal width, so a wrap between
        # any two words of '(default: 6)' would break a raw substring match.
        advertised = ' '.join(result.stdout.split())
        assert '--attempt-cap' in advertised, advertised
        assert '(default: 6)' in advertised, advertised

    def test_claim_refuses_a_missing_pr_number(self, isolated_base: dict) -> None:
        """No PR means no counter to count against — refuse rather than guess.

        The flag used to default to a sentinel PR that matched no stored record,
        so an omitted ``--pr-number`` read as a fresh budget and GRANTED a claim
        against a counter that belonged to nothing.
        """
        result = run_script(
            SCRIPT_PATH, 'rate-window', 'claim',
            '--plan-id', 'plan-a', '--bot-kind', 'coderabbit',
            env_overrides={'PLAN_BASE_DIR': str(isolated_base['base'])},
        )

        parsed = parse_toon(result.stdout)
        assert parsed['status'] == 'error', parsed
        assert parsed['error_code'] == 'INVALID_INPUT', parsed
        assert '--pr-number' in parsed['error'], parsed
        # The refusal precedes the store entirely — nothing was read or written.
        assert not isolated_base['queue_path'].exists()

    def test_check_refuses_a_missing_pr_number(self, isolated_base: dict) -> None:
        """``check`` counts against the caller's PR too, so it refuses identically."""
        result = run_script(
            SCRIPT_PATH, 'rate-window', 'check',
            '--plan-id', 'plan-a', '--bot-kind', 'coderabbit',
            env_overrides={'PLAN_BASE_DIR': str(isolated_base['base'])},
        )

        parsed = parse_toon(result.stdout)
        assert parsed['status'] == 'error', parsed
        assert parsed['error_code'] == 'INVALID_INPUT', parsed
        assert '--pr-number' in parsed['error'], parsed
        assert not isolated_base['queue_path'].exists()

    def test_release_still_accepts_an_absent_pr_number(self, isolated_base: dict) -> None:
        """Matched negative control for the two refusals above.

        The guard must be scoped to the verbs that consult the per-PR counter. A
        blanket requirement would break ``release``, which drops the holder while
        RETAINING whatever count is stored and so has no PR to count against.
        """
        result = run_script(
            SCRIPT_PATH, 'rate-window', 'release',
            '--plan-id', 'plan-a', '--bot-kind', 'coderabbit',
            env_overrides={'PLAN_BASE_DIR': str(isolated_base['base'])},
        )

        assert result.returncode == 0, result.stderr
        parsed = parse_toon(result.stdout)
        assert parsed['status'] == 'success', parsed
        assert parsed['action'] == 'noop', parsed


# =============================================================================
# Window expiry is wall-clock derived
# =============================================================================


def test_expires_at_is_derived_from_the_supplied_window_length(isolated_base: dict) -> None:
    before = time.time()

    result = _claim('plan-a', window_seconds=900.0)

    assert result['expires_at'] >= before + 900.0
    assert result['seconds_remaining'] <= 900.0

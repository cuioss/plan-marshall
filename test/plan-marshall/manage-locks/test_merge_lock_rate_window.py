#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2

"""Tests for the ``merge_lock.py`` ``rate-window`` verbs — the cross-plan claim on
ONE review bot's rate window, co-tenanting the merge-lock store — and for the
``poll-delay`` verb, the storeless jitter computation a caller waits after that
window elapses.
"""


from __future__ import annotations

import json
import time
from argparse import Namespace
from pathlib import Path

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


# =============================================================================
# poll-delay — a bounded jittered delay the CALLER waits
# =============================================================================
#
# The verb's whole value is a RANGE, and a range assertion is the easiest thing in
# this corpus to write vacuously: `300 <= delay <= 1200` holds just as well against
# an implementation that hard-codes 600 and never draws anything at all. So the
# range is pinned from two directions that fail for different reasons — through the
# `rng` injection seam, where the drawn value is known exactly and an ignored seam
# is structurally detectable, and over a real sample, where the SPREAD is what is
# measured and a degenerate constant cannot survive.
#
# The sample size below is 200. A uniform draw over a continuous interval repeats a
# value with probability zero, so "at least two distinct values" is not a flaky
# statistical bet — it is a property that only a broken (constant) implementation
# can fail.
_SAMPLE_SIZE = 200


def _poll_delay(min_seconds: float = 300.0, max_seconds: float = 1200.0) -> dict:
    """Drive ``run_poll_delay`` with a hand-built Namespace (argparse bypassed).

    Like the ``rate-window`` helpers above, this sees whatever bounds it is handed
    — never the ones the SHIPPED command line supplies when a caller omits the
    flags. Those are asserted in :class:`TestPollDelayCli`.
    """
    result: dict = merge_lock.run_poll_delay(
        Namespace(min_seconds=min_seconds, max_seconds=max_seconds)
    )
    return result


class TestPollDelayInjectionSeam:
    """``compute_poll_delay``'s ``rng`` parameter is the determinism seam.

    Without it the draw is observable only statistically, and a test that can only
    observe a distribution cannot assert which number came back.
    """

    def test_the_injected_draw_is_what_comes_back(self) -> None:
        assert merge_lock.compute_poll_delay(300.0, 1200.0, rng=lambda low, _high: low) == 300.0
        assert merge_lock.compute_poll_delay(300.0, 1200.0, rng=lambda _low, high: high) == 1200.0

    def test_an_out_of_range_injected_draw_comes_back_unclamped(self) -> None:
        """Matched negative control for every range assertion in this section.

        The injected callable returns a value no bound admits. Were ``rng`` ignored
        — dropped for a hard-wired ``random.uniform`` call inside the function — the
        result would land inside [300, 1200] and this assertion would fail. That is
        what makes the sibling range tests non-vacuous: they measure a draw the seam
        actually produced, not a constant the implementation could have baked in.

        It also pins that the function does not clamp: an out-of-range draw is
        returned as-is rather than pulled to the nearest bound, so `run_poll_delay`'s
        bounds validation is the only thing standing between a caller and a bad
        number — which is why that validation is tested as its own class below.
        """
        assert merge_lock.compute_poll_delay(300.0, 1200.0, rng=lambda _low, _high: -1.0) == -1.0

    def test_the_bounds_are_forwarded_to_the_injected_callable(self) -> None:
        """Custom bounds are honoured by being HANDED to the draw, not post-filtered."""
        seen: list[tuple[float, float]] = []

        def _record(low: float, high: float) -> float:
            seen.append((low, high))
            return low

        merge_lock.compute_poll_delay(45.0, 90.0, rng=_record)

        assert seen == [(45.0, 90.0)]

    def test_the_default_draw_delegates_to_random_uniform(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """``rng=None`` means ``random.uniform``, over the caller's own bounds.

        Asserted deterministically rather than inferred from the sample below: the
        sample can show that SOME spread exists, only this can show WHICH callable
        produced it and that the bounds reached it intact.
        """
        seen: list[tuple[float, float]] = []

        def _fake_uniform(low: float, high: float) -> float:
            seen.append((low, high))
            return 777.0

        monkeypatch.setattr(merge_lock.random, 'uniform', _fake_uniform)

        assert merge_lock.compute_poll_delay(300.0, 1200.0) == 777.0
        assert seen == [(300.0, 1200.0)]


class TestPollDelayRange:
    def test_every_draw_of_a_large_sample_lies_within_the_default_bounds(self) -> None:
        sample = [_poll_delay()['delay_seconds'] for _ in range(_SAMPLE_SIZE)]

        out_of_range = [d for d in sample if not 300.0 <= d <= 1200.0]
        assert out_of_range == [], out_of_range

    def test_the_sample_is_not_a_degenerate_constant(self) -> None:
        """A range assertion alone passes against a hard-coded 600.

        This is the assertion that constant cannot pass, and it is why the range
        test above measures anything: together they say "inside the bounds AND
        actually varying", which is the property the caller depends on.
        """
        sample = [_poll_delay()['delay_seconds'] for _ in range(_SAMPLE_SIZE)]

        assert len(set(sample)) > 1, sample[:5]

    def test_custom_bounds_are_honoured_end_to_end(self) -> None:
        sample = [_poll_delay(10.0, 20.0)['delay_seconds'] for _ in range(_SAMPLE_SIZE)]

        out_of_range = [d for d in sample if not 10.0 <= d <= 20.0]
        assert out_of_range == [], out_of_range
        # ...and the narrow range is the one drawn from, not the shipped range
        # filtered down to it: no draw may even reach the 300-second default floor.
        assert max(sample) < 300.0
        assert len(set(sample)) > 1, sample[:5]

    def test_the_payload_echoes_the_range_it_drew_from(self) -> None:
        """A consumer reading only the payload must be able to see the bounds."""
        result = _poll_delay(10.0, 20.0)

        assert result['status'] == 'success', result
        assert result['min_seconds'] == 10.0, result
        assert result['max_seconds'] == 20.0, result

    def test_equal_bounds_collapse_to_that_single_value(self) -> None:
        """``min == max`` is a legal degenerate range, not an inverted pair."""
        result = _poll_delay(42.0, 42.0)

        assert result['status'] == 'success', result
        assert result['delay_seconds'] == 42.0, result


class TestPollDelayBoundsRefusals:
    def test_inverted_bounds_are_refused_rather_than_swapped(self) -> None:
        """A swap would return a plausible delay from a range nobody asked for.

        Two things are asserted, and the second is the one that distinguishes a
        refusal from a silent correction: no ``delay_seconds`` is produced at all,
        and the echoed bounds are the caller's own, still in the caller's order.
        """
        result = _poll_delay(1200.0, 300.0)

        assert result['status'] == 'error', result
        assert result['error_code'] == 'INVALID_INPUT', result
        assert 'delay_seconds' not in result, result
        assert result['min_seconds'] == 1200.0, result
        assert result['max_seconds'] == 300.0, result

    @pytest.mark.parametrize(
        ('min_seconds', 'max_seconds'),
        [
            (-300.0, 1200.0),  # negative floor, otherwise well-ordered
            (300.0, -1200.0),  # negative ceiling (and inverted — negativity wins)
            (-1200.0, -300.0),  # both negative, correctly ordered
        ],
    )
    def test_negative_bounds_are_refused(self, min_seconds: float, max_seconds: float) -> None:
        """A negative bound does not stay inside this function as an odd number.

        ``delay_seconds`` is interpolated straight into the caller's ``sleep``
        command, so a negative draw leaves the verb as a malformed shell command at
        the one site that consumes it. The third case is the one an
        ordering-only guard misses entirely: ``-1200 <= -300`` is well-ordered.
        """
        result = _poll_delay(min_seconds, max_seconds)

        assert result['status'] == 'error', result
        assert result['error_code'] == 'INVALID_INPUT', result
        assert 'non-negative' in result['error'], result
        assert 'delay_seconds' not in result, result

    def test_a_zero_floor_is_still_accepted(self) -> None:
        """Matched negative control for the refusals above.

        The guard rejects NEGATIVE bounds, not FALSY ones. A ``not min_seconds``
        style check would pass every case above while refusing this legitimate
        zero floor — so without this test the guard could be written wrong and
        stay green.
        """
        result = _poll_delay(0.0, 5.0)

        assert result['status'] == 'success', result
        assert 0.0 <= result['delay_seconds'] <= 5.0, result


# The tests above drive `run_poll_delay` with a hand-built Namespace, which bypasses
# argparse: each asserts the semantics of whatever bounds it passes in, and would
# pass just as happily against shipped defaults of 1 and 2 seconds. The range a
# caller actually gets when it omits both flags is decided by the parser and is
# observable ONLY through the real entry point.


class TestPollDelayCli:
    def test_shipped_default_bounds_are_five_to_twenty_minutes(
        self, tmp_path: Path
    ) -> None:
        """Omitting both flags must yield the 300-1200 second range.

        The literals are the assertion. Every sibling test derives its bounds from
        what it passed in, so all of them agree with any defaults at all — only a
        test that names the numbers can fail when the numbers are wrong.
        """
        result = run_script(
            SCRIPT_PATH, 'poll-delay',
            env_overrides={'PLAN_BASE_DIR': str(tmp_path)},
        )

        assert result.returncode == 0, result.stderr
        parsed = parse_toon(result.stdout)
        assert parsed['status'] == 'success', parsed
        assert float(parsed['min_seconds']) == 300.0, parsed
        assert float(parsed['max_seconds']) == 1200.0, parsed
        assert 300.0 <= float(parsed['delay_seconds']) <= 1200.0, parsed

    def test_help_advertises_both_bounds_and_their_defaults(self) -> None:
        """``--help`` is the surface an operator reads before choosing a range."""
        result = run_script(SCRIPT_PATH, 'poll-delay', '--help')

        assert result.returncode == 0, result.stderr
        # argparse hard-wraps help text at the terminal width, so a wrap between
        # any two words of '(default: 300.0)' would break a raw substring match.
        advertised = ' '.join(result.stdout.split())
        assert '--min-seconds' in advertised, advertised
        assert '--max-seconds' in advertised, advertised
        assert '(default: 300.0)' in advertised, advertised
        assert '(default: 1200.0)' in advertised, advertised

    def test_the_shipped_cli_refuses_a_negative_bound(self, tmp_path: Path) -> None:
        """The guard must be reachable from the command line a human types.

        ``--min-seconds=-300`` uses the ``=`` form deliberately: a bare
        ``--min-seconds -300`` leans on argparse's negative-number heuristic, which
        is a property of the parser's option set rather than of this verb.
        """
        result = run_script(
            SCRIPT_PATH, 'poll-delay', '--min-seconds=-300',
            env_overrides={'PLAN_BASE_DIR': str(tmp_path)},
        )

        parsed = parse_toon(result.stdout)
        assert parsed['status'] == 'error', parsed
        assert parsed['error_code'] == 'INVALID_INPUT', parsed
        assert 'delay_seconds' not in parsed, parsed

    def test_the_shipped_cli_takes_no_plan_id(self, tmp_path: Path) -> None:
        """``poll-delay`` touches no state, so it declares no ``--plan-id``.

        The absence is the contract, not an omission: a pure computation that
        accepted a plan identifier would invite a reader to assume it reads or
        writes that plan's store. Asserted against the parser, which is the only
        place the flag set is real.
        """
        result = run_script(
            SCRIPT_PATH, 'poll-delay', '--plan-id', 'plan-a',
            env_overrides={'PLAN_BASE_DIR': str(tmp_path)},
        )

        assert result.returncode != 0, result.stdout
        assert '--plan-id' in result.stderr, result.stderr

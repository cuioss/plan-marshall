#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""A budgeted caller of ``rate-window wait`` ends, on the expiry or on its budget.

The consumer of ``rate-window wait`` holds a total budget in whole seconds and
re-issues the bounded call until the window has expired or the budget is spent.
Its budget defaults to the same length as the window a claim gets when the bot's
notice stated no reset time. These tests drive the verb the way that consumer
does, with injected clocks, and pin three things:

* a claim on the default window expires inside the default budget;
* a window longer than the budget spends the budget with the window still open;
* a call that reports ``timed_out`` reports a ``waited_seconds`` no smaller than
  the bound it ran under, which is what makes every re-issue lower the budget.
"""

from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

from _merge_lock_rate_window_fixtures import (
    _DEFAULT_ATTEMPT_CAP,
    isolated_base,
    merge_lock,
)

#: The instant the claim was made, in epoch seconds.
_CLAIMED_AT = 2_000_000_000.0

#: Seconds between the claim and the first wait call of the consumer.
_HAND_BACK_SECONDS = 5.0

#: The consumer's default total budget, in seconds.
_DEFAULT_BUDGET_SECONDS = 3600

#: A stated window longer than the default budget, in seconds.
_LONG_WINDOW_SECONDS = 2 * _DEFAULT_BUDGET_SECONDS

_PR = 42


class _FakeTime:
    """A wall clock and a monotonic clock that advance only when ``sleep`` is called."""

    def __init__(self, wall_start: float) -> None:
        self._wall_start = wall_start
        self.elapsed = 0.0

    def sleep(self, seconds: float) -> None:
        self.elapsed += seconds

    def clock(self) -> float:
        return self.elapsed

    def wall_clock(self) -> float:
        return self._wall_start + self.elapsed


def _store_window(queue_path: Path, window_seconds: float) -> float:
    """Store a claim made at ``_CLAIMED_AT`` on a window of ``window_seconds``; return its expiry."""
    expires_at: float = _CLAIMED_AT + window_seconds
    queue_path.write_text(
        json.dumps(
            {
                'waiting': [],
                'rate_windows': {
                    'coderabbit': {
                        'holder': 'plan-a',
                        'pr_number': _PR,
                        'expires_at': expires_at,
                        'attempts': 1,
                        'attempts_by_pr': {str(_PR): 1},
                    }
                },
            }
        ),
        encoding='utf-8',
    )
    return expires_at


def _wait(fake: _FakeTime, wait_seconds: float) -> dict:
    """Issue one bounded wait with no grace period, as the consumer does."""
    result: dict = merge_lock._run_rate_window_wait(
        Namespace(
            action='wait',
            plan_id='plan-a',
            bot_kind='coderabbit',
            pr_number=_PR,
            attempt_cap=_DEFAULT_ATTEMPT_CAP,
            grace_seconds=0.0,
            wait_seconds=wait_seconds,
            interval_seconds=15.0,
        ),
        sleep=fake.sleep,
        clock=fake.clock,
        wall_clock=fake.wall_clock,
    )
    return result


def _spend(fake: _FakeTime, budget_seconds: int) -> tuple[dict, int, list[tuple[float, int]]]:
    """Re-issue the bounded wait until the window has expired or the budget is spent.

    Returns the last return, the budget left, and the ``(bound, waited_seconds)`` pair
    of every call that reported ``timed_out``. The bound is the smaller of the
    requested seconds and the verb's per-call ceiling.
    """
    remaining = budget_seconds
    timed_out_calls: list[tuple[float, int]] = []
    while True:
        bound = min(float(remaining), merge_lock._RATE_WINDOW_WAIT_CEILING_SECONDS)
        result = _wait(fake, float(remaining))
        if not result['timed_out']:
            return result, remaining, timed_out_calls
        timed_out_calls.append((bound, result['waited_seconds']))
        remaining -= result['waited_seconds']
        if remaining <= 0:
            return result, remaining, timed_out_calls


def test_the_default_window_expires_inside_the_default_budget(isolated_base: dict) -> None:
    """The literals are the assertion: both defaults are one hour."""
    assert merge_lock._DEFAULT_WINDOW_SECONDS == _DEFAULT_BUDGET_SECONDS

    expires_at = _store_window(isolated_base['queue_path'], merge_lock._DEFAULT_WINDOW_SECONDS)
    fake = _FakeTime(_CLAIMED_AT + _HAND_BACK_SECONDS)

    result, remaining, _timed_out_calls = _spend(fake, _DEFAULT_BUDGET_SECONDS)

    assert result['timed_out'] is False, result
    assert result['expired'] is True, result
    assert remaining > 0, remaining
    assert fake.wall_clock() >= expires_at
    assert fake.elapsed <= _DEFAULT_BUDGET_SECONDS, fake.elapsed


def test_a_window_longer_than_the_budget_spends_it_with_the_window_open(isolated_base: dict) -> None:
    """Matched control: the same clock and budget, against a window that outlasts them."""
    _store_window(isolated_base['queue_path'], _LONG_WINDOW_SECONDS)
    fake = _FakeTime(_CLAIMED_AT + _HAND_BACK_SECONDS)

    result, remaining, _timed_out_calls = _spend(fake, _DEFAULT_BUDGET_SECONDS)

    assert result['timed_out'] is True, result
    assert result['expired'] is False, result
    assert remaining <= 0, remaining


def test_every_timed_out_call_reports_at_least_the_bound_it_ran_under(isolated_base: dict) -> None:
    """Each re-issue therefore lowers a whole-second budget, and the last one spends it."""
    _store_window(isolated_base['queue_path'], _LONG_WINDOW_SECONDS)
    fake = _FakeTime(_CLAIMED_AT + _HAND_BACK_SECONDS)

    _result, _remaining, timed_out_calls = _spend(fake, _DEFAULT_BUDGET_SECONDS)

    assert len(timed_out_calls) > 1, timed_out_calls
    assert all(waited >= bound >= 1 for bound, waited in timed_out_calls), timed_out_calls
    assert sum(waited for _bound, waited in timed_out_calls) >= _DEFAULT_BUDGET_SECONDS, timed_out_calls

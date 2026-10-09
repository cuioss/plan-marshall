#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""A budgeted caller of ``rate-window wait`` reaches the wake on the default window.

The consumer of ``rate-window wait`` holds a total budget and re-issues the bounded
call until the budget is spent. Its budget defaults to the same length as the
window a claim gets when the bot's notice stated no reset time. These tests drive
the verb the way that consumer does, with injected clocks, and pin the two ways
the calls can be sequenced:

* the window waited with no grace period inside the budget, then the grace period
  waited under a bound of its own — the wake is always reached;
* the grace period waited inside the budget — the budget is spent before the wake
  instant although the window has expired.

The second case is the control for the first: it shows the budget the first case
survives is one the other sequencing does not.
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

#: The largest grace period the jitter draw returns by default, in seconds.
_MAX_GRACE_SECONDS = 1200

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


def _store_default_window(queue_path: Path) -> float:
    """Store a claim made at ``_CLAIMED_AT`` on the verb's default window; return its expiry."""
    expires_at: float = _CLAIMED_AT + merge_lock._DEFAULT_WINDOW_SECONDS
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


def _spend(fake: _FakeTime, *, grace_seconds: float, budget_seconds: int) -> tuple[dict, int]:
    """Re-issue the bounded wait until it reports the wake or the budget is spent.

    Returns the last return and the budget left, charging ``waited_seconds`` per call
    as the consumer does.
    """
    remaining = budget_seconds
    while True:
        result: dict = merge_lock._run_rate_window_wait(
            Namespace(
                action='wait',
                plan_id='plan-a',
                bot_kind='coderabbit',
                pr_number=_PR,
                attempt_cap=_DEFAULT_ATTEMPT_CAP,
                grace_seconds=grace_seconds,
                wait_seconds=float(remaining),
                interval_seconds=15.0,
            ),
            sleep=fake.sleep,
            clock=fake.clock,
            wall_clock=fake.wall_clock,
        )
        remaining -= result['waited_seconds']
        if not result['timed_out'] or remaining <= 0:
            return result, remaining


def test_the_default_window_expires_inside_the_default_budget(isolated_base: dict) -> None:
    """The literals are the assertion: both defaults are one hour."""
    assert merge_lock._DEFAULT_WINDOW_SECONDS == _DEFAULT_BUDGET_SECONDS

    expires_at = _store_default_window(isolated_base['queue_path'])
    fake = _FakeTime(_CLAIMED_AT + _HAND_BACK_SECONDS)

    result, remaining = _spend(fake, grace_seconds=0.0, budget_seconds=_DEFAULT_BUDGET_SECONDS)

    assert result['timed_out'] is False, result
    assert result['expired'] is True, result
    assert remaining > 0, remaining
    assert fake.wall_clock() >= expires_at


def test_the_grace_is_then_reached_under_a_bound_of_its_own(isolated_base: dict) -> None:
    expires_at = _store_default_window(isolated_base['queue_path'])
    fake = _FakeTime(_CLAIMED_AT + _HAND_BACK_SECONDS)
    _spend(fake, grace_seconds=0.0, budget_seconds=_DEFAULT_BUDGET_SECONDS)

    result, _remaining = _spend(fake, grace_seconds=float(_MAX_GRACE_SECONDS), budget_seconds=_MAX_GRACE_SECONDS)

    assert result['timed_out'] is False, result
    assert result['wake_at'] == expires_at + _MAX_GRACE_SECONDS, result
    assert fake.elapsed <= _DEFAULT_BUDGET_SECONDS + _MAX_GRACE_SECONDS, fake.elapsed


def test_a_grace_charged_to_the_budget_spends_it_before_the_wake(isolated_base: dict) -> None:
    """Matched control: the same store and clock, with the grace inside the budget."""
    _store_default_window(isolated_base['queue_path'])
    fake = _FakeTime(_CLAIMED_AT + _HAND_BACK_SECONDS)

    result, remaining = _spend(fake, grace_seconds=300.0, budget_seconds=_DEFAULT_BUDGET_SECONDS)

    assert result['timed_out'] is True, result
    assert remaining <= 0, remaining
    # The window itself has expired: the budget ran out on the grace period alone.
    assert result['expired'] is True, result

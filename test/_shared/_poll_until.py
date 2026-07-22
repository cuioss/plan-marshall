# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared bounded-poll helper for tests that wait on an asynchronous side effect.

Tests that drive a detached or reparented child process cannot observe its
completion synchronously, so they poll for the effect the child produces. Every
such wait MUST be bounded and diagnosable per ADR-011: an unbounded loop hangs
the suite, and a bare ``assert effect_happened`` after an ad-hoc loop reports
"it did not happen" without saying how long it waited.

``poll_until`` is the single implementation of that pattern. It takes an
explicit predicate, an explicit bound, and an explicit interval, and raises an
``AssertionError`` naming the bound when the predicate never became true.
"""

from __future__ import annotations

import time
from collections.abc import Callable

#: Default polling cadence. Small enough that a fast effect is observed almost
#: immediately, large enough not to spin the CPU while waiting.
DEFAULT_INTERVAL_SECONDS = 0.05


def poll_until(
    predicate: Callable[[], bool],
    *,
    timeout_seconds: float,
    interval_seconds: float = DEFAULT_INTERVAL_SECONDS,
    description: str = 'condition',
) -> None:
    """Block until ``predicate()`` is true, or fail once ``timeout_seconds`` elapses.

    Args:
        predicate: Zero-argument callable polled until it returns truthy.
        timeout_seconds: Upper bound on the total wait. Always explicit — there
            is deliberately no default, so every caller states its own bound.
        interval_seconds: Delay between successive predicate evaluations.
        description: Human-readable name of what is being waited for, used in
            the timeout message so a failure is diagnosable without a debugger.

    Raises:
        AssertionError: If the predicate is still false when the bound expires.
    """
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(interval_seconds)
    # One final evaluation: the predicate may have become true during the last
    # sleep, and failing without re-checking would be a spurious timeout.
    if predicate():
        return
    raise AssertionError(f'timed out after {timeout_seconds}s waiting for {description}')

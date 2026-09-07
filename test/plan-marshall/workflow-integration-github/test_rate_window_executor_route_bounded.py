#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The rate-window guard's executor fallback is time-boxed.

``github_re_review.read_rate_window`` reads manage-locks' rate-window claim by
one of two routes: an in-process import first, and an executor subprocess when
that import (or the call behind it) fails. The function's whole contract is that
a read it could not perform is RETURNED as ``{'status': 'unreadable'}`` — a shape
with no ``expired`` key, which the trigger guard reads as "no observation" and
therefore permits.

An unbounded subprocess defeats that contract without ever contradicting it: an
executor that never exits holds the caller for the entire automatic-review budget
and the envelope is never produced at all, so the guard stops being fail-open and
becomes fail-silent. The bound is what keeps "unreadable" a value this function
can still hand back.

The three cases are a matched set. One pins that the dispatch carries a bound
shorter than the budget it protects, one pins that expiry becomes the envelope
rather than an exception, and the third pins that a responsive executor is still
read normally — without which a route that had simply stopped working would
satisfy the other two.
"""

import subprocess
import sys
import types

import file_ops
import github_re_review
import pytest

#: The automatic-review budget the bound exists to protect, in seconds. Named
#: here so the assertion is "shorter than the budget" rather than a re-literalled
#: copy of whatever the implementation happens to have chosen.
_AUTOMATIC_REVIEW_BUDGET_SECONDS = 900

_PLAN_ID = 'a-plan'
_BOT_KIND = 'coderabbit'
_PR_NUMBER = 4321

#: What ``rate-window check`` prints for a bot with no stored record.
_FREE_WINDOW_TOON = 'status: free\nexpired: true\nholder: \nseconds_remaining: 0.0\n'


@pytest.fixture
def executor_route(monkeypatch):
    """Force the executor route and return the recorder of its dispatch kwargs.

    The in-process route is made to fail — not removed — by standing a
    ``merge_lock`` stub in ``sys.modules`` whose handler refuses. That is the
    condition ``read_rate_window`` documents for falling through, so the fallback
    is reached the way production reaches it rather than by calling a private
    helper directly.

    ``get_executor_path`` is stubbed too: the route resolves it before dispatch,
    and a checkout without a generated executor would otherwise fail these tests
    for a reason that has nothing to do with the bound under test.
    """
    stub = types.ModuleType('merge_lock')
    stub._DEFAULT_RECOVERY_ATTEMPT_CAP = 3

    def _refuse(_namespace):
        raise RuntimeError('in-process route unavailable')

    stub.run_rate_window = _refuse
    monkeypatch.setitem(sys.modules, 'merge_lock', stub)
    monkeypatch.setattr(file_ops, 'get_executor_path', lambda: 'execute-script.py')
    return monkeypatch


def _capture_dispatch(monkeypatch, outcome):
    """Replace ``subprocess.run`` with a recorder that then applies ``outcome``."""
    calls: list[dict] = []

    def fake_run(argv, **kwargs):
        calls.append({'argv': argv, **kwargs})
        return outcome(argv, kwargs)

    monkeypatch.setattr(subprocess, 'run', fake_run)
    return calls


def _completed(stdout):
    return lambda argv, kwargs: subprocess.CompletedProcess(argv, 0, stdout=stdout, stderr='')


def test_the_executor_route_is_dispatched_with_a_bound_shorter_than_the_budget(executor_route):
    """The subprocess carries a positive ``timeout`` well inside the 900s budget.

    Asserted at the lowest primitive — the ``subprocess.run`` call itself — because
    that is the only place the bound either exists or does not. A test that only
    observed the return value would pass on an unbounded dispatch that happened to
    answer quickly, which is every run except the one that matters.
    """
    calls = _capture_dispatch(executor_route, _completed(_FREE_WINDOW_TOON))

    github_re_review.read_rate_window(_PLAN_ID, _BOT_KIND, _PR_NUMBER)

    assert len(calls) == 1, 'the executor route was not taken, so the bound was never exercised'
    timeout = calls[0].get('timeout')
    assert timeout is not None, 'the executor dispatch passed no timeout at all'
    assert timeout > 0
    assert timeout < _AUTOMATIC_REVIEW_BUDGET_SECONDS, (
        f'a {timeout}s bound does not protect the {_AUTOMATIC_REVIEW_BUDGET_SECONDS}s '
        f'automatic-review budget it exists to keep the guard inside'
    )


def test_a_stalled_executor_yields_the_unreadable_envelope(executor_route):
    """Expiry becomes the documented envelope, not an exception out of the guard.

    ``TimeoutExpired`` is what the bound produces, so the bound is only useful if
    it lands on the same path every other failure of this route lands on. The
    absent ``expired`` key is the load-bearing half: it is what makes the trigger
    guard treat the read as "no observation" and permit, rather than refusing the
    re-review because a subprocess was slow.
    """

    def _stall(argv, kwargs):
        raise subprocess.TimeoutExpired(argv, kwargs['timeout'])

    _capture_dispatch(executor_route, _stall)

    result = github_re_review.read_rate_window(_PLAN_ID, _BOT_KIND, _PR_NUMBER)

    assert result['status'] == 'unreadable'
    assert 'expired' not in result


def test_a_responsive_executor_is_still_read_through(executor_route):
    """MATCHED CONTROL — the bounded route still returns the handler's own payload.

    Without this, a fallback that had stopped reading anything at all would
    satisfy both cases above: the dispatch assertion inspects only the call, and
    the stall assertion only wants ``unreadable``.
    """
    _capture_dispatch(executor_route, _completed(_FREE_WINDOW_TOON))

    result = github_re_review.read_rate_window(_PLAN_ID, _BOT_KIND, _PR_NUMBER)

    assert result['status'] == 'free'
    assert result['expired'] is True

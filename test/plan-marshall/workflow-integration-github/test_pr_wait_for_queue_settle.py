# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for ``pr wait-for-queue-settle`` — the bounded merge-queue settle wait.

The verb observes a baseline, then polls the same observation ``pr queue-state``
makes until the PR has left the queue — ``merged``, ``closed`` or ``dequeued`` —
or its deadline elapses. Every path that produced a verdict returns
``status: success``; the deadline is ``timed_out: true`` beside
``settle: timeout``, never a distinct status.

The poll runs through the REAL shared ``poll_until`` in ``ci_base``. Its clock
and sleep are replaced by :class:`_FakeClock`, whose ``sleep`` advances the time
``time`` reports, so every test is deterministic and takes no wall-clock time.
Provider reads are answered at ``github_ops.run_gh``, the lowest primitive.
"""

import argparse

import _github_pr
import ci_base
import github_ops
import pytest
from _pr_queue_fixtures import (
    MERGE_SHA,
    PR_NUMBER,
    PR_VIEW_ARGV,
    QUEUE_GRAPHQL_ARGV,
    RUN_LIST_ARGV,
    QueueWorld,
    install_gh,
    merge_group_run,
    queued_world,
)

_TIMEOUT = 60
_INTERVAL = 30


class _FakeClock:
    """A clock that only moves when the code under test sleeps."""

    def __init__(self) -> None:
        self.now = 1_000.0
        self.sleeps: list[float] = []

    def time(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


@pytest.fixture
def clock(monkeypatch) -> _FakeClock:
    """Drive ``poll_until`` from an injected clock and sleep."""
    fake = _FakeClock()
    monkeypatch.setattr(ci_base.time, 'time', fake.time)
    monkeypatch.setattr(ci_base.time, 'sleep', fake.sleep)
    return fake


def _args(*, timeout: int = _TIMEOUT, interval: int = _INTERVAL) -> argparse.Namespace:
    return argparse.Namespace(pr_number=PR_NUMBER, timeout=timeout, interval=interval)


def _dequeued_world() -> QueueWorld:
    """Open, unlisted, not armed, newest merge-group run completed and failed."""
    return QueueWorld(runs=[merge_group_run(run_id=901, conclusion='failure')])


# =============================================================================
# Settles — merged / closed / dequeued
# =============================================================================


@pytest.mark.parametrize(
    ('settled_world', 'expected_settle', 'expected_pr_state'),
    [
        (QueueWorld(state='MERGED', merge_commit=MERGE_SHA), 'merged', 'merged'),
        (QueueWorld(state='CLOSED'), 'closed', 'closed'),
        (_dequeued_world(), 'dequeued', 'open'),
    ],
    ids=['merged', 'closed', 'dequeued'],
)
def test_wait_settles_when_the_pr_leaves_the_queue(
    monkeypatch, clock, settled_world, expected_settle, expected_pr_state
):
    """Queued at the baseline and on poll 1, settled on poll 2."""
    install_gh(monkeypatch, [queued_world(), queued_world(), settled_world])

    result = github_ops.cmd_pr_wait_for_queue_settle(_args())

    assert result['status'] == 'success'
    assert result['operation'] == 'pr_wait_for_queue_settle'
    assert result['pr_number'] == PR_NUMBER
    assert result['timed_out'] is False
    assert result['settle'] == expected_settle
    assert result['polls'] == 2
    assert result['duration_sec'] == _INTERVAL
    assert clock.sleeps == [_INTERVAL]
    assert result['baseline']['in_queue'] is True
    assert result['baseline']['pr_state'] == 'open'
    assert result['final']['pr_state'] == expected_pr_state
    assert result['final']['in_queue'] is False


def test_wait_reports_the_landing_commit_of_a_merged_settle(monkeypatch, clock):
    install_gh(monkeypatch, [queued_world(), QueueWorld(state='MERGED', merge_commit=MERGE_SHA)])

    result = github_ops.cmd_pr_wait_for_queue_settle(_args())

    assert result['settle'] == 'merged'
    assert result['final']['merge_commit_sha'] == MERGE_SHA
    assert result['baseline']['merge_commit_sha'] is None


def test_wait_settles_on_the_first_poll_without_sleeping(monkeypatch, clock):
    """A PR already merged when the wait starts settles on poll 1 — no sleep is spent."""
    install_gh(monkeypatch, [QueueWorld(state='MERGED', merge_commit=MERGE_SHA)])

    result = github_ops.cmd_pr_wait_for_queue_settle(_args())

    assert result['status'] == 'success'
    assert result['settle'] == 'merged'
    assert result['timed_out'] is False
    assert result['polls'] == 1
    assert result['duration_sec'] == 0
    assert clock.sleeps == []


def test_every_settle_value_is_a_member_of_the_declared_set():
    """The settles this module asserts are exactly the verb's own closed set."""
    assert set(_github_pr.QUEUE_SETTLES) == {'merged', 'closed', 'dequeued', 'timeout'}


# =============================================================================
# The deadline
# =============================================================================


def test_wait_reports_the_deadline_as_success_with_timed_out(monkeypatch, clock):
    """Still queued at the deadline: ``status: success``, ``timed_out: true``, ``settle: timeout``."""
    install_gh(monkeypatch, [queued_world()])

    result = github_ops.cmd_pr_wait_for_queue_settle(_args())

    assert result['status'] == 'success'
    assert result['operation'] == 'pr_wait_for_queue_settle'
    assert result['timed_out'] is True
    assert result['settle'] == 'timeout'
    # Polls at t=0 and t=30 observe; the iteration at t=60 meets the deadline.
    assert result['polls'] == 3
    assert result['duration_sec'] == _TIMEOUT
    assert clock.sleeps == [_INTERVAL, _INTERVAL]
    assert result['final']['in_queue'] is True
    assert result['final']['pr_state'] == 'open'


def test_wait_with_no_time_budget_reports_the_baseline_as_its_final_observation(monkeypatch, clock):
    """A zero timeout never polls; ``final`` is the baseline, not an empty observation."""
    stub = install_gh(monkeypatch, [queued_world()])

    result = github_ops.cmd_pr_wait_for_queue_settle(_args(timeout=0))

    assert result['status'] == 'success'
    assert result['timed_out'] is True
    assert result['settle'] == 'timeout'
    assert result['final'] == result['baseline']
    assert result['final']['in_queue'] is True
    assert stub.calls_starting('pr', 'view') == [PR_VIEW_ARGV]


# =============================================================================
# Indeterminate reads never settle as dequeued
# =============================================================================


@pytest.mark.parametrize(
    'unread_world',
    [
        # Queue membership unread; the failed run alone is not a dequeue.
        QueueWorld(graphql_fails=True, runs=[merge_group_run(run_id=901, conclusion='failure')]),
        # Membership read as out-of-queue, but the run list could not be read.
        QueueWorld(run_list_fails=True),
        # Membership read as out-of-queue, run list full with no run for the PR.
        QueueWorld(
            runs=[merge_group_run(run_id=2000 + n, pr_number=7) for n in range(github_ops.MERGE_GROUP_RUN_LIST_LIMIT)]
        ),
    ],
    ids=['queue_read_failed', 'run_list_failed', 'run_list_at_bound'],
)
def test_wait_does_not_settle_as_dequeued_on_an_indeterminate_read(monkeypatch, clock, unread_world):
    install_gh(monkeypatch, [queued_world(), unread_world])

    result = github_ops.cmd_pr_wait_for_queue_settle(_args())

    assert result['status'] == 'success'
    assert result['settle'] == 'timeout'
    assert result['settle'] != 'dequeued'
    assert result['timed_out'] is True
    final = result['final']
    indeterminate = _github_pr.QUEUE_READ_INDETERMINATE
    assert indeterminate in (final['in_queue'], final['merge_group_run']['found'])


@pytest.mark.parametrize(
    'in_flight_world',
    [
        # Unlisted and unarmed with no merge-group run at all: the instant
        # between an enqueue call and its admission looks exactly like this.
        QueueWorld(),
        # Unlisted, but auto-merge is still armed — GitHub will re-enqueue.
        QueueWorld(
            auto_merge={'enabledAt': '2026-01-01T00:00:00Z'},
            runs=[merge_group_run(run_id=901, conclusion='failure')],
        ),
        # Unlisted, newest run passed: the merge is about to be reported.
        QueueWorld(runs=[merge_group_run(run_id=901, conclusion='success')]),
        # Unlisted, newest run still running.
        QueueWorld(runs=[merge_group_run(run_id=901, status='in_progress', conclusion=None)]),
    ],
    ids=['no_run', 'auto_merge_armed', 'run_succeeded', 'run_in_progress'],
)
def test_wait_does_not_settle_an_open_pr_without_a_failed_completed_run(monkeypatch, clock, in_flight_world):
    install_gh(monkeypatch, [queued_world(), in_flight_world])

    result = github_ops.cmd_pr_wait_for_queue_settle(_args())

    assert result['status'] == 'success'
    assert result['timed_out'] is True
    assert result['settle'] == 'timeout'
    assert result['final']['pr_state'] == 'open'


# =============================================================================
# The PR could not be read
# =============================================================================


def test_wait_returns_pr_read_failed_at_the_baseline_without_polling(monkeypatch, clock):
    stub = install_gh(monkeypatch, [QueueWorld(view_fails=True, view_stderr='HTTP 502: Bad Gateway')])

    result = github_ops.cmd_pr_wait_for_queue_settle(_args())

    assert result['status'] == 'error'
    assert result['operation'] == 'pr_wait_for_queue_settle'
    assert result['error'] == _github_pr.PR_READ_FAILED
    assert result['pr_number'] == PR_NUMBER
    assert result['context'] == 'HTTP 502: Bad Gateway'
    # The baseline read is the only read: nothing was polled and nothing slept.
    assert stub.calls_starting('pr', 'view') == [PR_VIEW_ARGV]
    assert clock.sleeps == []
    assert 'polls' not in result
    assert 'settle' not in result
    assert 'timed_out' not in result


def test_wait_returns_pr_read_failed_when_the_pr_read_fails_mid_poll(monkeypatch, clock):
    """A PR read that fails during the poll ends the wait, carrying the polls and duration reached."""
    install_gh(
        monkeypatch,
        [queued_world(), queued_world(), QueueWorld(view_fails=True, view_stderr='HTTP 502: Bad Gateway')],
    )

    result = github_ops.cmd_pr_wait_for_queue_settle(_args())

    assert result['status'] == 'error'
    assert result['operation'] == 'pr_wait_for_queue_settle'
    assert result['error'] == _github_pr.PR_READ_FAILED
    assert result['context'] == 'HTTP 502: Bad Gateway'
    assert result['polls'] == 2
    assert result['duration_sec'] == _INTERVAL
    assert 'settle' not in result


# =============================================================================
# Constructed argv and the timeout / interval pass-through
# =============================================================================


def test_wait_repeats_the_same_three_reads_on_every_observation(monkeypatch, clock):
    """Baseline plus two polls is three observations, each the same three argvs."""
    stub = install_gh(monkeypatch, [queued_world(), queued_world(), QueueWorld(state='MERGED')])

    github_ops.cmd_pr_wait_for_queue_settle(_args())

    assert stub.calls_starting('pr', 'view') == [PR_VIEW_ARGV] * 3
    assert stub.calls_starting('api', 'graphql') == [QUEUE_GRAPHQL_ARGV] * 3
    assert stub.calls_starting('run', 'list') == [RUN_LIST_ARGV] * 3


def test_wait_passes_timeout_and_interval_straight_to_poll_until(monkeypatch):
    install_gh(monkeypatch, [queued_world()])
    seen: dict = {}

    def recording_poll_until(check_fn, is_complete_fn, *, timeout, interval):
        seen['timeout'] = timeout
        seen['interval'] = interval
        ok, data = check_fn()
        return {'timed_out': True, 'duration_sec': timeout, 'polls': 1, 'last_data': data if ok else {}}

    monkeypatch.setattr(github_ops, 'poll_until', recording_poll_until)

    result = github_ops.cmd_pr_wait_for_queue_settle(_args(timeout=7, interval=3))

    assert seen == {'timeout': 7, 'interval': 3}
    assert result['settle'] == 'timeout'
    assert result['duration_sec'] == 7

#!/usr/bin/env python3
"""Tests for github_ops.py ci/issue wait-for-* poll handlers.

Covers the three handlers added to the GitHub provider:
    cmd_ci_wait_for_status_flip
    cmd_issue_wait_for_close
    cmd_issue_wait_for_label

Scope:
    - Dispatch-table registration for each (group, subcommand) tuple
    - Auth short-circuit before any fetch helper / poll_until call
    - Happy path: fetch helper flips baseline → completed with timed_out=false
    - Timeout path: fetch helper always returns baseline → timed_out=true

Tests never shell out to the real ``gh`` CLI: every fetch helper and the
auth check are monkeypatched, and ``time.sleep`` inside ``poll_until`` is
neutralised so the timeout branch runs in constant time.
"""

import argparse
import time

import ci_base  # type: ignore[import-not-found]
import github_ops  # type: ignore[import-not-found]


def _ok_auth():
    return True, ''


def _noop_sleep(monkeypatch):
    """Make poll_until's sleep a no-op so timeout-path tests finish fast."""
    monkeypatch.setattr(ci_base.time, 'sleep', lambda *_a, **_kw: None)
    monkeypatch.setattr(time, 'sleep', lambda *_a, **_kw: None)


# =============================================================================
# Dispatch-table registration
# =============================================================================


def _build_handler_map():
    """Rebuild the dispatch map exactly as github_ops.main() does.

    Kept in sync with the dispatch block in github_ops.main(); we only assert
    on the three new wait-for-* entries here.
    """
    return {
        ('ci', 'wait-for-status-flip'): github_ops.cmd_ci_wait_for_status_flip,
        ('issue', 'wait-for-close'): github_ops.cmd_issue_wait_for_close,
        ('issue', 'wait-for-label'): github_ops.cmd_issue_wait_for_label,
    }


def test_dispatch_ci_wait_for_status_flip_registered():
    handlers = _build_handler_map()
    assert handlers[('ci', 'wait-for-status-flip')] is github_ops.cmd_ci_wait_for_status_flip


def test_dispatch_issue_wait_for_close_registered():
    handlers = _build_handler_map()
    assert handlers[('issue', 'wait-for-close')] is github_ops.cmd_issue_wait_for_close


def test_dispatch_issue_wait_for_label_registered():
    handlers = _build_handler_map()
    assert handlers[('issue', 'wait-for-label')] is github_ops.cmd_issue_wait_for_label


# =============================================================================
# cmd_ci_wait_for_status_flip
# =============================================================================


def _flip_ci_status_args(*, expected='any', timeout=5, interval=0):
    return argparse.Namespace(pr_number=42, timeout=timeout, interval=interval, expected=expected)


def test_ci_wait_for_status_flip_auth_failure_short_circuits(monkeypatch):
    """Auth failure returns an error result without calling fetch or poll_until."""
    monkeypatch.setattr(github_ops, 'check_auth', lambda: (False, 'not authenticated'))

    fetch_calls = {'count': 0}

    def fake_fetch(pr_number):
        fetch_calls['count'] += 1
        return True, 'pending'

    monkeypatch.setattr(github_ops, '_fetch_pr_overall_ci_status', fake_fetch)

    def exploding_poll(*_a, **_kw):  # pragma: no cover - should never run
        raise AssertionError('poll_until must not be called when auth fails')

    monkeypatch.setattr(github_ops, 'poll_until', exploding_poll)

    result = github_ops.cmd_ci_wait_for_status_flip(_flip_ci_status_args())

    assert result['status'] == 'error'
    assert result['operation'] == 'ci_wait_for_status_flip'
    assert 'not authenticated' in result['error']
    assert fetch_calls['count'] == 0


def test_ci_wait_for_status_flip_completes_on_flip(monkeypatch):
    """Baseline=pending, second fetch=success → handler returns success."""
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    _noop_sleep(monkeypatch)

    call_counts = {'fetch': 0}

    def fake_fetch(pr_number):
        assert pr_number == 42
        call_counts['fetch'] += 1
        if call_counts['fetch'] == 1:
            return True, 'pending'
        return True, 'success'

    monkeypatch.setattr(github_ops, '_fetch_pr_overall_ci_status', fake_fetch)

    result = github_ops.cmd_ci_wait_for_status_flip(_flip_ci_status_args())

    assert result['status'] == 'success', result
    assert result['operation'] == 'ci_wait_for_status_flip'
    assert result['pr_number'] == 42
    assert result['timed_out'] is False
    assert result['baseline_status'] == 'pending'
    assert result['final_status'] == 'success'
    assert result['polls'] >= 1
    # baseline fetch + at least one poll iteration
    assert call_counts['fetch'] >= 2


def test_ci_wait_for_status_flip_times_out_when_status_never_changes(monkeypatch):
    """Fetch always returns the baseline → timed_out=true, final==baseline."""
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    _noop_sleep(monkeypatch)

    def fake_fetch(pr_number):
        return True, 'pending'

    monkeypatch.setattr(github_ops, '_fetch_pr_overall_ci_status', fake_fetch)

    result = github_ops.cmd_ci_wait_for_status_flip(_flip_ci_status_args(timeout=1, interval=0))

    assert result['status'] == 'success', result
    assert result['timed_out'] is True
    assert result['baseline_status'] == 'pending'
    assert result['final_status'] == 'pending'


def test_ci_wait_for_status_flip_expected_success_rejects_failure(monkeypatch):
    """--expected=success must treat a pending→failure transition as no-flip."""
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    _noop_sleep(monkeypatch)

    call_counts = {'fetch': 0}

    def fake_fetch(pr_number):
        call_counts['fetch'] += 1
        if call_counts['fetch'] == 1:
            return True, 'pending'
        return True, 'failure'

    monkeypatch.setattr(github_ops, '_fetch_pr_overall_ci_status', fake_fetch)

    result = github_ops.cmd_ci_wait_for_status_flip(_flip_ci_status_args(expected='success', timeout=1, interval=0))

    assert result['status'] == 'success', result
    # Fresh differs from baseline but is_complete_fn rejects because
    # --expected=success does not match 'failure' → poll_until must time out.
    assert result['timed_out'] is True
    assert result['baseline_status'] == 'pending'
    assert result['final_status'] == 'failure'


def test_ci_wait_for_status_flip_expected_any_accepts_success(monkeypatch):
    """--expected=any accepts any non-pending / non-baseline status."""
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    _noop_sleep(monkeypatch)

    call_counts = {'fetch': 0}

    def fake_fetch(pr_number):
        call_counts['fetch'] += 1
        if call_counts['fetch'] == 1:
            return True, 'pending'
        return True, 'success'

    monkeypatch.setattr(github_ops, '_fetch_pr_overall_ci_status', fake_fetch)

    result = github_ops.cmd_ci_wait_for_status_flip(_flip_ci_status_args(expected='any'))

    assert result['status'] == 'success', result
    assert result['timed_out'] is False
    assert result['final_status'] == 'success'


def test_ci_wait_for_status_flip_expected_any_accepts_failure(monkeypatch):
    """--expected=any also accepts a flip to failure."""
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    _noop_sleep(monkeypatch)

    call_counts = {'fetch': 0}

    def fake_fetch(pr_number):
        call_counts['fetch'] += 1
        if call_counts['fetch'] == 1:
            return True, 'pending'
        return True, 'failure'

    monkeypatch.setattr(github_ops, '_fetch_pr_overall_ci_status', fake_fetch)

    result = github_ops.cmd_ci_wait_for_status_flip(_flip_ci_status_args(expected='any'))

    assert result['status'] == 'success', result
    assert result['timed_out'] is False
    assert result['final_status'] == 'failure'


# =============================================================================
# cmd_issue_wait_for_close
# =============================================================================


def _wait_for_close_args(*, timeout=5, interval=0):
    return argparse.Namespace(issue_number=101, timeout=timeout, interval=interval)


def test_issue_wait_for_close_auth_failure_short_circuits(monkeypatch):
    monkeypatch.setattr(github_ops, 'check_auth', lambda: (False, 'not authenticated'))

    fetch_calls = {'count': 0}

    def fake_fetch(issue_number):
        fetch_calls['count'] += 1
        return True, {'state': 'open', 'labels': []}

    monkeypatch.setattr(github_ops, '_fetch_issue_state_and_labels', fake_fetch)

    def exploding_poll(*_a, **_kw):  # pragma: no cover
        raise AssertionError('poll_until must not be called when auth fails')

    monkeypatch.setattr(github_ops, 'poll_until', exploding_poll)

    result = github_ops.cmd_issue_wait_for_close(_wait_for_close_args())

    assert result['status'] == 'error'
    assert result['operation'] == 'issue_wait_for_close'
    assert 'not authenticated' in result['error']
    assert fetch_calls['count'] == 0


def test_issue_wait_for_close_completes_on_flip(monkeypatch):
    """Baseline state=open, second fetch=closed → timed_out=false."""
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    _noop_sleep(monkeypatch)

    call_counts = {'fetch': 0}

    def fake_fetch(issue_number):
        assert issue_number == 101
        call_counts['fetch'] += 1
        if call_counts['fetch'] == 1:
            return True, {'state': 'open', 'labels': []}
        return True, {'state': 'closed', 'labels': []}

    monkeypatch.setattr(github_ops, '_fetch_issue_state_and_labels', fake_fetch)

    result = github_ops.cmd_issue_wait_for_close(_wait_for_close_args())

    assert result['status'] == 'success', result
    assert result['operation'] == 'issue_wait_for_close'
    assert result['issue_number'] == 101
    assert result['timed_out'] is False
    assert result['baseline_state'] == 'open'
    assert result['final_state'] == 'closed'
    assert result['polls'] >= 1
    assert call_counts['fetch'] >= 2


def test_issue_wait_for_close_times_out_when_state_never_changes(monkeypatch):
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    _noop_sleep(monkeypatch)

    def fake_fetch(issue_number):
        return True, {'state': 'open', 'labels': []}

    monkeypatch.setattr(github_ops, '_fetch_issue_state_and_labels', fake_fetch)

    result = github_ops.cmd_issue_wait_for_close(_wait_for_close_args(timeout=1, interval=0))

    assert result['status'] == 'success', result
    assert result['timed_out'] is True
    assert result['baseline_state'] == 'open'
    assert result['final_state'] == 'open'


# =============================================================================
# cmd_issue_wait_for_label
# =============================================================================


def _wait_for_label_args(*, mode='present', timeout=5, interval=0, label='ready'):
    return argparse.Namespace(
        issue_number=202,
        label=label,
        mode=mode,
        timeout=timeout,
        interval=interval,
    )


def test_issue_wait_for_label_auth_failure_short_circuits(monkeypatch):
    monkeypatch.setattr(github_ops, 'check_auth', lambda: (False, 'not authenticated'))

    fetch_calls = {'count': 0}

    def fake_fetch(issue_number):
        fetch_calls['count'] += 1
        return True, {'state': 'open', 'labels': []}

    monkeypatch.setattr(github_ops, '_fetch_issue_state_and_labels', fake_fetch)

    def exploding_poll(*_a, **_kw):  # pragma: no cover
        raise AssertionError('poll_until must not be called when auth fails')

    monkeypatch.setattr(github_ops, 'poll_until', exploding_poll)

    result = github_ops.cmd_issue_wait_for_label(_wait_for_label_args())

    assert result['status'] == 'error'
    assert result['operation'] == 'issue_wait_for_label'
    assert 'not authenticated' in result['error']
    assert fetch_calls['count'] == 0


def test_issue_wait_for_label_present_completes_when_label_appears(monkeypatch):
    """--mode=present: labels=[] → ['ready'] completes."""
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    _noop_sleep(monkeypatch)

    call_counts = {'fetch': 0}

    def fake_fetch(issue_number):
        call_counts['fetch'] += 1
        if call_counts['fetch'] == 1:
            return True, {'state': 'open', 'labels': []}
        return True, {'state': 'open', 'labels': ['ready']}

    monkeypatch.setattr(github_ops, '_fetch_issue_state_and_labels', fake_fetch)

    result = github_ops.cmd_issue_wait_for_label(_wait_for_label_args(mode='present'))

    assert result['status'] == 'success', result
    assert result['operation'] == 'issue_wait_for_label'
    assert result['mode'] == 'present'
    assert result['timed_out'] is False
    assert result['baseline_present'] is False
    assert result['final_present'] is True
    assert result['polls'] >= 1
    assert call_counts['fetch'] >= 2


def test_issue_wait_for_label_absent_completes_when_label_disappears(monkeypatch):
    """--mode=absent: labels=['ready'] → [] completes."""
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    _noop_sleep(monkeypatch)

    call_counts = {'fetch': 0}

    def fake_fetch(issue_number):
        call_counts['fetch'] += 1
        if call_counts['fetch'] == 1:
            return True, {'state': 'open', 'labels': ['ready']}
        return True, {'state': 'open', 'labels': []}

    monkeypatch.setattr(github_ops, '_fetch_issue_state_and_labels', fake_fetch)

    result = github_ops.cmd_issue_wait_for_label(_wait_for_label_args(mode='absent'))

    assert result['status'] == 'success', result
    assert result['mode'] == 'absent'
    assert result['timed_out'] is False
    assert result['baseline_present'] is True
    assert result['final_present'] is False


def test_issue_wait_for_label_times_out_when_label_state_never_changes(monkeypatch):
    """Baseline labels never flip → timed_out=true, final_present==baseline."""
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    _noop_sleep(monkeypatch)

    def fake_fetch(issue_number):
        return True, {'state': 'open', 'labels': []}

    monkeypatch.setattr(github_ops, '_fetch_issue_state_and_labels', fake_fetch)

    result = github_ops.cmd_issue_wait_for_label(_wait_for_label_args(mode='present', timeout=1, interval=0))

    assert result['status'] == 'success', result
    assert result['timed_out'] is True
    assert result['baseline_present'] is False
    assert result['final_present'] is False

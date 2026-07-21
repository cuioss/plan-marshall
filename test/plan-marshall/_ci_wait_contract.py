#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Provider-agnostic CI poll-handler contract, shared by the CI provider tests.

Two things live here:

1. **The helpers that every CI provider test module needs** — the auth stub, the
   sleep neutraliser, the three ``argparse.Namespace`` builders, the dispatch-map
   rebuilder, the plan-relative artifact path resolver, and the deterministic
   monotonic-clock stand-in. Each of these was previously re-declared verbatim in
   the GitHub and GitLab test modules; this is now their single home.

2. **The provider-agnostic poll-handler contract tests** — dispatch-table
   registration, the auth short-circuit, the flip/timeout matrix for
   ``cmd_ci_wait_for_status_flip``, and the close / label handlers. Every one of
   these is expressed purely against a provider ``ops`` module's public handler
   surface, so it holds identically for GitHub and GitLab.

The contract tests take a ``ci_ops`` fixture — the provider's ops module. A
provider test module imports the contract test names and defines that fixture,
so the contract is authored once and executes exactly once per provider.

This module is deliberately named with a leading underscore: ``python_files``
is ``test_*.py``, so pytest never collects the contract here. It is collected
only through the provider modules that import it.
"""

import argparse
import time
from pathlib import Path

import ci_base

#: Root of the committed provider CI log fixtures. Resolved relative to this
#: file so resolution never depends on cwd.
CI_LOG_FIXTURE_ROOT = Path(__file__).resolve().parent / 'tools-integration-ci' / 'fixtures' / 'ci-logs'


# =============================================================================
# Shared helpers
# =============================================================================


def _ok_auth():
    """Stand in for a provider ``check_auth`` that reports an authed session."""
    return True, ''


def _noop_sleep(monkeypatch):
    """Make poll_until's sleep a no-op so timeout-path tests finish fast."""
    monkeypatch.setattr(ci_base.time, 'sleep', lambda *_a, **_kw: None)
    monkeypatch.setattr(time, 'sleep', lambda *_a, **_kw: None)


def _build_handler_map(ops):
    """Rebuild the provider dispatch map slice for the three wait-for-* entries.

    Kept in sync with the dispatch block in each provider's ``main()``; only the
    three wait-for-* entries are asserted on.
    """
    return {
        ('checks', 'wait-for-status-flip'): ops.cmd_ci_wait_for_status_flip,
        ('issue', 'wait-for-close'): ops.cmd_issue_wait_for_close,
        ('issue', 'wait-for-label'): ops.cmd_issue_wait_for_label,
    }


def _flip_ci_status_args(*, expected='any', timeout=5, interval=0):
    return argparse.Namespace(pr_number=42, timeout=timeout, interval=interval, expected=expected)


def _wait_for_close_args(*, timeout=5, interval=0):
    return argparse.Namespace(issue_number=101, timeout=timeout, interval=interval)


def _wait_for_label_args(*, mode='present', timeout=5, interval=0, label='ready'):
    return argparse.Namespace(
        issue_number=202,
        label=label,
        mode=mode,
        timeout=timeout,
        interval=interval,
    )


def _resolve_plan_relative(plan_context, rel_path):
    """Resolve a plan-dir-relative artifact path under the redirected plan dir.

    The enrichment hook returns paths rooted at ``.plan/local/plans/{plan_id}/``;
    the ``plan_context`` fixture redirects PLAN_BASE_DIR so the on-disk tree is
    ``{fixture_dir}/plans/{plan_id}/...``. Splice on the ``plans/{plan_id}/``
    marker to map one onto the other without hard-coding the prefix shape.
    """
    marker = f'plans/{plan_context.plan_id}/'
    idx = rel_path.find(marker)
    assert idx != -1, f'unexpected artifact path shape: {rel_path}'
    return plan_context.fixture_dir / 'plans' / rel_path[idx + len('plans/'):]


def _make_incrementing_clock(step=60.0):
    """Return a monotonic-clock stand-in that advances ``step`` per call, so the
    recorded wall-clock duration is a positive, deterministic value in tests."""
    state = {'t': 0.0}

    def clock():
        state['t'] += step
        return state['t']

    return clock


# =============================================================================
# Contract: dispatch-table registration
# =============================================================================


def test_dispatch_ci_wait_for_status_flip_registered(ci_ops):
    handlers = _build_handler_map(ci_ops)
    assert handlers[('checks', 'wait-for-status-flip')] is ci_ops.cmd_ci_wait_for_status_flip


def test_dispatch_issue_wait_for_close_registered(ci_ops):
    handlers = _build_handler_map(ci_ops)
    assert handlers[('issue', 'wait-for-close')] is ci_ops.cmd_issue_wait_for_close


def test_dispatch_issue_wait_for_label_registered(ci_ops):
    handlers = _build_handler_map(ci_ops)
    assert handlers[('issue', 'wait-for-label')] is ci_ops.cmd_issue_wait_for_label


# =============================================================================
# Contract: cmd_ci_wait_for_status_flip
# =============================================================================


def test_ci_wait_for_status_flip_auth_failure_short_circuits(ci_ops, monkeypatch):
    """Auth failure returns an error result without calling fetch or poll_until."""
    monkeypatch.setattr(ci_ops, 'check_auth', lambda: (False, 'not authenticated'))

    fetch_calls = {'count': 0}

    def fake_fetch(pr_number):
        fetch_calls['count'] += 1
        return True, 'pending'

    monkeypatch.setattr(ci_ops, '_fetch_pr_overall_ci_status', fake_fetch)

    def exploding_poll(*_a, **_kw):  # pragma: no cover - should never run
        raise AssertionError('poll_until must not be called when auth fails')

    monkeypatch.setattr(ci_ops, 'poll_until', exploding_poll)

    result = ci_ops.cmd_ci_wait_for_status_flip(_flip_ci_status_args())

    assert result['status'] == 'error'
    assert result['operation'] == 'ci_wait_for_status_flip'
    assert 'not authenticated' in result['error']
    assert fetch_calls['count'] == 0


def test_ci_wait_for_status_flip_completes_on_flip(ci_ops, monkeypatch):
    """Baseline=pending, second fetch=success → handler returns success."""
    monkeypatch.setattr(ci_ops, 'check_auth', _ok_auth)
    _noop_sleep(monkeypatch)

    call_counts = {'fetch': 0}

    def fake_fetch(pr_number):
        assert pr_number == 42
        call_counts['fetch'] += 1
        if call_counts['fetch'] == 1:
            return True, 'pending'
        return True, 'success'

    monkeypatch.setattr(ci_ops, '_fetch_pr_overall_ci_status', fake_fetch)

    result = ci_ops.cmd_ci_wait_for_status_flip(_flip_ci_status_args())

    assert result['status'] == 'success', result
    assert result['operation'] == 'ci_wait_for_status_flip'
    assert result['pr_number'] == 42
    assert result['timed_out'] is False
    assert result['baseline_status'] == 'pending'
    assert result['final_status'] == 'success'
    assert result['polls'] >= 1
    # baseline fetch + at least one poll iteration
    assert call_counts['fetch'] >= 2


def test_ci_wait_for_status_flip_times_out_when_status_never_changes(ci_ops, monkeypatch):
    """Fetch always returns the baseline → timed_out=true, final==baseline."""
    monkeypatch.setattr(ci_ops, 'check_auth', _ok_auth)
    _noop_sleep(monkeypatch)

    def fake_fetch(pr_number):
        return True, 'pending'

    monkeypatch.setattr(ci_ops, '_fetch_pr_overall_ci_status', fake_fetch)

    result = ci_ops.cmd_ci_wait_for_status_flip(_flip_ci_status_args(timeout=1, interval=0))

    assert result['status'] == 'success', result
    assert result['timed_out'] is True
    assert result['baseline_status'] == 'pending'
    assert result['final_status'] == 'pending'


def test_ci_wait_for_status_flip_expected_success_rejects_failure(ci_ops, monkeypatch):
    """--expected=success must treat a pending→failure transition as no-flip."""
    monkeypatch.setattr(ci_ops, 'check_auth', _ok_auth)
    _noop_sleep(monkeypatch)

    call_counts = {'fetch': 0}

    def fake_fetch(pr_number):
        call_counts['fetch'] += 1
        if call_counts['fetch'] == 1:
            return True, 'pending'
        return True, 'failure'

    monkeypatch.setattr(ci_ops, '_fetch_pr_overall_ci_status', fake_fetch)

    result = ci_ops.cmd_ci_wait_for_status_flip(_flip_ci_status_args(expected='success', timeout=1, interval=0))

    assert result['status'] == 'success', result
    # Fresh differs from baseline but is_complete_fn rejects because
    # --expected=success does not match 'failure' → poll_until must time out.
    assert result['timed_out'] is True
    assert result['baseline_status'] == 'pending'
    assert result['final_status'] == 'failure'


def test_ci_wait_for_status_flip_expected_any_accepts_success(ci_ops, monkeypatch):
    """--expected=any accepts any non-pending / non-baseline status."""
    monkeypatch.setattr(ci_ops, 'check_auth', _ok_auth)
    _noop_sleep(monkeypatch)

    call_counts = {'fetch': 0}

    def fake_fetch(pr_number):
        call_counts['fetch'] += 1
        if call_counts['fetch'] == 1:
            return True, 'pending'
        return True, 'success'

    monkeypatch.setattr(ci_ops, '_fetch_pr_overall_ci_status', fake_fetch)

    result = ci_ops.cmd_ci_wait_for_status_flip(_flip_ci_status_args(expected='any'))

    assert result['status'] == 'success', result
    assert result['timed_out'] is False
    assert result['final_status'] == 'success'


def test_ci_wait_for_status_flip_expected_any_accepts_failure(ci_ops, monkeypatch):
    """--expected=any also accepts a flip to failure."""
    monkeypatch.setattr(ci_ops, 'check_auth', _ok_auth)
    _noop_sleep(monkeypatch)

    call_counts = {'fetch': 0}

    def fake_fetch(pr_number):
        call_counts['fetch'] += 1
        if call_counts['fetch'] == 1:
            return True, 'pending'
        return True, 'failure'

    monkeypatch.setattr(ci_ops, '_fetch_pr_overall_ci_status', fake_fetch)

    result = ci_ops.cmd_ci_wait_for_status_flip(_flip_ci_status_args(expected='any'))

    assert result['status'] == 'success', result
    assert result['timed_out'] is False
    assert result['final_status'] == 'failure'


# =============================================================================
# Contract: cmd_issue_wait_for_close
# =============================================================================


def test_issue_wait_for_close_auth_failure_short_circuits(ci_ops, monkeypatch):
    monkeypatch.setattr(ci_ops, 'check_auth', lambda: (False, 'not authenticated'))

    fetch_calls = {'count': 0}

    def fake_fetch(issue_number):
        fetch_calls['count'] += 1
        return True, {'state': 'open', 'labels': []}

    monkeypatch.setattr(ci_ops, '_fetch_issue_state_and_labels', fake_fetch)

    def exploding_poll(*_a, **_kw):  # pragma: no cover
        raise AssertionError('poll_until must not be called when auth fails')

    monkeypatch.setattr(ci_ops, 'poll_until', exploding_poll)

    result = ci_ops.cmd_issue_wait_for_close(_wait_for_close_args())

    assert result['status'] == 'error'
    assert result['operation'] == 'issue_wait_for_close'
    assert 'not authenticated' in result['error']
    assert fetch_calls['count'] == 0


def test_issue_wait_for_close_completes_on_flip(ci_ops, monkeypatch):
    """Baseline state=open, second fetch=closed → timed_out=false."""
    monkeypatch.setattr(ci_ops, 'check_auth', _ok_auth)
    _noop_sleep(monkeypatch)

    call_counts = {'fetch': 0}

    def fake_fetch(issue_number):
        assert issue_number == 101
        call_counts['fetch'] += 1
        if call_counts['fetch'] == 1:
            return True, {'state': 'open', 'labels': []}
        return True, {'state': 'closed', 'labels': []}

    monkeypatch.setattr(ci_ops, '_fetch_issue_state_and_labels', fake_fetch)

    result = ci_ops.cmd_issue_wait_for_close(_wait_for_close_args())

    assert result['status'] == 'success', result
    assert result['operation'] == 'issue_wait_for_close'
    assert result['issue_number'] == 101
    assert result['timed_out'] is False
    assert result['baseline_state'] == 'open'
    assert result['final_state'] == 'closed'
    assert result['polls'] >= 1
    assert call_counts['fetch'] >= 2


def test_issue_wait_for_close_times_out_when_state_never_changes(ci_ops, monkeypatch):
    monkeypatch.setattr(ci_ops, 'check_auth', _ok_auth)
    _noop_sleep(monkeypatch)

    def fake_fetch(issue_number):
        return True, {'state': 'open', 'labels': []}

    monkeypatch.setattr(ci_ops, '_fetch_issue_state_and_labels', fake_fetch)

    result = ci_ops.cmd_issue_wait_for_close(_wait_for_close_args(timeout=1, interval=0))

    assert result['status'] == 'success', result
    assert result['timed_out'] is True
    assert result['baseline_state'] == 'open'
    assert result['final_state'] == 'open'


# =============================================================================
# Contract: cmd_issue_wait_for_label
# =============================================================================


def test_issue_wait_for_label_auth_failure_short_circuits(ci_ops, monkeypatch):
    monkeypatch.setattr(ci_ops, 'check_auth', lambda: (False, 'not authenticated'))

    fetch_calls = {'count': 0}

    def fake_fetch(issue_number):
        fetch_calls['count'] += 1
        return True, {'state': 'open', 'labels': []}

    monkeypatch.setattr(ci_ops, '_fetch_issue_state_and_labels', fake_fetch)

    def exploding_poll(*_a, **_kw):  # pragma: no cover
        raise AssertionError('poll_until must not be called when auth fails')

    monkeypatch.setattr(ci_ops, 'poll_until', exploding_poll)

    result = ci_ops.cmd_issue_wait_for_label(_wait_for_label_args())

    assert result['status'] == 'error'
    assert result['operation'] == 'issue_wait_for_label'
    assert 'not authenticated' in result['error']
    assert fetch_calls['count'] == 0


def test_issue_wait_for_label_present_completes_when_label_appears(ci_ops, monkeypatch):
    """--mode=present: labels=[] → ['ready'] completes."""
    monkeypatch.setattr(ci_ops, 'check_auth', _ok_auth)
    _noop_sleep(monkeypatch)

    call_counts = {'fetch': 0}

    def fake_fetch(issue_number):
        call_counts['fetch'] += 1
        if call_counts['fetch'] == 1:
            return True, {'state': 'open', 'labels': []}
        return True, {'state': 'open', 'labels': ['ready']}

    monkeypatch.setattr(ci_ops, '_fetch_issue_state_and_labels', fake_fetch)

    result = ci_ops.cmd_issue_wait_for_label(_wait_for_label_args(mode='present'))

    assert result['status'] == 'success', result
    assert result['operation'] == 'issue_wait_for_label'
    assert result['mode'] == 'present'
    assert result['timed_out'] is False
    assert result['baseline_present'] is False
    assert result['final_present'] is True
    assert result['polls'] >= 1
    assert call_counts['fetch'] >= 2


def test_issue_wait_for_label_absent_completes_when_label_disappears(ci_ops, monkeypatch):
    """--mode=absent: labels=['ready'] → [] completes."""
    monkeypatch.setattr(ci_ops, 'check_auth', _ok_auth)
    _noop_sleep(monkeypatch)

    call_counts = {'fetch': 0}

    def fake_fetch(issue_number):
        call_counts['fetch'] += 1
        if call_counts['fetch'] == 1:
            return True, {'state': 'open', 'labels': ['ready']}
        return True, {'state': 'open', 'labels': []}

    monkeypatch.setattr(ci_ops, '_fetch_issue_state_and_labels', fake_fetch)

    result = ci_ops.cmd_issue_wait_for_label(_wait_for_label_args(mode='absent'))

    assert result['status'] == 'success', result
    assert result['mode'] == 'absent'
    assert result['timed_out'] is False
    assert result['baseline_present'] is True
    assert result['final_present'] is False


def test_issue_wait_for_label_times_out_when_label_state_never_changes(ci_ops, monkeypatch):
    """Baseline labels never flip → timed_out=true, final_present==baseline."""
    monkeypatch.setattr(ci_ops, 'check_auth', _ok_auth)
    _noop_sleep(monkeypatch)

    def fake_fetch(issue_number):
        return True, {'state': 'open', 'labels': []}

    monkeypatch.setattr(ci_ops, '_fetch_issue_state_and_labels', fake_fetch)

    result = ci_ops.cmd_issue_wait_for_label(_wait_for_label_args(mode='present', timeout=1, interval=0))

    assert result['status'] == 'success', result
    assert result['timed_out'] is True
    assert result['baseline_present'] is False
    assert result['final_present'] is False


#: The provider-agnostic contract test names. A provider test module imports
#: these names (binding them into its own namespace so pytest collects them
#: there) and supplies the ``ci_ops`` fixture.
CONTRACT_TESTS = (
    'test_dispatch_ci_wait_for_status_flip_registered',
    'test_dispatch_issue_wait_for_close_registered',
    'test_dispatch_issue_wait_for_label_registered',
    'test_ci_wait_for_status_flip_auth_failure_short_circuits',
    'test_ci_wait_for_status_flip_completes_on_flip',
    'test_ci_wait_for_status_flip_times_out_when_status_never_changes',
    'test_ci_wait_for_status_flip_expected_success_rejects_failure',
    'test_ci_wait_for_status_flip_expected_any_accepts_success',
    'test_ci_wait_for_status_flip_expected_any_accepts_failure',
    'test_issue_wait_for_close_auth_failure_short_circuits',
    'test_issue_wait_for_close_completes_on_flip',
    'test_issue_wait_for_close_times_out_when_state_never_changes',
    'test_issue_wait_for_label_auth_failure_short_circuits',
    'test_issue_wait_for_label_present_completes_when_label_appears',
    'test_issue_wait_for_label_absent_completes_when_label_disappears',
    'test_issue_wait_for_label_times_out_when_label_state_never_changes',
)

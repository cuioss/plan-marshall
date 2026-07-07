#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the GitHub `pr merge-queue` verb (deliverable 5).

Covers three surfaces:

* The shared `ci_base.build_parser` accepts `pr merge-queue` with the
  `--pr-number` | `--head` + optional `--strategy` / `--delete-branch` flags —
  the same declaration both providers consume.
* `github_ops.cmd_pr_merge_queue` enqueues the PR into the GitHub merge queue
  via `gh pr merge --auto` — pinned by a constructed-argv assertion against the
  captured `run_gh` invocation (the lowest subprocess primitive), with no live
  provider.
* The auth-failure and gh-error paths return the unified error TOON.

The dispatch wiring (`('pr', 'merge-queue') -> cmd_pr_merge_queue` in
`github_ops.main`) is exercised transitively: the parser round-trips the
sub-verb to `pr_command == 'merge-queue'` (the router key) and the handler is
the imported `github_ops.cmd_pr_merge_queue`.
"""

import argparse

import ci_base  # noqa: E402
import github_ops  # noqa: E402
import pytest


def _ok_auth():
    return True, ''


def _capture_run_gh(*, merge_ok: bool = True):
    """Return a run_gh stub that records argv, plus the captured list."""
    captured: list[list[str]] = []

    def run_gh_stub(args, capture_json=False, timeout=60):
        captured.append(list(args))
        if args[:2] == ['pr', 'merge']:
            return (0, '', '') if merge_ok else (1, '', 'merge queue rejected')
        return 0, '', ''

    return run_gh_stub, captured


def _mq_ns(*, pr_number=42, head=None, strategy='merge', delete_branch=False):
    return argparse.Namespace(
        pr_number=pr_number,
        head=head,
        strategy=strategy,
        delete_branch=delete_branch,
    )


def _install(monkeypatch, run_gh_stub):
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)
    monkeypatch.setattr(
        github_ops, '_resolve_pr_identifier', lambda args, op: ('42', None)
    )


# ---------------------------------------------------------------------------
# Shared parser acceptance
# ---------------------------------------------------------------------------


def test_ci_base_parser_accepts_pr_merge_queue():
    # Arrange
    parser, _pr_sub, _c, _i, _b = ci_base.build_parser('test')
    # Act
    args = parser.parse_args(['pr', 'merge-queue', '--pr-number', '42'])
    # Assert
    assert args.pr_command == 'merge-queue'
    assert args.pr_number == 42
    assert args.strategy == 'merge'


def test_ci_base_parser_merge_queue_accepts_head_strategy_delete():
    # Arrange
    parser, *_ = ci_base.build_parser('test')
    # Act
    args = parser.parse_args(
        ['pr', 'merge-queue', '--head', 'feature/x', '--strategy', 'squash', '--delete-branch']
    )
    # Assert
    assert args.pr_command == 'merge-queue'
    assert args.head == 'feature/x'
    assert args.strategy == 'squash'
    assert args.delete_branch is True


def test_ci_base_parser_rejects_illegal_strategy():
    # Arrange
    parser, *_ = ci_base.build_parser('test')
    # Act / Assert
    with pytest.raises(SystemExit):
        parser.parse_args(['pr', 'merge-queue', '--pr-number', '42', '--strategy', 'fast-forward'])


# ---------------------------------------------------------------------------
# Enqueue behavior — constructed-argv assertion
# ---------------------------------------------------------------------------


def test_cmd_pr_merge_queue_enqueues_via_gh_auto(monkeypatch):
    # Arrange
    run_gh_stub, captured = _capture_run_gh()
    _install(monkeypatch, run_gh_stub)

    # Act
    result = github_ops.cmd_pr_merge_queue(_mq_ns())

    # Assert — the enqueue rides on `gh pr merge --auto`.
    assert result['status'] == 'success'
    assert result['operation'] == 'pr_merge_queue'
    assert result['enqueued'] is True
    assert result['pr_number'] == 42
    merge_call = next(c for c in captured if c[:2] == ['pr', 'merge'])
    assert merge_call == ['pr', 'merge', '42', '--auto', '--merge']


def test_cmd_pr_merge_queue_delete_branch_appends_flag(monkeypatch):
    # Arrange
    run_gh_stub, captured = _capture_run_gh()
    _install(monkeypatch, run_gh_stub)

    # Act
    result = github_ops.cmd_pr_merge_queue(_mq_ns(delete_branch=True))

    # Assert
    assert result['delete_branch'] is True
    merge_call = next(c for c in captured if c[:2] == ['pr', 'merge'])
    assert merge_call == ['pr', 'merge', '42', '--auto', '--merge', '--delete-branch']


def test_cmd_pr_merge_queue_forwards_strategy(monkeypatch):
    # Arrange
    run_gh_stub, captured = _capture_run_gh()
    _install(monkeypatch, run_gh_stub)

    # Act
    github_ops.cmd_pr_merge_queue(_mq_ns(strategy='squash'))

    # Assert
    merge_call = next(c for c in captured if c[:2] == ['pr', 'merge'])
    assert '--squash' in merge_call
    assert '--merge' not in merge_call


# ---------------------------------------------------------------------------
# Error paths
# ---------------------------------------------------------------------------


def test_cmd_pr_merge_queue_auth_failure(monkeypatch):
    # Arrange
    monkeypatch.setattr(github_ops, 'check_auth', lambda: (False, 'not authed'))

    # Act
    result = github_ops.cmd_pr_merge_queue(_mq_ns())

    # Assert
    assert result['status'] == 'error'
    assert result['operation'] == 'pr_merge_queue'


def test_cmd_pr_merge_queue_gh_error_returns_error(monkeypatch):
    # Arrange — the merge-queue engagement fails at the gh layer.
    run_gh_stub, _captured = _capture_run_gh(merge_ok=False)
    _install(monkeypatch, run_gh_stub)

    # Act
    result = github_ops.cmd_pr_merge_queue(_mq_ns())

    # Assert
    assert result['status'] == 'error'
    assert result['operation'] == 'pr_merge_queue'


def test_github_ops_exposes_merge_queue_handler():
    # The router key the parser produces (`pr_command == 'merge-queue'`) maps to
    # this imported handler in github_ops.main's dispatch table.
    assert callable(github_ops.cmd_pr_merge_queue)

#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the GitHub `pr merge-queue` verb.

Covers three surfaces:

* The shared `ci_base.build_parser` accepts `pr merge-queue` with the
  `--pr-number` | `--head` flags only — no `--strategy` / `--delete-branch`.
  The merge queue's own branch-protection config dictates the merge method, and
  GitHub rejects `--delete-branch` when a merge queue is enabled, so those flags
  were removed from the shared declaration both providers consume.
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
from _ci_wait_contract import _ok_auth


def _capture_run_gh(*, merge_ok: bool = True):
    """Return a run_gh stub that records argv, plus the captured list."""
    captured: list[list[str]] = []

    def run_gh_stub(args, capture_json=False, timeout=60):
        captured.append(list(args))
        if args[:2] == ['pr', 'merge']:
            return (0, '', '') if merge_ok else (1, '', 'merge queue rejected')
        return 0, '', ''

    return run_gh_stub, captured


def _mq_ns(*, pr_number=42, head=None):
    # merge-queue declares ONLY --pr-number / --head. The enqueue rides on
    # ``gh pr merge --auto`` — the merge queue's own branch-protection config
    # dictates the merge method — so the Namespace carries exactly those two
    # attributes (no strategy / delete_branch).
    return argparse.Namespace(pr_number=pr_number, head=head)


def _base_view_payload(base_branch: str = 'main') -> dict:
    """Minimal ``view_pr_data`` success payload carrying a base branch."""
    return {
        'status': 'success',
        'operation': 'pr_view',
        'pr_number': 42,
        'state': 'open',
        'head_branch': 'feature/x',
        'base_branch': base_branch,
    }


def _install(
    monkeypatch,
    run_gh_stub,
    *,
    discriminator: str | None = None,
    detail: str = 'merge_queue rule active on branch',
    probe_error: str | None = None,
) -> dict:
    """Install the stubs ``cmd_pr_merge_queue`` needs, plus the base-branch probe.

    The enqueue is now CORROBORATED: the handler probes the PR's own base branch
    for a configured merge queue before calling gh, because ``gh pr merge --auto``
    exits zero on an unconfigured base having quietly enabled plain auto-merge.
    The default discriminator is ``eligible_configured`` so the pre-existing
    behavioural tests keep exercising the enqueue path they were written for.
    Returns the probe capture dict.
    """
    if discriminator is None:
        discriminator = github_ops.MERGE_QUEUE_ELIGIBLE_CONFIGURED
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)
    monkeypatch.setattr(
        github_ops, '_resolve_pr_identifier', lambda args, op: ('42', None)
    )
    monkeypatch.setattr(github_ops, 'view_pr_data', lambda head=None: _base_view_payload())
    monkeypatch.setattr(github_ops, 'get_repo_info', lambda: ('octo', 'repo'))

    captured: dict = {'branch': None, 'calls': 0}

    def probe_stub(owner, repo, branch):
        captured['branch'] = branch
        captured['calls'] += 1
        return discriminator, detail, probe_error, None

    monkeypatch.setattr(github_ops, '_probe_merge_queue_state', probe_stub)
    return captured


# ---------------------------------------------------------------------------
# Shared parser acceptance
# ---------------------------------------------------------------------------


def test_ci_base_parser_accepts_pr_merge_queue():
    # Arrange
    parser, _pr_sub, _c, _i, _b = ci_base.build_parser('test')
    # Act
    args = parser.parse_args(['pr', 'merge-queue', '--pr-number', '42'])
    # Assert — merge-queue declares only --pr-number / --head; the removed
    # --strategy / --delete-branch flags are absent from the parsed namespace.
    assert args.pr_command == 'merge-queue'
    assert args.pr_number == 42
    assert not hasattr(args, 'strategy')
    assert not hasattr(args, 'delete_branch')


# ---------------------------------------------------------------------------
# Enqueue behavior — constructed-argv assertion
# ---------------------------------------------------------------------------


def test_cmd_pr_merge_queue_enqueues_via_gh_auto(monkeypatch):
    # Arrange
    run_gh_stub, captured = _capture_run_gh()
    probe = _install(monkeypatch, run_gh_stub)

    # Act — the merge queue's own config dictates the method, so the enqueue is
    # exactly ``gh pr merge --auto`` with no strategy / delete-branch flags.
    result = github_ops.cmd_pr_merge_queue(_mq_ns())

    # Assert — the enqueue rides on `gh pr merge --auto`.
    assert result['status'] == 'success'
    assert result['operation'] == 'pr_merge_queue'
    assert result['enqueued'] is True
    assert result['pr_number'] == 42
    # The claim is corroborated against the PR's OWN base branch, not assumed.
    assert result['base_branch'] == 'main'
    assert result['enqueue_corroboration'] == 'merge_queue rule active on branch'
    assert probe['branch'] == 'main', probe
    merge_call = next(c for c in captured if c[:2] == ['pr', 'merge'])
    assert merge_call == ['pr', 'merge', '42', '--auto']


def test_cmd_pr_merge_queue_omits_strategy_when_unset(monkeypatch):
    # Arrange
    run_gh_stub, captured = _capture_run_gh()
    _install(monkeypatch, run_gh_stub)

    # Act
    github_ops.cmd_pr_merge_queue(_mq_ns())

    # Assert — no strategy-derived method flag is present on the enqueue.
    merge_call = next(c for c in captured if c[:2] == ['pr', 'merge'])
    assert '--merge' not in merge_call
    assert '--squash' not in merge_call
    assert '--rebase' not in merge_call
    assert '--delete-branch' not in merge_call


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


# ---------------------------------------------------------------------------
# Corroboration — `enqueued: true` requires a queue that actually exists
# ---------------------------------------------------------------------------


def test_cmd_pr_merge_queue_returns_error_when_base_has_no_configured_queue(monkeypatch):
    """An unconfigured base branch is an error, not a green `enqueued: true`.

    ``gh pr merge --auto`` exits zero either way — with a queue it enqueues,
    without one it quietly enables PLAIN auto-merge. The exit-code-derived claim
    therefore reported a successful enqueue for a PR that never joined a queue.
    Probing BEFORE the call also prevents that unwanted auto-merge side effect.
    """
    # Arrange
    run_gh_stub, captured = _capture_run_gh()
    probe = _install(
        monkeypatch,
        run_gh_stub,
        discriminator=github_ops.MERGE_QUEUE_ELIGIBLE_UNCONFIGURED,
        detail='no merge_queue rule on branch',
    )

    # Act
    result = github_ops.cmd_pr_merge_queue(_mq_ns())

    # Assert — refusal names the base branch and BOTH remedies, and nothing ran.
    assert result['status'] == 'error', result
    assert result['operation'] == 'pr_merge_queue'
    assert 'main' in result['error'], result
    assert '/marshall-steward' in result['error'], result
    assert 'use_merge_queue' in result['error'], result
    assert captured == [], captured
    assert probe['calls'] == 1, probe


def test_cmd_pr_merge_queue_probe_error_fails_closed(monkeypatch):
    """A probe failure refuses the enqueue rather than guessing it succeeded."""
    # Arrange
    run_gh_stub, captured = _capture_run_gh()
    _install(
        monkeypatch,
        run_gh_stub,
        discriminator=github_ops.MERGE_QUEUE_INELIGIBLE,
        detail='branch rules endpoint unreachable',
        probe_error='the gh token lacks the scope to read repository rulesets',
    )

    # Act
    result = github_ops.cmd_pr_merge_queue(_mq_ns())

    # Assert
    assert result['status'] == 'error', result
    assert 'scope' in result['error'], result
    assert captured == [], captured


def test_github_ops_exposes_merge_queue_handler():
    # The router key the parser produces (`pr_command == 'merge-queue'`) maps to
    # this imported handler in github_ops.main's dispatch table.
    assert callable(github_ops.cmd_pr_merge_queue)

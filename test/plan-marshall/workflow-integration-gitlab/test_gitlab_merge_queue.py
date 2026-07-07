#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the GitLab `pr merge-queue` handler (deliverable 5).

GitLab's platform equivalent of a GitHub merge queue is a **merge train** — a
Premium/Ultimate-tier feature enabled per-project with no stable `glab` CLI
surface. The handler therefore returns an EXPLICIT unsupported error (never a
silent immediate-merge fallback), mirroring the `pr submit-review`
GitLab-no-equivalent pattern, so cross-provider callers notice the mismatch.
"""

import argparse

import gitlab_ops


def _mq_ns():
    return argparse.Namespace(
        pr_number=42, head=None, strategy='merge', delete_branch=False
    )


def test_cmd_pr_merge_queue_returns_unsupported_error():
    # Act
    result = gitlab_ops.cmd_pr_merge_queue(_mq_ns())

    # Assert — explicit error, not a silent success.
    assert result['status'] == 'error'
    assert result['operation'] == 'pr_merge_queue'
    # The message names the merge-train platform equivalent.
    message = ' '.join(str(v) for v in result.values()).lower()
    assert 'merge train' in message


def test_cmd_pr_merge_queue_does_not_engage_glab(monkeypatch):
    # Arrange — fail loudly if the handler ever shells out to glab (it must not,
    # since a silent immediate merge would defeat the requested serialization).
    def _boom(*args, **kwargs):
        raise AssertionError('cmd_pr_merge_queue must not invoke run_glab on GitLab')

    monkeypatch.setattr(gitlab_ops, 'run_glab', _boom, raising=False)

    # Act
    result = gitlab_ops.cmd_pr_merge_queue(_mq_ns())

    # Assert
    assert result['status'] == 'error'


def test_gitlab_ops_exposes_merge_queue_handler():
    # The router key ('pr', 'merge-queue') maps to this imported handler in the
    # gitlab_ops dispatch table.
    assert callable(gitlab_ops.cmd_pr_merge_queue)

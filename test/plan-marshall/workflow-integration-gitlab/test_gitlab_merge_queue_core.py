#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Tests for gitlab_ops.py merge-queue — probe and enable happy paths.
"""

from __future__ import annotations

import argparse
import gitlab_ops
import pytest
from _ci_wait_contract import _ok_auth


def _mq_ns(*, pr_number=42, head=None, strategy='merge', delete_branch=False):
    return argparse.Namespace(pr_number=pr_number, head=head, strategy=strategy, delete_branch=delete_branch)


def _install_common(monkeypatch):
    monkeypatch.setattr(gitlab_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(gitlab_ops, 'get_project_path', lambda: 'group/repo')


def _stub_probe(monkeypatch, discriminator, *, detail='stubbed probe', error=None) -> dict:
    """Stub ``_probe_merge_train_state`` for the pre-enqueue read.

    The probe is PROJECT-scoped and takes no branch argument, so the stub's
    signature mirrors that exactly — a fixture can never drift into asserting a
    per-branch shape GitLab does not have.

    The ``cmd_repo_merge_queue_*`` scenarios deliberately do NOT use this helper:
    they drive the real probe through a stubbed ``run_api`` because the mapping
    from Projects-API response to discriminator is precisely what they assert.
    """
    captured: dict = {'calls': 0}

    def probe_stub():
        captured['calls'] += 1
        return discriminator, detail, error

    monkeypatch.setattr(gitlab_ops, '_probe_merge_train_state', probe_stub)
    return captured


# ---------------------------------------------------------------------------
# pr merge-queue — real merge-train enqueue
# ---------------------------------------------------------------------------
def test_cmd_pr_merge_queue_enqueues_via_merge_train(monkeypatch):
    # Arrange — the project actually runs a train, so the enqueue proceeds.
    _install_common(monkeypatch)
    monkeypatch.setattr(gitlab_ops, '_resolve_mr_iid', lambda args, op: ('42', None))
    _stub_probe(monkeypatch, gitlab_ops.MERGE_QUEUE_ELIGIBLE_CONFIGURED)
    captured: list[list[str]] = []

    def run_glab_stub(args):
        captured.append(list(args))
        return 0, '{"id": 7, "merge_request": {"iid": 42}}', ''

    monkeypatch.setattr(gitlab_ops, 'run_glab', run_glab_stub)

    # Act
    result = gitlab_ops.cmd_pr_merge_queue(_mq_ns())

    # Assert — a REAL POST to the merge-train endpoint, not a fail-loud error.
    assert result['status'] == 'success'
    assert result['operation'] == 'pr_merge_queue'
    assert result['provider'] == 'gitlab'
    assert result['enqueued'] is True
    assert result['merge_train_car_id'] == '7'
    assert captured == [['api', '-X', 'POST', 'projects/group%2Frepo/merge_trains/merge_requests/42']]


# ---------------------------------------------------------------------------
# repo merge-queue probe — merge_trains_enabled → eligibility discriminator
# ---------------------------------------------------------------------------
def test_repo_merge_queue_probe_configured(monkeypatch):
    _install_common(monkeypatch)
    monkeypatch.setattr(gitlab_ops, 'run_api', lambda ep: (0, {'merge_trains_enabled': True}, ''))

    result = gitlab_ops.cmd_repo_merge_queue_probe(argparse.Namespace())
    assert result['status'] == 'success'
    assert result['operation'] == 'repo_merge_queue_probe'
    assert result['provider'] == 'gitlab'
    assert result['eligibility'] == 'eligible_configured'


def test_repo_merge_queue_probe_unconfigured(monkeypatch):
    _install_common(monkeypatch)
    monkeypatch.setattr(gitlab_ops, 'run_api', lambda ep: (0, {'merge_trains_enabled': False}, ''))

    result = gitlab_ops.cmd_repo_merge_queue_probe(argparse.Namespace())
    assert result['eligibility'] == 'eligible_unconfigured'


def test_repo_merge_queue_probe_ineligible_when_field_absent(monkeypatch):
    # The Projects API response lacks merge_trains_enabled → tier does not expose it.
    _install_common(monkeypatch)
    monkeypatch.setattr(gitlab_ops, 'run_api', lambda ep: (0, {'id': 5}, ''))

    result = gitlab_ops.cmd_repo_merge_queue_probe(argparse.Namespace())
    assert result['eligibility'] == 'ineligible'


@pytest.mark.parametrize(
    ('value', 'expected'),
    [
        (True, gitlab_ops.MERGE_QUEUE_ELIGIBLE_CONFIGURED),
        (False, gitlab_ops.MERGE_QUEUE_ELIGIBLE_UNCONFIGURED),
    ],
    ids=['true', 'false'],
)
def test_probe_boolean_merge_trains_enabled_still_establishes_support(monkeypatch, value, expected):
    """Matched negative control: the two real booleans keep their error-free verdicts.

    Without this arm, a non-boolean guard that rejected everything — including
    `True` and `False` — would satisfy the cases above while destroying the
    probe.
    """
    _install_common(monkeypatch)
    monkeypatch.setattr(gitlab_ops, 'run_api', lambda ep: (0, {'merge_trains_enabled': value}, ''))

    discriminator, _detail, error = gitlab_ops._probe_merge_train_state()

    assert discriminator == expected
    assert error is None


def test_probe_absent_merge_trains_enabled_stays_ineligible_with_no_error(monkeypatch):
    """The absent-field branch is a real verdict and must NOT become UNSUPPORTED.

    An absent field means the tier does not expose merge trains — a genuine
    `ineligible` that DID read the project. The non-boolean guard is ordered
    after this branch precisely so tightening the malformed case cannot swallow
    it.
    """
    _install_common(monkeypatch)
    monkeypatch.setattr(gitlab_ops, 'run_api', lambda ep: (0, {'id': 5}, ''))

    discriminator, detail, error = gitlab_ops._probe_merge_train_state()

    assert discriminator == gitlab_ops.MERGE_QUEUE_INELIGIBLE
    assert error is None
    assert 'group/repo' in detail


# ---------------------------------------------------------------------------
# repo merge-queue enable — idempotent / PUT / refuse
# ---------------------------------------------------------------------------
def test_repo_merge_queue_enable_idempotent_when_configured(monkeypatch):
    _install_common(monkeypatch)
    monkeypatch.setattr(gitlab_ops, 'run_api', lambda ep: (0, {'merge_trains_enabled': True}, ''))

    def _boom(args):
        raise AssertionError('enable must not mutate an already-configured project')

    monkeypatch.setattr(gitlab_ops, 'run_glab', _boom)

    result = gitlab_ops.cmd_repo_merge_queue_enable(argparse.Namespace())
    assert result['status'] == 'success'
    assert result['changed'] is False
    assert result['eligibility'] == 'eligible_configured'


def test_repo_merge_queue_enable_sets_flag_when_unconfigured(monkeypatch):
    _install_common(monkeypatch)
    monkeypatch.setattr(gitlab_ops, 'run_api', lambda ep: (0, {'merge_trains_enabled': False}, ''))
    captured: list[list[str]] = []

    def run_glab_stub(args):
        captured.append(list(args))
        return 0, '{"merge_trains_enabled": true}', ''

    monkeypatch.setattr(gitlab_ops, 'run_glab', run_glab_stub)

    result = gitlab_ops.cmd_repo_merge_queue_enable(argparse.Namespace())
    assert result['status'] == 'success'
    assert result['changed'] is True
    assert result['eligibility'] == 'eligible_configured'
    assert captured == [['api', '-X', 'PUT', 'projects/group%2Frepo', '-f', 'merge_trains_enabled=true']]


def test_gitlab_ops_exposes_repo_merge_queue_handlers():
    assert callable(gitlab_ops.cmd_repo_merge_queue_probe)
    assert callable(gitlab_ops.cmd_repo_merge_queue_enable)
    assert callable(gitlab_ops.cmd_pr_merge_queue)


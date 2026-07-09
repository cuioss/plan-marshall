#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the GitLab merge-train surface (deliverable 2).

Three handlers are covered, all with API-shape-faithful fixtures (no live glab):

* ``cmd_pr_merge_queue`` — a REAL merge-train enqueue via
  ``POST /projects/:id/merge_trains/merge_requests/:iid`` (replacing the former
  fail-loud unsupported stub), pinned by a constructed-argv assertion against the
  captured ``run_glab`` invocation.
* ``cmd_repo_merge_queue_probe`` — reads ``merge_trains_enabled`` from
  ``GET /projects/:id`` and maps each state to the shared eligibility
  discriminator, including the auth-scope actionable-error path.
* ``cmd_repo_merge_queue_enable`` — idempotent no-op when already configured,
  ``PUT /projects/:id`` when unconfigured, actionable refusal when ineligible.
"""

import argparse

import gitlab_ops


def _mq_ns(*, pr_number=42, head=None, strategy='merge', delete_branch=False):
    return argparse.Namespace(
        pr_number=pr_number, head=head, strategy=strategy, delete_branch=delete_branch
    )


def _install_common(monkeypatch):
    monkeypatch.setattr(gitlab_ops, 'check_auth', lambda: (True, ''))
    monkeypatch.setattr(gitlab_ops, 'get_project_path', lambda: 'group/repo')


# ---------------------------------------------------------------------------
# pr merge-queue — real merge-train enqueue
# ---------------------------------------------------------------------------


def test_cmd_pr_merge_queue_enqueues_via_merge_train(monkeypatch):
    # Arrange
    _install_common(monkeypatch)
    monkeypatch.setattr(gitlab_ops, '_resolve_mr_iid', lambda args, op: ('42', None))
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
    assert captured == [
        ['api', '-X', 'POST', 'projects/group%2Frepo/merge_trains/merge_requests/42']
    ]


def test_cmd_pr_merge_queue_ineligible_on_403(monkeypatch):
    # Arrange — the project/tier does not offer merge trains.
    _install_common(monkeypatch)
    monkeypatch.setattr(gitlab_ops, '_resolve_mr_iid', lambda args, op: ('42', None))
    monkeypatch.setattr(
        gitlab_ops, 'run_glab', lambda args: (1, '', 'HTTP 403 Forbidden')
    )

    # Act
    result = gitlab_ops.cmd_pr_merge_queue(_mq_ns())

    # Assert — actionable ineligible error naming merge trains, never a stack trace.
    assert result['status'] == 'error'
    assert result['operation'] == 'pr_merge_queue'
    message = ' '.join(str(v) for v in result.values()).lower()
    assert 'merge train' in message


def test_cmd_pr_merge_queue_ineligible_on_404(monkeypatch):
    _install_common(monkeypatch)
    monkeypatch.setattr(gitlab_ops, '_resolve_mr_iid', lambda args, op: ('42', None))
    monkeypatch.setattr(
        gitlab_ops, 'run_glab', lambda args: (1, '', 'HTTP 404 Not Found')
    )

    result = gitlab_ops.cmd_pr_merge_queue(_mq_ns())
    assert result['status'] == 'error'
    assert result['operation'] == 'pr_merge_queue'


def test_cmd_pr_merge_queue_generic_error_is_not_ineligible(monkeypatch):
    # A non-403/404 failure is a plain enqueue error (not the ineligible branch).
    _install_common(monkeypatch)
    monkeypatch.setattr(gitlab_ops, '_resolve_mr_iid', lambda args, op: ('42', None))
    monkeypatch.setattr(
        gitlab_ops, 'run_glab', lambda args: (1, '', 'HTTP 500 Internal Server Error')
    )

    result = gitlab_ops.cmd_pr_merge_queue(_mq_ns())
    assert result['status'] == 'error'
    message = ' '.join(str(v) for v in result.values()).lower()
    assert 'failed to enqueue' in message


def test_cmd_pr_merge_queue_auth_failure(monkeypatch):
    monkeypatch.setattr(gitlab_ops, 'check_auth', lambda: (False, 'not authed'))
    result = gitlab_ops.cmd_pr_merge_queue(_mq_ns())
    assert result['status'] == 'error'
    assert result['operation'] == 'pr_merge_queue'


# ---------------------------------------------------------------------------
# repo merge-queue probe — merge_trains_enabled → eligibility discriminator
# ---------------------------------------------------------------------------


def test_repo_merge_queue_probe_configured(monkeypatch):
    _install_common(monkeypatch)
    monkeypatch.setattr(
        gitlab_ops, 'run_api', lambda ep: (0, {'merge_trains_enabled': True}, '')
    )

    result = gitlab_ops.cmd_repo_merge_queue_probe(argparse.Namespace())
    assert result['status'] == 'success'
    assert result['operation'] == 'repo_merge_queue_probe'
    assert result['provider'] == 'gitlab'
    assert result['eligibility'] == 'eligible_configured'


def test_repo_merge_queue_probe_unconfigured(monkeypatch):
    _install_common(monkeypatch)
    monkeypatch.setattr(
        gitlab_ops, 'run_api', lambda ep: (0, {'merge_trains_enabled': False}, '')
    )

    result = gitlab_ops.cmd_repo_merge_queue_probe(argparse.Namespace())
    assert result['eligibility'] == 'eligible_unconfigured'


def test_repo_merge_queue_probe_ineligible_when_field_absent(monkeypatch):
    # The Projects API response lacks merge_trains_enabled → tier does not expose it.
    _install_common(monkeypatch)
    monkeypatch.setattr(gitlab_ops, 'run_api', lambda ep: (0, {'id': 5}, ''))

    result = gitlab_ops.cmd_repo_merge_queue_probe(argparse.Namespace())
    assert result['eligibility'] == 'ineligible'


def test_repo_merge_queue_probe_auth_scope_error(monkeypatch):
    _install_common(monkeypatch)
    monkeypatch.setattr(gitlab_ops, 'run_api', lambda ep: (1, None, 'HTTP 403 Forbidden'))

    result = gitlab_ops.cmd_repo_merge_queue_probe(argparse.Namespace())
    # Auth-scope failure surfaces the actionable error, not a discriminator.
    assert result['status'] == 'error'
    assert result['operation'] == 'repo_merge_queue_probe'
    message = ' '.join(str(v) for v in result.values()).lower()
    assert 'scope' in message or 'permission' in message


def test_repo_merge_queue_probe_auth_failure(monkeypatch):
    monkeypatch.setattr(gitlab_ops, 'check_auth', lambda: (False, 'not authed'))
    result = gitlab_ops.cmd_repo_merge_queue_probe(argparse.Namespace())
    assert result['status'] == 'error'


# ---------------------------------------------------------------------------
# repo merge-queue enable — idempotent / PUT / refuse
# ---------------------------------------------------------------------------


def test_repo_merge_queue_enable_idempotent_when_configured(monkeypatch):
    _install_common(monkeypatch)
    monkeypatch.setattr(
        gitlab_ops, 'run_api', lambda ep: (0, {'merge_trains_enabled': True}, '')
    )

    def _boom(args):
        raise AssertionError('enable must not mutate an already-configured project')

    monkeypatch.setattr(gitlab_ops, 'run_glab', _boom)

    result = gitlab_ops.cmd_repo_merge_queue_enable(argparse.Namespace())
    assert result['status'] == 'success'
    assert result['changed'] is False
    assert result['eligibility'] == 'eligible_configured'


def test_repo_merge_queue_enable_sets_flag_when_unconfigured(monkeypatch):
    _install_common(monkeypatch)
    monkeypatch.setattr(
        gitlab_ops, 'run_api', lambda ep: (0, {'merge_trains_enabled': False}, '')
    )
    captured: list[list[str]] = []

    def run_glab_stub(args):
        captured.append(list(args))
        return 0, '{"merge_trains_enabled": true}', ''

    monkeypatch.setattr(gitlab_ops, 'run_glab', run_glab_stub)

    result = gitlab_ops.cmd_repo_merge_queue_enable(argparse.Namespace())
    assert result['status'] == 'success'
    assert result['changed'] is True
    assert result['eligibility'] == 'eligible_configured'
    assert captured == [
        ['api', '-X', 'PUT', 'projects/group%2Frepo', '-f', 'merge_trains_enabled=true']
    ]


def test_repo_merge_queue_enable_refuses_when_ineligible(monkeypatch):
    _install_common(monkeypatch)
    monkeypatch.setattr(gitlab_ops, 'run_api', lambda ep: (0, {'id': 5}, ''))

    def _boom(args):
        raise AssertionError('enable must not mutate an ineligible project')

    monkeypatch.setattr(gitlab_ops, 'run_glab', _boom)

    result = gitlab_ops.cmd_repo_merge_queue_enable(argparse.Namespace())
    assert result['status'] == 'error'
    assert result['operation'] == 'repo_merge_queue_enable'
    message = ' '.join(str(v) for v in result.values()).lower()
    assert 'merge train' in message


def test_gitlab_ops_exposes_repo_merge_queue_handlers():
    assert callable(gitlab_ops.cmd_repo_merge_queue_probe)
    assert callable(gitlab_ops.cmd_repo_merge_queue_enable)
    assert callable(gitlab_ops.cmd_pr_merge_queue)

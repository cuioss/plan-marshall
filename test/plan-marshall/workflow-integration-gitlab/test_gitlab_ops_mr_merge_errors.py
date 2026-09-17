#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Tests for gitlab_ops.py mr-merge — refusals and failure envelopes.
"""

from __future__ import annotations

import argparse
import gitlab_ops
import pytest
from _ci_wait_contract import _ok_auth


def _install_common(monkeypatch):
    """Install auth + project-path stubs used by every scenario.

    Tests override ``run_glab`` explicitly below; this helper only installs
    the pieces that are orthogonal to the merge/delete wiring.
    """
    monkeypatch.setattr(gitlab_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(
        gitlab_ops,
        'get_project_path',
        lambda: 'octo/repo',
    )
    # Every merge-shaped verb now runs the project merge-train preflight. Without
    # it these tests would exercise the preflight's fail-closed path instead of
    # the merge/delete wiring they assert.
    _install_merge_train_probe(monkeypatch)


def _mr_view_success_payload(state: str = 'merged') -> dict:
    """Minimal ``view_pr_data`` success payload with a source branch.

    ``state`` defaults to ``'merged'`` because this same stub feeds the POST-merge
    corroboration re-read: ``cmd_pr_merge`` establishes ``merged`` from
    ``state == 'merged'`` rather than the glab exit code (GitLab exposes no
    ``merged_at`` on this surface, so state is the whole verdict). Scenarios that
    need the NON-corroborating shape pass ``state`` explicitly.

    The readiness poll keys on ``merge_state``, not ``state``, so the default
    does not perturb the safe-merge polling scenarios.
    """
    return {
        'status': 'success',
        'operation': 'pr_view',
        'pr_number': 42,
        'pr_url': 'https://gitlab.com/octo/repo/-/merge_requests/42',
        'state': state,
        'title': 'T',
        'head_branch': 'feature/x',
        'base_branch': 'main',
        'is_draft': 'false',
        'mergeable': 'mergeable',
        'merge_state': 'can_be_merged',
        'review_decision': 'approved',
    }


def _install_merge_train_probe(
    monkeypatch,
    *,
    discriminator: str | None = None,
    detail: str = 'merge_trains_enabled=false',
    error: str | None = None,
) -> dict:
    """Stub ``gitlab_ops._probe_merge_train_state`` for the merge-shaped preflight.

    The GitLab probe is PROJECT-scoped and takes NO branch argument — merge
    trains are a per-project flag, unlike a GitHub merge queue which is
    base-branch-scoped. The stub mirrors that signature exactly so a fixture can
    never drift into asserting a per-branch shape GitLab does not have.

    Defaults to ``eligible_unconfigured`` (no train) so the pre-existing merge
    scenarios keep exercising the immediate-merge path they were written for.
    Returns a capture dict recording the call count.
    """
    if discriminator is None:
        discriminator = gitlab_ops.MERGE_QUEUE_ELIGIBLE_UNCONFIGURED
    captured: dict = {'calls': 0}

    def probe_stub():
        captured['calls'] += 1
        return discriminator, detail, error

    monkeypatch.setattr(gitlab_ops, '_probe_merge_train_state', probe_stub)
    return captured


def _capture_run_glab(
    *,
    merge_ok: bool = True,
    delete_mode: str = 'ok',
):
    """Build a ``run_glab`` stub + captured args list.

    Parameters
    ----------
    merge_ok:
        When False, the ``mr merge`` call returns a non-zero exit code,
        simulating a merge failure.
    delete_mode:
        One of:
          * ``'ok'``      — DELETE returns 204 No Content (success).
          * ``'gone'``    — DELETE returns HTTP 422 (already gone).
          * ``'notfound'``— DELETE returns HTTP 404 (already gone).
          * ``'error'``   — DELETE returns a generic HTTP 500.
    """
    captured: list[list[str]] = []

    def run_glab_stub(args):
        captured.append(list(args))

        if args[:2] == ['mr', 'merge']:
            if merge_ok:
                return 0, '', ''
            return 1, '', 'merge conflict'

        # DELETE /projects/{id}/repository/branches/{branch}
        if args[:3] == ['api', '-X', 'DELETE']:
            if delete_mode == 'ok':
                return 0, '', ''
            if delete_mode == 'gone':
                return 1, '', 'HTTP 422: Reference does not exist'
            if delete_mode == 'notfound':
                return 1, '', 'HTTP 404: Not Found'
            if delete_mode == 'error':
                return 1, '', 'HTTP 500: boom'

        # Any other call (should not happen in these tests) — return empty OK.
        return 0, '', ''

    return run_glab_stub, captured


def _merge_ns(*, delete_branch: bool, pr_number: int | None = 42, head: str | None = None):
    return argparse.Namespace(
        pr_number=pr_number,
        head=head,
        strategy='merge',
        delete_branch=delete_branch,
    )


# ---------------------------------------------------------------------------
# cmd_pr_safe_merge — poll readiness then merge (GitLab: poll-only, NO admin)
# ---------------------------------------------------------------------------
#
# Symmetric to ``test_github_ops_pr_merge.py`` but GitLab implements Layer 1
# only: poll the MR ``merge_status`` until ``can_be_merged``, then delegate to
# ``cmd_pr_merge``. There is no admin-merge equivalent — the
# ``--admin-merge-on-stuck-state`` knob is accepted for API uniformity but
# ignored, and a stuck-past-timeout MR returns a canonical error rather than
# force-merging.
def _safe_merge_ns(
    *,
    pr_number: int | None = 42,
    head: str | None = None,
    strategy: str = 'merge',
    delete_branch: bool = False,
    admin_merge_on_stuck_state: bool = False,
    poll_timeout: int = 300,
    poll_interval: int = 0,
):
    """Build the argparse.Namespace cmd_pr_safe_merge expects.

    ``poll_interval`` defaults to 0 so the real ``poll_until`` loop never sleeps
    during the polled-clean scenarios.
    """
    return argparse.Namespace(
        pr_number=pr_number,
        head=head,
        strategy=strategy,
        delete_branch=delete_branch,
        admin_merge_on_stuck_state=admin_merge_on_stuck_state,
        poll_timeout=poll_timeout,
        poll_interval=poll_interval,
    )


def _safe_merge_view_payload(merge_state: str) -> dict:
    """A ``view_pr_data`` success payload with the given raw ``merge_state``."""
    payload = _mr_view_success_payload()
    payload['merge_state'] = merge_state
    return payload


# ---------------------------------------------------------------------------
# Project scope: the guards fail closed on a project they never identified
# ---------------------------------------------------------------------------
#
# Every scenario above stubs ``_probe_merge_train_state``, so the probe's OWN
# scope handling has no coverage there. The cases below drive the REAL probe
# through a stubbed Projects API, because what they assert — which outcomes
# carry an actionable error, and which refusals name the concrete project — is
# a property of the probe itself.
def _install_unresolvable_scope(monkeypatch) -> None:
    """Auth OK, project scope unresolvable, REAL probe, Projects API trip-wired.

    The trip-wire is the negative control: an unresolved scope must refuse
    before any API call, so reaching ``run_api`` is itself the failure.
    """
    monkeypatch.setattr(gitlab_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(gitlab_ops, 'get_project_path', lambda: None)

    def _boom(endpoint):  # pragma: no cover — guard only
        raise AssertionError('an unresolved scope must not reach the Projects API')

    monkeypatch.setattr(gitlab_ops, 'run_api', _boom)


#: Every refusal reachable AFTER the project path resolved, as
#: ``(projects-API result, id)``. The three probe outcomes that establish
#: nothing about the project they DID reach, plus the positive train-required
#: verdict — which is the whole of the set, because the remaining two probe
#: outcomes (``eligible_unconfigured`` and an error-free ``ineligible``) permit
#: the merge rather than refusing it.
_KNOWN_PATH_REFUSALS: list[tuple[tuple, str]] = [
    ((1, None, 'HTTP 403 Forbidden'), 'auth_scope'),
    ((1, None, 'HTTP 500 Internal Server Error'), 'api_failure'),
    ((0, ['not', 'an', 'object'], ''), 'malformed_response'),
    ((0, {'merge_trains_enabled': True}, ''), 'train_required'),
]


# --- (b) stuck-state timeout, no admin fallback → error, no merge ------------
def test_safe_merge_timeout_returns_error_no_merge(monkeypatch):
    """Timed-out while not ready → canonical error, no merge, no --admin."""
    _install_common(monkeypatch)
    run_glab_stub, captured = _capture_run_glab(merge_ok=True, delete_mode='ok')
    monkeypatch.setattr(gitlab_ops, 'run_glab', run_glab_stub)
    monkeypatch.setattr(
        gitlab_ops,
        'poll_until',
        lambda *a, **kw: {
            'timed_out': True,
            'duration_sec': 300,
            'polls': 5,
            'last_data': _safe_merge_view_payload('cannot_be_merged'),
        },
    )

    result = gitlab_ops.cmd_pr_safe_merge(_safe_merge_ns(admin_merge_on_stuck_state=False))

    assert result['status'] == 'error', result
    assert result['operation'] == 'pr_safe_merge'
    assert 'no admin fallback' in result['error'], result
    # No merge was attempted at all.
    merge_calls = [c for c in captured if c[:2] == ['mr', 'merge']]
    assert merge_calls == [], merge_calls


# ---------------------------------------------------------------------------
# Merge-train preflight + post-merge corroboration (GitLab parity)
# ---------------------------------------------------------------------------
#
# Both guards were absent on GitLab: cmd_pr_merge and cmd_pr_safe_merge carried
# NO merge-train preflight at all (cmd_pr_safe_merge unlike its GitHub sibling),
# and ``merged`` was set from the glab exit code inside the --delete-branch
# branch. The probe is PROJECT-scoped here, not base-branch-scoped.
def test_mr_merge_refuses_when_base_merge_queue_required(monkeypatch):
    """Merge trains enabled on the project refuse the immediate merge."""
    _install_common(monkeypatch)
    probe = _install_merge_train_probe(
        monkeypatch,
        discriminator=gitlab_ops.MERGE_QUEUE_ELIGIBLE_CONFIGURED,
        detail='merge_trains_enabled=true',
    )
    run_glab_stub, captured = _capture_run_glab(merge_ok=True, delete_mode='ok')
    monkeypatch.setattr(gitlab_ops, 'run_glab', run_glab_stub)
    monkeypatch.setattr(gitlab_ops, 'view_pr_data', lambda head=None: _mr_view_success_payload())

    result = gitlab_ops.cmd_pr_merge(_merge_ns(delete_branch=True))

    assert result['status'] == 'error', result
    assert result['operation'] == 'pr_merge'
    # The message names BOTH remedies.
    assert 'ci pr merge-queue' in result['error'], result
    assert 'use_merge_queue' in result['error'], result
    assert '/marshall-steward' in result['error'], result
    # Nothing ran: no merge, no branch delete.
    assert captured == [], captured
    assert probe['calls'] == 1, probe


def test_mr_merge_preflight_probe_error_fails_closed(monkeypatch):
    """An unresolvable merge-train state refuses the merge rather than merging blind."""
    _install_common(monkeypatch)
    _install_merge_train_probe(
        monkeypatch,
        discriminator=gitlab_ops.MERGE_QUEUE_UNSUPPORTED,
        detail='project merge-train probe failed',
        error='project merge-train probe failed',
    )
    run_glab_stub, captured = _capture_run_glab(merge_ok=True, delete_mode='ok')
    monkeypatch.setattr(gitlab_ops, 'run_glab', run_glab_stub)
    monkeypatch.setattr(gitlab_ops, 'view_pr_data', lambda head=None: _mr_view_success_payload())

    result = gitlab_ops.cmd_pr_merge(_merge_ns(delete_branch=True))

    assert result['status'] == 'error', result
    assert 'probe failed' in result['error'], result
    assert captured == [], captured


@pytest.mark.parametrize('post_merge_state', ['open', 'closed', 'unknown'])
def test_mr_merge_uncorroborated_merge_refuses_and_skips_branch_delete(monkeypatch, post_merge_state):
    """Corroboration lock: an uncorroborated merge reports error and deletes NOTHING.

    GitLab corroborates from ``state == 'merged'`` — ``view_pr_data`` surfaces no
    ``merged_at`` here, so state is the whole verdict. The verdict is established
    BEFORE the branch-delete REST call, so a merge that never landed can never
    take the source branch down with it.
    """
    _install_common(monkeypatch)
    run_glab_stub, captured = _capture_run_glab(merge_ok=True, delete_mode='ok')
    monkeypatch.setattr(gitlab_ops, 'run_glab', run_glab_stub)
    monkeypatch.setattr(gitlab_ops, 'view_pr_data', lambda head=None: _mr_view_success_payload(state=post_merge_state))

    result = gitlab_ops.cmd_pr_merge(_merge_ns(delete_branch=True))

    assert result['status'] == 'error', result
    assert result['operation'] == 'pr_merge'
    assert 'corroborate' in result['error'].lower(), result
    # The merge command DID run, but no REST DELETE followed it.
    merge_calls = [c for c in captured if c[:2] == ['mr', 'merge']]
    assert len(merge_calls) == 1, merge_calls
    delete_calls = [c for c in captured if c[:3] == ['api', '-X', 'DELETE']]
    assert delete_calls == [], delete_calls


def test_safe_merge_refuses_when_base_merge_queue_required(monkeypatch):
    """safe-merge gains the merge-train preflight it previously lacked entirely.

    Its GitHub sibling has carried a queue preflight; the GitLab handler had NONE
    — the asymmetry this test locks closed. The refusal fires BEFORE the
    readiness poll, so no poll budget is spent on a merge that must not happen.
    """
    _install_common(monkeypatch)
    _install_merge_train_probe(
        monkeypatch,
        discriminator=gitlab_ops.MERGE_QUEUE_ELIGIBLE_CONFIGURED,
        detail='merge_trains_enabled=true',
    )
    run_glab_stub, captured = _capture_run_glab(merge_ok=True, delete_mode='ok')
    monkeypatch.setattr(gitlab_ops, 'run_glab', run_glab_stub)
    view_calls = {'i': 0}

    def counting_view(head=None):
        view_calls['i'] += 1
        return _safe_merge_view_payload('can_be_merged')

    monkeypatch.setattr(gitlab_ops, 'view_pr_data', counting_view)

    result = gitlab_ops.cmd_pr_safe_merge(_safe_merge_ns())

    assert result['status'] == 'error', result
    assert result['operation'] == 'pr_safe_merge'
    assert 'ci pr merge-queue' in result['error'], result
    assert 'use_merge_queue' in result['error'], result
    # Neither the readiness poll nor any merge ran.
    assert view_calls['i'] == 0, view_calls
    assert captured == [], captured


def test_mr_merge_refuses_when_project_scope_unresolvable(monkeypatch):
    """An unresolvable project scope refuses the merge and runs no merge command.

    The unresolvable scope used to return ``ineligible`` with no error, which
    ``_refuse_on_required_merge_train`` read as "no train to bypass" and let
    through — issuing a merge against a project nothing had identified.
    """
    _install_unresolvable_scope(monkeypatch)
    run_glab_stub, captured = _capture_run_glab(merge_ok=True, delete_mode='ok')
    monkeypatch.setattr(gitlab_ops, 'run_glab', run_glab_stub)
    monkeypatch.setattr(gitlab_ops, 'view_pr_data', lambda head=None: _mr_view_success_payload())

    result = gitlab_ops.cmd_pr_merge(_merge_ns(delete_branch=True))

    assert result['status'] == 'error', result
    assert result['operation'] == 'pr_merge'
    # ``run_glab`` is stubbed to SUCCEED, so a merge that was issued would have
    # been reported as a landed merge. Its absence is the contract.
    merge_calls = [c for c in captured if c[:2] == ['mr', 'merge']]
    assert merge_calls == [], merge_calls
    assert captured == [], captured


def test_scope_resolution_failure_message_names_the_scope_not_a_path(monkeypatch):
    """The scope-resolution refusal names the unresolved scope and NO project path.

    Nothing resolved a project, so interpolating one would report a scope the
    probe never established.
    """
    _install_unresolvable_scope(monkeypatch)
    run_glab_stub, _captured = _capture_run_glab(merge_ok=True, delete_mode='ok')
    monkeypatch.setattr(gitlab_ops, 'run_glab', run_glab_stub)

    result = gitlab_ops.cmd_pr_merge(_merge_ns(delete_branch=False))

    message = ' '.join(str(v) for v in result.values())
    assert 'scope could not be resolved' in message, result
    assert 'merge_trains_enabled' in message, result
    assert 'octo/repo' not in message, result
    assert 'projects/' not in message, result


@pytest.mark.parametrize(
    'api_result',
    [result for result, _ in _KNOWN_PATH_REFUSALS],
    ids=[case_id for _, case_id in _KNOWN_PATH_REFUSALS],
)
def test_known_path_refusal_names_the_concrete_project(monkeypatch, api_result):
    """Every refusal reached after resolution succeeded names the resolved project.

    A refusal that names no project cannot be acted on when several checkouts
    are in play — the reader cannot tell which project's setting to change.
    """
    monkeypatch.setattr(gitlab_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(gitlab_ops, 'get_project_path', lambda: 'octo/repo')
    monkeypatch.setattr(gitlab_ops, 'run_api', lambda endpoint: api_result)
    run_glab_stub, captured = _capture_run_glab(merge_ok=True, delete_mode='ok')
    monkeypatch.setattr(gitlab_ops, 'run_glab', run_glab_stub)
    monkeypatch.setattr(gitlab_ops, 'view_pr_data', lambda head=None: _mr_view_success_payload())

    result = gitlab_ops.cmd_pr_merge(_merge_ns(delete_branch=True))

    assert result['status'] == 'error', result
    message = ' '.join(str(v) for v in result.values())
    assert 'octo/repo' in message, result
    # Each of these refuses BEFORE the side effect.
    assert captured == [], captured


@pytest.mark.parametrize(
    'api_result',
    [result for result, _ in _KNOWN_PATH_REFUSALS],
    ids=[case_id for _, case_id in _KNOWN_PATH_REFUSALS],
)
def test_safe_merge_known_path_refusal_names_the_concrete_project(monkeypatch, api_result):
    """``safe-merge`` shares the preflight, so it names the project identically.

    It refuses before spending any of the readiness-poll budget.
    """
    monkeypatch.setattr(gitlab_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(gitlab_ops, 'get_project_path', lambda: 'octo/repo')
    monkeypatch.setattr(gitlab_ops, 'run_api', lambda endpoint: api_result)
    run_glab_stub, captured = _capture_run_glab(merge_ok=True, delete_mode='ok')
    monkeypatch.setattr(gitlab_ops, 'run_glab', run_glab_stub)
    view_calls = {'i': 0}

    def counting_view(head=None):
        view_calls['i'] += 1
        return _safe_merge_view_payload('can_be_merged')

    monkeypatch.setattr(gitlab_ops, 'view_pr_data', counting_view)

    result = gitlab_ops.cmd_pr_safe_merge(_safe_merge_ns())

    assert result['status'] == 'error', result
    assert result['operation'] == 'pr_safe_merge'
    message = ' '.join(str(v) for v in result.values())
    assert 'octo/repo' in message, result
    assert view_calls['i'] == 0, view_calls
    assert captured == [], captured


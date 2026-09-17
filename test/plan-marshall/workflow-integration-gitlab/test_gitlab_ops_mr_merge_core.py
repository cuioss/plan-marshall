#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Tests for gitlab_ops.py mr-merge — happy path, polling, and auto-merge.
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


def _assert_no_remove_source_branch_flag(captured_calls: list[list[str]]) -> None:
    """No ``--remove-source-branch`` may appear in ANY captured glab invocation."""
    for call in captured_calls:
        assert '--remove-source-branch' not in call, (
            f'cmd_pr_merge leaked --remove-source-branch into glab args: {call}'
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


def _sequenced_view_pr_data(states: list[str]):
    """Build a stateful ``view_pr_data`` stub returning ``states`` in order.

    The final state is repeated for any extra calls (e.g. the source-branch
    resolution ``cmd_pr_merge`` issues for ``--delete-branch``).
    """
    calls = {'i': 0}

    def stub(head=None):
        idx = min(calls['i'], len(states) - 1)
        calls['i'] += 1
        return _safe_merge_view_payload(states[idx])

    return stub, calls


# ---------------------------------------------------------------------------
# cmd_pr_auto_merge — disposition reporting, not an exit-code-derived boolean
# ---------------------------------------------------------------------------
#
# ``glab mr merge {iid} --when-pipeline-succeeds [--squash]`` has TWO
# dispositions decided by the project's merge-train setting, and the exit code is
# identical either way — the same defect class its GitHub sibling carried.
def _auto_merge_ns(*, pr_number: int | None = 42, head: str | None = None, strategy: str = 'squash'):
    return argparse.Namespace(pr_number=pr_number, head=head, strategy=strategy)


# --- (a) successful merge after poll (mergeable state reached) ---------------
def test_safe_merge_can_be_merged_on_first_poll(monkeypatch):
    """An MR already ``can_be_merged`` merges on the first poll via cmd_pr_merge."""
    _install_common(monkeypatch)
    run_glab_stub, captured = _capture_run_glab(merge_ok=True, delete_mode='ok')
    monkeypatch.setattr(gitlab_ops, 'run_glab', run_glab_stub)
    monkeypatch.setattr(gitlab_ops, 'view_pr_data', lambda head=None: _safe_merge_view_payload('can_be_merged'))

    result = gitlab_ops.cmd_pr_safe_merge(_safe_merge_ns())

    assert result['status'] == 'success', result
    assert result['operation'] == 'pr_safe_merge'
    assert result['merge_path'] == 'polled_clean'
    assert result['polls'] >= 1
    assert 'duration_sec' in result

    # Delegation goes through the normal merge — never a force/override flag.
    merge_call = next(c for c in captured if c[:2] == ['mr', 'merge'])
    assert '--admin' not in merge_call, merge_call
    _assert_no_remove_source_branch_flag(captured)


def test_safe_merge_recheck_then_can_be_merged(monkeypatch):
    """An MR that is recheck-pending then ready keeps polling, then merges."""
    _install_common(monkeypatch)
    run_glab_stub, _captured = _capture_run_glab(merge_ok=True, delete_mode='ok')
    monkeypatch.setattr(gitlab_ops, 'run_glab', run_glab_stub)
    view_stub, view_calls = _sequenced_view_pr_data(
        ['cannot_be_merged_recheck', 'cannot_be_merged_recheck', 'can_be_merged']
    )
    monkeypatch.setattr(gitlab_ops, 'view_pr_data', view_stub)

    result = gitlab_ops.cmd_pr_safe_merge(_safe_merge_ns(poll_interval=0))

    assert result['status'] == 'success', result
    assert result['merge_path'] == 'polled_clean'
    # The loop ran at least three readiness polls before reaching can_be_merged.
    assert view_calls['i'] >= 3, view_calls


# --- (c) --admin-merge-on-stuck-state accepted but IGNORED on GitLab ----------
def test_safe_merge_admin_knob_ignored_on_gitlab(monkeypatch):
    """The admin knob is accepted but has NO effect: stuck → error, no merge."""
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

    result = gitlab_ops.cmd_pr_safe_merge(_safe_merge_ns(admin_merge_on_stuck_state=True))

    # The knob does not unlock a force-merge on GitLab.
    assert result['status'] == 'error', result
    assert 'no admin fallback' in result['error'], result
    # glab was never invoked with a merge nor any admin/override flag.
    merge_calls = [c for c in captured if c[:2] == ['mr', 'merge']]
    assert merge_calls == [], merge_calls
    for call in captured:
        assert '--admin' not in call, call


# --- (d) --delete-branch round-trips through the shared REST-delete follow-up -
def test_safe_merge_delete_branch_round_trip(monkeypatch):
    """A polled-clean safe-merge with --delete-branch deletes via the REST leaf."""
    _install_common(monkeypatch)
    run_glab_stub, captured = _capture_run_glab(merge_ok=True, delete_mode='ok')
    monkeypatch.setattr(gitlab_ops, 'run_glab', run_glab_stub)
    monkeypatch.setattr(gitlab_ops, 'view_pr_data', lambda head=None: _safe_merge_view_payload('can_be_merged'))

    result = gitlab_ops.cmd_pr_safe_merge(_safe_merge_ns(delete_branch=True))

    assert result['status'] == 'success', result
    assert result['merge_path'] == 'polled_clean'
    assert result['branch_deleted'] == 'feature/x'
    assert result['already_gone'] is False

    # Branch delete went through the REST leaf, not local git nor a merge flag.
    delete_calls = [c for c in captured if c[:3] == ['api', '-X', 'DELETE']]
    assert len(delete_calls) == 1, delete_calls
    assert delete_calls[0][-1] == 'projects/octo%2Frepo/repository/branches/feature%2Fx'
    _assert_no_remove_source_branch_flag(captured)


# --- existing cmd_pr_merge / cmd_pr_auto_merge remain unaffected --------------
def test_pr_merge_unaffected_no_safe_merge_fields(monkeypatch):
    """cmd_pr_merge still returns the lean shape with no safe-merge fields."""
    _install_common(monkeypatch)
    run_glab_stub, _captured = _capture_run_glab(merge_ok=True, delete_mode='ok')
    monkeypatch.setattr(gitlab_ops, 'run_glab', run_glab_stub)
    monkeypatch.setattr(gitlab_ops, 'view_pr_data', lambda head=None: _mr_view_success_payload())

    result = gitlab_ops.cmd_pr_merge(_merge_ns(delete_branch=False))

    assert result['status'] == 'success', result
    assert result['operation'] == 'pr_merge'
    for key in ('merge_path', 'polls', 'duration_sec'):
        assert key not in result, (key, result)


def test_mr_auto_merge_reports_enabled_disposition_when_unconfigured(monkeypatch):
    """No merge train → a plain when-pipeline-succeeds schedule → ``enabled``."""
    _install_common(monkeypatch)
    run_glab_stub, captured = _capture_run_glab(merge_ok=True, delete_mode='ok')
    monkeypatch.setattr(gitlab_ops, 'run_glab', run_glab_stub)

    result = gitlab_ops.cmd_pr_auto_merge(_auto_merge_ns())

    assert result['status'] == 'success', result
    assert result['operation'] == 'pr_auto_merge'
    assert result['disposition'] == 'enabled', result
    # The exit-code-derived key is REMOVED with no alias.
    assert 'enabled' not in result, result
    merge_call = next(c for c in captured if c[:2] == ['mr', 'merge'])
    assert '--when-pipeline-succeeds' in merge_call, merge_call


def test_mr_auto_merge_reports_train_disposition_when_configured(monkeypatch):
    """Merge trains enabled → the MR joins the TRAIN, not a plain schedule.

    The GitLab-side mirror of the GitHub auto-merge disposition test: the glab
    call succeeds identically in both cases, so only the project probe can tell
    the two dispositions apart.
    """
    _install_common(monkeypatch)
    probe = _install_merge_train_probe(
        monkeypatch,
        discriminator=gitlab_ops.MERGE_QUEUE_ELIGIBLE_CONFIGURED,
        detail='merge_trains_enabled=true',
    )
    run_glab_stub, _captured = _capture_run_glab(merge_ok=True, delete_mode='ok')
    monkeypatch.setattr(gitlab_ops, 'run_glab', run_glab_stub)

    result = gitlab_ops.cmd_pr_auto_merge(_auto_merge_ns())

    assert result['status'] == 'success', result
    assert result['disposition'] == 'enqueued', result
    assert result['disposition_detail'] == 'merge_trains_enabled=true', result
    assert 'enabled' not in result, result
    # ``_install_common`` installs its own probe, so this scenario's probe is the
    # second registration; only its own call is counted here.
    assert probe['calls'] == 1, probe


def test_mr_auto_merge_probe_error_fails_closed(monkeypatch):
    """An unresolvable train state is an error, never a guessed disposition."""
    _install_common(monkeypatch)
    _install_merge_train_probe(
        monkeypatch,
        discriminator=gitlab_ops.MERGE_QUEUE_UNSUPPORTED,
        detail='project merge-train probe failed',
        error='project merge-train probe failed',
    )
    run_glab_stub, captured = _capture_run_glab(merge_ok=True, delete_mode='ok')
    monkeypatch.setattr(gitlab_ops, 'run_glab', run_glab_stub)

    result = gitlab_ops.cmd_pr_auto_merge(_auto_merge_ns())

    assert result['status'] == 'error', result
    assert 'probe failed' in result['error'], result
    # The probe precedes the call, so no auto-merge was scheduled as a side effect.
    assert captured == [], captured


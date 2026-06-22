#!/usr/bin/env python3
"""Tests for cmd_pr_merge (MR merge) branch-delete refactor — GitLab.

Symmetric to ``test_github_ops_pr_merge.py`` for the GitHub provider.

After the refactor:
* ``cmd_pr_merge`` MUST NOT pass ``--remove-source-branch`` (the GitLab mapping
  of ``--delete-branch``) to ``glab mr merge``.
* When the caller requests ``--delete-branch``, the merge is performed first
  and (on success) the MR source branch is deleted remotely via
  ``cmd_branch_delete`` (REST
  ``DELETE /projects/{id}/repository/branches/{branch}``).
* No local git state (checkout, ``git branch -D``) may be touched by this
  handler — that is the caller's responsibility.

The regression guard for the lesson-2026-04-17-19-002 fork exercises the
worktree scenario that broke with ``glab mr merge --remove-source-branch``:
here the merge must finish cleanly and the branch delete must round-trip
purely through the REST leaf, never through local git.
"""

import argparse

import gitlab_ops  # type: ignore[import-not-found]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ok_auth():
    return True, ''


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


def _mr_view_success_payload() -> dict:
    """Minimal ``view_pr_data`` success payload with a source branch."""
    return {
        'status': 'success',
        'operation': 'pr_view',
        'pr_number': 42,
        'pr_url': 'https://gitlab.com/octo/repo/-/merge_requests/42',
        'state': 'open',
        'title': 'T',
        'head_branch': 'feature/x',
        'base_branch': 'main',
        'is_draft': 'false',
        'mergeable': 'mergeable',
        'merge_state': 'can_be_merged',
        'review_decision': 'approved',
    }


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
# (a) Happy path — merge OK, branch delete OK
# ---------------------------------------------------------------------------


def test_mr_merge_delete_branch_happy_path(monkeypatch):
    _install_common(monkeypatch)
    run_glab_stub, captured = _capture_run_glab(merge_ok=True, delete_mode='ok')
    monkeypatch.setattr(gitlab_ops, 'run_glab', run_glab_stub)
    monkeypatch.setattr(gitlab_ops, 'view_pr_data', lambda head=None: _mr_view_success_payload())

    result = gitlab_ops.cmd_pr_merge(_merge_ns(delete_branch=True))

    assert result['status'] == 'success', result
    assert result['operation'] == 'pr_merge'
    assert result['merged'] is True
    assert result['branch_deleted'] == 'feature/x'
    assert result['already_gone'] is False
    assert 'branch_delete_error' not in result

    # The merge call is untouched by --delete-branch.
    merge_call = next(c for c in captured if c[:2] == ['mr', 'merge'])
    assert '--remove-source-branch' not in merge_call, merge_call

    # A REST DELETE was issued via cmd_branch_delete.
    delete_calls = [c for c in captured if c[:3] == ['api', '-X', 'DELETE']]
    assert len(delete_calls) == 1, delete_calls
    endpoint = delete_calls[0][-1]
    # Project path + branch are URL-encoded by the branch-delete leaf.
    assert endpoint == 'projects/octo%2Frepo/repository/branches/feature%2Fx', endpoint

    _assert_no_remove_source_branch_flag(captured)


# ---------------------------------------------------------------------------
# (b) Merge OK, branch already deleted (REST returns 422 / 404)
# ---------------------------------------------------------------------------


def test_mr_merge_delete_branch_already_gone_422(monkeypatch):
    _install_common(monkeypatch)
    run_glab_stub, captured = _capture_run_glab(merge_ok=True, delete_mode='gone')
    monkeypatch.setattr(gitlab_ops, 'run_glab', run_glab_stub)
    monkeypatch.setattr(gitlab_ops, 'view_pr_data', lambda head=None: _mr_view_success_payload())

    result = gitlab_ops.cmd_pr_merge(_merge_ns(delete_branch=True))

    assert result['status'] == 'success', result
    assert result['merged'] is True
    assert result['branch_deleted'] == 'feature/x'
    assert result['already_gone'] is True
    assert 'branch_delete_error' not in result

    _assert_no_remove_source_branch_flag(captured)


def test_mr_merge_delete_branch_already_gone_404(monkeypatch):
    _install_common(monkeypatch)
    run_glab_stub, captured = _capture_run_glab(merge_ok=True, delete_mode='notfound')
    monkeypatch.setattr(gitlab_ops, 'run_glab', run_glab_stub)
    monkeypatch.setattr(gitlab_ops, 'view_pr_data', lambda head=None: _mr_view_success_payload())

    result = gitlab_ops.cmd_pr_merge(_merge_ns(delete_branch=True))

    assert result['status'] == 'success', result
    assert result['merged'] is True
    assert result['branch_deleted'] == 'feature/x'
    assert result['already_gone'] is True
    assert 'branch_delete_error' not in result

    _assert_no_remove_source_branch_flag(captured)


# ---------------------------------------------------------------------------
# (c) Merge OK, branch delete API error
# ---------------------------------------------------------------------------


def test_mr_merge_delete_branch_api_error_produces_compound_result(monkeypatch):
    _install_common(monkeypatch)
    run_glab_stub, captured = _capture_run_glab(merge_ok=True, delete_mode='error')
    monkeypatch.setattr(gitlab_ops, 'run_glab', run_glab_stub)
    monkeypatch.setattr(gitlab_ops, 'view_pr_data', lambda head=None: _mr_view_success_payload())

    result = gitlab_ops.cmd_pr_merge(_merge_ns(delete_branch=True))

    # Compound result: merge succeeded, branch delete did not.
    assert result['status'] == 'success', result
    assert result['merged'] is True
    assert 'branch_delete_error' in result, result
    assert 'branch_deleted' not in result
    assert 'already_gone' not in result

    _assert_no_remove_source_branch_flag(captured)


# ---------------------------------------------------------------------------
# (d) Merge failure — branch delete must NOT be attempted
# ---------------------------------------------------------------------------


def test_mr_merge_merge_failure_skips_branch_delete(monkeypatch):
    _install_common(monkeypatch)
    run_glab_stub, captured = _capture_run_glab(merge_ok=False, delete_mode='ok')
    monkeypatch.setattr(gitlab_ops, 'run_glab', run_glab_stub)

    pr_view_calls = {'count': 0}

    def tracking_view_pr_data(head=None):
        pr_view_calls['count'] += 1
        return _mr_view_success_payload()

    monkeypatch.setattr(gitlab_ops, 'view_pr_data', tracking_view_pr_data)

    result = gitlab_ops.cmd_pr_merge(_merge_ns(delete_branch=True))

    assert result['status'] == 'error', result
    # Only the merge call should have been made — no REST DELETE.
    delete_calls = [c for c in captured if c[:3] == ['api', '-X', 'DELETE']]
    assert delete_calls == [], delete_calls
    assert pr_view_calls['count'] == 0, 'mr view must not be consulted when the merge itself fails'

    _assert_no_remove_source_branch_flag(captured)


# ---------------------------------------------------------------------------
# (e) mr merge WITHOUT --delete-branch — no REST delete, no new fields
# ---------------------------------------------------------------------------


def test_mr_merge_without_delete_branch_leaves_branch_untouched(monkeypatch):
    _install_common(monkeypatch)
    run_glab_stub, captured = _capture_run_glab(merge_ok=True, delete_mode='ok')
    monkeypatch.setattr(gitlab_ops, 'run_glab', run_glab_stub)

    pr_view_calls = {'count': 0}

    def tracking_view_pr_data(head=None):
        pr_view_calls['count'] += 1
        return _mr_view_success_payload()

    monkeypatch.setattr(gitlab_ops, 'view_pr_data', tracking_view_pr_data)

    result = gitlab_ops.cmd_pr_merge(_merge_ns(delete_branch=False))

    assert result['status'] == 'success', result
    assert result['operation'] == 'pr_merge'
    # When delete_branch is not requested, the compound-result fields must be
    # absent — the contract still returns the lean success shape.
    for key in ('merged', 'branch_deleted', 'already_gone', 'branch_delete_error'):
        assert key not in result, f'{key} leaked into non-delete result: {result}'

    # No REST DELETE, no mr view — this is a pure merge.
    delete_calls = [c for c in captured if c[:3] == ['api', '-X', 'DELETE']]
    assert delete_calls == [], delete_calls
    assert pr_view_calls['count'] == 0, 'mr view must not be consulted when --delete-branch is absent'

    _assert_no_remove_source_branch_flag(captured)


# ---------------------------------------------------------------------------
# Regression: lesson-2026-04-17-19-002 — worktree error case (symmetric)
# ---------------------------------------------------------------------------


def test_mr_merge_delete_branch_does_not_touch_local_git(monkeypatch):
    """Regression for lesson-2026-04-17-19-002 — GitLab side.

    The original bug on the GitHub side drove a local ``git checkout`` +
    ``git branch -D`` against the *caller's* cwd. The GitLab analogue is
    ``glab mr merge --remove-source-branch`` (the mapping of
    ``--delete-branch``), which must not be emitted by ``cmd_pr_merge``.
    The refactor removes that pass-through entirely, so ``glab mr merge``
    runs clean and the remote branch is deleted via a pure REST call.

    This test enforces both halves of that contract:
      1. ``glab mr merge`` is invoked without ``--remove-source-branch``.
      2. No ``git`` subprocess is ever spawned by ``cmd_pr_merge``.
      3. The remote branch is deleted via ``cmd_branch_delete``'s REST leaf.
    """
    _install_common(monkeypatch)
    run_glab_stub, captured = _capture_run_glab(merge_ok=True, delete_mode='ok')
    monkeypatch.setattr(gitlab_ops, 'run_glab', run_glab_stub)
    monkeypatch.setattr(gitlab_ops, 'view_pr_data', lambda head=None: _mr_view_success_payload())

    # Trip-wire: if cmd_pr_merge ever shells out to git, the regression is
    # back. We patch the most likely entry point to raise immediately.
    import subprocess as _subprocess

    def forbidden_subprocess_run(*a, **kw):  # pragma: no cover — guard only
        raise AssertionError(
            f'cmd_pr_merge must not invoke subprocess.run during merge + delete; args={a!r} kwargs={kw!r}'
        )

    monkeypatch.setattr(_subprocess, 'run', forbidden_subprocess_run)

    result = gitlab_ops.cmd_pr_merge(_merge_ns(delete_branch=True))

    # Contract (1): glab mr merge ran clean, no --remove-source-branch.
    merge_call = next(c for c in captured if c[:2] == ['mr', 'merge'])
    assert '--remove-source-branch' not in merge_call, merge_call

    # Contract (3): remote branch delete went through the REST leaf.
    delete_calls = [c for c in captured if c[:3] == ['api', '-X', 'DELETE']]
    assert len(delete_calls) == 1, delete_calls
    endpoint = delete_calls[0][-1]
    assert endpoint == 'projects/octo%2Frepo/repository/branches/feature%2Fx', endpoint

    # Compound-success shape (see happy path).
    assert result['status'] == 'success', result
    assert result['merged'] is True
    assert result['branch_deleted'] == 'feature/x'
    assert result['already_gone'] is False

    _assert_no_remove_source_branch_flag(captured)


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


# --- (a) successful merge after poll (mergeable state reached) ---------------


def test_safe_merge_can_be_merged_on_first_poll(monkeypatch):
    """An MR already ``can_be_merged`` merges on the first poll via cmd_pr_merge."""
    _install_common(monkeypatch)
    run_glab_stub, captured = _capture_run_glab(merge_ok=True, delete_mode='ok')
    monkeypatch.setattr(gitlab_ops, 'run_glab', run_glab_stub)
    monkeypatch.setattr(
        gitlab_ops, 'view_pr_data', lambda head=None: _safe_merge_view_payload('can_be_merged')
    )

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
    run_glab_stub, captured = _capture_run_glab(merge_ok=True, delete_mode='ok')
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
    monkeypatch.setattr(
        gitlab_ops, 'view_pr_data', lambda head=None: _safe_merge_view_payload('can_be_merged')
    )

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

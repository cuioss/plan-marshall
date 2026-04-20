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
    monkeypatch.setattr(
        gitlab_ops, 'view_pr_data', lambda head=None: _mr_view_success_payload()
    )

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
    monkeypatch.setattr(
        gitlab_ops, 'view_pr_data', lambda head=None: _mr_view_success_payload()
    )

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
    monkeypatch.setattr(
        gitlab_ops, 'view_pr_data', lambda head=None: _mr_view_success_payload()
    )

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
    monkeypatch.setattr(
        gitlab_ops, 'view_pr_data', lambda head=None: _mr_view_success_payload()
    )

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
    assert pr_view_calls['count'] == 0, (
        'mr view must not be consulted when the merge itself fails'
    )

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
    assert pr_view_calls['count'] == 0, (
        'mr view must not be consulted when --delete-branch is absent'
    )

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
    monkeypatch.setattr(
        gitlab_ops, 'view_pr_data', lambda head=None: _mr_view_success_payload()
    )

    # Trip-wire: if cmd_pr_merge ever shells out to git, the regression is
    # back. We patch the most likely entry point to raise immediately.
    import subprocess as _subprocess

    def forbidden_subprocess_run(*a, **kw):  # pragma: no cover — guard only
        raise AssertionError(
            'cmd_pr_merge must not invoke subprocess.run during merge + delete; '
            f'args={a!r} kwargs={kw!r}'
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

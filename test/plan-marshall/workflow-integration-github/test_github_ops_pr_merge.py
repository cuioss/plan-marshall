#!/usr/bin/env python3
"""Tests for cmd_pr_merge branch-delete refactor.

After the refactor:
* ``cmd_pr_merge`` MUST NOT pass ``--delete-branch`` to ``gh pr merge``.
* When the caller requests ``--delete-branch``, the merge is performed first
  and (on success) the PR head branch is deleted remotely via
  ``cmd_branch_delete`` (REST ``DELETE /git/refs/heads/{branch}``).
* No local git state (checkout, ``git branch -D``) may be touched by this
  handler — that is the caller's responsibility.

The regression guard for the lesson-2026-04-17-19-002 fork exercises the
worktree scenario that broke with ``gh pr merge --delete-branch``: here the
merge must finish cleanly and the branch delete must round-trip purely
through the REST leaf, never through local git.
"""

import argparse

import github_ops  # type: ignore[import-not-found]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ok_auth():
    return True, ''


def _install_common(monkeypatch):
    """Install auth + owner/repo stubs used by every scenario.

    Tests override ``run_gh`` explicitly below; this helper only installs the
    pieces that are orthogonal to the merge/delete wiring.
    """
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(
        github_ops,
        'get_repo_info',
        lambda: ('octo', 'repo'),
    )


def _pr_view_success_payload() -> dict:
    """Minimal ``view_pr_data`` success payload with a head branch."""
    return {
        'status': 'success',
        'operation': 'pr_view',
        'pr_number': 42,
        'pr_url': 'https://github.com/octo/repo/pull/42',
        'state': 'open',
        'title': 'T',
        'head_branch': 'feature/x',
        'base_branch': 'main',
        'is_draft': 'false',
        'mergeable': 'mergeable',
        'merge_state': 'clean',
    }


def _capture_run_gh(
    *,
    merge_ok: bool = True,
    delete_mode: str = 'ok',
):
    """Build a ``run_gh`` stub + captured args list.

    Parameters
    ----------
    merge_ok:
        When False, the ``pr merge`` call returns a non-zero exit code,
        simulating a merge failure.
    delete_mode:
        One of:
          * ``'ok'``      — DELETE returns 204 No Content (success).
          * ``'gone'``    — DELETE returns HTTP 422 (already gone).
          * ``'notfound'``— DELETE returns HTTP 404 (already gone).
          * ``'error'``   — DELETE returns a generic HTTP 500.
    """
    captured: list[list[str]] = []

    def run_gh_stub(args, capture_json=False, timeout=60):
        captured.append(list(args))

        if args[:2] == ['pr', 'merge']:
            if merge_ok:
                return 0, '', ''
            return 1, '', 'merge conflict'

        # DELETE /repos/{owner}/{repo}/git/refs/heads/{branch}
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

    return run_gh_stub, captured


def _merge_ns(*, delete_branch: bool, pr_number: int | None = 42, head: str | None = None):
    return argparse.Namespace(
        pr_number=pr_number,
        head=head,
        strategy='merge',
        delete_branch=delete_branch,
    )


def _assert_no_delete_branch_flag(captured_calls: list[list[str]]) -> None:
    """No ``--delete-branch`` may appear in ANY captured gh invocation."""
    for call in captured_calls:
        assert '--delete-branch' not in call, (
            f"cmd_pr_merge leaked --delete-branch into gh args: {call}"
        )


# ---------------------------------------------------------------------------
# (a) Happy path — merge OK, branch delete OK
# ---------------------------------------------------------------------------


def test_pr_merge_delete_branch_happy_path(monkeypatch):
    _install_common(monkeypatch)
    run_gh_stub, captured = _capture_run_gh(merge_ok=True, delete_mode='ok')
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)
    monkeypatch.setattr(
        github_ops, 'view_pr_data', lambda head=None: _pr_view_success_payload()
    )

    result = github_ops.cmd_pr_merge(_merge_ns(delete_branch=True))

    assert result['status'] == 'success', result
    assert result['operation'] == 'pr_merge'
    assert result['merged'] is True
    assert result['branch_deleted'] == 'feature/x'
    assert result['already_gone'] is False
    assert 'branch_delete_error' not in result

    # The merge call is untouched by --delete-branch.
    merge_call = next(c for c in captured if c[:2] == ['pr', 'merge'])
    assert '--delete-branch' not in merge_call, merge_call

    # A REST DELETE was issued via cmd_branch_delete. The branch segment is
    # URL-encoded (``/`` → ``%2F``) so names like ``feature/x`` serialize
    # safely as a single path segment.
    delete_calls = [c for c in captured if c[:3] == ['api', '-X', 'DELETE']]
    assert len(delete_calls) == 1, delete_calls
    assert delete_calls[0][-1].endswith('/git/refs/heads/feature%2Fx')

    _assert_no_delete_branch_flag(captured)


# ---------------------------------------------------------------------------
# (b) Merge OK, branch already deleted (REST returns 422 / 404)
# ---------------------------------------------------------------------------


def test_pr_merge_delete_branch_already_gone_422(monkeypatch):
    _install_common(monkeypatch)
    run_gh_stub, captured = _capture_run_gh(merge_ok=True, delete_mode='gone')
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)
    monkeypatch.setattr(
        github_ops, 'view_pr_data', lambda head=None: _pr_view_success_payload()
    )

    result = github_ops.cmd_pr_merge(_merge_ns(delete_branch=True))

    assert result['status'] == 'success', result
    assert result['merged'] is True
    assert result['branch_deleted'] == 'feature/x'
    assert result['already_gone'] is True
    assert 'branch_delete_error' not in result

    _assert_no_delete_branch_flag(captured)


def test_pr_merge_delete_branch_already_gone_404(monkeypatch):
    _install_common(monkeypatch)
    run_gh_stub, captured = _capture_run_gh(merge_ok=True, delete_mode='notfound')
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)
    monkeypatch.setattr(
        github_ops, 'view_pr_data', lambda head=None: _pr_view_success_payload()
    )

    result = github_ops.cmd_pr_merge(_merge_ns(delete_branch=True))

    assert result['status'] == 'success', result
    assert result['merged'] is True
    assert result['branch_deleted'] == 'feature/x'
    assert result['already_gone'] is True
    assert 'branch_delete_error' not in result

    _assert_no_delete_branch_flag(captured)


# ---------------------------------------------------------------------------
# (c) Merge OK, branch delete API error
# ---------------------------------------------------------------------------


def test_pr_merge_delete_branch_api_error_produces_compound_result(monkeypatch):
    _install_common(monkeypatch)
    run_gh_stub, captured = _capture_run_gh(merge_ok=True, delete_mode='error')
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)
    monkeypatch.setattr(
        github_ops, 'view_pr_data', lambda head=None: _pr_view_success_payload()
    )

    result = github_ops.cmd_pr_merge(_merge_ns(delete_branch=True))

    # Compound result: merge succeeded, branch delete did not.
    assert result['status'] == 'success', result
    assert result['merged'] is True
    assert 'branch_delete_error' in result, result
    assert 'branch_deleted' not in result
    assert 'already_gone' not in result

    _assert_no_delete_branch_flag(captured)


# ---------------------------------------------------------------------------
# (d) Merge failure — branch delete must NOT be attempted
# ---------------------------------------------------------------------------


def test_pr_merge_merge_failure_skips_branch_delete(monkeypatch):
    _install_common(monkeypatch)
    run_gh_stub, captured = _capture_run_gh(merge_ok=False, delete_mode='ok')
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    pr_view_calls = {'count': 0}

    def tracking_view_pr_data(head=None):
        pr_view_calls['count'] += 1
        return _pr_view_success_payload()

    monkeypatch.setattr(github_ops, 'view_pr_data', tracking_view_pr_data)

    result = github_ops.cmd_pr_merge(_merge_ns(delete_branch=True))

    assert result['status'] == 'error', result
    # Only the merge call should have been made — no REST DELETE.
    delete_calls = [c for c in captured if c[:3] == ['api', '-X', 'DELETE']]
    assert delete_calls == [], delete_calls
    assert pr_view_calls['count'] == 0, (
        'pr view must not be consulted when the merge itself fails'
    )

    _assert_no_delete_branch_flag(captured)


# ---------------------------------------------------------------------------
# (e) pr merge WITHOUT --delete-branch — no REST delete, no new fields
# ---------------------------------------------------------------------------


def test_pr_merge_without_delete_branch_leaves_branch_untouched(monkeypatch):
    _install_common(monkeypatch)
    run_gh_stub, captured = _capture_run_gh(merge_ok=True, delete_mode='ok')
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    pr_view_calls = {'count': 0}

    def tracking_view_pr_data(head=None):
        pr_view_calls['count'] += 1
        return _pr_view_success_payload()

    monkeypatch.setattr(github_ops, 'view_pr_data', tracking_view_pr_data)

    result = github_ops.cmd_pr_merge(_merge_ns(delete_branch=False))

    assert result['status'] == 'success', result
    assert result['operation'] == 'pr_merge'
    # When delete_branch is not requested, the compound-result fields must be
    # absent — the contract still returns the lean success shape.
    for key in ('merged', 'branch_deleted', 'already_gone', 'branch_delete_error'):
        assert key not in result, f'{key} leaked into non-delete result: {result}'

    # No REST DELETE, no pr view — this is a pure merge.
    delete_calls = [c for c in captured if c[:3] == ['api', '-X', 'DELETE']]
    assert delete_calls == [], delete_calls
    assert pr_view_calls['count'] == 0, (
        'pr view must not be consulted when --delete-branch is absent'
    )

    _assert_no_delete_branch_flag(captured)


# ---------------------------------------------------------------------------
# Regression: lesson-2026-04-17-19-002 — worktree error case
# ---------------------------------------------------------------------------


def test_pr_merge_delete_branch_does_not_touch_local_git(monkeypatch):
    """Regression for lesson-2026-04-17-19-002.

    The original bug: ``gh pr merge --delete-branch`` drove a local ``git
    checkout`` + ``git branch -D`` against the *caller's* cwd, which in an
    isolated worktree tried to delete the branch that was still checked out
    in the worktree itself and aborted with a checkout error. The refactor
    removes the ``--delete-branch`` pass-through entirely, so ``gh pr merge``
    runs clean and the remote branch is deleted via a pure REST call.

    This test enforces both halves of that contract:
      1. ``gh pr merge`` is invoked without ``--delete-branch``.
      2. No ``git`` subprocess is ever spawned by ``cmd_pr_merge``.
      3. The remote branch is deleted via ``cmd_branch_delete``'s REST leaf.
    """
    _install_common(monkeypatch)
    run_gh_stub, captured = _capture_run_gh(merge_ok=True, delete_mode='ok')
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)
    monkeypatch.setattr(
        github_ops, 'view_pr_data', lambda head=None: _pr_view_success_payload()
    )

    # Trip-wire: if cmd_pr_merge ever shells out to git, the regression is
    # back. We patch the two most likely entry points to raise immediately.
    import subprocess as _subprocess

    def forbidden_subprocess_run(*a, **kw):  # pragma: no cover — guard only
        raise AssertionError(
            'cmd_pr_merge must not invoke subprocess.run during merge + delete; '
            f'args={a!r} kwargs={kw!r}'
        )

    monkeypatch.setattr(_subprocess, 'run', forbidden_subprocess_run)

    result = github_ops.cmd_pr_merge(_merge_ns(delete_branch=True))

    # Contract (1): gh pr merge ran clean, no --delete-branch.
    merge_call = next(c for c in captured if c[:2] == ['pr', 'merge'])
    assert '--delete-branch' not in merge_call, merge_call

    # Contract (3): remote branch delete went through the REST leaf. The
    # branch segment is URL-encoded so ``/`` becomes ``%2F``.
    delete_calls = [c for c in captured if c[:3] == ['api', '-X', 'DELETE']]
    assert len(delete_calls) == 1, delete_calls
    endpoint = delete_calls[0][-1]
    assert endpoint == 'repos/octo/repo/git/refs/heads/feature%2Fx', endpoint

    # Compound-success shape (see happy path).
    assert result['status'] == 'success', result
    assert result['merged'] is True
    assert result['branch_deleted'] == 'feature/x'
    assert result['already_gone'] is False

    _assert_no_delete_branch_flag(captured)


# ---------------------------------------------------------------------------
# cmd_branch_delete — URL-encoding of the branch segment
# ---------------------------------------------------------------------------


def _branch_ns(branch: str) -> argparse.Namespace:
    return argparse.Namespace(branch=branch, remote_only=True)


def _capture_branch_delete_run_gh(returncode: int = 0, stderr: str = ''):
    """Minimal run_gh stub for cmd_branch_delete tests."""
    captured: list[list[str]] = []

    def run_gh_stub(args, capture_json=False, timeout=60):
        captured.append(list(args))
        return returncode, '', stderr

    return run_gh_stub, captured


def test_branch_delete_url_encodes_slash_in_branch_name(monkeypatch):
    """Regression: PR #256 review (gemini-code-assist).

    Branch names containing ``/`` must be URL-encoded into a single path
    segment — ``feature/x`` → ``feature%2Fx`` — otherwise the REST path
    becomes ``/git/refs/heads/feature/x`` which GitHub interprets as
    ``refs/heads/feature`` + an extra ``/x`` segment (malformed ref path).
    ``urllib.parse.quote(branch, safe='')`` is the canonical fix and mirrors
    the pattern already in use in ``gitlab_ops.py``.
    """
    _install_common(monkeypatch)
    run_gh_stub, captured = _capture_branch_delete_run_gh(returncode=0)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    result = github_ops.cmd_branch_delete(_branch_ns('feature/x'))

    assert result['status'] == 'success', result
    assert result['branch'] == 'feature/x'
    assert result['already_gone'] is False

    assert len(captured) == 1, captured
    endpoint = captured[0][-1]
    assert endpoint == 'repos/octo/repo/git/refs/heads/feature%2Fx', endpoint
    # Raw unencoded slash must NOT appear in the branch segment.
    assert '/feature/x' not in endpoint, endpoint


def test_branch_delete_url_encodes_special_characters(monkeypatch):
    """Branch names with reserved characters (``#``, ``?``, space) must be
    percent-encoded so the REST path stays a single well-formed segment.
    """
    _install_common(monkeypatch)
    run_gh_stub, captured = _capture_branch_delete_run_gh(returncode=0)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    result = github_ops.cmd_branch_delete(_branch_ns('feat/bug#42?x y'))

    assert result['status'] == 'success', result

    endpoint = captured[0][-1]
    # ``/`` → %2F, ``#`` → %23, ``?`` → %3F, space → %20.
    assert endpoint == 'repos/octo/repo/git/refs/heads/feat%2Fbug%2342%3Fx%20y', endpoint


def test_branch_delete_simple_branch_name_is_unchanged(monkeypatch):
    """Plain branch names (no reserved characters) pass through quote() as
    identity — nothing to encode, so the endpoint keeps its literal form.
    """
    _install_common(monkeypatch)
    run_gh_stub, captured = _capture_branch_delete_run_gh(returncode=0)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    result = github_ops.cmd_branch_delete(_branch_ns('main'))

    assert result['status'] == 'success', result

    endpoint = captured[0][-1]
    assert endpoint == 'repos/octo/repo/git/refs/heads/main', endpoint

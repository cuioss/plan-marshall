"""Tests for cmd_pr_merge branch-delete refactor.

After the refactor:
* ``cmd_pr_merge`` MUST NOT pass ``--delete-branch`` to ``gh pr merge``.
* When the caller requests ``--delete-branch``, the merge is performed first
  and (on success) the PR head branch is deleted remotely via
  ``cmd_branch_delete`` (REST ``DELETE /git/refs/heads/{branch}``).
* No local git state (checkout, ``git branch -D``) may be touched by this
  handler — that is the caller's responsibility.

The worktree fork exercises the scenario ``gh pr merge --delete-branch``
cannot serve: the merge must finish cleanly and the branch delete must
round-trip purely through the REST leaf, never through local git.
"""
import argparse
import json
from datetime import UTC, datetime

import github_ops
import pytest
from _ci_wait_contract import _ok_auth


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
def _install_probe(
    monkeypatch,
    *,
    discriminator: str | None = None,
    detail: str = 'no merge_queue rule on branch',
    error: str | None = None,
    merge_method: str | None = None,
) -> dict:
    """Stub ``github_ops._probe_merge_queue_state`` for the safe-merge preflight.

    Returns a capture dict recording the ``(owner, repo, branch)`` the probe was
    called with plus a call count, so tests can assert base-branch specificity.
    The four-tuple return shape ``(discriminator, detail, error, merge_method)``
    mirrors the production ``_probe_merge_queue_state`` signature exactly, so a
    green fixture cannot diverge from the production data shape. By
    default the probe reports ``eligible_unconfigured`` with ``merge_method=None``
    so the preflight proceeds to the normal merge path unchanged.
    """
    if discriminator is None:
        discriminator = github_ops.MERGE_QUEUE_ELIGIBLE_UNCONFIGURED
    captured: dict = {'owner': None, 'repo': None, 'branch': None, 'calls': 0}

    def probe_stub(owner, repo, branch):
        captured['owner'] = owner
        captured['repo'] = repo
        captured['branch'] = branch
        captured['calls'] += 1
        return discriminator, detail, error, merge_method

    monkeypatch.setattr(github_ops, '_probe_merge_queue_state', probe_stub)
    return captured
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
_CORROBORATION_PAYLOADS: dict[str, dict] = {
    # Landed merge — the only shape that corroborates.
    'merged': {
        'state': 'MERGED',
        'mergedAt': '2026-01-01T00:00:00Z',
        'baseRefName': 'main',
        'headRefOid': 'abc123',
    },
    # The closed-unmerged signature: the merge command reports success but
    # GitHub closed the PR without merging it.
    'closed': {
        'state': 'CLOSED',
        'mergedAt': None,
        'baseRefName': 'main',
        'headRefOid': 'abc123',
    },
    # The merge silently did nothing and the PR is still open.
    'open': {
        'state': 'OPEN',
        'mergedAt': None,
        'baseRefName': 'main',
        'headRefOid': 'abc123',
    },
    # A wrongly-shaped record: the key EXISTS but carries no usable instant. A
    # narrow presence check would pass here; the value-meaning assertion must not.
    'merged_without_timestamp': {
        'state': 'MERGED',
        'mergedAt': None,
        'baseRefName': 'main',
        'headRefOid': 'abc123',
    },
}
def _capture_run_gh(
    *,
    merge_ok: bool = True,
    delete_mode: str = 'ok',
    corroborate: str = 'merged',
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
    corroborate:
        Key into :data:`_CORROBORATION_PAYLOADS` selecting what the post-merge
        ``gh pr view --json ...`` re-read observes. ``'unreadable'`` makes that
        re-read fail outright.
    """
    captured: list[list[str]] = []

    def run_gh_stub(args, capture_json=False, timeout=60):
        captured.append(list(args))

        if args[:2] == ['pr', 'merge']:
            if merge_ok:
                return 0, '', ''
            return 1, '', 'merge conflict'

        # Post-merge corroboration re-read.
        if args[:2] == ['pr', 'view']:
            if corroborate == 'unreadable':
                return 1, '', 'HTTP 500: boom'
            return 0, json.dumps(_CORROBORATION_PAYLOADS[corroborate]), ''

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
def _install_merge_preconditions(monkeypatch, *, view_payload: dict | None = None) -> dict:
    """Install the stubs ``cmd_pr_merge``'s own guards require.

    ``cmd_pr_merge`` now runs the shared base-branch merge-queue preflight before
    merging, so every direct ``cmd_pr_merge`` test needs BOTH the probe stub and
    a ``view_pr_data`` that resolves a base branch — otherwise the test would be
    exercising the preflight's fail-closed path rather than the merge wiring it
    means to assert. Returns the probe capture dict.
    """
    monkeypatch.setattr(github_ops, 'view_pr_data', lambda head=None: view_payload or _pr_view_success_payload())
    return _install_probe(monkeypatch)
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
        assert '--delete-branch' not in call, f'cmd_pr_merge leaked --delete-branch into gh args: {call}'
def _gate_run_gh(*, view, compare):
    """run_gh stub dispatching the gate's two query shapes.

    ``view`` / ``compare`` are ``(returncode, json_obj_or_str)`` tuples for the
    ``gh pr view --json ...`` and ``gh api .../compare/...`` calls respectively.
    """

    def _payload(obj):
        return obj if isinstance(obj, str) else json.dumps(obj)

    def run_gh_stub(args, capture_json=False, timeout=60):
        if args[:2] == ['pr', 'view']:
            rc, obj = view
            return rc, _payload(obj), '' if rc == 0 else 'view failed'
        if args[:1] == ['api']:
            rc, obj = compare
            return rc, _payload(obj), '' if rc == 0 else 'compare failed'
        return 0, '', ''

    return run_gh_stub


def test_pr_merge_delete_branch_happy_path(monkeypatch):
    _install_common(monkeypatch)
    run_gh_stub, captured = _capture_run_gh(merge_ok=True, delete_mode='ok')
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)
    _install_merge_preconditions(monkeypatch)

    result = github_ops.cmd_pr_merge(_merge_ns(delete_branch=True))

    assert result['status'] == 'success', result
    assert result['operation'] == 'pr_merge'
    assert result['merged'] is True
    # The claim rests on the re-read, and the evidence rides along with it.
    assert 'MERGED' in result['merge_corroboration'], result
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
def test_pr_merge_delete_branch_already_gone_422(monkeypatch):
    _install_common(monkeypatch)
    run_gh_stub, captured = _capture_run_gh(merge_ok=True, delete_mode='gone')
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)
    _install_merge_preconditions(monkeypatch)

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
    _install_merge_preconditions(monkeypatch)

    result = github_ops.cmd_pr_merge(_merge_ns(delete_branch=True))

    assert result['status'] == 'success', result
    assert result['merged'] is True
    assert result['branch_deleted'] == 'feature/x'
    assert result['already_gone'] is True
    assert 'branch_delete_error' not in result

    _assert_no_delete_branch_flag(captured)
def test_pr_merge_delete_branch_api_error_produces_compound_result(monkeypatch):
    _install_common(monkeypatch)
    run_gh_stub, captured = _capture_run_gh(merge_ok=True, delete_mode='error')
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)
    _install_merge_preconditions(monkeypatch)

    result = github_ops.cmd_pr_merge(_merge_ns(delete_branch=True))

    # Compound result: merge succeeded, branch delete did not.
    assert result['status'] == 'success', result
    assert result['merged'] is True
    assert 'branch_delete_error' in result, result
    assert 'branch_deleted' not in result
    assert 'already_gone' not in result

    _assert_no_delete_branch_flag(captured)
def test_pr_merge_without_delete_branch_leaves_branch_untouched(monkeypatch):
    """A merge without --delete-branch still reports a corroborated verdict.

    ``merged`` used to live INSIDE the ``--delete-branch`` branch, so this shape
    reported no merge verdict at all. It is now reported on every successful
    merge; only the branch-delete compound-result keys stay absent.
    """
    _install_common(monkeypatch)
    _install_probe(monkeypatch)
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
    assert result['merged'] is True, result
    assert 'MERGED' in result['merge_corroboration'], result
    # The branch-delete compound-result fields stay absent.
    for key in ('branch_deleted', 'already_gone', 'branch_delete_error'):
        assert key not in result, f'{key} leaked into non-delete result: {result}'

    # No REST DELETE. The only view_pr_data call is the preflight — the
    # head-branch resolution for the delete never runs.
    delete_calls = [c for c in captured if c[:3] == ['api', '-X', 'DELETE']]
    assert delete_calls == [], delete_calls
    assert pr_view_calls['count'] == 1, pr_view_calls

    _assert_no_delete_branch_flag(captured)
def test_pr_merge_delete_branch_does_not_touch_local_git(monkeypatch):
    """``--delete-branch`` deletes the head remotely, never through local git.

    A local ``git checkout`` + ``git branch -D`` against the *caller's* cwd —
    which is what ``gh pr merge --delete-branch`` does — in an isolated
    worktree tries to delete the branch that is still checked out
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
    _install_merge_preconditions(monkeypatch)

    # Trip-wire: if cmd_pr_merge ever shells out to git, the regression is
    # back. We patch the two most likely entry points to raise immediately.
    import subprocess as _subprocess

    def forbidden_subprocess_run(*a, **kw):  # pragma: no cover — guard only
        raise AssertionError(
            f'cmd_pr_merge must not invoke subprocess.run during merge + delete; args={a!r} kwargs={kw!r}'
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
def test_stuck_state_gate_behind_base(monkeypatch):
    """A branch behind its base (behind_by != 0) fails the gate closed."""
    _install_common(monkeypatch)
    monkeypatch.setattr(github_ops, 'view_pr_data', lambda head=None: _pr_view_success_payload())
    monkeypatch.setattr(
        github_ops,
        'run_gh',
        _gate_run_gh(
            view=(
                0,
                {
                    'reviewDecision': 'APPROVED',
                    'statusCheckRollup': [{'name': 'verify', 'conclusion': 'SUCCESS'}],
                    'headRefOid': 'abc123',
                },
            ),
            compare=(0, {'behind_by': 3}),
        ),
    )

    ok, reason = github_ops._safe_merge_stuck_state_gate('42')

    assert ok is False
    assert 'behind base by 3' in reason
def test_stuck_state_gate_non_dict_payload_fails_closed(monkeypatch):
    """A non-dict gate-query payload fails closed rather than raising."""
    _install_common(monkeypatch)
    monkeypatch.setattr(github_ops, 'view_pr_data', lambda head=None: _pr_view_success_payload())
    monkeypatch.setattr(
        github_ops,
        'run_gh',
        _gate_run_gh(view=(0, '["unexpected", "list"]'), compare=(0, {'behind_by': 0})),
    )

    ok, reason = github_ops._safe_merge_stuck_state_gate('42')

    assert ok is False
    assert 'non-dictionary JSON' in reason

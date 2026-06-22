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
import json

import github_ops  # type: ignore[import-not-found]  # noqa: E402

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
        assert '--delete-branch' not in call, f'cmd_pr_merge leaked --delete-branch into gh args: {call}'


# ---------------------------------------------------------------------------
# (a) Happy path — merge OK, branch delete OK
# ---------------------------------------------------------------------------


def test_pr_merge_delete_branch_happy_path(monkeypatch):
    _install_common(monkeypatch)
    run_gh_stub, captured = _capture_run_gh(merge_ok=True, delete_mode='ok')
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)
    monkeypatch.setattr(github_ops, 'view_pr_data', lambda head=None: _pr_view_success_payload())

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
    monkeypatch.setattr(github_ops, 'view_pr_data', lambda head=None: _pr_view_success_payload())

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
    monkeypatch.setattr(github_ops, 'view_pr_data', lambda head=None: _pr_view_success_payload())

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
    monkeypatch.setattr(github_ops, 'view_pr_data', lambda head=None: _pr_view_success_payload())

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
    assert pr_view_calls['count'] == 0, 'pr view must not be consulted when the merge itself fails'

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
    assert pr_view_calls['count'] == 0, 'pr view must not be consulted when --delete-branch is absent'

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
    monkeypatch.setattr(github_ops, 'view_pr_data', lambda head=None: _pr_view_success_payload())

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


# ---------------------------------------------------------------------------
# cmd_pr_safe_merge — poll readiness then merge; GitHub-only admin fallback
# ---------------------------------------------------------------------------
#
# Layer 1 (both providers): poll the PR's ``mergeStateStatus`` until it reaches
# a mergeable state, then delegate to ``cmd_pr_merge``.
# Layer 2 (GitHub-only): when readiness stays ``blocked`` past the poll timeout
# AND ``--admin-merge-on-stuck-state`` is set AND every active ruleset
# requirement is provably met, fall back to ``gh pr merge --admin``.


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

    ``poll_interval`` defaults to 0 so the real ``poll_until`` loop never
    sleeps during the polled-clean scenarios.
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


def _pr_view_payload(merge_state: str) -> dict:
    """A ``view_pr_data`` success payload with the given ``merge_state``."""
    payload = _pr_view_success_payload()
    payload['merge_state'] = merge_state
    return payload


def _sequenced_view_pr_data(states: list[str]):
    """Build a stateful ``view_pr_data`` stub returning ``states`` in order.

    The final state is repeated for any extra calls (e.g. the head-branch
    resolution that ``cmd_pr_merge`` issues for ``--delete-branch``).
    """
    calls = {'i': 0}

    def stub(head=None):
        idx = min(calls['i'], len(states) - 1)
        calls['i'] += 1
        return _pr_view_payload(states[idx])

    return stub, calls


def _stuck_gate_ok(_identifier):
    return True, None


def _stuck_gate_fail(_identifier):
    return False, 'required check verify has not concluded'


# --- (a) successful merge on first poll (mergeable_state: clean) -------------


def test_safe_merge_clean_on_first_poll(monkeypatch):
    """A PR already ``clean`` merges on the first poll via the normal path."""
    _install_common(monkeypatch)
    run_gh_stub, captured = _capture_run_gh(merge_ok=True, delete_mode='ok')
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)
    monkeypatch.setattr(github_ops, 'view_pr_data', lambda head=None: _pr_view_payload('clean'))

    result = github_ops.cmd_pr_safe_merge(_safe_merge_ns())

    assert result['status'] == 'success', result
    assert result['operation'] == 'pr_safe_merge'
    assert result['merge_path'] == 'polled_clean'
    assert result['polls'] >= 1
    assert 'duration_sec' in result

    # Layer-1 delegation goes through the normal merge — no --admin flag.
    merge_call = next(c for c in captured if c[:2] == ['pr', 'merge'])
    assert '--admin' not in merge_call, merge_call
    _assert_no_delete_branch_flag(captured)


# --- (b) retry on blocked state then clean ----------------------------------


def test_safe_merge_blocked_then_clean(monkeypatch):
    """A PR that is ``blocked`` then ``clean`` keeps polling, then merges."""
    _install_common(monkeypatch)
    run_gh_stub, captured = _capture_run_gh(merge_ok=True, delete_mode='ok')
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)
    view_stub, view_calls = _sequenced_view_pr_data(['blocked', 'blocked', 'clean'])
    monkeypatch.setattr(github_ops, 'view_pr_data', view_stub)

    result = github_ops.cmd_pr_safe_merge(_safe_merge_ns(poll_interval=0))

    assert result['status'] == 'success', result
    assert result['merge_path'] == 'polled_clean'
    # The loop ran at least three readiness polls before reaching clean.
    assert view_calls['i'] >= 3, view_calls
    # No admin fallback was needed.
    merge_call = next(c for c in captured if c[:2] == ['pr', 'merge'])
    assert '--admin' not in merge_call, merge_call


# --- (c) stuck-state detection after max retries (no admin) ------------------


def test_safe_merge_stuck_blocked_no_admin_returns_error(monkeypatch):
    """Timed-out while blocked, admin fallback NOT enabled → error, no merge."""
    _install_common(monkeypatch)
    run_gh_stub, captured = _capture_run_gh(merge_ok=True, delete_mode='ok')
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)
    # Drive the timeout deterministically: poll_until returns timed_out while
    # the last observed state is ``blocked``.
    monkeypatch.setattr(
        github_ops,
        'poll_until',
        lambda *a, **kw: {
            'timed_out': True,
            'duration_sec': 300,
            'polls': 5,
            'last_data': _pr_view_payload('blocked'),
        },
    )

    result = github_ops.cmd_pr_safe_merge(_safe_merge_ns(admin_merge_on_stuck_state=False))

    assert result['status'] == 'error', result
    assert result['operation'] == 'pr_safe_merge'
    assert 'admin fallback not enabled' in result['error'], result
    # No merge was attempted at all.
    merge_calls = [c for c in captured if c[:2] == ['pr', 'merge']]
    assert merge_calls == [], merge_calls


# --- (d) admin fallback when admin_merge_on_stuck_state is enabled -----------


def test_safe_merge_admin_fallback_on_stuck_blocked(monkeypatch):
    """Stuck blocked + knob on + gate provably met → admin merge fallback."""
    _install_common(monkeypatch)
    run_gh_stub, captured = _capture_run_gh(merge_ok=True, delete_mode='ok')
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)
    monkeypatch.setattr(
        github_ops,
        'poll_until',
        lambda *a, **kw: {
            'timed_out': True,
            'duration_sec': 300,
            'polls': 5,
            'last_data': _pr_view_payload('blocked'),
        },
    )
    # Gate provably met — admin fallback proceeds.
    monkeypatch.setattr(github_ops, '_safe_merge_stuck_state_gate', _stuck_gate_ok)

    result = github_ops.cmd_pr_safe_merge(_safe_merge_ns(admin_merge_on_stuck_state=True))

    assert result['status'] == 'success', result
    assert result['merge_path'] == 'admin_fallback', result
    assert result['polls'] == 5
    assert result['duration_sec'] == 300

    # The admin merge used --admin and the resolved strategy.
    merge_call = next(c for c in captured if c[:2] == ['pr', 'merge'])
    assert '--admin' in merge_call, merge_call
    assert '--merge' in merge_call, merge_call
    assert '42' in merge_call, merge_call


def test_safe_merge_admin_fallback_blocked_by_unmet_gate(monkeypatch):
    """Stuck blocked + knob on but ruleset NOT provably met → refuse, no merge."""
    _install_common(monkeypatch)
    run_gh_stub, captured = _capture_run_gh(merge_ok=True, delete_mode='ok')
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)
    monkeypatch.setattr(
        github_ops,
        'poll_until',
        lambda *a, **kw: {
            'timed_out': True,
            'duration_sec': 300,
            'polls': 5,
            'last_data': _pr_view_payload('blocked'),
        },
    )
    monkeypatch.setattr(github_ops, '_safe_merge_stuck_state_gate', _stuck_gate_fail)

    result = github_ops.cmd_pr_safe_merge(_safe_merge_ns(admin_merge_on_stuck_state=True))

    assert result['status'] == 'error', result
    assert 'ruleset requirements not provably met' in result['error'], result
    assert 'required check verify has not concluded' in result['error'], result
    # The gate failed closed — no merge of any kind was attempted.
    merge_calls = [c for c in captured if c[:2] == ['pr', 'merge']]
    assert merge_calls == [], merge_calls


def test_safe_merge_admin_fallback_only_for_blocked_state(monkeypatch):
    """Timed out while NOT blocked (e.g. behind) → admin fallback does not apply."""
    _install_common(monkeypatch)
    run_gh_stub, captured = _capture_run_gh(merge_ok=True, delete_mode='ok')
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)
    monkeypatch.setattr(
        github_ops,
        'poll_until',
        lambda *a, **kw: {
            'timed_out': True,
            'duration_sec': 300,
            'polls': 5,
            'last_data': _pr_view_payload('behind'),
        },
    )

    result = github_ops.cmd_pr_safe_merge(_safe_merge_ns(admin_merge_on_stuck_state=True))

    assert result['status'] == 'error', result
    assert 'applies only to a stuck blocked state' in result['error'], result
    merge_calls = [c for c in captured if c[:2] == ['pr', 'merge']]
    assert merge_calls == [], merge_calls


def test_safe_merge_admin_fallback_deletes_branch(monkeypatch):
    """Admin fallback honours --delete-branch via the REST leaf follow-up."""
    _install_common(monkeypatch)
    run_gh_stub, captured = _capture_run_gh(merge_ok=True, delete_mode='ok')
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)
    monkeypatch.setattr(
        github_ops,
        'poll_until',
        lambda *a, **kw: {
            'timed_out': True,
            'duration_sec': 300,
            'polls': 5,
            'last_data': _pr_view_payload('blocked'),
        },
    )
    monkeypatch.setattr(github_ops, '_safe_merge_stuck_state_gate', _stuck_gate_ok)
    monkeypatch.setattr(github_ops, 'view_pr_data', lambda head=None: _pr_view_success_payload())

    result = github_ops.cmd_pr_safe_merge(
        _safe_merge_ns(admin_merge_on_stuck_state=True, delete_branch=True)
    )

    assert result['status'] == 'success', result
    assert result['merge_path'] == 'admin_fallback'
    assert result['merged'] is True
    assert result['branch_deleted'] == 'feature/x'
    assert result['already_gone'] is False
    # The branch delete went through the REST leaf, URL-encoded.
    delete_calls = [c for c in captured if c[:3] == ['api', '-X', 'DELETE']]
    assert len(delete_calls) == 1, delete_calls
    assert delete_calls[0][-1].endswith('/git/refs/heads/feature%2Fx')


# --- readiness-poll failure (PR not found / auth) propagates ----------------


def test_safe_merge_poll_failure_propagates(monkeypatch):
    """A check_fn failure during the readiness poll is surfaced as an error."""
    _install_common(monkeypatch)
    run_gh_stub, captured = _capture_run_gh(merge_ok=True, delete_mode='ok')
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)
    monkeypatch.setattr(
        github_ops,
        'poll_until',
        lambda *a, **kw: {
            'timed_out': False,
            'duration_sec': 1,
            'polls': 1,
            'last_data': {'error': 'No PR found for current branch'},
            'error': 'No PR found for current branch',
        },
    )

    result = github_ops.cmd_pr_safe_merge(_safe_merge_ns())

    assert result['status'] == 'error', result
    assert 'Readiness poll failed' in result['error'], result
    merge_calls = [c for c in captured if c[:2] == ['pr', 'merge']]
    assert merge_calls == [], merge_calls


# --- (f) existing cmd_pr_merge / cmd_pr_auto_merge tests unaffected ----------
#
# The existing cmd_pr_merge tests above (happy path, already-gone, api-error,
# merge-failure, no-delete-branch, local-git regression) continue to assert
# the unchanged merge contract. The two guards below pin the invariant that
# safe-merge added neither an --admin flag nor a stuck-state gate call to the
# normal merge/auto-merge paths.


def test_pr_merge_unaffected_no_admin_or_safe_merge_fields(monkeypatch):
    """cmd_pr_merge still returns the lean shape with no safe-merge fields."""
    _install_common(monkeypatch)
    run_gh_stub, captured = _capture_run_gh(merge_ok=True, delete_mode='ok')
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    result = github_ops.cmd_pr_merge(_merge_ns(delete_branch=False))

    assert result['status'] == 'success', result
    assert result['operation'] == 'pr_merge'
    for key in ('merge_path', 'polls', 'duration_sec'):
        assert key not in result, f'{key} leaked into cmd_pr_merge result: {result}'
    merge_call = next(c for c in captured if c[:2] == ['pr', 'merge'])
    assert '--admin' not in merge_call, merge_call


def test_pr_auto_merge_unaffected(monkeypatch):
    """cmd_pr_auto_merge still enables auto-merge without safe-merge wiring."""
    _install_common(monkeypatch)
    captured: list[list[str]] = []

    def run_gh_stub(args, capture_json=False, timeout=60):
        captured.append(list(args))
        return 0, '', ''

    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    result = github_ops.cmd_pr_auto_merge(
        argparse.Namespace(pr_number=42, head=None, strategy='squash')
    )

    assert result['status'] == 'success', result
    assert result['operation'] == 'pr_auto_merge'
    assert result['enabled'] is True
    merge_call = next(c for c in captured if c[:2] == ['pr', 'merge'])
    assert '--auto' in merge_call, merge_call
    assert '--admin' not in merge_call, merge_call


# ---------------------------------------------------------------------------
# _safe_merge_stuck_state_gate / _safe_merge_behind_by_zero — the GitHub-only
# admin-fallback safety gate. The end-to-end safe-merge tests above monkeypatch
# the gate; these exercise its real ruleset-met verification (fail-closed).
# ---------------------------------------------------------------------------


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


def test_stuck_state_gate_all_requirements_met(monkeypatch):
    """Approved + all checks SUCCESS + behind_by 0 → gate passes."""
    _install_common(monkeypatch)
    monkeypatch.setattr(github_ops, 'view_pr_data', lambda head=None: _pr_view_success_payload())
    monkeypatch.setattr(
        github_ops,
        'run_gh',
        _gate_run_gh(
            view=(0, {
                'reviewDecision': 'APPROVED',
                'statusCheckRollup': [{'name': 'verify', 'conclusion': 'SUCCESS'}],
                'mergeable': 'MERGEABLE',
                'mergeStateStatus': 'BLOCKED',
                'headRefOid': 'abc123',
            }),
            compare=(0, {'behind_by': 0}),
        ),
    )

    ok, reason = github_ops._safe_merge_stuck_state_gate('42')

    assert ok is True, reason
    assert reason is None


def test_stuck_state_gate_review_not_approved(monkeypatch):
    """A non-approved review decision fails the gate closed."""
    _install_common(monkeypatch)
    monkeypatch.setattr(github_ops, 'view_pr_data', lambda head=None: _pr_view_success_payload())
    monkeypatch.setattr(
        github_ops,
        'run_gh',
        _gate_run_gh(
            view=(0, {
                'reviewDecision': 'REVIEW_REQUIRED',
                'statusCheckRollup': [{'name': 'verify', 'conclusion': 'SUCCESS'}],
                'headRefOid': 'abc123',
            }),
            compare=(0, {'behind_by': 0}),
        ),
    )

    ok, reason = github_ops._safe_merge_stuck_state_gate('42')

    assert ok is False
    assert 'not approved' in reason


def test_stuck_state_gate_failing_required_check(monkeypatch):
    """A non-SUCCESS required check fails the gate closed."""
    _install_common(monkeypatch)
    monkeypatch.setattr(github_ops, 'view_pr_data', lambda head=None: _pr_view_success_payload())
    monkeypatch.setattr(
        github_ops,
        'run_gh',
        _gate_run_gh(
            view=(0, {
                'reviewDecision': 'APPROVED',
                'statusCheckRollup': [{'name': 'verify', 'conclusion': 'FAILURE'}],
                'headRefOid': 'abc123',
            }),
            compare=(0, {'behind_by': 0}),
        ),
    )

    ok, reason = github_ops._safe_merge_stuck_state_gate('42')

    assert ok is False
    assert 'verify' in reason and 'FAILURE' in reason


def test_stuck_state_gate_check_not_concluded(monkeypatch):
    """An in-progress (no-conclusion) required check fails the gate closed."""
    _install_common(monkeypatch)
    monkeypatch.setattr(github_ops, 'view_pr_data', lambda head=None: _pr_view_success_payload())
    monkeypatch.setattr(
        github_ops,
        'run_gh',
        _gate_run_gh(
            view=(0, {
                'reviewDecision': 'APPROVED',
                'statusCheckRollup': [{'name': 'verify', 'status': 'IN_PROGRESS'}],
                'headRefOid': 'abc123',
            }),
            compare=(0, {'behind_by': 0}),
        ),
    )

    ok, reason = github_ops._safe_merge_stuck_state_gate('42')

    assert ok is False
    assert 'has not concluded' in reason


def test_stuck_state_gate_behind_base(monkeypatch):
    """A branch behind its base (behind_by != 0) fails the gate closed."""
    _install_common(monkeypatch)
    monkeypatch.setattr(github_ops, 'view_pr_data', lambda head=None: _pr_view_success_payload())
    monkeypatch.setattr(
        github_ops,
        'run_gh',
        _gate_run_gh(
            view=(0, {
                'reviewDecision': 'APPROVED',
                'statusCheckRollup': [{'name': 'verify', 'conclusion': 'SUCCESS'}],
                'headRefOid': 'abc123',
            }),
            compare=(0, {'behind_by': 3}),
        ),
    )

    ok, reason = github_ops._safe_merge_stuck_state_gate('42')

    assert ok is False
    assert 'behind base by 3' in reason


def test_stuck_state_gate_query_failure_fails_closed(monkeypatch):
    """A failed gate query fails closed rather than permitting the admin merge."""
    _install_common(monkeypatch)
    monkeypatch.setattr(github_ops, 'view_pr_data', lambda head=None: _pr_view_success_payload())
    monkeypatch.setattr(
        github_ops,
        'run_gh',
        _gate_run_gh(view=(1, ''), compare=(0, {'behind_by': 0})),
    )

    ok, reason = github_ops._safe_merge_stuck_state_gate('42')

    assert ok is False
    assert 'gate query failed' in reason


def test_stuck_state_gate_unparseable_json_fails_closed(monkeypatch):
    """Unparseable gate-query JSON fails closed."""
    _install_common(monkeypatch)
    monkeypatch.setattr(github_ops, 'view_pr_data', lambda head=None: _pr_view_success_payload())
    monkeypatch.setattr(
        github_ops,
        'run_gh',
        _gate_run_gh(view=(0, 'not-json{'), compare=(0, {'behind_by': 0})),
    )

    ok, reason = github_ops._safe_merge_stuck_state_gate('42')

    assert ok is False
    assert 'could not be parsed' in reason


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


def test_stuck_state_gate_non_list_rollup_fails_closed(monkeypatch):
    """A statusCheckRollup that is not a list fails closed."""
    _install_common(monkeypatch)
    monkeypatch.setattr(github_ops, 'view_pr_data', lambda head=None: _pr_view_success_payload())
    monkeypatch.setattr(
        github_ops,
        'run_gh',
        _gate_run_gh(
            view=(0, {
                'reviewDecision': 'APPROVED',
                'statusCheckRollup': {'not': 'a list'},
                'headRefOid': 'abc123',
            }),
            compare=(0, {'behind_by': 0}),
        ),
    )

    ok, reason = github_ops._safe_merge_stuck_state_gate('42')

    assert ok is False
    assert 'not a list' in reason


def test_behind_by_zero_compare_missing_field_fails_closed(monkeypatch):
    """A compare response missing behind_by fails closed."""
    _install_common(monkeypatch)
    monkeypatch.setattr(github_ops, 'view_pr_data', lambda head=None: _pr_view_success_payload())
    monkeypatch.setattr(
        github_ops,
        'run_gh',
        _gate_run_gh(view=(0, {'behind_by': None}), compare=(0, {})),
    )

    ok, reason = github_ops._safe_merge_behind_by_zero('42', 'abc123')

    assert ok is False
    assert 'missing behind_by' in reason

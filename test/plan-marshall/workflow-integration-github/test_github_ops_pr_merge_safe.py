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
def _branch_ns(branch: str) -> argparse.Namespace:
    return argparse.Namespace(branch=branch, remote_only=True)
def _capture_branch_delete_run_gh(returncode: int = 0, stderr: str = ''):
    """Minimal run_gh stub for cmd_branch_delete tests."""
    captured: list[list[str]] = []

    def run_gh_stub(args, capture_json=False, timeout=60):
        captured.append(list(args))
        return returncode, '', stderr

    return run_gh_stub, captured
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
def _pr_view_payload(merge_state: str, *, state: str | None = None) -> dict:
    """A ``view_pr_data`` success payload with the given ``merge_state``.

    ``state`` overrides the PR lifecycle state (``open`` / ``merged`` /
    ``closed``) so tests can mirror post-merge reality — a merge-queue-required
    base branch closes the PR unmerged (``state: closed``) while a normal merge
    yields ``state: merged``.
    """
    payload = _pr_view_success_payload()
    payload['merge_state'] = merge_state
    if state is not None:
        payload['state'] = state
    return payload
def _sequenced_view_pr_data(states: list[str]):
    """Build a stateful ``view_pr_data`` stub returning ``states`` in order.

    Once the sequence is exhausted the stub returns a ``state: merged`` payload
    (repeating the final ``merge_state``), mirroring post-merge reality: the
    safe-merge preflight consumes the first call for ``base_branch``, the
    readiness poll walks the sequence, and the post-merge re-fetch sees a merged
    PR.
    """
    calls = {'i': 0}

    def stub(head=None):
        idx = calls['i']
        calls['i'] += 1
        if idx < len(states):
            return _pr_view_payload(states[idx])
        return _pr_view_payload(states[-1], state='merged')

    return stub, calls
def _stuck_gate_ok(_identifier):
    return True, None
def _stuck_gate_fail(_identifier):
    return False, 'required check verify has not concluded'


@pytest.mark.parametrize('raw', ['', 'not-a-timestamp', '2026-13-45T99:99:99Z'])
def test_parse_merged_at_rejects_unusable_values(raw):
    """An empty or unparseable stamp is a NON-corroboration, never a wildcard."""
    import _github_pr

    assert _github_pr._parse_merged_at(raw) is None, raw
def test_branch_delete_url_encodes_slash_in_branch_name(monkeypatch):
    """Branch names containing ``/`` are URL-encoded into a single path
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
def test_safe_merge_clean_on_first_poll(monkeypatch):
    """A PR already ``clean`` merges on the first poll via the normal path."""
    _install_common(monkeypatch)
    _install_probe(monkeypatch)
    run_gh_stub, captured = _capture_run_gh(merge_ok=True, delete_mode='ok')
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)
    # A single payload serves all three view_pr_data calls: preflight reads
    # base_branch, the poll reads merge_state='clean', and the post-merge
    # re-fetch reads state='merged'.
    monkeypatch.setattr(github_ops, 'view_pr_data', lambda head=None: _pr_view_payload('clean', state='merged'))

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
def test_safe_merge_blocked_then_clean(monkeypatch):
    """A PR that is ``blocked`` then ``clean`` keeps polling, then merges."""
    _install_common(monkeypatch)
    _install_probe(monkeypatch)
    run_gh_stub, captured = _capture_run_gh(merge_ok=True, delete_mode='ok')
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)
    view_stub, view_calls = _sequenced_view_pr_data(['blocked', 'blocked', 'clean'])
    monkeypatch.setattr(github_ops, 'view_pr_data', view_stub)

    result = github_ops.cmd_pr_safe_merge(_safe_merge_ns(poll_interval=0))

    assert result['status'] == 'success', result
    assert result['merge_path'] == 'polled_clean'
    # The preflight consumed the first view; the poll then walked blocked→clean;
    # the post-merge re-fetch consumed one more — at least three calls total.
    assert view_calls['i'] >= 3, view_calls
    # No admin fallback was needed.
    merge_call = next(c for c in captured if c[:2] == ['pr', 'merge'])
    assert '--admin' not in merge_call, merge_call
def test_safe_merge_stuck_blocked_no_admin_returns_error(monkeypatch):
    """Timed-out while blocked, admin fallback NOT enabled → error, no merge."""
    _install_common(monkeypatch)
    _install_probe(monkeypatch)
    monkeypatch.setattr(github_ops, 'view_pr_data', lambda head=None: _pr_view_success_payload())
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
def test_safe_merge_admin_fallback_on_stuck_blocked(monkeypatch):
    """Stuck blocked + knob on + gate provably met → admin merge fallback."""
    _install_common(monkeypatch)
    _install_probe(monkeypatch)
    monkeypatch.setattr(github_ops, 'view_pr_data', lambda head=None: _pr_view_success_payload())
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
    _install_probe(monkeypatch)
    monkeypatch.setattr(github_ops, 'view_pr_data', lambda head=None: _pr_view_success_payload())
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
    _install_probe(monkeypatch)
    monkeypatch.setattr(github_ops, 'view_pr_data', lambda head=None: _pr_view_success_payload())
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
    _install_probe(monkeypatch)

    result = github_ops.cmd_pr_safe_merge(_safe_merge_ns(admin_merge_on_stuck_state=True, delete_branch=True))

    assert result['status'] == 'success', result
    assert result['merge_path'] == 'admin_fallback'
    assert result['merged'] is True
    assert result['branch_deleted'] == 'feature/x'
    assert result['already_gone'] is False
    # The branch delete went through the REST leaf, URL-encoded.
    delete_calls = [c for c in captured if c[:3] == ['api', '-X', 'DELETE']]
    assert len(delete_calls) == 1, delete_calls
    assert delete_calls[0][-1].endswith('/git/refs/heads/feature%2Fx')
def test_safe_merge_poll_failure_propagates(monkeypatch):
    """A check_fn failure during the readiness poll is surfaced as an error."""
    _install_common(monkeypatch)
    _install_probe(monkeypatch)
    monkeypatch.setattr(github_ops, 'view_pr_data', lambda head=None: _pr_view_success_payload())
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
@pytest.mark.parametrize('post_merge_state', ['closed', 'open', 'merged_without_timestamp'])
def test_safe_merge_polled_clean_closed_without_merge_is_error(monkeypatch, post_merge_state):
    """Merge reports success but the post-merge state does not corroborate → error.

    The old guard probed only for the single known-bad ``state == closed``, so
    every OTHER non-merged shape read as a merge. The positive assertion covers
    all three: the closed-unmerged signature, a PR left ``open``, and the
    wrongly-shaped record whose ``mergedAt`` key exists but carries no instant —
    the last of which a narrow presence check would wave through.
    """
    _install_common(monkeypatch)
    _install_probe(monkeypatch)
    run_gh_stub, captured = _capture_run_gh(merge_ok=True, delete_mode='ok', corroborate=post_merge_state)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)
    monkeypatch.setattr(github_ops, 'view_pr_data', lambda head=None: _pr_view_payload('clean'))

    result = github_ops.cmd_pr_safe_merge(_safe_merge_ns())

    assert result['status'] == 'error', result
    assert result['operation'] == 'pr_safe_merge'
    assert 'corroborate' in result['error'].lower(), result
    # A merge WAS attempted (the false success), but the result is converted.
    merge_calls = [c for c in captured if c[:2] == ['pr', 'merge']]
    assert len(merge_calls) == 1, merge_calls
def test_safe_merge_polled_clean_merged_refetch_succeeds(monkeypatch):
    """Merge reports success and the re-fetch confirms merged → success shape."""
    _install_common(monkeypatch)
    _install_probe(monkeypatch)
    run_gh_stub, captured = _capture_run_gh(merge_ok=True, delete_mode='ok')
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)
    monkeypatch.setattr(github_ops, 'view_pr_data', lambda head=None: _pr_view_payload('clean', state='merged'))

    result = github_ops.cmd_pr_safe_merge(_safe_merge_ns())

    assert result['status'] == 'success', result
    assert result['merge_path'] == 'polled_clean', result
def test_pr_merge_unaffected_no_admin_or_safe_merge_fields(monkeypatch):
    """cmd_pr_merge carries no safe-merge-only fields and never uses --admin."""
    _install_common(monkeypatch)
    _install_merge_preconditions(monkeypatch)
    run_gh_stub, captured = _capture_run_gh(merge_ok=True, delete_mode='ok')
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    result = github_ops.cmd_pr_merge(_merge_ns(delete_branch=False))

    assert result['status'] == 'success', result
    assert result['operation'] == 'pr_merge'
    for key in ('merge_path', 'polls', 'duration_sec'):
        assert key not in result, f'{key} leaked into cmd_pr_merge result: {result}'
    merge_call = next(c for c in captured if c[:2] == ['pr', 'merge'])
    assert '--admin' not in merge_call, merge_call

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
def _counting_view(payload: dict):
    """A ``view_pr_data`` stub returning ``payload`` and counting invocations."""
    calls = {'i': 0}

    def stub(head=None):
        calls['i'] += 1
        return payload

    return stub, calls


def test_pr_merge_merge_failure_skips_branch_delete(monkeypatch):
    _install_common(monkeypatch)
    _install_probe(monkeypatch)
    run_gh_stub, captured = _capture_run_gh(merge_ok=False, delete_mode='ok')
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    pr_view_calls = {'count': 0}

    def tracking_view_pr_data(head=None):
        pr_view_calls['count'] += 1
        return _pr_view_success_payload()

    monkeypatch.setattr(github_ops, 'view_pr_data', tracking_view_pr_data)

    result = github_ops.cmd_pr_merge(_merge_ns(delete_branch=True))

    assert result['status'] == 'error', result
    # No REST DELETE, and no post-merge corroboration re-read either — a failed
    # merge command short-circuits before both.
    delete_calls = [c for c in captured if c[:3] == ['api', '-X', 'DELETE']]
    assert delete_calls == [], delete_calls
    corroboration_calls = [c for c in captured if c[:2] == ['pr', 'view']]
    assert corroboration_calls == [], corroboration_calls
    # Exactly ONE view_pr_data call: the base-branch preflight before the merge.
    # The head-branch resolution for the delete is never reached.
    assert pr_view_calls['count'] == 1, 'only the merge-queue preflight may consult pr view when the merge itself fails'

    _assert_no_delete_branch_flag(captured)
def test_pr_merge_refuses_when_base_merge_queue_required(monkeypatch):
    """A required merge queue on the PR's base branch refuses the immediate merge.

    Without the preflight this is the closed-unmerged signature: ``gh pr merge`` exits zero
    and GitHub closes the PR unmerged.
    """
    _install_common(monkeypatch)
    monkeypatch.setattr(github_ops, 'view_pr_data', lambda head=None: _pr_view_success_payload())
    probe = _install_probe(
        monkeypatch,
        discriminator=github_ops.MERGE_QUEUE_ELIGIBLE_CONFIGURED,
        detail='merge_queue rule active on branch',
    )
    run_gh_stub, captured = _capture_run_gh(merge_ok=True, delete_mode='ok')
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    result = github_ops.cmd_pr_merge(_merge_ns(delete_branch=True))

    assert result['status'] == 'error', result
    assert result['operation'] == 'pr_merge'
    # The message names the base branch and BOTH remedies.
    assert 'main' in result['error'], result
    assert 'ci pr merge-queue' in result['error'], result
    assert 'use_merge_queue' in result['error'], result
    assert '/marshall-steward' in result['error'], result
    # Nothing was attempted: no merge, no branch delete.
    assert captured == [], captured
    assert probe['branch'] == 'main', probe
def test_pr_merge_preflight_probe_error_fails_closed(monkeypatch):
    """An unresolvable queue state refuses the merge rather than merging blind."""
    _install_common(monkeypatch)
    monkeypatch.setattr(github_ops, 'view_pr_data', lambda head=None: _pr_view_success_payload())
    _install_probe(
        monkeypatch,
        discriminator=github_ops.MERGE_QUEUE_INELIGIBLE,
        detail='branch rules endpoint unreachable',
        error='the gh token lacks the scope to read repository rulesets',
    )
    run_gh_stub, captured = _capture_run_gh(merge_ok=True, delete_mode='ok')
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    result = github_ops.cmd_pr_merge(_merge_ns(delete_branch=True))

    assert result['status'] == 'error', result
    assert 'scope' in result['error'], result
    assert captured == [], captured
@pytest.mark.parametrize('post_merge_state', ['closed', 'open', 'merged_without_timestamp', 'unreadable'])
def test_pr_merge_uncorroborated_merge_refuses_and_skips_branch_delete(monkeypatch, post_merge_state):
    """An uncorroborated merge reports error and deletes NOTHING.

    The verdict is established from the post-merge re-read BEFORE the
    branch-delete REST call, so a merge that never landed can never take the head
    branch down with it. ``merged_without_timestamp`` is the wrongly-shaped
    record a narrow ``'mergedAt' in payload`` check would wave through;
    ``unreadable`` is the fail-closed path.
    """
    _install_common(monkeypatch)
    _install_merge_preconditions(monkeypatch)
    run_gh_stub, captured = _capture_run_gh(merge_ok=True, delete_mode='ok', corroborate=post_merge_state)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    result = github_ops.cmd_pr_merge(_merge_ns(delete_branch=True))

    assert result['status'] == 'error', result
    assert result['operation'] == 'pr_merge'
    assert 'corroborate' in result['error'].lower(), result
    # The merge command DID run, but no REST DELETE followed it.
    merge_calls = [c for c in captured if c[:2] == ['pr', 'merge']]
    assert len(merge_calls) == 1, merge_calls
    delete_calls = [c for c in captured if c[:3] == ['api', '-X', 'DELETE']]
    assert delete_calls == [], delete_calls
def test_safe_merge_preflight_refuses_when_merge_queue_required(monkeypatch):
    """A required merge queue on the PR's base branch refuses the immediate merge."""
    _install_common(monkeypatch)
    _install_probe(
        monkeypatch,
        discriminator=github_ops.MERGE_QUEUE_ELIGIBLE_CONFIGURED,
        detail='merge_queue rule active on branch',
    )
    run_gh_stub, captured = _capture_run_gh(merge_ok=True, delete_mode='ok')
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)
    view_stub, view_calls = _counting_view(_pr_view_success_payload())
    monkeypatch.setattr(github_ops, 'view_pr_data', view_stub)

    result = github_ops.cmd_pr_safe_merge(_safe_merge_ns())

    assert result['status'] == 'error', result
    assert result['operation'] == 'pr_safe_merge'
    # The message names the PR's base branch and BOTH remedies.
    assert 'main' in result['error'], result
    assert 'ci pr merge-queue' in result['error'], result
    assert '/marshall-steward' in result['error'], result
    assert 'use_merge_queue' in result['error'], result
    # No merge attempted, and the readiness poll never ran — the preflight is
    # the only view_pr_data consumer on the refusal path.
    merge_calls = [c for c in captured if c[:2] == ['pr', 'merge']]
    assert merge_calls == [], merge_calls
    assert view_calls['i'] == 1, view_calls
def test_safe_merge_preflight_probe_error_fails_closed(monkeypatch):
    """A probe error (auth scope / malformed rules) refuses the merge, fail-closed."""
    _install_common(monkeypatch)
    _install_probe(
        monkeypatch,
        discriminator=github_ops.MERGE_QUEUE_INELIGIBLE,
        detail='branch rules endpoint unreachable',
        error='the gh token lacks the scope to read repository rulesets',
    )
    run_gh_stub, captured = _capture_run_gh(merge_ok=True, delete_mode='ok')
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)
    monkeypatch.setattr(github_ops, 'view_pr_data', lambda head=None: _pr_view_success_payload())

    result = github_ops.cmd_pr_safe_merge(_safe_merge_ns())

    assert result['status'] == 'error', result
    assert 'scope' in result['error'], result
    merge_calls = [c for c in captured if c[:2] == ['pr', 'merge']]
    assert merge_calls == [], merge_calls
@pytest.mark.parametrize(
    'discriminator',
    [
        github_ops.MERGE_QUEUE_ELIGIBLE_UNCONFIGURED,
        github_ops.MERGE_QUEUE_INELIGIBLE,
        github_ops.MERGE_QUEUE_UNSUPPORTED,
    ],
)
def test_safe_merge_preflight_proceeds_for_non_configured(monkeypatch, discriminator):
    """unconfigured / ineligible / unsupported all proceed to the normal merge."""
    _install_common(monkeypatch)
    _install_probe(monkeypatch, discriminator=discriminator)
    run_gh_stub, captured = _capture_run_gh(merge_ok=True, delete_mode='ok')
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)
    monkeypatch.setattr(github_ops, 'view_pr_data', lambda head=None: _pr_view_payload('clean', state='merged'))

    result = github_ops.cmd_pr_safe_merge(_safe_merge_ns())

    assert result['status'] == 'success', result
    assert result['merge_path'] == 'polled_clean', result
    merge_call = next(c for c in captured if c[:2] == ['pr', 'merge'])
    assert '--admin' not in merge_call, merge_call
def test_safe_merge_preflight_probes_pr_own_base_branch(monkeypatch):
    """The preflight probes the PR's OWN base branch, not the repo default."""
    _install_common(monkeypatch)
    probe = _install_probe(monkeypatch, discriminator=github_ops.MERGE_QUEUE_ELIGIBLE_UNCONFIGURED)
    run_gh_stub, captured = _capture_run_gh(merge_ok=True, delete_mode='ok')
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)
    develop_payload = _pr_view_payload('clean', state='merged')
    develop_payload['base_branch'] = 'develop'
    monkeypatch.setattr(github_ops, 'view_pr_data', lambda head=None: develop_payload)

    result = github_ops.cmd_pr_safe_merge(_safe_merge_ns())

    assert result['status'] == 'success', result
    # The probe was driven with the PR's non-default base branch, not 'main'.
    assert probe['branch'] == 'develop', probe
    assert probe['calls'] == 1, probe
def test_safe_merge_preflight_empty_base_branch_fails_closed(monkeypatch):
    """An empty base branch in the PR view refuses the merge, fail-closed."""
    _install_common(monkeypatch)
    _install_probe(monkeypatch)
    run_gh_stub, captured = _capture_run_gh(merge_ok=True, delete_mode='ok')
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)
    empty_base = _pr_view_success_payload()
    empty_base['base_branch'] = ''
    monkeypatch.setattr(github_ops, 'view_pr_data', lambda head=None: empty_base)

    result = github_ops.cmd_pr_safe_merge(_safe_merge_ns())

    assert result['status'] == 'error', result
    assert 'base branch' in result['error'], result
    merge_calls = [c for c in captured if c[:2] == ['pr', 'merge']]
    assert merge_calls == [], merge_calls
def test_safe_merge_preflight_view_failure_fails_closed(monkeypatch):
    """A failed PR view during the preflight refuses the merge, fail-closed."""
    _install_common(monkeypatch)
    _install_probe(monkeypatch)
    run_gh_stub, captured = _capture_run_gh(merge_ok=True, delete_mode='ok')
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)
    monkeypatch.setattr(
        github_ops,
        'view_pr_data',
        lambda head=None: {'status': 'error', 'operation': 'pr_view', 'error': 'No PR found'},
    )

    result = github_ops.cmd_pr_safe_merge(_safe_merge_ns())

    assert result['status'] == 'error', result
    merge_calls = [c for c in captured if c[:2] == ['pr', 'merge']]
    assert merge_calls == [], merge_calls

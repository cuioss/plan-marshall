"""Tests for github_ops.py --head flag routing.

Verifies that branch-aware operations forward the --head value to gh and that
the --pr-number/--head dual-flag validation works as expected.
"""
import argparse

import ci_base
import github_ops
import gitlab_ops
import pytest
from _ci_wait_contract import _ok_auth
from _resolve_project_dir_fixtures import worktree_query_result

from conftest import MARKETPLACE_ROOT

_CORROBORATION_JSON_MARKER = 'mergedAt'
_CORROBORATED_MERGE_PAYLOAD = (
    '{"state": "MERGED", "mergedAt": "2026-01-01T00:00:00Z", "baseRefName": "main", "headRefOid": "abc123"}'
)
def _capture_run_gh():
    """Return a (run_gh_stub, captured_args_list) pair."""
    captured: list[list[str]] = []

    def run_gh_stub(args, capture_json=False, timeout=60):
        captured.append(list(args))
        # Provide a minimal valid response per operation.
        if args[:2] == ['pr', 'create']:
            return 0, 'https://github.com/octo/repo/pull/42', ''
        if args[:2] == ['pr', 'view']:
            if any(_CORROBORATION_JSON_MARKER in str(a) for a in args):
                return 0, _CORROBORATED_MERGE_PAYLOAD, ''
            return 0, '{"number": 42, "url": "https://github.com/octo/repo/pull/42", "state": "OPEN"}', ''
        if args[:2] == ['pr', 'merge']:
            return 0, '', ''
        if args[:2] == ['pr', 'checks']:
            return 0, '[]', ''
        if args[:2] == ['pr', 'update-branch']:
            return 0, '', ''
        return 0, '', ''

    return run_gh_stub, captured
_PROVIDERS = (github_ops, gitlab_ops)
_PROVIDER_IDS = ('github', 'gitlab')
_PROVIDER_FIXTURES = {
    github_ops: {
        'no_pr_stderr': 'no pull requests found for branch "feature/x"',
        'success_stdout': '{"number": 42, "url": "https://github.com/octo/repo/pull/42", "state": "OPEN"}',
    },
    gitlab_ops: {
        'no_pr_stderr': 'no merge requests found for branch "feature/x"',
        'success_stdout': '{"iid": 42, "web_url": "https://gitlab.com/octo/repo/-/merge_requests/42", "state": "opened"}',
    },
}
_CREATE_PR_DOC = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'phase-6-finalize' / 'workflow' / 'create-pr.md'
def _wait_for_comments_args(timeout=2, interval=1):
    return argparse.Namespace(pr_number=42, timeout=timeout, interval=interval)
def _patch_graphql(monkeypatch, pull_request):
    """Patch auth, repo resolution, and the GraphQL call for fetch_pr_comments_data."""
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'get_repo_info', lambda: ('octo', 'repo'))
    monkeypatch.setattr(
        github_ops,
        'run_graphql',
        lambda query, variables: (0, {'repository': {'pullRequest': pull_request}}, ''),
    )
def _comment_record(result, comment_id):
    """Return the projected comment record carrying ``comment_id``."""
    return next(c for c in result['comments'] if c['id'] == comment_id)
_GO_ZERO_GH = '0001-01-01T00:00:00Z'
def _mixed_pass_skipping_checks_json():
    return (
        '['
        '{"name":"a","state":"SUCCESS","bucket":"pass","startedAt":"","completedAt":"","link":"","workflow":"CI"},'
        '{"name":"b","state":"SKIPPED","bucket":"skipping","startedAt":"","completedAt":"","link":"","workflow":"CI"}'
        ']'
    )
def _skipped_only_checks_json():
    """A check set containing ONE check whose state is SKIPPED.

    The single-check shape exercises the "all-terminal" exit path of
    cmd_ci_wait — there is no other check that could be in-progress,
    so the wait loop MUST exit immediately on its first poll.
    """
    return (
        '['
        '{"name":"skipped-only","state":"SKIPPED","bucket":"skipping",'
        '"startedAt":"","completedAt":"","link":"","workflow":"CI"}'
        ']'
    )
_REUSABLE_LINK = 'https://github.com/octo/repo/actions/runs/123/job/456'
_RUN_ONLY_LINK = 'https://github.com/octo/repo/actions/runs/123'


def test_ci_status_with_head(monkeypatch):
    run_gh_stub, captured = _capture_run_gh()
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    ns = argparse.Namespace(pr_number=None, head='feature/x')
    result = github_ops.cmd_ci_status(ns)

    assert result['status'] == 'success', result
    checks_call = next(c for c in captured if c[:2] == ['pr', 'checks'])
    assert checks_call[2] == 'feature/x'
def test_fetch_pr_head_sha_returns_empty_on_unparseable_json(monkeypatch):
    """Malformed gh JSON yields an empty string rather than raising."""
    monkeypatch.setattr(github_ops, 'run_gh', lambda *_a, **_kw: (0, 'not-json', ''))

    assert github_ops.fetch_pr_head_sha(42) == ''
def test_fetch_pr_reviews_with_commits_defaults_missing_fields(monkeypatch):
    """Reviews missing user/state/submitted_at/commit_id/body get safe defaults."""
    monkeypatch.setattr(github_ops, 'get_repo_info', lambda: ('octo', 'repo'))
    # --slurp wraps pages in an outer array; simulate a single page with one empty review.
    monkeypatch.setattr(github_ops, 'run_gh', lambda *_a, **_kw: (0, '[[{}]]', ''))

    result = github_ops.fetch_pr_reviews_with_commits(42)

    assert result['status'] == 'success'
    assert result['reviews'] == [
        {'user': 'unknown', 'state': 'UNKNOWN', 'submitted_at': '', 'commit_sha': '', 'body': ''}
    ]
def test_fetch_pr_reviews_with_commits_no_repo_info(monkeypatch):
    """When repo owner/name cannot be resolved, an error envelope is returned."""
    monkeypatch.setattr(github_ops, 'get_repo_info', lambda: (None, None))

    result = github_ops.fetch_pr_reviews_with_commits(42)

    assert result['status'] == 'error'
    assert result['operation'] == 'fetch_pr_reviews_with_commits'
    assert 'owner/name' in result['error']
def test_fetch_pr_comments_data_surfaces_updated_at_on_issue_comments(monkeypatch):
    """An issue comment's ``updatedAt`` is projected as ``updated_at``."""
    _patch_graphql(
        monkeypatch,
        {
            'reviewThreads': {'nodes': []},
            'reviews': {'nodes': []},
            'comments': {
                'nodes': [
                    {
                        'id': 'IC_1',
                        'body': '## PR Reviewer Guide',
                        'author': {'login': 'cuioss-review-bot'},
                        'createdAt': '2026-07-26T09:27:15Z',
                        'updatedAt': '2026-07-26T11:00:00Z',
                    }
                ]
            },
        },
    )

    result = github_ops.fetch_pr_comments_data(103)

    assert result['status'] == 'success'
    record = _comment_record(result, 'IC_1')
    assert record['kind'] == 'issue_comment'
    assert record['created_at'] == '2026-07-26T09:27:15Z'
    assert record['updated_at'] == '2026-07-26T11:00:00Z'
def test_pr_wait_for_comments_times_out_when_no_new_comments(monkeypatch):
    """Timeout path: count never grows above baseline → returns timed_out: true, new_count: 0."""
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)

    def fake_fetch(pr_number, unresolved_only=False):
        return {'status': 'success', 'unresolved': 5, 'comments': []}

    monkeypatch.setattr(github_ops, 'fetch_pr_comments_data', fake_fetch)

    result = github_ops.cmd_pr_wait_for_comments(_wait_for_comments_args(timeout=1, interval=1))

    assert result['status'] == 'success', result
    assert result['operation'] == 'pr_wait_for_comments'
    assert result['timed_out'] is True
    assert result['baseline_count'] == 5
    assert result['final_count'] == 5
    assert result['new_count'] == 0
def test_main_project_dir_equals_form(tmp_path, monkeypatch, capsys):
    """The --project-dir=PATH form is also honoured by github_ops.main().

    Uses ``pr view`` (no subcommand-level --plan-id) with a mocked gh response
    so the test does not require a live GitHub token.

    Fix A (secondary guard): ``--plan-id`` must appear before the subcommand
    token. ``--project-dir=PATH`` (equals form) before the subcommand is the
    explicit-path escape hatch and must still work.

    Uses the module-level ``ci_base`` binding for the same reason as the sibling
    above — see its docstring.
    """
    import sys

    monkeypatch.setattr(ci_base, '_DEFAULT_CWD', None, raising=False)

    # Mock gh pr view to return a minimal success JSON so the handler
    # returns a result dict instead of raising on missing auth.
    monkeypatch.setattr(
        ci_base.subprocess,
        'run',
        lambda cmd, **kw: type('R', (), {'returncode': 0, 'stdout': '{}', 'stderr': ''})(),
    )

    worktree = str(tmp_path / 'wt2')
    monkeypatch.setattr(
        sys,
        'argv',
        [
            'github_ops.py',
            f'--project-dir={worktree}',
            'pr',
            'view',
        ],
    )

    github_ops.main()
    assert ci_base.get_default_cwd() == worktree
    capsys.readouterr()  # drain
def test_main_routes_plan_id_via_extract_routing_args(monkeypatch):
    """github_ops.main() MUST consume router-level --plan-id and set the default cwd."""
    import file_ops as _resolver_core
    from ci_base import get_default_cwd

    # Patch the manage-status shell-out seam, which lives in file_ops —
    # resolve_project_dir delegates the worktree face to resolve_plan_context.
    monkeypatch.setattr(
        _resolver_core, '_query_worktree_path', lambda _pid: worktree_query_result(True, '/tmp/wt-resolved')
    )
    # Stub gh CLI invocations so we don't actually shell out.
    captured_cwds: list = []

    def fake_run_cli(_cli, _args, **kwargs):
        captured_cwds.append(kwargs.get('cwd'))
        return 0, '{"number": 1, "state": "OPEN"}', ''

    # Redirect the test argv so main() sees the routing flag pair plus a
    # safe subcommand that needs no real gh invocation. We swallow the
    # argparse-required arguments by hitting a help-style path instead.
    monkeypatch.setattr(
        'sys.argv',
        [
            'github_ops.py',
            '--plan-id',
            'task-routing-canonical',
            '--help',
        ],
    )

    # main() will sys.exit(0) on --help; we just verify extract_routing_args
    # was honoured (cwd default set BEFORE argparse runs).
    import pytest as _pytest

    with _pytest.raises(SystemExit):
        github_ops.main()

    # After main() returns, the default cwd must reflect the resolved worktree.
    assert get_default_cwd() == '/tmp/wt-resolved', (
        f'Expected default cwd to be set from --plan-id resolution; got {get_default_cwd()!r}'
    )

    # Cleanup — restore default cwd to None for downstream tests.
    from ci_base import set_default_cwd

    set_default_cwd(None)
def test_ci_status_aggregates_pass_plus_skipping_as_success(monkeypatch):
    """pass + skipping → overall=success (skipping is non-failing)."""
    payload = _mixed_pass_skipping_checks_json()

    def run_gh_stub(args, capture_json=False, timeout=60):
        if args[:2] == ['pr', 'checks']:
            return 0, payload, ''
        return 0, '', ''

    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    ns = argparse.Namespace(pr_number=42, head=None)
    result = github_ops.cmd_ci_status(ns)
    assert result['status'] == 'success'
    assert result['overall_status'] == 'success', result
def test_ci_wait_aggregates_pass_plus_skipping_as_success(monkeypatch):
    """ci_wait: pass + skipping → final_status=success (not 'mixed')."""
    import json as _json

    checks = _json.loads(_mixed_pass_skipping_checks_json())

    def run_gh_stub(args, capture_json=False, timeout=60):
        if args[:2] == ['pr', 'checks']:
            return 0, _mixed_pass_skipping_checks_json(), ''
        return 0, '', ''

    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)
    # poll_until returns the fully-resolved check set immediately.
    monkeypatch.setattr(
        github_ops,
        'poll_until',
        lambda check_fn, is_complete_fn, **_: {
            'timed_out': False,
            'duration_sec': 1,
            'polls': 1,
            'last_data': {'checks': checks},
        },
    )

    ns = argparse.Namespace(pr_number=42, timeout=30, interval=5)
    result = github_ops.cmd_ci_wait(ns)
    assert result['status'] == 'success'
    assert result['final_status'] == 'success', result
def test_fetch_pr_overall_ci_status_pass_plus_skipping_is_success(monkeypatch):
    """_fetch_pr_overall_ci_status: pass + skipping → 'success'."""
    payload = _mixed_pass_skipping_checks_json()

    def run_gh_stub(args, capture_json=False, timeout=60):
        if args[:2] == ['pr', 'checks']:
            return 0, payload, ''
        return 0, '', ''

    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)
    ok, overall = github_ops._fetch_pr_overall_ci_status(42)
    assert ok is True
    assert overall == 'success'
def test_ci_wait_exits_immediately_for_skipped_only_check_set(monkeypatch):
    """A SKIPPED-only check set MUST be treated as all-terminal so cmd_ci_wait
    exits on its first poll with final_status=success and an empty
    failing_checks list. A regression that classifies SKIPPED as in-progress
    would block the wait loop until the host-platform timeout fires.
    """
    import json as _json

    checks = _json.loads(_skipped_only_checks_json())

    def run_gh_stub(args, capture_json=False, timeout=60):
        if args[:2] == ['pr', 'checks']:
            return 0, _skipped_only_checks_json(), ''
        return 0, '', ''

    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)
    # The poll loop returns the SKIPPED-only check set on the first poll.
    monkeypatch.setattr(
        github_ops,
        'poll_until',
        lambda check_fn, is_complete_fn, **_: {
            'timed_out': False,
            'duration_sec': 1,
            'polls': 1,
            'last_data': {'checks': checks},
        },
    )

    ns = argparse.Namespace(pr_number=42, timeout=30, interval=5)
    result = github_ops.cmd_ci_wait(ns)
    assert result['status'] == 'success'
    assert result['final_status'] == 'success', (
        f'SKIPPED-only check set must classify as final_status=success; got {result!r}'
    )
    assert result.get('failing_checks', []) == [], (
        f'SKIPPED-only check set must produce zero failing_checks; got {result.get("failing_checks")!r}'
    )
def test_ci_status_and_ci_wait_agree_on_skipped_bearing_set(monkeypatch):
    """cmd_ci_status() and cmd_ci_wait() MUST agree on a SKIPPED-bearing
    check set: both resolve to success. A divergence would surface as
    cmd_ci_status reporting "success" while cmd_ci_wait reports "failure"
    or "mixed" — the exact failure mode the bucket-based classification
    bug produced before the SKIPPED-state fix.
    """
    import json as _json

    payload = (
        '['
        '{"name":"build","state":"SUCCESS","bucket":"pass","startedAt":"","completedAt":"","link":"","workflow":"CI"},'
        '{"name":"lint","state":"SKIPPED","bucket":"skipping","startedAt":"","completedAt":"","link":"","workflow":"CI"},'
        '{"name":"deploy","state":"SKIPPED","bucket":"skipping","startedAt":"","completedAt":"","link":"","workflow":"CI"}'
        ']'
    )
    checks = _json.loads(payload)

    def run_gh_stub(args, capture_json=False, timeout=60):
        if args[:2] == ['pr', 'checks']:
            return 0, payload, ''
        return 0, '', ''

    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    # cmd_ci_status: synchronous read of the same check set.
    status_ns = argparse.Namespace(pr_number=42, head=None)
    status_result = github_ops.cmd_ci_status(status_ns)
    assert status_result['status'] == 'success'
    assert status_result['overall_status'] == 'success'

    # cmd_ci_wait: short-circuit the poll loop to the same data.
    monkeypatch.setattr(
        github_ops,
        'poll_until',
        lambda check_fn, is_complete_fn, **_: {
            'timed_out': False,
            'duration_sec': 1,
            'polls': 1,
            'last_data': {'checks': checks},
        },
    )
    wait_ns = argparse.Namespace(pr_number=42, timeout=30, interval=5)
    wait_result = github_ops.cmd_ci_wait(wait_ns)
    assert wait_result['status'] == 'success'
    assert wait_result['final_status'] == 'success'

    # Agreement is the load-bearing assertion: both verdicts MUST match.
    assert status_result['overall_status'] == wait_result['final_status'], (
        f'cmd_ci_status (overall_status={status_result["overall_status"]!r}) '
        f'and cmd_ci_wait (final_status={wait_result["final_status"]!r}) '
        'disagree on a SKIPPED-bearing check set — the bucket-vs-state '
        'classification bug is back'
    )
def test_cmd_ci_logs_returns_error_context_window_not_head(monkeypatch):
    """cmd_ci_logs must surface the failure tail via the error-context filter.

    A raw log whose ERROR/Traceback lines fall well past line 200 would have
    been dropped by the old head-200 truncation; the error-context window keeps
    them.
    """
    setup_lines = [f'runner setup line {i}' for i in range(260)]
    setup_lines[250] = 'Traceback (most recent call last):'
    setup_lines[251] = '  File "foo.py", line 9, in bar'
    setup_lines[252] = 'IndexError: list index out of range'
    raw_log = '\n'.join(setup_lines)

    def run_gh_stub(args, capture_json=False, timeout=60):
        assert args[:4] == ['run', 'view', '999', '--log-failed']
        return 0, raw_log, ''

    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    ns = argparse.Namespace(run_id='999')
    result = github_ops.cmd_ci_logs(ns)

    assert result['status'] == 'success', result
    content = result['content']
    # The failure tail (past line 200) is present — the head-200 path dropped it.
    assert 'Traceback (most recent call last):' in content
    assert 'IndexError: list index out of range' in content
    # Pure runner-setup noise that is far from any error marker is dropped.
    assert 'runner setup line 10' not in content

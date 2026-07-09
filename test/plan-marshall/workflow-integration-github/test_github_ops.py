#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for github_ops.py --head flag routing.

Verifies that branch-aware operations forward the --head value to gh and that
the --pr-number/--head dual-flag validation works as expected.
"""

import argparse

import github_ops


def _ok_auth():
    return True, ''


def _capture_run_gh():
    """Return a (run_gh_stub, captured_args_list) pair."""
    captured: list[list[str]] = []

    def run_gh_stub(args, capture_json=False, timeout=60):
        captured.append(list(args))
        # Provide a minimal valid response per operation.
        if args[:2] == ['pr', 'create']:
            return 0, 'https://github.com/octo/repo/pull/42', ''
        if args[:2] == ['pr', 'view']:
            return 0, '{"number": 42, "url": "https://github.com/octo/repo/pull/42", "state": "OPEN"}', ''
        if args[:2] == ['pr', 'merge']:
            return 0, '', ''
        if args[:2] == ['pr', 'checks']:
            return 0, '[]', ''
        if args[:2] == ['pr', 'update-branch']:
            return 0, '', ''
        return 0, '', ''

    return run_gh_stub, captured


# =============================================================================
# pr_create --head
# =============================================================================


def _prepare_pr_create_body(tmp_path, monkeypatch, body_text='B', plan_id='p'):
    """Seed PLAN_BASE_DIR with a prepared pr-create body scratch file."""
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
    from ci_base import BODY_KIND_PR_CREATE, get_body_path

    path = get_body_path(plan_id, BODY_KIND_PR_CREATE)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body_text, encoding='utf-8')
    return plan_id


def test_pr_create_forwards_head_flag(monkeypatch, tmp_path):
    run_gh_stub, captured = _capture_run_gh()
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    plan_id = _prepare_pr_create_body(tmp_path, monkeypatch)
    ns = argparse.Namespace(title='T', plan_id=plan_id, slot=None, base=None, draft=False, head='feature/x')
    result = github_ops.cmd_pr_create(ns)

    assert result['status'] == 'success', result
    assert any('--head' in c and 'feature/x' in c for c in captured), captured


def test_pr_create_omits_head_when_unset(monkeypatch, tmp_path):
    run_gh_stub, captured = _capture_run_gh()
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    plan_id = _prepare_pr_create_body(tmp_path, monkeypatch)
    ns = argparse.Namespace(title='T', plan_id=plan_id, slot=None, base=None, draft=False, head=None)
    result = github_ops.cmd_pr_create(ns)

    assert result['status'] == 'success', result
    assert not any('--head' in c for c in captured), captured


# =============================================================================
# pr_view --head
# =============================================================================


def test_pr_view_forwards_head_as_positional(monkeypatch):
    run_gh_stub, captured = _capture_run_gh()
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    ns = argparse.Namespace(head='feature/x')
    result = github_ops.cmd_pr_view(ns)

    assert result['status'] == 'success', result
    pr_view_call = next(c for c in captured if c[:2] == ['pr', 'view'])
    assert 'feature/x' in pr_view_call, pr_view_call


# =============================================================================
# pr_merge --head / --pr-number
# =============================================================================


def test_pr_merge_with_head(monkeypatch):
    run_gh_stub, captured = _capture_run_gh()
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    ns = argparse.Namespace(pr_number=None, head='feature/x', strategy='merge', delete_branch=False)
    result = github_ops.cmd_pr_merge(ns)

    assert result['status'] == 'success', result
    merge_call = next(c for c in captured if c[:2] == ['pr', 'merge'])
    assert merge_call[2] == 'feature/x'


def test_pr_merge_with_pr_number(monkeypatch):
    run_gh_stub, captured = _capture_run_gh()
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    ns = argparse.Namespace(pr_number=42, head=None, strategy='merge', delete_branch=False)
    result = github_ops.cmd_pr_merge(ns)

    assert result['status'] == 'success', result
    merge_call = next(c for c in captured if c[:2] == ['pr', 'merge'])
    assert merge_call[2] == '42'


def test_pr_merge_dual_flag_rejected(monkeypatch):
    run_gh_stub, captured = _capture_run_gh()
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    ns = argparse.Namespace(pr_number=42, head='feature/x', strategy='merge', delete_branch=False)
    result = github_ops.cmd_pr_merge(ns)

    assert result['status'] == 'error'
    assert 'exactly one' in result['error']
    assert captured == [], 'Should not invoke gh when validation fails'


def test_pr_merge_neither_flag_rejected(monkeypatch):
    run_gh_stub, captured = _capture_run_gh()
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    ns = argparse.Namespace(pr_number=None, head=None, strategy='merge', delete_branch=False)
    result = github_ops.cmd_pr_merge(ns)

    assert result['status'] == 'error'
    assert 'either' in result['error']


# =============================================================================
# pr_auto_merge --head
# =============================================================================


def test_pr_auto_merge_with_head(monkeypatch):
    run_gh_stub, captured = _capture_run_gh()
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    ns = argparse.Namespace(pr_number=None, head='feature/x', strategy='merge')
    result = github_ops.cmd_pr_auto_merge(ns)

    assert result['status'] == 'success', result
    merge_call = next(c for c in captured if c[:2] == ['pr', 'merge'])
    assert merge_call[2] == 'feature/x'
    assert '--auto' in merge_call


def test_pr_auto_merge_dual_flag_rejected(monkeypatch):
    run_gh_stub, _ = _capture_run_gh()
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    ns = argparse.Namespace(pr_number=42, head='feature/x', strategy='merge')
    result = github_ops.cmd_pr_auto_merge(ns)

    assert result['status'] == 'error'
    assert 'exactly one' in result['error']


# =============================================================================
# pr_update_branch --head / --pr-number
# =============================================================================


def test_pr_update_branch_with_head(monkeypatch):
    run_gh_stub, captured = _capture_run_gh()
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    ns = argparse.Namespace(pr_number=None, head='feature/x')
    result = github_ops.cmd_pr_update_branch(ns)

    assert result['status'] == 'success', result
    update_call = next(c for c in captured if c[:2] == ['pr', 'update-branch'])
    assert update_call[2] == 'feature/x'


def test_pr_update_branch_with_pr_number(monkeypatch):
    run_gh_stub, captured = _capture_run_gh()
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    ns = argparse.Namespace(pr_number=42, head=None)
    result = github_ops.cmd_pr_update_branch(ns)

    assert result['status'] == 'success', result
    update_call = next(c for c in captured if c[:2] == ['pr', 'update-branch'])
    assert update_call[2] == '42'


def test_pr_update_branch_dual_flag_rejected(monkeypatch):
    run_gh_stub, captured = _capture_run_gh()
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    ns = argparse.Namespace(pr_number=42, head='feature/x')
    result = github_ops.cmd_pr_update_branch(ns)

    assert result['status'] == 'error'
    assert 'exactly one' in result['error']
    assert captured == [], 'Should not invoke gh when validation fails'


def test_pr_update_branch_neither_flag_rejected(monkeypatch):
    run_gh_stub, captured = _capture_run_gh()
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    ns = argparse.Namespace(pr_number=None, head=None)
    result = github_ops.cmd_pr_update_branch(ns)

    assert result['status'] == 'error'
    assert 'either' in result['error']


def test_pr_update_branch_gh_failure(monkeypatch):
    """When gh returns non-zero, the handler should return an error result."""

    def failing_run_gh(args, capture_json=False, timeout=60):
        if args[:2] == ['pr', 'update-branch']:
            return 1, '', 'merge conflict'
        return 0, '', ''

    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', failing_run_gh)

    ns = argparse.Namespace(pr_number=42, head=None)
    result = github_ops.cmd_pr_update_branch(ns)

    assert result['status'] == 'error'
    assert 'Failed to update branch' in result['error']


def test_pr_update_branch_auth_failure(monkeypatch):
    """When auth fails, the handler should return an error result."""
    monkeypatch.setattr(github_ops, 'check_auth', lambda: (False, 'not logged in'))
    monkeypatch.setattr(github_ops, 'run_gh', _capture_run_gh()[0])

    ns = argparse.Namespace(pr_number=42, head=None)
    result = github_ops.cmd_pr_update_branch(ns)

    assert result['status'] == 'error'
    assert 'not logged in' in result['error']


# =============================================================================
# ci_status --head
# =============================================================================


def test_ci_status_with_head(monkeypatch):
    run_gh_stub, captured = _capture_run_gh()
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    ns = argparse.Namespace(pr_number=None, head='feature/x')
    result = github_ops.cmd_ci_status(ns)

    assert result['status'] == 'success', result
    checks_call = next(c for c in captured if c[:2] == ['pr', 'checks'])
    assert checks_call[2] == 'feature/x'


# =============================================================================
# Re-review registry helpers: fetch_pr_head_sha, post_pr_comment,
# fetch_pr_reviews_with_commits
#
# These three functions back the post-merge re-review strategy registry
# (github_re_review.py). Each goes through run_gh; get_repo_info (itself a
# run_gh caller) is mocked directly where the function under test consults it.
# Tests never shell out to the real gh CLI.
# =============================================================================


def test_fetch_pr_head_sha_returns_sha_on_success(monkeypatch):
    """The public wrapper resolves headRefOid from gh pr view JSON."""
    captured: list[list[str]] = []

    def run_gh_stub(args, capture_json=False, timeout=60):
        captured.append(list(args))
        return 0, '{"headRefOid": "abc123def"}', ''

    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    sha = github_ops.fetch_pr_head_sha(42)

    assert sha == 'abc123def'
    # The wrapper forwards to gh pr view --json headRefOid for the PR.
    assert captured == [['pr', 'view', '42', '--json', 'headRefOid']]


def test_fetch_pr_head_sha_returns_empty_on_gh_failure(monkeypatch):
    """A non-zero gh exit yields an empty string (no-abort contract)."""
    monkeypatch.setattr(github_ops, 'run_gh', lambda *_a, **_kw: (1, '', 'boom'))

    assert github_ops.fetch_pr_head_sha(42) == ''


def test_fetch_pr_head_sha_returns_empty_on_unparseable_json(monkeypatch):
    """Malformed gh JSON yields an empty string rather than raising."""
    monkeypatch.setattr(github_ops, 'run_gh', lambda *_a, **_kw: (0, 'not-json', ''))

    assert github_ops.fetch_pr_head_sha(42) == ''


def test_fetch_pr_head_sha_returns_empty_when_field_missing(monkeypatch):
    """A JSON payload without headRefOid yields an empty string."""
    monkeypatch.setattr(github_ops, 'run_gh', lambda *_a, **_kw: (0, '{"other": "x"}', ''))

    assert github_ops.fetch_pr_head_sha(42) == ''


def test_post_pr_comment_success(monkeypatch):
    """A successful gh pr comment returns a success envelope with the output."""
    captured: list[list[str]] = []

    def run_gh_stub(args, capture_json=False, timeout=60):
        captured.append(list(args))
        return 0, 'https://github.com/octo/repo/pull/42#issuecomment-1\n', ''

    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    result = github_ops.post_pr_comment(42, '/gemini review')

    assert result['status'] == 'success'
    assert result['operation'] == 'post_pr_comment'
    assert result['pr_number'] == 42
    assert result['output'] == 'https://github.com/octo/repo/pull/42#issuecomment-1'
    assert captured == [['pr', 'comment', '42', '--body', '/gemini review']]


def test_post_pr_comment_gh_failure_returns_error(monkeypatch):
    """A non-zero gh exit surfaces as an error envelope carrying stderr."""
    monkeypatch.setattr(github_ops, 'run_gh', lambda *_a, **_kw: (1, '', 'no such PR\n'))

    result = github_ops.post_pr_comment(42, '/gemini review')

    assert result['status'] == 'error'
    assert result['operation'] == 'post_pr_comment'
    assert 'no such PR' in result['context']


def test_fetch_pr_reviews_with_commits_success(monkeypatch):
    """Reviews are projected to {user, state, submitted_at, commit_sha} rows."""
    captured: list[list[str]] = []

    def run_gh_stub(args, capture_json=False, timeout=60):
        captured.append(list(args))
        # --slurp wraps all pages into an outer array; simulate a single page.
        payload = (
            '[[{"user": {"login": "coderabbitai"}, "state": "COMMENTED", '
            '"submitted_at": "2026-01-01T00:05:00Z", "commit_id": "headsha"}]]'
        )
        return 0, payload, ''

    monkeypatch.setattr(github_ops, 'get_repo_info', lambda: ('octo', 'repo'))
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    result = github_ops.fetch_pr_reviews_with_commits(42)

    assert result['status'] == 'success'
    assert result['operation'] == 'fetch_pr_reviews_with_commits'
    assert result['review_count'] == 1
    assert result['reviews'] == [
        {
            'user': 'coderabbitai',
            'state': 'COMMENTED',
            'submitted_at': '2026-01-01T00:05:00Z',
            'commit_sha': 'headsha',
        }
    ]
    # REST /reviews endpoint is consulted with --paginate --slurp.
    assert captured == [['api', 'repos/octo/repo/pulls/42/reviews', '--paginate', '--slurp']]


def test_fetch_pr_reviews_with_commits_defaults_missing_fields(monkeypatch):
    """Reviews missing user/state/submitted_at/commit_id get safe defaults."""
    monkeypatch.setattr(github_ops, 'get_repo_info', lambda: ('octo', 'repo'))
    # --slurp wraps pages in an outer array; simulate a single page with one empty review.
    monkeypatch.setattr(github_ops, 'run_gh', lambda *_a, **_kw: (0, '[[{}]]', ''))

    result = github_ops.fetch_pr_reviews_with_commits(42)

    assert result['status'] == 'success'
    assert result['reviews'] == [
        {'user': 'unknown', 'state': 'UNKNOWN', 'submitted_at': '', 'commit_sha': ''}
    ]


def test_fetch_pr_reviews_with_commits_skips_non_dict_rows(monkeypatch):
    """Non-dict entries in the reviews page array are filtered out."""
    monkeypatch.setattr(github_ops, 'get_repo_info', lambda: ('octo', 'repo'))
    # --slurp wraps pages in an outer array; non-dict entries within the page are skipped.
    monkeypatch.setattr(
        github_ops,
        'run_gh',
        lambda *_a, **_kw: (0, '[["junk", {"user": {"login": "bot"}, "commit_id": "s"}]]', ''),
    )

    result = github_ops.fetch_pr_reviews_with_commits(42)

    assert result['status'] == 'success'
    assert result['review_count'] == 1
    assert result['reviews'][0]['user'] == 'bot'


def test_fetch_pr_reviews_with_commits_no_repo_info(monkeypatch):
    """When repo owner/name cannot be resolved, an error envelope is returned."""
    monkeypatch.setattr(github_ops, 'get_repo_info', lambda: (None, None))

    result = github_ops.fetch_pr_reviews_with_commits(42)

    assert result['status'] == 'error'
    assert result['operation'] == 'fetch_pr_reviews_with_commits'
    assert 'owner/name' in result['error']


def test_fetch_pr_reviews_with_commits_gh_failure(monkeypatch):
    """A non-zero gh api exit surfaces as an error envelope."""
    monkeypatch.setattr(github_ops, 'get_repo_info', lambda: ('octo', 'repo'))
    monkeypatch.setattr(github_ops, 'run_gh', lambda *_a, **_kw: (1, '', 'api error\n'))

    result = github_ops.fetch_pr_reviews_with_commits(42)

    assert result['status'] == 'error'
    assert 'Failed to fetch reviews' in result['error']
    assert 'api error' in result['context']


def test_fetch_pr_reviews_with_commits_unparseable_json(monkeypatch):
    """Malformed gh api JSON surfaces as a parse error envelope."""
    monkeypatch.setattr(github_ops, 'get_repo_info', lambda: ('octo', 'repo'))
    monkeypatch.setattr(github_ops, 'run_gh', lambda *_a, **_kw: (0, 'not-json', ''))

    result = github_ops.fetch_pr_reviews_with_commits(42)

    assert result['status'] == 'error'
    assert 'Failed to parse' in result['error']


def test_fetch_pr_reviews_with_commits_non_list_payload(monkeypatch):
    """A non-list reviews payload surfaces as an unexpected-shape error."""
    monkeypatch.setattr(github_ops, 'get_repo_info', lambda: ('octo', 'repo'))
    monkeypatch.setattr(github_ops, 'run_gh', lambda *_a, **_kw: (0, '{"message": "x"}', ''))

    result = github_ops.fetch_pr_reviews_with_commits(42)

    assert result['status'] == 'error'
    assert 'Unexpected reviews payload shape' in result['error']


def test_ci_status_dual_flag_rejected(monkeypatch):
    run_gh_stub, _ = _capture_run_gh()
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    ns = argparse.Namespace(pr_number=42, head='feature/x')
    result = github_ops.cmd_ci_status(ns)

    assert result['status'] == 'error'
    assert 'exactly one' in result['error']


# =============================================================================
# pr wait-for-comments (poll-instead-of-sleep replacement)
# =============================================================================


def _wait_for_comments_args(timeout=2, interval=1):
    return argparse.Namespace(pr_number=42, timeout=timeout, interval=interval)


def test_pr_wait_for_comments_returns_when_new_comment_arrives(monkeypatch):
    """Happy path: baseline=1, second poll sees count=2 → returns timed_out: false, new_count: 1."""
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)

    call_counts = {'fetch': 0}

    def fake_fetch(pr_number, unresolved_only=False):
        assert pr_number == 42
        # After the poll settles the handler makes ONE additional all-comments
        # fetch (unresolved_only defaults to False) to compute the rate_limited
        # discriminator. Tolerate that extra call: return a genuine (non
        # rate-limit) CodeRabbit review payload so the discriminator resolves
        # False without touching the poll-path baseline/new counting.
        if not unresolved_only:
            return {
                'status': 'success',
                'unresolved': 2,
                'comments': [
                    {
                        'author': 'coderabbitai[bot]',
                        'created_at': '2026-07-09T10:00:00Z',
                        'body': 'Looks good overall, one nit on the variable name.',
                    }
                ],
            }
        call_counts['fetch'] += 1
        # First call (baseline) returns 1; subsequent calls return 2 (new comment arrived)
        unresolved = 1 if call_counts['fetch'] == 1 else 2
        return {'status': 'success', 'unresolved': unresolved, 'comments': []}

    monkeypatch.setattr(github_ops, 'fetch_pr_comments_data', fake_fetch)

    result = github_ops.cmd_pr_wait_for_comments(_wait_for_comments_args())

    assert result['status'] == 'success', result
    assert result['operation'] == 'pr_wait_for_comments'
    assert result['pr_number'] == 42
    assert result['timed_out'] is False
    assert result['baseline_count'] == 1
    assert result['final_count'] == 2
    assert result['new_count'] == 1
    assert result['polls'] >= 1
    # baseline + at least one poll (post-poll rate-limit fetch is not counted)
    assert call_counts['fetch'] >= 2
    # the rate-limit discriminator is present and False for a genuine review
    assert 'rate_limited' in result
    assert result['rate_limited'] is False


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


def test_pr_wait_for_comments_returns_error_when_initial_fetch_fails(monkeypatch):
    """Error path: baseline fetch fails → returns status: error before polling starts."""
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)

    def failing_fetch(pr_number, unresolved_only=False):
        return {'status': 'error', 'error': 'GraphQL query failed: boom'}

    monkeypatch.setattr(github_ops, 'fetch_pr_comments_data', failing_fetch)

    result = github_ops.cmd_pr_wait_for_comments(_wait_for_comments_args())

    assert result['status'] == 'error', result
    assert result['operation'] == 'pr_wait_for_comments'
    assert 'Initial unresolved-comment fetch failed' in result['error']


def test_pr_wait_for_comments_returns_error_when_auth_fails(monkeypatch):
    """Auth failure short-circuits before any fetch."""
    monkeypatch.setattr(github_ops, 'check_auth', lambda: (False, 'not logged in'))

    fetch_calls = {'count': 0}

    def fake_fetch(pr_number, unresolved_only=False):
        fetch_calls['count'] += 1
        return {'status': 'success', 'unresolved': 0, 'comments': []}

    monkeypatch.setattr(github_ops, 'fetch_pr_comments_data', fake_fetch)

    result = github_ops.cmd_pr_wait_for_comments(_wait_for_comments_args())

    assert result['status'] == 'error', result
    assert result['operation'] == 'pr_wait_for_comments'
    assert 'not logged in' in result['error']
    assert fetch_calls['count'] == 0, 'fetch should not be called when auth fails'


# =============================================================================
# --project-dir pre-parse plumbing (cwd forwarding)
# =============================================================================


def test_main_project_dir_sets_default_cwd(tmp_path, monkeypatch, capsys):
    """github_ops.main() strips --project-dir from argv and installs it as the
    process-global default cwd used by ci_base.run_cli.

    Uses ``pr view`` (no subcommand-level --plan-id) with a mocked gh response
    so the test does not require a live GitHub token.

    Fix A (secondary guard): ``--plan-id`` must appear before the subcommand
    token, not after. ``--project-dir`` may still appear before the subcommand
    as the explicit-path escape hatch.
    """
    import sys

    import ci_base

    monkeypatch.setattr(ci_base, '_DEFAULT_CWD', None, raising=False)

    # Mock gh pr view to return a minimal success JSON so the handler
    # returns a result dict instead of raising on missing auth.
    monkeypatch.setattr(
        ci_base.subprocess,
        'run',
        lambda cmd, **kw: type('R', (), {'returncode': 0, 'stdout': '{}', 'stderr': ''})(),
    )

    worktree = str(tmp_path / 'worktree')
    monkeypatch.setattr(
        sys,
        'argv',
        [
            'github_ops.py',
            '--project-dir',
            worktree,
            'pr',
            'view',
        ],
    )

    github_ops.main()
    # Default cwd was installed before argparse ran.
    assert ci_base.get_default_cwd() == worktree
    # argv was stripped so argparse never saw --project-dir.
    assert '--project-dir' not in sys.argv


def test_main_project_dir_equals_form(tmp_path, monkeypatch, capsys):
    """The --project-dir=PATH form is also honoured by github_ops.main().

    Uses ``pr view`` (no subcommand-level --plan-id) with a mocked gh response
    so the test does not require a live GitHub token.

    Fix A (secondary guard): ``--plan-id`` must appear before the subcommand
    token. ``--project-dir=PATH`` (equals form) before the subcommand is the
    explicit-path escape hatch and must still work.
    """
    import sys

    import ci_base

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


def test_main_without_project_dir_leaves_cwd_untouched(tmp_path, monkeypatch):
    """Omitting --project-dir must not mutate the process-global default cwd.

    Uses ``pr view`` (no subcommand-level --plan-id) with a mocked gh response
    so the test does not require a live GitHub token.

    Fix A (secondary guard): ``--plan-id`` must appear before the subcommand
    token. This test verifies the sentinel cwd is not overwritten when neither
    ``--plan-id`` nor ``--project-dir`` is supplied at the router level.
    """
    import sys

    import ci_base

    sentinel = str(tmp_path / 'sentinel')
    monkeypatch.setattr(ci_base, '_DEFAULT_CWD', sentinel, raising=False)

    # Mock gh pr view to return a minimal success JSON so the handler
    # returns a result dict instead of raising on missing auth.
    monkeypatch.setattr(
        ci_base.subprocess,
        'run',
        lambda cmd, **kw: type('R', (), {'returncode': 0, 'stdout': '{}', 'stderr': ''})(),
    )

    monkeypatch.setattr(
        sys,
        'argv',
        [
            'github_ops.py',
            'pr',
            'view',
        ],
    )

    github_ops.main()
    # Unchanged sentinel — pre-parse did not clobber an existing default.
    assert ci_base.get_default_cwd() == sentinel


# =============================================================================
# format_checks_toon — Go zero-value timestamp regression
# =============================================================================
#
# Regression for the lesson-2026-04-19-14-007 bug: a SKIPPED check with
# `0001-01-01T00:00:00Z` timestamps used to leak ~63.9-billion-second
# `elapsed_sec` values into the TOON aggregate. Contract after the fix:
#
#   (a) aggregate elapsed_sec is bounded by a 24h ceiling
#   (b) SKIPPED row (with Go zero-value timestamps) has NO `elapsed_sec` key
#   (c) other (real-timestamped) rows have non-negative integer `elapsed_sec`


_GO_ZERO_GH = '0001-01-01T00:00:00Z'


def test_format_checks_toon_skips_go_zero_timestamps():
    """Three checks: SUCCESS+real, SKIPPED+zero-time, SUCCESS+real.

    The SKIPPED check must contribute neither a row-level `elapsed_sec`
    nor any positive value to the aggregate. Aggregate must stay ≤ 24h.
    """
    # `gh pr checks --json` shape: name, state, bucket, startedAt, completedAt, link, workflow
    checks = [
        {
            'name': 'unit-tests',
            'state': 'SUCCESS',
            'bucket': 'pass',
            'startedAt': '2025-01-15T11:55:00+00:00',
            'completedAt': '2025-01-15T11:58:00+00:00',  # 180s
            'link': 'https://example.test/1',
            'workflow': 'CI',
        },
        {
            'name': 'integration-tests-skipped',
            'state': 'SKIPPED',
            'bucket': 'skipping',
            # Go zero-value emitted by gh for never-started checks.
            'startedAt': _GO_ZERO_GH,
            'completedAt': _GO_ZERO_GH,
            'link': '',
            'workflow': 'CI',
        },
        {
            'name': 'lint',
            'state': 'SUCCESS',
            'bucket': 'pass',
            'startedAt': '2025-01-15T11:50:00+00:00',
            'completedAt': '2025-01-15T11:55:00+00:00',  # 300s
            'link': 'https://example.test/2',
            'workflow': 'CI',
        },
    ]

    rows, total_elapsed = github_ops.format_checks_toon(checks)

    # (a) Aggregate is bounded by 24h ceiling (not ~63.9 billion seconds).
    assert isinstance(total_elapsed, int)
    assert 0 <= total_elapsed <= 24 * 3600, (
        f'Aggregate elapsed_sec={total_elapsed} out of [0, 86400] — '
        'Go zero-value timestamp likely poisoned the aggregate'
    )

    # Three rows preserved, in the input order.
    assert len(rows) == 3
    skipped_row = next(r for r in rows if r['status'] == 'SKIPPED')
    real_rows = [r for r in rows if r['status'] == 'SUCCESS']

    # (b) SKIPPED row has NO elapsed_sec key — TOON treats absent as null.
    assert 'elapsed_sec' not in skipped_row, f'SKIPPED row must omit elapsed_sec; got {skipped_row!r}'

    # (c) Real-timestamped rows expose non-negative integer elapsed_sec.
    assert len(real_rows) == 2
    for r in real_rows:
        assert 'elapsed_sec' in r, f'Real row missing elapsed_sec: {r!r}'
        assert isinstance(r['elapsed_sec'], int)
        assert r['elapsed_sec'] >= 0, f'Real row elapsed_sec must be non-negative; got {r!r}'


def test_format_checks_toon_clamps_runaway_aggregate(monkeypatch, capsys):
    """Defense-in-depth: if compute_total_elapsed somehow returns a runaway
    value, format_checks_toon clamps to the caller-supplied ceiling and warns.

    We patch compute_total_elapsed to simulate the exact pre-fix bug
    (63.9 billion seconds) and verify the clamp engages.
    """
    import ci_base

    # Simulate the pre-fix bug: compute_total_elapsed returns runaway value.
    monkeypatch.setattr(github_ops, 'compute_total_elapsed', lambda values, now: 63_870_000_000)

    checks = [
        {
            'name': 'unit-tests',
            'state': 'SUCCESS',
            'bucket': 'pass',
            'startedAt': '2025-01-15T11:55:00+00:00',
            'completedAt': '2025-01-15T11:58:00+00:00',
            'link': 'https://example.test/1',
            'workflow': 'CI',
        },
    ]

    # ci_status path: duration_ceiling=0 → clamp substitutes 0.
    rows, total_elapsed = github_ops.format_checks_toon(checks, duration_ceiling=0)
    assert total_elapsed == 0, f'Expected runaway aggregate to clamp to 0, got {total_elapsed}'
    captured = capsys.readouterr()
    assert 'out of range' in captured.err, 'Expected stderr warning when clamp engages'

    # ci_wait path: duration_ceiling=42 → clamp substitutes 42.
    _, total_elapsed_wait = github_ops.format_checks_toon(checks, duration_ceiling=42)
    assert total_elapsed_wait == 42

    # Ensure ci_base import survives the patching (sanity).
    assert ci_base is not None


# =============================================================================
# Two-state ``--plan-id`` / ``--project-dir`` routing in github_ops.main()
# =============================================================================
#
# github_ops.main() consumes router-level --plan-id and --project-dir
# via ci_base.extract_routing_args BEFORE delegating to argparse. The
# resolved cwd is installed as the process-global default cwd via
# set_default_cwd, so every subsequent gh subprocess inherits it.


def test_main_routes_plan_id_via_extract_routing_args(monkeypatch):
    """github_ops.main() MUST consume router-level --plan-id and set the default cwd."""
    import resolve_project_dir as _routing
    from ci_base import get_default_cwd

    # Patch manage-status helper deterministically.
    monkeypatch.setattr(_routing, '_query_worktree_path', lambda _pid: (True, '/tmp/wt-resolved'))
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


def test_main_emits_mutually_exclusive_error_on_both_flags(monkeypatch, capsys):
    """github_ops.main() with both --plan-id and --project-dir → mutually_exclusive_args."""
    monkeypatch.setattr(
        'sys.argv',
        [
            'github_ops.py',
            '--plan-id',
            'task-routing-canonical',
            '--project-dir',
            '/tmp/explicit',
            'pr',
            'view',
        ],
    )
    import pytest as _pytest

    with _pytest.raises(SystemExit) as exc_info:
        github_ops.main()
    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert 'mutually_exclusive_args' in captured.out


# =============================================================================
# ci_status / ci_wait bucket aggregation — `skipping` is non-failing
# =============================================================================
#
# gh CLI reports `bucket: "skipping"` (not `"skipped"`) for skipped/neutral
# check conclusions. The aggregator must treat this as non-failing so a PR
# with all-pass-plus-skipped checks aggregates to overall=success /
# final_status=success rather than the (incorrect) pending / mixed.


def _mixed_pass_skipping_checks_json():
    return (
        '['
        '{"name":"a","state":"SUCCESS","bucket":"pass","startedAt":"","completedAt":"","link":"","workflow":"CI"},'
        '{"name":"b","state":"SKIPPED","bucket":"skipping","startedAt":"","completedAt":"","link":"","workflow":"CI"}'
        ']'
    )


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


# =============================================================================
# SKIPPED-as-terminal regression — deliverable 7
# =============================================================================
#
# The SKIPPED-classification root cause is the gh CLI's gerund bucket form
# (`bucket: "skipping"` rather than `"skipped"`). The fix is in
# _normalize_conclusion()/_CONCLUSION_NON_FAILING reading the state field
# rather than bucket. The regression tests below pin this contract at the
# cmd_ci_wait / cmd_ci_status entry points so a future refactor that
# silently reintroduces bucket-based classification fails loudly here.


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
        f'SKIPPED-only check set must classify as final_status=success; '
        f'got {result!r}'
    )
    assert result.get('failing_checks', []) == [], (
        f'SKIPPED-only check set must produce zero failing_checks; '
        f'got {result.get("failing_checks")!r}'
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


# =============================================================================
# reusable-workflow job-id log download
# =============================================================================

_REUSABLE_LINK = 'https://github.com/octo/repo/actions/runs/123/job/456'
_RUN_ONLY_LINK = 'https://github.com/octo/repo/actions/runs/123'


def test_extract_job_id_from_link_with_job_segment():
    assert github_ops._extract_job_id_from_link(_REUSABLE_LINK) == '456'


def test_extract_job_id_from_link_without_job_segment():
    # A run-only link (no nested /job/ segment) yields the empty string.
    assert github_ops._extract_job_id_from_link(_RUN_ONLY_LINK) == ''


def test_extract_job_id_from_link_none_and_empty():
    assert github_ops._extract_job_id_from_link(None) == ''
    assert github_ops._extract_job_id_from_link('') == ''


def test_build_failing_check_entry_populates_job_id():
    check = {
        'name': 'verify / verify',
        'state': 'FAILURE',
        'workflow': 'CI',
        'link': _REUSABLE_LINK,
        'startedAt': '',
        'completedAt': '',
    }
    entry = github_ops._build_failing_check_entry(check)
    assert entry['run_id'] == '123'
    assert entry['job_id'] == '456'


def test_build_failing_check_entry_empty_job_id_for_run_only_link():
    check = {
        'name': 'build',
        'state': 'FAILURE',
        'workflow': 'CI',
        'link': _RUN_ONLY_LINK,
        'startedAt': '',
        'completedAt': '',
    }
    entry = github_ops._build_failing_check_entry(check)
    assert entry['run_id'] == '123'
    assert entry['job_id'] == ''


def test_fetch_failed_run_log_forwards_job_flag_when_job_id_present(monkeypatch):
    captured: list[list[str]] = []

    def run_gh_stub(args, capture_json=False, timeout=60):
        captured.append(list(args))
        return 0, 'log-body', ''

    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)
    out = github_ops._fetch_failed_run_log('123', '456')

    assert out == 'log-body'
    assert len(captured) == 1
    argv = captured[0]
    assert argv[:4] == ['run', 'view', '123', '--log-failed']
    assert '--job' in argv
    assert argv[argv.index('--job') + 1] == '456'


def test_fetch_failed_run_log_omits_job_flag_when_job_id_absent(monkeypatch):
    captured: list[list[str]] = []

    def run_gh_stub(args, capture_json=False, timeout=60):
        captured.append(list(args))
        return 0, 'log-body', ''

    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)
    out = github_ops._fetch_failed_run_log('123')

    assert out == 'log-body'
    assert len(captured) == 1
    assert captured[0] == ['run', 'view', '123', '--log-failed']
    assert '--job' not in captured[0]


def test_fetch_failed_run_log_returns_none_on_nonzero_exit(monkeypatch):
    monkeypatch.setattr(github_ops, 'run_gh', lambda args, capture_json=False, timeout=60: (1, '', 'boom'))
    assert github_ops._fetch_failed_run_log('123', '456') is None


# =============================================================================
# cmd_ci_logs error-context window
# =============================================================================


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


# =============================================================================
# issue comment
# =============================================================================


def _prepare_issue_comment_body(tmp_path, monkeypatch, body_text='Milestone reached', plan_id='p'):
    """Seed PLAN_BASE_DIR with a prepared issue-comment body scratch file."""
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
    from ci_base import BODY_KIND_ISSUE_COMMENT, get_body_path

    path = get_body_path(plan_id, BODY_KIND_ISSUE_COMMENT)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body_text, encoding='utf-8')
    return plan_id


def test_cmd_issue_comment_posts_prepared_body(monkeypatch, tmp_path):
    """cmd_issue_comment posts the prepared body via `gh issue comment {n} --body`."""
    run_gh_stub, captured = _capture_run_gh()
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    plan_id = _prepare_issue_comment_body(tmp_path, monkeypatch, body_text='Outline ready')
    ns = argparse.Namespace(issue='42', plan_id=plan_id, slot=None)
    result = github_ops.cmd_issue_comment(ns)

    assert result['status'] == 'success', result
    assert result['operation'] == 'issue_comment'
    assert result['issue_number'] == '42'
    assert captured[-1] == ['issue', 'comment', '42', '--body', 'Outline ready']


def test_cmd_issue_comment_deletes_body_on_success(monkeypatch, tmp_path):
    """The prepared scratch body is removed only after a successful post."""
    from ci_base import BODY_KIND_ISSUE_COMMENT, get_body_path

    run_gh_stub, _ = _capture_run_gh()
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    plan_id = _prepare_issue_comment_body(tmp_path, monkeypatch)
    body_path = get_body_path(plan_id, BODY_KIND_ISSUE_COMMENT)
    assert body_path.exists()

    ns = argparse.Namespace(issue='42', plan_id=plan_id, slot=None)
    result = github_ops.cmd_issue_comment(ns)

    assert result['status'] == 'success', result
    assert not body_path.exists()


def test_cmd_issue_comment_body_not_prepared(monkeypatch, tmp_path):
    """A missing prepared body yields a body_not_prepared error, no gh call."""
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
    run_gh_stub, captured = _capture_run_gh()
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    ns = argparse.Namespace(issue='42', plan_id='p', slot=None)
    result = github_ops.cmd_issue_comment(ns)

    assert result['status'] == 'error', result
    assert result['operation'] == 'issue_comment'
    assert captured == []


def test_cmd_issue_comment_api_failure_keeps_body(monkeypatch, tmp_path):
    """A non-zero gh exit returns an error and leaves the scratch body in place."""
    from ci_base import BODY_KIND_ISSUE_COMMENT, get_body_path

    def failing_run_gh(args, capture_json=False, timeout=60):
        return 1, '', 'gh: not found'

    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', failing_run_gh)

    plan_id = _prepare_issue_comment_body(tmp_path, monkeypatch)
    body_path = get_body_path(plan_id, BODY_KIND_ISSUE_COMMENT)

    ns = argparse.Namespace(issue='42', plan_id=plan_id, slot=None)
    result = github_ops.cmd_issue_comment(ns)

    assert result['status'] == 'error', result
    assert body_path.exists()


def test_cmd_issue_comment_auth_failure(monkeypatch, tmp_path):
    """An auth failure short-circuits before any gh call."""
    run_gh_stub, captured = _capture_run_gh()
    monkeypatch.setattr(github_ops, 'check_auth', lambda: (False, 'not logged in'))
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    ns = argparse.Namespace(issue='42', plan_id='p', slot=None)
    result = github_ops.cmd_issue_comment(ns)

    assert result['status'] == 'error', result
    assert captured == []


def test_cmd_issue_prepare_comment_allocates_path(monkeypatch, tmp_path):
    """_cmd_issue_prepare_comment allocates an issue-comment scratch path."""
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
    plan_dir = tmp_path / 'plans' / 'p'
    plan_dir.mkdir(parents=True)
    (plan_dir / 'status.json').write_text('{}', encoding='utf-8')

    ns = argparse.Namespace(plan_id='p', slot=None)
    result = github_ops._cmd_issue_prepare_comment(ns)

    assert result['status'] == 'success', result
    assert result['kind'] == 'issue-comment'
    assert result['path'].endswith('issue-comment-default.md')


def test_cmd_issue_comment_normalizes_full_url(monkeypatch, tmp_path):
    """A full issue URL in --issue is normalized to the bare number for gh and the return."""
    run_gh_stub, captured = _capture_run_gh()
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    plan_id = _prepare_issue_comment_body(tmp_path, monkeypatch, body_text='Outline ready')
    ns = argparse.Namespace(issue='https://github.com/o/r/issues/42', plan_id=plan_id, slot=None)
    result = github_ops.cmd_issue_comment(ns)

    assert result['status'] == 'success', result
    assert result['issue_number'] == '42'
    assert captured[-1] == ['issue', 'comment', '42', '--body', 'Outline ready']

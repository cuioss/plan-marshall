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
_REUSABLE_LINK = 'https://github.com/octo/repo/actions/runs/123/job/456'
_RUN_ONLY_LINK = 'https://github.com/octo/repo/actions/runs/123'
def _prepare_issue_comment_body(tmp_path, monkeypatch, body_text='Milestone reached', plan_id='p'):
    """Seed PLAN_BASE_DIR with a prepared issue-comment body scratch file."""
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
    from ci_base import BODY_KIND_ISSUE_COMMENT, get_body_path

    path = get_body_path(plan_id, BODY_KIND_ISSUE_COMMENT)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body_text, encoding='utf-8')
    return plan_id


def test_fetch_pr_head_sha_returns_empty_on_gh_failure(monkeypatch):
    """A non-zero gh exit yields an empty string (no-abort contract)."""
    monkeypatch.setattr(github_ops, 'run_gh', lambda *_a, **_kw: (1, '', 'boom'))

    assert github_ops.fetch_pr_head_sha(42) == ''
def test_fetch_pr_head_sha_returns_empty_when_field_missing(monkeypatch):
    """A JSON payload without headRefOid yields an empty string."""
    monkeypatch.setattr(github_ops, 'run_gh', lambda *_a, **_kw: (0, '{"other": "x"}', ''))

    assert github_ops.fetch_pr_head_sha(42) == ''
def test_post_pr_comment_gh_failure_returns_error(monkeypatch):
    """A non-zero gh exit surfaces as an error envelope carrying stderr."""
    monkeypatch.setattr(github_ops, 'run_gh', lambda *_a, **_kw: (1, '', 'no such PR\n'))

    result = github_ops.post_pr_comment(42, '/review')

    assert result['status'] == 'error'
    assert result['operation'] == 'post_pr_comment'
    assert 'no such PR' in result['context']
def test_fetch_pr_reviews_with_commits_gh_failure(monkeypatch):
    """A non-zero gh api exit surfaces as an error envelope."""
    monkeypatch.setattr(github_ops, 'get_repo_info', lambda: ('octo', 'repo'))
    monkeypatch.setattr(github_ops, 'run_gh', lambda *_a, **_kw: (1, '', 'api error\n'))

    result = github_ops.fetch_pr_reviews_with_commits(42)

    assert result['status'] == 'error'
    assert 'Failed to fetch reviews' in result['error']
    assert 'api error' in result['context']
def test_fetch_pr_comments_data_preserves_existing_fields_across_all_kinds(monkeypatch):
    """Adding ``updated_at`` disturbs no existing key on any of the three kinds.

    ``kind`` / ``thread_id`` / ``created_at`` / ``resolved`` keep their meanings
    for inline thread comments, review bodies, and issue comments alike.
    """
    _patch_graphql(
        monkeypatch,
        {
            'reviewThreads': {
                'nodes': [
                    {
                        'id': 'PRRT_1',
                        'isResolved': False,
                        'path': 'src/a.py',
                        'line': 10,
                        'comments': {
                            'nodes': [
                                {
                                    'id': 'PRRC_1',
                                    'body': 'Guard the None case.',
                                    'author': {'login': 'coderabbitai'},
                                    'createdAt': '2026-07-26T08:00:00Z',
                                }
                            ]
                        },
                    }
                ]
            },
            'reviews': {
                'nodes': [
                    {
                        'id': 'PRR_1',
                        'state': 'COMMENTED',
                        'body': 'Overall Comments: extract the helper.',
                        'author': {'login': 'sourcery-ai'},
                        'submittedAt': '2026-07-26T08:30:00Z',
                    }
                ]
            },
            'comments': {
                'nodes': [
                    {
                        'id': 'IC_3',
                        'body': '## PR Reviewer Guide',
                        'author': {'login': 'cuioss-review-bot'},
                        'createdAt': '2026-07-26T09:27:15Z',
                        'updatedAt': '2026-07-26T09:27:15Z',
                    }
                ]
            },
        },
    )

    result = github_ops.fetch_pr_comments_data(103)

    assert result['total'] == 3

    inline = _comment_record(result, 'PRRC_1')
    assert inline['kind'] == 'inline'
    assert inline['thread_id'] == 'PRRT_1'
    assert inline['path'] == 'src/a.py'
    assert inline['line'] == 10
    assert inline['resolved'] is False
    assert inline['created_at'] == '2026-07-26T08:00:00Z'
    # Inline thread comments expose no edit timestamp in the query projection.
    assert inline['updated_at'] == ''

    review_body = _comment_record(result, 'PRR_1')
    assert review_body['kind'] == 'review_body'
    assert review_body['thread_id'] == ''
    assert review_body['created_at'] == '2026-07-26T08:30:00Z'
    assert review_body['updated_at'] == ''

    issue_comment = _comment_record(result, 'IC_3')
    assert issue_comment['kind'] == 'issue_comment'
    assert issue_comment['thread_id'] == ''
    assert issue_comment['updated_at'] == '2026-07-26T09:27:15Z'
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
def test_extract_job_id_from_link_with_job_segment():
    assert github_ops._extract_job_id_from_link(_REUSABLE_LINK) == '456'
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

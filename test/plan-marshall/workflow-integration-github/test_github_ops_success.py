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
def test_post_pr_comment_success(monkeypatch):
    """A successful gh pr comment returns a success envelope with the output."""
    captured: list[list[str]] = []

    def run_gh_stub(args, capture_json=False, timeout=60):
        captured.append(list(args))
        return 0, 'https://github.com/octo/repo/pull/42#issuecomment-1\n', ''

    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    result = github_ops.post_pr_comment(42, '/review')

    assert result['status'] == 'success'
    assert result['operation'] == 'post_pr_comment'
    assert result['pr_number'] == 42
    assert result['output'] == 'https://github.com/octo/repo/pull/42#issuecomment-1'
    assert captured == [['pr', 'comment', '42', '--body', '/review']]
def test_fetch_pr_reviews_with_commits_success(monkeypatch):
    """Reviews are projected to {user, state, submitted_at, commit_sha, body} rows."""
    captured: list[list[str]] = []

    def run_gh_stub(args, capture_json=False, timeout=60):
        captured.append(list(args))
        # --slurp wraps all pages into an outer array; simulate a single page.
        payload = (
            '[[{"user": {"login": "coderabbitai"}, "state": "COMMENTED", '
            '"submitted_at": "2026-01-01T00:05:00Z", "commit_id": "headsha", '
            '"body": "Actionable comments posted: 2"}]]'
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
            'body': 'Actionable comments posted: 2',
        }
    ]
    # REST /reviews endpoint is consulted with --paginate --slurp.
    assert captured == [['api', 'repos/octo/repo/pulls/42/reviews', '--paginate', '--slurp']]
def test_fetch_pr_reviews_with_commits_non_list_payload(monkeypatch):
    """A non-list reviews payload surfaces as an unexpected-shape error."""
    monkeypatch.setattr(github_ops, 'get_repo_info', lambda: ('octo', 'repo'))
    monkeypatch.setattr(github_ops, 'run_gh', lambda *_a, **_kw: (0, '{"message": "x"}', ''))

    result = github_ops.fetch_pr_reviews_with_commits(42)

    assert result['status'] == 'error'
    assert 'Unexpected reviews payload shape' in result['error']
def test_pr_wait_for_comments_returns_when_new_comment_arrives(monkeypatch):
    """Happy path: baseline=1, second poll sees count=2 → returns timed_out: false, new_count: 1."""
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)

    call_counts = {'fetch': 0}

    def fake_fetch(pr_number, unresolved_only=False):
        assert pr_number == 42
        # After the poll settles the handler makes ONE additional all-comments
        # fetch (unresolved_only defaults to False) to compute the per-bot
        # rate_limited_bots[] discriminator. Tolerate that extra call: return a
        # genuine (non rate-limit) bot review payload so the discriminator
        # resolves to an empty list without touching the poll-path baseline/new
        # counting.
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
    # the per-bot rate-limit discriminator is present and EMPTY for a genuine
    # review — an empty list is the positive "no registered bot is rate-limited"
    # signal, and the key is always present so consumers can rely on it
    assert 'rate_limited_bots' in result
    assert result['rate_limited_bots'] == []
def test_main_project_dir_sets_default_cwd(tmp_path, monkeypatch, capsys):
    """github_ops.main() strips --project-dir from argv and installs it as the
    process-global default cwd used by ci_base.run_cli.

    Uses ``pr view`` (no subcommand-level --plan-id) with a mocked gh response
    so the test does not require a live GitHub token.

    Fix A (secondary guard): ``--plan-id`` must appear before the subcommand
    token, not after. ``--project-dir`` may still appear before the subcommand
    as the explicit-path escape hatch.

    ``ci_base`` is the MODULE-LEVEL binding deliberately, not a function-local
    ``import ci_base``. A local import re-resolves the name through
    ``sys.modules`` at call time, so it would read whichever copy was published
    last, while ``github_ops`` calls the ``set_default_cwd`` it bound at ITS
    import time — the two can be different objects, and then the assertion reads
    a ``_DEFAULT_CWD`` nothing ever wrote to.
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
def test_extract_job_id_from_link_without_job_segment():
    # A run-only link (no nested /job/ segment) yields the empty string.
    assert github_ops._extract_job_id_from_link(_RUN_ONLY_LINK) == ''
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
def test_fetch_failed_run_log_returns_none_on_nonzero_exit(monkeypatch):
    monkeypatch.setattr(github_ops, 'run_gh', lambda args, capture_json=False, timeout=60: (1, '', 'boom'))
    assert github_ops._fetch_failed_run_log('123', '456') is None
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

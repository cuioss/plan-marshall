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


def test_create_pr_doc_creates_only_on_the_no_pr_cause():
    """`create-pr.md` gates creation on ``no_pr_found`` and STOPs on every other cause.

    The consumer here is a document an agent executes, so the doc text IS the
    behaviour. Before the discriminator existed this step read a bare
    ``status: error`` as "no PR exists" — the reading that opens the duplicate —
    so what is asserted is that each cause now routes explicitly, and that the
    three non-absence causes route to a STOP rather than to creation.
    """
    # Annotated because `conftest` is an untyped import for mypy, so every path
    # derived from it — and everything read through it — arrives as `Any`.
    lines: list[str] = _CREATE_PR_DOC.read_text(encoding='utf-8').splitlines()

    def _line_naming(needle: str) -> str:
        matches = [line for line in lines if needle in line]
        assert len(matches) == 1, (
            f'create-pr.md: expected exactly one line naming {needle!r}, found {len(matches)}. '
            'The cause routing cannot be read unambiguously.'
        )
        return matches[0]

    creating = _line_naming(ci_base.PR_VIEW_CAUSE_NO_PR)
    assert 'create' in creating.lower(), (
        f'create-pr.md does not route {ci_base.PR_VIEW_CAUSE_NO_PR} to creation: {creating}'
    )

    for cause in (
        ci_base.PR_VIEW_CAUSE_AUTH_FAILED,
        ci_base.PR_VIEW_CAUSE_PROVIDER_FAILED,
        ci_base.PR_VIEW_CAUSE_MALFORMED_RESPONSE,
    ):
        stopping = _line_naming(cause)
        assert 'STOP' in stopping, (
            f'create-pr.md does not STOP on {cause}: {stopping}. A non-absence cause that '
            'falls through to creation opens a duplicate PR.'
        )
        assert 'Do NOT create' in stopping or 'do NOT create' in stopping, (
            f'create-pr.md does not forbid creation on {cause}: {stopping}'
        )
def test_create_pr_doc_treats_an_absent_cause_as_unanswered():
    """A missing discriminator must not fall through to creation.

    The fail-closed default matters for exactly the window this change opens: a
    provider (or a cached older copy of one) that does not yet stamp the field.
    Reading its absence as "no PR exists" would reintroduce the defect on the
    one path the new branch does not otherwise cover.
    """
    text = _CREATE_PR_DOC.read_text(encoding='utf-8')

    assert '`error_cause` absent' in text, (
        'create-pr.md names no disposition for a MISSING error_cause, so a provider that '
        'does not stamp the field falls through to whichever branch happens to match.'
    )
    absent_line = next(line for line in text.splitlines() if '`error_cause` absent' in line)
    assert 'STOP' in absent_line, absent_line
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
def test_fetch_pr_reviews_with_commits_unparseable_json(monkeypatch):
    """Malformed gh api JSON surfaces as a parse error envelope."""
    monkeypatch.setattr(github_ops, 'get_repo_info', lambda: ('octo', 'repo'))
    monkeypatch.setattr(github_ops, 'run_gh', lambda *_a, **_kw: (0, 'not-json', ''))

    result = github_ops.fetch_pr_reviews_with_commits(42)

    assert result['status'] == 'error'
    assert 'Failed to parse' in result['error']
def test_fetch_pr_comments_data_updated_at_degrades_to_empty_string(monkeypatch):
    """A provider payload omitting ``updatedAt`` yields ``''``, never a missing key.

    The key must always be present so a consumer can read it unconditionally —
    mirroring the existing ``created_at`` handling.
    """
    _patch_graphql(
        monkeypatch,
        {
            'reviewThreads': {'nodes': []},
            'reviews': {'nodes': []},
            'comments': {
                'nodes': [
                    {
                        'id': 'IC_2',
                        'body': 'A comment with no edit timestamp.',
                        'author': {'login': 'alice'},
                        'createdAt': '2026-07-26T09:00:00Z',
                    }
                ]
            },
        },
    )

    result = github_ops.fetch_pr_comments_data(103)

    record = _comment_record(result, 'IC_2')
    assert record['updated_at'] == ''
    assert record['created_at'] == '2026-07-26T09:00:00Z'
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
def test_extract_job_id_from_link_none_and_empty():
    assert github_ops._extract_job_id_from_link(None) == ''
    assert github_ops._extract_job_id_from_link('') == ''
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

"""Tests for github.py script.

Tests command structure and argument parsing.
Note: Actual gh CLI operations require authentication and network.
These tests focus on the script interface, not live operations.
"""
import pytest

from conftest import get_script_path, run_script

SCRIPT_PATH = get_script_path('plan-marshall', 'workflow-integration-github', 'github_ops.py')
_HELP_SURFACE = [
    ((), ('pr', 'checks', 'issue'), ()),
    (
        ('pr',),
        (
            'create',
            'view',
            'reply',
            'resolve-thread',
            'thread-reply',
            'merge',
            'auto-merge',
            'close',
            'ready',
            'edit',
            'reviews',
            'list',
        ),
        (),
    ),
    (('issue',), ('create', 'view', 'close'), ()),
    (('checks',), ('status', 'wait', 'rerun', 'logs'), ()),
    # The plan-bound store is the ONE body source: a retired --body-file must be
    # gone from the advertised surface, since help text is what a caller reads to
    # decide how to supply a body. The legacy inline --body is asserted absent at
    # the parser level by test_ci_base.py.
    (('pr', 'create'), ('--title', '--plan-id'), ('--body-file',)),
    (('pr', 'view'), (), ()),
    (('pr', 'reply'), ('--pr-number', '--plan-id'), ('--body',)),
    (('pr', 'resolve-thread'), ('--thread-id',), ()),
    (('pr', 'thread-reply'), ('--pr-number', '--thread-id', '--plan-id'), ('--body',)),
    (('pr', 'merge'), ('--pr-number',), ()),
    (('pr', 'comments'), ('--pr-number',), ()),
    (('pr', 'auto-merge'), ('--pr-number',), ()),
    (('pr', 'close'), ('--pr-number',), ()),
    (('pr', 'ready'), ('--pr-number',), ()),
    (('pr', 'edit'), ('--pr-number', '--title'), ()),
    (('pr', 'list'), ('--head', '--state', '--limit'), ()),
    # --help renders the choices, so the advertised default doubles as the
    # state-choices assertion.
    (('pr', 'list'), ('open',), ()),
    (('checks', 'rerun'), ('--run-id',), ()),
    (('checks', 'logs'), ('--run-id',), ()),
    (('issue', 'close'), ('--issue',), ()),
]
_MISSING_REQUIRED = [
    (('pr', 'create'), 'title'),
    (('pr', 'reviews'), None),
    (('pr', 'reply'), None),
    (('pr', 'resolve-thread'), None),
    (('pr', 'thread-reply'), None),
    (('checks', 'wait'), None),
    (('checks', 'rerun'), None),
    (('issue', 'create'), None),
    ((), None),
]
_STRUCTURED_REFUSAL = [(('checks', 'status'),), (('pr', 'merge'),)]
def _install_github_ops_stubs(monkeypatch, pull_request_payload: dict):
    """Install standard auth/repo/graphql stubs on github_ops for pr_comments tests.

    Returns the imported github_ops module so callers can invoke handlers.
    """
    import github_ops

    def fake_check_auth():
        return True, ''

    def fake_get_repo_info():
        return 'octo', 'repo'

    def fake_run_graphql(query: str, variables: dict):
        return 0, {'repository': {'pullRequest': pull_request_payload}}, ''

    monkeypatch.setattr(github_ops, 'check_auth', fake_check_auth)
    monkeypatch.setattr(github_ops, 'get_repo_info', fake_get_repo_info)
    monkeypatch.setattr(github_ops, 'run_graphql', fake_run_graphql)
    return github_ops
def _inline_thread_payload(body: str = 'Inline feedback', resolved: bool = False) -> dict:
    return {
        'reviewThreads': {
            'nodes': [
                {
                    'id': 'PRRT_1',
                    'isResolved': resolved,
                    'path': 'src/File.py',
                    'line': 10,
                    'comments': {
                        'nodes': [
                            {
                                'id': 'IC_1',
                                'author': {'login': 'reviewer'},
                                'body': body,
                                'createdAt': '2026-04-14T00:00:00Z',
                            }
                        ]
                    },
                }
            ]
        },
        'reviews': {'nodes': []},
        'comments': {'nodes': []},
    }


@pytest.mark.parametrize('argv', [c[0] for c in _STRUCTURED_REFUSAL], ids=['checks-status', 'pr-merge'])
def test_either_or_flags_missing_emits_a_structured_error(argv):
    """Supplying neither ``--pr-number`` nor ``--head`` is reported, not ignored."""
    result = run_script(SCRIPT_PATH, *argv)
    combined = (result.stdout + result.stderr).lower()
    assert 'pr-number' in combined or 'head' in combined or 'auth' in combined, (
        f'Expected pr-number/head/auth in output, got: {combined}'
    )
def test_pr_submit_review_calls_submit_mutation(monkeypatch):
    """Regression: cmd_pr_submit_review must call submitPullRequestReview with
    exactly {reviewId, event} variables and return the state field."""
    import argparse

    import github_ops

    captured: dict = {}

    def fake_run_graphql(query: str, variables: dict):
        captured['query'] = query
        captured['variables'] = variables
        return (
            0,
            {'submitPullRequestReview': {'pullRequestReview': {'id': 'PRR_xyz', 'state': 'COMMENTED'}}},
            '',
        )

    def fake_run_gh(args, capture_json=False, timeout=60):
        if args[:1] == ['auth']:
            return 0, '', ''
        raise AssertionError(f'Unexpected gh call: {args}')

    monkeypatch.setattr(github_ops, 'run_graphql', fake_run_graphql)
    monkeypatch.setattr(github_ops, 'run_gh', fake_run_gh)

    ns = argparse.Namespace(review_id='PRR_xyz', event='COMMENT')
    result = github_ops.cmd_pr_submit_review(ns)

    assert result['status'] == 'success', f'Expected success, got: {result}'
    assert 'submitPullRequestReview' in captured['query']
    assert set(captured['variables'].keys()) == {'reviewId', 'event'}
    assert result['state'] == 'COMMENTED'
    assert result['review_id'] == 'PRR_xyz'
def test_pr_comments_no_body_truncation():
    """Regression: comment body must not be truncated (was [:100]).

    Tolerates the unified schema `kind` field on emitted comments by only
    asserting on the truncation anti-pattern, not on comment shape.
    """
    with open(SCRIPT_PATH) as f:
        source = f.read()
    # The TOON output section for pr_comments should normalize but not truncate
    assert "['body'].replace('\\t', ' ').replace('\\n', ' ')[:100]" not in source, (
        'Comment body is still truncated at 100 chars — remove [:100]'
    )
    # Sanity: unified schema discriminator is present in the source
    assert "'kind'" in source, 'Unified comment schema kind field missing from github_ops'
def test_pr_comments_includes_review_body(monkeypatch):
    """New: top-level review submission bodies are emitted as kind=review_body."""
    import argparse

    payload = {
        'reviewThreads': {'nodes': []},
        'reviews': {
            'nodes': [
                {
                    'id': 'PRR_1',
                    'author': {'login': 'senior'},
                    'body': 'Overall looks good, a few nits',
                    'submittedAt': '2026-04-14T01:00:00Z',
                }
            ]
        },
        'comments': {'nodes': []},
    }
    github_ops = _install_github_ops_stubs(monkeypatch, payload)

    ns = argparse.Namespace(pr_number=42, unresolved_only=False)
    result = github_ops.cmd_pr_comments(ns)

    assert result['status'] == 'success', result
    assert result['total'] == 1
    comment = result['comments'][0]
    assert comment['kind'] == 'review_body'
    assert comment['author'] == 'senior'
    assert comment['body'] == 'Overall looks good, a few nits'
    assert comment['path'] == ''
    assert comment['line'] == 0
def test_pr_comments_includes_issue_comment(monkeypatch):
    """New: PR issue-level comments are emitted as kind=issue_comment."""
    import argparse

    payload = {
        'reviewThreads': {'nodes': []},
        'reviews': {'nodes': []},
        'comments': {
            'nodes': [
                {
                    'id': 'IC_99',
                    'author': {'login': 'random-user'},
                    'body': 'CI is flaky, please rerun',
                    'createdAt': '2026-04-14T02:00:00Z',
                }
            ]
        },
    }
    github_ops = _install_github_ops_stubs(monkeypatch, payload)

    ns = argparse.Namespace(pr_number=42, unresolved_only=False)
    result = github_ops.cmd_pr_comments(ns)

    assert result['status'] == 'success', result
    assert result['total'] == 1
    comment = result['comments'][0]
    assert comment['kind'] == 'issue_comment'
    assert comment['author'] == 'random-user'
    assert comment['body'] == 'CI is flaky, please rerun'
    assert comment['path'] == ''
def test_pr_comments_skips_empty_review_body(monkeypatch):
    """New: reviews with empty body must not appear as review_body entries."""
    import argparse

    payload = {
        'reviewThreads': {'nodes': []},
        'reviews': {
            'nodes': [
                {
                    'id': 'PRR_empty',
                    'author': {'login': 'approver'},
                    'body': '',
                    'submittedAt': '2026-04-14T03:00:00Z',
                },
                {
                    'id': 'PRR_none',
                    'author': {'login': 'approver'},
                    'body': None,
                    'submittedAt': '2026-04-14T03:05:00Z',
                },
            ]
        },
        'comments': {'nodes': []},
    }
    github_ops = _install_github_ops_stubs(monkeypatch, payload)

    ns = argparse.Namespace(pr_number=42, unresolved_only=False)
    result = github_ops.cmd_pr_comments(ns)

    assert result['status'] == 'success', result
    assert result['total'] == 0
    assert result['comments'] == []
def test_pr_comments_kind_field_on_inline(monkeypatch):
    """New: inline review thread comments are emitted as kind=inline with path/line."""
    import argparse

    payload = _inline_thread_payload(body='fix this line')
    github_ops = _install_github_ops_stubs(monkeypatch, payload)

    ns = argparse.Namespace(pr_number=42, unresolved_only=False)
    result = github_ops.cmd_pr_comments(ns)

    assert result['status'] == 'success', result
    assert result['total'] == 1
    comment = result['comments'][0]
    assert comment['kind'] == 'inline'
    assert comment['path'] == 'src/File.py'
    assert comment['line'] == 10
    assert comment['thread_id'] == 'PRRT_1'
    assert comment['body'] == 'fix this line'

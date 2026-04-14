#!/usr/bin/env python3
"""Tests for github.py script.

Tests command structure and argument parsing.
Note: Actual gh CLI operations require authentication and network.
These tests focus on the script interface, not live operations.
"""

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import get_script_path, run_script

# Get script path
SCRIPT_PATH = get_script_path('plan-marshall', 'workflow-integration-github', 'github_ops.py')


def test_help_flag():
    """Test --help flag works."""
    result = run_script(SCRIPT_PATH, '--help')
    assert result.success, f'--help failed: {result.stderr}'
    assert 'pr' in result.stdout
    assert 'ci' in result.stdout
    assert 'issue' in result.stdout


def test_pr_subcommand_help():
    """Test pr subcommand help."""
    result = run_script(SCRIPT_PATH, 'pr', '--help')
    assert result.success, f'pr --help failed: {result.stderr}'
    assert 'create' in result.stdout
    assert 'view' in result.stdout
    assert 'reply' in result.stdout
    assert 'resolve-thread' in result.stdout
    assert 'thread-reply' in result.stdout
    assert 'merge' in result.stdout
    assert 'auto-merge' in result.stdout
    assert 'close' in result.stdout
    assert 'ready' in result.stdout
    assert 'edit' in result.stdout
    assert 'reviews' in result.stdout
    assert 'list' in result.stdout


def test_issue_subcommand_help():
    """Test issue subcommand help."""
    result = run_script(SCRIPT_PATH, 'issue', '--help')
    assert result.success, f'issue --help failed: {result.stderr}'
    assert 'create' in result.stdout
    assert 'view' in result.stdout
    assert 'close' in result.stdout


def test_ci_subcommand_help():
    """Test ci subcommand help."""
    result = run_script(SCRIPT_PATH, 'ci', '--help')
    assert result.success, f'ci --help failed: {result.stderr}'
    assert 'status' in result.stdout
    assert 'wait' in result.stdout
    assert 'rerun' in result.stdout
    assert 'logs' in result.stdout


def test_pr_create_help():
    """Test pr create help shows required arguments."""
    result = run_script(SCRIPT_PATH, 'pr', 'create', '--help')
    assert result.success, f'pr create --help failed: {result.stderr}'
    assert '--title' in result.stdout
    assert '--body' in result.stdout


def test_pr_create_missing_required():
    """Test pr create fails without required arguments."""
    result = run_script(SCRIPT_PATH, 'pr', 'create')
    assert not result.success, 'Expected failure without --title'
    assert 'title' in result.stderr.lower() or 'required' in result.stderr.lower()


def test_pr_reviews_missing_required():
    """Test pr reviews fails without pr-number."""
    result = run_script(SCRIPT_PATH, 'pr', 'reviews')
    assert not result.success, 'Expected failure without --pr-number'


def test_ci_status_missing_required():
    """Test ci status fails without pr-number."""
    result = run_script(SCRIPT_PATH, 'ci', 'status')
    assert not result.success, 'Expected failure without --pr-number'


def test_ci_wait_missing_required():
    """Test ci wait fails without pr-number."""
    result = run_script(SCRIPT_PATH, 'ci', 'wait')
    assert not result.success, 'Expected failure without --pr-number'


def test_issue_create_missing_required():
    """Test issue create fails without required arguments."""
    result = run_script(SCRIPT_PATH, 'issue', 'create')
    assert not result.success, 'Expected failure without --title'


def test_pr_view_help():
    """Test pr view help works."""
    result = run_script(SCRIPT_PATH, 'pr', 'view', '--help')
    assert result.success, f'pr view --help failed: {result.stderr}'


def test_pr_reply_help():
    """Test pr reply help shows required arguments."""
    result = run_script(SCRIPT_PATH, 'pr', 'reply', '--help')
    assert result.success, f'pr reply --help failed: {result.stderr}'
    assert '--pr-number' in result.stdout
    assert '--body' in result.stdout


def test_pr_reply_missing_required():
    """Test pr reply fails without required arguments."""
    result = run_script(SCRIPT_PATH, 'pr', 'reply')
    assert not result.success, 'Expected failure without --pr-number'


def test_pr_resolve_thread_help():
    """Test pr resolve-thread help shows required arguments."""
    result = run_script(SCRIPT_PATH, 'pr', 'resolve-thread', '--help')
    assert result.success, f'pr resolve-thread --help failed: {result.stderr}'
    assert '--thread-id' in result.stdout


def test_pr_resolve_thread_missing_required():
    """Test pr resolve-thread fails without required arguments."""
    result = run_script(SCRIPT_PATH, 'pr', 'resolve-thread')
    assert not result.success, 'Expected failure without --thread-id'


def test_pr_thread_reply_help():
    """Test pr thread-reply help shows required arguments."""
    result = run_script(SCRIPT_PATH, 'pr', 'thread-reply', '--help')
    assert result.success, f'pr thread-reply --help failed: {result.stderr}'
    assert '--pr-number' in result.stdout
    assert '--thread-id' in result.stdout
    assert '--body' in result.stdout


def test_pr_thread_reply_missing_required():
    """Test pr thread-reply fails without required arguments."""
    result = run_script(SCRIPT_PATH, 'pr', 'thread-reply')
    assert not result.success, 'Expected failure without --pr-number'


def test_pr_merge_help():
    """Test pr merge help shows required arguments."""
    result = run_script(SCRIPT_PATH, 'pr', 'merge', '--help')
    assert result.success, f'pr merge --help failed: {result.stderr}'
    assert '--pr-number' in result.stdout


def test_pr_merge_missing_required():
    """Test pr merge fails without required arguments."""
    result = run_script(SCRIPT_PATH, 'pr', 'merge')
    assert not result.success, 'Expected failure without --pr-number'


def test_pr_comments_help():
    """Test pr comments help shows required arguments."""
    result = run_script(SCRIPT_PATH, 'pr', 'comments', '--help')
    assert result.success, f'pr comments --help failed: {result.stderr}'
    assert '--pr-number' in result.stdout


def test_pr_auto_merge_help():
    """Test pr auto-merge help shows required arguments."""
    result = run_script(SCRIPT_PATH, 'pr', 'auto-merge', '--help')
    assert result.success, f'pr auto-merge --help failed: {result.stderr}'
    assert '--pr-number' in result.stdout


def test_pr_close_help():
    """Test pr close help shows required arguments."""
    result = run_script(SCRIPT_PATH, 'pr', 'close', '--help')
    assert result.success, f'pr close --help failed: {result.stderr}'
    assert '--pr-number' in result.stdout


def test_pr_ready_help():
    """Test pr ready help shows required arguments."""
    result = run_script(SCRIPT_PATH, 'pr', 'ready', '--help')
    assert result.success, f'pr ready --help failed: {result.stderr}'
    assert '--pr-number' in result.stdout


def test_pr_edit_help():
    """Test pr edit help shows arguments."""
    result = run_script(SCRIPT_PATH, 'pr', 'edit', '--help')
    assert result.success, f'pr edit --help failed: {result.stderr}'
    assert '--pr-number' in result.stdout
    assert '--title' in result.stdout


def test_ci_rerun_help():
    """Test ci rerun help shows required arguments."""
    result = run_script(SCRIPT_PATH, 'ci', 'rerun', '--help')
    assert result.success, f'ci rerun --help failed: {result.stderr}'
    assert '--run-id' in result.stdout


def test_ci_rerun_missing_required():
    """Test ci rerun fails without required arguments."""
    result = run_script(SCRIPT_PATH, 'ci', 'rerun')
    assert not result.success, 'Expected failure without --run-id'


def test_ci_logs_help():
    """Test ci logs help shows required arguments."""
    result = run_script(SCRIPT_PATH, 'ci', 'logs', '--help')
    assert result.success, f'ci logs --help failed: {result.stderr}'
    assert '--run-id' in result.stdout


def test_issue_close_help():
    """Test issue close help shows required arguments."""
    result = run_script(SCRIPT_PATH, 'issue', 'close', '--help')
    assert result.success, f'issue close --help failed: {result.stderr}'
    assert '--issue' in result.stdout


def test_pr_list_help():
    """Test pr list help shows optional arguments."""
    result = run_script(SCRIPT_PATH, 'pr', 'list', '--help')
    assert result.success, f'pr list --help failed: {result.stderr}'
    assert '--head' in result.stdout
    assert '--state' in result.stdout


def test_pr_list_state_choices():
    """Test pr list accepts valid state choices."""
    # --help already validates choices are defined; verify the default
    result = run_script(SCRIPT_PATH, 'pr', 'list', '--help')
    assert result.success
    assert 'open' in result.stdout


def test_no_subcommand():
    """Test that script requires a subcommand."""
    result = run_script(SCRIPT_PATH)
    assert not result.success, 'Expected failure without subcommand'


def test_pr_thread_reply_uses_thread_reply_mutation(monkeypatch):
    """Regression: cmd_pr_thread_reply must use addPullRequestReviewThreadReply
    with exactly {threadId, body} variables, and MUST NOT shell out to gh pr view
    for a PR id. The follow-up PENDING-review check must see zero stuck reviews."""
    import argparse

    import github_ops  # type: ignore[import-not-found]

    graphql_calls: list[tuple[str, dict]] = []
    gh_calls: list[list[str]] = []

    def fake_run_graphql(query: str, variables: dict):
        graphql_calls.append((query, variables))
        if 'addPullRequestReviewThreadReply' in query:
            return 0, {'addPullRequestReviewThreadReply': {'comment': {'id': 'C_1', 'databaseId': 1}}}, ''
        if 'viewer' in query:
            return 0, {'viewer': {'login': 'octocat'}}, ''
        if 'reviews(states: [PENDING]' in query:
            return 0, {'repository': {'pullRequest': {'reviews': {'nodes': []}}}}, ''
        raise AssertionError(f'Unexpected GraphQL query: {query}')

    def fake_run_gh(args, capture_json=False, timeout=60):
        gh_calls.append(list(args))
        if args[:1] == ['auth']:
            return 0, '', ''
        if args[:2] == ['repo', 'view']:
            return 0, '{"owner": {"login": "octo"}, "name": "repo"}', ''
        raise AssertionError(f'Unexpected gh call: {args}')

    monkeypatch.setattr(github_ops, 'run_graphql', fake_run_graphql)
    monkeypatch.setattr(github_ops, 'run_gh', fake_run_gh)

    ns = argparse.Namespace(pr_number=42, thread_id='PRRT_abc', body='Fixed it')
    result = github_ops.cmd_pr_thread_reply(ns)

    assert result['status'] == 'success', f'Expected success, got: {result}'
    # Assert mutation and variables
    reply_call = next((q, v) for q, v in graphql_calls if 'addPullRequestReviewThreadReply' in q)
    assert 'addPullRequestReviewThreadReply' in reply_call[0]
    assert set(reply_call[1].keys()) == {'threadId', 'body'}, (
        f'Unexpected variables: {reply_call[1].keys()}'
    )
    assert 'prId' not in reply_call[1]
    assert 'inReplyTo' not in reply_call[1]
    # Assert NO gh pr view call
    assert not any(c[:2] == ['pr', 'view'] for c in gh_calls), (
        f'Unexpected gh pr view call: {gh_calls}'
    )


def test_pr_thread_reply_fails_when_pending_review_remains(monkeypatch):
    """Regression: if a PENDING review owned by the viewer remains after the
    mutation, the handler must return status: error naming the stuck review id,
    NOT status: success."""
    import argparse

    import github_ops  # type: ignore[import-not-found]

    def fake_run_graphql(query: str, variables: dict):
        if 'addPullRequestReviewThreadReply' in query:
            return 0, {'addPullRequestReviewThreadReply': {'comment': {'id': 'C_1', 'databaseId': 1}}}, ''
        if 'viewer' in query:
            return 0, {'viewer': {'login': 'octocat'}}, ''
        if 'reviews(states: [PENDING]' in query:
            return (
                0,
                {
                    'repository': {
                        'pullRequest': {
                            'reviews': {
                                'nodes': [
                                    {'id': 'PRR_stuck', 'author': {'login': 'octocat'}},
                                ]
                            }
                        }
                    }
                },
                '',
            )
        raise AssertionError(f'Unexpected GraphQL query: {query}')

    def fake_run_gh(args, capture_json=False, timeout=60):
        if args[:1] == ['auth']:
            return 0, '', ''
        if args[:2] == ['repo', 'view']:
            return 0, '{"owner": {"login": "octo"}, "name": "repo"}', ''
        raise AssertionError(f'Unexpected gh call: {args}')

    monkeypatch.setattr(github_ops, 'run_graphql', fake_run_graphql)
    monkeypatch.setattr(github_ops, 'run_gh', fake_run_gh)

    ns = argparse.Namespace(pr_number=42, thread_id='PRRT_abc', body='Fixed it')
    result = github_ops.cmd_pr_thread_reply(ns)

    assert result['status'] == 'error', f'Expected error, got: {result}'
    assert 'PRR_stuck' in (result.get('error', '') + result.get('context', '')), (
        f'Stuck review id missing from error payload: {result}'
    )


def test_pr_submit_review_calls_submit_mutation(monkeypatch):
    """Regression: cmd_pr_submit_review must call submitPullRequestReview with
    exactly {reviewId, event} variables and return the state field."""
    import argparse

    import github_ops  # type: ignore[import-not-found]

    captured: dict = {}

    def fake_run_graphql(query: str, variables: dict):
        captured['query'] = query
        captured['variables'] = variables
        return (
            0,
            {
                'submitPullRequestReview': {
                    'pullRequestReview': {'id': 'PRR_xyz', 'state': 'COMMENTED'}
                }
            },
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


def _install_github_ops_stubs(monkeypatch, pull_request_payload: dict):
    """Install standard auth/repo/graphql stubs on github_ops for pr_comments tests.

    Returns the imported github_ops module so callers can invoke handlers.
    """
    import github_ops  # type: ignore[import-not-found]

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

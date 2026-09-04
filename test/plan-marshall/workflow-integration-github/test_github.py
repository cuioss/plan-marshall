#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for github.py script.

Tests command structure and argument parsing.
Note: Actual gh CLI operations require authentication and network.
These tests focus on the script interface, not live operations.
"""

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
import pytest

from conftest import get_script_path, run_script

# Get script path
SCRIPT_PATH = get_script_path('plan-marshall', 'workflow-integration-github', 'github_ops.py')


# ---------------------------------------------------------------------------
# CLI plumbing. The subprocess layer proves the entry point wires up — argv
# parses, the declared flags are advertised, the declared exit code is used.
# The handlers' behaviour is asserted in-process elsewhere in this suite.
# ---------------------------------------------------------------------------

# (argv, substrings the help text MUST advertise, substrings it must NOT)
_HELP_SURFACE = [
    ((), ('pr', 'checks', 'issue'), ()),
    (
        ('pr',),
        (
            'create', 'view', 'reply', 'resolve-thread', 'thread-reply', 'merge',
            'auto-merge', 'close', 'ready', 'edit', 'reviews', 'list',
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
    (('pr', 'list'), ('--head', '--state'), ()),
    # --help renders the choices, so the advertised default doubles as the
    # state-choices assertion.
    (('pr', 'list'), ('open',), ()),
    (('checks', 'rerun'), ('--run-id',), ()),
    (('checks', 'logs'), ('--run-id',), ()),
    (('issue', 'close'), ('--issue',), ()),
]


@pytest.mark.parametrize(
    ('argv', 'advertised', 'absent'),
    _HELP_SURFACE,
    ids=[
        'root', 'pr', 'issue', 'checks', 'pr-create', 'pr-view', 'pr-reply',
        'pr-resolve-thread', 'pr-thread-reply', 'pr-merge', 'pr-comments',
        'pr-auto-merge', 'pr-close', 'pr-ready', 'pr-edit', 'pr-list',
        'pr-list-state-default', 'checks-rerun', 'checks-logs', 'issue-close',
    ],
)
def test_help_advertises_the_declared_surface(argv, advertised, absent):
    """``--help`` exits zero and advertises exactly the flags a caller drives it with."""
    result = run_script(SCRIPT_PATH, *argv, '--help')
    assert result.success, f'{" ".join(argv)} --help failed: {result.stderr}'
    for token in advertised:
        assert token in result.stdout, f'{token!r} missing from {" ".join(argv)} --help'
    for token in absent:
        assert token not in result.stdout, f'{token!r} still advertised by {" ".join(argv)} --help'


# (argv, a substring the diagnostic must name — None when only the exit code is pinned)
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


@pytest.mark.parametrize(
    ('argv', 'names'),
    _MISSING_REQUIRED,
    ids=[
        'pr-create', 'pr-reviews', 'pr-reply', 'pr-resolve-thread',
        'pr-thread-reply', 'checks-wait', 'checks-rerun', 'issue-create',
        'no-subcommand',
    ],
)
def test_missing_required_argument_is_a_nonzero_exit(argv, names):
    """A subcommand invoked without its required flags exits non-zero."""
    result = run_script(SCRIPT_PATH, *argv)
    assert not result.success, f'{" ".join(argv) or "<no subcommand>"} unexpectedly succeeded'
    if names:
        combined = result.stderr.lower()
        assert names in combined or 'required' in combined, combined


# Verbs whose required flags are mutually-exclusive alternatives: the parser
# accepts the bare call and the HANDLER rejects it, so the diagnostic — not the
# exit code — is the contract. Auth runs first, so its error is also admissible.
_STRUCTURED_REFUSAL = [(('checks', 'status'),), (('pr', 'merge'),)]


@pytest.mark.parametrize('argv', [c[0] for c in _STRUCTURED_REFUSAL], ids=['checks-status', 'pr-merge'])
def test_either_or_flags_missing_emits_a_structured_error(argv):
    """Supplying neither ``--pr-number`` nor ``--head`` is reported, not ignored."""
    result = run_script(SCRIPT_PATH, *argv)
    combined = (result.stdout + result.stderr).lower()
    assert 'pr-number' in combined or 'head' in combined or 'auth' in combined, (
        f'Expected pr-number/head/auth in output, got: {combined}'
    )


def test_pr_create_handler_has_a_single_body_source():
    """Provider parity: one store call, and no surviving ``body_file`` path.

    The symmetric residue this deliverable owes. Both providers' ``cmd_pr_create``
    handlers must resolve the body through the SAME store call and retain no
    ``body_file`` branch — the sibling assertion lives in the GitLab suite and is
    deliberately identical, because the two handlers are kept in lock-step so the
    CI abstraction presents one contract per verb.

    Asserted structurally over the handler's AST rather than behaviourally: a
    behavioural test can only observe the branch that RUNS, so a dormant
    ``body_file`` branch reachable from a direct-Namespace caller would stay
    invisible to it.
    """
    _assert_single_body_source('plan-marshall', 'workflow-integration-github', '_github_pr.py')


def _assert_single_body_source(bundle: str, skill: str, script: str) -> None:
    """Assert ``cmd_pr_create`` in the named script has exactly one body source."""
    import ast  # local import: only this structural check needs it

    from conftest import get_scripts_dir  # local import: only this structural check needs it

    source = (get_scripts_dir(bundle, skill) / script).read_text(encoding='utf-8')
    handler = next(
        (
            node
            for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.FunctionDef) and node.name == 'cmd_pr_create'
        ),
        None,
    )
    assert handler is not None, f'cmd_pr_create not found in {script}'

    called = {
        node.func.id
        for node in ast.walk(handler)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert 'read_and_consume_body' in called, (
        f'{script}::cmd_pr_create no longer resolves the body through the store'
    )

    # ``body_file`` can survive as an attribute/local name, as an attribute
    # access (``args.body_file`` — the dormant ``if args.body_file:`` guard
    # this assertion exists to catch, still reachable from a direct-Namespace
    # caller), OR as the string key of a ``getattr(args, "body_file", None)``
    # read — check all three spellings.
    identifiers = {node.id for node in ast.walk(handler) if isinstance(node, ast.Name)}
    identifiers |= {node.attr for node in ast.walk(handler) if isinstance(node, ast.Attribute)}
    literals = {
        node.value
        for node in ast.walk(handler)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    assert 'body_file' not in identifiers, (
        f'{script}::cmd_pr_create retains a body_file local or attribute access'
    )
    assert 'body_file' not in literals, f'{script}::cmd_pr_create retains a body_file lookup'


def _prepare_thread_reply_body(tmp_path, monkeypatch, body_text='Fixed it', plan_id='p'):
    """Seed PLAN_BASE_DIR with a prepared thread-reply body scratch file."""
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
    from ci_base import (
        BODY_KIND_PR_THREAD_REPLY,
        get_body_path,
    )

    path = get_body_path(plan_id, BODY_KIND_PR_THREAD_REPLY)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body_text, encoding='utf-8')
    return plan_id


def test_pr_thread_reply_uses_thread_reply_mutation(monkeypatch, tmp_path):
    """Regression: cmd_pr_thread_reply must use addPullRequestReviewThreadReply
    with exactly {threadId, body} variables, and MUST NOT shell out to gh pr view
    for a PR id. The follow-up PENDING-review check must see zero stuck reviews."""
    import argparse

    import github_ops

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

    plan_id = _prepare_thread_reply_body(tmp_path, monkeypatch)
    ns = argparse.Namespace(pr_number=42, thread_id='PRRT_abc', plan_id=plan_id, slot=None)
    result = github_ops.cmd_pr_thread_reply(ns)

    assert result['status'] == 'success', f'Expected success, got: {result}'
    # mutation and variables
    reply_call = next((q, v) for q, v in graphql_calls if 'addPullRequestReviewThreadReply' in q)
    assert 'addPullRequestReviewThreadReply' in reply_call[0]
    assert set(reply_call[1].keys()) == {'threadId', 'body'}, f'Unexpected variables: {reply_call[1].keys()}'
    assert 'prId' not in reply_call[1]
    assert 'inReplyTo' not in reply_call[1]
    # NO gh pr view call
    assert not any(c[:2] == ['pr', 'view'] for c in gh_calls), f'Unexpected gh pr view call: {gh_calls}'


def test_pr_thread_reply_fails_when_pending_review_remains(monkeypatch, tmp_path):
    """Regression: if a PENDING review owned by the viewer remains after the
    mutation, the handler must return status: error naming the stuck review id,
    NOT status: success."""
    import argparse

    import github_ops

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

    plan_id = _prepare_thread_reply_body(tmp_path, monkeypatch)
    ns = argparse.Namespace(pr_number=42, thread_id='PRRT_abc', plan_id=plan_id, slot=None)
    result = github_ops.cmd_pr_thread_reply(ns)

    assert result['status'] == 'error', f'Expected error, got: {result}'
    assert 'PRR_stuck' in (result.get('error', '') + result.get('context', '')), (
        f'Stuck review id missing from error payload: {result}'
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

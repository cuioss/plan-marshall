# SPDX-License-Identifier: FSL-1.1-ALv2
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
            'comments',
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


@pytest.mark.parametrize(
    ('argv', 'advertised', 'absent'),
    _HELP_SURFACE,
    ids=[
        'root',
        'pr',
        'issue',
        'checks',
        'pr-create',
        'pr-view',
        'pr-reply',
        'pr-resolve-thread',
        'pr-thread-reply',
        'pr-merge',
        'pr-comments',
        'pr-auto-merge',
        'pr-close',
        'pr-ready',
        'pr-edit',
        'pr-list',
        'pr-list-state-default',
        'checks-rerun',
        'checks-logs',
        'issue-close',
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

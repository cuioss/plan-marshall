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


def _run_pr_list(monkeypatch, rows, **overrides):
    """Drive ``cmd_pr_list`` over a stubbed ``gh``; return ``(result, captured_argv)``.

    Stubs only the subprocess primitive ``run_gh``, so the argument vector the
    handler CONSTRUCTED is captured verbatim rather than re-derived from a copy of
    the builder. ``overrides`` are applied to the Namespace, so a caller can omit
    ``limit`` entirely to exercise the default.
    """
    import argparse
    import json

    import github_ops

    captured: list[list[str]] = []

    def fake_run_gh(args, capture_json=False, timeout=60):
        captured.append(list(args))
        return 0, json.dumps(rows), ''

    monkeypatch.setattr(github_ops, 'check_auth', lambda: (True, ''))
    monkeypatch.setattr(github_ops, 'run_gh', fake_run_gh)

    fields = {'state': 'open', 'head': None}
    fields.update(overrides)
    result = github_ops.cmd_pr_list(argparse.Namespace(**fields))
    assert len(captured) == 1, f'expected exactly one gh invocation, got {captured}'
    return result, captured[0]


def _pr_row(number: int) -> dict:
    return {
        'number': number,
        'url': f'https://github.com/octo/repo/pull/{number}',
        'title': f'Change {number}',
        'state': 'OPEN',
        'headRefName': f'feature/{number}',
        'baseRefName': 'main',
    }


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


def test_pr_list_reports_a_short_listing_as_untruncated(monkeypatch):
    """A row count BELOW the requested bound is a complete enumeration.

    ``total`` is only quotable as a population on this arm, which is why the
    bound it was read at travels beside it even when nothing was cut off.
    """
    result, _argv = _run_pr_list(monkeypatch, [_pr_row(1), _pr_row(2)], limit=5)

    assert result['status'] == 'success', result
    assert result['total'] == 2
    assert result['limit'] == 5
    assert result['truncated'] is False


def test_pr_list_reports_a_limit_filling_listing_as_truncated(monkeypatch):
    """A row count that REACHES the requested bound is reported as unenumerable.

    A listing exactly filling its bound and one cut short by it are
    indistinguishable from outside, so both are ``truncated: true``: ``total`` is a
    floor rather than a population, and a caller must widen the bound instead of
    quoting the number it has.
    """
    result, _argv = _run_pr_list(monkeypatch, [_pr_row(1), _pr_row(2), _pr_row(3)], limit=3)

    assert result['status'] == 'success', result
    assert result['total'] == 3
    assert result['limit'] == 3
    assert result['truncated'] is True


def test_pr_list_passes_the_requested_limit_into_the_gh_invocation(monkeypatch):
    """``--limit`` reaches the constructed ``gh pr list`` argument vector.

    Asserted on the vector the handler handed to the subprocess primitive: a bound
    the handler reports but never sends leaves the listing capped at the provider's
    own invisible page size while the payload claims it was read at the requested
    figure.
    """
    _result, argv = _run_pr_list(monkeypatch, [_pr_row(1)], limit=50)

    assert argv[:2] == ['pr', 'list'], argv
    assert '--limit' in argv, argv
    assert argv[argv.index('--limit') + 1] == '50', argv


def test_pr_list_sends_the_documented_default_when_no_limit_is_supplied(monkeypatch):
    """A caller supplying no bound still gets an EXPLICIT one of ``100``.

    The Namespace carries no ``limit`` at all here, which is the direct-caller
    shape that bypasses the argparse default. An unbounded invocation would fall
    back to the provider's own page size — the silent cap the flag exists to
    remove — so the default is sent rather than omitted.
    """
    result, argv = _run_pr_list(monkeypatch, [_pr_row(1)])

    assert '--limit' in argv, argv
    assert argv[argv.index('--limit') + 1] == '100', argv
    assert result['limit'] == 100


def test_pr_list_limit_is_accepted_at_verb_scope():
    """``--limit`` parses where it is declared — on the ``pr list`` subparser.

    The positive arm of the scoping pair. ``--help`` is reached only after the
    preceding ``--limit 50`` has parsed, so a zero exit is evidence the subparser
    accepts the flag rather than evidence the help path skipped it.
    """
    result = run_script(SCRIPT_PATH, 'pr', 'list', '--limit', '50', '--help')

    assert result.success, f'pr list rejected a verb-scoped --limit: {result.stderr}'


def test_pr_list_limit_is_refused_at_router_scope():
    """The ROOT parser refuses ``--limit``, so it cannot drift up to the router.

    The negative control of the pair above, and the reason the flag is declared on
    the subparser at all: a router-scoped flag is consumed before the provider
    parser is built, so it would never reach the ``gh`` invocation — the listing
    would stay page-bounded while the call still looked accepted. The refusal is
    what makes that move fail loudly instead of silently.
    """
    result = run_script(SCRIPT_PATH, '--limit', '50', 'pr', 'list')

    assert not result.success, 'root parser accepted a router-placed --limit'
    assert 'error:' in result.stderr, result.stderr

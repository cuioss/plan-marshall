# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for github.py script.

Tests command structure and argument parsing.
Note: Actual gh CLI operations require authentication and network.
These tests focus on the script interface, not live operations.
"""

import pytest

from conftest import get_script_path, run_script

SCRIPT_PATH = get_script_path('plan-marshall', 'workflow-integration-github', 'github_ops.py')


def _derive_verb_roster() -> dict[tuple[str, ...], tuple[str, ...]]:
    """Every group path in the live parser, mapped to the verbs registered under it.

    Derived by walking the parser ``github_ops`` builds, never transcribed: a
    hand-listed roster silently omits a verb added later, so its ``--help`` and
    its presence in the parent's help would go unexercised on a green run.
    """
    import argparse

    import github_ops

    roster: dict[tuple[str, ...], tuple[str, ...]] = {}

    def _walk(parser: argparse.ArgumentParser, path: tuple[str, ...]) -> None:
        for action in parser._actions:
            if isinstance(action, argparse._SubParsersAction):
                roster[path] = tuple(action.choices)
                for verb, child in action.choices.items():
                    _walk(child, (*path, verb))

    _walk(github_ops.build_github_parser(), ())
    return roster


_VERB_ROSTER = _derive_verb_roster()
#: Every node of the parser tree — each group and each leaf verb — as an argv path.
_EVERY_PARSER_PATH = sorted(
    {(), *_VERB_ROSTER, *((*group, verb) for group, verbs in _VERB_ROSTER.items() for verb in verbs)}
)

_HELP_SURFACE = [
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


def test_the_derived_verb_roster_is_not_vacuous():
    """The parser walk found the group tree, so the parametrization below sweeps something."""
    assert {'pr', 'checks', 'issue'} <= set(_VERB_ROSTER.get((), ())), _VERB_ROSTER.get(())
    assert len(_EVERY_PARSER_PATH) > len(_VERB_ROSTER), 'the walk found groups but no leaf verb'


@pytest.mark.parametrize('argv', _EVERY_PARSER_PATH, ids=lambda argv: '-'.join(argv) or 'root')
def test_help_exits_zero_and_advertises_every_registered_verb(argv):
    """``--help`` works at every parser node, and each group's help names every verb under it."""
    result = run_script(SCRIPT_PATH, *argv, '--help')
    assert result.success, f'{" ".join(argv)} --help failed: {result.stderr}'
    for verb in _VERB_ROSTER.get(argv, ()):
        assert verb in result.stdout, f'{verb!r} missing from {" ".join(argv)} --help'


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

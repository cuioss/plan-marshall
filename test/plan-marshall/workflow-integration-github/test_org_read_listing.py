#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the GitHub population listings ``org list-repos`` and ``repo label list``.

Both walk a GraphQL connection to exhaustion and answer with the evidence of
their own completeness: ``status: success`` only when the rows read ARE the
population (the connection is exhausted AND the row count equals the provider's
``totalCount``), ``status: incomplete`` with ``complete: false`` and an
``incomplete_reason`` when the rows demonstrably are not, and ``status: error``
when a page could not be read at all — in which case no rows are returned.

The GitHub primitives (``check_auth``, ``run_graphql``, ``get_repo_info``) are
patched on ``_github_org.github_ops`` — the module object the handlers reach
through at call time — so no network call occurs.
"""

import argparse

import pytest

from conftest import load_script_module

_github_org = load_script_module('plan-marshall', 'workflow-integration-github', '_github_org.py', '_github_org')

_ORG = 'cuioss'


def _repo_node(name: str, *, archived: bool = False) -> dict:
    """Build one ``repositories`` connection node."""
    return {
        'name': name,
        'nameWithOwner': f'{_ORG}/{name}',
        'isArchived': archived,
        'isFork': False,
        'visibility': 'PUBLIC',
        'defaultBranchRef': {'name': 'main'},
    }


def _page(nodes: list, *, total: int, next_cursor: str | None) -> dict:
    """Build one connection page."""
    return {
        'totalCount': total,
        'pageInfo': {'hasNextPage': next_cursor is not None, 'endCursor': next_cursor},
        'nodes': nodes,
    }


def _serve_pages(monkeypatch, pages: list, *, wrap) -> list:
    """Stub ``run_graphql`` to serve ``pages`` in order, keyed by the ``after`` cursor.

    Returns the list of variable dicts each call received. A page entry that is a
    ``str`` is served as a provider failure carrying that error text.
    """
    monkeypatch.setattr(_github_org.github_ops, 'check_auth', lambda: (True, ''))
    calls: list = []

    def _fake_graphql(query, variables):
        calls.append(dict(variables))
        page = pages[len(calls) - 1]
        if isinstance(page, str):
            return 1, None, page
        return 0, wrap(page), ''

    monkeypatch.setattr(_github_org.github_ops, 'run_graphql', _fake_graphql)
    return calls


def _wrap_repos(page):
    return {'repositoryOwner': {'repositories': page}}


def _wrap_labels(page):
    return {'repository': {'labels': page}}


def _list_repos(org: str = _ORG) -> dict:
    result: dict = _github_org.cmd_org_list_repos(argparse.Namespace(org=org))
    return result


def test_list_repos_walks_every_page_and_reports_a_complete_population(monkeypatch):
    """Two pages are walked via the ``after`` cursor; rows == totalCount → success."""
    calls = _serve_pages(
        monkeypatch,
        [
            _page([_repo_node('a'), _repo_node('b', archived=True)], total=3, next_cursor='C1'),
            _page([_repo_node('c')], total=3, next_cursor=None),
        ],
        wrap=_wrap_repos,
    )

    result = _list_repos()

    assert result['status'] == 'success'
    assert result['complete'] is True
    assert result['incomplete_reason'] == ''
    assert result['count'] == result['total_count'] == 3
    assert result['archived_count'] == 1
    assert result['pages_read'] == 2
    assert [repo['full_name'] for repo in result['repos']] == ['cuioss/a', 'cuioss/b', 'cuioss/c']
    assert result['repos'][1]['archived'] is True
    assert result['repos'][0]['visibility'] == 'public'
    assert 'after' not in calls[0]
    assert calls[1]['after'] == 'C1'


def test_list_repos_row_count_below_total_is_incomplete_not_a_shorter_success(monkeypatch):
    """An exhausted connection whose rows disagree with totalCount is ``incomplete``."""
    _serve_pages(monkeypatch, [_page([_repo_node('a')], total=2, next_cursor=None)], wrap=_wrap_repos)

    result = _list_repos()

    assert result['status'] == 'incomplete'
    assert result['complete'] is False
    assert result['incomplete_reason'] == 'count_mismatch'
    assert result['count'] == 1
    assert result['total_count'] == 2


def test_list_repos_page_bound_is_reported_as_incomplete(monkeypatch):
    """A walk that reaches the page bound with pages remaining is ``page_bound_reached``."""
    monkeypatch.setattr(_github_org, '_MAX_PAGES', 2)
    _serve_pages(
        monkeypatch,
        [
            _page([_repo_node('a')], total=3, next_cursor='C1'),
            _page([_repo_node('b')], total=3, next_cursor='C2'),
        ],
        wrap=_wrap_repos,
    )

    result = _list_repos()

    assert result['status'] == 'incomplete'
    assert result['incomplete_reason'] == 'page_bound_reached'
    assert result['pages_read'] == 2


def test_list_repos_failed_later_page_is_an_error_carrying_no_rows(monkeypatch):
    """A page that cannot be read fails the whole listing — no partial rows are returned."""
    _serve_pages(
        monkeypatch,
        [_page([_repo_node('a')], total=2, next_cursor='C1'), 'HTTP 502'],
        wrap=_wrap_repos,
    )

    result = _list_repos()

    assert result['status'] == 'error'
    assert result['reason'] == 'page_read_failed'
    assert result['pages_read'] == 1
    assert 'repos' not in result


def test_list_repos_unknown_owner_is_an_error_not_an_empty_population(monkeypatch):
    """A null ``repositoryOwner`` is ``owner_not_found`` — never a zero-row success."""
    monkeypatch.setattr(_github_org.github_ops, 'check_auth', lambda: (True, ''))
    monkeypatch.setattr(_github_org.github_ops, 'run_graphql', lambda q, v: (0, {'repositoryOwner': None}, ''))

    result = _list_repos()

    assert result['status'] == 'error'
    assert result['reason'] == 'owner_not_found'


def test_list_repos_cursor_missing_while_more_pages_is_malformed(monkeypatch):
    """``hasNextPage`` without an ``endCursor`` cannot be walked and is reported, not truncated."""
    _serve_pages(
        monkeypatch,
        [{'totalCount': 2, 'pageInfo': {'hasNextPage': True, 'endCursor': None}, 'nodes': [_repo_node('a')]}],
        wrap=_wrap_repos,
    )

    result = _list_repos()

    assert result['status'] == 'error'
    assert result['reason'] == 'malformed_response'


@pytest.mark.parametrize('org', ['', 'bad org', '-leading-hyphen', 'a' * 40])
def test_list_repos_rejects_an_invalid_login_before_any_call(monkeypatch, org):
    """A malformed login is refused before auth or any provider call."""
    monkeypatch.setattr(_github_org.github_ops, 'check_auth', lambda: pytest.fail('must not be called'))

    result = _list_repos(org)

    assert result['status'] == 'error'
    assert 'invalid organization login' in result['error']


def test_list_repos_unauthenticated_fails_loud(monkeypatch):
    """An unauthenticated gh surfaces as an error, never an empty population."""
    monkeypatch.setattr(_github_org.github_ops, 'check_auth', lambda: (False, 'Not authenticated'))

    result = _list_repos()

    assert result['status'] == 'error'
    assert result['error'] == 'Not authenticated'


def test_label_list_reads_every_label_of_the_named_repository(monkeypatch):
    """``--repo OWNER/NAME`` is split into the query variables; a full walk is success."""
    calls = _serve_pages(
        monkeypatch,
        [_page([{'name': 'bug', 'color': 'd73a4a', 'description': None}], total=1, next_cursor=None)],
        wrap=_wrap_labels,
    )

    result = _github_org.cmd_repo_label_list(argparse.Namespace(repo='cuioss/plan-marshall'))

    assert result['status'] == 'success'
    assert result['repo'] == 'cuioss/plan-marshall'
    assert result['labels'] == [{'name': 'bug', 'color': 'd73a4a', 'description': ''}]
    assert calls[0]['owner'] == 'cuioss'
    assert calls[0]['name'] == 'plan-marshall'


def test_label_list_defaults_to_the_routed_repository(monkeypatch):
    """Without ``--repo`` the repository of the routed working tree is used."""
    calls = _serve_pages(monkeypatch, [_page([], total=0, next_cursor=None)], wrap=_wrap_labels)
    monkeypatch.setattr(_github_org.github_ops, 'get_repo_info', lambda: ('cuioss', 'here'))

    result = _github_org.cmd_repo_label_list(argparse.Namespace(repo=None))

    assert result['status'] == 'success'
    assert result['repo'] == 'cuioss/here'
    assert result['count'] == 0
    assert calls[0]['name'] == 'here'


def test_label_list_unresolvable_routed_repository_is_an_error(monkeypatch):
    """No ``--repo`` and no resolvable routed repository is an error, not an empty list."""
    monkeypatch.setattr(_github_org.github_ops, 'check_auth', lambda: (True, ''))
    monkeypatch.setattr(_github_org.github_ops, 'get_repo_info', lambda: (None, None))

    result = _github_org.cmd_repo_label_list(argparse.Namespace(repo=None))

    assert result['status'] == 'error'


@pytest.mark.parametrize('repo', ['plan-marshall', 'a/b/c', '/x', 'owner/'])
def test_label_list_rejects_a_malformed_repository(repo):
    """A ``--repo`` that is not ``OWNER/NAME`` is refused."""
    result = _github_org.cmd_repo_label_list(argparse.Namespace(repo=repo))

    assert result['status'] == 'error'
    assert 'OWNER/NAME' in result['error']

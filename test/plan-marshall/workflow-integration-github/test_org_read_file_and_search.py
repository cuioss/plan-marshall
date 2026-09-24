#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the GitHub reads ``repo file read`` and ``org search-code``.

``repo file read`` answers "what is at this path?" in three shapes that never
collapse into one another: ``state: found`` (an empty file included),
``state: not_found`` (a successful, distinct answer), and ``status: error``
(the question was not answered). A GitHub 404 is ambiguous between a missing
path and an unreadable repository, so a 404 is attributed to the PATH only
after the repository itself is read.

``org search-code`` reports GitHub's own completeness signal and index scope
beside its matches, so a zero always states the population it was computed over.

``check_auth`` / ``run_gh`` are patched on ``_github_org.github_ops`` — the
module object the handlers reach through at call time.
"""

import argparse
import base64
import json

import pytest

from conftest import load_script_module

_github_org = load_script_module('plan-marshall', 'workflow-integration-github', '_github_org.py', '_github_org')

_REPO = 'cuioss/example'
_PATH = '.github/project.yml'
_NOT_FOUND_STDERR = 'gh: Not Found (HTTP 404)'


def _serve_gh(monkeypatch, responses: list) -> list:
    """Stub auth + ``run_gh`` to return ``responses`` in order; return the captured argv list."""
    monkeypatch.setattr(_github_org.github_ops, 'check_auth', lambda: (True, ''))
    calls: list = []

    def _fake_run_gh(gh_args):
        calls.append(list(gh_args))
        return responses[len(calls) - 1]

    monkeypatch.setattr(_github_org.github_ops, 'run_gh', _fake_run_gh)
    return calls


def _contents(text: str) -> str:
    """Build a contents-API file response carrying ``text``."""
    encoded = base64.b64encode(text.encode('utf-8')).decode('ascii')
    return json.dumps({'type': 'file', 'encoding': 'base64', 'content': encoded, 'sha': 'abc', 'size': len(text)})


def _read(ref: str | None = None, path: str = _PATH) -> dict:
    result: dict = _github_org.cmd_repo_file_read(argparse.Namespace(repo=_REPO, path=path, ref=ref))
    return result


def test_file_read_found_carries_content_at_the_default_branch(monkeypatch):
    """A readable file is ``found`` with its content; no ``--ref`` reads the default branch."""
    calls = _serve_gh(monkeypatch, [(0, _contents('name: example\n'), '')])

    result = _read()

    assert result['status'] == 'success'
    assert result['state'] == 'found'
    assert result['content'] == 'name: example\n'
    assert result['ref_source'] == 'default_branch'
    assert calls == [['api', f'repos/{_REPO}/contents/{_PATH}']]


def test_file_read_explicit_ref_is_url_encoded_into_the_query(monkeypatch):
    """``--ref`` is passed as an encoded ``?ref=`` so a slash in a branch name survives."""
    calls = _serve_gh(monkeypatch, [(0, _contents('x'), '')])

    result = _read(ref='feature/a b')

    assert result['ref_source'] == 'explicit'
    assert calls[0][1].endswith('?ref=feature%2Fa%20b')


def test_file_read_empty_file_is_found_not_absent(monkeypatch):
    """An empty file is ``found`` with empty content — never confused with ``not_found``."""
    _serve_gh(monkeypatch, [(0, _contents(''), '')])

    result = _read()

    assert result['state'] == 'found'
    assert result['content'] == ''
    assert result['size'] == 0


def test_file_read_absent_path_in_a_readable_repository_is_not_found(monkeypatch):
    """A 404 on the path plus a readable repository is ``not_found`` / ``path_absent``."""
    calls = _serve_gh(monkeypatch, [(1, '', _NOT_FOUND_STDERR), (0, '{}', '')])

    result = _read()

    assert result['status'] == 'success'
    assert result['state'] == 'not_found'
    assert result['not_found_reason'] == 'path_absent'
    assert 'content' not in result
    assert calls[1] == ['api', f'repos/{_REPO}']


def test_file_read_unreadable_repository_is_an_error_not_an_absent_file(monkeypatch):
    """A 404 whose repository probe also fails is an error — nobody looked at the tree."""
    _serve_gh(monkeypatch, [(1, '', _NOT_FOUND_STDERR), (1, '', _NOT_FOUND_STDERR)])

    result = _read()

    assert result['status'] == 'error'
    assert result['error'].startswith('repository_not_accessible')
    assert 'state' not in result


def test_file_read_unknown_ref_is_an_error(monkeypatch):
    """GitHub's "No commit found for the ref" 404 is ``ref_not_found``, not an absent file."""
    calls = _serve_gh(monkeypatch, [(1, '', 'gh: No commit found for the ref nope (HTTP 404)')])

    result = _read(ref='nope')

    assert result['status'] == 'error'
    assert result['error'].startswith('ref_not_found')
    assert len(calls) == 1


def test_file_read_empty_repository_is_not_found(monkeypatch):
    """A 409 "repository is empty" is ``not_found`` / ``repository_empty``."""
    _serve_gh(monkeypatch, [(1, '', 'gh: This repository is empty. (HTTP 409)')])

    result = _read()

    assert result['state'] == 'not_found'
    assert result['not_found_reason'] == 'repository_empty'


@pytest.mark.parametrize(
    ('stdout', 'fragment'),
    [
        (json.dumps([{'name': 'a'}]), 'not_a_file'),
        (json.dumps({'type': 'submodule'}), 'not_a_file'),
        (json.dumps({'type': 'file', 'encoding': 'none', 'content': '', 'size': 5_000_000}), 'content_unavailable'),
        (
            json.dumps({'type': 'file', 'encoding': 'base64', 'content': base64.b64encode(b'\xff').decode()}),
            'undecodable',
        ),
        ('not json', 'malformed'),
    ],
    ids=['directory', 'submodule', 'too-large', 'not-utf8', 'malformed-json'],
)
def test_file_read_unanswerable_content_is_an_error(monkeypatch, stdout, fragment):
    """Every response that yields no text file is an error — never an empty ``found``."""
    _serve_gh(monkeypatch, [(0, stdout, '')])

    result = _read()

    assert result['status'] == 'error'
    assert fragment in result['error']


def test_file_read_other_provider_failure_is_an_error(monkeypatch):
    """A non-404 / non-409 failure is ``read_failed``."""
    _serve_gh(monkeypatch, [(1, '', 'gh: Server Error (HTTP 500)')])

    result = _read()

    assert result['status'] == 'error'
    assert result['error'] == 'read_failed'


def _search_page(total: int, count: int, *, incomplete: bool = False, start: int = 0) -> tuple:
    items = [
        {'path': f'f{start + i}.yml', 'sha': 's', 'repository': {'full_name': f'cuioss/r{i % 2}'}} for i in range(count)
    ]
    return 0, json.dumps({'total_count': total, 'incomplete_results': incomplete, 'items': items}), ''


def _search(query: str = 'review-charter') -> dict:
    result: dict = _github_org.cmd_org_search_code(argparse.Namespace(org='cuioss', query=query))
    return result


def test_search_code_quotes_the_literal_and_scopes_it_to_the_org(monkeypatch):
    """The literal is searched as one exact phrase inside ``org:``; a single page completes."""
    calls = _serve_gh(monkeypatch, [_search_page(total=3, count=3)])

    result = _search()

    assert result['status'] == 'success'
    assert result['complete'] is True
    assert result['count'] == result['total_count'] == 3
    assert result['repository_count'] == 2
    assert result['scope'] == 'default_branch_index'
    assert 'q="review-charter" org:cuioss' in calls[0]


def test_search_code_zero_hits_is_a_complete_answer_with_its_evidence(monkeypatch):
    """A zero carries ``incomplete_results: false`` and ``complete: true`` — not a bare negative."""
    _serve_gh(monkeypatch, [_search_page(total=0, count=0)])

    result = _search()

    assert result['status'] == 'success'
    assert result['count'] == 0
    assert result['incomplete_results'] is False
    assert result['complete'] is True


def test_search_code_provider_incomplete_flag_makes_the_answer_incomplete(monkeypatch):
    """GitHub's ``incomplete_results: true`` is surfaced as ``status: incomplete``."""
    _serve_gh(monkeypatch, [_search_page(total=2, count=2, incomplete=True)])

    result = _search()

    assert result['status'] == 'incomplete'
    assert result['incomplete_reason'] == 'provider_incomplete_results'


def test_search_code_result_cap_is_reported(monkeypatch):
    """More hits than the page cap can serve is ``result_cap_reached``."""
    monkeypatch.setattr(_github_org, '_CODE_SEARCH_MAX_PAGES', 2)
    monkeypatch.setattr(_github_org, '_CODE_SEARCH_PAGE_SIZE', 2)
    calls = _serve_gh(monkeypatch, [_search_page(total=5, count=2), _search_page(total=5, count=2, start=2)])

    result = _search()

    assert result['status'] == 'incomplete'
    assert result['incomplete_reason'] == 'result_cap_reached'
    assert result['count'] == 4
    assert len(calls) == 2


def test_search_code_failed_page_is_an_error(monkeypatch):
    """A page that cannot be read (e.g. the search rate limit) fails the search."""
    _serve_gh(monkeypatch, [(1, '', 'gh: API rate limit exceeded (HTTP 403)')])

    result = _search()

    assert result['status'] == 'error'
    assert result['pages_read'] == 0


@pytest.mark.parametrize('query', ['', '   ', 'has "quote"'])
def test_search_code_refuses_an_unsearchable_literal(query):
    """An empty literal or one carrying a double quote is refused before any call."""
    result = _search(query)

    assert result['status'] == 'error'


@pytest.mark.parametrize(
    'spec',
    ['cuioss/example\n', 'cuioss/.', 'cuioss/..', 'cuioss\n/example', 'cuioss/', '/example'],
    ids=['trailing-newline', 'dot', 'dot-dot', 'newline-in-owner', 'empty-name', 'empty-owner'],
)
def test_repo_spec_rejects_malformed_and_traversing_names(spec):
    """A spec is matched whole: a trailing newline or a dot-only name never splits."""
    assert _github_org._split_repo(spec) is None


@pytest.mark.parametrize('path', ['../../o2/r2/contents/x.yml', 'a/../b', './x', 'a/./b'])
def test_file_read_refuses_dot_segments_before_any_call(monkeypatch, path):
    """A '.' or '..' path segment is refused before auth or any provider call."""
    calls = _serve_gh(monkeypatch, [])

    result = _read(path=path)

    assert result['status'] == 'error'
    assert calls == []


def test_repo_spec_accepts_a_dotted_name():
    """A name that merely contains dots is a legitimate repository name."""
    assert _github_org._split_repo('cuioss/.github') == ('cuioss', '.github')


@pytest.mark.parametrize('org', ['cuioss\n', 'cuioss org', '-cuioss', ''])
def test_org_login_is_matched_whole(org):
    """An org login with a trailing newline or illegal character is refused before any call."""
    assert _github_org._LOGIN_RE.fullmatch(org) is None

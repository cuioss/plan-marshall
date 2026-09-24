#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""GitHub organization-wide and foreign-repository READ handlers.

Holds the four read-only handlers that reach beyond the checkout the router is
bound to:

- ``cmd_org_list_repos`` — ``org list-repos``: every repository of an
  organization, all pages, archived flag included.
- ``cmd_org_search_code`` — ``org search-code``: every indexed file of an
  organization containing a literal, with GitHub's own completeness signal.
- ``cmd_repo_file_read`` — ``repo file read``: one file at a repository's
  default branch or at an explicit ref.
- ``cmd_repo_label_list`` — ``repo label list``: every label of a repository.

**Every answer carries the evidence of its own completeness.** The three
population verbs return ``status: success`` only when the rows read ARE the
population; a listing that is demonstrably partial returns
``status: incomplete`` with ``complete: false`` and an ``incomplete_reason``
(see ``ci_base.STATUS_INCOMPLETE``), so a caller branching on ``status`` alone
can never read a shorter list as the whole one. A page that could not be read at
all is ``status: error`` — nothing is returned as though it were a population.
``repo file read`` separates the absent path (``state: not_found``) from an
empty file and from a read failure.

Every network primitive (``run_gh``, ``run_graphql``, ``check_auth``,
``get_repo_info``) lives in the entry module ``github_ops`` and is reached here
via ATTRIBUTE access on the imported module at call time, so a test's
``monkeypatch.setattr(github_ops, '<name>', ...)`` reaches these handlers
unchanged — never ``from github_ops import <name>``, which would copy the
binding and defeat the patch. See the adjudication comment above the bottom
imports in ``github_ops.py`` for the other half of that contract.
"""

import argparse
import base64
import binascii
import json
import re
from collections.abc import Callable
from typing import Any
from urllib.parse import quote

import github_ops
from ci_base import (
    FILE_READ_FOUND,
    FILE_READ_NOT_FOUND,
    STATUS_INCOMPLETE,
    BlockScalar,
    make_error,
)

#: Rows requested per GraphQL page (the GitHub maximum).
_PAGE_SIZE = 100

#: Upper bound on pages one GraphQL listing walks (100 x 100 = 10,000 rows). A
#: listing that reaches it without exhausting the connection reports
#: ``incomplete_reason: page_bound_reached`` rather than a truncated success.
_MAX_PAGES = 100

#: GitHub's REST code search serves at most 1,000 results — 10 pages of 100.
_CODE_SEARCH_PAGE_SIZE = 100
_CODE_SEARCH_MAX_PAGES = 10

#: What the GitHub code-search index covers. Published on every search result
#: so a zero states the population it was computed over: the index holds each
#: repository's DEFAULT BRANCH only, and GitHub documents further exclusions
#: (most forks, files over its size limit).
_CODE_SEARCH_SCOPE = 'default_branch_index'

_LOGIN_RE = re.compile(r'^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$')
_REPO_RE = re.compile(r'^([A-Za-z0-9](?:[A-Za-z0-9-]{0,38}))/([A-Za-z0-9._-]{1,100})$')

_ORG_REPOS_QUERY = """
query($login: String!, $first: Int!, $after: String) {
  repositoryOwner(login: $login) {
    repositories(first: $first, after: $after, orderBy: {field: NAME, direction: ASC}) {
      totalCount
      pageInfo { hasNextPage endCursor }
      nodes { name nameWithOwner isArchived isFork visibility defaultBranchRef { name } }
    }
  }
}
"""

_REPO_LABELS_QUERY = """
query($owner: String!, $name: String!, $first: Int!, $after: String) {
  repository(owner: $owner, name: $name) {
    labels(first: $first, after: $after, orderBy: {field: NAME, direction: ASC}) {
      totalCount
      pageInfo { hasNextPage endCursor }
      nodes { name color description }
    }
  }
}
"""


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _split_repo(spec: str | None) -> tuple[str, str] | None:
    """Return ``(owner, name)`` for an ``OWNER/NAME`` spec, or ``None`` when malformed."""
    match = _REPO_RE.match(spec or '')
    if not match:
        return None
    return match.group(1), match.group(2)


def _paginate_connection(
    query: str,
    variables: dict[str, Any],
    connection_of: Callable[[dict], dict | None],
) -> dict[str, Any]:
    """Walk every page of one GraphQL connection.

    Args:
        query: GraphQL query declaring ``$first: Int!`` and ``$after: String``.
        variables: The query's other variables.
        connection_of: Extracts the connection object from a page's ``data``;
            returns ``None`` when the owning node is absent.

    Returns:
        ``{'ok': True, 'nodes', 'total_count', 'pages_read', 'bound_reached'}``
        when the walk ended, or ``{'ok': False, 'reason', 'detail',
        'pages_read'}`` when a page could not be read. ``reason`` is
        ``owner_not_found`` when the owning node is absent, ``page_read_failed``
        when the provider call failed, and ``malformed_response`` when a page
        lacked the connection fields.
    """
    nodes: list[dict] = []
    after: str | None = None
    for page in range(1, _MAX_PAGES + 1):
        page_vars: dict[str, Any] = {**variables, 'first': _PAGE_SIZE}
        if after is not None:
            page_vars['after'] = after
        returncode, data, error = github_ops.run_graphql(query, page_vars)
        if returncode != 0 or data is None:
            return {'ok': False, 'reason': 'page_read_failed', 'detail': error, 'pages_read': page - 1}
        connection = connection_of(data)
        if connection is None:
            return {'ok': False, 'reason': 'owner_not_found', 'detail': '', 'pages_read': page - 1}
        try:
            total_count = int(connection['totalCount'])
            nodes.extend(node for node in (connection.get('nodes') or []) if isinstance(node, dict))
            page_info = connection['pageInfo']
            has_next = bool(page_info['hasNextPage'])
            after = page_info.get('endCursor')
        except (KeyError, TypeError, ValueError) as exc:
            return {'ok': False, 'reason': 'malformed_response', 'detail': str(exc), 'pages_read': page - 1}
        if not has_next:
            return {
                'ok': True,
                'nodes': nodes,
                'total_count': total_count,
                'pages_read': page,
                'bound_reached': False,
            }
        if not after:
            return {
                'ok': False,
                'reason': 'malformed_response',
                'detail': 'hasNextPage is true but endCursor is empty',
                'pages_read': page,
            }
    return {
        'ok': True,
        'nodes': nodes,
        'total_count': total_count,
        'pages_read': _MAX_PAGES,
        'bound_reached': True,
    }


def _completeness(row_count: int, total_count: int, bound_reached: bool) -> str:
    """Return ``''`` when a walked listing is the whole population, else the reason it is not."""
    if bound_reached:
        return 'page_bound_reached'
    if row_count != total_count:
        return 'count_mismatch'
    return ''


def _population_envelope(operation: str, incomplete_reason: str, fields: dict[str, Any]) -> dict[str, Any]:
    """Build the success / incomplete envelope shared by the population verbs."""
    envelope: dict[str, Any] = {
        'status': STATUS_INCOMPLETE if incomplete_reason else 'success',
        'operation': operation,
        'provider': 'github',
        'complete': not incomplete_reason,
        'incomplete_reason': incomplete_reason,
    }
    envelope.update(fields)
    return envelope


def _walk_failure(operation: str, walk: dict[str, Any], subject: str) -> dict[str, Any]:
    """Build the error envelope for a GraphQL walk that could not be completed."""
    result = make_error(operation, f'{walk["reason"]}: {subject}', str(walk.get('detail') or ''))
    result['reason'] = walk['reason']
    result['pages_read'] = walk['pages_read']
    return result


# ---------------------------------------------------------------------------
# org list-repos
# ---------------------------------------------------------------------------


def cmd_org_list_repos(args: argparse.Namespace) -> dict:
    """Handle ``org list-repos`` — every repository of an organization, all pages."""
    operation = 'org_list_repos'
    if not _LOGIN_RE.match(args.org or ''):
        return make_error(operation, f'invalid organization login: {args.org!r}')

    is_auth, err = github_ops.check_auth()
    if not is_auth:
        return make_error(operation, err)

    walk = _paginate_connection(
        _ORG_REPOS_QUERY,
        {'login': args.org},
        lambda data: (data.get('repositoryOwner') or {}).get('repositories'),
    )
    if not walk['ok']:
        return _walk_failure(operation, walk, f'org={args.org}')

    repos = [
        {
            'name': node.get('name', ''),
            'full_name': node.get('nameWithOwner', ''),
            'archived': bool(node.get('isArchived')),
            'fork': bool(node.get('isFork')),
            'visibility': str(node.get('visibility') or '').lower(),
            'default_branch': (node.get('defaultBranchRef') or {}).get('name', ''),
        }
        for node in walk['nodes']
    ]
    reason = _completeness(len(repos), walk['total_count'], walk['bound_reached'])
    return _population_envelope(
        operation,
        reason,
        {
            'org': args.org,
            'count': len(repos),
            'total_count': walk['total_count'],
            'archived_count': sum(1 for repo in repos if repo['archived']),
            'pages_read': walk['pages_read'],
            'repos': repos,
        },
    )


# ---------------------------------------------------------------------------
# org search-code
# ---------------------------------------------------------------------------


def cmd_org_search_code(args: argparse.Namespace) -> dict:
    """Handle ``org search-code`` — every indexed file of an org containing a literal."""
    operation = 'org_search_code'
    if not _LOGIN_RE.match(args.org or ''):
        return make_error(operation, f'invalid organization login: {args.org!r}')
    literal = args.query or ''
    if not literal.strip():
        return make_error(operation, 'query must not be empty')
    if '"' in literal:
        return make_error(
            operation,
            'query must not contain a double quote: the literal is searched as one quoted phrase',
        )

    is_auth, err = github_ops.check_auth()
    if not is_auth:
        return make_error(operation, err)

    search_query = f'"{literal}" org:{args.org}'
    items: list[dict] = []
    total_count = 0
    provider_incomplete = False
    pages_read = 0
    for page in range(1, _CODE_SEARCH_MAX_PAGES + 1):
        returncode, stdout, stderr = github_ops.run_gh(
            [
                'api',
                '-X',
                'GET',
                'search/code',
                '-f',
                f'q={search_query}',
                '-F',
                f'per_page={_CODE_SEARCH_PAGE_SIZE}',
                '-F',
                f'page={page}',
            ]
        )
        if returncode != 0:
            result = make_error(operation, f'code search page {page} could not be read', stderr.strip())
            result['pages_read'] = pages_read
            return result
        try:
            data = json.loads(stdout)
            total_count = int(data['total_count'])
            provider_incomplete = provider_incomplete or bool(data['incomplete_results'])
            batch = [item for item in data['items'] if isinstance(item, dict)]
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            result = make_error(operation, f'malformed code search response on page {page}', str(exc))
            result['pages_read'] = pages_read
            return result
        pages_read = page
        items.extend(batch)
        if len(items) >= total_count or len(batch) < _CODE_SEARCH_PAGE_SIZE:
            break

    matches = [
        {
            'repository': (item.get('repository') or {}).get('full_name', ''),
            'path': item.get('path', ''),
            'sha': item.get('sha', ''),
        }
        for item in items
    ]
    if provider_incomplete:
        reason = 'provider_incomplete_results'
    elif len(matches) < total_count and pages_read == _CODE_SEARCH_MAX_PAGES:
        reason = 'result_cap_reached'
    elif len(matches) != total_count:
        reason = 'count_mismatch'
    else:
        reason = ''
    return _population_envelope(
        operation,
        reason,
        {
            'org': args.org,
            'query': literal,
            'scope': _CODE_SEARCH_SCOPE,
            'incomplete_results': provider_incomplete,
            'count': len(matches),
            'total_count': total_count,
            'repository_count': len({match['repository'] for match in matches}),
            'pages_read': pages_read,
            'matches': matches,
        },
    )


# ---------------------------------------------------------------------------
# repo file read
# ---------------------------------------------------------------------------


def _http_status_in(stderr: str, status: int) -> bool:
    """Return True when ``gh api``'s stderr reports the given HTTP status."""
    return f'(HTTP {status})' in (stderr or '')


def cmd_repo_file_read(args: argparse.Namespace) -> dict:
    """Handle ``repo file read`` — one file at the default branch or an explicit ref."""
    operation = 'repo_file_read'
    repo = _split_repo(args.repo)
    if repo is None:
        return make_error(operation, f'invalid repository (expected OWNER/NAME): {args.repo!r}')
    path = (args.path or '').strip('/')
    if not path:
        return make_error(operation, 'path must not be empty')

    is_auth, err = github_ops.check_auth()
    if not is_auth:
        return make_error(operation, err)

    full_name = f'{repo[0]}/{repo[1]}'
    endpoint = f'repos/{full_name}/contents/{quote(path, safe="/")}'
    if args.ref:
        endpoint += f'?ref={quote(args.ref, safe="")}'
    identity = {
        'repo': full_name,
        'path': path,
        'ref': args.ref or '',
        'ref_source': 'explicit' if args.ref else 'default_branch',
    }

    returncode, stdout, stderr = github_ops.run_gh(['api', endpoint])
    if returncode != 0:
        return _classify_file_read_failure(operation, identity, stderr)

    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        return make_error(operation, 'malformed contents response', stdout[:200])
    if not isinstance(data, dict) or data.get('type') != 'file':
        kind = 'directory' if isinstance(data, list) else str((data or {}).get('type', 'unknown'))
        return make_error(operation, f'not_a_file: {path} is a {kind}', full_name)
    if data.get('encoding') != 'base64':
        return make_error(
            operation,
            'content_unavailable: the contents API returned no inline content (file exceeds its size limit)',
            f'{full_name}:{path} size={data.get("size", "")}',
        )
    try:
        content = base64.b64decode(data.get('content') or '').decode('utf-8')
    except (binascii.Error, UnicodeDecodeError) as exc:
        return make_error(operation, 'undecodable_content: file is not valid UTF-8 text', str(exc))

    return {
        'status': 'success',
        'operation': operation,
        'provider': 'github',
        'state': FILE_READ_FOUND,
        **identity,
        'sha': data.get('sha', ''),
        'size': len(content.encode('utf-8')),
        'content': BlockScalar(content),
    }


def _classify_file_read_failure(operation: str, identity: dict, stderr: str) -> dict:
    """Separate an absent path from an unreadable repository or ref.

    GitHub answers HTTP 404 both for a missing path and for a repository the
    credentials cannot see, so a 404 is attributed to the PATH only after the
    repository itself is shown readable. An unknown ref and an unreadable
    repository are errors, never ``not_found``: reporting them as an absent file
    would answer "the file is not there" about a tree nobody looked at.
    """
    if _http_status_in(stderr, 409) and 'empty' in stderr.lower():
        return {
            'status': 'success',
            'operation': operation,
            'provider': 'github',
            'state': FILE_READ_NOT_FOUND,
            'not_found_reason': 'repository_empty',
            **identity,
        }
    if not _http_status_in(stderr, 404):
        return make_error(operation, 'read_failed', stderr.strip())
    if 'no commit found for the ref' in stderr.lower():
        return make_error(operation, f'ref_not_found: {identity["ref"]}', stderr.strip())

    full_name = identity['repo']
    repo_rc, _, repo_stderr = github_ops.run_gh(['api', f'repos/{full_name}'])
    if repo_rc != 0:
        return make_error(operation, f'repository_not_accessible: {full_name}', repo_stderr.strip())
    return {
        'status': 'success',
        'operation': operation,
        'provider': 'github',
        'state': FILE_READ_NOT_FOUND,
        'not_found_reason': 'path_absent',
        **identity,
    }


# ---------------------------------------------------------------------------
# repo label list
# ---------------------------------------------------------------------------


def cmd_repo_label_list(args: argparse.Namespace) -> dict:
    """Handle ``repo label list`` — every label of a repository, all pages."""
    operation = 'repo_label_list'
    if args.repo:
        repo = _split_repo(args.repo)
        if repo is None:
            return make_error(operation, f'invalid repository (expected OWNER/NAME): {args.repo!r}')
    else:
        repo = None

    is_auth, err = github_ops.check_auth()
    if not is_auth:
        return make_error(operation, err)

    if repo is None:
        owner, name = github_ops.get_repo_info()
        if not owner or not name:
            return make_error(operation, 'could not resolve the repository of the routed working tree')
        repo = (owner, name)
    full_name = f'{repo[0]}/{repo[1]}'

    walk = _paginate_connection(
        _REPO_LABELS_QUERY,
        {'owner': repo[0], 'name': repo[1]},
        lambda data: (data.get('repository') or {}).get('labels'),
    )
    if not walk['ok']:
        return _walk_failure(operation, walk, f'repo={full_name}')

    labels = [
        {
            'name': node.get('name', ''),
            'color': node.get('color', ''),
            'description': node.get('description') or '',
        }
        for node in walk['nodes']
    ]
    reason = _completeness(len(labels), walk['total_count'], walk['bound_reached'])
    return _population_envelope(
        operation,
        reason,
        {
            'repo': full_name,
            'count': len(labels),
            'total_count': walk['total_count'],
            'pages_read': walk['pages_read'],
            'labels': labels,
        },
    )

#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for ``fetch_pr_comments_data``: ``updated_at`` plumbing and connection coverage.

Two concerns share this file because both are only observable on the REAL parsing
path. The first is the ``updated_at`` plumbing across record kinds, documented
below. The second is COVERAGE: every connection of the comment fetch is paginated
by cursor to completion, and the result reports per connection what was observed
against its first-page cap (``connections[]``) plus a top-level ``complete`` flag,
so a clipped population is never published as a complete one. The coverage arms
drive the pagination through a query-dispatching ``run_graphql`` stub.

``REVIEW_THREADS_QUERY`` used to select ``updatedAt`` only on the issue-level
``comments`` node. The record BUILDERS read ``comment.get('updatedAt')`` /
``review.get('updatedAt')`` for all three kinds, so the omission was invisible in
the code: the ``inline`` and ``review_body`` records simply resolved to ``''`` on
every call, and the docstring asserted that as a PROVIDER limitation
("review bodies and inline thread comments do not expose one") — which is false.
``PullRequestReviewComment.updatedAt`` and ``PullRequestReview.updatedAt`` both
exist.

That mattered beyond tidiness: a completion predicate keying on ``updated_at``
movement can only ever fire for a bot whose declared ``participation_evidence`` is
``issue_comment``. For any bot declaring ``review_body`` or ``inline`` evidence the
detector was structurally VACUOUS — it could never succeed — while every
registry-derived answerability signal still reported it as answerable.

**This file exists because no other test exercises ``REVIEW_THREADS_QUERY`` at
all.** Every consumer test (``test_comments_stage.py``, ``test_re_review_strategy.py``,
``test_pre_merge_barrier.py``, ``test_github_pr.py``) monkeypatches
``fetch_pr_comments_data`` wholesale and constructs its own record dicts — which is
precisely how a long-lived selection-set gap went unobserved. These tests drive the
REAL parsing path with only ``run_graphql`` (plus auth/repo resolution) patched:
no network, no ``gh``.

Scope (AAA):
    - ``REVIEW_THREADS_QUERY`` SELECTS ``updatedAt`` inside all three source-node
      selection sets. **This is the arm that reddens against the pre-widening
      query**, and it asserts on the query TEXT rather than on parsed output for a
      load-bearing reason spelled out below.
    - every emitted record kind carries the ``updated_at`` its source node reported
    - ``created_at`` keeps its per-kind source mapping, so ``max(updated_at,
      created_at)`` retains its meaning
    - a payload whose nodes omit ``updatedAt`` falls back to ``''`` rather than
      raising — pinning that the empty string now means "the provider reported
      none", the claim the corrected docstring makes

**Why the selection set needs its own arm.** The parse-level arms monkeypatch
``run_graphql`` and feed a canned payload, so their fixture carries ``updatedAt``
on every node NO MATTER WHAT THE QUERY ASKED FOR — a stub cannot omit a field on
the strength of a selection set it never sees. Those arms therefore pass
identically against the pre-widening query and cannot, even in principle, detect
the omission this file exists to close. They guard the record BUILDERS (which were
never broken); only :func:`test_query_selects_updated_at_on_every_source_node`
guards the QUERY (which was). Deleting or weakening that arm silently returns this
file to a suite that would have watched the original gap ship.
"""

import github_ops

# One DISTINCT timestamp per source node, so the assertions prove each record kind
# is plumbed from its OWN node rather than from a shared constant that happens to
# be non-empty. A fourth record kind added later has no entry here and raises a
# KeyError in the per-record loop below — it cannot escape the assertion by
# simply not being on a hard-coded name list.
_EXPECTED_UPDATED_AT = {
    'inline': '2026-03-01T11:00:00Z',
    'review_body': '2026-03-02T12:00:00Z',
    'issue_comment': '2026-03-03T13:00:00Z',
}

# The per-kind ``created_at`` source differs by design (``createdAt`` for inline and
# issue comments, ``submittedAt`` for a review body). Pinned because the movement
# arm compares ``max(updated_at, created_at)``: silently re-pointing either field
# would change that comparison's meaning without changing its shape.
_EXPECTED_CREATED_AT = {
    'inline': '2026-03-01T10:00:00Z',
    'review_body': '2026-03-02T10:00:00Z',
    'issue_comment': '2026-03-03T10:00:00Z',
}


def _payload(*, with_updated_at: bool) -> dict:
    """Build a GraphQL response carrying all three source-node kinds.

    When ``with_updated_at`` is False every node OMITS the ``updatedAt`` key
    entirely — the shape a provider returns when it reports no edit timestamp.
    """
    inline_comment = {
        'id': 'PRRC_inline',
        'body': 'inline thread comment',
        'author': {'login': 'coderabbitai[bot]'},
        'createdAt': _EXPECTED_CREATED_AT['inline'],
    }
    review = {
        'id': 'PRR_review',
        'state': 'COMMENTED',
        'body': 'review submission body',
        'author': {'login': 'coderabbitai[bot]'},
        'submittedAt': _EXPECTED_CREATED_AT['review_body'],
    }
    issue_comment = {
        'id': 'IC_issue',
        'body': 'issue-level comment',
        'author': {'login': 'cuioss-review-bot'},
        'createdAt': _EXPECTED_CREATED_AT['issue_comment'],
    }
    if with_updated_at:
        inline_comment['updatedAt'] = _EXPECTED_UPDATED_AT['inline']
        review['updatedAt'] = _EXPECTED_UPDATED_AT['review_body']
        issue_comment['updatedAt'] = _EXPECTED_UPDATED_AT['issue_comment']

    return {
        'repository': {
            'pullRequest': {
                'reviewThreads': {
                    'nodes': [
                        {
                            'id': 'PRRT_thread',
                            'isResolved': False,
                            'path': 'src/foo.py',
                            'line': 42,
                            'comments': {'nodes': [inline_comment]},
                        }
                    ]
                },
                'reviews': {'nodes': [review]},
                'comments': {'nodes': [issue_comment]},
            }
        }
    }


def _wire(monkeypatch, *, with_updated_at: bool) -> None:
    """Patch auth / repo resolution / transport so the REAL parsing path runs."""
    monkeypatch.setattr(github_ops, 'check_auth', lambda: (True, ''))
    monkeypatch.setattr(github_ops, 'get_repo_info', lambda: ('cuioss', 'plan-marshall'))

    def fake_run_graphql(query, variables):
        # The query under test is the one the widening applies to; asserting on it
        # keeps this test bound to REVIEW_THREADS_QUERY rather than to whatever
        # query fetch_pr_comments_data might later issue.
        assert query == github_ops.REVIEW_THREADS_QUERY
        return 0, _payload(with_updated_at=with_updated_at), ''

    monkeypatch.setattr(github_ops, 'run_graphql', fake_run_graphql)


def _selection_block(query: str, opening: str) -> str:
    """Return the brace-balanced body of the selection set introduced by ``opening``.

    Scoping each assertion to ONE node's own braces is what stops a single
    ``updatedAt`` elsewhere in the query from satisfying every check — the exact
    shape of the original defect, where the issue-level ``comments`` node carried
    the field and the other two did not.
    """
    start = query.index(opening) + len(opening)
    depth = 0
    for index in range(start, len(query)):
        if query[index] == '{':
            depth += 1
        elif query[index] == '}':
            depth -= 1
            if depth == 0:
                return query[start : index + 1]
    raise AssertionError(f'unbalanced selection set after {opening!r}')


# The three leaf selection sets whose records must carry an edit timestamp, keyed
# by the record kind each one produces. Both GraphQL types expose the field
# (``PullRequestReviewComment.updatedAt``, ``PullRequestReview.updatedAt``), so an
# absent selection is this query's own omission and never a provider limitation.
_SOURCE_NODE_OPENINGS = {
    'inline': 'comments(first: 10)',
    'review_body': 'reviews(first: 100)',
    'issue_comment': 'comments(first: 100)',
}


def test_query_selects_updated_at_on_every_source_node():
    # THE selection-set pin, and the ONLY arm in this file that reddens against the
    # pre-widening query. Pre-fix, `reviewThreads.comments.nodes` selected only
    # `createdAt` and `reviews.nodes` only `submittedAt`, so the inline and
    # review_body records resolved to '' on every real call no matter what GitHub
    # held — making an updated_at-movement detector structurally VACUOUS for any
    # bot whose declared participation evidence is not `issue_comment`.
    #
    # It asserts on the query text because the parse arms below CANNOT catch this:
    # they stub run_graphql, so their payload carries updatedAt regardless of the
    # selection set and they pass identically against the broken query.
    query = github_ops.REVIEW_THREADS_QUERY

    for kind, opening in _SOURCE_NODE_OPENINGS.items():
        block = _selection_block(query, opening)
        assert 'updatedAt' in block, (
            f'{kind} records are built from the {opening!r} selection set, which does '
            f'not request updatedAt — those records can only ever emit an empty '
            f'updated_at, silently disabling every edit-movement consumer'
        )


def test_every_record_kind_carries_its_source_updated_at(monkeypatch):
    # Guards the record BUILDERS: each kind must read its edit timestamp from its
    # OWN source node. Explicitly NOT a selection-set pin — `run_graphql` is stubbed
    # here, so the payload carries `updatedAt` whatever the query asked for and this
    # arm passes against the pre-widening query too. The query is pinned separately
    # by `test_query_selects_updated_at_on_every_source_node`; claiming this arm
    # covers it would be the vacuous-detector mistake the widening exists to fix.
    _wire(monkeypatch, with_updated_at=True)

    result = github_ops.fetch_pr_comments_data(123)

    assert result['status'] == 'success'
    emitted_kinds = {record['kind'] for record in result['comments']}
    # Non-vacuity floor: all three kinds really were emitted, so the per-record
    # loop below cannot pass by iterating an empty or partial list. Written as a
    # SUBSET test so a fourth kind widens the population instead of breaking it.
    assert set(_EXPECTED_UPDATED_AT) <= emitted_kinds

    # Iterate the records the function ACTUALLY emitted — not a hard-coded name
    # list — so a kind added later is covered automatically (and, lacking an
    # expectation entry, fails loudly rather than slipping through unchecked).
    for record in result['comments']:
        assert record['updated_at'], f'{record["kind"]} record lost its updated_at'
        assert record['updated_at'] == _EXPECTED_UPDATED_AT[record['kind']]


def test_created_at_keeps_its_per_kind_source_mapping(monkeypatch):
    # The movement arm compares max(updated_at, created_at). Widening the selection
    # set must not disturb which node each kind's created_at comes from, or that
    # comparison silently changes meaning while keeping its shape.
    _wire(monkeypatch, with_updated_at=True)

    result = github_ops.fetch_pr_comments_data(123)

    for record in result['comments']:
        assert record['created_at'] == _EXPECTED_CREATED_AT[record['kind']]


def test_absent_updated_at_falls_back_to_empty_string(monkeypatch):
    # The corrected docstring's claim: an empty updated_at now means "the provider
    # reported none" — no longer "this query forgot to ask". A node that omits the
    # field must degrade to '' rather than raising into the caller.
    _wire(monkeypatch, with_updated_at=False)

    result = github_ops.fetch_pr_comments_data(123)

    assert result['status'] == 'success'
    assert set(_EXPECTED_UPDATED_AT) <= {record['kind'] for record in result['comments']}
    for record in result['comments']:
        assert record['updated_at'] == ''


# ============================================================================
# Connection coverage: pagination to completion, reported per connection
# ============================================================================

#: The first-page size of the three top-level connections, and of each thread's
#: comment connection — read from the module so the fixtures below always build a
#: population exactly one past the page the unpaginated read used to stop at.
_PAGE = github_ops._COMMENT_CONNECTION_PAGE_SIZE
_THREAD_PAGE = github_ops._THREAD_COMMENT_FIRST_PAGE_SIZE

#: The connection openings of the FIRST-page query, each of which must select its
#: own ``totalCount`` and ``pageInfo``.
_CONNECTION_OPENINGS = {
    github_ops.CONNECTION_REVIEW_THREADS: f'reviewThreads(first: {_PAGE})',
    github_ops.CONNECTION_THREAD_COMMENTS: f'comments(first: {_THREAD_PAGE})',
    github_ops.CONNECTION_REVIEWS: f'reviews(first: {_PAGE})',
    github_ops.CONNECTION_ISSUE_COMMENTS: f'comments(first: {_PAGE})',
}


def _connection(nodes: list, *, has_next: bool = False, cursor: str | None = None, total: int | None = None) -> dict:
    """A connection object as GitHub returns it: nodes, ``totalCount`` and ``pageInfo``."""
    return {
        'totalCount': len(nodes) if total is None else total,
        'pageInfo': {'hasNextPage': has_next, 'endCursor': cursor},
        'nodes': nodes,
    }


def _review(n: int) -> dict:
    return {
        'id': f'PRR_{n}',
        'state': 'COMMENTED',
        'body': f'review body {n}',
        'author': {'login': 'coderabbitai[bot]'},
        'submittedAt': '2026-03-02T10:00:00Z',
        'updatedAt': '2026-03-02T10:00:00Z',
    }


def _thread_comment(n: int) -> dict:
    return {
        'id': f'PRRC_{n}',
        'body': f'thread comment {n}',
        'author': {'login': 'alice'},
        'createdAt': '2026-03-01T10:00:00Z',
        'updatedAt': '2026-03-01T10:00:00Z',
    }


def _first_page(*, threads: dict, reviews: dict, issue_comments: dict) -> dict:
    return {'repository': {'pullRequest': {'reviewThreads': threads, 'reviews': reviews, 'comments': issue_comments}}}


def _thread(thread_id: str, comments: dict) -> dict:
    return {'id': thread_id, 'isResolved': False, 'path': 'src/foo.py', 'line': 7, 'comments': comments}


def _wire_pages(monkeypatch, responses: dict) -> list[tuple[str, dict]]:
    """Patch the transport with a query-dispatching stub; return the recorded calls.

    ``responses`` maps each query constant to a callable taking the call's variables
    and returning ``(returncode, data, error)``. A query the case did not declare
    fails the case — an undeclared page read is itself a finding.
    """
    monkeypatch.setattr(github_ops, 'check_auth', lambda: (True, ''))
    monkeypatch.setattr(github_ops, 'get_repo_info', lambda: ('cuioss', 'plan-marshall'))
    calls: list[tuple[str, dict]] = []

    def fake_run_graphql(query, variables):
        calls.append((query, dict(variables)))
        assert query in responses, f'unexpected GraphQL query issued:\n{query}'
        return responses[query](variables)

    monkeypatch.setattr(github_ops, 'run_graphql', fake_run_graphql)
    return calls


def _records_by_connection(result: dict) -> dict:
    return {record['connection']: record for record in result['connections']}


def test_query_selects_page_info_and_total_count_on_every_connection():
    # Selection-set pin, for the same reason as the updated_at pin above: a stub
    # carries pageInfo whatever the query asked for, so only the query text can show
    # that a real response will carry the evidence the coverage report is built from.
    query = github_ops.REVIEW_THREADS_QUERY

    for connection, opening in _CONNECTION_OPENINGS.items():
        block = _selection_block(query, opening)
        for field in ('totalCount', 'hasNextPage', 'endCursor'):
            assert field in block, f'{connection} ({opening!r}) does not select {field}'


def test_101st_review_and_11th_thread_comment_are_fetched_and_reported(monkeypatch):
    # THE fail-first case. Before pagination the single query stopped at the first
    # page of every connection: the 101st review and the 11th comment of a thread were
    # silently dropped while the fetch reported success, and the result carried no
    # coverage field at all. Here both follow-up pages are served and must be read.
    first = _first_page(
        threads=_connection(
            [
                _thread(
                    'PRRT_long',
                    _connection(
                        [_thread_comment(n) for n in range(1, _THREAD_PAGE + 1)],
                        has_next=True,
                        cursor='tc-page-1',
                        total=_THREAD_PAGE + 1,
                    ),
                )
            ]
        ),
        reviews=_connection(
            [_review(n) for n in range(1, _PAGE + 1)], has_next=True, cursor='rev-page-1', total=_PAGE + 1
        ),
        issue_comments=_connection([]),
    )

    def reviews_page(variables):
        assert variables['cursor'] == 'rev-page-1'
        page = _connection([_review(_PAGE + 1)], total=_PAGE + 1)
        return 0, {'repository': {'pullRequest': {'reviews': page}}}, ''

    def thread_comments_page(variables):
        assert variables == {'thread': 'PRRT_long', 'cursor': 'tc-page-1'}
        return 0, {'node': {'comments': _connection([_thread_comment(_THREAD_PAGE + 1)], total=_THREAD_PAGE + 1)}}, ''

    calls = _wire_pages(
        monkeypatch,
        {
            github_ops.REVIEW_THREADS_QUERY: lambda _v: (0, first, ''),
            github_ops.REVIEWS_PAGE_QUERY: reviews_page,
            github_ops.THREAD_COMMENTS_PAGE_QUERY: thread_comments_page,
        },
    )

    result = github_ops.fetch_pr_comments_data(123)

    assert result['status'] == 'success'
    review_ids = [c['id'] for c in result['comments'] if c['kind'] == 'review_body']
    inline_ids = [c['id'] for c in result['comments'] if c['kind'] == 'inline']
    assert len(review_ids) == _PAGE + 1
    assert f'PRR_{_PAGE + 1}' in review_ids
    assert len(inline_ids) == _THREAD_PAGE + 1
    assert f'PRRC_{_THREAD_PAGE + 1}' in inline_ids
    # Each follow-up page was read exactly once, and no exhausted connection was re-read.
    assert [query for query, _ in calls].count(github_ops.REVIEWS_PAGE_QUERY) == 1
    assert [query for query, _ in calls].count(github_ops.THREAD_COMMENTS_PAGE_QUERY) == 1
    assert github_ops.REVIEW_THREADS_PAGE_QUERY not in [query for query, _ in calls]
    assert github_ops.ISSUE_COMMENTS_PAGE_QUERY not in [query for query, _ in calls]

    records = _records_by_connection(result)
    assert set(records) == set(_CONNECTION_OPENINGS)
    assert records[github_ops.CONNECTION_REVIEWS] == {
        'connection': github_ops.CONNECTION_REVIEWS,
        'observed': _PAGE + 1,
        'cap': _PAGE,
        'total': _PAGE + 1,
        'capped': False,
    }
    assert records[github_ops.CONNECTION_THREAD_COMMENTS] == {
        'connection': github_ops.CONNECTION_THREAD_COMMENTS,
        'observed': _THREAD_PAGE + 1,
        'cap': _THREAD_PAGE,
        'total': _THREAD_PAGE + 1,
        'capped': False,
    }
    assert result['complete'] is True


def test_connection_not_proven_exhausted_is_reported_capped(monkeypatch):
    # A page claiming more data but naming no cursor cannot be continued. The pages
    # read are still returned, but the connection is reported capped against its cap
    # and the fetch is not complete — never a clipped population published as whole.
    first = _first_page(
        threads=_connection([]),
        reviews=_connection([_review(n) for n in range(1, _PAGE + 1)], has_next=True, cursor=None, total=_PAGE + 5),
        issue_comments=_connection([]),
    )
    calls = _wire_pages(monkeypatch, {github_ops.REVIEW_THREADS_QUERY: lambda _v: (0, first, '')})

    result = github_ops.fetch_pr_comments_data(123)

    assert result['status'] == 'success'
    assert len(calls) == 1
    reviews = _records_by_connection(result)[github_ops.CONNECTION_REVIEWS]
    assert reviews == {
        'connection': github_ops.CONNECTION_REVIEWS,
        'observed': _PAGE,
        'cap': _PAGE,
        'total': _PAGE + 5,
        'capped': True,
    }
    assert result['complete'] is False


def test_total_count_beyond_observed_is_reported_capped(monkeypatch):
    # hasNextPage false does not outvote the provider's own totalCount: when the
    # provider says more exist than were observed, the population is not proven whole.
    first = _first_page(
        threads=_connection([]),
        reviews=_connection([]),
        issue_comments=_connection([], total=3),
    )
    _wire_pages(monkeypatch, {github_ops.REVIEW_THREADS_QUERY: lambda _v: (0, first, '')})

    result = github_ops.fetch_pr_comments_data(123)

    records = _records_by_connection(result)
    assert records[github_ops.CONNECTION_ISSUE_COMMENTS]['capped'] is True
    assert records[github_ops.CONNECTION_REVIEWS]['capped'] is False
    assert result['complete'] is False


def test_cursor_that_does_not_advance_stops_and_reports_capped(monkeypatch):
    # A provider repeating the same cursor with hasNextPage true would loop forever.
    # The drain stops after the non-advancing page and reports the connection capped.
    first = _first_page(
        threads=_connection([]),
        reviews=_connection([]),
        issue_comments=_connection([], has_next=True, cursor='stuck'),
    )

    def stuck_page(variables):
        assert variables['cursor'] == 'stuck'
        return 0, {'repository': {'pullRequest': {'comments': _connection([], has_next=True, cursor='stuck')}}}, ''

    calls = _wire_pages(
        monkeypatch,
        {github_ops.REVIEW_THREADS_QUERY: lambda _v: (0, first, ''), github_ops.ISSUE_COMMENTS_PAGE_QUERY: stuck_page},
    )

    result = github_ops.fetch_pr_comments_data(123)

    assert [query for query, _ in calls].count(github_ops.ISSUE_COMMENTS_PAGE_QUERY) == 1
    assert _records_by_connection(result)[github_ops.CONNECTION_ISSUE_COMMENTS]['capped'] is True
    assert result['complete'] is False


def test_failed_follow_up_page_fails_the_fetch(monkeypatch):
    # The pages read before a failed follow-up are never published as the whole.
    first = _first_page(
        threads=_connection([]),
        reviews=_connection([_review(1)], has_next=True, cursor='rev-page-1', total=2),
        issue_comments=_connection([]),
    )
    _wire_pages(
        monkeypatch,
        {
            github_ops.REVIEW_THREADS_QUERY: lambda _v: (0, first, ''),
            github_ops.REVIEWS_PAGE_QUERY: lambda _v: (1, None, 'HTTP 502'),
        },
    )

    result = github_ops.fetch_pr_comments_data(123)

    assert result['status'] == 'error'
    assert 'HTTP 502' in result['error']
    assert 'comments' not in result


def test_response_without_page_info_is_not_reported_complete(monkeypatch):
    # A response carrying no pageInfo proves nothing about exhaustion. Every
    # connection is reported capped rather than read as whole on absent evidence.
    _wire(monkeypatch, with_updated_at=True)

    result = github_ops.fetch_pr_comments_data(123)

    assert result['status'] == 'success'
    records = _records_by_connection(result)
    assert set(records) == set(_CONNECTION_OPENINGS)
    assert all(record['capped'] for record in records.values())
    assert result['complete'] is False

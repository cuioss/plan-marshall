#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for ``fetch_pr_comments_data``'s ``updated_at`` plumbing across record kinds.

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

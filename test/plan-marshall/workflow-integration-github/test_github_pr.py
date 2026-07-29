#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Regression tests for github_pr.cmd_fetch_findings cross-iteration dedup.

Covers the producer-side dedup guard hardened to key on
``(bot_kind, comment_id)`` for ALL bot kinds — thread-bearing and thread_id-less
alike:

    1. A second ``fetch_findings`` over the same PR (mixed bot kinds,
       thread-bearing + thread_id-less) stores zero new findings and raises no
       ``(producer-mismatch)`` Q-Gate false-positive.
    2. Two distinct bots reusing the same numeric ``comment_id`` are kept
       distinct — keying on ``(bot_kind, comment_id)`` rather than ``comment_id``
       alone means a second bot's identically-numbered comment is NOT wrongly
       deduped against the first bot's.

The findings store is REAL (isolated via the autouse ``plan_context``
``PLAN_BASE_DIR`` sandbox); only the GitHub provider surface (``check_auth``,
``fetch_pr_comments_data``, ``fetch_pr_head_sha``) is monkeypatched, so the
dedup path exercises the genuine ``_findings_core`` add/query round-trip —
including the ``bot_kind`` field the guard now keys on. Module import resolves
via the root conftest's marketplace PYTHONPATH setup.
"""

import argparse
import json
import sys

import pytest

from conftest import load_script_module

github_pr = load_script_module('plan-marshall', 'workflow-integration-github', 'github_pr.py', 'github_pr')
_findings_core = load_script_module('plan-marshall', 'manage-findings', '_findings_core.py', '_findings_core')

query_findings = _findings_core.query_findings


# Mixed-bot, mixed-thread comment set: coderabbit (thread-bearing), sourcery
# (thread_id-less review_body), pr-agent (thread-bearing — a third registered
# bot_kind, which is all this fixture needs), and a human (thread_id-less issue
# comment). Bodies are substantive so none is dropped by the
# ``_is_obvious_noise`` pre-filter.
_COMMENTS = [
    {
        'id': 'c1',
        'author': 'coderabbitai',
        'thread_id': 'PRRT_1',
        'kind': 'inline',
        'body': 'Consider handling the None case here before dereferencing.',
        'path': 'src/a.py',
        'line': 10,
        'resolved': False,
    },
    {
        'id': 'c2',
        'author': 'sourcery-ai',
        'thread_id': '',
        'kind': 'review_body',
        'body': 'Overall the change reads well but this helper should be extracted.',
        'resolved': False,
    },
    {
        'id': 'c3',
        'author': 'cuioss-review-bot',
        'thread_id': 'PRRT_3',
        'kind': 'inline',
        'body': 'This loop can be simplified into a comprehension.',
        'path': 'src/b.py',
        'line': 5,
        'resolved': False,
    },
    {
        'id': 'c4',
        'author': 'alice',
        'thread_id': '',
        'kind': 'issue_comment',
        'body': 'Please add a regression test for the edge case described in the ticket.',
        'resolved': False,
    },
]


def _patch_provider(monkeypatch, comments):
    """Monkeypatch the GitHub provider surface ``github_pr`` reaches through ``_github``."""
    monkeypatch.setattr(github_pr._github, 'check_auth', lambda: (True, ''))
    monkeypatch.setattr(
        github_pr._github,
        'fetch_pr_comments_data',
        lambda pr_number, unresolved_only=False: {
            'status': 'success',
            'provider': 'github',
            'comments': list(comments),
            'total': len(comments),
            'unresolved': len(comments),
        },
    )
    monkeypatch.setattr(github_pr._github, 'fetch_pr_head_sha', lambda pr_number: 'deadbeef')


def _run_fetch(pr_number, plan_id):
    args = argparse.Namespace(pr_number=pr_number, plan_id=plan_id)
    return github_pr.cmd_fetch_findings(args)


def _live_findings_core():
    """Return the ``_findings_core`` module object the SUT will actually import.

    ``cmd_fetch_findings`` imports ``_findings_core`` lazily, inside the function
    body, so the module object it binds is whatever ``sys.modules`` holds at CALL
    time. ``load_script_module`` re-registers ``sys.modules['_findings_core']``
    with a *fresh* object on every call, and several test modules load it — so
    the object this module captured at import time is not necessarily the one the
    SUT resolves when the test runs. Monkeypatching the import-time capture is
    then a silent no-op: the validator keeps reading the unpatched globals of a
    different module object. Resolving the live ``sys.modules`` entry at call
    time targets the very globals ``add_finding`` reads.
    """
    return sys.modules['_findings_core']


def test_second_fetch_dedupes_all_bot_kinds(plan_context, monkeypatch):
    """A re-fetch of an already-staged PR stores zero new findings for every bot kind.

    Thread-bearing (coderabbit/pr-agent) AND thread_id-less (sourcery/human)
    comments are all deduped on ``(bot_kind, comment_id)``, and the deduped
    comments — legitimate non-stores — do not trip the producer-mismatch Q-Gate.
    """
    plan_id = 'gh-pr-dedup-refetch'
    _patch_provider(monkeypatch, _COMMENTS)

    # First fetch: every surviving comment becomes a fresh pr-comment finding.
    first = _run_fetch(101, plan_id)
    assert first['status'] == 'success'
    assert first['count_stored'] == len(_COMMENTS)
    assert first['count_skipped_duplicate'] == 0
    assert first['producer_mismatch_hash_id'] is None
    assert len(query_findings(plan_id, finding_type='pr-comment')['findings']) == len(_COMMENTS)

    # Second fetch: identical comments. Every one is deduped — nothing new is
    # stored, and the store is unchanged (no duplicate findings accreted).
    second = _run_fetch(101, plan_id)
    assert second['status'] == 'success'
    assert second['count_stored'] == 0
    assert second['count_skipped_duplicate'] == len(_COMMENTS)
    assert second['producer_mismatch_hash_id'] is None
    assert len(query_findings(plan_id, finding_type='pr-comment')['findings']) == len(_COMMENTS)


def test_same_comment_id_distinct_bots_not_collided(plan_context, monkeypatch):
    """Two bots reusing the same numeric comment_id stay distinct across fetches.

    With the old ``comment_id``-only key the second bot's identically-numbered
    comment would be wrongly skipped as a duplicate. Keying on
    ``(bot_kind, comment_id)`` keeps them apart, so the second bot's comment is
    stored on the follow-up fetch.
    """
    plan_id = 'gh-pr-dedup-collision'
    coderabbit_999 = {
        'id': '999',
        'author': 'coderabbitai',
        'thread_id': '',
        'kind': 'review_body',
        'body': 'CodeRabbit: this branch is never exercised by a test.',
        'resolved': False,
    }
    sourcery_999 = {
        'id': '999',
        'author': 'sourcery-ai',
        'thread_id': '',
        'kind': 'review_body',
        'body': 'Sourcery: consider renaming this variable for clarity.',
        'resolved': False,
    }

    # Fetch 1: only the coderabbit comment, numeric id 999.
    _patch_provider(monkeypatch, [coderabbit_999])
    first = _run_fetch(102, plan_id)
    assert first['count_stored'] == 1

    # Fetch 2: a sourcery comment reusing the SAME numeric id 999. It must NOT
    # be deduped against the coderabbit one — distinct bot_kind, distinct key.
    _patch_provider(monkeypatch, [sourcery_999])
    second = _run_fetch(102, plan_id)
    assert second['count_stored'] == 1
    assert second['count_skipped_duplicate'] == 0
    assert second['producer_mismatch_hash_id'] is None

    # Both bots' comments now coexist in the store under the shared numeric id.
    stored = query_findings(plan_id, finding_type='pr-comment')['findings']
    assert len(stored) == 2
    assert {f.get('bot_kind') for f in stored} == {'coderabbit', 'sourcery'}


def _run_fetch_classified(pr_number, plan_id, *, required_bots=None, optional_bots=None):
    """Invoke ``cmd_fetch_findings`` with explicit participation-classification lists.

    ``required_bots`` / ``optional_bots`` are the raw comma-joined flag values
    (``'coderabbit'``, ``'coderabbit,pr-agent'``, or ``''`` for an
    answered-empty list). Their union is the CLASSIFIED set; neither list admits
    or drops a comment. The sibling ``_run_fetch`` omits both attributes, which
    is the never-supplied case.
    """
    args = argparse.Namespace(
        pr_number=pr_number,
        plan_id=plan_id,
        required_bots=required_bots,
        optional_bots=optional_bots,
    )
    return github_pr.cmd_fetch_findings(args)


def test_unclassified_bot_comments_are_ingested_and_reported(plan_context, monkeypatch):
    """A bot in NEITHER list is warned about, never dropped — its findings are USED.

    With only ``--required-bots "coderabbit"`` supplied, sourcery and pr-agent
    fall outside the classified union. Under the warn-but-ingest rule their
    comments are stored exactly like a classified bot's; the two bots are merely
    named in ``unclassified_bots`` so the caller can surface the configuration
    gap. Dropping them would let a configuration omission silently destroy real
    review signal.
    """
    plan_id = 'gh-pr-unclassified-reported'
    _patch_provider(monkeypatch, _COMMENTS)

    result = _run_fetch_classified(101, plan_id, required_bots='coderabbit')
    assert result['status'] == 'success'
    # Every comment is ingested — classification is not admission.
    assert result['count_stored'] == len(_COMMENTS)
    assert result['unclassified_bots'] == ['pr-agent', 'sourcery']
    assert result['producer_mismatch_hash_id'] is None

    stored = query_findings(plan_id, finding_type='pr-comment')['findings']
    bot_kinds = {f.get('bot_kind') for f in stored}
    # The unclassified bots' findings are present and usable, not merely counted.
    assert {'coderabbit', 'pr-agent', 'sourcery'} <= bot_kinds


def test_classification_union_spans_both_lists(plan_context, monkeypatch):
    """A bot classified via EITHER list is not reported unclassified.

    ``--required-bots "coderabbit,pr-agent"`` plus ``--optional-bots "sourcery"``
    classifies all three participating bots, proving the producer takes the union
    of the two comma-split sets rather than reading only one list.
    """
    plan_id = 'gh-pr-classification-union'
    _patch_provider(monkeypatch, _COMMENTS)

    result = _run_fetch_classified(
        103, plan_id, required_bots='coderabbit,pr-agent', optional_bots='sourcery'
    )
    assert result['status'] == 'success'
    assert result['count_stored'] == len(_COMMENTS)
    assert result['unclassified_bots'] == []
    assert result['producer_mismatch_hash_id'] is None

    stored = query_findings(plan_id, finding_type='pr-comment')['findings']
    bot_kinds = {f.get('bot_kind') for f in stored}
    assert {'coderabbit', 'pr-agent', 'sourcery'} <= bot_kinds


def test_empty_classification_lists_still_ingest_every_bot(plan_context, monkeypatch):
    """Answered-empty lists classify nothing yet suppress nothing.

    Both knobs default to the empty string, so an unconfigured project yields an
    empty classified union. Every participating bot is therefore reported as
    unclassified — and every one of their comments is still stored. An empty
    configuration degrades to "warn about everything", never to "drop
    everything".
    """
    plan_id = 'gh-pr-classification-empty'
    _patch_provider(monkeypatch, _COMMENTS)

    result = _run_fetch_classified(102, plan_id, required_bots='', optional_bots='')
    assert result['status'] == 'success'
    assert result['count_stored'] == len(_COMMENTS)
    assert result['unclassified_bots'] == ['coderabbit', 'pr-agent', 'sourcery']
    assert result['producer_mismatch_hash_id'] is None

    stored = query_findings(plan_id, finding_type='pr-comment')['findings']
    assert len(stored) == len(_COMMENTS)


def test_pipeline_trigger_is_noise_while_a_rate_limit_notice_is_a_refusal(plan_context, monkeypatch):
    """A pipeline trigger is noise; a rate-limit notice is a REFUSAL, and the two differ.

    Over a comment set carrying (a) a ``@coderabbitai review`` re-review trigger
    comment this workflow itself posts, (b) a CodeRabbit rate-limit status notice
    posted in place of a review, and (c) a genuine substantive reviewer comment,
    ``fetch_findings`` stores ONLY the genuine comment — but the two non-stores are
    accounted for DIFFERENTLY. The trigger is noise (breaking the re-review feedback
    loop). The rate-limit notice is positive evidence CodeRabbit declined to review,
    so it lands in ``count_skipped_refusal`` and names the bot in ``refused_bots``
    instead of vanishing into the noise count. Neither raises a
    ``(producer-mismatch)`` Q-Gate false-positive.
    """
    plan_id = 'gh-pr-barrier-noise'
    comments = [
        # (a) Pipeline-authored re-review trigger — the exact registered coderabbit
        # trigger string. Dropped regardless of author (the recognizer is
        # author-agnostic: the pipeline posts it under the authenticated account).
        {
            'id': 'trigger-1',
            'author': 'oliver',
            'thread_id': '',
            'kind': 'issue_comment',
            'body': '@coderabbitai review',
            'resolved': False,
        },
        # (b) CodeRabbit rate-limit status notice — carries BOTH markers (the
        # ``## Rate limit exceeded`` heading AND the body sentence). Authored by
        # the coderabbit bot, so bot_kind resolves to 'coderabbit' and the refusal
        # is attributable.
        {
            'id': 'ratelimit-1',
            'author': 'coderabbitai',
            'thread_id': '',
            'kind': 'review_body',
            'body': (
                '> [!WARNING]\n'
                '> ## Rate limit exceeded\n'
                '>\n'
                '> @oliver has exceeded the limit for the number of files or '
                'commits that can be reviewed per hour.'
            ),
            'resolved': False,
        },
        # (c) Genuine substantive reviewer comment — must be stored.
        {
            'id': 'genuine-1',
            'author': 'coderabbitai',
            'thread_id': 'PRRT_9',
            'kind': 'inline',
            'body': 'This off-by-one in the slice bound drops the last element; use len(items).',
            'path': 'src/c.py',
            'line': 20,
            'resolved': False,
        },
    ]
    _patch_provider(monkeypatch, comments)

    result = _run_fetch(104, plan_id)
    assert result['status'] == 'success'
    # Only the genuine reviewer comment survives.
    assert result['count_stored'] == 1
    # The pipeline-authored trigger is noise...
    assert result['count_skipped_noise'] == 1
    # ...but the rate-limit notice is a REFUSAL, counted and attributed separately.
    # Collapsing it into count_skipped_noise is what hid a declined review.
    assert result['count_skipped_refusal'] == 1
    assert result['refused_bots'] == ['coderabbit']
    # Legitimate non-stores — no producer-mismatch Q-Gate false-positive.
    assert result['producer_mismatch_hash_id'] is None

    stored = query_findings(plan_id, finding_type='pr-comment')['findings']
    assert len(stored) == 1
    # The one stored finding is the genuine comment, not the trigger/notice.
    detail = stored[0].get('detail') or ''
    assert 'comment_id: genuine-1' in detail
    assert 'comment_id: trigger-1' not in detail
    assert 'comment_id: ratelimit-1' not in detail


# =============================================================================
# Self-authored response exclusion + loop bound (the non-terminating barrier loop)
# =============================================================================
#
# ``post_responses`` transmits thread-less dispositions as a NEW PR-level comment.
# On the next fetch that comment is unresolved, is not a refusal, matches no
# ``ignore`` regex, and carries a NEW comment_id the ``(bot_kind, comment_id)``
# dedup cannot know — so before the fix it was filed as a fresh pending finding,
# the pre-merge barrier blocked on it, triage responded again, and the cycle never
# terminated.
#
# The self-response bodies below are produced by the REAL emitter
# (``_build_batched_response_body``) rather than a hand-written literal. That is
# deliberate: it makes the test prove the recognizer matches what the emitter
# actually emits, so a future rename of the heading cannot leave a green test
# while silently reopening the loop.


def _self_response_body(comment_id='c1', reply='Fixed in the follow-up commit; see the updated guard.'):
    """Render a real ``post_responses`` batched body via the production emitter."""
    return github_pr._build_batched_response_body([(comment_id, reply)])


def test_self_authored_response_excluded_and_counted_separately(plan_context, monkeypatch):
    """Our own batched response is excluded, counted apart from noise, and files no finding.

    This is the loop-closing property: the comment ``post_responses`` posted must
    not come back as a fresh pending ``pr-comment`` finding. It is counted in
    ``count_skipped_self_response`` — NOT ``count_skipped_noise``, because our own
    transmitted output is not acknowledgment noise — and it is subtracted from
    ``expected_stored`` so a correctly-excluded self response never trips the
    ``(producer-mismatch)`` Q-Gate.
    """
    plan_id = 'gh-pr-self-response-excluded'
    comments = [
        # The batched disposition comment this workflow itself posted, authored by
        # the repo-owner account (bot_kind None) with kind issue_comment — exactly
        # the shape every other pre-filter stage misses.
        {
            'id': 'self-1',
            'author': 'oliver',
            'thread_id': '',
            'kind': 'issue_comment',
            'body': _self_response_body(),
            'resolved': False,
        },
        # A genuine reviewer comment on the same fetch — the exclusion must be
        # surgical, not a blanket drop of everything on the PR.
        {
            'id': 'genuine-1',
            'author': 'coderabbitai',
            'thread_id': 'PRRT_7',
            'kind': 'inline',
            'body': 'This slice bound drops the final element; use len(items) instead.',
            'path': 'src/e.py',
            'line': 12,
            'resolved': False,
        },
    ]
    _patch_provider(monkeypatch, comments)

    result = _run_fetch(105, plan_id)
    assert result['status'] == 'success'
    # Only the genuine reviewer comment is filed.
    assert result['count_stored'] == 1
    # Counted as a self response...
    assert result['count_skipped_self_response'] == 1
    # ...and NOT folded into the noise count (the counters are deliberately split).
    assert result['count_skipped_noise'] == 0
    # expected_stored accounts for the new counter — no producer-mismatch false-positive.
    assert result['producer_mismatch_hash_id'] is None
    # One self response is far below the bound, so no loop is reported.
    assert result['self_response_loop_detected'] is False

    stored = query_findings(plan_id, finding_type='pr-comment')['findings']
    assert len(stored) == 1
    detail = stored[0].get('detail') or ''
    assert 'comment_id: genuine-1' in detail
    assert 'comment_id: self-1' not in detail


def test_human_comment_quoting_the_disposition_heading_is_still_stored(plan_context, monkeypatch):
    """The false-positive boundary: quoting the heading is feedback, not our output.

    The recognizer is START-ANCHORED, never a substring search. A reviewer who
    blockquotes the disposition heading while disputing it, or who mentions it
    mid-sentence, is giving real feedback — dropping either would silently destroy
    review signal, which is a strictly worse failure than the loop the exclusion
    closes.
    """
    plan_id = 'gh-pr-self-response-boundary'
    comments = [
        # (a) Blockquoted heading — the body starts with '>', not with the heading.
        {
            'id': 'quote-1',
            'author': 'alice',
            'thread_id': '',
            'kind': 'issue_comment',
            'body': (
                '> ## Triage dispositions\n'
                '>\n'
                'This disposition is wrong: the guard still misses the empty-thread case.'
            ),
            'resolved': False,
        },
        # (b) Heading mentioned inside prose — never at the start of the body.
        {
            'id': 'quote-2',
            'author': 'alice',
            'thread_id': '',
            'kind': 'issue_comment',
            'body': 'The ## Triage dispositions comment above skipped my second point entirely.',
            'resolved': False,
        },
    ]
    _patch_provider(monkeypatch, comments)

    result = _run_fetch(106, plan_id)
    assert result['status'] == 'success'
    # Both human comments survive — neither is mistaken for our own output.
    assert result['count_stored'] == 2
    assert result['count_skipped_self_response'] == 0
    assert result['producer_mismatch_hash_id'] is None

    stored = query_findings(plan_id, finding_type='pr-comment')['findings']
    details = ' '.join(f.get('detail') or '' for f in stored)
    assert 'comment_id: quote-1' in details
    assert 'comment_id: quote-2' in details


def test_accumulated_self_responses_at_the_bound_report_the_loop(plan_context, monkeypatch):
    """At the bound the guard REPORTS exhaustion — it never passes silently.

    The filter alone cannot terminate every cycle (a thread-bearing disposition
    whose resolve-thread failed leaves an unresolved reply carrying no
    transmission shape at all), so a bound backs it. Every turn leaves one
    permanent response comment on the PR, which makes the PR's own comment list
    the iteration counter — no new state store, no new config key.
    """
    plan_id = 'gh-pr-self-response-bound'
    comments = [
        {
            'id': f'self-{i}',
            'author': 'oliver',
            'thread_id': '',
            'kind': 'issue_comment',
            'body': _self_response_body(comment_id=f'c{i}'),
            'resolved': False,
        }
        for i in range(github_pr._SELF_RESPONSE_LOOP_BOUND)
    ]
    _patch_provider(monkeypatch, comments)

    result = _run_fetch(107, plan_id)
    # The fetch itself succeeded — the loop report travels as its own field.
    assert result['status'] == 'success'
    assert result['count_stored'] == 0
    assert result['count_skipped_self_response'] == github_pr._SELF_RESPONSE_LOOP_BOUND
    assert result['self_response_loop_detected'] is True
    # The exhaustion was actually FILED, not merely flagged on the return.
    assert result['self_response_loop_hash_id']
    assert 'self_response_loop_persist_failed' not in result
    # Every excluded self response is subtracted, so no mismatch false-positive.
    assert result['producer_mismatch_hash_id'] is None


# ---------------------------------------------------------------------------
# Current-cycle bound: history must not be read as an active loop
# ---------------------------------------------------------------------------
#
# ``cmd_fetch_findings`` fetches with ``unresolved_only=False``, so every fetch
# sees the PR's ENTIRE comment history. Comparing the cumulative
# ``count_skipped_self_response`` against the bound therefore counted
# already-converged cycles as evidence of a running one: any PR that completed
# three normal triage rounds tripped ``self_response_loop_detected`` on its next
# fetch — typically at pre-merge validation, long after every finding was
# resolved — and filed a spurious ``(self-response-loop)`` Q-Gate finding.
#
# The predicate is now the TRAILING run of self-responses. The two properties
# below are co-equal and both must hold: history no longer trips the bound, and a
# genuinely non-converging cycle still does.


def _at(second):
    """ISO-8601 ``created_at`` on a fixed day — only the relative order matters."""
    return f'2026-07-29T10:{second:02d}:00Z'


def _reviewer_comment(comment_id, created_at, body):
    """A substantive coderabbit inline comment — provider ``kind`` group 1."""
    return {
        'id': comment_id,
        'author': 'coderabbitai',
        'thread_id': f'PRRT_{comment_id}',
        'kind': 'inline',
        'body': body,
        'path': 'src/loop.py',
        'line': 7,
        'resolved': False,
        'created_at': created_at,
    }


def _self_comment(comment_id, created_at):
    """A real batched self-response — provider ``kind`` group 3 (``issue_comment``)."""
    return {
        'id': comment_id,
        'author': 'oliver',
        'thread_id': '',
        'kind': 'issue_comment',
        'body': _self_response_body(comment_id=comment_id),
        'resolved': False,
        'created_at': created_at,
    }


def test_converged_history_at_the_bound_does_not_report_a_loop(plan_context, monkeypatch):
    """Three ALREADY-CONVERGED cycles must not be read as one non-converging cycle.

    The PR below completed three ordinary triage rounds: each reviewer comment was
    answered once, and the reviewer came back with fresh feedback afterwards. Its
    lifetime self-response total therefore equals ``_SELF_RESPONSE_LOOP_BOUND``,
    which is exactly what the cumulative predicate mistook for a live loop. The
    current cycle is one turn deep, so no loop is reported.

    The comment list is built in the order the provider actually returns it —
    GROUPED BY KIND (all ``inline`` threads, then all ``issue_comment`` bodies),
    NOT chronologically. That grouping is why this test is load-bearing rather than
    cosmetic: self-responses are always ``issue_comment``, so they occupy the tail
    of the raw list no matter when they were written. A trailing-run scan over the
    list AS RECEIVED would count all three and re-report the very false positive
    this test pins. Only the ``created_at`` sort recovers the real interleaving.
    """
    plan_id = 'gh-pr-self-response-converged-history'
    comments = [
        # Provider group 1 — inline reviewer comments, oldest first.
        _reviewer_comment('rev-1', _at(1), 'The retry bound is off by one here.'),
        _reviewer_comment('rev-2', _at(3), 'This branch swallows the decode error silently.'),
        _reviewer_comment('rev-3', _at(5), 'Prefer an explicit timeout over the implicit default.'),
        # Provider group 3 — our batched responses, each answering the reviewer
        # comment immediately above it in TIME, though they land last in the list.
        _self_comment('self-1', _at(2)),
        _self_comment('self-2', _at(4)),
        _self_comment('self-3', _at(6)),
    ]
    _patch_provider(monkeypatch, comments)

    result = _run_fetch(108, plan_id)
    assert result['status'] == 'success'
    # The lifetime total is exactly the bound — the figure the old predicate read.
    assert result['count_skipped_self_response'] == github_pr._SELF_RESPONSE_LOOP_BOUND
    # ...but only the newest response belongs to the current cycle.
    assert result['count_self_response_current_cycle'] == 1
    # So no loop is reported, and none is FILED.
    assert result['self_response_loop_detected'] is False
    assert result['self_response_loop_hash_id'] is None
    # The reviewer comments are still ingested normally.
    assert result['count_stored'] == 3
    assert result['producer_mismatch_hash_id'] is None


def test_unbroken_self_response_run_still_reports_the_loop(plan_context, monkeypatch):
    """The termination guarantee survives: a genuinely stuck cycle is still caught.

    Narrowing the predicate must not blunt it. Here one reviewer comment is
    followed by three self-responses with NOBODY else speaking in between — which
    is precisely what a non-converging respond → re-fetch cycle looks like. The run
    reaches the bound and the exhaustion is filed as a Q-Gate finding for an
    operator decision.
    """
    plan_id = 'gh-pr-self-response-live-loop'
    comments = [
        _reviewer_comment('rev-1', _at(1), 'This disposition does not address the null path.'),
        _self_comment('self-1', _at(2)),
        _self_comment('self-2', _at(3)),
        _self_comment('self-3', _at(4)),
    ]
    _patch_provider(monkeypatch, comments)

    result = _run_fetch(109, plan_id)
    assert result['status'] == 'success'
    assert result['count_self_response_current_cycle'] == github_pr._SELF_RESPONSE_LOOP_BOUND
    assert result['self_response_loop_detected'] is True
    # Reported, not merely flagged — the finding actually persisted.
    assert result['self_response_loop_hash_id']
    assert 'self_response_loop_persist_failed' not in result
    assert result['producer_mismatch_hash_id'] is None


def test_interleaved_pipeline_triggers_do_not_reset_the_run(plan_context, monkeypatch):
    """The pipeline cannot reset its own guard by posting re-review triggers.

    A registered re-review trigger is pipeline-authored output, exactly like the
    self-responses it sits between — it is not somebody else engaging with the PR.
    If it broke the run, the pipeline could cycle trigger → response → trigger →
    response indefinitely and never reach the bound, masking the exact loop class
    the bound exists to terminate. Triggers are therefore transparent: they neither
    count toward the run nor break it.
    """
    plan_id = 'gh-pr-self-response-trigger-interleave'
    trigger = {
        'author': 'oliver',
        'thread_id': '',
        'kind': 'issue_comment',
        'body': '@coderabbitai review',
        'resolved': False,
    }
    comments = [
        _reviewer_comment('rev-1', _at(1), 'The guard still misses the empty-thread case.'),
        _self_comment('self-1', _at(2)),
        {**trigger, 'id': 'trigger-1', 'created_at': _at(3)},
        _self_comment('self-2', _at(4)),
        {**trigger, 'id': 'trigger-2', 'created_at': _at(5)},
        _self_comment('self-3', _at(6)),
    ]
    _patch_provider(monkeypatch, comments)

    result = _run_fetch(110, plan_id)
    assert result['status'] == 'success'
    # Three responses in the run; the two triggers between them are transparent.
    assert result['count_self_response_current_cycle'] == github_pr._SELF_RESPONSE_LOOP_BOUND
    assert result['self_response_loop_detected'] is True
    assert result['self_response_loop_hash_id']
    # The triggers are still dropped as pipeline noise, and the accounting balances.
    assert result['count_skipped_noise'] == 2
    assert result['count_stored'] == 1
    assert result['producer_mismatch_hash_id'] is None


def test_reviewer_comment_after_a_stuck_run_reopens_the_cycle(plan_context, monkeypatch):
    """Fresh reviewer activity breaks the run — the next response starts a new cycle.

    The mirror of the trigger case: a reviewer comment is somebody OTHER than this
    pipeline speaking, so the cycle it interrupts has converged by definition.
    Three self-responses that would have reached the bound are cut off by the
    reviewer's reply, leaving a one-turn current cycle.
    """
    plan_id = 'gh-pr-self-response-reopened'
    comments = [
        _self_comment('self-1', _at(1)),
        _self_comment('self-2', _at(2)),
        _self_comment('self-3', _at(3)),
        # The reviewer comes back — everything before this belongs to a closed cycle.
        _reviewer_comment('rev-1', _at(4), 'Reopening: the second disposition regressed the retry path.'),
        _self_comment('self-4', _at(5)),
    ]
    _patch_provider(monkeypatch, comments)

    result = _run_fetch(111, plan_id)
    assert result['status'] == 'success'
    assert result['count_skipped_self_response'] == 4
    assert result['count_self_response_current_cycle'] == 1
    assert result['self_response_loop_detected'] is False
    assert result['self_response_loop_hash_id'] is None
    assert result['count_stored'] == 1


# =============================================================================
# Bot-agnostic rate-limit / service-notice recognizer (github_pr._is_refusal_notice)
# =============================================================================
#
# Exercised with NO bot_kind, which is exactly the structural last-resort layer of
# the refusal seam (an unregistered / renamed bot, or a phrasing not yet filed in
# the registry): with no bot_kind there is no registry data layer to consult, so a
# match here is a match by structural signature alone.
#
# Both directions are covered per bot shape. The false-negative direction — a
# genuine reviewer comment that merely MENTIONS a rate limit must NOT be
# misclassified — is the real hazard, so it is asserted per bot shape alongside
# the recognized cases.

# Rate-limit / service notices from three distinct bot shapes. Each carries a
# LIMIT-EXCEEDED statement (notice-voiced "exceeded" / "reached" / "hit") paired
# with a NOTICE shape (callout / limit-heading / service tail) — the two-part
# structural signature, with no author-specific literal.
_RATE_LIMIT_NOTICES = {
    # CodeRabbit: ``## Rate limit exceeded`` callout + body sentence.
    'coderabbit': (
        '> [!WARNING]\n'
        '> ## Rate limit exceeded\n'
        '>\n'
        '> @oliver has exceeded the limit for the number of files or commits '
        'that can be reviewed per hour.'
    ),
    # Sourcery: a weekly-review-limit note in a callout, "reached your ... limit".
    'sourcery': (
        '> [!NOTE]\n'
        '> Sourcery has reached your weekly review limit. '
        'Reviews will resume next Monday.'
    ),
    # Arbitrary unknown/renamed bot: a limit heading + "hit the ... rate limit"
    # + a "try again" service tail. No code names this bot.
    'unknown': (
        '> [!IMPORTANT]\n'
        '> ## API request limit reached\n'
        '>\n'
        '> This bot has hit the hourly rate limit and will try again in 60 minutes.'
    ),
}

# Genuine reviewer comments — per bot shape — that MENTION a rate limit in prose
# but are actionable feedback, not a service notice. Every one uses review-voiced
# phrasing ("exceeds" / "can exceed" / "does not exceed") rather than the
# notice-voiced past tense the recognizer keys on, so none may be dropped.
_GENUINE_RATE_LIMIT_MENTIONS = {
    # Plain inline comment, no notice structure at all.
    'coderabbit': (
        'This off-by-one in the slice bound drops the last element; use len(items).'
    ),
    # Mentions a rate limit in prose, no notice structure.
    'sourcery': (
        'Consider adding a retry with backoff here in case the API rate limit is '
        'exceeded under load — a bare call will fail hard.'
    ),
    # Has a markdown heading AND mentions the rate limit, but the heading is not
    # the limit phrase and the verb is modal ("does not exceed") — review voice.
    'unknown': (
        '## Suggestion\n'
        'Guard this call with a token bucket so it does not exceed the provider '
        'rate limit; add exponential backoff on 429s.'
    ),
    # A genuine comment inside a callout that discusses the rate limit — the
    # ungated recognizer must still not drop it (no limit-EXCEEDED statement).
    'callout': (
        '> [!WARNING]\n'
        '> This endpoint can exceed the provider rate limit under sustained load; '
        'add caching before the next release.'
    ),
}


@pytest.mark.parametrize('shape', sorted(_RATE_LIMIT_NOTICES))
def test_refusal_notice_recognizes_every_bot_shape(shape):
    """A rate-limit / service notice from any bot shape is recognized as a refusal.

    CodeRabbit, Sourcery, and an arbitrary unknown/renamed bot's notice are each
    matched by the same structural signature — no author-specific literal, so
    adding a future bot needs no recognizer edit.
    """
    assert github_pr._is_refusal_notice(_RATE_LIMIT_NOTICES[shape]) is True


@pytest.mark.parametrize('shape', sorted(_GENUINE_RATE_LIMIT_MENTIONS))
def test_refusal_notice_keeps_genuine_rate_limit_mentions(shape):
    """A genuine reviewer comment that merely mentions a rate limit is NOT a refusal.

    The false-negative direction is the real hazard: review-voiced phrasing
    ("exceeds" / "can exceed" / "does not exceed"), with or without a heading or
    callout, must survive the recognizer's two-part precision (a limit-EXCEEDED
    statement AND a notice shape are BOTH required).
    """
    assert github_pr._is_refusal_notice(_GENUINE_RATE_LIMIT_MENTIONS[shape]) is False


def test_refusal_notice_empty_body_is_not_a_refusal():
    """An empty body is not a refusal (the recognizer returns False)."""
    assert github_pr._is_refusal_notice('') is False


def test_fetch_findings_surfaces_rate_limit_refusals_bot_agnostically(plan_context, monkeypatch):
    """fetch_findings SURFACES rate-limit refusals from every bot — including an unknown one.

    Over a mixed set carrying a rate-limit notice AND a genuine comment from each
    of CodeRabbit, Sourcery, and an unregistered ``randombot[bot]`` (bot_kind
    resolves to None), only the three genuine comments are stored — a refusal is
    never handed to the operator as an actionable ``pr-comment`` finding, because it
    is a signal ABOUT the review, not feedback about the code.

    But the three notices are **refusals, not noise**: they are counted in
    ``count_skipped_refusal`` and the two ATTRIBUTABLE ones name their bot in
    ``refused_bots``, so the completeness / quorum layer sees a declined review
    rather than inferring absence from silence. The unknown bot's notice being
    recognized at all proves the recognizer is author-ungated (no resolved
    ``bot_kind`` is required); it cannot be attributed, so it contributes to the
    count without naming a bot. No ``(producer-mismatch)`` Q-Gate fires on the
    legitimate non-stores.
    """
    plan_id = 'gh-pr-rate-limit-bot-agnostic'
    comments = [
        {
            'id': 'cr-notice',
            'author': 'coderabbitai',
            'thread_id': '',
            'kind': 'review_body',
            'body': _RATE_LIMIT_NOTICES['coderabbit'],
            'resolved': False,
        },
        {
            'id': 'cr-genuine',
            'author': 'coderabbitai',
            'thread_id': 'PRRT_A',
            'kind': 'inline',
            'body': _GENUINE_RATE_LIMIT_MENTIONS['coderabbit'],
            'path': 'src/a.py',
            'line': 3,
            'resolved': False,
        },
        {
            'id': 'sr-notice',
            'author': 'sourcery-ai',
            'thread_id': '',
            'kind': 'review_body',
            'body': _RATE_LIMIT_NOTICES['sourcery'],
            'resolved': False,
        },
        {
            'id': 'sr-genuine',
            'author': 'sourcery-ai',
            'thread_id': 'PRRT_B',
            'kind': 'inline',
            'body': _GENUINE_RATE_LIMIT_MENTIONS['sourcery'],
            'path': 'src/b.py',
            'line': 7,
            'resolved': False,
        },
        {
            'id': 'unk-notice',
            'author': 'randombot[bot]',
            'thread_id': '',
            'kind': 'review_body',
            'body': _RATE_LIMIT_NOTICES['unknown'],
            'resolved': False,
        },
        {
            'id': 'unk-genuine',
            'author': 'randombot[bot]',
            'thread_id': 'PRRT_C',
            'kind': 'inline',
            'body': 'Rename this helper; the current name shadows the stdlib module.',
            'path': 'src/c.py',
            'line': 9,
            'resolved': False,
        },
    ]
    _patch_provider(monkeypatch, comments)

    result = _run_fetch(105, plan_id)
    assert result['status'] == 'success'
    # Three genuine comments stored; three rate-limit notices recognized as refusals.
    assert result['count_stored'] == 3
    assert result['count_skipped_refusal'] == 3
    # NONE of them is noise — that conflation is the defect this pins.
    assert result['count_skipped_noise'] == 0
    # Only the two notices whose author resolves to a registered bot are attributable.
    assert result['refused_bots'] == ['coderabbit', 'sourcery']
    # Participation is unaffected by the refusal it also posted: CodeRabbit's
    # genuine inline comment is one of its declared publish shapes, so positive
    # diff-derived evidence still outranks the refusal observation. Sourcery's
    # genuine comment is `inline`, which is NOT its declared shape (`review_body`),
    # so it is not credited — the evidence-typed contract, not a refusal effect.
    assert result['participated_bots'] == [{'bot_kind': 'coderabbit', 'evidence_kind': 'inline'}]
    assert result['producer_mismatch_hash_id'] is None

    stored = query_findings(plan_id, finding_type='pr-comment')['findings']
    stored_ids = {
        _stored_comment_id(f) for f in stored
    }
    assert stored_ids == {'cr-genuine', 'sr-genuine', 'unk-genuine'}


def _stored_comment_id(finding):
    """Extract the ``comment_id`` value from a stored pr-comment finding's detail."""
    for detail_line in (finding.get('detail') or '').splitlines():
        if detail_line.startswith('comment_id:'):
            return detail_line.split(':', 1)[1].strip()
    return ''


def test_fetch_findings_splits_a_refusing_bot_from_a_participating_one(plan_context, monkeypatch):
    """A bot that only refused lands in ``refused_bots``, never in ``participated_bots``.

    This is the #1037 signature, pinned: over a set where CodeRabbit posts ONLY a
    rate-limit notice, Sourcery posts a genuine review comment in its declared
    publish shape, and a human comments, the producer must report the two bots
    DIFFERENTLY.

    The retired ``responded_bots`` field could not: it named every bot whose login
    appeared on any comment, so a bot that did nothing but decline was reported
    identically to one that reviewed. ``participated_bots`` is evidence-typed and
    excludes a refusal (a refusal is positive evidence the bot did NOT review, even
    though it is published in one of the bot's declared shapes), while
    ``refused_bots`` carries the refusal so the quorum layer can classify it as
    ``refused_awaitable`` / ``refused_hard``. The human author (``bot_kind`` None)
    appears in neither.
    """
    plan_id = 'gh-pr-refusal-vs-participation'
    comments = [
        # CodeRabbit posts ONLY a rate-limit notice — a refusal, not a review.
        {
            'id': 'cr-notice',
            'author': 'coderabbitai',
            'thread_id': '',
            'kind': 'review_body',
            'body': _RATE_LIMIT_NOTICES['coderabbit'],
            'resolved': False,
        },
        # Sourcery posts a genuine substantive review body — its declared publish
        # shape, so it is stored AND proves participation.
        {
            'id': 'sr-genuine',
            'author': 'sourcery-ai',
            'thread_id': '',
            'kind': 'review_body',
            'body': 'Extract this duplicated branch into a helper for clarity.',
            'resolved': False,
        },
        # Human comment — bot_kind None, in neither bot list.
        {
            'id': 'human-1',
            'author': 'alice',
            'thread_id': '',
            'kind': 'issue_comment',
            'body': 'Please add a regression test for this path.',
            'resolved': False,
        },
    ]
    _patch_provider(monkeypatch, comments)

    result = _run_fetch(106, plan_id)
    assert result['status'] == 'success'
    # Sourcery's review and the human comment are stored; the refusal files nothing.
    assert result['count_stored'] == 2
    assert result['count_skipped_refusal'] == 1
    assert result['count_skipped_noise'] == 0
    # The refusing bot is SURFACED, not silently absent.
    assert result['refused_bots'] == ['coderabbit']
    # ...and is NOT laundered into the participation set by its publish shape.
    assert result['participated_bots'] == [{'bot_kind': 'sourcery', 'evidence_kind': 'review_body'}]


# =============================================================================
# Unknown-bot contract — an unregistered login is FILED, never dropped
# =============================================================================


def test_unregistered_bot_login_is_filed_unattributed(plan_context, monkeypatch):
    """A comment from a login absent from the registry is filed, never dropped.

    The pipeline is fail-open by construction: ``bot_kind_for_author`` returns
    ``None`` for an unregistered login, so the comment degrades to the
    human-author path and is filed as a ``pr-comment`` finding with an empty
    ``bot_kind``. Its feedback still reaches triage, unattributed.

    This is the retirement-safety contract: a consumer project that still lists a
    retired bot, or a bot renamed upstream, loses ATTRIBUTION — it does not lose
    its review.
    """
    plan_id = 'gh-pr-unregistered-bot-filed'
    comments = [
        {
            'id': 'retired-1',
            'author': 'some-retired-bot',
            'thread_id': 'PRRT_R',
            'kind': 'inline',
            'body': 'This comparison uses == on floats; use math.isclose with a tolerance.',
            'path': 'src/r.py',
            'line': 4,
            'resolved': False,
        },
    ]
    _patch_provider(monkeypatch, comments)

    result = _run_fetch(107, plan_id)
    assert result['status'] == 'success'
    assert result['count_stored'] == 1

    stored = query_findings(plan_id, finding_type='pr-comment')['findings']
    assert len(stored) == 1
    # Filed, but unattributed — no bot_kind was resolvable.
    assert stored[0].get('bot_kind') in (None, '')
    # The unregistered author is NOT credited as a proven participant, and it did
    # not refuse — an unattributable login contributes to neither observation set.
    assert result['participated_bots'] == []
    assert result['refused_bots'] == []


def test_unregistered_bot_login_is_not_reported_unclassified(plan_context, monkeypatch):
    """An unattributable login is filed, and is NOT named as an unclassified bot.

    Classification is bot-scoped: the producer records an unclassified bot only
    when a ``bot_kind`` resolved. An unregistered login yields a falsy
    ``bot_kind``, so its comment is treated as human input — stored, and absent
    from ``unclassified_bots`` (which would otherwise report a nonexistent bot
    kind for the operator to classify).
    """
    plan_id = 'gh-pr-unregistered-bot-classification'
    comments = [
        {
            'id': 'retired-2',
            'author': 'some-retired-bot',
            'thread_id': 'PRRT_R2',
            'kind': 'inline',
            'body': 'The retry loop has no ceiling; a persistent 500 will spin forever.',
            'path': 'src/r.py',
            'line': 8,
            'resolved': False,
        },
    ]
    _patch_provider(monkeypatch, comments)

    result = _run_fetch_classified(108, plan_id, required_bots='coderabbit')
    assert result['status'] == 'success'
    assert result['count_stored'] == 1
    assert result['unclassified_bots'] == []

    stored = query_findings(plan_id, finding_type='pr-comment')['findings']
    assert len(stored) == 1
    assert stored[0].get('bot_kind') in (None, '')


# =============================================================================
# post_responses — three-way transmit disposition
# =============================================================================


def _stage_respondable(plan_id, *, comment_id, thread_id, resolution_detail, kind='review_body'):
    """Add a pr-comment finding already resolved by triage; return its ``hash_id``.

    ``resolution_detail`` of ``None`` stages a finding whose disposition carries
    no body — the ``skipped`` branch's input.

    ``kind`` is the finding's recorded publish shape and is LOAD-BEARING, because it
    is the routing predicate ``post_responses`` reads: a genuinely threadless kind
    (``review_body`` / ``issue_comment``) is the only admission into the batched
    PR-level comment, while a thread-bearing kind (``inline``) must reach the
    reviewer's own thread or be reported untransmitted. A test must therefore stage
    the kind its scenario is about — staging ``review_body`` for a thread-bearing
    scenario would silently assert the batch path under a thread-bearing name.
    """
    detail = f'comment_id: {comment_id}\nthread_id: {thread_id}\nkind: {kind}'
    add_result = _findings_core.add_finding(plan_id, 'pr-comment', f'Finding {comment_id}', detail)
    hash_id = add_result['hash_id']
    _findings_core.resolve_finding(plan_id, hash_id, 'accepted', detail=resolution_detail)
    return hash_id


def _run_post_responses(pr_number, plan_id):
    args = argparse.Namespace(pr_number=pr_number, plan_id=plan_id)
    return github_pr.cmd_post_responses(args)


class _PostSpy:
    """Records every ``post_pr_comment`` call and returns a fixed outcome."""

    def __init__(self, *, succeed=True):
        self.calls = []
        self._succeed = succeed

    def __call__(self, pr_number, body):
        self.calls.append((pr_number, body))
        if self._succeed:
            return {'status': 'success', 'operation': 'post_pr_comment', 'pr_number': pr_number}
        return {'status': 'error', 'operation': 'post_pr_comment', 'detail': 'gh rejected the comment'}


def test_post_responses_batches_thread_less_dispositions_into_one_comment(plan_context, monkeypatch):
    """Two thread-less dispositions are transmitted by exactly ONE batched PR comment.

    Batching is the contract, not an optimization: ``review_body`` findings from
    every bot are thread-less, so a per-finding comment would spam the PR. The
    single posted body must carry BOTH source ``comment_id``s so each disposition
    stays traceable to the comment it answers.
    """
    plan_id = 'gh-pr-respond-batched'
    hash_a = _stage_respondable(plan_id, comment_id='ca', thread_id='', resolution_detail='Accepted: covered by TASK-3.')
    hash_b = _stage_respondable(plan_id, comment_id='cb', thread_id='', resolution_detail='Accepted: out of scope here.')

    monkeypatch.setattr(github_pr._github, 'check_auth', lambda: (True, ''))
    spy = _PostSpy()
    monkeypatch.setattr(github_pr._github, 'post_pr_comment', spy)

    result = _run_post_responses(300, plan_id)

    # Exactly ONE post for two thread-less dispositions.
    assert len(spy.calls) == 1
    posted_pr, posted_body = spy.calls[0]
    assert posted_pr == 300
    assert 'ca' in posted_body
    assert 'cb' in posted_body
    assert 'Accepted: covered by TASK-3.' in posted_body
    assert 'Accepted: out of scope here.' in posted_body

    assert result['status'] == 'success'
    assert result['count_untransmitted'] == 0
    assert result['count_responded'] == 2
    by_hash = {entry['hash_id']: entry for entry in result['responded']}
    for hash_id in (hash_a, hash_b):
        assert by_hash[hash_id]['transmit_mode'] == 'batched_issue_comment'
        # No thread exists on this path — claiming a resolve would be a false signal.
        assert by_hash[hash_id]['resolved_on_provider'] is False


def test_post_responses_missing_resolution_detail_is_skipped_not_untransmitted(plan_context, monkeypatch):
    """A disposition with no body lands in ``skipped``, never in ``untransmitted``.

    The two buckets mean different things and must not be conflated: ``skipped``
    is "nothing to say" (honest), ``untransmitted`` is "had something to say and
    could not deliver it" (a real failure).
    """
    plan_id = 'gh-pr-respond-skipped'
    hash_id = _stage_respondable(plan_id, comment_id='cs', thread_id='', resolution_detail=None)

    monkeypatch.setattr(github_pr._github, 'check_auth', lambda: (True, ''))
    spy = _PostSpy()
    monkeypatch.setattr(github_pr._github, 'post_pr_comment', spy)

    result = _run_post_responses(301, plan_id)

    # Nothing to transmit, so nothing is posted.
    assert spy.calls == []
    assert result['status'] == 'success'
    assert result['count_skipped'] == 1
    assert result['count_untransmitted'] == 0
    assert result['skipped'] == [{'hash_id': hash_id, 'reason': 'no_resolution_detail'}]


def test_post_responses_batch_post_failure_untransmits_whole_batch(plan_context, monkeypatch):
    """When the single batched post fails, EVERY finding in it is reported untransmitted.

    This is the regression guard against a silently-dropped disposition: the
    envelope must report ``partial``, never an unconditional ``success``, and each
    lost disposition must be enumerated with a reason.
    """
    plan_id = 'gh-pr-respond-batch-fails'
    hash_a = _stage_respondable(plan_id, comment_id='fa', thread_id='', resolution_detail='Accepted: noted.')
    hash_b = _stage_respondable(plan_id, comment_id='fb', thread_id='', resolution_detail='Accepted: also noted.')

    monkeypatch.setattr(github_pr._github, 'check_auth', lambda: (True, ''))
    spy = _PostSpy(succeed=False)
    monkeypatch.setattr(github_pr._github, 'post_pr_comment', spy)

    result = _run_post_responses(302, plan_id)

    assert len(spy.calls) == 1
    assert result['status'] == 'partial'
    assert result['count_untransmitted'] == 2
    assert result['count_responded'] == 0
    untransmitted_hashes = {entry['hash_id'] for entry in result['untransmitted']}
    assert untransmitted_hashes == {hash_a, hash_b}
    for entry in result['untransmitted']:
        assert 'batched-comment post failed' in entry['reason']


def test_post_responses_all_thread_bearing_keeps_reply_then_resolve_sequence(plan_context, monkeypatch):
    """A thread-bearing finding still gets thread-reply THEN resolve, and reports success.

    The unchanged path must stay unchanged: two GraphQL mutations in that order,
    ``transmit_mode: thread_reply``, ``resolved_on_provider: true``, and no
    batched PR comment at all.
    """
    plan_id = 'gh-pr-respond-threaded'
    hash_id = _stage_respondable(
        plan_id, comment_id='ct', thread_id='PRRT_T', resolution_detail='Fixed in TASK-4.', kind='inline'
    )

    monkeypatch.setattr(github_pr._github, 'check_auth', lambda: (True, ''))
    spy = _PostSpy()
    monkeypatch.setattr(github_pr._github, 'post_pr_comment', spy)

    mutations = []

    def _run_graphql(query, variables):
        mutations.append((query, variables))
        return (0, {}, '')

    monkeypatch.setattr(github_pr._github, 'run_graphql', _run_graphql)

    result = _run_post_responses(303, plan_id)

    # No batched comment — the thread path handled it.
    assert spy.calls == []
    assert len(mutations) == 2
    assert mutations[0][0] == github_pr.THREAD_REPLY_MUTATION
    assert mutations[0][1] == {'threadId': 'PRRT_T', 'body': 'Fixed in TASK-4.'}
    assert mutations[1][0] == github_pr.RESOLVE_THREAD_MUTATION
    assert mutations[1][1] == {'threadId': 'PRRT_T'}

    assert result['status'] == 'success'
    assert result['count_untransmitted'] == 0
    assert result['responded'] == [
        {
            'hash_id': hash_id,
            'thread_id': 'PRRT_T',
            'transmit_mode': 'thread_reply',
            'resolved_on_provider': True,
        }
    ]


def test_post_responses_thread_reply_failure_is_untransmitted(plan_context, monkeypatch):
    """A failed thread-reply is an UNTRANSMITTED disposition, not a silent skip."""
    plan_id = 'gh-pr-respond-thread-fails'
    hash_id = _stage_respondable(
        plan_id, comment_id='cf', thread_id='PRRT_F', resolution_detail='Fixed in TASK-5.', kind='inline'
    )

    monkeypatch.setattr(github_pr._github, 'check_auth', lambda: (True, ''))
    monkeypatch.setattr(github_pr._github, 'run_graphql', lambda query, variables: (1, None, 'permission denied'))

    result = _run_post_responses(304, plan_id)

    assert result['status'] == 'partial'
    assert result['count_untransmitted'] == 1
    assert result['untransmitted'][0]['hash_id'] == hash_id
    assert 'thread-reply failed' in result['untransmitted'][0]['reason']


# =============================================================================
# bot_completion — per-bot check-run completion read
# =============================================================================


def _run_gh_returning(rc, stdout, stderr=''):
    """Return a ``run_gh`` stub yielding a fixed ``(rc, stdout, stderr)`` tuple."""

    def _run_gh(args, capture_json=False, timeout=60):
        return (rc, stdout, stderr)

    return _run_gh


def _checks_json(*checks):
    """Serialize ``(name, state, bucket)`` triples as the ``gh pr checks --json`` array."""
    return json.dumps([{'name': name, 'state': state, 'bucket': bucket} for name, state, bucket in checks])


def _run_bot_completion(pr_number, bot_kind):
    args = argparse.Namespace(pr_number=pr_number, bot_kind=bot_kind)
    return github_pr.cmd_bot_completion(args)


def test_bot_completion_slow_bot_in_progress_then_completed(monkeypatch):
    """A slow bot reports in_progress on the first poll and completed on the next.

    ``bot_completion`` resolves coderabbit's registry ``completion_check_name``
    (``'CodeRabbit'``), finds that check on the PR HEAD, and reports its state:
    an IN_PROGRESS check yields ``in_progress=True`` / ``completed=False``; once
    the same check concludes SUCCESS a follow-up poll yields ``completed=True``.
    """
    monkeypatch.setattr(github_pr._github, 'check_auth', lambda: (True, ''))

    # Poll 1 — the CodeRabbit check is still running.
    monkeypatch.setattr(
        github_pr._github,
        'run_gh',
        _run_gh_returning(0, _checks_json(('CodeRabbit', 'IN_PROGRESS', 'pending'))),
    )
    first = _run_bot_completion(200, 'coderabbit')
    assert first['check_name'] == 'CodeRabbit'
    assert first['in_progress'] is True
    assert first['completed'] is False

    # Poll 2 — the same check has concluded SUCCESS.
    monkeypatch.setattr(
        github_pr._github,
        'run_gh',
        _run_gh_returning(0, _checks_json(('CodeRabbit', 'SUCCESS', 'pass'))),
    )
    second = _run_bot_completion(200, 'coderabbit')
    assert second['in_progress'] is False
    assert second['completed'] is True


def test_bot_completion_no_check_name_for_markerless_bot(monkeypatch):
    """A bot with no registry completion_check_name reports ``no_check_name``.

    Sourcery declares an empty ``completion_check_name``, so ``bot_completion``
    short-circuits to ``no_check_name`` with both flags false — the caller falls
    back to the ``review_bot_buffer_seconds`` wait — without ever querying gh.
    """
    monkeypatch.setattr(github_pr._github, 'check_auth', lambda: (True, ''))

    result = _run_bot_completion(200, 'sourcery')
    assert result['status'] == 'no_check_name'
    assert result['in_progress'] is False
    assert result['completed'] is False


def test_bot_completion_check_absent_yields_not_found(monkeypatch):
    """A completion check not yet posted on the PR yields ``not_found`` (keep polling)."""
    monkeypatch.setattr(github_pr._github, 'check_auth', lambda: (True, ''))
    monkeypatch.setattr(
        github_pr._github,
        'run_gh',
        _run_gh_returning(0, _checks_json(('verify', 'SUCCESS', 'pass'))),
    )

    result = _run_bot_completion(200, 'coderabbit')
    assert result['status'] == 'not_found'
    assert result['in_progress'] is False
    assert result['completed'] is False


def test_bot_completion_no_checks_at_all_yields_not_found(monkeypatch):
    """Empty gh output (PR has no checks) resolves to ``not_found``, not an error."""
    monkeypatch.setattr(github_pr._github, 'check_auth', lambda: (True, ''))
    monkeypatch.setattr(github_pr._github, 'run_gh', _run_gh_returning(1, '', 'no checks reported'))

    result = _run_bot_completion(200, 'coderabbit')
    assert result['status'] == 'not_found'
    assert result['completed'] is False


def test_bot_completion_unconfigured_fails_loud(monkeypatch):
    """When GitHub is not authenticated, ``bot_completion`` fails loud (never a silent no-op)."""
    monkeypatch.setattr(github_pr._github, 'check_auth', lambda: (False, 'Not authenticated'))

    result = _run_bot_completion(200, 'coderabbit')
    assert result['status'] == 'unconfigured'


# =============================================================================
# Rejected producer-mismatch persist (P5) — FIELD_ONLY loudness
# =============================================================================
#
# The producer-mismatch finding exists to report that findings were lost. When
# its OWN persist is rejected, the loss must surface on the returned dict — but
# the enclosing ``status`` stays truthful about the fetch, which did succeed.

# A comment whose ``kind`` is outside PR_COMMENT_KINDS, so the real ``add_finding``
# validator rejects it and the producer-mismatch guard fires for real.
_BAD_KIND_COMMENT = {
    'id': 'cbad',
    'author': 'coderabbitai',
    'thread_id': 'PRRT_BAD',
    'kind': 'not-a-comment-kind',
    'body': 'This comment cannot be stored because its kind is invalid.',
    'path': 'src/z.py',
    'line': 3,
    'resolved': False,
}


def test_rejected_mismatch_persist_surfaces_field_without_flipping_status(plan_context, monkeypatch):
    """A rejected mismatch persist sets qgate_persist_failed and leaves status success.

    Driven by the real validator: ``pr-comment`` is removed from the live
    ``FINDING_TYPES``, so both the per-comment stores AND the mismatch finding
    are rejected by ``_findings_core`` itself — no synthetic persist mock. The
    patch targets the LIVE module object (see ``_live_findings_core``), because
    that is the one ``cmd_fetch_findings`` imports at call time.
    """
    plan_id = 'gh-pr-persist-reject'
    _patch_provider(monkeypatch, _COMMENTS)
    live_core = _live_findings_core()
    monkeypatch.setattr(
        live_core,
        'FINDING_TYPES',
        tuple(t for t in live_core.FINDING_TYPES if t != 'pr-comment'),
    )

    result = _run_fetch(105, plan_id)

    # FIELD_ONLY loudness: the fetch itself succeeded, so its status is unchanged.
    assert result['status'] == 'success'
    assert result['count_fetched'] == len(_COMMENTS)
    assert result['count_stored'] == 0
    # The lost mismatch finding travels as a first-class field, never as a
    # ``producer_mismatch_hash_id`` a caller could read as "filed".
    assert result['qgate_persist_failed'] is True
    assert result['producer_mismatch_hash_id'] is None
    failure = result['qgate_persist_failure']
    assert '(producer-mismatch)' in failure['title']
    assert 'count_stored=0' in failure['detail']
    assert 'Invalid finding type' in failure['message']


def test_deduplicated_mismatch_persist_stays_benign(plan_context, monkeypatch):
    """A ``deduplicated`` mismatch persist is benign — it never reads as a rejection.

    The same unstorable comment is fetched twice, so the second run re-detects an
    identical mismatch and the primitive dedups it. The record is in the store,
    so the result reports a hash id and no persist failure.
    """
    plan_id = 'gh-pr-persist-dedup'
    _patch_provider(monkeypatch, [_BAD_KIND_COMMENT])

    first = _run_fetch(106, plan_id)
    assert first['status'] == 'success'
    assert first['count_stored'] == 0
    assert first['producer_mismatch_hash_id']
    assert 'qgate_persist_failed' not in first

    second = _run_fetch(106, plan_id)

    assert second['status'] == 'success'
    assert 'qgate_persist_failed' not in second
    # Dedup returns the SAME record — still in the store, so still a hash id.
    assert second['producer_mismatch_hash_id'] == first['producer_mismatch_hash_id']

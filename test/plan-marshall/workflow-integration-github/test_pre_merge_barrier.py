#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Fixture-accurate provider tests for the D1 pre-merge comment-completeness barrier.

The barrier re-runs the ``github_pr fetch_findings`` producer immediately before
merge/enqueue and then queries pending ``pr-comment`` findings; any pending
finding blocks the merge. These tests exercise the two barrier-critical producer
properties end-to-end against the REAL findings store (isolated via the autouse
``plan_context`` PLAN_BASE_DIR sandbox), monkeypatching only the GitHub provider
surface (``check_auth``, ``fetch_pr_comments_data``, ``fetch_pr_head_sha``):

    (a) late-comment-after-triage — a comment posted after the prior fetch is
        filed as a NEW pending pr-comment finding on the re-fetch (the
        ``(bot_kind, comment_id)`` dedup does not suppress a genuinely-new
        comment), so the barrier's pending query is non-empty and blocks.
    (b) clean-path — a re-fetch whose comments were all already stored files
        zero new findings, so the barrier query is empty and the merge proceeds.

Per lesson 2026-07-09-14-001 the provider response is built from a real fixture
shape (mirroring ``test_github_pr.py``), so a green fixture cannot diverge from
production provider behaviour.
"""

import argparse

from conftest import load_script_module

github_pr = load_script_module('plan-marshall', 'workflow-integration-github', 'github_pr.py', 'github_pr')
_findings_core = load_script_module('plan-marshall', 'manage-findings', '_findings_core.py', '_findings_core')

query_findings = _findings_core.query_findings
resolve_finding = _findings_core.resolve_finding


# Initial bot-review comment set fetched during the automatic-review pass —
# coderabbit (thread-bearing inline) + sourcery (thread_id-less review_body).
# Bodies are substantive so neither is dropped by the ``_is_obvious_noise``
# pre-filter.
_INITIAL_COMMENTS = [
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
]

# A late review comment that lands AFTER the automatic-review pass marked the
# step done — a distinct ``comment_id`` from a bot author, so it is genuinely new
# and must not be deduped against the already-stored comments.
_LATE_COMMENT = {
    'id': 'c-late',
    'author': 'coderabbitai',
    'thread_id': 'PRRT_9',
    'kind': 'inline',
    'body': 'This newly-pushed branch introduces an off-by-one in the loop bound.',
    'path': 'src/c.py',
    'line': 42,
    'resolved': False,
}


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


def _pending(plan_id):
    """The pending pr-comment findings — the exact set the barrier query returns."""
    return [
        f
        for f in query_findings(plan_id, finding_type='pr-comment')['findings']
        if f.get('resolution') == 'pending'
    ]


def _resolve_all_pending(plan_id):
    """Simulate the triage pass resolving every fetched comment (bot handled)."""
    for f in query_findings(plan_id, finding_type='pr-comment')['findings']:
        if f.get('resolution') == 'pending':
            resolve_finding(plan_id, f['hash_id'], 'fixed')


def test_late_comment_after_triage_surfaces_pending_finding(plan_context, monkeypatch):
    """A comment posted after triage is re-fetched as a NEW pending finding.

    The initial pass fetches and triages (resolves) the bot comments; a late
    comment then lands. The barrier's re-fetch files ONLY the genuinely-new
    comment as a fresh pending finding (the already-stored resolved comments
    dedupe on ``(bot_kind, comment_id)``), so the barrier's pending query is
    non-empty and the merge is blocked.
    """
    plan_id = 'barrier-late-comment'

    _patch_provider(monkeypatch, _INITIAL_COMMENTS)
    first = _run_fetch(202, plan_id)
    assert first['status'] == 'success'
    assert first['count_stored'] == len(_INITIAL_COMMENTS)

    # Triage handled every comment — the store has no pending findings left.
    _resolve_all_pending(plan_id)
    assert _pending(plan_id) == []

    # A late comment lands; the barrier re-fetches with it now present.
    _patch_provider(monkeypatch, [*_INITIAL_COMMENTS, _LATE_COMMENT])
    second = _run_fetch(202, plan_id)
    assert second['status'] == 'success'
    # Only the genuinely-new comment is stored; the already-stored ones dedupe.
    assert second['count_stored'] == 1
    assert second['count_skipped_duplicate'] == len(_INITIAL_COMMENTS)
    assert second['producer_mismatch_hash_id'] is None

    # The barrier's pending query is now non-empty — exactly the late comment.
    pending = _pending(plan_id)
    assert len(pending) == 1
    assert 'comment_id: c-late' in (pending[0].get('detail') or '')


def test_clean_path_no_new_comments_leaves_barrier_empty(plan_context, monkeypatch):
    """A re-fetch with no new comments files zero findings — the barrier passes.

    Every comment was already stored and resolved during the automatic-review
    pass; the barrier's re-fetch dedupes all of them, adds zero dispatches, and
    the pending query stays empty so the merge proceeds.
    """
    plan_id = 'barrier-clean-path'

    _patch_provider(monkeypatch, _INITIAL_COMMENTS)
    first = _run_fetch(203, plan_id)
    assert first['status'] == 'success'
    assert first['count_stored'] == len(_INITIAL_COMMENTS)

    _resolve_all_pending(plan_id)

    # Barrier re-fetch: identical comments, all already stored.
    second = _run_fetch(203, plan_id)
    assert second['status'] == 'success'
    assert second['count_stored'] == 0
    assert second['count_skipped_duplicate'] == len(_INITIAL_COMMENTS)
    assert second['producer_mismatch_hash_id'] is None

    # Barrier query empty → merge proceeds.
    assert _pending(plan_id) == []

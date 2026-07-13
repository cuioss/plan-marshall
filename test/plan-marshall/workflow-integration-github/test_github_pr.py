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

from conftest import load_script_module

github_pr = load_script_module('plan-marshall', 'workflow-integration-github', 'github_pr.py', 'github_pr')
_findings_core = load_script_module('plan-marshall', 'manage-findings', '_findings_core.py', '_findings_core')

query_findings = _findings_core.query_findings


# Mixed-bot, mixed-thread comment set: coderabbit (thread-bearing), sourcery
# (thread_id-less review_body), gemini (thread-bearing), and a human
# (thread_id-less issue comment). Bodies are substantive so none is dropped by
# the ``_is_obvious_noise`` pre-filter.
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
        'author': 'gemini-code-assist',
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


def test_second_fetch_dedupes_all_bot_kinds(plan_context, monkeypatch):
    """A re-fetch of an already-staged PR stores zero new findings for every bot kind.

    Thread-bearing (coderabbit/gemini) AND thread_id-less (sourcery/human)
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


def _run_fetch_enabled(pr_number, plan_id, enabled_bots):
    """Invoke ``cmd_fetch_findings`` with an explicit ``--enabled-bots`` value.

    ``enabled_bots`` is the raw comma-joined flag value (``'coderabbit'``,
    ``'coderabbit,sourcery'``, or ``''`` to disable every bot). Passing the
    attribute at all switches the producer filter on; the sibling ``_run_fetch``
    omits it so the filter stays disabled there.
    """
    args = argparse.Namespace(pr_number=pr_number, plan_id=plan_id, enabled_bots=enabled_bots)
    return github_pr.cmd_fetch_findings(args)


def test_enabled_bots_filters_disabled_bot_comments(plan_context, monkeypatch):
    """``--enabled-bots "coderabbit"`` files no sourcery/gemini findings.

    Over the mixed-bot comment set, only the coderabbit comment (enabled) and
    the human comment (``bot_kind`` None, never filtered — the gate is
    bot-scoped) are stored; the sourcery (``review_body``) and gemini
    (``inline``) comments are skipped as disabled bots. The disabled skips are
    legitimate non-stores, so no producer-mismatch Q-Gate fires.
    """
    plan_id = 'gh-pr-enabled-bots-coderabbit'
    _patch_provider(monkeypatch, _COMMENTS)

    result = _run_fetch_enabled(101, plan_id, 'coderabbit')
    assert result['status'] == 'success'
    # coderabbit (c1) + human (c4) survive; sourcery (c2) + gemini (c3) disabled.
    assert result['count_stored'] == 2
    assert result['count_skipped_disabled'] == 2
    assert result['producer_mismatch_hash_id'] is None

    stored = query_findings(plan_id, finding_type='pr-comment')['findings']
    bot_kinds = {f.get('bot_kind') for f in stored}
    assert 'sourcery' not in bot_kinds
    assert 'gemini' not in bot_kinds
    assert 'coderabbit' in bot_kinds


def test_enabled_bots_multiple_enabled_pass_through(plan_context, monkeypatch):
    """A comma-joined enabled set passes each named bot; the unnamed one is filtered.

    ``--enabled-bots "coderabbit,gemini"`` keeps coderabbit and gemini but
    filters sourcery, proving the split-at-read set membership rather than a
    single-value match.
    """
    plan_id = 'gh-pr-enabled-bots-multi'
    _patch_provider(monkeypatch, _COMMENTS)

    result = _run_fetch_enabled(103, plan_id, 'coderabbit,gemini')
    assert result['status'] == 'success'
    # coderabbit (c1) + gemini (c3) + human (c4) survive; only sourcery (c2) disabled.
    assert result['count_stored'] == 3
    assert result['count_skipped_disabled'] == 1
    assert result['producer_mismatch_hash_id'] is None

    stored = query_findings(plan_id, finding_type='pr-comment')['findings']
    bot_kinds = {f.get('bot_kind') for f in stored}
    assert 'sourcery' not in bot_kinds
    assert {'coderabbit', 'gemini'} <= bot_kinds


def test_enabled_bots_empty_disables_all_bots(plan_context, monkeypatch):
    """An empty ``--enabled-bots`` value disables every bot; only human comments store.

    An empty string yields an empty enabled set, so every comment whose
    ``bot_kind`` is non-empty is filtered. The human comment (``bot_kind`` None)
    is bot-scoped-exempt and still files a finding.
    """
    plan_id = 'gh-pr-enabled-bots-empty'
    _patch_provider(monkeypatch, _COMMENTS)

    result = _run_fetch_enabled(102, plan_id, '')
    assert result['status'] == 'success'
    # Only the human comment (c4) survives; all three bots are disabled.
    assert result['count_stored'] == 1
    assert result['count_skipped_disabled'] == 3
    assert result['producer_mismatch_hash_id'] is None

    stored = query_findings(plan_id, finding_type='pr-comment')['findings']
    assert len(stored) == 1
    assert stored[0].get('bot_kind') in (None, '')


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

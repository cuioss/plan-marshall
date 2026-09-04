#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""``github_pr.cmd_fetch_findings``: cross-iteration dedup, classification, and participation.

The producer-side dedup keys on ``(bot_kind, comment_id)`` for every bot kind,
thread-bearing and thread_id-less alike. Covered here: re-fetch idempotence, the
``(bot_kind, comment_id)`` collision boundary, the contentless-boilerplate
pre-filter layer, and the ``stale_participation_bots[]`` currency observation.

The findings store is REAL (isolated via the autouse ``plan_context``
``PLAN_BASE_DIR`` sandbox); only the GitHub provider surface (``check_auth``,
``fetch_pr_comments_data``, ``fetch_pr_head_sha``) is monkeypatched, so the dedup
path exercises the genuine ``_findings_core`` add/query round-trip.
"""

import argparse
import json
import sys

import bot_registry
import pytest
from _bot_flag_derivation import derive_bot_flags
from _github_pr_fixtures import (
    CURRENCY_BLIND_BOT_COUNT,
    CURRENCY_BLIND_BOTS,
    CURRENCY_SUBJECT_BOT_COUNT,
    CURRENCY_SUBJECT_BOTS,
    VacuousPopulationError,
    guard_non_empty,
)
from _pr_agent_guide_bodies import GUIDE_WITH_FINDING, OBSERVED_CLEAN_GUIDE

from conftest import get_script_path, get_skill_dir, load_script_module, run_script

# Plan ids this module's tests file findings against — seeded by the autouse
# ``_materialize_declared_plan_dirs`` fixture in ``test/conftest.py``.
PLAN_IDS: tuple[str, ...] = (
    'gh-pr-bare-flags',
    'gh-pr-bare-warn-but-ingest',
    'gh-pr-barrier-noise',
    'gh-pr-classification-empty',
    'gh-pr-classification-union',
    'gh-pr-dedup-collision',
    'gh-pr-dedup-decoupled',
    'gh-pr-dedup-refetch',
    'gh-pr-persist-dedup',
    'gh-pr-persist-reject',
    'gh-pr-quota-only-no-measure',
    'gh-pr-rate-limit-bot-agnostic',
    'gh-pr-recognised-refusal-control',
    'gh-pr-refusal-cause-sticky',
    'gh-pr-refusal-cause-sticky-reverse',
    'gh-pr-refusal-causes',
    'gh-pr-refusal-vs-participation',
    'gh-pr-respond-batch-fails',
    'gh-pr-respond-batched',
    'gh-pr-respond-changed',
    'gh-pr-respond-count-contract',
    'gh-pr-respond-round2-only-new',
    'gh-pr-respond-skipped',
    'gh-pr-respond-thread-fails',
    'gh-pr-respond-thread-idempotent',
    'gh-pr-respond-threaded',
    'gh-pr-self-response-bound',
    'gh-pr-self-response-boundary',
    'gh-pr-self-response-converged-history',
    'gh-pr-self-response-excluded',
    'gh-pr-self-response-live-loop',
    'gh-pr-self-response-reopened',
    'gh-pr-self-response-trigger-interleave',
    'gh-pr-size-refusal-no-cap',
    'gh-pr-size-refusal-unmeasurable',
    'gh-pr-unclassified-reported',
    'gh-pr-unrecognised-human',
    'gh-pr-unrecognised-inert',
    'gh-pr-unrecognised-partial',
    'gh-pr-unrecognised-refusal',
    'gh-pr-unrecognised-remedy',
    'gh-pr-unregistered-bot-classification',
    'gh-pr-unregistered-bot-filed',
    'p',
)

#: The per-bot cases derive their plan id from the bot under test, so the seeded
#: ids are derived from the SAME registry-backed population the parametrisation
#: iterates rather than transcribed — a bot added to the registry seeds its plan
#: id too, instead of failing with an unreached store.
PLAN_IDS += tuple(f'gh-pr-preupgrade-dedup-{bot_kind}' for bot_kind in CURRENCY_SUBJECT_BOTS)

github_pr = load_script_module('plan-marshall', 'workflow-integration-github', 'github_pr.py', 'github_pr')
_findings_core = load_script_module('plan-marshall', 'manage-findings', '_findings_core.py', '_findings_core')

# The refusal-layer vocabulary lives in ``_github_pr``, and ``github_pr`` re-exports
# only the members it uses — so the shared names are read from the DEFINING module.
# Taken from ``sys.modules`` rather than re-loaded, so it is the very object the
# ``github_pr`` above imported: a second load would register a rival ``_github_pr``
# and reopen the ``github_ops`` import cycle.
_github_pr = sys.modules['_github_pr']

query_findings = _findings_core.query_findings


# Mixed-bot, mixed-thread comment set: coderabbit (thread-bearing), sourcery
# (thread_id-less review_body), cuioss-review-bot (thread-bearing — a third registered
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


def _patch_provider(monkeypatch, comments, head_sha='deadbeef', head_committed_at=''):
    """Monkeypatch the GitHub provider surface ``github_pr`` reaches through ``_github``.

    ``head_sha`` is the PR HEAD the producer stamps as ``reviewed_commit_sha`` and
    compares each comment's recorded SHA against. A test simulates a loop-back /
    force-push by re-patching with a DIFFERENT value between fetches.

    ``head_committed_at`` is the merge-candidate commit's OWN timestamp — the second
    input to the first-observation arm, which withholds the credit from a comment whose
    timestamps predate the commit. It defaults to the empty string, the UNREADABLE case
    under which the arm keeps its SHA-only behaviour, so every case that is not about
    commit ordering is unaffected by the guard.
    """
    monkeypatch.setattr(github_pr._github, 'check_auth', lambda: (True, ''))
    monkeypatch.setattr(
        github_pr._github, 'fetch_pr_head_committed_at', lambda pr_number: head_committed_at
    )
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
    monkeypatch.setattr(github_pr._github, 'fetch_pr_head_sha', lambda pr_number: head_sha)
    # Stub the RAW subprocess seam too, not only the three named provider helpers.
    # ``measure_diff_size`` reaches the provider through ``github_ops.run_gh`` rather
    # than through ``_github``, so without this a size-refusal fixture would shell out
    # to a real ``gh pr view`` and silently take its failure path — a test passing for
    # the wrong reason, which is exactly the synthetic-double shape these fixtures are
    # meant to avoid. The default is a well-formed measurement so the field is EXERCISED;
    # a test that cares about the unmeasurable path re-patches with its own value.
    # ``github_pr._github`` and ``_github_pr.github_ops`` are the SAME module object, so
    # patching the attribute here reaches the call site inside ``measure_diff_size``.
    monkeypatch.setattr(
        github_pr._github,
        'run_gh',
        lambda *_a, **_k: (0, '{"additions": 900, "deletions": 340}', ''),
    )


def _run_fetch(pr_number, plan_id):
    """Run the producer's FIND verb against ``plan_id``, with its plan directory present.

    The directory is materialized HERE because ``phase-1-init`` materializes it in
    production before any producer runs, and ``cmd_fetch_findings`` REFUSES a plan
    directory absent from the resolved root — a plan that exists in no checkout is not
    a plan that has filed nothing. Constructing it in the shared helper keeps that one
    line of production context in one place instead of obliging every case below to
    repeat it, and it is the same construction the autouse
    ``_materialize_declared_plan_dirs`` fixture performs for the module-level
    ``PLAN_IDS``; the cases here derive their ids per bot, so they cannot be listed
    there without re-deriving the registry population a second time.

    ⛔ It does NOT neutralize the refusal. A test whose subject IS the unreached store
    drives ``cmd_fetch_findings`` directly rather than coming through this helper — see
    the unreached-store section in ``test_comments_stage.py``.
    """
    from file_ops import get_base_dir  # local import: resolved per call, after the sandbox fixture

    (get_base_dir() / 'plans' / plan_id).mkdir(parents=True, exist_ok=True)
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

    Thread-bearing (coderabbit/cuioss-review-bot) AND thread_id-less (sourcery/human)
    comments are all deduped on ``(bot_kind, comment_id)``. Without that, every
    barrier re-fetch re-stores the same comments as fresh ``pending`` findings,
    so the queue accretes duplicates faster than triage can drain it and the
    completeness gate never closes. The deduped comments are legitimate
    non-stores, so they must also not trip the producer-mismatch Q-Gate.
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


def test_a_deduped_comment_is_still_credited_as_participating(plan_context, monkeypatch):
    """A bot deduped on STORAGE is still credited as participating.

    Participation derives from the raw comment scan (unioned with the currency
    ledger for ``participation_requires_update`` bots) BEFORE and INDEPENDENT of
    the storage dedup. That decoupling is load-bearing: the pre-merge barrier
    feeds ``participated_bots`` to the participation predicate, so coupling it to
    the dedup would read a proven reviewer as ``absent`` on any re-fetch.

    Both observables are pinned on ONE fetch: at an unchanged HEAD every comment
    is dropped by the storage dedup, YET every participating bot stays credited
    byte-identically to the first fetch. It covers a
    ``participation_requires_update`` bot (cuioss-review-bot, credited via the SHA-current
    currency arm) alongside the presence-credited bots, so the guard holds across
    both participation shapes.
    """
    plan_id = 'gh-pr-dedup-decoupled'
    # A fixed head SHA across both fetches: the requires_update bot stays SHA-current on
    # the re-fetch, so the ONLY thing that changes between the two fetches is that every
    # comment is now already stored and therefore deduped.
    _patch_provider(monkeypatch, _COMMENTS)

    first = _run_fetch(150, plan_id)
    assert first['status'] == 'success'
    assert first['count_skipped_duplicate'] == 0
    # Every bot with a comment in a declared publish shape is credited: coderabbit and
    # sourcery by presence of a declared evidence kind, cuioss-review-bot by the first-observation
    # currency arm at the resolvable head. (The human comment resolves to no bot_kind.)
    # The expected participant list is DERIVED from the registry intersected with the
    # bots the _COMMENTS fixture represents — never a hand-listed set of bot names, which
    # would not notice a bot whose declared publish shapes changed.
    expected_participants = sorted(
        {
            kind
            for comment in _COMMENTS
            if (kind := bot_registry.bot_kind_for_login(comment['author']))
            and comment['kind'] in bot_registry.participation_evidence(kind)
        }
    )
    assert expected_participants, 'the _COMMENTS fixture represents no participating bot'
    first_bots = [e['bot_kind'] for e in first['participated_bots']]
    assert first_bots == expected_participants

    # Re-fetch the IDENTICAL comments at the SAME head. Every comment is already stored,
    # so the storage dedup drops all of them...
    second = _run_fetch(150, plan_id)
    assert second['status'] == 'success'
    assert second['count_skipped_duplicate'] == len(_COMMENTS)
    assert second['count_stored'] == 0
    # ...and yet participation is UNCHANGED — the dedup did not empty participated_bots.
    # This is the decoupling: a storage-hygiene drop can no longer flip a merge verdict.
    assert second['participated_bots'] == first['participated_bots']
    assert second['producer_mismatch_hash_id'] is None


def test_same_comment_id_distinct_bots_not_collided(plan_context, monkeypatch):
    """Two bots reusing the same numeric comment_id stay distinct across fetches.

    Comment ids are provider-assigned per comment surface, so they are not
    unique across bots — two reviewers can legitimately arrive carrying the same
    numeric id. A ``comment_id``-only dedup key therefore silently swallows the
    second bot's comment as a duplicate: a genuine review finding that never
    reaches triage, and never reaches the pre-merge barrier that reads the
    store. Keying on ``(bot_kind, comment_id)`` keeps them apart.
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
    (``'coderabbit'``, ``'coderabbit,cuioss-review-bot'``, or ``''`` for an answered-empty
    list). Their union is the CLASSIFIED set; neither list admits or drops a
    comment. The sibling ``_run_fetch`` omits both attributes entirely, which the
    handler's ``getattr(args, ..., None)`` reads as the never-supplied case. Both
    readings are falsy and drive the identical empty-classification behaviour.
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

    With only ``--required-bots "coderabbit"`` supplied, sourcery and cuioss-review-bot
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
    assert result['unclassified_bots'] == ['cuioss-review-bot', 'sourcery']
    assert result['producer_mismatch_hash_id'] is None

    stored = query_findings(plan_id, finding_type='pr-comment')['findings']
    bot_kinds = {f.get('bot_kind') for f in stored}
    # The unclassified bots' findings are present and usable, not merely counted.
    assert {'coderabbit', 'cuioss-review-bot', 'sourcery'} <= bot_kinds


def test_classification_union_spans_both_lists(plan_context, monkeypatch):
    """A bot classified via EITHER list is not reported unclassified.

    ``--required-bots "coderabbit,cuioss-review-bot"`` plus ``--optional-bots "sourcery"``
    classifies all three participating bots, proving the producer takes the union
    of the two comma-split sets rather than reading only one list.
    """
    plan_id = 'gh-pr-classification-union'
    _patch_provider(monkeypatch, _COMMENTS)

    result = _run_fetch_classified(
        103, plan_id, required_bots='coderabbit,cuioss-review-bot', optional_bots='sourcery'
    )
    assert result['status'] == 'success'
    assert result['count_stored'] == len(_COMMENTS)
    assert result['unclassified_bots'] == []
    assert result['producer_mismatch_hash_id'] is None

    stored = query_findings(plan_id, finding_type='pr-comment')['findings']
    bot_kinds = {f.get('bot_kind') for f in stored}
    assert {'coderabbit', 'cuioss-review-bot', 'sourcery'} <= bot_kinds


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
    assert result['unclassified_bots'] == ['coderabbit', 'cuioss-review-bot', 'sourcery']
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
# Exercised with NO bot_kind, which isolates the STRUCTURAL arm of the refusal seam
# (an unregistered / renamed bot, or a notice-shaped phrasing not yet filed in the
# registry): with no bot_kind the registry arm has nothing to consult, so a match
# here is a match by structural signature alone. The other arms of the stack are
# covered elsewhere — the registry arm throughout this file, and the enumerative arm
# under "The ENUMERATIVE arm on the producer path" below; isolating one arm here is a
# scoping choice, not a statement that the stack has only these.
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


#: A notice the STRUCTURAL arm recognises (alert callout + a limit-exceeded
#: statement) while CodeRabbit's declared ``refusal_patterns`` (``Review limit
#: reached``) do NOT match it — the drifted-wording shape.
_DRIFTED_CODERABBIT_NOTICE = (
    '> [!WARNING] > ## Usage limit reached > '
    'This reviewer has reached its usage limit. Reviews will resume after the limit resets.'
)

#: The same presentation carrying CodeRabbit's DECLARED wording, so both arms match
#: and the arms AGREE — the matched control for the drift case.
_AGREEING_CODERABBIT_NOTICE = (
    '> [!WARNING] > ## Review limit reached > '
    'Review limit reached. Reviews will resume after the limit resets.'
)

#: Sourcery's OBSERVED size refusal — the MIRROR direction of the drifted notice
#: above. The bot's own declared ``refusal_patterns`` match it while the structural
#: arm is blind to it ("larger than the review limit of" is a COMPARISON, not an
#: "exceeded / reached / hit" statement), so the arms differ in the REGISTRY-only
#: direction. Interpolated from the registry marker rather than hand-copied, so it
#: tracks the declared wording; that it really is registry-only is ASSERTED in the
#: control below rather than assumed here.
_SOURCERY_SIZE_REFUSAL = (
    'Sourcery was unable to review this pull request because '
    f'{bot_registry.refusal_patterns("sourcery")[0]} 150000 characters. '
    'Reduce the size of the pull request and request another review.'
)


def _drift_records(result):
    return {(r['bot_kind'], r['layer']) for r in result['refusal_pattern_drift']}


def test_fetch_findings_reports_drift_when_only_the_structural_arm_matched(
    plan_context, monkeypatch
):
    """⛔ A refusal caught by SHAPE alone names the bot whose wording has drifted.

    The notice is recognised, so the refusal itself is handled exactly as before —
    what the drift record adds is that the catch rested on a SINGLE arm. CodeRabbit
    declares ``Review limit reached``; this body says ``Usage limit reached``, so
    the registry arm misses and only the structural arm fires. The boolean seam
    returns ``True`` either way, which is precisely why the disagreement needs its
    own channel: the next rewording may clear the structural shape too, and then
    the refusal is filed as review feedback and the bot is credited with a review
    it declined.
    """
    plan_id = 'gh-pr-refusal-drift'
    comments = [
        {
            'id': 'cr-drifted',
            'author': 'coderabbitai',
            'thread_id': '',
            'kind': 'review_body',
            'body': _DRIFTED_CODERABBIT_NOTICE,
            'resolved': False,
        },
    ]
    _patch_provider(monkeypatch, comments)

    result = _run_fetch(131, plan_id)

    assert result['status'] == 'success'
    # The refusal is still recognised and classified — drift changes no verdict.
    assert result['count_skipped_refusal'] == 1
    assert result['refused_bots'] == ['coderabbit']
    # ...and the drift is reported, naming the arm that fired ALONE.
    assert result['refusal_pattern_drift'] == [
        {'bot_kind': 'coderabbit', 'layer': _github_pr.REFUSAL_LAYER_STRUCTURAL}
    ]


def test_fetch_findings_reports_no_drift_when_only_the_registry_arm_matched(
    plan_context, monkeypatch
):
    """⛔ MATCHED NEGATIVE CONTROL: a registry-only match is the DESIGN, not decay.

    The exact mirror of the positive case above — one arm fires there too, so a
    predicate that merely counted the matching arms (``len(layers) == 1``) reported
    drift for BOTH. But the two directions mean opposite things. A body only the
    STRUCTURAL arm reads means the bot's declared wording went stale. A body only
    the REGISTRY arm reads is the registry doing precisely the job it is
    load-bearing FOR: Sourcery's size refusal is invisible to the structural arm BY
    CONSTRUCTION, so this state is permanent and correct, and reporting it as drift
    named a stale record that does not exist. It fired for real on PR #1368.

    Anti-vacuity: the registry-only direction is ASSERTED against the live registry
    (not assumed of the fixture), and the publish shape is asserted to be one
    Sourcery declares — so this cannot pass because the drift channel was never
    reached at all, which is what the wrong-shape control below covers instead.
    """
    plan_id = 'gh-pr-refusal-registry-only'
    # The arms really do differ, and in the REGISTRY direction — the mirror of the
    # positive case. Read from the live seam so a registry rewording that made this
    # body structurally visible fails here rather than silently neutering the test.
    assert _github_pr.refusal_layers(_SOURCERY_SIZE_REFUSAL, 'sourcery') == [
        _github_pr.REFUSAL_LAYER_REGISTRY
    ]
    # ...and the drift channel is genuinely REACHED: review_body is a shape Sourcery
    # declares, so an empty result below is the direction, never the shape gate.
    assert 'review_body' in bot_registry.participation_evidence('sourcery')

    comments = [
        {
            'id': 'sr-size',
            'author': 'sourcery-ai',
            'thread_id': '',
            'kind': 'review_body',
            'body': _SOURCERY_SIZE_REFUSAL,
            'resolved': False,
        },
    ]
    _patch_provider(monkeypatch, comments)

    result = _run_fetch(136, plan_id)

    assert result['status'] == 'success'
    # The refusal is recognised, attributed, and classified exactly as before —
    # narrowing the drift predicate changes no verdict.
    # (``refused_bots`` naming sourcery IS the proof the registry arm fired, since
    # the structural arm was just asserted blind to this body.)
    assert result['count_skipped_refusal'] == 1
    assert result['refused_bots'] == ['sourcery']
    # ...and NO drift is reported: the registry arm matching alone is the designed
    # state for this whole class of refusal, so there is no stale record to name.
    assert result['refusal_pattern_drift'] == []


def test_fetch_findings_reports_no_drift_when_both_arms_agree(plan_context, monkeypatch):
    """⛔ Matched control: agreement is silence, so the record means something.

    Same bot, same presentation, same publish shape — the ONLY difference is that
    this body carries CodeRabbit's declared wording, so both arms match. Without
    this control the positive case would also pass on an implementation that
    emitted a drift record for every refusal.
    """
    plan_id = 'gh-pr-refusal-no-drift'
    comments = [
        {
            'id': 'cr-agreeing',
            'author': 'coderabbitai',
            'thread_id': '',
            'kind': 'review_body',
            'body': _AGREEING_CODERABBIT_NOTICE,
            'resolved': False,
        },
    ]
    _patch_provider(monkeypatch, comments)

    result = _run_fetch(132, plan_id)

    assert result['refused_bots'] == ['coderabbit']
    assert result['refusal_pattern_drift'] == []


def test_fetch_findings_reports_no_drift_for_an_unattributable_refusal(
    plan_context, monkeypatch
):
    """An unregistered author has no declared wording that COULD have drifted.

    The notice is still recognised structurally and still counted, but naming a
    registry record to fix would be meaningless — there is none.
    """
    plan_id = 'gh-pr-refusal-drift-unknown'
    comments = [
        {
            'id': 'unk-drifted',
            'author': 'randombot[bot]',
            'thread_id': '',
            'kind': 'review_body',
            'body': _DRIFTED_CODERABBIT_NOTICE,
            'resolved': False,
        },
    ]
    _patch_provider(monkeypatch, comments)

    result = _run_fetch(133, plan_id)

    assert result['count_skipped_refusal'] == 1
    assert result['refused_bots'] == []
    assert result['refusal_pattern_drift'] == []


def test_fetch_findings_reports_no_drift_outside_a_declared_publish_shape(
    plan_context, monkeypatch
):
    """Scoped to the bot's declared ``participation_evidence`` shapes.

    ``issue_comment`` is not one of CodeRabbit's declared publish shapes, so a body
    arriving in it is not evidence that the wording it uses when REVIEWING has
    drifted. Same bot and same body as the positive case — only the shape differs.
    """
    plan_id = 'gh-pr-refusal-drift-shape'
    comments = [
        {
            'id': 'cr-drifted-issue',
            'author': 'coderabbitai',
            'thread_id': '',
            'kind': 'issue_comment',
            'body': _DRIFTED_CODERABBIT_NOTICE,
            'resolved': False,
        },
    ]
    _patch_provider(monkeypatch, comments)

    result = _run_fetch(134, plan_id)

    assert 'issue_comment' not in bot_registry.participation_evidence('coderabbit')
    # Still recognised as a refusal — only the DRIFT channel is scoped.
    assert result['refused_bots'] == ['coderabbit']
    assert result['refusal_pattern_drift'] == []


def test_fetch_findings_dedupes_drift_per_bot_and_layer(plan_context, monkeypatch):
    """Drift is a property of the declared WORDING, not of each comment carrying it.

    A bot that posts the same drifted notice repeatedly has ONE stale registry
    record to fix; five identical rows would read as five problems.
    """
    plan_id = 'gh-pr-refusal-drift-dedup'
    comments = [
        {
            'id': f'cr-drifted-{n}',
            'author': 'coderabbitai',
            'thread_id': '',
            'kind': 'review_body',
            'body': _DRIFTED_CODERABBIT_NOTICE,
            'resolved': False,
        }
        for n in range(3)
    ]
    _patch_provider(monkeypatch, comments)

    result = _run_fetch(135, plan_id)

    assert _drift_records(result) == {('coderabbit', _github_pr.REFUSAL_LAYER_STRUCTURAL)}
    assert len(result['refusal_pattern_drift']) == 1


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
    ``refused_bots`` carries the refusal so the quorum layer can classify it into a
    refusal member — mapping the bot's declared ``rate_limit_class`` by DEFAULT, with
    the per-refusal overrides ``review_completeness`` applies on top. The human author
    (``bot_kind`` None) appears in neither.
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
# The ENUMERATIVE arm on the producer path — unrecognised_refusal
# =============================================================================
#
# A refusal REWORDED past every arm consulted before the noise filter used to be
# filed as ordinary review feedback while its author was credited as a participant,
# so a bot that declined reported as one that reviewed and found nothing. The
# enumerative arm withholds the finding, denies the credit, and reports the state.
#
# The fixture body is MUTATED FROM a declared registry pattern rather than
# hand-written. That is the anti-vacuity property: a hand-written body could pass
# these cases by accidentally tripping the STRUCTURAL arm, which would prove nothing
# about the enumerative one. Deriving it from the registry literal and asserting that
# BOTH earlier arms decline it is what makes the positive case load-bearing.
#
# The arm ships INERT (no threshold was derivable at D1), so every case that
# exercises the firing path sets a threshold explicitly; the shipped-inert behaviour
# is asserted separately below.

_SOURCERY_DECLARED_REFUSAL_MARKER = bot_registry.refusal_patterns('sourcery')[0]

#: The declared marker with its comparison verb swapped — the same notice, reworded
#: past the registry arm. Derived by TRANSFORMING the registry literal, so it tracks
#: the registry instead of drifting from it.
_REWORDED_SOURCERY_REFUSAL = (
    f'Sorry, {_SOURCERY_DECLARED_REFUSAL_MARKER.replace("larger than", "over")} our current plan.'
)

#: The SAME sentence built from the UNMUTATED literal — the matched negative control.
_RECOGNISED_SOURCERY_REFUSAL = f'Sorry, {_SOURCERY_DECLARED_REFUSAL_MARKER} our current plan.'


def _sourcery_comment(comment_id, body):
    """A sourcery comment in its declared publish shape (``review_body``)."""
    return {
        'id': comment_id,
        'author': 'sourcery-ai',
        'thread_id': '',
        'kind': bot_registry.participation_evidence('sourcery')[0],
        'body': body,
        'resolved': False,
    }


def _arm_the_enumerative_arm(monkeypatch, max_chars=400):
    """Give the enumerative arm a threshold so it can fire.

    Patches the globals of the FUNCTION OBJECT ``github_pr`` actually calls, not a
    ``_github_pr`` module this test imported for itself. ``github_pr`` binds the
    predicate with ``from _github_pr import _is_unrecognised_refusal``, so the name
    ``UNRECOGNISED_REFUSAL_MAX_CHARS`` is resolved in the defining module's namespace
    at call time — and ``load_script_module`` can leave this test holding a DIFFERENT
    ``_github_pr`` object than the one the SUT imported. Patching that other object is
    a silent no-op: the predicate keeps reading the unpatched ``None`` and never fires,
    so every case below would fail for a reason that has nothing to do with the arm.
    (The same module-identity hazard ``_live_findings_core`` above exists for.)

    Required at all because the SHIPPED value is ``None`` — D1 derived no bound from
    an empty corpus — which keeps the arm inert by construction.
    """
    monkeypatch.setitem(
        github_pr._is_unrecognised_refusal.__globals__,
        'UNRECOGNISED_REFUSAL_MAX_CHARS',
        max_chars,
    )


def test_the_mutated_fixture_reaches_neither_earlier_arm():
    """Anti-vacuity guard, asserted BEFORE any behavioural case depends on it.

    If the reworded body still matched the registry arm (an incomplete mutation) or
    the structural arm (a body that happens to be notice-shaped), every case below
    would pass for the wrong reason. The unmutated control must still be recognised,
    which is what proves the mutation is the only difference.
    """
    import _github_pr

    # The mutation really removed the declared marker...
    assert _SOURCERY_DECLARED_REFUSAL_MARKER not in _REWORDED_SOURCERY_REFUSAL
    assert _SOURCERY_DECLARED_REFUSAL_MARKER in _RECOGNISED_SOURCERY_REFUSAL
    # ...so no arm consulted before the noise filter sees the reworded body...
    assert _github_pr._is_refusal_notice(_REWORDED_SOURCERY_REFUSAL, 'sourcery') is False
    assert _github_pr._is_rate_limit_notice(_REWORDED_SOURCERY_REFUSAL) is False
    # ...while the unmutated control is still recognised by the registry arm.
    assert _github_pr._is_refusal_notice(_RECOGNISED_SOURCERY_REFUSAL, 'sourcery') is True


def test_an_unrecognised_refusal_files_no_finding_and_denies_credit(plan_context, monkeypatch):
    """The defect this plan closes: the reworded refusal is neither filed nor credited.

    Pre-fix the body below became an ordinary ``pr-comment`` finding AND credited
    sourcery as a proven participant — a bot that declined reporting as one that
    reviewed. Now it files nothing, credits nothing, and is reported as its own state.
    """
    plan_id = 'gh-pr-unrecognised-refusal'
    _arm_the_enumerative_arm(monkeypatch)
    _patch_provider(monkeypatch, [_sourcery_comment('sr-reworded', _REWORDED_SOURCERY_REFUSAL)])

    result = _run_fetch(180, plan_id)

    assert result['status'] == 'success'
    # No finding filed — a refusal is a signal about the review, not feedback.
    assert result['count_stored'] == 0
    assert query_findings(plan_id, finding_type='pr-comment')['findings'] == []
    # No participation credit — every publish-shape comment was an unrecognised refusal.
    assert result['participated_bots'] == []
    # Counted as a refusal, so expected_stored balances and no mismatch Q-Gate fires.
    assert result['count_skipped_refusal'] == 1
    assert result['count_skipped_noise'] == 0
    assert result['producer_mismatch_hash_id'] is None
    # Reported as the THIRD state — alongside refused_bots, never folded into it.
    assert result['refused_bots'] == []
    assert len(result['unrecognised_refusal']) == 1
    record = result['unrecognised_refusal'][0]
    assert record['bot_kind'] == 'sourcery'
    # The layer value is READ from the shared vocabulary, never restated as a literal.
    assert record['layer'] == github_pr.REFUSAL_LAYER_ENUMERATIVE


def test_the_unmutated_literal_still_classifies_as_a_recognised_refusal(plan_context, monkeypatch):
    """Matched negative control: the case cannot be passing via the structural arm.

    Same bot, same sentence, same length class — the ONLY difference is that the
    declared marker is intact. It must take the ordinary recognised-refusal path, so
    ``refused_bots`` names the bot and the enumerative list stays empty.
    """
    plan_id = 'gh-pr-recognised-refusal-control'
    _arm_the_enumerative_arm(monkeypatch)
    _patch_provider(monkeypatch, [_sourcery_comment('sr-declared', _RECOGNISED_SOURCERY_REFUSAL)])

    result = _run_fetch(181, plan_id)

    assert result['status'] == 'success'
    assert result['count_stored'] == 0
    assert result['count_skipped_refusal'] == 1
    # Recognised: the bot is named, and the enumerative list is empty.
    assert result['refused_bots'] == ['sourcery']
    assert result['unrecognised_refusal'] == []
    assert result['producer_mismatch_hash_id'] is None


def test_the_record_carries_a_reachable_remedy_not_a_description(plan_context, monkeypatch):
    """Splitting out a state owes a REACHABLE remedy — the record carries the mechanism.

    The excerpt is the phrasing to file, and the record names the exact file and field
    to file it in. A remedy that existed only in prose somewhere else would not be
    shipped with the finding that needs it.
    """
    plan_id = 'gh-pr-unrecognised-remedy'
    _arm_the_enumerative_arm(monkeypatch)
    _patch_provider(monkeypatch, [_sourcery_comment('sr-remedy', _REWORDED_SOURCERY_REFUSAL)])

    record = _run_fetch(182, plan_id)['unrecognised_refusal'][0]

    # The withheld text travels, so the decision is auditable and the phrasing filable.
    assert record['excerpt']
    assert record['excerpt'] in _REWORDED_SOURCERY_REFUSAL
    # The concrete file and field that close the gap.
    assert record['registry_file'] == 'automatic-review/standards/sourcery.md'
    assert record['registry_field'] == 'refusal_patterns'
    assert 'refusal_patterns' in record['remedy']
    assert 'sourcery.md' in record['remedy']


def test_a_bot_with_any_genuine_review_keeps_its_credit(plan_context, monkeypatch):
    """Matched negative control for the subtraction: credit is denied only when EVERY
    publish-shape comment was an unrecognised refusal.

    The same reworded refusal, this time accompanied by a real review in the bot's
    declared publish shape. The bot genuinely reviewed the diff, so it stays a proven
    participant and the unrecognised refusal remains a diagnostic — without the
    all-quantifier this case would strip the credit from a bot that did review.

    ⛔ The genuine review carries a CODE ANCHOR, and that is load-bearing rather than
    decorative. Under this test's deliberately generous threshold the review is short
    enough to satisfy every other condition of the arm, so without the anchor the arm
    would withhold it too and this case would fail — which is exactly the
    false-positive direction the design bounds. It is also why D1 must derive the
    threshold from the shortest GENUINE comment observed rather than pick one: a
    guessed bound this loose would withhold real review feedback in production, and
    the shipped ``None`` is what keeps that from happening.
    """
    plan_id = 'gh-pr-unrecognised-partial'
    _arm_the_enumerative_arm(monkeypatch)
    _patch_provider(
        monkeypatch,
        [
            _sourcery_comment('sr-reworded', _REWORDED_SOURCERY_REFUSAL),
            _sourcery_comment(
                'sr-genuine',
                'Extract this duplicated branch into a helper; `src/retry.py:41` repeats it.',
            ),
        ],
    )

    result = _run_fetch(183, plan_id)

    assert result['status'] == 'success'
    # The genuine review is filed and the credit stands.
    assert result['count_stored'] == 1
    assert result['participated_bots'] == [{'bot_kind': 'sourcery', 'evidence_kind': 'review_body'}]
    # The unrecognised refusal is still REPORTED — it is a diagnostic, not a silent drop.
    assert len(result['unrecognised_refusal']) == 1
    assert result['producer_mismatch_hash_id'] is None


def test_a_human_authored_short_comment_is_never_an_unrecognised_refusal(plan_context, monkeypatch):
    """A human's short comment is review feedback and must still be filed.

    The arm requires a REGISTERED bot; without that condition every terse human
    comment would be withheld as a refusal, which is the strictly worse failure.
    """
    plan_id = 'gh-pr-unrecognised-human'
    _arm_the_enumerative_arm(monkeypatch)
    _patch_provider(
        monkeypatch,
        [
            {
                'id': 'human-short',
                'author': 'alice',
                'thread_id': '',
                'kind': 'issue_comment',
                'body': _REWORDED_SOURCERY_REFUSAL,
                'resolved': False,
            }
        ],
    )

    result = _run_fetch(184, plan_id)

    assert result['status'] == 'success'
    assert result['count_stored'] == 1
    assert result['unrecognised_refusal'] == []
    assert result['count_skipped_refusal'] == 0


def test_with_no_threshold_the_producer_behaves_exactly_as_before(plan_context, monkeypatch):
    """At the SHIPPED value the arm never fires, so the producer is unchanged.

    This is the fail-safe the tightening rests on: D1 derived no threshold, so the
    reworded refusal is filed and credited exactly as it was before this arm existed.
    The case documents the shipped behaviour honestly rather than asserting a fix
    that is not yet armed.
    """
    plan_id = 'gh-pr-unrecognised-inert'
    # Read from the globals the SUT's own predicate resolves, so this asserts the
    # SHIPPED value rather than some other _github_pr instance's copy of it.
    assert github_pr._is_unrecognised_refusal.__globals__['UNRECOGNISED_REFUSAL_MAX_CHARS'] is None
    _patch_provider(monkeypatch, [_sourcery_comment('sr-reworded', _REWORDED_SOURCERY_REFUSAL)])

    result = _run_fetch(185, plan_id)

    assert result['status'] == 'success'
    # Inert: the comment is filed and the bot credited, as before the arm existed.
    assert result['count_stored'] == 1
    assert result['unrecognised_refusal'] == []
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


def _stage_respondable(plan_id, *, pr_number, comment_id, thread_id, resolution_detail, kind='review_body'):
    """Add a pr-comment finding already resolved by triage; return its ``hash_id``.

    ``resolution_detail`` of ``None`` stages a finding whose disposition carries
    no body — the ``skipped`` branch's input.

    ``pr_number`` is stamped as the first detail line exactly as
    ``cmd_fetch_findings`` writes it, and is required rather than defaulted: it is
    the gate ``post_responses`` reads to decide whether a row belongs to the PR
    being responded to. A staged row with no recorded PR is a different case (the
    fail-closed ``pr_number_unrecorded`` skip, covered by its own test), so
    defaulting it here would let a caller silently stage the wrong shape.

    ``kind`` is the finding's recorded publish shape and is LOAD-BEARING, because it
    is the routing predicate ``post_responses`` reads: a genuinely threadless kind
    (``review_body`` / ``issue_comment``) is the only admission into the batched
    PR-level comment, while a thread-bearing kind (``inline``) must reach the
    reviewer's own thread or be reported untransmitted. A test must therefore stage
    the kind its scenario is about — staging ``review_body`` for a thread-bearing
    scenario would silently assert the batch path under a thread-bearing name.
    """
    detail = f'pr_number: {pr_number}\ncomment_id: {comment_id}\nthread_id: {thread_id}\nkind: {kind}'
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


# =============================================================================
# post_responses PR-scoping — a plan-scoped store must not cross-deliver
# =============================================================================
#
# The findings store is keyed by PLAN, not by PR, so a plan that gathered
# findings across several PRs (a review-debt sweep, a multi-PR triage) holds
# rows owned by PRs other than the one being responded to. ``post_responses``
# used to read the whole plan ledger unfiltered, so every threadless row landed
# in the batched comment on whichever PR was passed — misdelivering other PRs'
# dispositions while still returning ``count_untransmitted: 0``, a confidently
# green report for a partly-misdelivered action.


def _resolved_pr_comment_finding(hash_id, pr_number, *, thread_id='', comment_id='cid', pr_line=True):
    """Build a resolved pr-comment finding shaped exactly as cmd_fetch_findings writes it.

    ``thread_id`` selects the recorded ``kind`` so the fixture matches the
    routing predicate: a thread-bearing row is ``inline``, a threadless row is
    ``review_body``. ``pr_line=False`` omits the ``pr_number:`` line entirely,
    modelling a row whose originating PR was never recorded.
    """
    detail_lines = []
    if pr_line:
        detail_lines.append(f'pr_number: {pr_number}')
    detail_lines.extend(
        [
            'kind: inline' if thread_id else 'kind: review_body',
            'author: coderabbitai',
            f'thread_id: {thread_id}',
            f'comment_id: {comment_id}',
        ]
    )
    return {
        'hash_id': hash_id,
        'detail': '\n'.join(detail_lines),
        'resolution': 'fixed',
        'resolution_detail': f'disposition body for {hash_id}',
    }


def _patch_respond_surface(monkeypatch, findings, posted, replied):
    """Patch the provider surface + the live findings store cmd_post_responses reads.

    ``cmd_post_responses`` does ``from _findings_core import query_findings``
    INSIDE the function body, so the attribute is resolved from the live
    ``sys.modules`` entry at call time — the same reason ``_live_findings_core``
    exists above. Patching that attribute is what the SUT actually reads.
    """
    monkeypatch.setattr(github_pr._github, 'check_auth', lambda: (True, ''))
    monkeypatch.setattr(
        _live_findings_core(),
        'query_findings',
        lambda plan_id, finding_type=None, **kwargs: {'findings': list(findings)},
    )

    def _run_graphql(_mutation, variables):
        replied.append(variables.get('threadId'))
        return 0, {}, ''

    def _post_pr_comment(pr_number, body):
        posted.append((pr_number, body))
        return {'status': 'success'}

    monkeypatch.setattr(github_pr._github, 'run_graphql', _run_graphql)
    monkeypatch.setattr(github_pr._github, 'post_pr_comment', _post_pr_comment)


def test_post_responses_transmits_only_the_target_prs_findings(monkeypatch):
    """A multi-PR store transmits only the rows owned by the PR being responded to.

    Two threadless rows belong to PR 1036, one to PR 1013. Responding to 1036
    must transmit exactly the two, and report the foreign row as skipped with a
    reason naming its real owner — not fold it into the batched comment.
    """
    # Arrange
    findings = [
        _resolved_pr_comment_finding('own-a', 1036, comment_id='a'),
        _resolved_pr_comment_finding('own-b', 1036, comment_id='b'),
        _resolved_pr_comment_finding('foreign', 1013, comment_id='f'),
    ]
    posted, replied = [], []
    _patch_respond_surface(monkeypatch, findings, posted, replied)

    # Act
    result = _run_post_responses(1036, 'gh-pr-scoping')

    # Assert — only this PR's rows were transmitted.
    assert result['status'] == 'success'
    assert {entry['hash_id'] for entry in result['responded']} == {'own-a', 'own-b'}
    assert {entry['hash_id'] for entry in result['skipped']} == {'foreign'}
    assert result['skipped'][0]['reason'] == 'belongs_to_pr_1013'

    # Exactly one batched comment, on the target PR, carrying only its own rows.
    assert len(posted) == 1
    target_pr, body = posted[0]
    assert target_pr == 1036
    assert 'comment_id: `a`' in body
    assert 'comment_id: `b`' in body
    assert 'comment_id: `f`' not in body


def test_post_responses_does_not_reply_to_foreign_threads(monkeypatch):
    """A thread-bearing row owned by another PR is not replied to or resolved.

    A ``thread_id`` is a global GraphQL node id, so an unfiltered pass WOULD
    reach the foreign PR's thread — and because the caller loops once per PR, it
    would re-reply and re-resolve that thread on every iteration. The gate must
    apply to thread-bearing rows too, not only to the batched ones.
    """
    # Arrange
    findings = [
        _resolved_pr_comment_finding('own-thread', 1036, thread_id='PRRT_OWN', comment_id='a'),
        _resolved_pr_comment_finding('foreign-thread', 1013, thread_id='PRRT_FOREIGN', comment_id='f'),
    ]
    posted, replied = [], []
    _patch_respond_surface(monkeypatch, findings, posted, replied)

    # Act
    result = _run_post_responses(1036, 'gh-pr-scoping-threads')

    # Assert — the foreign thread was never touched.
    assert 'PRRT_FOREIGN' not in replied
    # The own thread got its reply-then-resolve pair (both mutations run).
    assert replied.count('PRRT_OWN') == 2
    assert {entry['hash_id'] for entry in result['responded']} == {'own-thread'}
    assert {entry['hash_id'] for entry in result['skipped']} == {'foreign-thread'}
    # No threadless rows survived the gate, so no batched comment was posted.
    assert posted == []


def test_post_responses_skips_a_row_whose_pr_number_was_never_recorded(monkeypatch):
    """An unattributable row is skipped, not defaulted onto the current PR.

    Fail-closed: a row with no recorded ``pr_number`` is precisely the case that
    cannot be shown to belong here, so it is reported in ``skipped`` — visibly
    deferred rather than silently dropped or misdelivered.
    """
    # Arrange
    findings = [
        _resolved_pr_comment_finding('own', 1036, comment_id='a'),
        _resolved_pr_comment_finding('orphan', 0, comment_id='o', pr_line=False),
    ]
    posted, replied = [], []
    _patch_respond_surface(monkeypatch, findings, posted, replied)

    # Act
    result = _run_post_responses(1036, 'gh-pr-scoping-orphan')

    # Assert
    assert {entry['hash_id'] for entry in result['responded']} == {'own'}
    assert result['skipped'] == [{'hash_id': 'orphan', 'reason': 'pr_number_unrecorded'}]
    # The orphan is skipped, never transmitted — and skips are not failures.
    assert result['count_untransmitted'] == 0
    assert result['status'] == 'success'
    assert 'comment_id: `o`' not in posted[0][1]


def test_pr_number_detail_matcher_reads_the_producer_written_shape():
    """Mutation guard: the matcher fires on the exact detail block the producer writes.

    ``cmd_fetch_findings`` stamps ``pr_number`` as the FIRST line of the detail
    block. Without this guard a regex typo would make ``_detail_field`` return
    '' for every row, so every finding would look unattributable and
    ``post_responses`` would silently transmit nothing at all — a vacuous pass of
    the three tests above.
    """
    producer_shape = 'pr_number: 1036\nkind: inline\nauthor: coderabbitai\nthread_id: PRRT_1\ncomment_id: c1'

    assert github_pr._detail_field(producer_shape, github_pr._PR_NUMBER_DETAIL) == '1036'
    # A detail block with no pr_number line yields '' (drives the fail-closed skip).
    assert github_pr._detail_field('kind: inline\ncomment_id: c1', github_pr._PR_NUMBER_DETAIL) == ''


def _pr_comment_finding_with_detail(hash_id, detail):
    """Build a resolved threadless pr-comment finding carrying a hand-written detail block.

    ``_resolved_pr_comment_finding`` always writes the producer's own shape, so it
    cannot express a detail block that DEVIATES from it. These deviation cases are
    exactly what the ``pr_number`` extraction must reject, so they are built here.
    """
    return {
        'hash_id': hash_id,
        'detail': detail,
        'resolution': 'fixed',
        'resolution_detail': f'disposition body for {hash_id}',
    }


def test_post_responses_skips_a_row_whose_pr_number_marker_is_not_the_first_line(monkeypatch):
    """A ``pr_number:`` marker appearing later in the detail block does not attribute the row.

    The producer stamps ``pr_number`` as the FIRST detail line and nowhere else, so
    a marker found deeper in the block did not come from the producer — it is text
    that happens to look like the marker. Honouring it would let arbitrary later
    content decide which PR a disposition is transmitted to, which is precisely the
    routing predicate ``cmd_post_responses`` must not widen. The row is reported as
    ``pr_number_unrecorded`` (visibly deferred), never delivered to PR 1036.
    """
    # Arrange
    findings = [
        _resolved_pr_comment_finding('own', 1036, comment_id='a'),
        _pr_comment_finding_with_detail(
            'late-marker',
            'kind: review_body\nauthor: coderabbitai\nthread_id: \ncomment_id: L\npr_number: 1036',
        ),
    ]
    posted, replied = [], []
    _patch_respond_surface(monkeypatch, findings, posted, replied)

    # Act
    result = _run_post_responses(1036, 'gh-pr-scoping-late-marker')

    # Assert
    assert {entry['hash_id'] for entry in result['responded']} == {'own'}
    assert result['skipped'] == [{'hash_id': 'late-marker', 'reason': 'pr_number_unrecorded'}]
    assert result['status'] == 'success'
    assert 'comment_id: `L`' not in posted[0][1]


def test_post_responses_skips_a_row_whose_pr_number_marker_is_not_numeric(monkeypatch):
    """A non-numeric ``pr_number`` value does not attribute the row to any PR.

    The producer writes an integer PR number, so a non-numeric value cannot have
    come from it. Accepting it would produce a nonsense ``belongs_to_pr_<value>``
    verdict — a confident-looking attribution to a PR that does not exist — instead
    of the fail-closed ``pr_number_unrecorded`` deferral.
    """
    # Arrange
    findings = [
        _resolved_pr_comment_finding('own', 1036, comment_id='a'),
        _pr_comment_finding_with_detail(
            'non-numeric',
            'pr_number: 1036x\nkind: review_body\nauthor: coderabbitai\nthread_id: \ncomment_id: N',
        ),
    ]
    posted, replied = [], []
    _patch_respond_surface(monkeypatch, findings, posted, replied)

    # Act
    result = _run_post_responses(1036, 'gh-pr-scoping-non-numeric')

    # Assert
    assert {entry['hash_id'] for entry in result['responded']} == {'own'}
    assert result['skipped'] == [{'hash_id': 'non-numeric', 'reason': 'pr_number_unrecorded'}]
    assert result['status'] == 'success'
    assert 'comment_id: `N`' not in posted[0][1]


def test_post_responses_batches_thread_less_dispositions_into_one_comment(plan_context, monkeypatch):
    """Two thread-less dispositions are transmitted by exactly ONE batched PR comment.

    Batching is the contract, not an optimization: ``review_body`` findings from
    every bot are thread-less, so a per-finding comment would spam the PR. The
    single posted body must carry BOTH source ``comment_id``s so each disposition
    stays traceable to the comment it answers.
    """
    plan_id = 'gh-pr-respond-batched'
    hash_a = _stage_respondable(
        plan_id, pr_number=300, comment_id='ca', thread_id='', resolution_detail='Accepted: covered by TASK-3.'
    )
    hash_b = _stage_respondable(
        plan_id, pr_number=300, comment_id='cb', thread_id='', resolution_detail='Accepted: out of scope here.'
    )

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
    hash_id = _stage_respondable(plan_id, pr_number=301, comment_id='cs', thread_id='', resolution_detail=None)

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
    hash_a = _stage_respondable(
        plan_id, pr_number=302, comment_id='fa', thread_id='', resolution_detail='Accepted: noted.'
    )
    hash_b = _stage_respondable(
        plan_id, pr_number=302, comment_id='fb', thread_id='', resolution_detail='Accepted: also noted.'
    )

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
        plan_id, pr_number=303, comment_id='ct', thread_id='PRRT_T', resolution_detail='Fixed in TASK-4.', kind='inline'
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
        plan_id, pr_number=304, comment_id='cf', thread_id='PRRT_F', resolution_detail='Fixed in TASK-5.', kind='inline'
    )

    monkeypatch.setattr(github_pr._github, 'check_auth', lambda: (True, ''))
    monkeypatch.setattr(github_pr._github, 'run_graphql', lambda query, variables: (1, None, 'permission denied'))

    result = _run_post_responses(304, plan_id)

    assert result['status'] == 'partial'
    assert result['count_untransmitted'] == 1
    assert result['untransmitted'][0]['hash_id'] == hash_id
    assert 'thread-reply failed' in result['untransmitted'][0]['reason']


# =============================================================================
# post_responses idempotency — a reply is transmitted once per (finding,
# disposition). The store is plan-scoped and persists across rounds, so a
# terminal finding re-qualifies on every pass unless a prior-transmission marker
# excludes it. Terminality is the SELECTION criterion (``_RESPONDABLE_RESOLUTIONS``),
# never an exclusion — so the guard is an explicit per-finding ``responded`` marker,
# not a property of terminality. A disposition that genuinely CHANGED between rounds
# clears the marker (via ``manage-findings resolve``) and transmits again.
# =============================================================================


def test_post_responses_second_round_transmits_only_newly_resolved_dispositions(plan_context, monkeypatch):
    """The observed defect: round 2 must re-transmit NOTHING already sent.

    Round 1 stages four resolved dispositions and transmits them. Round 2 adds
    three genuinely new dispositions on top of the SAME plan-scoped store. The
    verb must transmit exactly the three new ones and report ``count_responded:
    3`` — never re-send the four already-satisfied replies. The pre-fix code had
    no prior-transmission term, so round 2 re-selected all seven and reported
    ``count_responded: 7`` — a confident affirmative over work that mostly did not
    need to happen. This is the (a) case of D3.
    """
    plan_id = 'gh-pr-respond-round2-only-new'
    monkeypatch.setattr(github_pr._github, 'check_auth', lambda: (True, ''))
    spy = _PostSpy()
    monkeypatch.setattr(github_pr._github, 'post_pr_comment', spy)

    round1 = [
        _stage_respondable(
            plan_id, pr_number=400, comment_id=f'r1-{i}', thread_id='', resolution_detail=f'Accepted: round-1 reply {i}.'
        )
        for i in range(4)
    ]
    first = _run_post_responses(400, plan_id)
    assert first['count_responded'] == 4

    round2 = [
        _stage_respondable(
            plan_id, pr_number=400, comment_id=f'r2-{i}', thread_id='', resolution_detail=f'Accepted: round-2 reply {i}.'
        )
        for i in range(3)
    ]
    second = _run_post_responses(400, plan_id)

    # Only the three new dispositions transmit; the four already-sent are skipped
    # as already-responded, not folded into the count as work done.
    assert second['count_responded'] == 3
    assert {entry['hash_id'] for entry in second['responded']} == set(round2)
    already = [entry for entry in second['skipped'] if entry['reason'] == 'already responded']
    assert {entry['hash_id'] for entry in already} == set(round1)

    # The round-2 batched body must carry ONLY the new comment_ids, never the old.
    round2_body = spy.calls[1][1]
    for i in range(3):
        assert f'r2-{i}' in round2_body
    for i in range(4):
        assert f'r1-{i}' not in round2_body


def test_post_responses_retransmits_a_changed_disposition(plan_context, monkeypatch):
    """A disposition CHANGED between rounds must transmit again — the fix is a KEY.

    The ``responded`` marker suppresses an UNCHANGED disposition, but re-resolving
    a finding to a different disposition (a new resolution or a new reply body)
    must make it transmittable again — otherwise the reviewer never sees the
    corrected decision. This is the (b) case of D3, and it is what distinguishes a
    per-``(finding, disposition)`` key from a blanket suppression.
    """
    plan_id = 'gh-pr-respond-changed'
    monkeypatch.setattr(github_pr._github, 'check_auth', lambda: (True, ''))
    spy = _PostSpy()
    monkeypatch.setattr(github_pr._github, 'post_pr_comment', spy)

    hash_id = _stage_respondable(
        plan_id, pr_number=401, comment_id='cc', thread_id='', resolution_detail='Accepted: original reply.'
    )
    first = _run_post_responses(401, plan_id)
    assert first['count_responded'] == 1

    # An UNCHANGED re-run transmits nothing — the marker holds.
    unchanged = _run_post_responses(401, plan_id)
    assert unchanged['count_responded'] == 0
    assert [entry for entry in unchanged['skipped'] if entry['reason'] == 'already responded']

    # The disposition genuinely CHANGES: a new resolution AND a new reply body.
    # ``resolve_finding`` must clear the marker so the corrected decision goes out.
    _findings_core.resolve_finding(plan_id, hash_id, 'rejected', detail='Rejected: on reflection, out of scope.')
    changed = _run_post_responses(401, plan_id)

    assert changed['count_responded'] == 1
    assert changed['responded'][0]['hash_id'] == hash_id
    assert 'Rejected: on reflection, out of scope.' in spy.calls[-1][1]


def test_post_responses_count_responded_names_this_rounds_transmits(plan_context, monkeypatch):
    """The count-field family names what it counts — non-empty-asserted and covered.

    D0 derived the PRODUCTION consumer set of ``count_responded`` as empty: the
    review-retrospective computes ``pct_resolved_as_fixed`` from each finding's
    ``resolution`` field (not from this return), and the RESPOND workflow reads
    ``status`` / ``count_untransmitted``. The population a consumer reads for
    "replies this round" is therefore the return's own responded-count family.
    Derive that family from the return contract, assert it is non-empty (the
    vacuous-set guard, per ``test/_shared/_dispatch_roster.py``'s
    non-empty-first discipline), and cover every member: after a round has already
    satisfied some dispositions, the family must report only the NEW transmit,
    never the standing total of terminal findings. This is the (c) case of D3.
    """
    plan_id = 'gh-pr-respond-count-contract'
    monkeypatch.setattr(github_pr._github, 'check_auth', lambda: (True, ''))
    spy = _PostSpy()
    monkeypatch.setattr(github_pr._github, 'post_pr_comment', spy)

    prior = [
        _stage_respondable(
            plan_id, pr_number=402, comment_id=f'p-{i}', thread_id='', resolution_detail=f'Accepted: prior {i}.'
        )
        for i in range(5)
    ]
    _run_post_responses(402, plan_id)  # all five now satisfied and marked

    new_one = _stage_respondable(
        plan_id, pr_number=402, comment_id='n', thread_id='', resolution_detail='Accepted: the only new one.'
    )
    result = _run_post_responses(402, plan_id)

    # Derive the responded-count family from the return contract, non-empty first.
    responded_family = {key: value for key, value in result.items() if key in ('count_responded', 'responded')}
    assert responded_family, 'the return must expose a responded-count family'

    # Every member names ONLY this round's transmit — the single new disposition,
    # never the six standing terminal findings.
    assert responded_family['count_responded'] == 1
    assert [entry['hash_id'] for entry in responded_family['responded']] == [new_one]
    # The five already-satisfied are named as already-responded, not counted as work.
    already = [entry['hash_id'] for entry in result['skipped'] if entry['reason'] == 'already responded']
    assert set(already) == set(prior)


def test_post_responses_thread_reply_path_is_idempotent_across_rounds(plan_context, monkeypatch):
    """The thread-reply branch stamps and honours the ``responded`` marker too.

    The (a)/(b)/(c) tests exercise the batched path; this one covers the
    thread-bearing branch, where the marker is stamped after a successful
    reply-then-resolve. A second pass over the unchanged disposition must skip it
    and issue NO further GraphQL mutations — otherwise the reviewer's thread is
    re-replied and re-resolved on every round.
    """
    plan_id = 'gh-pr-respond-thread-idempotent'
    monkeypatch.setattr(github_pr._github, 'check_auth', lambda: (True, ''))
    mutations = []

    def _run_graphql(query, variables):
        mutations.append((query, variables))
        return (0, {}, '')

    monkeypatch.setattr(github_pr._github, 'run_graphql', _run_graphql)

    hash_id = _stage_respondable(
        plan_id, pr_number=405, comment_id='ti', thread_id='PRRT_IDEM', resolution_detail='Fixed in TASK-9.', kind='inline'
    )

    first = _run_post_responses(405, plan_id)
    assert first['count_responded'] == 1
    assert len(mutations) == 2  # thread-reply + resolve-thread

    second = _run_post_responses(405, plan_id)
    assert second['count_responded'] == 0
    assert [entry for entry in second['skipped'] if entry['reason'] == 'already responded'] == [
        {'hash_id': hash_id, 'reason': 'already responded'}
    ]
    # No further GraphQL traffic — the thread was not re-replied or re-resolved.
    assert len(mutations) == 2


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


# =============================================================================
# Bare classification flags — the interpolation-collapse the callers produce
# =============================================================================
#
# ``automatic-review/SKILL.md`` and ``phase-6-finalize/standards/branch-cleanup.md``
# interpolate ``--required-bots {required_bots} --optional-bots {optional_bots}``
# into this verb's command line, and both knobs default EMPTY. An unquoted
# placeholder with an empty value therefore collapses to a BARE flag, which the
# pre-fix parser (no ``default``, no ``nargs``) answered with ``expected one
# argument`` and argparse exit 2 — killing the producer that feeds the
# participation quorum its evidence.
#
# Every case below is red against the pre-fix parser by construction: neither flag
# accepted a bare form at all, and an omitted flag left the attribute at ``None``
# rather than ``''``. Nothing here can pass without the ``nargs='?'`` +
# ``const=''`` + ``default=''`` relaxation.

#: The classification flags and the ``argparse`` dest each resolves to, derived
#: from the live ``fetch_findings`` parser so a flag added to the script inherits
#: the bare-form sweeps below instead of silently losing them.
_CLASSIFICATION_FLAGS = derive_bot_flags(
    get_script_path('plan-marshall', 'workflow-integration-github', 'github_pr.py'),
    'fetch_findings',
)


def _parsed_fetch_args(monkeypatch, argv):
    """Return the ``argparse.Namespace`` ``github_pr.main`` built for ``argv``.

    Replaces ``cmd_fetch_findings`` with a recorder so the parse is observed
    WITHOUT reaching the provider. ``main`` reads the handler from module globals
    when it builds the subcommand table at call time, so patching the module
    attribute reaches the binding it uses.
    """
    captured = {}

    def _recorder(args):
        captured['args'] = args
        return {'status': 'success'}

    monkeypatch.setattr(github_pr, 'cmd_fetch_findings', _recorder)
    monkeypatch.setattr(sys, 'argv', ['github_pr.py', *argv])
    github_pr.main()
    return captured['args']


class TestBareClassificationFlags:
    """Both classification flags accept a bare form that reads as the empty list."""

    def test_both_flags_bare_is_not_an_argparse_rejection(self, plan_context):
        """The collapsed shape reaches the handler instead of exiting 2.

        Asserted through the constructed-argv subprocess runner — the lowest
        primitive that actually exercises argparse, so a parser regression cannot
        hide behind an in-process ``Namespace`` the test built itself.

        ``PATH`` is emptied so the ``gh`` binary is unresolvable and the run cannot
        reach the network: the process gets past argparse and then fails at the
        provider boundary, which is exactly the boundary this case is about. The
        assertions are therefore about the ABSENCE of an argparse rejection, not
        about the provider outcome.
        """
        script_path = get_script_path('plan-marshall', 'workflow-integration-github', 'github_pr.py')

        result = run_script(
            script_path,
            'fetch_findings',
            '--pr-number',
            '999',
            '--plan-id',
            'gh-pr-bare-flags',
            '--required-bots',
            '--optional-bots',
            env_overrides={'PATH': ''},
        )

        assert result.returncode != 2, result.stderr
        assert 'expected one argument' not in result.stderr
        assert 'unrecognized arguments' not in result.stderr

    @pytest.mark.parametrize(('flag', 'dest'), _CLASSIFICATION_FLAGS)
    def test_each_flag_bare_individually_resolves_to_empty_string(self, monkeypatch, flag, dest):
        """A bare flag resolves to ``''`` — the empty list, never ``None``.

        Asserted on the parsed namespace, because ``None`` and ``''`` are both
        falsy to the handler's classification split: a downstream behavioural
        assertion alone would pass for either and so would not pin the parse.
        """
        args = _parsed_fetch_args(
            monkeypatch,
            ['fetch_findings', '--pr-number', '1', '--plan-id', 'p', flag],
        )

        assert getattr(args, dest) == ''

    @pytest.mark.parametrize(('flag', 'dest'), _CLASSIFICATION_FLAGS)
    def test_each_flag_bare_followed_by_the_other_flag(self, monkeypatch, flag, dest):
        """A bare flag does not swallow the NEXT flag as its value.

        The collapse normally leaves the bare flag followed by the sibling
        ``--flag``; argparse treats a ``-``-prefixed token as an option rather
        than an optional value, so the bare flag takes ``const=''`` and the
        sibling parses its own value normally.
        """
        other_flag = next(f for f, _ in _CLASSIFICATION_FLAGS if f != flag)
        other_dest = next(d for f, d in _CLASSIFICATION_FLAGS if f != flag)

        args = _parsed_fetch_args(
            monkeypatch,
            ['fetch_findings', '--pr-number', '1', '--plan-id', 'p', flag, other_flag, 'sourcery'],
        )

        assert getattr(args, dest) == ''
        assert getattr(args, other_dest) == 'sourcery'

    @pytest.mark.parametrize(('flag', 'dest'), _CLASSIFICATION_FLAGS)
    def test_each_flag_value_form_is_unchanged(self, monkeypatch, flag, dest):
        """The existing ``--flag value`` form parses exactly as before.

        Pairs with the bare-form cases so the relaxation is shown to ADD a form
        rather than replace one.
        """
        args = _parsed_fetch_args(
            monkeypatch,
            ['fetch_findings', '--pr-number', '1', '--plan-id', 'p', flag, 'coderabbit,cuioss-review-bot'],
        )

        assert getattr(args, dest) == 'coderabbit,cuioss-review-bot'

    @pytest.mark.parametrize(('flag', 'dest'), _CLASSIFICATION_FLAGS)
    def test_omitted_flag_now_parses_to_empty_string_not_none(self, monkeypatch, flag, dest):
        """The omitted-flag value moved from ``None`` to ``''`` with ``default=''``.

        Recorded explicitly because it is the one BEHAVIOURAL change the
        relaxation makes to an existing invocation shape. Both values are falsy
        and drive identical classification, so no caller behaviour changes — but
        a future assertion that the omitted flag is ``None`` would be wrong, and
        this pins which value is correct.
        """
        args = _parsed_fetch_args(
            monkeypatch, ['fetch_findings', '--pr-number', '1', '--plan-id', 'p']
        )

        assert getattr(args, dest) == ''

    def test_bare_flags_reach_the_handler_and_still_warn_but_ingest(
        self, plan_context, monkeypatch, capsys
    ):
        """END-TO-END through the relaxed parser: bare flags still ingest everything.

        Distinct from ``test_empty_classification_lists_still_ingest_every_bot``,
        which hand-builds an ``argparse.Namespace`` and so proves nothing about the
        parser: this case drives the REAL ``main`` -> parse -> handler chain with
        both flags bare, so the value the relaxation produces is the value the
        handler actually consumes. It pins that the relaxation does not turn
        "classify nothing" into "drop everything" — the warn-but-ingest rule is not
        a casualty of it.
        """
        plan_id = 'gh-pr-bare-warn-but-ingest'
        _patch_provider(monkeypatch, _COMMENTS)
        monkeypatch.setattr(
            sys,
            'argv',
            [
                'github_pr.py',
                'fetch_findings',
                '--pr-number',
                '112',
                '--plan-id',
                plan_id,
                '--required-bots',
                '--optional-bots',
            ],
        )

        github_pr.main()

        emitted = capsys.readouterr().out
        assert 'status: success' in emitted
        assert f'count_stored: {len(_COMMENTS)}' in emitted
        # Every participating bot is named as unclassified — warned about, not dropped.
        for bot_kind in ('coderabbit', 'cuioss-review-bot', 'sourcery'):
            assert bot_kind in emitted

        stored = query_findings(plan_id, finding_type='pr-comment')['findings']
        assert len(stored) == len(_COMMENTS)
        assert {f.get('bot_kind') for f in stored} >= {'coderabbit', 'cuioss-review-bot', 'sourcery'}


# =============================================================================
# Pre-filter layer 3 — contentless review boilerplate
# =============================================================================
#
# Driven directly with a body string and a bot_kind: no provider monkeypatching
# and no findings-store round-trip, so these assert the predicate itself rather
# than an end-to-end ingest outcome.
#
# The required-marker set is read FROM THE REGISTRY rather than restated here, so
# a marker added to (or dropped from) ``cuioss-review-bot.md`` changes the covered
# population automatically instead of leaving a hand-written list one member
# short of the real one.

_PR_AGENT_REQUIRED_MARKERS = bot_registry.contentless_review_markers('cuioss-review-bot')

# Both Guide bodies come from ``test/_shared/_pr_agent_guide_bodies.py`` — the
# CLEAN one is the verbatim body observed on #1078 (an HTML ``<table>`` of
# ``<strong>`` assertions, NOT the markdown rendering a human reads), and the
# finding-bearing one is rendered from the same markup with one ``<details>``
# added. A local literal is what previously let these units and the registry
# agree with each other while matching no real body at all.


def test_clean_guide_fixture_carries_every_declared_required_marker():
    """The fixture stays in step with the registry it is meant to exercise.

    Without this guard a marker added to ``cuioss-review-bot.md`` would leave the
    conjunction cases below asserting ``False`` for the trivial reason that the
    fixture never carried the new marker — the whole layer-3 suite would keep
    passing while covering nothing.
    """
    assert _PR_AGENT_REQUIRED_MARKERS
    for marker in _PR_AGENT_REQUIRED_MARKERS:
        assert marker in OBSERVED_CLEAN_GUIDE


@pytest.mark.parametrize('bot_kind', ['coderabbit', 'sourcery', 'not-a-registered-bot', None])
def test_empty_required_markers_short_circuit_to_false(bot_kind):
    """A bot declaring no clean shape can never have a comment dropped by layer 3.

    This is the fail-closed default and the state EVERY bot other than PR-Agent
    is in — including an unregistered kind and the human path (``bot_kind`` is
    ``None``). It is asserted against a body that carries PR-Agent's every
    required marker, so the ``False`` can only come from the empty-required
    short-circuit and not from a failed marker match.
    """
    assert bot_registry.contentless_review_markers(bot_kind or '') == []
    assert github_pr._is_contentless_boilerplate(OBSERVED_CLEAN_GUIDE, bot_kind) is False


def test_clean_guide_is_contentless_boilerplate():
    """Every required marker present and no disqualifying marker — the drop case."""
    assert github_pr._is_contentless_boilerplate(OBSERVED_CLEAN_GUIDE, 'cuioss-review-bot') is True


@pytest.mark.parametrize('missing', _PR_AGENT_REQUIRED_MARKERS)
def test_removing_any_single_required_marker_fails_the_conjunction(missing):
    """The predicate is ``all(required)`` — one absent marker is enough to keep the comment.

    One case PER MARKER rather than one representative case, so the set is
    covered member-by-member: weakening the registry list to the 🔒 row alone
    (operator decision Q1's rejected shortcut) turns the corresponding case red
    instead of silently widening the suppression. The docs-only PR — whose Guide
    carries the 🔒 clean assertion but not the 🧪 one — is exactly this shape.
    """
    body = OBSERVED_CLEAN_GUIDE.replace(missing, '')

    assert missing not in body
    assert github_pr._is_contentless_boilerplate(body, 'cuioss-review-bot') is False


def test_any_actionable_marker_vetoes_the_drop():
    """A ``<details>`` finding disqualifies the drop even with every clean marker present.

    The veto is what keeps the predicate fail-OPEN: a Guide that asserts a clean
    security row while also carrying a focus-area finding is a review WITH
    content, and dropping it would destroy real review signal.
    """
    for marker in _PR_AGENT_REQUIRED_MARKERS:
        assert marker in GUIDE_WITH_FINDING
    assert '<details>' in GUIDE_WITH_FINDING

    assert github_pr._is_contentless_boilerplate(GUIDE_WITH_FINDING, 'cuioss-review-bot') is False


def test_registry_markers_are_stripped_before_matching(monkeypatch):
    """Incidental whitespace around a registry value must not break the match.

    The registry values are markdown-quoted inside a fenced data block, so a
    stray leading/trailing space is a plausible data edit. Both sides of the
    comparison are normalized — the project's normalize-both-sides-of-a-
    registry-comparison rule — so such a value still matches the raw body.
    Without the strip the required marker would never be found and the layer
    would silently stop firing.
    """
    monkeypatch.setattr(
        github_pr.bot_registry,
        'contentless_review_markers',
        lambda bot_kind: [f'  {marker}  ' for marker in _PR_AGENT_REQUIRED_MARKERS],
    )
    monkeypatch.setattr(
        github_pr.bot_registry,
        'actionable_content_markers',
        lambda bot_kind: ['  <details>  '],
    )

    assert github_pr._is_contentless_boilerplate(OBSERVED_CLEAN_GUIDE, 'cuioss-review-bot') is True
    # The disqualifying marker is stripped on the same path — a padded veto entry
    # must still veto, not silently stop matching.
    assert github_pr._is_contentless_boilerplate(GUIDE_WITH_FINDING, 'cuioss-review-bot') is False


def test_obvious_noise_drops_the_clean_guide_via_layer_three():
    """``_is_obvious_noise`` returns True for the clean Guide and False for the finding-bearing one.

    Layer 3 is reached through the public pre-filter, not only through the helper
    — the wiring is what makes the fix take effect in ``cmd_fetch_findings``.
    """
    assert github_pr._is_obvious_noise(OBSERVED_CLEAN_GUIDE, 'cuioss-review-bot') is True
    assert github_pr._is_obvious_noise(GUIDE_WITH_FINDING, 'cuioss-review-bot') is False


def test_layer_three_is_consulted_only_after_layers_one_and_two_miss(monkeypatch):
    """Ordering: a body already matched by layer 1 or layer 2 never reaches layer 3.

    Asserted by spying on ``_is_contentless_boilerplate`` rather than on the
    return value, because all three layers return ``True`` — a return-value
    assertion could not tell which layer produced it, and would pass just as
    happily if layer 3 ran first.
    """
    calls = []
    real = github_pr._is_contentless_boilerplate

    def _spy(body, bot_kind):
        calls.append(bot_kind)
        return real(body, bot_kind)

    monkeypatch.setattr(github_pr, '_is_contentless_boilerplate', _spy)

    # Layer 1 — a shared, bot-agnostic acknowledgment regex.
    assert github_pr._is_obvious_noise('LGTM, nothing further from me.', 'cuioss-review-bot') is True
    assert calls == []

    # Layer 2 — PR-Agent's own literal ignore marker.
    assert github_pr._is_obvious_noise('## PR Agent Walkthrough\n\nAvailable commands.', 'cuioss-review-bot') is True
    assert calls == []

    # Neither matches — only now is layer 3 consulted.
    assert github_pr._is_obvious_noise(OBSERVED_CLEAN_GUIDE, 'cuioss-review-bot') is True
    assert calls == ['cuioss-review-bot']


# =============================================================================
# stale_participation_bots — the currency-test failure is REPORTED, not discarded
# =============================================================================
#
# For a bot declaring ``participation_requires_update`` the movement guard denies
# credit to a stale unchanged comment. At that point the comment's ``kind`` has
# ALREADY matched a declared ``participation_evidence`` publish shape — only the
# currency test failed — so silently discarding the observation collapsed a stale
# review into ``absent``. The two states have OPPOSITE remedies (re-trigger a
# re-review vs escalate a bot that never engaged), which is why the observation is
# now emitted instead of dropped.
#
# The bot population is DERIVED from the registry rather than named, so a bot that
# newly opts into ``participation_requires_update`` inherits every case below
# instead of silently escaping it. It is imported by bare name from this subtree's
# ``_github_pr_fixtures`` helper, which is its single home in the test tree and
# guards it non-empty at import — re-deriving or hand-listing it here would be the
# duplicate definition that guard exists to forbid.

#: ``bot_kind`` -> ``author_login``, inverted from the registry's forward map so a
#: comment fixture can be authored for a derived bot without naming its login.
_BOT_KIND_TO_LOGIN = {kind: login for login, kind in bot_registry.login_to_bot_kind().items()}


def test_the_currency_subject_population_guard_is_exercised():
    """The population's import-time vacuity guard admits the real set and rejects an empty one.

    A parametrize over an empty tuple produces a skip, not a failure, so an unguarded
    empty population would let every case below report clean while covering nothing.
    Both controls are asserted: a guard only ever observed on its PASSING input proves
    nothing about what it rejects.
    """
    assert CURRENCY_SUBJECT_BOT_COUNT == len(CURRENCY_SUBJECT_BOTS)
    assert CURRENCY_SUBJECT_BOT_COUNT > 0
    assert guard_non_empty(CURRENCY_SUBJECT_BOTS, 'CURRENCY_SUBJECT_BOTS', 'the registry')
    with pytest.raises(VacuousPopulationError, match='reporting clean while covering nothing'):
        guard_non_empty((), 'CURRENCY_SUBJECT_BOTS', 'a registry declaring no such bot')


def test_currency_anchor_is_recorded_in_the_ledger_on_credit(plan_context, monkeypatch):
    """The currency anchor is DERIVED from the production ledger, not hand-listed — D4(d).

    D0 named the currency ledger as the single source the currency test compares
    against. A hand-maintained list of currency sites is the same defect class this
    plan closes, so the population of currency-subject bots is registry-derived and
    guarded non-empty at import in ``_github_pr_fixtures`` (``CURRENCY_SUBJECT_BOTS``, in
    the ``_dispatch_roster`` "guard against vacuity" spirit), and the anchor is the ledger
    the producer itself writes on credit. This drives a real fetch and reads the ledger
    back through the SUT's own reader: a credited comment records its
    ``(merge_candidate_sha, updated_at)``, so the derivation is re-run against production
    code rather than a copy.
    """
    bot = CURRENCY_SUBJECT_BOTS[0]
    plan_id = f'gh-pr-ledger-{bot}'
    comment = _publish_comment(bot, 'c-ledger', created_at=_at(1))
    _patch_provider(monkeypatch, [comment], head_sha=_HEAD_A)
    result = _run_fetch(140, plan_id)
    assert result['participated_bots'] == [{'bot_kind': bot, 'evidence_kind': comment['kind']}]

    ledger = github_pr._recorded_currency_records(plan_id)
    # The reader returns THREE states — absent, invalid-legacy, and a usable anchor.
    # A credit must produce the third: both that it is not the sentinel, and that the
    # anchor it carries is the merge candidate the credit was granted against.
    record = ledger.get((bot, 'c-ledger'))
    assert record == (_HEAD_A, comment['updated_at'])
    assert not isinstance(record, github_pr._InvalidLegacyRecord)


@pytest.mark.parametrize('bot_kind', CURRENCY_SUBJECT_BOTS)
def test_edit_at_one_commit_does_not_credit_a_later_commit(
    bot_kind, plan_context, monkeypatch
):
    """An in-place edit credits the commit it was made against, NOT every later HEAD.

    The defect PR-Agent flagged on #1141: with the edit arm keyed on
    ``updated_at != created_at`` (a permanent "was ever edited" flag), a comment edited
    at commit N was credited at N+1, N+2, ... even without re-review, defeating the
    currency check for the edit case. The ledger fix measures a fresh edit against the
    recorded ``updated_at`` instead, so the edit at N credits N (and its re-fetches),
    the re-review edit at N+1 credits N+1, but a further HEAD advance with NO new edit is
    stale.
    """
    plan_id = f'gh-pr-edit-once-{bot_kind}'
    # HEAD_A: first observation, credited.
    base = _publish_comment(bot_kind, 'guide-1', created_at=_at(1))
    _patch_provider(monkeypatch, [base], head_sha=_HEAD_A)
    _run_fetch(135, plan_id)

    # HEAD_B: the bot edits its comment in place — a genuine re-review, credited.
    edited = _publish_comment(bot_kind, 'guide-1', created_at=_at(1), updated_at=_at(9))
    _patch_provider(monkeypatch, [edited], head_sha=_HEAD_B)
    at_b = _run_fetch(135, plan_id)
    assert at_b['participated_bots'] == [{'bot_kind': bot_kind, 'evidence_kind': edited['kind']}]

    # HEAD_C: the SAME edited comment (no NEW edit since B) must NOT credit the later
    # commit — the false positive PR-Agent found, now closed.
    _patch_provider(monkeypatch, [edited], head_sha=_HEAD_C)
    at_c = _run_fetch(135, plan_id)
    assert at_c['participated_bots'] == []
    assert at_c['stale_participation_bots'] == [
        {'bot_kind': bot_kind, 'evidence_kind': edited['kind']}
    ]


def _publish_comment(bot_kind, comment_id, *, created_at, updated_at=None, body=None):
    """A comment in ``bot_kind``'s FIRST declared publish shape.

    ``updated_at`` defaults to ``created_at`` — the unchanged shape the movement
    guard denies. The body is substantive and carries no clean-shape marker, so no
    pre-filter layer drops it: these cases are about the movement guard, not noise.
    The ``kind`` is read from the registry rather than written literally, so the
    comment is always in a shape that bot really publishes.
    """
    return {
        'id': comment_id,
        'author': _BOT_KIND_TO_LOGIN[bot_kind],
        'thread_id': '',
        'kind': bot_registry.participation_evidence(bot_kind)[0],
        'body': body or 'The retry helper drops the final attempt when max_attempts is 1.',
        'resolved': False,
        'created_at': created_at,
        'updated_at': updated_at or created_at,
    }


# --- D4: the currency credit is anchored to the merge candidate SHA, and idempotent.
#
# ``_HEAD_A`` / ``_HEAD_B`` model a loop-back / force-push: the same unchanged comment
# reviewed at ``_HEAD_A`` is fresh while the merge candidate IS ``_HEAD_A`` and stale
# once HEAD advances to ``_HEAD_B``. The two members below are a MATCHED PAIR that
# differs only in whether the merge candidate still equals the reviewed commit — which
# is the discrimination the pre-fix currency test (which read observation history, no
# SHA) could not make: pre-fix, both members returned the same second-fetch answer
# (``participated_stale``), so the same-HEAD member fails against the pre-fix code.
_HEAD_A = 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
_HEAD_B = 'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb'
_HEAD_C = 'cccccccccccccccccccccccccccccccccccccccc'


@pytest.mark.parametrize('bot_kind', CURRENCY_SUBJECT_BOTS)
def test_second_fetch_at_the_same_head_stays_participated(
    bot_kind, plan_context, monkeypatch
):
    """Re-evaluating at an UNCHANGED HEAD returns the same verdict — the observer-effect regression.

    D4(b)/(c) and the core defect this plan closes. The currency credit is an SHA
    comparison against the merge candidate, so evaluating participation a second time
    at the same HEAD — with the observation ledger written by the first fetch in
    between — returns the SAME answer. This FAILS against the pre-fix code, which
    *consumed* the first-presence arm on the first fetch and flipped the identical
    unchanged comment ``participated`` -> ``participated_stale`` on the second look at
    the same tree.
    """
    plan_id = f'gh-pr-idem-{bot_kind}'
    comment = _publish_comment(bot_kind, 'guide-1', created_at=_at(1))
    _patch_provider(monkeypatch, [comment], head_sha=_HEAD_A)

    first = _run_fetch(130, plan_id)
    # The ledger is written between the two evaluations (this is the whole point).
    second = _run_fetch(130, plan_id)

    assert first['status'] == 'success' and second['status'] == 'success'
    expected = [{'bot_kind': bot_kind, 'evidence_kind': comment['kind']}]
    assert first['participated_bots'] == expected
    assert first['stale_participation_bots'] == []
    # Idempotent: the second evaluation matches the first, byte for byte.
    assert second['participated_bots'] == first['participated_bots']
    assert second['stale_participation_bots'] == first['stale_participation_bots']


@pytest.mark.parametrize('bot_kind', CURRENCY_SUBJECT_BOTS)
def test_unresolvable_head_sha_fails_closed_and_stays_idempotent(
    bot_kind, plan_context, monkeypatch
):
    """An unreadable merge-candidate SHA withholds the credit AND returns the same answer twice.

    ``fetch_pr_head_sha`` returns an empty string on any provider-failure path. The
    credit cannot then be anchored to a commit, so the currency test withholds it —
    the fail-closed direction, since crediting an unverified review is the expensive
    error. The property the plan insists on is that the verdict does not depend on how
    many times it is evaluated: two fetches at an unreadable HEAD return the SAME
    (blocking) answer, never a flip. Without the fail-closed guard on the
    first-observation arm the first fetch would credit and the second — reading the
    recorded empty SHA — would go stale, re-introducing an observer effect on the one
    path where the SHA is absent.

    The withheld credit is reported as UNDECIDABLE, not as stale. A stale verdict
    prescribes re-triggering the review, which cannot fix a failed head read, so the
    placement is re-derived here rather than left asserting the retired stale-set
    position.
    """
    plan_id = f'gh-pr-empty-sha-{bot_kind}'
    comment = _publish_comment(bot_kind, 'guide-1', created_at=_at(1))
    _patch_provider(monkeypatch, [comment], head_sha='')

    first = _run_fetch(134, plan_id)
    second = _run_fetch(134, plan_id)

    assert first['status'] == 'success' and second['status'] == 'success'
    # Fail-closed: an un-anchorable comment is not credited as a proven participant.
    assert first['participated_bots'] == []
    assert first['stale_participation_bots'] == []
    assert first['merge_candidate_sha_resolved'] is False
    assert first['undecidable_participation_bots'] == [
        {'bot_kind': bot_kind, 'evidence_kind': comment['kind']}
    ]
    # Idempotent: the second evaluation matches the first exactly.
    assert second['participated_bots'] == first['participated_bots']
    assert second['stale_participation_bots'] == first['stale_participation_bots']
    assert second['undecidable_participation_bots'] == first['undecidable_participation_bots']


@pytest.mark.parametrize('bot_kind', CURRENCY_SUBJECT_BOTS)
def test_review_predating_the_merge_candidate_is_stale(
    bot_kind, plan_context, monkeypatch
):
    """After HEAD advances past the reviewed commit, the unchanged comment is STALE — D4(a).

    The matched control for the idempotence case above: identical observation history
    (the comment is observed once, unchanged, ``updated_at == created_at``), differing
    ONLY in whether the merge candidate is still the commit the comment was recorded
    against. A genuine loop-back / force-push advances HEAD, and the same comment now
    proves only a review of the earlier commit — so it resolves to
    ``participated_stale``, not ``participated``. This proves the credit is anchored
    to the commit rather than being "always participated"; together with the
    same-HEAD case above it is the pair the pre-fix code could not tell apart.
    """
    plan_id = f'gh-pr-advanced-{bot_kind}'
    comment = _publish_comment(bot_kind, 'guide-1', created_at=_at(1))
    _patch_provider(monkeypatch, [comment], head_sha=_HEAD_A)
    first = _run_fetch(131, plan_id)
    assert first['participated_bots'] == [{'bot_kind': bot_kind, 'evidence_kind': comment['kind']}]

    # Loop-back / force-push: HEAD advances, the comment does not move.
    _patch_provider(monkeypatch, [comment], head_sha=_HEAD_B)
    second = _run_fetch(131, plan_id)
    assert second['participated_bots'] == []
    assert second['stale_participation_bots'] == [
        {'bot_kind': bot_kind, 'evidence_kind': comment['kind']}
    ]


@pytest.mark.parametrize('bot_kind', CURRENCY_SUBJECT_BOTS)
def test_in_place_edit_credits_participation_after_a_head_advance(
    bot_kind, plan_context, monkeypatch
):
    """An in-place EDIT re-credits the bot even after HEAD advances past the recorded commit.

    The edit-movement arm of the currency test, exercised where it actually matters:
    HEAD has advanced, so the SHA arm misses, and only the edit (``updated_at`` moved
    since the comment was posted) can credit the bot. This is PR-Agent's real
    re-review shape — it edits its one persistent comment rather than posting a new
    one — so without this arm every genuine re-review after a loop-back would resolve
    stale forever.
    """
    plan_id = f'gh-pr-moved-{bot_kind}'
    comment = _publish_comment(bot_kind, 'guide-1', created_at=_at(1))
    _patch_provider(monkeypatch, [comment], head_sha=_HEAD_A)
    _run_fetch(132, plan_id)

    edited = _publish_comment(bot_kind, 'guide-1', created_at=_at(1), updated_at=_at(9))
    _patch_provider(monkeypatch, [edited], head_sha=_HEAD_B)
    second = _run_fetch(132, plan_id)

    assert second['status'] == 'success'
    assert second['participated_bots'] == [{'bot_kind': bot_kind, 'evidence_kind': edited['kind']}]
    assert second['stale_participation_bots'] == []


@pytest.mark.parametrize('bot_kind', CURRENCY_SUBJECT_BOTS)
def test_a_fresh_comment_outranks_a_stale_one_through_the_subtraction(
    bot_kind, plan_context, monkeypatch
):
    """One stale and one fresh comment resolves ``participated``, never both states.

    The stale comment is listed FIRST, which is the ordering under which the
    subtraction is load-bearing: the stale observation is recorded before the fresh
    comment is reached, so without subtracting the proven set the bot would be
    reported in BOTH sets and the classifier's branch order would be settling a
    question the producer should have settled. HEAD is advanced between the two
    fetches so ``guide-1`` is GENUINELY stale (reviewed the earlier commit) while
    ``guide-2`` is a fresh review of the merge candidate.
    """
    plan_id = f'gh-pr-stale-subtract-{bot_kind}'
    stale = _publish_comment(bot_kind, 'guide-1', created_at=_at(1))
    _patch_provider(monkeypatch, [stale], head_sha=_HEAD_A)
    _run_fetch(133, plan_id)

    fresh = _publish_comment(
        bot_kind,
        'guide-2',
        created_at=_at(5),
        body='A second pass: this comparison uses == on floats, use math.isclose instead.',
    )
    _patch_provider(monkeypatch, [stale, fresh], head_sha=_HEAD_B)
    second = _run_fetch(133, plan_id)

    assert second['status'] == 'success'
    assert second['participated_bots'] == [{'bot_kind': bot_kind, 'evidence_kind': fresh['kind']}]
    assert second['stale_participation_bots'] == []


# --- D1: the currency test is evaluated for EVERY evidence comment, not just the first.
#
# A currency-subject bot declares several publish shapes and can have several evidence
# comments live at once. While the participation loop short-circuited at the bot's first
# credit, only that one comment was evaluated and recorded in the currency ledger; every
# LATER comment stayed unrecorded, so on the next fetch it had no ledger row, took the
# first-observation arm, and credited the bot at whatever HEAD was resolvable — bypassing
# the currency test the first comment had just failed.


def _two_evidence_comments(bot_kind):
    """Two unchanged evidence comments of one bot, both in a declared publish shape."""
    return [
        _publish_comment(bot_kind, 'guide-a', created_at=_at(1)),
        _publish_comment(
            bot_kind,
            'guide-b',
            created_at=_at(2),
            body='A second observation: the retry budget is read before the config is loaded.',
        ),
    ]


@pytest.mark.parametrize('bot_kind', CURRENCY_SUBJECT_BOTS)
def test_two_unchanged_evidence_comments_are_stale_at_an_advanced_head(
    bot_kind, plan_context, monkeypatch
):
    """Neither of a bot's two unchanged comments credits it once HEAD advances.

    Both are credited and recorded at HEAD_A. At HEAD_B neither has been edited and
    both are recorded against HEAD_A, so BOTH fail the currency test and the bot
    resolves to ``stale_participation_bots[]`` — never ``participated_bots[]``.

    While the loop short-circuited at the first credit, only ``guide-a`` was ever
    evaluated and recorded, so at HEAD_B ``guide-b`` had no ledger row, took the
    first-observation arm, and credited the bot at the very HEAD the first comment
    had just been found stale against.
    """
    plan_id = f'gh-pr-every-comment-{bot_kind}'
    comments = _two_evidence_comments(bot_kind)

    _patch_provider(monkeypatch, comments, head_sha=_HEAD_A)
    at_a = _run_fetch(160, plan_id)
    assert at_a['participated_bots'] == [
        {'bot_kind': bot_kind, 'evidence_kind': comments[0]['kind']}
    ]

    _patch_provider(monkeypatch, comments, head_sha=_HEAD_B)
    at_b = _run_fetch(160, plan_id)
    assert at_b['status'] == 'success'
    assert at_b['participated_bots'] == []
    assert at_b['stale_participation_bots'] == [
        {'bot_kind': bot_kind, 'evidence_kind': comments[0]['kind']}
    ]


@pytest.mark.parametrize('bot_kind', CURRENCY_SUBJECT_BOTS)
def test_a_rejecting_fetch_stages_no_ledger_row_so_the_verdict_holds(
    bot_kind, plan_context, monkeypatch
):
    """A third fetch at the UNCHANGED advanced HEAD returns the identical verdict.

    The pass-only staging rule, pinned by its consequence. A ledger row is written
    only for a comment that PASSED the currency test on that fetch; a failing comment
    leaves its row exactly as it stood. Were the rejecting fetch at HEAD_B to stage
    HEAD_B onto both stale comments, the very next fetch would read
    ``recorded_sha == merge_candidate_sha`` and credit the comments it had just
    rejected — a stale review laundered into a credit by the act of rejecting it.
    """
    plan_id = f'gh-pr-pass-only-staging-{bot_kind}'
    comments = _two_evidence_comments(bot_kind)

    _patch_provider(monkeypatch, comments, head_sha=_HEAD_A)
    _run_fetch(161, plan_id)

    _patch_provider(monkeypatch, comments, head_sha=_HEAD_B)
    at_b = _run_fetch(161, plan_id)

    # Third fetch: nothing changed — not the comments, not HEAD.
    third = _run_fetch(161, plan_id)
    assert third['status'] == 'success'
    assert third['participated_bots'] == at_b['participated_bots'] == []
    assert third['stale_participation_bots'] == at_b['stale_participation_bots']
    assert third['stale_participation_bots'] == [
        {'bot_kind': bot_kind, 'evidence_kind': comments[0]['kind']}
    ]

    # And the ledger still anchors both comments on HEAD_A — the rejecting fetch wrote
    # nothing, which is what makes the verdict above hold rather than flip.
    ledger = github_pr._recorded_currency_records(plan_id)
    assert ledger[(bot_kind, 'guide-a')][0] == _HEAD_A
    assert ledger[(bot_kind, 'guide-b')][0] == _HEAD_A


# --- D2: every arm of the currency predicate fails closed on degenerate input.
#
# Each arm previously failed OPEN in its own way: the first-observation arm credited any
# comment absent from the ledger whatever commit it had really read; the fresh-edit arm
# was unguarded on a resolvable head; and a pre-upgrade row with no reviewed SHA read as
# ``('', '')`` and fell through to the edit arm, which is true for essentially any real
# comment. Withholding a credit is the cheap error; crediting an unverified review is the
# expensive one, so every arm now errs toward withholding.


@pytest.mark.parametrize('bot_kind', CURRENCY_SUBJECT_BOTS)
def test_a_comment_predating_the_merge_candidate_is_stale_on_first_observation(
    bot_kind, plan_context, monkeypatch
):
    """A comment older than the commit cannot be an observation of it — even unseen.

    The first-observation arm's ledger-silence means only that THIS PLAN has not seen
    the comment before; it never proved the comment reviewed the merge candidate. When
    the commit's own timestamp is readable, a comment whose timestamps precede it is
    positively disqualified: the comment demonstrably existed before the code did.
    """
    plan_id = f'gh-pr-predates-{bot_kind}'
    comment = _publish_comment(bot_kind, 'guide-old', created_at=_at(1))

    _patch_provider(monkeypatch, [comment], head_sha=_HEAD_A, head_committed_at=_at(30))
    result = _run_fetch(170, plan_id)

    assert result['status'] == 'success'
    assert result['participated_bots'] == []
    assert result['stale_participation_bots'] == [
        {'bot_kind': bot_kind, 'evidence_kind': comment['kind']}
    ]
    # A withheld credit stages no anchor either — otherwise the next fetch would read
    # the comment as SHA-current and credit what this fetch refused.
    assert github_pr._recorded_currency_records(plan_id) == {}


@pytest.mark.parametrize('bot_kind', CURRENCY_SUBJECT_BOTS)
def test_a_fresh_edit_at_an_unreadable_head_blocks_on_both_fetches(
    bot_kind, plan_context, monkeypatch
):
    """An unreadable head fails closed on the EDIT arm too, and writes no poisoned row.

    An edit proves a fresh review of *something*; without a readable head there is no
    commit to say it was a review OF. The answer must also be the SAME on a second
    consecutive fetch — a verdict that flips between two identical fetches is the
    observer effect this predicate exists to close. And no row may be written carrying
    an empty ``reviewed_commit_sha``: such a row can never again equal a merge
    candidate, so it would poison the key permanently.
    """
    plan_id = f'gh-pr-unreadable-head-{bot_kind}'
    base = _publish_comment(bot_kind, 'guide-1', created_at=_at(1))
    _patch_provider(monkeypatch, [base], head_sha=_HEAD_A)
    _run_fetch(171, plan_id)
    ledger_after_credit = github_pr._recorded_currency_records(plan_id)
    assert ledger_after_credit[(bot_kind, 'guide-1')] == (_HEAD_A, base['updated_at'])

    edited = _publish_comment(bot_kind, 'guide-1', created_at=_at(1), updated_at=_at(9))
    _patch_provider(monkeypatch, [edited], head_sha='')
    first = _run_fetch(171, plan_id)
    second = _run_fetch(171, plan_id)

    assert first['participated_bots'] == []
    # The credit is withheld on the EDIT arm — and disclosed as undecidable rather than
    # stale, because the head read is what failed (deliverable 4's routing).
    assert first['stale_participation_bots'] == []
    assert first['undecidable_participation_bots'] == [
        {'bot_kind': bot_kind, 'evidence_kind': edited['kind']}
    ]
    assert second['participated_bots'] == first['participated_bots']
    assert second['stale_participation_bots'] == first['stale_participation_bots']
    assert second['undecidable_participation_bots'] == first['undecidable_participation_bots']

    ledger = github_pr._recorded_currency_records(plan_id)
    assert ledger == ledger_after_credit
    assert not any(isinstance(v, github_pr._InvalidLegacyRecord) for v in ledger.values())


@pytest.mark.parametrize('bot_kind', CURRENCY_SUBJECT_BOTS)
def test_a_pre_upgrade_key_only_ledger_row_resolves_stale_not_participated(
    bot_kind, plan_context, monkeypatch
):
    """A row carrying no reviewed SHA is REFUSED, never read as a first observation.

    Dropping such a row is the non-fix: an absent key takes the first-observation arm,
    so the bot would be credited at any resolvable advanced HEAD — the very credit the
    row's unreadability should deny. The row survives the read as a stated third state
    and the predicate refuses it, so the bot resolves ``participated_stale``.

    The assertion is on the RESOLVED STATE, not on an equivalence with some other
    input: proving this ledger behaves 'the same as' an empty one would certify the
    drop-the-row non-fix rather than refute it.
    """
    from jsonl_store import append_jsonl

    plan_id = f'gh-pr-legacy-row-{bot_kind}'
    comment = _publish_comment(bot_kind, 'guide-1', created_at=_at(1))
    # A pre-upgrade row: the key, and no ``reviewed_commit_sha`` field at all.
    append_jsonl(
        github_pr._currency_ledger_path(plan_id),
        {'bot_kind': bot_kind, 'comment_id': 'guide-1'},
    )

    _patch_provider(monkeypatch, [comment], head_sha=_HEAD_B)
    result = _run_fetch(172, plan_id)

    # The resolved state first: this is the claim, and it must be what fails when the
    # predicate regresses — not a downstream assertion about the reader's vocabulary.
    assert result['status'] == 'success'
    assert result['participated_bots'] == []
    assert result['stale_participation_bots'] == [
        {'bot_kind': bot_kind, 'evidence_kind': comment['kind']}
    ]
    # ...and the mechanism that produced it: the row survived the read as the stated
    # third state rather than being dropped or coerced into a usable-looking anchor.
    assert (
        github_pr._recorded_currency_records(plan_id)[(bot_kind, 'guide-1')]
        is github_pr.INVALID_LEGACY_RECORD
    )


# --- D3: an unresolvable merge candidate is UNDECIDABLE, never blocking-stale.
#
# ``fetch_pr_head_sha`` returns '' on any failure path. Reporting the affected bot as
# stale prescribes "re-trigger the review", a remedy that cannot fix a failed read; and
# reporting nothing at all leaves the caller unable to tell an unread head from a read
# one. The producer therefore discloses the read itself and carries the affected bots in
# their own disjoint set.


@pytest.mark.parametrize('bot_kind', CURRENCY_SUBJECT_BOTS)
def test_a_credited_bot_becomes_undecidable_when_the_head_read_fails(
    bot_kind, plan_context, monkeypatch
):
    """A resolved-then-unresolved sequence moves the bot to undecidable, not to stale.

    Fetch 1 reads a real head and credits the bot. Fetch 2 cannot read the head at all.
    The bot is then in NEITHER existing set — not credited (nothing anchors it) and not
    stale (its remedy would be a re-review, which cannot fix a read failure) — and the
    return says so in as many words via ``merge_candidate_sha_resolved: false``.

    The assertions are on the PRODUCER's emitted sets only. No downstream classification
    is asserted, because ``review_completeness``'s taxonomy has no member for this state
    yet: a test written against it would pin the consumer gap rather than the behaviour.
    """
    plan_id = f'gh-pr-undecidable-{bot_kind}'
    comment = _publish_comment(bot_kind, 'guide-1', created_at=_at(1))

    _patch_provider(monkeypatch, [comment], head_sha=_HEAD_A)
    credited = _run_fetch(180, plan_id)
    assert credited['merge_candidate_sha_resolved'] is True
    assert credited['participated_bots'] == [
        {'bot_kind': bot_kind, 'evidence_kind': comment['kind']}
    ]
    assert credited['undecidable_participation_bots'] == []

    _patch_provider(monkeypatch, [comment], head_sha='')
    unread = _run_fetch(180, plan_id)

    assert unread['status'] == 'success'
    assert unread['merge_candidate_sha_resolved'] is False
    assert unread['participated_bots'] == []
    assert unread['stale_participation_bots'] == []
    assert unread['undecidable_participation_bots'] == [
        {'bot_kind': bot_kind, 'evidence_kind': comment['kind']}
    ]


# --- D4: the cross-iteration filing dedup identity carries an EDIT TERM.
#
# The identity is (bot_kind, comment_id, edit_term). Under the old two-term key a bot
# that edits its one persistent comment in place kept the same comment_id forever, so an
# edit that replaced a clean summary with a real finding was dropped as a duplicate while
# the currency test credited the bot as participating: the reviewer read present and
# clean, and its feedback never became a finding.

_GUIDE_CLEAN_BODY = 'Nothing further to report on this pass; the change reads consistently.'
_GUIDE_FINDING_BODY = 'The retry helper drops the final attempt when max_attempts is 1.'


def _edit_term_comment(bot_kind, *, body, updated_at=None):
    """One persistent comment of ``bot_kind``, re-published with a new body/timestamp."""
    comment = _publish_comment(bot_kind, 'guide-persistent', created_at=_at(1), body=body)
    comment['updated_at'] = updated_at if updated_at is not None else _at(1)
    return comment


@pytest.mark.parametrize('bot_kind', CURRENCY_SUBJECT_BOTS)
def test_an_edited_comment_is_filed_as_new_information(bot_kind, plan_context, monkeypatch):
    """A moved ``updated_at`` with a changed body files a NEW finding, never a duplicate.

    This is the defect in full: the same ``comment_id``, so the two-term key matched and
    the edited review — carrying a real finding — was dropped as already-seen.
    """
    plan_id = f'gh-pr-edit-term-files-{bot_kind}'
    clean = _edit_term_comment(bot_kind, body=_GUIDE_CLEAN_BODY)
    _patch_provider(monkeypatch, [clean], head_sha=_HEAD_A)
    first = _run_fetch(190, plan_id)
    assert first['count_stored'] == 1
    assert first['count_skipped_duplicate'] == 0

    edited = _edit_term_comment(bot_kind, body=_GUIDE_FINDING_BODY, updated_at=_at(9))
    _patch_provider(monkeypatch, [edited], head_sha=_HEAD_A)
    second = _run_fetch(190, plan_id)

    assert second['status'] == 'success'
    assert second['count_stored'] == 1
    assert second['count_skipped_duplicate'] == 0
    assert len(query_findings(plan_id, finding_type='pr-comment')['findings']) == 2


@pytest.mark.parametrize('bot_kind', CURRENCY_SUBJECT_BOTS)
def test_an_unchanged_comment_still_dedupes_under_the_widened_key(
    bot_kind, plan_context, monkeypatch
):
    """The widening must not turn every re-fetch into a re-file.

    The matched control for the case above: an unchanged comment carries an unchanged
    edit term, so the three-term key still matches and the comment still dedupes.
    """
    plan_id = f'gh-pr-edit-term-dedupes-{bot_kind}'
    clean = _edit_term_comment(bot_kind, body=_GUIDE_CLEAN_BODY)
    _patch_provider(monkeypatch, [clean], head_sha=_HEAD_A)
    first = _run_fetch(191, plan_id)
    assert first['count_stored'] == 1

    second = _run_fetch(191, plan_id)

    assert second['status'] == 'success'
    assert second['count_stored'] == 0
    assert second['count_skipped_duplicate'] == 1
    stored = query_findings(plan_id, finding_type='pr-comment')['findings']
    assert len(stored) == 1
    # The third term SURVIVED into the store. Without this the widened key would be
    # write-only — every stored finding would read back as a pre-upgrade row and the
    # dedup would silently fall back to two terms, which is indistinguishable from the
    # defect while every count above still looks right.
    assert github_pr._detail_field(stored[0].get('detail'), github_pr._EDIT_TERM_DETAIL) == (
        clean['updated_at']
    )


@pytest.mark.parametrize('bot_kind', CURRENCY_SUBJECT_BOTS)
def test_a_pre_upgrade_finding_without_an_edit_term_does_not_refile_history(
    bot_kind, plan_context, monkeypatch
):
    """A finding stored before the edit term existed still dedupes, against ANY term.

    A pre-upgrade row carries no ``edit_term`` line, so it can match no three-term key.
    Were it not deduped on the two-term key, the first fetch after this widening landed
    would re-file a PR's entire comment history at once — a worse outcome than the
    defect being fixed.
    """
    plan_id = f'gh-pr-preupgrade-dedup-{bot_kind}'
    comment = _edit_term_comment(bot_kind, body=_GUIDE_CLEAN_BODY)

    # A pre-upgrade finding: the detail block the producer wrote before the third term
    # existed — every line it carried then, and no ``edit_term``.
    added = _live_findings_core().add_finding(
        plan_id=plan_id,
        finding_type='pr-comment',
        title=f"PR #192 {comment['kind']} comment by {comment['author']} (guide-persistent)",
        detail=(
            'pr_number: 192\n'
            f"kind: {comment['kind']}\n"
            f"author: {comment['author']}\n"
            'thread_id: \n'
            'comment_id: guide-persistent'
        ),
        bot_kind=bot_kind,
    )
    assert added['status'] == 'success'

    _patch_provider(monkeypatch, [comment], head_sha=_HEAD_A)
    result = _run_fetch(192, plan_id)

    assert result['status'] == 'success'
    assert result['count_stored'] == 0
    assert result['count_skipped_duplicate'] == 1
    stored = query_findings(plan_id, finding_type='pr-comment')['findings']
    assert len(stored) == 1
    # The surviving row is the PRE-UPGRADE one, still carrying no edit term — proving
    # the two-term fallback is what deduped it, rather than the row having been
    # rewritten or replaced by a three-term one.
    assert github_pr._detail_field(stored[0].get('detail'), github_pr._EDIT_TERM_DETAIL) == ''


# --- D5: the currency ledger is named for what it holds, and the rename loses no anchor.
#
# The ledger's on-disk name changed from one describing a NOISE-DROP side effect to one
# naming the currency anchor it actually holds. Every row already written under the old
# name is a real credit, so the reader opens BOTH filenames and the writer only ever
# appends to the current one. The read is DATA MIGRATION, not a deprecation shim: dropping
# it hands every comment recorded under the old name back to the first-observation arm,
# which credits it at any resolvable HEAD — the exact false credit the ledger prevents.

_LEGACY_LEDGER_FILENAME = 'pr-noise-dropped-comments.jsonl'


def _write_ledger_row(path, bot_kind, comment_id, sha, updated_at):
    """Append one currency-ledger row to ``path`` in the producer's own row shape."""
    from jsonl_store import append_jsonl

    append_jsonl(
        path,
        {
            'bot_kind': bot_kind,
            'comment_id': comment_id,
            'reviewed_commit_sha': sha,
            'updated_at': updated_at,
        },
    )


def test_the_pre_rename_ledger_filename_is_the_literal_real_plans_carry():
    """The migration target is an exact on-disk name, so it is pinned as a literal.

    Every other name in this area is derived, but this one cannot be: it is the string
    already written into existing plan directories. A constant that drifted from it would
    make the reader open a file nothing ever wrote, and every case below would still pass
    — reading an absent legacy file and an absent current file are indistinguishable.
    """
    assert github_pr._LEGACY_CURRENCY_LEDGER_ARTIFACT == _LEGACY_LEDGER_FILENAME
    # ...and the current name says what the file holds, rather than a drop side effect.
    assert 'currency' in github_pr._CURRENCY_LEDGER_ARTIFACT
    assert 'dropped' not in github_pr._CURRENCY_LEDGER_ARTIFACT
    assert github_pr._CURRENCY_LEDGER_ARTIFACT != github_pr._LEGACY_CURRENCY_LEDGER_ARTIFACT


@pytest.mark.parametrize('bot_kind', CURRENCY_SUBJECT_BOTS)
def test_a_ledger_written_under_the_pre_rename_filename_is_still_read(
    bot_kind, plan_context, monkeypatch
):
    """An anchor recorded under the OLD filename still denies a credit at an advanced HEAD.

    The migration's whole point, asserted through its CONSEQUENCE rather than through the
    reader's return alone: a plan whose ledger predates the rename holds real credits, and
    a reader that stopped opening that file would find no row for the comment, take the
    first-observation arm, and credit it at whatever HEAD is resolvable.
    """
    plan_id = f'gh-pr-legacy-filename-read-{bot_kind}'
    comment = _publish_comment(bot_kind, 'guide-1', created_at=_at(1))
    _write_ledger_row(
        github_pr._legacy_currency_ledger_path(plan_id),
        bot_kind,
        'guide-1',
        _HEAD_A,
        comment['updated_at'],
    )

    _patch_provider(monkeypatch, [comment], head_sha=_HEAD_B)
    result = _run_fetch(200, plan_id)

    assert result['status'] == 'success'
    assert result['participated_bots'] == []
    assert result['stale_participation_bots'] == [
        {'bot_kind': bot_kind, 'evidence_kind': comment['kind']}
    ]
    # ...and the mechanism: the row reached the reader as a usable anchor, not as the
    # invalid-legacy sentinel and not as an absent key.
    assert github_pr._recorded_currency_records(plan_id)[(bot_kind, 'guide-1')] == (
        _HEAD_A,
        comment['updated_at'],
    )


@pytest.mark.parametrize('bot_kind', CURRENCY_SUBJECT_BOTS)
def test_the_same_fetch_with_no_ledger_at_all_credits_the_comment(
    bot_kind, plan_context, monkeypatch
):
    """Matched negative control: without the legacy row, that very fetch CREDITS the bot.

    Identical comment, identical advanced HEAD — the only difference is whether a row was
    written under the pre-rename filename. Without this control the case above would be
    consistent with the fetch resolving stale for some unrelated reason, and would keep
    passing against a reader that never opened the legacy file.
    """
    plan_id = f'gh-pr-legacy-filename-control-{bot_kind}'
    comment = _publish_comment(bot_kind, 'guide-1', created_at=_at(1))

    _patch_provider(monkeypatch, [comment], head_sha=_HEAD_B)
    result = _run_fetch(201, plan_id)

    assert result['status'] == 'success'
    assert result['participated_bots'] == [
        {'bot_kind': bot_kind, 'evidence_kind': comment['kind']}
    ]
    assert result['stale_participation_bots'] == []


@pytest.mark.parametrize('bot_kind', CURRENCY_SUBJECT_BOTS)
def test_a_populated_current_ledger_does_not_hide_the_pre_rename_rows(
    bot_kind, plan_context, monkeypatch
):
    """⛔ The per-FILE fallback shape is refuted here: both files are read, always.

    Reading the old file only while the new one is ABSENT looks equivalent and is not.
    The writer appends only CHANGED records, so the first post-rename credit creates a
    current file holding that ONE key — and from then on a per-file fallback would ignore
    the legacy file entirely, handing every key that lives only there back to the
    first-observation arm.

    The fixture reproduces exactly that state: ``guide-a``'s anchor lives only in the
    legacy file, ``guide-b``'s only in the current file (staged by a real credit). At the
    advanced HEAD BOTH must be stale. Under a per-file fallback ``guide-a`` would be
    first-observed and the bot would be credited.
    """
    plan_id = f'gh-pr-legacy-coexist-{bot_kind}'
    comments = _two_evidence_comments(bot_kind)
    guide_a, guide_b = comments

    # ``guide-a``'s anchor exists ONLY under the pre-rename filename.
    _write_ledger_row(
        github_pr._legacy_currency_ledger_path(plan_id),
        bot_kind,
        'guide-a',
        _HEAD_A,
        guide_a['updated_at'],
    )

    # A real fetch at HEAD_A credits ``guide-b`` for the first time and stages it — which
    # is what CREATES the current file, the precondition the fallback shape trips over.
    _patch_provider(monkeypatch, comments, head_sha=_HEAD_A)
    at_a = _run_fetch(202, plan_id)
    assert at_a['participated_bots'] == [
        {'bot_kind': bot_kind, 'evidence_kind': guide_a['kind']}
    ]
    assert github_pr._currency_ledger_path(plan_id).exists()

    # HEAD advances. Neither comment moved, and both anchors point at HEAD_A.
    _patch_provider(monkeypatch, comments, head_sha=_HEAD_B)
    at_b = _run_fetch(202, plan_id)

    assert at_b['status'] == 'success'
    assert at_b['participated_bots'] == []
    assert at_b['stale_participation_bots'] == [
        {'bot_kind': bot_kind, 'evidence_kind': guide_a['kind']}
    ]
    # Both anchors resolved, each from the file that holds it.
    ledger = github_pr._recorded_currency_records(plan_id)
    assert ledger[(bot_kind, 'guide-a')] == (_HEAD_A, guide_a['updated_at'])
    assert ledger[(bot_kind, 'guide-b')] == (_HEAD_A, guide_b['updated_at'])


@pytest.mark.parametrize('bot_kind', CURRENCY_SUBJECT_BOTS)
def test_a_credit_is_written_only_under_the_current_filename(
    bot_kind, plan_context, monkeypatch
):
    """The pre-rename file is READ and never written — the migration is one-directional.

    Appending to it as well would keep minting rows under a name that no longer says what
    the file holds, which is the state the rename exists to end.
    """
    plan_id = f'gh-pr-write-current-only-{bot_kind}'
    comment = _publish_comment(bot_kind, 'guide-1', created_at=_at(1))
    _patch_provider(monkeypatch, [comment], head_sha=_HEAD_A)

    result = _run_fetch(203, plan_id)

    assert result['participated_bots'] == [
        {'bot_kind': bot_kind, 'evidence_kind': comment['kind']}
    ]
    assert github_pr._currency_ledger_path(plan_id).exists()
    assert not github_pr._legacy_currency_ledger_path(plan_id).exists()


# --- D6: the currency-blind path for append-per-review bots, as an ACCEPTED bounded gap.
#
# A bot declaring ``participation_requires_update: false`` posts a new comment per review,
# so the producer credits it on the presence of a declared publish shape and compares no
# commit. A comment posted against an EARLIER commit therefore still credits it at the
# merge candidate. That is a real gap and it is ACCEPTED — so the contract must SAY so,
# and the code must do what the contract says. Both halves are asserted together, because
# a documented gap nobody re-derives from the code is how the reach drifted in the first
# place.

_CONTRACT_DOC = (
    get_skill_dir('plan-marshall', 'automatic-review') / 'standards' / 'bot-participation-contract.md'
)
_CONTRACT_TEXT = _CONTRACT_DOC.read_text(encoding='utf-8')


def test_the_currency_blind_population_is_derived_and_guarded():
    """The complement is non-empty and disjoint from the currency-subject population.

    Both halves matter. Non-empty, because every case below is parametrized over it and a
    parametrize over an empty tuple SKIPS rather than fails. Disjoint and total, because
    the two populations come from one registry read: a bot that fell out of both, or into
    both, would make one of the two sweeps quietly wrong about which rule governs it.
    """
    assert CURRENCY_BLIND_BOT_COUNT == len(CURRENCY_BLIND_BOTS)
    assert CURRENCY_BLIND_BOT_COUNT > 0
    assert guard_non_empty(CURRENCY_BLIND_BOTS, 'CURRENCY_BLIND_BOTS', 'the registry')
    with pytest.raises(VacuousPopulationError, match='reporting clean while covering nothing'):
        guard_non_empty((), 'CURRENCY_BLIND_BOTS', 'a registry declaring no such bot')

    assert not set(CURRENCY_BLIND_BOTS) & set(CURRENCY_SUBJECT_BOTS)
    assert set(CURRENCY_BLIND_BOTS) | set(CURRENCY_SUBJECT_BOTS) == set(bot_registry.bot_kinds())


def test_the_contract_records_the_currency_blind_gap_rather_than_leaving_it_inferable():
    """The bounded gap is WRITTEN DOWN — reason, bound, and revisit condition.

    A gap a reader can only infer from the rule's silence is one every reader infers
    differently. The contract must name the reach, name the consequence, and say when the
    decision is revisited; asserting only the runtime behaviour would leave the document
    free to keep claiming the rule governs every crediting site.
    """
    assert '### The currency rule — an in-place re-reviewer' in _CONTRACT_TEXT
    assert '#### The currency-blind path for append-per-review bots' in _CONTRACT_TEXT
    # The reach is stated as the registry flag, not as a list of bot names.
    assert '`participation_requires_update: true`' in _CONTRACT_TEXT
    assert '`participation_requires_update: false`' in _CONTRACT_TEXT
    # The retired universal claim is gone — this is the sentence whose reach was wrong.
    assert 'This one rule governs' not in _CONTRACT_TEXT
    # A bounded gap owes all three: why it is accepted, what bounds it, when it reopens.
    assert 'Why the gap is accepted' in _CONTRACT_TEXT
    assert 'What bounds it' in _CONTRACT_TEXT
    assert 'When it is revisited' in _CONTRACT_TEXT


@pytest.mark.parametrize('bot_kind', CURRENCY_BLIND_BOTS)
def test_an_append_per_review_bot_stays_credited_after_a_head_advance(
    bot_kind, plan_context, monkeypatch
):
    """The documented behaviour, asserted as a REACH DIFFERENCE on one identical fixture.

    ⚠ This case is deliberately GREEN against the pre-change code, and that is the correct
    outcome rather than a weakness to hide: deliverable 6's disposition is to DOCUMENT this
    gap, explicitly not to change the behaviour, so a case that went red here would be
    evidence the reach had moved. The discrimination for the documentation itself lives in
    ``test_the_contract_records_the_currency_blind_gap_rather_than_leaving_it_inferable``.

    What keeps it from being a bare restatement is the MATCHED CONTROL run inside it: the
    same comment shape, the same two commits, the same fetch sequence, differing only in
    which population the bot comes from. Asserting only the credit would pass just as
    happily against a producer that had stopped currency-testing anybody; asserting the
    pair pins the reach DIFFERENCE, so a change in either direction — currency-testing
    these bots, or silently exempting the others — turns it red.
    """
    plan_id = f'gh-pr-currency-blind-{bot_kind}'
    comment = _publish_comment(bot_kind, 'guide-1', created_at=_at(1))

    _patch_provider(monkeypatch, [comment], head_sha=_HEAD_A)
    at_a = _run_fetch(204, plan_id)
    expected = [{'bot_kind': bot_kind, 'evidence_kind': comment['kind']}]
    assert at_a['participated_bots'] == expected

    # HEAD advances past the commit the comment could have reviewed; the comment does not
    # move. This is the exact sequence that resolves ``participated_stale`` for a
    # currency-subject bot — the control below re-runs it to prove that is still so.
    _patch_provider(monkeypatch, [comment], head_sha=_HEAD_B)
    at_b = _run_fetch(204, plan_id)

    assert at_b['status'] == 'success'
    # Still credited — the accepted, bounded gap, exercised rather than merely described.
    assert at_b['participated_bots'] == expected
    # And the two states that are structurally unreachable for such a bot stay empty.
    assert at_b['stale_participation_bots'] == []
    assert at_b['undecidable_participation_bots'] == []
    # No ledger row is written for it, in either file — the ledger's reach matches the
    # rule's, so a reader cannot mistake a currency-blind credit for an anchored one.
    assert github_pr._recorded_currency_records(plan_id) == {}

    # MATCHED CONTROL — identical fixture, identical two-fetch sequence, a bot from the
    # OTHER side of the registry partition. It must go stale where this one stayed
    # credited; without it, a producer that currency-tested nobody would pass the above.
    subject_bot = CURRENCY_SUBJECT_BOTS[0]
    subject_plan_id = f'gh-pr-currency-blind-control-{bot_kind}'
    subject_comment = _publish_comment(subject_bot, 'guide-1', created_at=_at(1))
    _patch_provider(monkeypatch, [subject_comment], head_sha=_HEAD_A)
    _run_fetch(205, subject_plan_id)
    _patch_provider(monkeypatch, [subject_comment], head_sha=_HEAD_B)
    subject_at_b = _run_fetch(205, subject_plan_id)

    assert subject_at_b['participated_bots'] == []
    assert subject_at_b['stale_participation_bots'] == [
        {'bot_kind': subject_bot, 'evidence_kind': subject_comment['kind']}
    ]


# =============================================================================
# Refusal CAUSE classification (github_pr.refusal_cause) — size vs quota
# =============================================================================
#
# The orthogonal axis to rate_limit_class (awaitability): whether a refusal was
# caused by the diff being over a per-PR size ceiling (remedy: a smaller diff) or by
# a rate/budget quota (remedy: backoff). ``size`` iff a declared refusal_size_pattern
# matches; every other refusal is ``quota``.

# Sourcery's per-PR size-ceiling refusal — matched by its refusal_patterns (detection)
# AND its refusal_size_patterns (cause), and invisible to the structural recognizer
# ("larger than the review limit of" is a comparison, not an "exceeded" statement).
_SOURCERY_SIZE_NOTICE = (
    '> [!NOTE]\n'
    '> Sorry, your pull request is larger than the review limit of 150000 diff '
    'characters. Please split it into smaller PRs.'
)


def test_refusal_cause_size_matches_the_declared_size_pattern():
    """A refusal matching a bot's ``refusal_size_patterns`` is caused by diff SIZE."""
    assert github_pr.refusal_cause(_SOURCERY_SIZE_NOTICE, 'sourcery') == 'size'


def test_refusal_cause_quota_is_the_default_for_a_non_size_refusal():
    """Any refusal that is not a declared size pattern is a rate/budget QUOTA."""
    # Sourcery's weekly notice is a quota, not a size ceiling.
    assert github_pr.refusal_cause(_RATE_LIMIT_NOTICES['sourcery'], 'sourcery') == 'quota'
    # CodeRabbit declares no size patterns, so its refusal is quota.
    assert github_pr.refusal_cause(_RATE_LIMIT_NOTICES['coderabbit'], 'coderabbit') == 'quota'


def test_refusal_cause_unregistered_bot_is_quota():
    """A structurally-detected refusal with no bot_kind declares no size pattern → quota."""
    assert github_pr.refusal_cause(_RATE_LIMIT_NOTICES['unknown'], None) == 'quota'


def test_refusal_cause_size_pattern_is_bot_scoped():
    """The size pattern is read from the NAMED bot's registry, not any bot's.

    The same size-ceiling body attributed to a bot that declares no size pattern
    classifies quota — the cause is grounded in the bot's own declared patterns.
    """
    assert github_pr.refusal_cause(_SOURCERY_SIZE_NOTICE, 'coderabbit') == 'quota'


def test_fetch_findings_reports_refusal_causes(plan_context, monkeypatch):
    """fetch_findings emits refused_causes[] — the size vs quota CAUSE per refusing bot.

    Sourcery posts its per-PR size-ceiling refusal (cause=size — the remedy is a
    smaller diff); CodeRabbit posts a rate-limit refusal (cause=quota — the remedy is
    backoff). Both are surfaced in refused_bots AND attributed by cause in
    refused_causes, the orthogonal axis to rate_limit_class.
    """
    plan_id = 'gh-pr-refusal-causes'
    comments = [
        {
            'id': 'sr-size',
            'author': 'sourcery-ai',
            'thread_id': '',
            'kind': 'review_body',
            'body': _SOURCERY_SIZE_NOTICE,
            'resolved': False,
        },
        {
            'id': 'cr-quota',
            'author': 'coderabbitai',
            'thread_id': '',
            'kind': 'review_body',
            'body': _RATE_LIMIT_NOTICES['coderabbit'],
            'resolved': False,
        },
    ]
    _patch_provider(monkeypatch, comments)

    result = _run_fetch(106, plan_id)
    assert result['status'] == 'success'
    assert result['refused_bots'] == ['coderabbit', 'sourcery']
    assert result['refused_causes'] == [
        {'bot_kind': 'coderabbit', 'cause': 'quota'},
        {'bot_kind': 'sourcery', 'cause': 'size'},
    ]
    # The CAP rides alongside the cause, read off the SIZE-refusing bot's own notice —
    # and only that bot's: a quota refusal names no diff ceiling, so CodeRabbit
    # contributes no row rather than a zero or an empty one.
    assert result['refused_size_caps'] == [
        {'bot_kind': 'sourcery', 'cap': '150000 diff characters'}
    ]
    # ...and the measurement that makes the recorded gap auditable rather than asserted.
    assert result['measured_diff_size'] == '1240 changed lines'


def test_fetch_findings_size_cause_is_sticky(plan_context, monkeypatch):
    """A bot that posted BOTH a quota notice and a size ceiling records cause=size.

    Size is the more actionable remedy (a smaller diff), so it wins over a quota
    notice on the same PR regardless of order.
    """
    plan_id = 'gh-pr-refusal-cause-sticky'
    comments = [
        {
            'id': 'sr-quota',
            'author': 'sourcery-ai',
            'thread_id': '',
            'kind': 'review_body',
            'body': (
                '> [!NOTE]\n'
                '> Sourcery: you have reached your weekly rate limit of 500000 diff '
                'characters.'
            ),
            'resolved': False,
        },
        {
            'id': 'sr-size',
            'author': 'sourcery-ai',
            'thread_id': '',
            'kind': 'review_body',
            'body': _SOURCERY_SIZE_NOTICE,
            'resolved': False,
        },
    ]
    _patch_provider(monkeypatch, comments)

    result = _run_fetch(107, plan_id)
    assert result['status'] == 'success'
    assert result['refused_bots'] == ['sourcery']
    # Both notices are quota-and-size for the same bot; size wins (more actionable).
    assert result['refused_causes'] == [{'bot_kind': 'sourcery', 'cause': 'size'}]


def test_fetch_findings_size_cause_is_sticky_size_first(plan_context, monkeypatch):
    """Sticky-size holds under the reverse order too: size first, then quota, stays size.

    The stickiness must be order-independent — the symmetry the quota-then-size case
    does not exercise.
    """
    plan_id = 'gh-pr-refusal-cause-sticky-reverse'
    comments = [
        {
            'id': 'sr-size',
            'author': 'sourcery-ai',
            'thread_id': '',
            'kind': 'review_body',
            'body': _SOURCERY_SIZE_NOTICE,
            'resolved': False,
        },
        {
            'id': 'sr-quota',
            'author': 'sourcery-ai',
            'thread_id': '',
            'kind': 'review_body',
            'body': (
                '> [!NOTE]\n'
                '> Sourcery: you have reached your weekly rate limit of 500000 diff '
                'characters.'
            ),
            'resolved': False,
        },
    ]
    _patch_provider(monkeypatch, comments)

    result = _run_fetch(108, plan_id)
    assert result['status'] == 'success'
    assert result['refused_causes'] == [{'bot_kind': 'sourcery', 'cause': 'size'}]


def test_fetch_findings_measures_the_diff_on_a_size_refusal_with_no_stated_cap(
    plan_context, monkeypatch
):
    """⛔ The measurement is gated on the CAUSE, never on a successfully-extracted cap.

    Those two come apart exactly where the measurement matters most. A size refusal
    whose notice states no figure yields NO cap — so a guard keyed on the cap would
    leave the operator with neither number in the one case the feature exists to
    prevent: an unquantified gap it cannot even bound.
    """
    plan_id = 'gh-pr-size-refusal-no-cap'
    comments = [
        {
            'id': 'sr-size-nofigure',
            'author': 'sourcery-ai',
            'thread_id': '',
            'kind': 'review_body',
            # Recognised as a size refusal (the detection marker is number-free by
            # design) but stating no figure, so no cap can be read from it.
            'body': (
                '> [!NOTE]\n'
                '> Sorry, your pull request is larger than the review limit of our '
                'current plan. Please split it into smaller PRs.'
            ),
            'resolved': False,
        },
    ]
    _patch_provider(monkeypatch, comments)

    result = _run_fetch(109, plan_id)
    assert result['status'] == 'success'
    assert result['refused_causes'] == [{'bot_kind': 'sourcery', 'cause': 'size'}]
    # No cap could be read...
    assert result['refused_size_caps'] == []
    # ...but the diff was still measured, so the gap is bounded rather than opaque.
    assert result['measured_diff_size'] == '1240 changed lines'


def test_fetch_findings_does_not_measure_the_diff_without_a_size_refusal(
    plan_context, monkeypatch
):
    """A quota-only refusal names no diff ceiling, so it buys no provider round-trip.

    The measurement is a real extra call; paying it on every fetch would tax the common
    path for a figure with nothing to reconcile against.
    """
    plan_id = 'gh-pr-quota-only-no-measure'
    comments = [
        {
            'id': 'cr-quota-only',
            'author': 'coderabbitai',
            'thread_id': '',
            'kind': 'review_body',
            'body': _RATE_LIMIT_NOTICES['coderabbit'],
            'resolved': False,
        },
    ]
    _patch_provider(monkeypatch, comments)
    # Make any measurement attempt LOUD rather than merely absent from the output.
    monkeypatch.setattr(
        github_pr._github,
        'run_gh',
        lambda *_a, **_k: pytest.fail('measured the diff with no size refusal'),
    )

    result = _run_fetch(110, plan_id)
    assert result['status'] == 'success'
    assert result['refused_causes'] == [{'bot_kind': 'coderabbit', 'cause': 'quota'}]
    assert result['measured_diff_size'] == ''


def test_fetch_findings_reports_an_unmeasurable_diff_as_unknown_never_zero(
    plan_context, monkeypatch
):
    """A failed measurement stays empty. ``0`` would read as an empty diff refused."""
    plan_id = 'gh-pr-size-refusal-unmeasurable'
    comments = [
        {
            'id': 'sr-size-unmeasurable',
            'author': 'sourcery-ai',
            'thread_id': '',
            'kind': 'review_body',
            'body': _SOURCERY_SIZE_NOTICE,
            'resolved': False,
        },
    ]
    _patch_provider(monkeypatch, comments)
    monkeypatch.setattr(github_pr._github, 'run_gh', lambda *_a, **_k: (1, '', 'boom'))

    result = _run_fetch(111, plan_id)
    assert result['status'] == 'success'
    assert result['measured_diff_size'] == ''
    # The cap still travels — the two are independent, so losing one must not lose both.
    assert result['refused_size_caps'] == [
        {'bot_kind': 'sourcery', 'cap': '150000 diff characters'}
    ]


# ============================================================================
# _comment_predates_commit — the comparability guard
# ============================================================================
#
# The predicate promises that THREE undecidable inputs resolve to False: an unreadable
# commit timestamp, an absent comment timestamp, and TIMESTAMPS THAT DO NOT COMPARE.
# The third had no guard — the ordering was a bare lexicographic string compare — so a
# format mismatch did not fail to decide, it decided WRONGLY and confidently: a comment
# stamped ``…T11:30:00-05:00`` names an instant AFTER a commit stamped ``…T12:00:00Z``,
# yet sorts before it, and the withheld-credit guard would fire on a comment that
# post-dates the code. Every case below is a shape whose lexicographic order disagrees
# with (or says nothing about) the real instant order.
#
# The two controls at the end are matched positives: they prove the guard withholds on
# uncomparable input WITHOUT neutering the predicate on the only shape it is valid over.

_ISO_COMMIT_AT = '2026-08-25T12:00:00Z'


@pytest.mark.parametrize(
    ('updated_at', 'created_at', 'why'),
    [
        # Negative UTC offset: the real instant is 16:30Z, four and a half hours AFTER
        # the commit, but '11:30' sorts before '12:00'. The pre-guard compare called
        # this a comment that predates the commit.
        ('2026-08-25T11:30:00-05:00', '', 'negative offset sorts before, happens after'),
        # Fractional seconds: '.' (0x2E) sorts before 'Z' (0x5A), so a comment half a
        # second AFTER the commit sorted before it.
        ('2026-08-25T12:00:00.500000Z', '', 'fractional seconds sort before the Z'),
        # Bare date — names a day, not a moment; nothing about it is comparable to a
        # second-resolution instant.
        ('2026-08-25', '', 'a bare date names no moment'),
        # Epoch seconds: every digit string starting '1' sorts before every ISO string
        # starting '2', so the shape reads as "predates" for the next ~250 years.
        ('1787654400', '', 'epoch seconds sort before every ISO-8601 year'),
        # The comment's OWN two stamps disagree in shape, so ``max`` over them does not
        # select the later moment — guarded before the ordering, not after.
        ('2026-08-25T11:30:00-05:00', '2026-08-25T10:00:00Z', 'max over mixed shapes'),
    ],
)
def test_comment_predates_commit_withholds_when_the_timestamps_do_not_compare(
    updated_at, created_at, why
):
    """An uncomparable timestamp yields the promised False, not a lexicographic guess.

    ⛔ This is the docstring's third undecidable case, which had no guard. Withholding
    here is the fail-closed direction the whole deliverable is about: an unknown
    ordering is not a claim that the comment predates the commit.
    """
    comment = {'updated_at': updated_at, 'created_at': created_at}

    assert github_pr._comment_predates_commit(comment, _ISO_COMMIT_AT) is False, why


def test_comment_predates_commit_withholds_on_an_uncomparable_commit_timestamp():
    """The guard is symmetric: a non-``Z`` COMMIT stamp is equally undecidable.

    Guarding only the comment side would leave the same wrong-ordering claim reachable
    from the other operand.
    """
    comment = {'updated_at': '2026-08-25T09:00:00Z', 'created_at': '2026-08-25T09:00:00Z'}

    assert github_pr._comment_predates_commit(comment, '2026-08-25T12:00:00+02:00') is False


def test_comment_predates_commit_still_decides_two_comparable_timestamps():
    """Matched positive control — a comment that really does predate still reports True.

    Without this, a guard that returned False unconditionally would pass the cases
    above while silently deleting the predicate.
    """
    comment = {'updated_at': '2026-08-25T09:00:00Z', 'created_at': '2026-08-25T08:00:00Z'}

    assert github_pr._comment_predates_commit(comment, _ISO_COMMIT_AT) is True


def test_comment_predates_commit_reports_false_for_a_comment_after_the_commit():
    """Matched negative control — the comparable, NOT-predating case stays False.

    The later of the two stamps is what decides, so a comment created before the commit
    but edited after it does not count as predating it.
    """
    comment = {'updated_at': '2026-08-25T14:00:00Z', 'created_at': '2026-08-25T08:00:00Z'}

    assert github_pr._comment_predates_commit(comment, _ISO_COMMIT_AT) is False

# SPDX-License-Identifier: FSL-1.1-ALv2
"""``github_pr.cmd_fetch_findings``: cross-iteration dedup, classification, and participation.

The producer-side dedup keys on ``(bot_kind, comment_id)`` for every bot kind,
thread-bearing and thread_id-less alike. Covered here: re-fetch idempotence, the
``(bot_kind, comment_id)`` collision boundary, the contentless-boilerplate
pre-filter layer, the per-shape evidence content gate, and the
``stale_participation_bots[]`` currency observation.

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
    MARKER_GATED_EVIDENCE,
    MARKER_GATED_EVIDENCE_COUNT,
    UNGATED_EVIDENCE,
    UNGATED_EVIDENCE_COUNT,
    VacuousPopulationError,
    guard_non_empty,
)
from _pr_agent_guide_bodies import GUIDE_WITH_FINDING, OBSERVED_CLEAN_GUIDE

from conftest import get_script_path, get_skill_dir, load_script_module, run_script

PLAN_IDS: tuple[str, ...] = (
    'gh-pr-bare-flags',
    'gh-pr-bare-warn-but-ingest',
    'gh-pr-barrier-noise',
    'gh-pr-clean-verdict-credited',
    'gh-pr-clean-verdict-edited-in',
    'gh-pr-clean-verdict-walkthrough-only',
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
PLAN_IDS += tuple(f'gh-pr-preupgrade-dedup-{bot_kind}' for bot_kind in CURRENCY_SUBJECT_BOTS)


def _evidence_plan_id(prefix: str, bot_kind: str, shape: str) -> str:
    """The kebab-case plan id a per-(bot, shape) evidence-gate case files against."""
    return f'gh-pr-evidence-{prefix}-{bot_kind}-{shape.replace("_", "-")}'


PLAN_IDS += tuple(
    _evidence_plan_id(prefix, bot_kind, shape)
    for bot_kind, shape, _marker in MARKER_GATED_EVIDENCE
    for prefix in ('gated-marked', 'gated-bare')
)
PLAN_IDS += tuple(_evidence_plan_id('ungated', bot_kind, shape) for bot_kind, shape in UNGATED_EVIDENCE)
github_pr = load_script_module('plan-marshall', 'workflow-integration-github', 'github_pr.py', 'github_pr')
_findings_core = load_script_module('plan-marshall', 'manage-findings', '_findings_core.py', '_findings_core')
_github_pr = sys.modules['_github_pr']
query_findings = _findings_core.query_findings
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
    monkeypatch.setattr(github_pr._github, 'fetch_pr_head_committed_at', lambda pr_number: head_committed_at)
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


def _at(second):
    """ISO-8601 ``created_at`` on a fixed day — only the relative order matters."""
    return f'2026-07-29T10:{second:02d}:00Z'


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
    'sourcery': ('> [!NOTE]\n> Sourcery has reached your weekly review limit. Reviews will resume next Monday.'),
    # Arbitrary unknown/renamed bot: a limit heading + "hit the ... rate limit"
    # + a "try again" service tail. No code names this bot.
    'unknown': (
        '> [!IMPORTANT]\n'
        '> ## API request limit reached\n'
        '>\n'
        '> This bot has hit the hourly rate limit and will try again in 60 minutes.'
    ),
}
_GENUINE_RATE_LIMIT_MENTIONS = {
    # Plain inline comment, no notice structure at all.
    'coderabbit': ('This off-by-one in the slice bound drops the last element; use len(items).'),
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
_DRIFTED_CODERABBIT_NOTICE = (
    '> [!WARNING] > ## Usage limit reached > '
    'This reviewer has reached its usage limit. Reviews will resume after the limit resets.'
)
_AGREEING_CODERABBIT_NOTICE = (
    '> [!WARNING] > ## Review limit reached > Review limit reached. Reviews will resume after the limit resets.'
)
_SOURCERY_SIZE_REFUSAL = (
    'Sourcery was unable to review this pull request because '
    f'{bot_registry.refusal_patterns("sourcery")[0]} 150000 characters. '
    'Reduce the size of the pull request and request another review.'
)


def _drift_records(result):
    return {(r['bot_kind'], r['layer']) for r in result['refusal_pattern_drift']}


_PUBLISH_SHAPE_VOCABULARY: tuple[str, ...] = tuple(
    sorted({shape for bot in bot_registry.bot_kinds() for shape in bot_registry.participation_evidence(bot)})
)
_LOGIN_FOR_KIND: dict[str, str] = {kind: login for login, kind in bot_registry.login_to_bot_kind().items()}
_CODERABBIT_CLEAN_VERDICT = (
    f'{bot_registry.participation_evidence_marker("coderabbit", "issue_comment")}  '
    'No actionable comments were generated in the recent review. 🎉'
)
_CODERABBIT_WALKTHROUGH = (
    '<!-- This is an auto-generated comment: summarize by coderabbit.ai -->\n'
    '## Walkthrough\n'
    'The change gates participation credit on a per-shape content marker.'
)
_SOURCERY_DECLARED_REFUSAL_MARKER = bot_registry.refusal_patterns('sourcery')[0]
_REWORDED_SOURCERY_REFUSAL = (
    f'Sorry, {_SOURCERY_DECLARED_REFUSAL_MARKER.replace("larger than", "over")} our current plan.'
)
_RECOGNISED_SOURCERY_REFUSAL = f'Sorry, {_SOURCERY_DECLARED_REFUSAL_MARKER} our current plan.'


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
_CLASSIFICATION_FLAGS = derive_bot_flags(
    get_script_path('plan-marshall', 'workflow-integration-github', 'github_pr.py'),
    'fetch_findings',
)
assert _CLASSIFICATION_FLAGS, 'derive_bot_flags found no classification flags on fetch_findings'
_PR_AGENT_REQUIRED_MARKERS = bot_registry.contentless_review_markers('cuioss-review-bot')
assert _PR_AGENT_REQUIRED_MARKERS, 'bot_registry declares no contentless review markers for cuioss-review-bot'
_BOT_KIND_TO_LOGIN = {kind: login for login, kind in bot_registry.login_to_bot_kind().items()}


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


_HEAD_A = 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
_HEAD_B = 'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb'
_HEAD_C = 'cccccccccccccccccccccccccccccccccccccccc'
_GUIDE_CLEAN_BODY = 'Nothing further to report on this pass; the change reads consistently.'
_GUIDE_FINDING_BODY = 'The retry helper drops the final attempt when max_attempts is 1.'


def _edit_term_comment(bot_kind, *, body, updated_at=None):
    """One persistent comment of ``bot_kind``, re-published with a new body/timestamp."""
    comment = _publish_comment(bot_kind, 'guide-persistent', created_at=_at(1), body=body)
    comment['updated_at'] = updated_at if updated_at is not None else _at(1)
    return comment


_LEGACY_LEDGER_FILENAME = 'pr-noise-dropped-comments.jsonl'
_CONTRACT_DOC = get_skill_dir('plan-marshall', 'automatic-review') / 'standards' / 'bot-participation-contract.md'
_CONTRACT_TEXT = _CONTRACT_DOC.read_text(encoding='utf-8')
_SOURCERY_SIZE_NOTICE = (
    '> [!NOTE]\n'
    '> Sorry, your pull request is larger than the review limit of 150000 diff '
    'characters. Please split it into smaller PRs.'
)
_ISO_COMMIT_AT = '2026-08-25T12:00:00Z'


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
    byte-identically to the first fetch. The ``_COMMENTS`` fixture spans both
    participation shapes — the currency-tested bots (every bot declaring
    ``participation_requires_update``, credited via the SHA-current currency arm)
    alongside the presence-credited ones — so the guard holds across both.
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
            plan_id,
            pr_number=400,
            comment_id=f'r1-{i}',
            thread_id='',
            resolution_detail=f'Accepted: round-1 reply {i}.',
        )
        for i in range(4)
    ]
    first = _run_post_responses(400, plan_id)
    assert first['count_responded'] == 4

    round2 = [
        _stage_respondable(
            plan_id,
            pr_number=400,
            comment_id=f'r2-{i}',
            thread_id='',
            resolution_detail=f'Accepted: round-2 reply {i}.',
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
        plan_id,
        pr_number=405,
        comment_id='ti',
        thread_id='PRRT_IDEM',
        resolution_detail='Fixed in TASK-9.',
        kind='inline',
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


@pytest.mark.parametrize('bot_kind', CURRENCY_SUBJECT_BOTS)
def test_unresolvable_head_sha_fails_closed_and_stays_idempotent(bot_kind, plan_context, monkeypatch):
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
    assert first['undecidable_participation_bots'] == [{'bot_kind': bot_kind, 'evidence_kind': comment['kind']}]
    # Idempotent: the second evaluation matches the first exactly.
    assert second['participated_bots'] == first['participated_bots']
    assert second['stale_participation_bots'] == first['stale_participation_bots']
    assert second['undecidable_participation_bots'] == first['undecidable_participation_bots']


@pytest.mark.parametrize('bot_kind', CURRENCY_SUBJECT_BOTS)
def test_an_unchanged_comment_still_dedupes_under_the_widened_key(bot_kind, plan_context, monkeypatch):
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
    assert github_pr._detail_field(stored[0].get('detail'), github_pr._EDIT_TERM_DETAIL) == (clean['updated_at'])

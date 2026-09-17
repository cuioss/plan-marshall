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
def _self_response_body(comment_id='c1', reply='Fixed in the follow-up commit; see the updated guard.'):
    """Render a real ``post_responses`` batched body via the production emitter."""
    return github_pr._build_batched_response_body([(comment_id, reply)])
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
def _stored_comment_id(finding):
    """Extract the ``comment_id`` value from a stored pr-comment finding's detail."""
    for detail_line in (finding.get('detail') or '').splitlines():
        if detail_line.startswith('comment_id:'):
            return detail_line.split(':', 1)[1].strip()
    return ''
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
_HEAD_A = 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
_HEAD_B = 'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb'
_HEAD_C = 'cccccccccccccccccccccccccccccccccccccccc'
_GUIDE_CLEAN_BODY = 'Nothing further to report on this pass; the change reads consistently.'
_GUIDE_FINDING_BODY = 'The retry helper drops the final attempt when max_attempts is 1.'
_LEGACY_LEDGER_FILENAME = 'pr-noise-dropped-comments.jsonl'
_CONTRACT_DOC = get_skill_dir('plan-marshall', 'automatic-review') / 'standards' / 'bot-participation-contract.md'
_CONTRACT_TEXT = _CONTRACT_DOC.read_text(encoding='utf-8')
_SOURCERY_SIZE_NOTICE = (
    '> [!NOTE]\n'
    '> Sorry, your pull request is larger than the review limit of 150000 diff '
    'characters. Please split it into smaller PRs.'
)
_ISO_COMMIT_AT = '2026-08-25T12:00:00Z'


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
                '> ## Triage dispositions\n>\nThis disposition is wrong: the guard still misses the empty-thread case.'
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
    stored_ids = {_stored_comment_id(f) for f in stored}
    assert stored_ids == {'cr-genuine', 'sr-genuine', 'unk-genuine'}
def test_fetch_findings_reports_no_drift_for_an_unattributable_refusal(plan_context, monkeypatch):
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
def test_fetch_findings_splits_a_refusing_bot_from_a_participating_one(plan_context, monkeypatch):
    """A bot that only refused lands in ``refused_bots``, never in ``participated_bots``.

    The signature pinned here: over a set where CodeRabbit posts ONLY a
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
    assert result['refused_size_caps'] == [{'bot_kind': 'sourcery', 'cap': '150000 diff characters'}]
    # ...and the measurement that makes the recorded gap auditable rather than asserted.
    assert result['measured_diff_size'] == '1240 changed lines'
def test_fetch_findings_measures_the_diff_on_a_size_refusal_with_no_stated_cap(plan_context, monkeypatch):
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
def test_fetch_findings_does_not_measure_the_diff_without_a_size_refusal(plan_context, monkeypatch):
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

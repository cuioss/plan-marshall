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
def _evidence_comment(bot_kind, shape, comment_id, body, **extra):
    """One comment authored by ``bot_kind`` in publish shape ``shape``."""
    comment = {
        'id': comment_id,
        'author': _LOGIN_FOR_KIND[bot_kind],
        'thread_id': f'PRRT_{comment_id}' if shape == 'inline' else '',
        'kind': shape,
        'body': body,
        'resolved': False,
    }
    comment.update(extra)
    return comment
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
_GUIDE_CLEAN_BODY = 'Nothing further to report on this pass; the change reads consistently.'
_GUIDE_FINDING_BODY = 'The retry helper drops the final attempt when max_attempts is 1.'
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
_CONTRACT_DOC = get_skill_dir('plan-marshall', 'automatic-review') / 'standards' / 'bot-participation-contract.md'
_CONTRACT_TEXT = _CONTRACT_DOC.read_text(encoding='utf-8')
_SOURCERY_SIZE_NOTICE = (
    '> [!NOTE]\n'
    '> Sorry, your pull request is larger than the review limit of 150000 diff '
    'characters. Please split it into smaller PRs.'
)
_ISO_COMMIT_AT = '2026-08-25T12:00:00Z'


def test_the_gate_populations_are_non_empty_and_disjoint():
    """Both halves of the partition carry members, and no declared pairing is in both.

    The two parametrized sweeps below would SKIP rather than fail over an empty
    population, so their sizes are asserted here; disjointness is what makes the pair a
    partition rather than two overlapping lists.
    """
    assert MARKER_GATED_EVIDENCE and UNGATED_EVIDENCE, 'a half with no members makes its sweep vacuous'
    gated_pairs = {(bot_kind, shape) for bot_kind, shape, _marker in MARKER_GATED_EVIDENCE}
    assert MARKER_GATED_EVIDENCE_COUNT == len(gated_pairs)
    assert UNGATED_EVIDENCE_COUNT == len(set(UNGATED_EVIDENCE))
    assert gated_pairs.isdisjoint(UNGATED_EVIDENCE)
@pytest.mark.parametrize(
    ('bot_kind', 'shape', 'marker'),
    MARKER_GATED_EVIDENCE,
    ids=[f'{bot_kind}-{shape}' for bot_kind, shape, _marker in MARKER_GATED_EVIDENCE],
)
def test_a_gated_shape_credits_the_marker_bearing_comment(plan_context, monkeypatch, bot_kind, shape, marker):
    """A comment in a gated shape that CARRIES the declared marker is participation evidence."""
    body = f'{marker}\nReviewed the change; the retry bound and its guard are both correct.'
    _patch_provider(monkeypatch, [_evidence_comment(bot_kind, shape, 'gated-marked', body)])

    result = _run_fetch(190, _evidence_plan_id('gated-marked', bot_kind, shape))

    assert result['status'] == 'success'
    assert result['participated_bots'] == [{'bot_kind': bot_kind, 'evidence_kind': shape}]
@pytest.mark.parametrize(
    ('bot_kind', 'shape', 'marker'),
    MARKER_GATED_EVIDENCE,
    ids=[f'{bot_kind}-{shape}' for bot_kind, shape, _marker in MARKER_GATED_EVIDENCE],
)
def test_a_gated_shape_without_the_marker_credits_nothing(plan_context, monkeypatch, bot_kind, shape, marker):
    """⛔ MATCHED NEGATIVE CONTROL: the same shape WITHOUT the marker is not evidence at all.

    Same bot, same shape, same head — only the marker is missing. Pre-fix this comment
    credited the bot on its shape alone. It is now neither a participant NOR a stale or
    undecidable publisher: a comment the gate rejects is not a review artifact, so it
    must not reach any participation set.
    """
    body = 'Summary of the change: the retry helper is reworked. Review in progress.'
    assert marker not in body
    _patch_provider(monkeypatch, [_evidence_comment(bot_kind, shape, 'gated-bare', body)])

    result = _run_fetch(191, _evidence_plan_id('gated-bare', bot_kind, shape))

    assert result['status'] == 'success'
    assert result['participated_bots'] == []
    assert result['stale_participation_bots'] == []
    assert result['undecidable_participation_bots'] == []
@pytest.mark.parametrize(
    ('bot_kind', 'shape'),
    UNGATED_EVIDENCE,
    ids=[f'{bot_kind}-{shape}' for bot_kind, shape in UNGATED_EVIDENCE],
)
def test_an_ungated_shape_credits_on_the_shape_alone(plan_context, monkeypatch, bot_kind, shape):
    """The gate is FAIL-OPEN: a shape with no declared marker credits exactly as before.

    This is the guard against the gate regressing a bot to ``absent``. The body carries
    no marker of any bot, so a gate that failed CLOSED on an absent declaration — or
    that leaked one bot's marker onto another bot's shape — would deny the credit here.
    """
    body = 'The retry loop has no ceiling; a persistent 500 will spin forever.'
    assert not any(marker in body for _bot, _shape, marker in MARKER_GATED_EVIDENCE)
    _patch_provider(monkeypatch, [_evidence_comment(bot_kind, shape, 'ungated', body)])

    result = _run_fetch(192, _evidence_plan_id('ungated', bot_kind, shape))

    assert result['status'] == 'success'
    assert result['participated_bots'] == [{'bot_kind': bot_kind, 'evidence_kind': shape}]
def test_a_coderabbit_clean_verdict_comment_credits_participation(plan_context, monkeypatch):
    """CodeRabbit's clean verdict, published as its ONLY comment, credits it — and files nothing.

    The observed ``cui-http#194`` shape: one ``issue_comment`` carrying the verdict marker.
    It is dropped as noise (its clean text is one of CodeRabbit's ``ignore_patterns``), so
    nothing is filed — yet the bot is credited, because participation is derived before
    the noise filter. That pairing is what lets the classifier resolve a clean review to
    ``participated_but_empty`` instead of ``absent``.
    """
    plan_id = 'gh-pr-clean-verdict-credited'
    assert 'issue_comment' in bot_registry.participation_evidence('coderabbit')
    _patch_provider(
        monkeypatch, [_evidence_comment('coderabbit', 'issue_comment', 'cr-verdict', _CODERABBIT_CLEAN_VERDICT)]
    )

    result = _run_fetch(193, plan_id)

    assert result['status'] == 'success'
    assert result['participated_bots'] == [{'bot_kind': 'coderabbit', 'evidence_kind': 'issue_comment'}]
    assert result['count_stored'] == 0
    assert result['count_skipped_noise'] == 1
    assert result['producer_mismatch_hash_id'] is None
def test_a_coderabbit_walkthrough_alone_credits_nothing(plan_context, monkeypatch):
    """⛔ MATCHED NEGATIVE CONTROL: the pre-review walkthrough is the same shape and credits nothing.

    The defect this deliverable closes. The walkthrough is posted before any review
    completes, in the SAME ``issue_comment`` shape as the verdict above, so on shape and
    currency alone it earned the credit a finished review earns. It now credits nothing
    and is reported in no participation set, while still being dropped as noise exactly
    as before.
    """
    plan_id = 'gh-pr-clean-verdict-walkthrough-only'
    _patch_provider(
        monkeypatch, [_evidence_comment('coderabbit', 'issue_comment', 'cr-walkthrough', _CODERABBIT_WALKTHROUGH)]
    )

    result = _run_fetch(194, plan_id)

    assert result['status'] == 'success'
    assert result['participated_bots'] == []
    assert result['stale_participation_bots'] == []
    assert result['undecidable_participation_bots'] == []
    assert result['count_skipped_noise'] == 1
def test_a_rejected_comment_stages_no_currency_row_so_its_later_verdict_edit_is_credited(plan_context, monkeypatch):
    """The gate runs BEFORE the currency test, so a rejected walkthrough anchors nothing.

    CodeRabbit edits its summary comment IN PLACE. Fetch 1 sees it as a walkthrough: no
    credit, and — because the gate rejected it before the currency test — no currency
    ledger row. Fetch 2 sees the SAME comment id edited to carry the verdict at the same
    head: with no row recorded it takes the first-observation arm and is credited.

    Had the rejected walkthrough staged a row, the verdict edit would instead be
    measured against an anchor a non-review had set.
    """
    plan_id = 'gh-pr-clean-verdict-edited-in'
    walkthrough = _evidence_comment(
        'coderabbit',
        'issue_comment',
        'cr-summary',
        _CODERABBIT_WALKTHROUGH,
        created_at='2026-09-01T10:00:00Z',
        updated_at='2026-09-01T10:00:00Z',
    )
    _patch_provider(monkeypatch, [walkthrough])

    first = _run_fetch(195, plan_id)

    assert first['participated_bots'] == []
    assert github_pr._recorded_currency_records(plan_id) == {}

    verdict = {**walkthrough, 'body': _CODERABBIT_CLEAN_VERDICT, 'updated_at': '2026-09-01T10:20:00Z'}
    _patch_provider(monkeypatch, [verdict])

    second = _run_fetch(195, plan_id)

    assert second['participated_bots'] == [{'bot_kind': 'coderabbit', 'evidence_kind': 'issue_comment'}]
    assert github_pr._recorded_currency_records(plan_id) == {
        ('coderabbit', 'cr-summary'): ('deadbeef', '2026-09-01T10:20:00Z'),
    }
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
def test_the_currency_subject_population_guard_is_exercised():
    """The population's import-time vacuity guard admits the real set and rejects an empty one.

    A parametrize over an empty tuple produces a skip, not a failure, so an unguarded
    empty population would let every case below report clean while covering nothing.
    Both controls are asserted: a guard only ever observed on its PASSING input proves
    nothing about what it rejects.
    """
    assert CURRENCY_SUBJECT_BOT_COUNT == len(CURRENCY_SUBJECT_BOTS)
    assert len(CURRENCY_SUBJECT_BOTS) > 0
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
def test_edit_at_one_commit_does_not_credit_a_later_commit(bot_kind, plan_context, monkeypatch):
    """An in-place edit credits the commit it was made against, NOT every later HEAD.

    The defect this forbids: with the edit arm keyed on
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
    assert at_c['stale_participation_bots'] == [{'bot_kind': bot_kind, 'evidence_kind': edited['kind']}]
@pytest.mark.parametrize('bot_kind', CURRENCY_SUBJECT_BOTS)
def test_review_predating_the_merge_candidate_is_stale(bot_kind, plan_context, monkeypatch):
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
    assert second['stale_participation_bots'] == [{'bot_kind': bot_kind, 'evidence_kind': comment['kind']}]
@pytest.mark.parametrize('bot_kind', CURRENCY_SUBJECT_BOTS)
def test_in_place_edit_credits_participation_after_a_head_advance(bot_kind, plan_context, monkeypatch):
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
def test_a_fresh_comment_outranks_a_stale_one_through_the_subtraction(bot_kind, plan_context, monkeypatch):
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
@pytest.mark.parametrize('bot_kind', CURRENCY_SUBJECT_BOTS)
def test_two_unchanged_evidence_comments_are_stale_at_an_advanced_head(bot_kind, plan_context, monkeypatch):
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
    assert at_a['participated_bots'] == [{'bot_kind': bot_kind, 'evidence_kind': comments[0]['kind']}]

    _patch_provider(monkeypatch, comments, head_sha=_HEAD_B)
    at_b = _run_fetch(160, plan_id)
    assert at_b['status'] == 'success'
    assert at_b['participated_bots'] == []
    assert at_b['stale_participation_bots'] == [{'bot_kind': bot_kind, 'evidence_kind': comments[0]['kind']}]
@pytest.mark.parametrize('bot_kind', CURRENCY_SUBJECT_BOTS)
def test_a_rejecting_fetch_stages_no_ledger_row_so_the_verdict_holds(bot_kind, plan_context, monkeypatch):
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
    assert third['stale_participation_bots'] == [{'bot_kind': bot_kind, 'evidence_kind': comments[0]['kind']}]

    # And the ledger still anchors both comments on HEAD_A — the rejecting fetch wrote
    # nothing, which is what makes the verdict above hold rather than flip.
    ledger = github_pr._recorded_currency_records(plan_id)
    assert ledger[(bot_kind, 'guide-a')][0] == _HEAD_A
    assert ledger[(bot_kind, 'guide-b')][0] == _HEAD_A
@pytest.mark.parametrize('bot_kind', CURRENCY_SUBJECT_BOTS)
def test_a_comment_predating_the_merge_candidate_is_stale_on_first_observation(bot_kind, plan_context, monkeypatch):
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
    assert result['stale_participation_bots'] == [{'bot_kind': bot_kind, 'evidence_kind': comment['kind']}]
    # A withheld credit stages no anchor either — otherwise the next fetch would read
    # the comment as SHA-current and credit what this fetch refused.
    assert github_pr._recorded_currency_records(plan_id) == {}
@pytest.mark.parametrize('bot_kind', CURRENCY_SUBJECT_BOTS)
def test_a_pre_upgrade_key_only_ledger_row_resolves_stale_not_participated(bot_kind, plan_context, monkeypatch):
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
    assert result['stale_participation_bots'] == [{'bot_kind': bot_kind, 'evidence_kind': comment['kind']}]
    # ...and the mechanism that produced it: the row survived the read as the stated
    # third state rather than being dropped or coerced into a usable-looking anchor.
    assert github_pr._recorded_currency_records(plan_id)[(bot_kind, 'guide-1')] is github_pr.INVALID_LEGACY_RECORD
@pytest.mark.parametrize('bot_kind', CURRENCY_SUBJECT_BOTS)
def test_a_credited_bot_becomes_undecidable_when_the_head_read_fails(bot_kind, plan_context, monkeypatch):
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
    assert credited['participated_bots'] == [{'bot_kind': bot_kind, 'evidence_kind': comment['kind']}]
    assert credited['undecidable_participation_bots'] == []

    _patch_provider(monkeypatch, [comment], head_sha='')
    unread = _run_fetch(180, plan_id)

    assert unread['status'] == 'success'
    assert unread['merge_candidate_sha_resolved'] is False
    assert unread['participated_bots'] == []
    assert unread['stale_participation_bots'] == []
    assert unread['undecidable_participation_bots'] == [{'bot_kind': bot_kind, 'evidence_kind': comment['kind']}]
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
def test_a_ledger_written_under_the_pre_rename_filename_is_still_read(bot_kind, plan_context, monkeypatch):
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
    assert result['stale_participation_bots'] == [{'bot_kind': bot_kind, 'evidence_kind': comment['kind']}]
    # ...and the mechanism: the row reached the reader as a usable anchor, not as the
    # invalid-legacy sentinel and not as an absent key.
    assert github_pr._recorded_currency_records(plan_id)[(bot_kind, 'guide-1')] == (
        _HEAD_A,
        comment['updated_at'],
    )
@pytest.mark.parametrize('bot_kind', CURRENCY_SUBJECT_BOTS)
def test_the_same_fetch_with_no_ledger_at_all_credits_the_comment(bot_kind, plan_context, monkeypatch):
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
    assert result['participated_bots'] == [{'bot_kind': bot_kind, 'evidence_kind': comment['kind']}]
    assert result['stale_participation_bots'] == []
@pytest.mark.parametrize('bot_kind', CURRENCY_SUBJECT_BOTS)
def test_a_populated_current_ledger_does_not_hide_the_pre_rename_rows(bot_kind, plan_context, monkeypatch):
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
    assert at_a['participated_bots'] == [{'bot_kind': bot_kind, 'evidence_kind': guide_a['kind']}]
    assert github_pr._currency_ledger_path(plan_id).exists()

    # HEAD advances. Neither comment moved, and both anchors point at HEAD_A.
    _patch_provider(monkeypatch, comments, head_sha=_HEAD_B)
    at_b = _run_fetch(202, plan_id)

    assert at_b['status'] == 'success'
    assert at_b['participated_bots'] == []
    assert at_b['stale_participation_bots'] == [{'bot_kind': bot_kind, 'evidence_kind': guide_a['kind']}]
    # Both anchors resolved, each from the file that holds it.
    ledger = github_pr._recorded_currency_records(plan_id)
    assert ledger[(bot_kind, 'guide-a')] == (_HEAD_A, guide_a['updated_at'])
    assert ledger[(bot_kind, 'guide-b')] == (_HEAD_A, guide_b['updated_at'])
@pytest.mark.parametrize('bot_kind', CURRENCY_SUBJECT_BOTS)
def test_a_credit_is_written_only_under_the_current_filename(bot_kind, plan_context, monkeypatch):
    """The pre-rename file is READ and never written — the migration is one-directional.

    Appending to it as well would keep minting rows under a name that no longer says what
    the file holds, which is the state the rename exists to end.
    """
    plan_id = f'gh-pr-write-current-only-{bot_kind}'
    comment = _publish_comment(bot_kind, 'guide-1', created_at=_at(1))
    _patch_provider(monkeypatch, [comment], head_sha=_HEAD_A)

    result = _run_fetch(203, plan_id)

    assert result['participated_bots'] == [{'bot_kind': bot_kind, 'evidence_kind': comment['kind']}]
    assert github_pr._currency_ledger_path(plan_id).exists()
    assert not github_pr._legacy_currency_ledger_path(plan_id).exists()
def test_the_currency_blind_population_is_derived_and_guarded():
    """The complement is non-empty and disjoint from the currency-subject population.

    Both halves matter. Non-empty, because every case below is parametrized over it and a
    parametrize over an empty tuple SKIPS rather than fails. Disjoint and total, because
    the two populations come from one registry read: a bot that fell out of both, or into
    both, would make one of the two sweeps quietly wrong about which rule governs it.
    """
    assert CURRENCY_BLIND_BOT_COUNT == len(CURRENCY_BLIND_BOTS)
    assert len(CURRENCY_BLIND_BOTS) > 0
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
def test_an_append_per_review_bot_stays_credited_after_a_head_advance(bot_kind, plan_context, monkeypatch):
    """The documented behaviour, asserted as a REACH DIFFERENCE on one identical fixture.

    ⚠ This case is deliberately GREEN against the pre-change code, and that is the correct
    outcome rather than a weakness to hide: the recorded disposition is to DOCUMENT this
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

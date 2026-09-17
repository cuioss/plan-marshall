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
_SOURCERY_DECLARED_REFUSAL_MARKER = bot_registry.refusal_patterns('sourcery')[0]
_REWORDED_SOURCERY_REFUSAL = (
    f'Sorry, {_SOURCERY_DECLARED_REFUSAL_MARKER.replace("larger than", "over")} our current plan.'
)
_RECOGNISED_SOURCERY_REFUSAL = f'Sorry, {_SOURCERY_DECLARED_REFUSAL_MARKER} our current plan.'


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

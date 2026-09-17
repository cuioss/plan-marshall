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
assert CURRENCY_SUBJECT_BOTS, (
    'the registry declares no currency-subject bots — every parametrize below would be vacuous'
)


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
        args = _parsed_fetch_args(monkeypatch, ['fetch_findings', '--pr-number', '1', '--plan-id', 'p'])

        assert getattr(args, dest) == ''

    def test_bare_flags_reach_the_handler_and_still_warn_but_ingest(self, plan_context, monkeypatch, capsys):
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


@pytest.mark.parametrize('bot_kind', CURRENCY_SUBJECT_BOTS)
def test_second_fetch_at_the_same_head_stays_participated(bot_kind, plan_context, monkeypatch):
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
def test_a_fresh_edit_at_an_unreadable_head_blocks_on_both_fetches(bot_kind, plan_context, monkeypatch):
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
    # stale, because the head read is what failed.
    assert first['stale_participation_bots'] == []
    assert first['undecidable_participation_bots'] == [{'bot_kind': bot_kind, 'evidence_kind': edited['kind']}]
    assert second['participated_bots'] == first['participated_bots']
    assert second['stale_participation_bots'] == first['stale_participation_bots']
    assert second['undecidable_participation_bots'] == first['undecidable_participation_bots']

    ledger = github_pr._recorded_currency_records(plan_id)
    assert ledger == ledger_after_credit
    assert not any(isinstance(v, github_pr._InvalidLegacyRecord) for v in ledger.values())


@pytest.mark.parametrize('bot_kind', CURRENCY_SUBJECT_BOTS)
def test_a_pre_upgrade_finding_without_an_edit_term_does_not_refile_history(bot_kind, plan_context, monkeypatch):
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
        title=f'PR #192 {comment["kind"]} comment by {comment["author"]} (guide-persistent)',
        detail=(
            'pr_number: 192\n'
            f'kind: {comment["kind"]}\n'
            f'author: {comment["author"]}\n'
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
def test_comment_predates_commit_withholds_when_the_timestamps_do_not_compare(updated_at, created_at, why):
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

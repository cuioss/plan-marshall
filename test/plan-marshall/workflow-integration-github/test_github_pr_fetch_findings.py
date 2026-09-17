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
def _undeclared_shape_pairs() -> list[tuple[str, str]]:
    """Every ``(bot_kind, publish_shape)`` pairing the registry leaves UNDECLARED.

    Derived from the live registry rather than hand-listed. A literal bot name here
    is the hand-maintained roster this suite's population-derivation rule forbids: it
    goes stale on the next registry edit, silently, exactly as a ``coderabbit`` /
    ``issue_comment`` literal did the moment CodeRabbit declared all three shapes.
    """
    return [
        (bot, shape)
        for bot in bot_registry.bot_kinds()
        for shape in _PUBLISH_SHAPE_VOCABULARY
        if shape not in bot_registry.participation_evidence(bot)
    ]
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


def test_classification_union_spans_both_lists(plan_context, monkeypatch):
    """A bot classified via EITHER list is not reported unclassified.

    ``--required-bots "coderabbit,cuioss-review-bot"`` plus ``--optional-bots "sourcery"``
    classifies all three participating bots, proving the producer takes the union
    of the two comma-split sets rather than reading only one list.
    """
    plan_id = 'gh-pr-classification-union'
    _patch_provider(monkeypatch, _COMMENTS)

    result = _run_fetch_classified(103, plan_id, required_bots='coderabbit,cuioss-review-bot', optional_bots='sourcery')
    assert result['status'] == 'success'
    assert result['count_stored'] == len(_COMMENTS)
    assert result['unclassified_bots'] == []
    assert result['producer_mismatch_hash_id'] is None

    stored = query_findings(plan_id, finding_type='pr-comment')['findings']
    bot_kinds = {f.get('bot_kind') for f in stored}
    assert {'coderabbit', 'cuioss-review-bot', 'sourcery'} <= bot_kinds
def test_fetch_findings_reports_drift_when_only_the_structural_arm_matched(plan_context, monkeypatch):
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
    assert result['refusal_pattern_drift'] == [{'bot_kind': 'coderabbit', 'layer': _github_pr.REFUSAL_LAYER_STRUCTURAL}]
def test_fetch_findings_reports_no_drift_when_only_the_registry_arm_matched(plan_context, monkeypatch):
    """⛔ MATCHED NEGATIVE CONTROL: a registry-only match is the DESIGN, not decay.

    The exact mirror of the positive case above — one arm fires there too, so a
    predicate that merely counted the matching arms (``len(layers) == 1``) reported
    drift for BOTH. But the two directions mean opposite things. A body only the
    STRUCTURAL arm reads means the bot's declared wording went stale. A body only
    the REGISTRY arm reads is the registry doing precisely the job it is
    load-bearing FOR: Sourcery's size refusal is invisible to the structural arm BY
    CONSTRUCTION, so this state is permanent and correct, and reporting it as drift
    named a stale record that does not exist. It has fired for real in production.

    Anti-vacuity: the registry-only direction is ASSERTED against the live registry
    (not assumed of the fixture), and the publish shape is asserted to be one
    Sourcery declares — so this cannot pass because the drift channel was never
    reached at all, which is what the wrong-shape control below covers instead.
    """
    plan_id = 'gh-pr-refusal-registry-only'
    # The arms really do differ, and in the REGISTRY direction — the mirror of the
    # positive case. Read from the live seam so a registry rewording that made this
    # body structurally visible fails here rather than silently neutering the test.
    assert _github_pr.refusal_layers(_SOURCERY_SIZE_REFUSAL, 'sourcery') == [_github_pr.REFUSAL_LAYER_REGISTRY]
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
def test_fetch_findings_reports_no_drift_outside_a_declared_publish_shape(plan_context, monkeypatch):
    """Scoped to the bot's declared ``participation_evidence`` shapes.

    A body arriving in a shape the bot does NOT declare is no evidence that the
    wording it uses when REVIEWING has drifted, so the drift channel stays silent
    while the refusal itself is still recognised and attributed. Same drifted body as
    the positive case — only the (bot, shape) pairing differs.

    The pairing is DERIVED from the registry and guarded NON-EMPTY, so a registry
    that left no undeclared pairing FAILS this case rather than passing it over
    nothing.
    """
    plan_id = 'gh-pr-refusal-drift-shape'
    undeclared_pairs = _undeclared_shape_pairs()
    assert undeclared_pairs, (
        'every registered bot declares every publish shape, so the registry offers no '
        '(bot_kind, undeclared shape) pairing — this case would assert nothing.'
    )
    bot_kind, undeclared_shape = undeclared_pairs[0]
    login_for_kind = {kind: login for login, kind in bot_registry.login_to_bot_kind().items()}

    comments = [
        {
            'id': 'drifted-undeclared-shape',
            'author': login_for_kind[bot_kind],
            'thread_id': '',
            'kind': undeclared_shape,
            'body': _DRIFTED_CODERABBIT_NOTICE,
            'resolved': False,
        },
    ]
    _patch_provider(monkeypatch, comments)

    result = _run_fetch(134, plan_id)

    assert undeclared_shape not in bot_registry.participation_evidence(bot_kind)
    # Still recognised as a refusal — only the DRIFT channel is scoped.
    assert result['refused_bots'] == [bot_kind]
    assert result['refusal_pattern_drift'] == []
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
            'body': ('> [!NOTE]\n> Sourcery: you have reached your weekly rate limit of 500000 diff characters.'),
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
            'body': ('> [!NOTE]\n> Sourcery: you have reached your weekly rate limit of 500000 diff characters.'),
            'resolved': False,
        },
    ]
    _patch_provider(monkeypatch, comments)

    result = _run_fetch(108, plan_id)
    assert result['status'] == 'success'
    assert result['refused_causes'] == [{'bot_kind': 'sourcery', 'cause': 'size'}]
def test_fetch_findings_reports_an_unmeasurable_diff_as_unknown_never_zero(plan_context, monkeypatch):
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
    assert result['refused_size_caps'] == [{'bot_kind': 'sourcery', 'cap': '150000 diff characters'}]

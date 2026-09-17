#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for review_completeness.py — the automatic-review step-done PARTICIPATION guard.

The predicate classifies every required ∪ optional bot into exactly one state and
reports whether every REQUIRED bot's participation is proven:

    participated            — proven participant that filed at least one finding
    participated_but_empty  — proven participant that filed none (accounted-for)
    refused_awaitable       — published a refusal whose window reopens on its own
    refused_hard            — published a refusal that does not usefully reopen
    refused_unknown         — declared ignorance about whether waiting helps. Reached
                              either because the registry declares the bot's class
                              unknown (neither awaitable nor a hard quota), or because
                              NO arm of the recognition stack could read the refusal —
                              an override that displaces whatever class the bot
                              declares. Its own member, never folded into refused_hard
    refused_structural      — published a refusal whose CAUSE is a ceiling on the DIFF
                              itself, so the same request never succeeds while the diff
                              is this size. Its own member because the remedy set is
                              DISJOINT from the three temporal ones: split the diff,
                              accept the gap, or disable the reviewer for this PR —
                              and never wait
    participated_stale      — published in a declared shape, but the currency test
                              failed, so the review predates the merge candidate
                              (blocking, yet remedied by a re-trigger rather than by
                              awaiting)
    declined                — answered a re-review of the merge candidate without
                              producing a review of it (an incremental-review decline;
                              blocking, yet remedied by accepting the decline rather
                              than re-triggering a bot that already declined)
    in_progress             — review still running at the poll bound
    not_triggered           — PR-wide: no pull_request-event run exists for the PR at
                              all, so NO bot could have published and this bot's
                              silence says nothing about this bot. A refinement of
                              absent whose remedy is to trigger the review, rather
                              than to escalate a reviewer that was asked and stayed
                              silent
    unregistered_kind       — the configured token matches no member of the live
                              registry kind set, so no reviewer answers to this name
                              and none ever could. A refinement of absent decided from
                              the CONFIGURATION rather than from an observation, and
                              checked after every observation branch; blocking exactly
                              as absent is, but remedied by fixing the NAME rather
                              than by chasing the reviewer
    absent                  — no evidence of any kind (the fail-closed default)

Participation is **evidence-typed, not presence-typed**: a bot counts only when an
observed comment's ``kind`` is one of the publish shapes its registry record
declares in ``participation_evidence``. **The quorum is over ``required_bots``
ONLY** — an optional bot is classified and reported for visibility but never gates
the verdict. ``triage_ran=False`` (default, the FIND-only step) treats a
``pending`` finding as the expected awaiting-triage state that does NOT block;
``triage_ran=True`` treats a still-``pending`` required finding as a real
incompleteness.

The verdict proves PARTICIPATION, never review QUALITY; the obligations that
follow from that ceiling are pinned by ``TestParticipationIsNotReviewQuality``.
See ``automatic-review/standards/bot-participation-contract.md``.

The store is seeded in-process via ``_findings_core.add_finding`` /
``resolve_finding`` under the ``plan_context`` PLAN_BASE_DIR sandbox, so
``check_completeness`` reads a real per-plan store rather than a stub.
"""

from __future__ import annotations

import _findings_core as fc
import pytest
from _bot_flag_derivation import derive_bot_flags

from conftest import get_script_path, load_script_module, run_script

# ``register=False``: only the returned module is needed, and a sibling suite
# imports ``review_completeness`` plainly. Registering under that name would put two
# copies in play, reachable by different routes and differing by collection order.
rc = load_script_module('plan-marshall', 'automatic-review', 'review_completeness.py', register=False)

SCRIPT_PATH = get_script_path('plan-marshall', 'automatic-review', 'review_completeness.py')

# The registered bot population, hoisted to module scope so every sweep over it —
# the collection-time parametrize below and the in-test PR-wide sweep — reads ONE
# guarded derivation rather than re-deriving it unguarded at each site.
#
# The assertion is load-bearing at COLLECTION time, not merely tidy: pytest
# generates zero cases from an empty parametrize argument and reports the test as
# SKIPPED, not failed. An empty registry would therefore silently retire every
# property swept over this population while the suite still read green. A check
# that can return zero from an empty population must assert that population's size.
#
# ``derive_bot_flags`` guards its own derivation internally (see
# ``_bot_flag_derivation``), so ``_LIST_FLAGS`` below needs no second guard here;
# this population has no such internal guard and so takes one at the use site.
_REGISTERED_BOTS = rc.bot_registry.bot_kinds()
assert _REGISTERED_BOTS, (
    'the bot registry declared no bot — every sweep over this population would '
    'generate zero parametrized cases, which pytest reports as SKIPPED rather '
    'than failed, so the swept properties would be covered by nothing'
)

# The two tokens the unregistered-kind cases turn on, both DERIVED against the live
# registry rather than written as independent literals.
#
# ``_VALID_TOKEN`` is taken FROM the registry, never spelled. That is what keeps the
# matched negative control honest across a bot_kind RENAME: a hardcoded name would
# silently become an unregistered token the moment the registry renamed it, at which
# point the control would assert ``absent`` for a token that no longer resolves —
# passing before the rename and failing after it for a reason that has nothing to do
# with the property under test.
_VALID_TOKEN = _REGISTERED_BOTS[0]

# ...and its counterpart, asserted OUT of the registry rather than assumed to be. A
# fixture whose unregistered-ness is merely believed is one a future registry can
# quietly adopt, and every case below would then classify it ``absent`` and still
# report green while covering nothing.
_UNREGISTERED_TOKEN = 'not-a-registered-reviewer'
assert _UNREGISTERED_TOKEN not in _REGISTERED_BOTS, (
    f'{_UNREGISTERED_TOKEN!r} is a REGISTERED bot kind, so it cannot stand for a '
    f'configured name that matches no reviewer — every unregistered-kind case would '
    f'silently degrade into an absent case. Live kind set: {_REGISTERED_BOTS}'
)

# Evidence pairs that match each bot's DECLARED participation_evidence. Derived by
# name from the registry docs rather than invented, so a registry change that
# retires a publish shape breaks these tests loudly instead of silently.
CODERABBIT_EVIDENCE = {'coderabbit': 'inline'}
SOURCERY_EVIDENCE = {'sourcery': 'review_body'}
PR_AGENT_EVIDENCE = {'cuioss-review-bot': 'issue_comment'}

#: The publish-shape vocabulary DERIVED from the live registry: the union of every
#: registered bot's declared ``participation_evidence``, sorted so the pairing order
#: below is deterministic.
#:
#: Derived rather than transcribed, for two reasons. A hand-written tuple is the
#: hand-maintained copy of a source-defined enumeration that
#: ``persona-plan-marshall-agent/standards/agent-behavior-rules.md`` forbids: a shape
#: newly declared by a registry record would be invisible to it, so
#: ``_undeclared_shape_pairs()`` would keep returning an older pair, its non-empty
#: guard would still pass, and the new shape would be exercised by nothing. And a
#: written-out tuple can name a shape NO registered bot publishes, which pairs against
#: every bot and proves nothing about per-bot admissibility — the union makes every
#: generated pairing "a shape SOME bot publishes but THIS one does not", which is the
#: property the case below asserts.
_PUBLISH_SHAPE_VOCABULARY: tuple[str, ...] = tuple(
    sorted({shape for bot in _REGISTERED_BOTS for shape in rc.bot_registry.participation_evidence(bot)})
)


def _undeclared_shape_pairs() -> list[tuple[str, str]]:
    """Every ``(bot_kind, publish_shape)`` pairing the live registry leaves UNDECLARED.

    Derived rather than hand-listed. A written-out bot name is the hand-maintained
    roster that went stale here once already: ``coderabbit:issue_comment`` was the
    inadmissible pair until CodeRabbit declared all three publish shapes, at which
    point the assertion silently asserted the opposite of its own premise.
    """
    return [
        (bot, shape)
        for bot in _REGISTERED_BOTS
        for shape in _PUBLISH_SHAPE_VOCABULARY
        if shape not in rc.bot_registry.participation_evidence(bot)
    ]


def _seed(plan_id: str, bot_kind: str, resolution: str = 'pending', detail: str | None = None) -> str:
    """File one pr-comment finding for ``bot_kind`` and optionally resolve it.

    Returns the finding's hash_id. When ``resolution`` is not ``pending`` the
    finding is immediately resolved to that value so it counts as handled.
    """
    result = fc.add_finding(
        plan_id,
        'pr-comment',
        title=f'{bot_kind} comment',
        detail=detail if detail is not None else f'thread from {bot_kind}',
        bot_kind=bot_kind,
        kind='inline',
    )
    assert result['status'] == 'success', result
    hash_id: str = result['hash_id']
    if resolution != 'pending':
        resolved = fc.resolve_finding(plan_id, hash_id, resolution)
        assert resolved['status'] == 'success', resolved
    return hash_id


def _state_of(result: dict, bot_kind: str) -> str:
    """Return the single state ``bot_kind`` was classified into."""
    matches = [r['state'] for r in result['bot_states'] if r['bot_kind'] == bot_kind]
    assert len(matches) == 1, f'{bot_kind} must be classified exactly once: {result["bot_states"]}'
    state: str = matches[0]
    return state


# =============================================================================
# Evidence typing — participation is proven by publish shape, never by presence
# =============================================================================




_CODERABBIT_CLEAN_REVIEW_SHAPE = 'issue_comment'


_DECLARED_RATE_LIMIT_CLASSES = sorted({rc.bot_registry.rate_limit_class(bot) for bot in _REGISTERED_BOTS})


assert _DECLARED_RATE_LIMIT_CLASSES, (
    'no rate_limit_class value is declared by any registered bot — the override sweep below would cover nothing'
)


_LIST_FLAGS = derive_bot_flags(SCRIPT_PATH, 'check')


assert _LIST_FLAGS, 'derive_bot_flags found no list-shaped bot flags on the check parser'


def _parsed_check_args(monkeypatch, argv: list[str]):
    """Return the ``argparse.Namespace`` ``main`` built for ``argv``.

    Replaces ``cmd_check`` with a recorder so the parse is observed WITHOUT
    running the predicate. ``main`` resolves ``cmd_check`` from module globals at
    call time (``check_parser.set_defaults(func=cmd_check)`` executes inside
    ``main``), so patching the module attribute reaches the binding it uses.
    """
    captured: dict = {}

    def _recorder(args):
        captured['args'] = args
        return 0

    monkeypatch.setattr(rc, 'cmd_check', _recorder)
    assert rc.main(argv) == 0
    return captured['args']


def _declared_state_values() -> set[str]:
    """Every state value ``review_completeness`` declares, DERIVED from the module.

    Read off the live module namespace by the ``STATE_`` naming convention the
    constants already follow, rather than restated here. A restated list is one more
    copy that goes stale, and it goes stale in the one direction that matters: it
    would still list the old population on the very commit that added a state to the
    real one, so the totality check below would pass exactly when it was meant to
    fail.
    """
    return {value for name, value in vars(rc).items() if name.startswith('STATE_') and isinstance(value, str)}


def _bucketed_state_values() -> list[str]:
    """Every state named across the display buckets, in declaration order.

    Returned as a LIST rather than a set, deliberately: the MULTIPLICITY is what
    makes the disjointness half checkable at all, and collapsing to a set here would
    silently absorb the duplicate that check exists to find.
    """
    return [state for _label, states in rc._STATE_SUMMARY_BUCKETS for state in states]


class TestEvidenceTyping:
    """A bot is a participant only via the publish shapes its registry doc declares."""

    def test_each_bots_declared_shape_proves_participation(self, plan_context):
        """Each bot's OWN declared evidence shape is admitted."""
        assert rc.parse_participation('coderabbit:inline') == CODERABBIT_EVIDENCE
        assert rc.parse_participation('coderabbit:review_body') == {'coderabbit': 'review_body'}
        # CodeRabbit's standalone summary comment is a declared shape, so it is
        # admitted POSITIVELY rather than covered only by the absence of a failure.
        assert rc.parse_participation('coderabbit:issue_comment') == {'coderabbit': 'issue_comment'}
        assert rc.parse_participation('sourcery:review_body') == SOURCERY_EVIDENCE
        assert rc.parse_participation('cuioss-review-bot:issue_comment') == PR_AGENT_EVIDENCE

    def test_a_shape_the_bot_does_not_publish_is_not_evidence(self, plan_context):
        """Evidence is per-bot: another bot's publish shape proves nothing here.

        Sourcery publishes no inline comments, so that pair is inadmissible even
        though ``inline`` is a real publish shape for other bots.

        The second pair is DERIVED from the live registry and guarded non-empty, so
        the case FAILS rather than asserting nothing should every registered bot come
        to declare every shape.
        """
        assert rc.parse_participation('sourcery:inline') == {}

        undeclared_pairs = _undeclared_shape_pairs()
        assert undeclared_pairs, (
            'every registered bot declares every publish shape, so the registry offers '
            'no (bot_kind, undeclared shape) pairing — this case would assert nothing.'
        )
        bot_kind, undeclared_shape = undeclared_pairs[0]
        assert rc.parse_participation(f'{bot_kind}:{undeclared_shape}') == {}

    def test_unqualified_presence_is_rejected(self, plan_context):
        """A bare ``bot_kind`` with no evidence kind is REJECTED, never silently dropped.

        Unqualified presence still proves nothing — but the disposition is now a loud
        caller error, not a silent drop. Silently dropping a bare kind resolves the bot
        to ``absent`` (a blocking member) and manufactures a confident false merge block
        against a bot the caller meant to record as a participant; that polarity-selecting
        misparse is what D1 closes. A pair with an empty side is the same shape violation.
        """
        with pytest.raises(rc.MalformedBotFlag):
            rc.parse_participation('coderabbit')
        with pytest.raises(rc.MalformedBotFlag):
            rc.parse_participation('coderabbit,sourcery')
        with pytest.raises(rc.MalformedBotFlag):
            rc.parse_participation('coderabbit:')
        with pytest.raises(rc.MalformedBotFlag):
            rc.parse_participation(':inline')
        # A well-formed pair whose evidence kind is inadmissible is a SEMANTIC
        # non-match, not a shape error, and stays a silent drop (diff-derived-evidence).
        assert rc.parse_participation('coderabbit:pr_body') == {}
        # The empty-list forms are never malformed.
        assert rc.parse_participation('') == {}
        assert rc.parse_participation('  ,  ') == {}

    def test_unknown_bot_can_never_be_proven(self, plan_context):
        """A bot with no registry record declares no evidence → fail-closed."""
        assert rc.parse_participation('mystery-bot:inline') == {}

    def test_admissible_and_inadmissible_pairs_are_separated(self, plan_context):
        """A mixed list admits only the pairs that match their own bot's shapes.

        Sourcery declares ``review_body`` and no inline shape, so its inline pair
        is dropped while CodeRabbit's is kept.
        """
        assert rc.parse_participation('coderabbit:inline,sourcery:inline') == CODERABBIT_EVIDENCE

    def test_a_shape_two_bots_both_declare_is_admitted_for_both(self, plan_context):
        """Admissibility is per-bot membership, not per-bot exclusivity.

        CodeRabbit and PR-Agent both declare ``inline``, so a mixed list admits it
        for each of them — a shape is not owned by the first bot to declare it.
        """
        assert rc.parse_participation('coderabbit:inline,cuioss-review-bot:inline') == {
            'coderabbit': 'inline',
            'cuioss-review-bot': 'inline',
        }

    def test_bot_with_empty_participation_evidence_is_never_proven(self, plan_context, monkeypatch):
        """FAIL-CLOSED: a bot declaring NO evidence shape can never be a participant.

        Every candidate pair is rejected, so however much the caller asserts, the
        bot resolves to ``absent`` and — when required — holds the step open. A bot
        whose publish shape nobody has recorded is never silently credited.
        """
        monkeypatch.setattr(rc.bot_registry, 'participation_evidence', lambda _bot: [])

        assert rc.parse_participation('coderabbit:inline') == {}
        assert rc.parse_participation('coderabbit:review_body') == {}

        plan_id = 'rc-empty-evidence'
        plan_context.plan_dir_for(plan_id)
        result = rc.check_completeness(
            plan_id, ['coderabbit'], participated_bots=rc.parse_participation('coderabbit:inline')
        )

        assert result['participation_complete'] is False
        assert _state_of(result, 'coderabbit') == rc.STATE_ABSENT
        assert result['unproven_bots'] == ['coderabbit']


class TestPRAgentParticipation:
    """PR-Agent is proven by a declared publish shape plus movement — never by check state."""

    def test_guide_comment_is_its_evidence(self, plan_context):
        """Its single persistent `issue_comment` IS its review artifact."""
        plan_id = 'rc-cuioss-review-bot-guide'
        plan_context.plan_dir_for(plan_id)

        result = rc.check_completeness(plan_id, ['cuioss-review-bot'], participated_bots=PR_AGENT_EVIDENCE)

        assert result['participation_complete'] is True
        assert _state_of(result, 'cuioss-review-bot') == rc.STATE_PARTICIPATED_BUT_EMPTY

    def test_inline_comment_is_also_its_evidence(self, plan_context):
        """`/improve` publishes inline suggestions, so an inline pair proves it too.

        The registry declares ``inline`` alongside ``issue_comment``, so an
        observation of the label-gated shape is admissible on its own.
        """
        plan_id = 'rc-cuioss-review-bot-inline'
        plan_context.plan_dir_for(plan_id)
        _seed(plan_id, 'cuioss-review-bot', resolution='fixed')

        result = rc.check_completeness(
            plan_id, ['cuioss-review-bot'], participated_bots=rc.parse_participation('cuioss-review-bot:inline')
        )

        assert result['participation_complete'] is True
        assert _state_of(result, 'cuioss-review-bot') != rc.STATE_ABSENT

    def test_absent_inline_shape_does_not_make_it_unproven(self, plan_context):
        """An absent inline count is NOT evidence of non-participation.

        ``/improve`` is label-gated per pull request, so on most repositories the
        inline shape is simply never published. The Guide comment alone therefore
        still proves participation — reading the missing inline shape as a failure
        would score the bot unproven on every repository that did not opt in.
        """
        plan_id = 'rc-cuioss-review-bot-guide-only'
        plan_context.plan_dir_for(plan_id)

        result = rc.check_completeness(
            plan_id, ['cuioss-review-bot'], participated_bots=rc.parse_participation('cuioss-review-bot:issue_comment')
        )

        assert result['participation_complete'] is True
        assert _state_of(result, 'cuioss-review-bot') != rc.STATE_ABSENT

    def test_a_shape_it_does_not_declare_is_still_not_its_evidence(self, plan_context):
        """The widening is an enumeration, not a blanket admission.

        ``review_body`` is a real publish shape for other bots and is NOT declared
        by PR-Agent, so it proves nothing here — without this control the widened
        record would be indistinguishable from "any shape counts".
        """
        plan_id = 'rc-cuioss-review-bot-review-body'
        plan_context.plan_dir_for(plan_id)

        assert rc.parse_participation('cuioss-review-bot:review_body') == {}

        result = rc.check_completeness(
            plan_id, ['cuioss-review-bot'], participated_bots=rc.parse_participation('cuioss-review-bot:review_body')
        )

        assert result['participation_complete'] is False
        assert _state_of(result, 'cuioss-review-bot') == rc.STATE_ABSENT

    def test_check_state_is_not_its_evidence(self, plan_context):
        """It posts NO check-run, so no check signal can stand in for participation.

        The predicate takes no check-state input at all for participation — a
        completion signal only ever feeds the orthogonal ``in_progress`` timing
        state, which is an UNPROVEN state, not a proven one.
        """
        plan_id = 'rc-cuioss-review-bot-check'
        plan_context.plan_dir_for(plan_id)

        result = rc.check_completeness(plan_id, ['cuioss-review-bot'], in_progress_bots=['cuioss-review-bot'])

        assert result['participation_complete'] is False
        assert _state_of(result, 'cuioss-review-bot') == rc.STATE_IN_PROGRESS
        assert result['unproven_bots'] == ['cuioss-review-bot']

    def test_registry_declares_update_movement_requirement(self, plan_context):
        """The in-place-edit qualifier is registry data, not a code branch.

        PR-Agent re-reviews by editing the SAME Guide comment, and CodeRabbit
        likewise edits its summary comment in place, so BOTH records set
        ``participation_requires_update``; ``sourcery`` appends a new comment per
        review and does not. Two of the three registered bots therefore declare the
        flag, which is the point: the producer reads the flag, so a second bot
        adopting in-place editing is a registry edit with no bot-name literal to
        change anywhere.
        """
        assert rc.bot_registry.participation_requires_update('cuioss-review-bot') is True
        assert rc.bot_registry.participation_requires_update('coderabbit') is True
        assert rc.bot_registry.participation_requires_update('sourcery') is False

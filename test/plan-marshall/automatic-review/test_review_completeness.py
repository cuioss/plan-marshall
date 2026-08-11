#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for review_completeness.py — the automatic-review step-done PARTICIPATION guard.

The predicate classifies every required ∪ optional bot into exactly one state and
reports whether every REQUIRED bot's participation is proven:

    participated            — proven participant that filed at least one finding
    participated_but_empty  — proven participant that filed none (accounted-for)
    refused_awaitable       — published a refusal whose window reopens on its own
    refused_hard            — published a refusal that does not usefully reopen
    refused_unknown         — published a refusal whose class the registry declares
                              unknown (neither awaitable nor a hard quota); its own
                              member, never folded into refused_hard
    participated_stale      — published in a declared shape, but the currency test
                              failed, so the review predates the merge candidate
                              (blocking, yet remedied by a re-trigger rather than by
                              awaiting)
    declined                — answered a re-review of the merge candidate without
                              producing a review of it (an incremental-review decline;
                              blocking, yet remedied by accepting the decline rather
                              than re-triggering a bot that already declined)
    in_progress             — review still running at the poll bound
    absent                  — no evidence of any kind (the fail-closed default)

Participation is **evidence-typed, not presence-typed**: a bot counts only when an
observed comment's ``kind`` is one of the publish shapes its registry record
declares in ``participation_evidence``. **The quorum is over ``required_bots``
ONLY** — an optional bot is classified and reported for visibility but never gates
the verdict. ``triage_ran=False`` (default, the FIND-only step) treats a
``pending`` finding as the expected awaiting-triage state that does NOT block;
``triage_ran=True`` treats a still-``pending`` required finding as a real
incompleteness.

The verdict proves PARTICIPATION, never review QUALITY — the three D8-interaction
obligations that follow from that ceiling are pinned by
``TestParticipationIsNotReviewQuality`` below. See
``automatic-review/standards/bot-participation-contract.md``.

The store is seeded in-process via ``_findings_core.add_finding`` /
``resolve_finding`` under the ``plan_context`` PLAN_BASE_DIR sandbox, so
``check_completeness`` reads a real per-plan store rather than a stub.
"""

from __future__ import annotations

import sys

import pytest

from _bot_flag_derivation import derive_bot_flags
from conftest import get_script_path, run_script

SCRIPT_PATH = get_script_path('plan-marshall', 'automatic-review', 'review_completeness.py')
SCRIPTS_DIR = SCRIPT_PATH.parent

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import review_completeness as rc  # noqa: E402
import _findings_core as fc  # noqa: E402

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

# Evidence pairs that match each bot's DECLARED participation_evidence. Derived by
# name from the registry docs rather than invented, so a registry change that
# retires a publish shape breaks these tests loudly instead of silently.
CODERABBIT_EVIDENCE = {'coderabbit': 'inline'}
SOURCERY_EVIDENCE = {'sourcery': 'review_body'}
PR_AGENT_EVIDENCE = {'pr-agent': 'issue_comment'}


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


class TestEvidenceTyping:
    """A bot is a participant only via the publish shapes its registry doc declares."""

    def test_each_bots_declared_shape_proves_participation(self, plan_context):
        """Each bot's OWN declared evidence shape is admitted."""
        assert rc.parse_participation('coderabbit:inline') == CODERABBIT_EVIDENCE
        assert rc.parse_participation('coderabbit:review_body') == {'coderabbit': 'review_body'}
        assert rc.parse_participation('sourcery:review_body') == SOURCERY_EVIDENCE
        assert rc.parse_participation('pr-agent:issue_comment') == PR_AGENT_EVIDENCE

    def test_a_shape_the_bot_does_not_publish_is_not_evidence(self, plan_context):
        """Evidence is per-bot: another bot's publish shape proves nothing here.

        Sourcery publishes no inline comments and CodeRabbit publishes no
        standalone issue comment, so neither pair is admissible even though both
        name a real publish shape for SOME bot.
        """
        assert rc.parse_participation('sourcery:inline') == {}
        assert rc.parse_participation('coderabbit:issue_comment') == {}

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
        assert rc.parse_participation('coderabbit:inline,pr-agent:inline') == {
            'coderabbit': 'inline',
            'pr-agent': 'inline',
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


# =============================================================================
# PR-Agent — an unconditional Guide comment plus a label-gated inline shape
# =============================================================================


class TestPRAgentParticipation:
    """PR-Agent is proven by a declared publish shape plus movement — never by check state."""

    def test_guide_comment_is_its_evidence(self, plan_context):
        """Its single persistent `issue_comment` IS its review artifact."""
        plan_id = 'rc-pr-agent-guide'
        plan_context.plan_dir_for(plan_id)

        result = rc.check_completeness(
            plan_id, ['pr-agent'], participated_bots=PR_AGENT_EVIDENCE
        )

        assert result['participation_complete'] is True
        assert _state_of(result, 'pr-agent') == rc.STATE_PARTICIPATED_BUT_EMPTY

    def test_inline_comment_is_also_its_evidence(self, plan_context):
        """`/improve` publishes inline suggestions, so an inline pair proves it too.

        The registry declares ``inline`` alongside ``issue_comment``, so an
        observation of the label-gated shape is admissible on its own.
        """
        plan_id = 'rc-pr-agent-inline'
        plan_context.plan_dir_for(plan_id)
        _seed(plan_id, 'pr-agent', resolution='fixed')

        result = rc.check_completeness(
            plan_id, ['pr-agent'], participated_bots=rc.parse_participation('pr-agent:inline')
        )

        assert result['participation_complete'] is True
        assert _state_of(result, 'pr-agent') != rc.STATE_ABSENT

    def test_absent_inline_shape_does_not_make_it_unproven(self, plan_context):
        """An absent inline count is NOT evidence of non-participation.

        ``/improve`` is label-gated per pull request, so on most repositories the
        inline shape is simply never published. The Guide comment alone therefore
        still proves participation — reading the missing inline shape as a failure
        would score the bot unproven on every repository that did not opt in.
        """
        plan_id = 'rc-pr-agent-guide-only'
        plan_context.plan_dir_for(plan_id)

        result = rc.check_completeness(
            plan_id, ['pr-agent'], participated_bots=rc.parse_participation('pr-agent:issue_comment')
        )

        assert result['participation_complete'] is True
        assert _state_of(result, 'pr-agent') != rc.STATE_ABSENT

    def test_a_shape_it_does_not_declare_is_still_not_its_evidence(self, plan_context):
        """The widening is an enumeration, not a blanket admission.

        ``review_body`` is a real publish shape for other bots and is NOT declared
        by PR-Agent, so it proves nothing here — without this control the widened
        record would be indistinguishable from "any shape counts".
        """
        plan_id = 'rc-pr-agent-review-body'
        plan_context.plan_dir_for(plan_id)

        assert rc.parse_participation('pr-agent:review_body') == {}

        result = rc.check_completeness(
            plan_id, ['pr-agent'], participated_bots=rc.parse_participation('pr-agent:review_body')
        )

        assert result['participation_complete'] is False
        assert _state_of(result, 'pr-agent') == rc.STATE_ABSENT

    def test_check_state_is_not_its_evidence(self, plan_context):
        """It posts NO check-run, so no check signal can stand in for participation.

        The predicate takes no check-state input at all for participation — a
        completion signal only ever feeds the orthogonal ``in_progress`` timing
        state, which is an UNPROVEN state, not a proven one.
        """
        plan_id = 'rc-pr-agent-check'
        plan_context.plan_dir_for(plan_id)

        result = rc.check_completeness(
            plan_id, ['pr-agent'], in_progress_bots=['pr-agent']
        )

        assert result['participation_complete'] is False
        assert _state_of(result, 'pr-agent') == rc.STATE_IN_PROGRESS
        assert result['unproven_bots'] == ['pr-agent']

    def test_registry_declares_update_movement_requirement(self, plan_context):
        """The in-place-edit qualifier is registry data, not a code branch.

        PR-Agent re-reviews by editing the SAME Guide comment, so its record sets
        ``participation_requires_update``; the bots that append a new comment per
        review do not. The producer reads this flag — there is no bot-name literal.
        """
        assert rc.bot_registry.participation_requires_update('pr-agent') is True
        assert rc.bot_registry.participation_requires_update('coderabbit') is False
        assert rc.bot_registry.participation_requires_update('sourcery') is False


# =============================================================================
# The quorum is over required_bots only
# =============================================================================


class TestQuorumIsRequiredOnly:
    """Only required bots gate; optional bots are reported and ignored by the verdict."""

    def test_silent_optional_bot_does_not_block(self, plan_context):
        """An OPTIONAL bot with no evidence is reported but does NOT block."""
        plan_id = 'rc-optional-silent'
        plan_context.plan_dir_for(plan_id)
        _seed(plan_id, 'coderabbit', resolution='fixed')

        result = rc.check_completeness(
            plan_id,
            ['coderabbit'],
            optional_bots=['sourcery'],
            participated_bots=CODERABBIT_EVIDENCE,
        )

        assert result['participation_complete'] is True
        assert result['unproven_bots'] == ['sourcery']
        assert _state_of(result, 'sourcery') == rc.STATE_ABSENT

    def test_silent_required_bot_blocks(self, plan_context):
        """The counterpart against an otherwise identical store: required DOES block.

        Paired with the test above so the assertion isolates the required/optional
        dial as the only difference.
        """
        plan_id = 'rc-required-silent'
        plan_context.plan_dir_for(plan_id)
        _seed(plan_id, 'coderabbit', resolution='fixed')

        result = rc.check_completeness(
            plan_id, ['coderabbit', 'sourcery'], participated_bots=CODERABBIT_EVIDENCE
        )

        assert result['participation_complete'] is False
        assert result['unproven_bots'] == ['sourcery']

    def test_pending_optional_bot_does_not_block_after_triage(self, plan_context):
        """``triage_ran`` escalates a pending finding only for a REQUIRED bot."""
        plan_id = 'rc-optional-pending'
        plan_context.plan_dir_for(plan_id)
        _seed(plan_id, 'sourcery', resolution='pending')

        result = rc.check_completeness(
            plan_id,
            [],
            optional_bots=['sourcery'],
            triage_ran=True,
            participated_bots=SOURCERY_EVIDENCE,
        )

        assert result['participation_complete'] is True
        assert result['pending_bots'] == ['sourcery']

    def test_empty_required_bots_is_vacuously_complete(self, plan_context):
        """No required bots means nothing to await — the quorum is vacuous.

        An EMPTY ``required_bots`` is a legitimate configured state (the operator
        answered "none"), not a misconfiguration.
        """
        plan_id = 'rc-no-bots'
        plan_context.plan_dir_for(plan_id)

        result = rc.check_completeness(plan_id, [])

        assert result['participation_complete'] is True
        assert result['pending_bots'] == []
        assert result['unproven_bots'] == []
        assert result['bot_states'] == []

    def test_bot_listed_both_required_and_optional_is_classified_once(self, plan_context):
        """A bot named in BOTH lists is classified once, as required."""
        plan_id = 'rc-both-lists'
        plan_context.plan_dir_for(plan_id)

        result = rc.check_completeness(plan_id, ['sourcery'], optional_bots=['sourcery'])

        assert result['unproven_bots'] == ['sourcery']
        assert result['participation_complete'] is False
        assert len(result['bot_states']) == 1


# =============================================================================
# The state taxonomy — every classified bot resolves to exactly one member
# =============================================================================


class TestStateTaxonomy:
    """Each bot resolves to exactly one state; refusals split by registry class."""

    def test_proven_participant_with_findings_is_participated(self, plan_context):
        plan_id = 'rc-state-participated'
        plan_context.plan_dir_for(plan_id)
        _seed(plan_id, 'coderabbit', resolution='fixed')

        result = rc.check_completeness(
            plan_id, ['coderabbit'], participated_bots=CODERABBIT_EVIDENCE
        )

        assert _state_of(result, 'coderabbit') == rc.STATE_PARTICIPATED
        assert result['participation_complete'] is True

    def test_proven_participant_without_findings_is_participated_but_empty(self, plan_context):
        """It did its pass and had nothing actionable to say — accounted-for.

        This is the member most often misread: a clean review is a SUCCESSFUL
        review, and treating it as an incompleteness would hold a clean PR open
        forever.
        """
        plan_id = 'rc-state-empty'
        plan_context.plan_dir_for(plan_id)

        result = rc.check_completeness(
            plan_id, ['coderabbit'], participated_bots=CODERABBIT_EVIDENCE
        )

        assert _state_of(result, 'coderabbit') == rc.STATE_PARTICIPATED_BUT_EMPTY
        assert result['participation_complete'] is True
        assert result['unproven_bots'] == []

    def test_refusal_splits_by_registry_rate_limit_class(self, plan_context):
        """The refusal member comes from the bot's own class — no bot-name literal.

        CodeRabbit's limit is a rolling window that reopens (``awaitable_window``);
        Sourcery's is a per-PR size ceiling that never reopens (``hard_quota``). The
        caller supplies only the observation that each refused.
        """
        plan_id = 'rc-state-refused'
        plan_context.plan_dir_for(plan_id)

        result = rc.check_completeness(
            plan_id, ['coderabbit', 'sourcery'], refused_bots=['coderabbit', 'sourcery']
        )

        assert _state_of(result, 'coderabbit') == rc.STATE_REFUSED_AWAITABLE
        assert _state_of(result, 'sourcery') == rc.STATE_REFUSED_HARD
        assert result['participation_complete'] is False
        assert result['unproven_bots'] == ['coderabbit', 'sourcery']

    def test_refusal_of_unknown_class_is_its_own_state_not_hard(self, plan_context):
        """An ``unknown`` rate-limit class resolves to ``refused_unknown``, never ``refused_hard``.

        The three-valued ``rate_limit_class`` splits ONE-TO-ONE into three refusal
        members: ``awaitable_window`` -> ``refused_awaitable``, ``hard_quota`` ->
        ``refused_hard``, ``unknown`` -> ``refused_unknown``. A binary
        ``== 'awaitable_window'`` test collapsed ``unknown`` into ``refused_hard``,
        rendering a declared *we-do-not-know* as a positive *hard quota* finding —
        which steers an operator toward "waiting is futile, force it" when the refusal
        shape had simply never been observed. ``refused_unknown`` is its own member so
        the declared ignorance reaches the reader as ignorance, not as a hard quota.
        It is still an UNPROVEN, blocking state — a refusal is a refusal — but a
        DIFFERENT one from ``refused_hard``.
        """
        plan_id = 'rc-state-refused-unknown'
        plan_context.plan_dir_for(plan_id)

        result = rc.check_completeness(plan_id, ['pr-agent'], refused_bots=['pr-agent'])

        assert rc.bot_registry.rate_limit_class('pr-agent') == 'unknown'
        assert _state_of(result, 'pr-agent') == rc.STATE_REFUSED_UNKNOWN
        assert _state_of(result, 'pr-agent') != rc.STATE_REFUSED_HARD
        assert rc.STATE_REFUSED_UNKNOWN in rc._UNPROVEN_STATES
        assert result['participation_complete'] is False

    def test_refusal_state_maps_one_to_one_over_the_three_classes(self, plan_context):
        """``_refusal_state`` is total and injective over the three declared classes.

        Asserted directly on the mapping so a future fold of any two classes into one
        member breaks here, not only via a downstream verdict. A value that is neither
        of the first two — including a malformed one — fails closed to
        ``refused_unknown`` rather than being asserted as a hard quota.
        """
        assert rc._refusal_state('awaitable_window') == rc.STATE_REFUSED_AWAITABLE
        assert rc._refusal_state('hard_quota') == rc.STATE_REFUSED_HARD
        assert rc._refusal_state('unknown') == rc.STATE_REFUSED_UNKNOWN
        assert rc._refusal_state('some_unrecognised_value') == rc.STATE_REFUSED_UNKNOWN
        # The three refusal members are distinct — no two collapse into one.
        assert len({rc.STATE_REFUSED_AWAITABLE, rc.STATE_REFUSED_HARD, rc.STATE_REFUSED_UNKNOWN}) == 3

    def test_no_evidence_of_any_kind_is_absent(self, plan_context):
        plan_id = 'rc-state-absent'
        plan_context.plan_dir_for(plan_id)

        result = rc.check_completeness(plan_id, ['coderabbit'])

        assert _state_of(result, 'coderabbit') == rc.STATE_ABSENT

    def test_proven_participation_outranks_a_stale_refusal_observation(self, plan_context):
        """Positive diff-derived evidence beats an absence-of-review signal.

        A bot that refused an earlier attempt and then reviewed on a retry is a
        participant; the refusal observation must not veto observed evidence.
        """
        plan_id = 'rc-state-precedence'
        plan_context.plan_dir_for(plan_id)
        _seed(plan_id, 'coderabbit', resolution='fixed')

        result = rc.check_completeness(
            plan_id,
            ['coderabbit'],
            participated_bots=CODERABBIT_EVIDENCE,
            refused_bots=['coderabbit'],
            in_progress_bots=['coderabbit'],
        )

        assert _state_of(result, 'coderabbit') == rc.STATE_PARTICIPATED

    def test_stale_participation_is_participated_stale_and_blocks_like_absent(self, plan_context):
        """A required bot whose publish failed the currency test blocks exactly as ``absent``.

        The state is a RENAME of what was already reported, not a softening: the
        gate outcome is asserted to be identical to the ``absent`` control below,
        so nothing about this member can be read as relaxing the quorum. What
        changes is that the operator now learns the remedy is a re-review trigger
        rather than an escalation for a bot that never engaged.
        """
        plan_id = 'rc-state-stale'
        plan_context.plan_dir_for(plan_id)

        result = rc.check_completeness(
            plan_id, ['coderabbit'], stale_participation_bots=['coderabbit']
        )

        assert _state_of(result, 'coderabbit') == rc.STATE_PARTICIPATED_STALE
        assert result['unproven_bots'] == ['coderabbit']
        assert result['participation_complete'] is False

        # The absent control, over an otherwise identical store: same verdict, same
        # unproven set. Only the reported state differs.
        control_id = 'rc-state-stale-absent-control'
        plan_context.plan_dir_for(control_id)
        control = rc.check_completeness(control_id, ['coderabbit'])

        assert control['participation_complete'] == result['participation_complete']
        assert control['unproven_bots'] == result['unproven_bots']
        assert _state_of(control, 'coderabbit') == rc.STATE_ABSENT

    def test_stale_participation_blocks_in_both_triage_modes(self, plan_context):
        """Stale participation is a participation gap, independent of triage state.

        Pairs with the pending-finding cases: a pending finding's contribution
        depends on ``triage_ran``, an unproven state's never does.
        """
        for triage_ran in (False, True):
            plan_id = f'rc-state-stale-triage-{str(triage_ran).lower()}'
            plan_context.plan_dir_for(plan_id)

            result = rc.check_completeness(
                plan_id,
                ['coderabbit'],
                triage_ran=triage_ran,
                stale_participation_bots=['coderabbit'],
            )

            assert result['participation_complete'] is False
            assert _state_of(result, 'coderabbit') == rc.STATE_PARTICIPATED_STALE

    def test_stale_optional_bot_is_reported_but_does_not_block(self, plan_context):
        """The required/optional dial governs the new member exactly as the others."""
        plan_id = 'rc-state-stale-optional'
        plan_context.plan_dir_for(plan_id)

        result = rc.check_completeness(
            plan_id, [], optional_bots=['coderabbit'], stale_participation_bots=['coderabbit']
        )

        assert _state_of(result, 'coderabbit') == rc.STATE_PARTICIPATED_STALE
        assert result['unproven_bots'] == ['coderabbit']
        assert result['participation_complete'] is True

    def test_declined_bot_is_declined_and_blocks_like_absent(self, plan_context):
        """A required bot that answered a re-review without reviewing this commit blocks — D3.

        The incremental-review decline (``head_sha_verified: false``): the bot engaged
        but did not review the merge candidate, so it is not a proven participant and
        the quorum EXCLUDES it. The gate outcome is asserted identical to the ``absent``
        control, so nothing about the member relaxes the quorum; only the reported state
        and its remedy (accept the decline rather than re-trigger) differ.
        """
        plan_id = 'rc-state-declined'
        plan_context.plan_dir_for(plan_id)

        result = rc.check_completeness(plan_id, ['pr-agent'], declined_bots=['pr-agent'])

        assert _state_of(result, 'pr-agent') == rc.STATE_DECLINED
        assert result['unproven_bots'] == ['pr-agent']
        assert result['participation_complete'] is False

        control_id = 'rc-state-declined-absent-control'
        plan_context.plan_dir_for(control_id)
        control = rc.check_completeness(control_id, ['pr-agent'])

        assert control['participation_complete'] == result['participation_complete']
        assert control['unproven_bots'] == result['unproven_bots']
        assert _state_of(control, 'pr-agent') == rc.STATE_ABSENT

    def test_declined_is_an_unproven_state_distinct_from_refused_and_stale(self, plan_context):
        """``declined`` blocks like the others but is a DISTINCT member with its own remedy.

        Pins the two halves the plan insists on keeping disjoint: an explicit refusal
        (``refused_*``) and an incremental-review decline (``declined``) both leave the
        bot out of the quorum, but they are different observations with different
        remedies, so neither collapses into the other or into ``participated_stale``.
        """
        assert rc.STATE_DECLINED in rc._UNPROVEN_STATES
        assert rc.STATE_DECLINED != rc.STATE_PARTICIPATED_STALE
        assert rc.STATE_DECLINED != rc.STATE_REFUSED_AWAITABLE
        assert rc.STATE_DECLINED != rc.STATE_REFUSED_HARD

    def test_refusal_and_incremental_decline_are_both_excluded_from_quorum(self, plan_context):
        """The two refusal shapes each keep the bot out of the quorum — D3, one test per shape.

        Shape A — an EXPLICIT refusal notice — resolves to a refusal member and does not
        satisfy the quorum. Shape B — an incremental-review DECLINE — resolves to
        ``declined`` and does not satisfy the quorum either. Both are asserted against the
        same required set so the exclusion is the property under test, not the state name.
        """
        # Shape A: explicit refusal.
        refusal_id = 'rc-two-shapes-refusal'
        plan_context.plan_dir_for(refusal_id)
        refusal = rc.check_completeness(refusal_id, ['coderabbit'], refused_bots=['coderabbit'])
        assert refusal['participation_complete'] is False
        assert 'coderabbit' in refusal['unproven_bots']
        assert _state_of(refusal, 'coderabbit') in (rc.STATE_REFUSED_AWAITABLE, rc.STATE_REFUSED_HARD)

        # Shape B: incremental-review decline.
        decline_id = 'rc-two-shapes-decline'
        plan_context.plan_dir_for(decline_id)
        decline = rc.check_completeness(decline_id, ['pr-agent'], declined_bots=['pr-agent'])
        assert decline['participation_complete'] is False
        assert 'pr-agent' in decline['unproven_bots']
        assert _state_of(decline, 'pr-agent') == rc.STATE_DECLINED

    def test_a_refusal_outranks_a_decline(self, plan_context):
        """A bot with BOTH an explicit refusal and a decline is classified refused.

        The branch order: an explicit rate-limit / quota / size notice is the more
        specific "will not review now" signal, so it outranks the quieter incremental
        decline — mirroring the refusal-outranks-stale precedence.
        """
        plan_id = 'rc-refusal-outranks-decline'
        plan_context.plan_dir_for(plan_id)

        result = rc.check_completeness(
            plan_id, ['coderabbit'], refused_bots=['coderabbit'], declined_bots=['coderabbit']
        )

        assert _state_of(result, 'coderabbit') in (rc.STATE_REFUSED_AWAITABLE, rc.STATE_REFUSED_HARD)
        assert _state_of(result, 'coderabbit') != rc.STATE_DECLINED

    def test_proven_participation_outranks_a_decline(self, plan_context):
        """A bot that both declined an earlier attempt and later reviewed is ``participated``.

        Proven, diff-derived participation is positive evidence and outranks every
        absence-or-refusal signal, ``declined`` included. A finding is seeded so the
        proven bot resolves to ``participated`` rather than ``participated_but_empty`` —
        either way it is NOT ``declined``, which is the property under test.
        """
        plan_id = 'rc-participation-outranks-decline'
        plan_context.plan_dir_for(plan_id)
        _seed(plan_id, 'coderabbit')

        result = rc.check_completeness(
            plan_id,
            ['coderabbit'],
            participated_bots=CODERABBIT_EVIDENCE,
            declined_bots=['coderabbit'],
        )

        assert _state_of(result, 'coderabbit') == rc.STATE_PARTICIPATED

    def test_proven_participation_outranks_stale_participation(self, plan_context):
        """Precedence edge (a): proven evidence beats a stale observation.

        A bot with one fresh qualifying comment and one stale one is a participant.
        The producer already subtracts the proven set, so this arrival shape should
        not occur — the branch order is asserted anyway, because a classifier that
        depended on its caller having filtered correctly would be one refactor away
        from crediting nothing.
        """
        plan_id = 'rc-state-stale-vs-proven'
        plan_context.plan_dir_for(plan_id)
        _seed(plan_id, 'coderabbit', resolution='fixed')

        result = rc.check_completeness(
            plan_id,
            ['coderabbit'],
            participated_bots=CODERABBIT_EVIDENCE,
            stale_participation_bots=['coderabbit'],
        )

        assert _state_of(result, 'coderabbit') == rc.STATE_PARTICIPATED

    @pytest.mark.parametrize('bot_kind', _REGISTERED_BOTS)
    def test_a_refusal_outranks_stale_participation(self, bot_kind, plan_context):
        """Precedence edge (b): a newer refusal outranks a stale publish.

        A refusal names a reason the bot will not review NOW, whereas a stale
        publish only says its last review predates this HEAD — and the two call for
        different remedies (wait out or accept the refusal vs re-trigger), so the
        newer and more actionable signal wins.

        Swept over the WHOLE registered population, and the expected member is
        derived from each bot's own ``rate_limit_class`` rather than written as a
        literal, so no bot name is pinned here and a bot whose class changes is
        still asserted correctly.
        """
        plan_id = f'rc-stale-vs-refusal-{bot_kind}'
        plan_context.plan_dir_for(plan_id)

        result = rc.check_completeness(
            plan_id,
            [bot_kind],
            refused_bots=[bot_kind],
            stale_participation_bots=[bot_kind],
        )

        # The expected member is derived ONE-TO-ONE from the bot's own three-valued
        # rate_limit_class, never written as a literal, so a bot whose class is
        # ``unknown`` (pr-agent) is asserted as ``refused_unknown`` — not folded into
        # ``refused_hard`` — and the sweep stays correct if a bot's class changes.
        expected = rc._refusal_state(rc.bot_registry.rate_limit_class(bot_kind))

        assert _state_of(result, bot_kind) == expected
        assert _state_of(result, bot_kind) != rc.STATE_PARTICIPATED_STALE

    def test_stale_participation_outranks_in_progress(self, plan_context):
        """A stale publish is stronger evidence than a still-running review.

        The branch sits ABOVE ``in_progress``: an observed publish — even a stale
        one — says more about what the bot did than an unfinished check-run does.
        """
        plan_id = 'rc-state-stale-vs-in-progress'
        plan_context.plan_dir_for(plan_id)

        result = rc.check_completeness(
            plan_id,
            ['coderabbit'],
            in_progress_bots=['coderabbit'],
            stale_participation_bots=['coderabbit'],
        )

        assert _state_of(result, 'coderabbit') == rc.STATE_PARTICIPATED_STALE

    def test_stale_participation_is_an_unproven_state(self, plan_context):
        """The membership is asserted on the constant set, not only on a verdict.

        ``_UNPROVEN_STATES`` is what makes the member block; asserting the set
        directly stops a future edit from removing the member while every
        verdict-level test still passes for an unrelated reason.
        """
        assert rc.STATE_PARTICIPATED_STALE in rc._UNPROVEN_STATES
        # And it is never confused with either accounted-for outcome.
        assert rc.STATE_PARTICIPATED not in rc._UNPROVEN_STATES
        assert rc.STATE_PARTICIPATED_BUT_EMPTY not in rc._UNPROVEN_STATES

    def test_not_triggered_refines_absent_and_blocks(self, plan_context):
        """With the PR-wide flag set, an otherwise-absent required bot is not_triggered.

        The refinement, and the whole point of the member: ``absent`` means the bot
        was asked and did not answer, so its remedy is to escalate a
        non-participating reviewer. ``not_triggered`` means nothing ever asked it, so
        its remedy is to trigger the review. Both block; the operator is pointed at
        opposite actions.
        """
        plan_id = 'rc-state-not-triggered'
        plan_context.plan_dir_for(plan_id)

        result = rc.check_completeness(plan_id, ['coderabbit'], not_triggered=True)

        assert _state_of(result, 'coderabbit') == rc.STATE_NOT_TRIGGERED
        assert result['unproven_bots'] == ['coderabbit']
        assert result['participation_complete'] is False

    def test_not_triggered_false_leaves_the_absent_verdict_untouched(self, plan_context):
        """The paired control: without the flag the same store still reports absent.

        Isolates the PR-wide flag as the only difference, so the new member cannot
        be credited with a verdict change it did not cause.
        """
        plan_id = 'rc-state-not-triggered-control'
        plan_context.plan_dir_for(plan_id)

        result = rc.check_completeness(plan_id, ['coderabbit'], not_triggered=False)

        assert _state_of(result, 'coderabbit') == rc.STATE_ABSENT
        assert result['participation_complete'] is False

    def test_not_triggered_applies_pr_wide_to_every_classified_bot(self, plan_context):
        """One PR-wide condition resolves EVERY otherwise-absent bot, not just the first.

        The flag is a single bool precisely because the condition holds for the whole
        PR. Sweeping the registered population pins that the branch is inside the
        per-bot loop rather than applied once.
        """
        plan_id = 'rc-state-not-triggered-pr-wide'
        plan_context.plan_dir_for(plan_id)
        # The module-scope population, already guarded non-empty at import.
        bots = _REGISTERED_BOTS

        result = rc.check_completeness(plan_id, bots, not_triggered=True)

        assert {r['state'] for r in result['bot_states']} == {rc.STATE_NOT_TRIGGERED}
        assert sorted(result['unproven_bots']) == sorted(bots)

    @pytest.mark.parametrize(
        'observation',
        ['participated_with_findings', 'participated_empty', 'refused', 'in_progress', 'stale'],
    )
    def test_not_triggered_never_overrides_a_per_bot_observation(self, observation, plan_context):
        """Precedence: a PR-wide "nothing ran" must not overwrite evidence that it did.

        The flag is the LAST branch before the fallthrough, so every state carrying
        positive evidence about a specific bot outranks it. Swept across all five
        earlier states rather than spot-checked on one, because a misplaced branch
        would capture whichever states sit below it — a single-state check would pass
        while the branch sat one line too high.
        """
        plan_id = f'rc-not-triggered-precedence-{observation.replace("_", "-")}'
        plan_context.plan_dir_for(plan_id)

        kwargs: dict = {}
        expected: str
        if observation == 'participated_with_findings':
            _seed(plan_id, 'coderabbit', resolution='fixed')
            kwargs['participated_bots'] = CODERABBIT_EVIDENCE
            expected = rc.STATE_PARTICIPATED
        elif observation == 'participated_empty':
            kwargs['participated_bots'] = CODERABBIT_EVIDENCE
            expected = rc.STATE_PARTICIPATED_BUT_EMPTY
        elif observation == 'refused':
            kwargs['refused_bots'] = ['coderabbit']
            expected = rc.STATE_REFUSED_AWAITABLE
        elif observation == 'in_progress':
            kwargs['in_progress_bots'] = ['coderabbit']
            expected = rc.STATE_IN_PROGRESS
        else:
            kwargs['stale_participation_bots'] = ['coderabbit']
            expected = rc.STATE_PARTICIPATED_STALE

        result = rc.check_completeness(plan_id, ['coderabbit'], not_triggered=True, **kwargs)

        assert _state_of(result, 'coderabbit') == expected
        assert _state_of(result, 'coderabbit') != rc.STATE_NOT_TRIGGERED

    def test_not_triggered_is_an_unproven_state(self, plan_context):
        """Membership asserted on the constant set, not only via a verdict."""
        assert rc.STATE_NOT_TRIGGERED in rc._UNPROVEN_STATES

    def test_not_triggered_default_is_false(self, plan_context):
        """The parameter defaults FALSE, so no existing caller's verdict moves.

        The flag is opt-in: an existing caller that does not pass it keeps the
        ``absent`` verdict it had before the member existed.
        """
        plan_id = 'rc-state-not-triggered-default'
        plan_context.plan_dir_for(plan_id)

        result = rc.check_completeness(plan_id, ['coderabbit'])

        assert _state_of(result, 'coderabbit') == rc.STATE_ABSENT

    def test_stale_state_value_is_never_the_bare_word(self, plan_context):
        """The state value is ``participated_stale``, never a bare ``stale``.

        The short name would lose the very distinction the member exists to carry:
        that the bot DID publish, unlike a bot that never engaged.
        """
        assert rc.STATE_PARTICIPATED_STALE == 'participated_stale'

    def test_every_classified_bot_gets_exactly_one_state(self, plan_context):
        """The classification is total and mutually exclusive over required ∪ optional."""
        plan_id = 'rc-state-total'
        plan_context.plan_dir_for(plan_id)
        _seed(plan_id, 'coderabbit', resolution='fixed')

        result = rc.check_completeness(
            plan_id,
            ['coderabbit', 'sourcery'],
            optional_bots=['pr-agent'],
            participated_bots=CODERABBIT_EVIDENCE,
            refused_bots=['sourcery'],
        )

        classified = [r['bot_kind'] for r in result['bot_states']]
        assert classified == ['coderabbit', 'sourcery', 'pr-agent']
        assert len(set(classified)) == len(classified)
        known_states = {
            rc.STATE_ABSENT,
            rc.STATE_IN_PROGRESS,
            rc.STATE_REFUSED_AWAITABLE,
            rc.STATE_REFUSED_HARD,
            rc.STATE_REFUSED_UNKNOWN,
            rc.STATE_PARTICIPATED_BUT_EMPTY,
            rc.STATE_PARTICIPATED_STALE,
            rc.STATE_DECLINED,
            rc.STATE_NOT_TRIGGERED,
            rc.STATE_PARTICIPATED,
        }
        assert {r['state'] for r in result['bot_states']} <= known_states


# =============================================================================
# Triage-state awareness (unchanged semantics, new field names)
# =============================================================================


class TestTriageStateAwareness:
    """A pending finding blocks only once triage has run, and only for a required bot."""

    def test_pending_bot_does_not_block_pre_triage(self, plan_context):
        """At the FIND-only step a pending finding is the expected state."""
        plan_id = 'rc-pending-pre-triage'
        plan_context.plan_dir_for(plan_id)
        _seed(plan_id, 'coderabbit', resolution='pending')

        result = rc.check_completeness(
            plan_id, ['coderabbit'], participated_bots=CODERABBIT_EVIDENCE
        )

        assert result['participation_complete'] is True
        assert result['pending_bots'] == ['coderabbit']
        assert result['unproven_bots'] == []

    def test_pending_bot_blocks_after_triage(self, plan_context):
        """The SAME store loops back once triage has run."""
        plan_id = 'rc-pending-post-triage'
        plan_context.plan_dir_for(plan_id)
        _seed(plan_id, 'coderabbit', resolution='pending')

        result = rc.check_completeness(
            plan_id, ['coderabbit'], triage_ran=True, participated_bots=CODERABBIT_EVIDENCE
        )

        assert result['participation_complete'] is False
        assert result['pending_bots'] == ['coderabbit']

    def test_bot_with_multiple_findings_one_pending(self, plan_context):
        """A bot is pending if ANY of its findings is unresolved."""
        plan_id = 'rc-multi'
        plan_context.plan_dir_for(plan_id)
        _seed(plan_id, 'coderabbit', resolution='fixed')
        _seed(plan_id, 'coderabbit', resolution='pending')

        pre = rc.check_completeness(
            plan_id, ['coderabbit'], participated_bots=CODERABBIT_EVIDENCE
        )
        assert pre['participation_complete'] is True
        assert pre['pending_bots'] == ['coderabbit']

        post = rc.check_completeness(
            plan_id, ['coderabbit'], triage_ran=True, participated_bots=CODERABBIT_EVIDENCE
        )
        assert post['participation_complete'] is False

    def test_unproven_bot_blocks_in_both_triage_modes(self, plan_context):
        """Unproven participation is a gap independent of whether triage has run."""
        plan_id = 'rc-unproven-both-modes'
        plan_context.plan_dir_for(plan_id)
        _seed(plan_id, 'coderabbit', resolution='fixed')

        for triage_ran in (False, True):
            result = rc.check_completeness(
                plan_id,
                ['coderabbit', 'sourcery'],
                triage_ran=triage_ran,
                participated_bots=CODERABBIT_EVIDENCE,
            )
            assert result['participation_complete'] is False
            assert result['unproven_bots'] == ['sourcery']

    def test_empty_store_all_absent(self, plan_context):
        """Fail-closed: a store with no observations proves nothing."""
        plan_id = 'rc-empty-store'
        plan_context.plan_dir_for(plan_id)

        result = rc.check_completeness(plan_id, ['coderabbit', 'pr-agent'])

        assert result['participation_complete'] is False
        assert result['pending_bots'] == []
        assert result['unproven_bots'] == ['coderabbit', 'pr-agent']


# =============================================================================
# D8 interaction — participation is not review quality
# =============================================================================


class TestParticipationIsNotReviewQuality:
    """The three normative obligations from the PR body's distilled Intent section.

    The PR body carries an Intent section, which is exactly the kind of input that
    can make a shallow review LOOK like a real one. See
    ``standards/bot-participation-contract.md`` § "Participation is not review
    quality".
    """

    def test_envelope_declares_the_ceiling_machine_readably(self, plan_context):
        """Even a fully-satisfied quorum states that it proves participation only.

        The claim is machine-readable so a consumer cannot read the envelope as a
        quality statement without ignoring a field that says otherwise.
        """
        plan_id = 'rc-d8-ceiling'
        plan_context.plan_dir_for(plan_id)
        _seed(plan_id, 'coderabbit', resolution='fixed')

        result = rc.check_completeness(
            plan_id, ['coderabbit'], participated_bots=CODERABBIT_EVIDENCE
        )

        assert result['participation_complete'] is True
        assert result['proves'] == 'participation_only'

    def test_obligation_1_intent_echo_is_participation_not_review(self, plan_context):
        """A review that only restates the intent resolves to ``participated_but_empty``.

        The bot ran and said something, so it participated — but echoing the stated
        intent demonstrates no engagement with the diff, so it files no finding and
        must NOT be recorded as having delivered a review. Crediting an intent-echo
        as a review would let a PR pass on the strength of its own description.
        """
        plan_id = 'rc-d8-intent-echo'
        plan_context.plan_dir_for(plan_id)
        # The intent-echo review produced no actionable finding.

        result = rc.check_completeness(
            plan_id, ['coderabbit'], participated_bots=CODERABBIT_EVIDENCE
        )

        assert _state_of(result, 'coderabbit') == rc.STATE_PARTICIPATED_BUT_EMPTY
        assert _state_of(result, 'coderabbit') != rc.STATE_PARTICIPATED
        assert result['proves'] == 'participation_only'

    def test_obligation_2_intent_section_never_makes_the_verdict_looser(self, plan_context):
        """PARITY: the verdict is identical-or-stricter with an Intent section present.

        Same observed review artifacts, two PR bodies — one carrying a distilled
        Intent section, one not. The predicate must not become MORE permissive on
        the Intent-bearing PR: an empty review and a conformance-only review must
        resolve to exactly the state they would resolve to with no Intent section
        at all.
        """
        intent_free = 'thread from coderabbit'
        intent_bearing = (
            '## Intent\nRoute every thread-bearing disposition into its own thread.\n\n'
            'This change matches the stated intent and looks consistent with the goal.'
        )

        verdicts = []
        for label, detail in (('no-intent', intent_free), ('with-intent', intent_bearing)):
            plan_id = f'rc-d8-parity-{label}'
            plan_context.plan_dir_for(plan_id)
            _seed(plan_id, 'coderabbit', resolution='pending', detail=detail)
            verdicts.append(
                rc.check_completeness(
                    plan_id,
                    ['coderabbit'],
                    triage_ran=True,
                    participated_bots=CODERABBIT_EVIDENCE,
                )
            )

        without, with_intent = verdicts
        # Identical, therefore trivially never looser.
        assert with_intent['participation_complete'] == without['participation_complete']
        assert with_intent['bot_states'] == without['bot_states']
        assert with_intent['pending_bots'] == without['pending_bots']
        assert with_intent['unproven_bots'] == without['unproven_bots']
        # And specifically NOT looser: the conformance-only review still blocks.
        assert with_intent['participation_complete'] is False

    def test_obligation_2_no_predicate_branch_keys_on_an_intent_section(self, plan_context):
        """Structural proof that the parity above cannot regress by a new branch.

        The parity test shows the CURRENT verdicts agree; this asserts the
        predicate has no way to tell the two apart in the first place — it takes no
        PR-body input and mentions no Intent concept anywhere in its source.
        """
        source = SCRIPT_PATH.read_text(encoding='utf-8').lower()
        for forbidden in ('intent_section', 'has_intent', 'pr_body', 'intent-section'):
            assert forbidden not in source, f'predicate must not branch on {forbidden}'

    def test_obligation_3_only_diff_derived_evidence_discharges(self, plan_context):
        """A body-derived signal carries no admissible evidence kind, so it cannot discharge.

        This is enforced structurally rather than asserted in prose: the admissible
        vocabulary is CLOSED to publish shapes, and the PR description is not a
        publish shape. Anything a reviewer could have produced by reading the
        description alone therefore has no evidence kind to present.
        """
        for body_derived in (
            'coderabbit:pr_body',
            'coderabbit:intent_section',
            'coderabbit:pr_description',
            'coderabbit:summary',
        ):
            assert rc.parse_participation(body_derived) == {}, body_derived

        plan_id = 'rc-d8-body-derived'
        plan_context.plan_dir_for(plan_id)
        result = rc.check_completeness(
            plan_id,
            ['coderabbit'],
            participated_bots=rc.parse_participation('coderabbit:pr_body'),
        )

        assert result['participation_complete'] is False
        assert _state_of(result, 'coderabbit') == rc.STATE_ABSENT

    def test_obligation_3_diff_derived_shapes_do_discharge(self, plan_context):
        """The complement: the diff-derived publish shapes DO prove participation.

        Pairs with the test above so the assertion isolates diff-derived-ness as
        the discriminator, rather than passing because everything is rejected.
        """
        plan_id = 'rc-d8-diff-derived'
        plan_context.plan_dir_for(plan_id)
        _seed(plan_id, 'coderabbit', resolution='fixed')

        result = rc.check_completeness(
            plan_id,
            ['coderabbit'],
            participated_bots=rc.parse_participation('coderabbit:inline'),
        )

        assert result['participation_complete'] is True
        assert _state_of(result, 'coderabbit') == rc.STATE_PARTICIPATED


# =============================================================================
# CLI surface
# =============================================================================


class TestCLI:
    """The check verb's argparse surface and emitted TOON block."""

    def test_emits_toon_and_zero_exit(self, plan_context):
        plan_id = 'rc-cli'
        plan_context.plan_dir_for(plan_id)
        _seed(plan_id, 'coderabbit', resolution='pending')

        result = run_script(
            SCRIPT_PATH,
            'check',
            '--plan-id',
            plan_id,
            '--required-bots',
            'coderabbit,sourcery',
            '--participated-bots',
            'coderabbit:inline',
        )

        assert result.success, result.stderr
        assert 'status: success' in result.stdout
        assert 'participation_complete: false' in result.stdout
        assert 'proves: participation_only' in result.stdout
        assert 'pending_bots[1]' in result.stdout
        assert 'unproven_bots[1]' in result.stdout
        assert 'sourcery' in result.stdout

    def test_emits_bot_states_rows(self, plan_context):
        plan_id = 'rc-cli-states'
        plan_context.plan_dir_for(plan_id)

        result = run_script(
            SCRIPT_PATH,
            'check',
            '--plan-id',
            plan_id,
            '--required-bots',
            'coderabbit,sourcery',
            '--participated-bots',
            'coderabbit:inline',
            '--refused-bots',
            'sourcery',
        )

        assert result.success, result.stderr
        assert 'bot_states[2]{bot_kind,state}:' in result.stdout
        assert 'coderabbit,participated_but_empty' in result.stdout
        assert 'sourcery,refused_hard' in result.stdout

    def test_participated_bots_flag_proves_participation(self, plan_context):
        """Without evidence the required bots are absent; with it they are proven."""
        plan_id = 'rc-cli-participated'
        plan_context.plan_dir_for(plan_id)

        without = run_script(
            SCRIPT_PATH, 'check', '--plan-id', plan_id, '--required-bots', 'coderabbit,sourcery'
        )
        assert without.success, without.stderr
        assert 'participation_complete: false' in without.stdout
        assert 'unproven_bots[2]' in without.stdout

        with_evidence = run_script(
            SCRIPT_PATH,
            'check',
            '--plan-id',
            plan_id,
            '--required-bots',
            'coderabbit,sourcery',
            '--participated-bots',
            'coderabbit:inline,sourcery:review_body',
        )
        assert with_evidence.success, with_evidence.stderr
        assert 'participation_complete: true' in with_evidence.stdout
        assert 'unproven_bots' not in with_evidence.stdout

    # -----------------------------------------------------------------------
    # --not-triggered: a BOOLEAN flag, hand-covered by necessity
    # -----------------------------------------------------------------------
    #
    # These four cases are written out rather than swept, and that is the point.
    # ``_bot_flag_derivation.derive_bot_flags`` builds its population from the live
    # parser with the regex ``--[a-z][a-z-]*-bots``, so every flag in the
    # ``--*-bots`` FAMILY inherits the bare-form / advertised-form sweeps
    # automatically — ``--stale-participation-bots`` did, gaining its coverage with
    # no edit to any suite. ``--not-triggered`` is a ``store_true`` bool and matches
    # that regex nowhere, so it inherits NOTHING and would ship entirely untested
    # while every derived sweep still reported clean. The flag is a bool because the
    # observable is PR-wide, so this gap is structural rather than incidental: any
    # future PR-wide boolean needs its own hand-written cases too.

    def test_not_triggered_flag_is_accepted_and_drives_the_verdict(self, plan_context):
        """The flag parses through the REAL CLI and changes the reported state.

        Driven through the constructed-argv subprocess runner rather than an
        in-process call, because the parser is the part no derived sweep covers for
        this flag: an in-process ``check_completeness`` call would pass even if the
        argparse declaration were missing entirely.
        """
        plan_id = 'rc-cli-not-triggered'
        plan_context.plan_dir_for(plan_id)

        result = run_script(
            SCRIPT_PATH,
            'check',
            '--plan-id',
            plan_id,
            '--required-bots',
            'coderabbit',
            '--not-triggered',
        )

        assert result.success, result.stderr
        assert result.returncode != 2, result.stderr
        assert 'participation_complete: false' in result.stdout
        assert 'coderabbit,not_triggered' in result.stdout

    def test_omitting_not_triggered_reports_absent_instead(self, plan_context):
        """The paired control through the same CLI: omitted flag keeps ``absent``.

        Isolates the flag as the only difference between the two invocations, so the
        state change cannot be attributed to anything else in the command line.
        """
        plan_id = 'rc-cli-not-triggered-omitted'
        plan_context.plan_dir_for(plan_id)

        result = run_script(
            SCRIPT_PATH, 'check', '--plan-id', plan_id, '--required-bots', 'coderabbit'
        )

        assert result.success, result.stderr
        assert 'coderabbit,absent' in result.stdout
        assert 'not_triggered' not in result.stdout

    def test_not_triggered_takes_no_value(self, plan_context):
        """It is ``store_true``: a value after it is not consumed as its own.

        Pins the shape deliberately. Its list-flag siblings all declare
        ``nargs='?'``, so a reader (or a caller copying a sibling's call shape) could
        reasonably expect a value here; asserting the bool shape stops a value from
        being silently swallowed.
        """
        plan_id = 'rc-cli-not-triggered-novalue'
        plan_context.plan_dir_for(plan_id)

        result = run_script(
            SCRIPT_PATH,
            'check',
            '--plan-id',
            plan_id,
            '--required-bots',
            'coderabbit',
            '--not-triggered',
            '--optional-bots',
            'sourcery',
        )

        assert result.success, result.stderr
        # The sibling flag after it parsed its own value normally.
        assert 'coderabbit,not_triggered' in result.stdout
        assert 'sourcery,not_triggered' in result.stdout

    def test_not_triggered_is_advertised_on_the_usage_line(self):
        """The bool is advertised in the module docstring's ``Usage:`` line.

        The advertised-form agreement tests in
        ``test_bot_participation_contract.py`` are parametrized over the derived
        ``--*-bots`` family and therefore never see this flag. Without this case the
        docs could omit it indefinitely while every derived advertised-form
        assertion stayed green.
        """
        docstring = rc.__doc__ or ''

        assert '--not-triggered' in docstring

    def test_unqualified_participated_bot_is_rejected_via_cli(self, plan_context):
        """A bare bot_kind on the CLI is a VISIBLE caller error, not an absent verdict.

        The D1 disposition through the real parser: a bare kind fed to the pair-form
        ``--participated-bots`` exits non-zero with ``status: error`` and NO
        ``participation_complete`` field (read as an UNKNOWN verdict), instead of the
        pre-fix silent ``coderabbit,absent`` verdict that manufactured a false merge
        block over a bot the caller meant to record as a participant.
        """
        plan_id = 'rc-cli-bare'
        plan_context.plan_dir_for(plan_id)

        result = run_script(
            SCRIPT_PATH,
            'check',
            '--plan-id',
            plan_id,
            '--required-bots',
            'coderabbit',
            '--participated-bots',
            'coderabbit',
        )

        assert result.returncode == 1, result.stderr
        assert 'status: error' in result.stdout
        assert 'malformed_bot_flag' in result.stdout
        assert 'participation_complete' not in result.stdout

    def test_optional_bots_flag_does_not_gate(self, plan_context):
        plan_id = 'rc-cli-optional'
        plan_context.plan_dir_for(plan_id)

        result = run_script(
            SCRIPT_PATH,
            'check',
            '--plan-id',
            plan_id,
            '--required-bots',
            '',
            '--optional-bots',
            'sourcery',
        )

        assert result.success, result.stderr
        assert 'participation_complete: true' in result.stdout
        assert 'unproven_bots[1]' in result.stdout

    def test_triage_ran_flips_pending_to_incomplete(self, plan_context):
        plan_id = 'rc-cli-triage-ran'
        plan_context.plan_dir_for(plan_id)
        _seed(plan_id, 'coderabbit', resolution='pending')

        pre = run_script(
            SCRIPT_PATH,
            'check',
            '--plan-id',
            plan_id,
            '--required-bots',
            'coderabbit',
            '--participated-bots',
            'coderabbit:inline',
        )
        assert pre.success, pre.stderr
        assert 'participation_complete: true' in pre.stdout

        post = run_script(
            SCRIPT_PATH,
            'check',
            '--plan-id',
            plan_id,
            '--required-bots',
            'coderabbit',
            '--participated-bots',
            'coderabbit:inline',
            '--triage-ran',
        )
        assert post.success, post.stderr
        assert 'participation_complete: false' in post.stdout
        assert 'pending_bots[1]' in post.stdout

    def test_whitespace_in_bot_tokens_tolerated(self, plan_context):
        plan_id = 'rc-cli-ws'
        plan_context.plan_dir_for(plan_id)
        _seed(plan_id, 'coderabbit', resolution='fixed')

        result = run_script(
            SCRIPT_PATH,
            'check',
            '--plan-id',
            plan_id,
            '--required-bots',
            ' coderabbit , ',
            '--participated-bots',
            ' coderabbit : inline ',
        )

        assert result.success, result.stderr
        assert 'participation_complete: true' in result.stdout


# =============================================================================
# Malformed bot-flag rejection (D1) — a wrong-form token is a loud caller error
# =============================================================================


class TestMalformedBotFlagRejection:
    """A token forwarded to the wrong flag FORM is a loud caller error, both directions.

    D1's ``Done when``, pinned end to end: a pair fed to a bare-form flag, and a bare
    kind fed to a pair-form flag. Each is a VISIBLE caller error — non-zero exit,
    ``status: error``, and NO ``participation_complete`` field, so the caller reads it
    as an UNKNOWN verdict — never the pre-fix silent ``absent`` verdict that
    manufactured a confident false merge block over a misparsed population.
    """

    # --- Unit level: the two parsers reject the wrong form ---

    def test_parse_participation_rejects_a_bare_kind(self, plan_context):
        """The pair-form parser rejects a colonless token."""
        with pytest.raises(rc.MalformedBotFlag):
            rc.parse_participation('coderabbit')

    def test_parse_participation_rejects_an_empty_sided_pair(self, plan_context):
        """An empty bot_kind or evidence_kind is a shape violation."""
        for bad in ('coderabbit:', ':inline'):
            with pytest.raises(rc.MalformedBotFlag):
                rc.parse_participation(bad)

    def test_parse_participation_names_the_flag_in_the_error(self, plan_context):
        """The caller error names WHICH flag was misused, so the fix is obvious."""
        with pytest.raises(rc.MalformedBotFlag, match='--stale-participation-bots'):
            rc.parse_participation('coderabbit', '--stale-participation-bots')

    def test_split_bots_rejects_a_pair(self, plan_context):
        """The bare-form splitter rejects a pair-shaped (colon-bearing) token."""
        with pytest.raises(rc.MalformedBotFlag):
            rc._split_bots('coderabbit:inline', '--refused-bots')

    def test_split_bots_accepts_bare_and_empty(self, plan_context):
        """The bare and empty-list forms are never malformed — only a pair is."""
        assert rc._split_bots('coderabbit,sourcery', '--refused-bots') == ['coderabbit', 'sourcery']
        assert rc._split_bots('', '--refused-bots') == []
        assert rc._split_bots('  ,  ', '--refused-bots') == []

    # --- CLI level: both directions are visible caller errors ---

    def test_bare_kind_to_pair_form_flag_is_a_caller_error(self, plan_context):
        """Direction 1 — a bare kind fed to a pair-form flag exits non-zero, no verdict."""
        plan_id = 'rc-malformed-bare-to-pair'
        plan_context.plan_dir_for(plan_id)

        result = run_script(
            SCRIPT_PATH,
            'check',
            '--plan-id',
            plan_id,
            '--required-bots',
            'coderabbit',
            '--participated-bots',
            'coderabbit',
        )

        assert result.returncode == 1, result.stderr
        assert 'status: error' in result.stdout
        assert 'malformed_bot_flag' in result.stdout
        assert 'participation_complete' not in result.stdout

    def test_pair_to_bare_form_flag_is_a_caller_error(self, plan_context):
        """Direction 2 — a pair fed to a bare-form flag exits non-zero, no verdict.

        ``--refused-bots`` is bare-form; the producer emits ``refused_bots[]`` as bare
        kinds, so a pair here is a caller error, symmetric with direction 1.
        """
        plan_id = 'rc-malformed-pair-to-bare'
        plan_context.plan_dir_for(plan_id)

        result = run_script(
            SCRIPT_PATH,
            'check',
            '--plan-id',
            plan_id,
            '--required-bots',
            'coderabbit',
            '--refused-bots',
            'coderabbit:inline',
        )

        assert result.returncode == 1, result.stderr
        assert 'status: error' in result.stdout
        assert 'malformed_bot_flag' in result.stdout
        assert 'participation_complete' not in result.stdout


# =============================================================================
# --stale-participation-bots is pair-form (D1/D2) — matches the producer's shape
# =============================================================================


class TestStaleParticipationIsPairForm:
    """``--stale-participation-bots`` takes evidence-typed pairs, matching the producer.

    The producer emits ``stale_participation_bots[]`` as ``{bot_kind, evidence_kind}``
    pairs, identical to ``participated_bots[]``. Making the consumer flag pair-form is
    the root fix for "the producer emits pairs for both while the flags require
    different forms": the producer's output forwards to ``--stale-participation-bots``
    verbatim, and the classifier reads only the bot_kind.
    """

    def test_pair_form_stale_classifies_participated_stale(self, plan_context):
        """A pair — the producer's exact shape — classifies the bot participated_stale."""
        plan_id = 'rc-stale-pair'
        plan_context.plan_dir_for(plan_id)

        result = run_script(
            SCRIPT_PATH,
            'check',
            '--plan-id',
            plan_id,
            '--required-bots',
            'pr-agent',
            '--stale-participation-bots',
            'pr-agent:issue_comment',
        )

        assert result.success, result.stderr
        assert 'participation_complete: false' in result.stdout
        assert 'pr-agent,participated_stale' in result.stdout

    def test_bare_kind_to_stale_flag_is_rejected(self, plan_context):
        """A BARE kind on the now-pair-form flag is a caller error — the other D1 half."""
        plan_id = 'rc-stale-bare'
        plan_context.plan_dir_for(plan_id)

        result = run_script(
            SCRIPT_PATH,
            'check',
            '--plan-id',
            plan_id,
            '--required-bots',
            'pr-agent',
            '--stale-participation-bots',
            'pr-agent',
        )

        assert result.returncode == 1, result.stderr
        assert 'malformed_bot_flag' in result.stdout
        assert 'participation_complete' not in result.stdout


# =============================================================================
# Fail-loud store errors
# =============================================================================


class TestLoadFailure:
    """A findings-store failure is rendered as a structured error, never swallowed."""

    def test_oserror_returns_structured_error(self, plan_context, monkeypatch):
        plan_id = 'rc-oserror'
        plan_context.plan_dir_for(plan_id)

        def _raise(*_args, **_kwargs):
            raise OSError('store unreadable')

        monkeypatch.setattr(rc, 'query_findings', _raise)

        result = rc.check_completeness(plan_id, ['coderabbit'])

        assert result['status'] == 'error'
        assert result['error'] == 'load_failure'
        assert 'store unreadable' in result['detail']

    def test_valueerror_returns_structured_error(self, plan_context, monkeypatch):
        plan_id = 'rc-valueerror'
        plan_context.plan_dir_for(plan_id)

        def _raise(*_args, **_kwargs):
            raise ValueError('bad json')

        monkeypatch.setattr(rc, 'query_findings', _raise)

        result = rc.check_completeness(plan_id, ['coderabbit'])

        assert result['status'] == 'error'
        assert result['error'] == 'load_failure'
        assert 'bad json' in result['detail']

    def test_cmd_check_load_failure_nonzero_exit(self, plan_context, monkeypatch, capsys):
        plan_id = 'rc-cmd-load-fail'
        plan_context.plan_dir_for(plan_id)

        def _raise(*_args, **_kwargs):
            raise OSError('store gone')

        monkeypatch.setattr(rc, 'query_findings', _raise)

        rc_exit = rc.main(['check', '--plan-id', plan_id, '--required-bots', 'coderabbit'])

        captured = capsys.readouterr()
        assert rc_exit == 1
        assert 'status: error' in captured.out
        assert 'error: load_failure' in captured.out
        assert 'detail:' in captured.out


# =============================================================================
# Zero participation — every list flag may be supplied BARE
# =============================================================================
#
# The defect this pins: the callers interpolate all five list flags into the
# command line, and every one of them is legitimately empty in normal operation
# (no optional bots, no in-progress bots, no refusals). An unquoted
# ``--refused-bots {refused_bots}`` with an empty value collapses to a BARE
# ``--refused-bots``, which the pre-fix parser rejected with argparse exit 2 —
# and a crashed gate that a caller reads as a pass is a participation verdict
# nobody produced.
#
# Every case below is red against the pre-fix parser by construction: the five
# flags declared ``default=''`` with no ``nargs``, so argparse required a value
# and answered a bare flag with ``expected one argument`` / exit 2. Nothing here
# can pass without the ``nargs='?'`` + ``const=''`` relaxation.

#: The list flags and the ``argparse`` dest each resolves to, derived from the live
#: ``check`` parser so a flag added to the script inherits the bare-form sweeps
#: below instead of silently losing them.
_LIST_FLAGS = derive_bot_flags(SCRIPT_PATH, 'check')


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


class TestBareListFlags:
    """Every list flag accepts a bare form that reads as the empty list."""

    def test_every_list_flag_bare_is_accepted(self, plan_context):
        """All five bare at once — the exact shape the callers produce when empty.

        Exits 0 with a real verdict instead of the pre-fix argparse rejection. An
        empty ``required_bots`` is the vacuously-satisfied quorum, so the honest
        verdict here is ``true``: there is nothing to await. The point of the case
        is that a verdict is PRODUCED at all — see
        ``test_zero_participation_with_required_bots_blocks`` for the arm where
        zero observations must block.
        """
        plan_id = 'rc-bare-all'
        plan_context.plan_dir_for(plan_id)

        result = run_script(
            SCRIPT_PATH,
            'check',
            '--plan-id',
            plan_id,
            '--required-bots',
            '--optional-bots',
            '--participated-bots',
            '--in-progress-bots',
            '--refused-bots',
        )

        assert result.success, result.stderr
        assert 'expected one argument' not in result.stderr
        assert 'status: success' in result.stdout
        assert 'participation_complete: true' in result.stdout
        assert 'proves: participation_only' in result.stdout

    def test_zero_participation_with_required_bots_blocks(self, plan_context):
        """Zero observations against a real required set is a BLOCK, never a pass.

        The four observation flags are bare — no proven participant, nothing in
        progress, nothing refused — while ``required_bots`` names two bots. The
        relaxation must not buy a pass: the run completes with exit 0 and
        ``participation_complete: false``, naming both required bots unproven.
        """
        plan_id = 'rc-bare-zero-participation'
        plan_context.plan_dir_for(plan_id)

        result = run_script(
            SCRIPT_PATH,
            'check',
            '--plan-id',
            plan_id,
            '--required-bots',
            'coderabbit,pr-agent',
            '--optional-bots',
            '--participated-bots',
            '--in-progress-bots',
            '--refused-bots',
        )

        assert result.success, result.stderr
        assert 'status: success' in result.stdout
        assert 'participation_complete: false' in result.stdout
        assert 'unproven_bots[2]' in result.stdout
        assert 'coderabbit,absent' in result.stdout
        assert 'pr-agent,absent' in result.stdout

    @pytest.mark.parametrize(('flag', 'dest'), _LIST_FLAGS)
    def test_each_flag_bare_followed_by_another_flag(self, monkeypatch, flag, dest):
        """A bare flag does not swallow the NEXT flag as its value.

        The interpolation collapse rarely leaves the bare flag last on the line —
        it is normally followed by the next ``--flag``. ``argparse`` treats a
        ``-``-prefixed token as an option rather than an optional value, so the
        bare flag still takes ``const=''`` and the following flag parses normally.
        """
        args = _parsed_check_args(
            monkeypatch,
            ['check', '--plan-id', 'rc-bare-then-flag', flag, '--triage-ran'],
        )

        assert getattr(args, dest) == ''
        assert args.triage_ran is True

    @pytest.mark.parametrize(('flag', 'dest'), _LIST_FLAGS)
    def test_each_flag_value_form_is_unchanged(self, monkeypatch, flag, dest):
        """The existing ``--flag value`` form parses exactly as before.

        Pairs with the bare-form cases so the relaxation is shown to ADD a form
        rather than replace one.
        """
        args = _parsed_check_args(
            monkeypatch, ['check', '--plan-id', 'rc-value-form', flag, 'coderabbit']
        )

        assert getattr(args, dest) == 'coderabbit'

    @pytest.mark.parametrize(('flag', 'dest'), _LIST_FLAGS)
    def test_bare_omitted_and_explicit_empty_agree(self, monkeypatch, flag, dest):
        """Bare, omitted, and explicitly-empty are the same parse: ``''``.

        This three-way agreement is what makes the bare form safe to reach by
        accident — a caller whose interpolation collapsed gets the reading it
        would have got had it quoted the placeholder or omitted the flag.
        """
        bare = _parsed_check_args(monkeypatch, ['check', '--plan-id', 'rc-agree', flag])
        omitted = _parsed_check_args(monkeypatch, ['check', '--plan-id', 'rc-agree'])
        explicit = _parsed_check_args(monkeypatch, ['check', '--plan-id', 'rc-agree', flag, ''])

        assert getattr(bare, dest) == getattr(omitted, dest) == getattr(explicit, dest) == ''

    def test_bare_flag_still_swallows_a_following_plain_value(self, monkeypatch):
        """WHY quoting is still mandatory: a bare flag DOES take a following plain token.

        ``nargs='?'`` is a parser-side backstop, not a substitute for quoting the
        interpolated placeholder. When the collapsed flag is followed by a plain
        (non ``-``-prefixed) token, argparse hands that token to the bare flag —
        so an unquoted empty ``--optional-bots`` silently steals the NEXT flag's
        value and the value-bearing flag is left empty. The docs state the two
        defences are complementary; this is the case that makes that concrete.
        """
        args = _parsed_check_args(
            monkeypatch,
            [
                'check',
                '--plan-id',
                'rc-swallow',
                '--optional-bots',
                # `--required-bots "coderabbit"` with the value collapsed away in
                # front of it: the bare --optional-bots eats 'coderabbit'.
                'coderabbit',
            ],
        )

        assert args.optional_bots == 'coderabbit'
        assert args.required_bots == ''


# =============================================================================
# UNKNOWN verdict — a crashed predicate emits NO verdict to misread
# =============================================================================


class TestUnknownVerdictEmitsNoParticipationField:
    """A non-zero exit never carries a ``participation_complete`` a caller could read.

    The callers treat "non-zero exit, or a return with no ``participation_complete``
    field" as an UNKNOWN verdict — explicitly not ``false`` and emphatically not
    ``true``. That routing is only sound if a crashed run cannot emit a verdict
    field at all, which is what these cases pin.
    """

    def test_argparse_rejection_emits_no_verdict(self, plan_context):
        """An unrecognised flag exits 2 with no verdict on stdout."""
        plan_id = 'rc-unknown-argparse'
        plan_context.plan_dir_for(plan_id)

        result = run_script(
            SCRIPT_PATH, 'check', '--plan-id', plan_id, '--not-a-real-flag', 'x'
        )

        assert result.returncode == 2
        assert 'participation_complete' not in result.stdout

    def test_load_failure_emits_no_verdict(self, plan_context, monkeypatch, capsys):
        """The store-failure error branch exits 1 and emits no verdict field.

        ``_emit_toon`` returns immediately on the error branch, so ``status:
        error`` is the whole payload — there is no ``participation_complete`` line
        for a caller to mistake for a verdict.
        """
        plan_id = 'rc-unknown-load-failure'
        plan_context.plan_dir_for(plan_id)

        def _raise(*_args, **_kwargs):
            raise OSError('store gone')

        monkeypatch.setattr(rc, 'query_findings', _raise)

        rc_exit = rc.main(['check', '--plan-id', plan_id, '--required-bots', 'coderabbit'])

        captured = capsys.readouterr()
        assert rc_exit == 1
        assert 'participation_complete' not in captured.out


# =============================================================================
# D3 — the reviewer-state distribution reaches the display field
# =============================================================================


class TestReviewStateSummary:
    """``compose_review_state_summary`` distinguishes reviewed-clean from nobody-reviewed.

    ``"0 comment(s) found"`` is the identical display string for a clean 27-file
    review and for a run where no reviewer produced any content. The summary is what
    a reader appends to tell those two facts apart — the whole point of D3.
    """

    def test_nobody_reviewed_and_reviewed_clean_render_differently(self):
        """The load-bearing distinction: three refusals is NOT three clean reviews."""
        nobody = rc.compose_review_state_summary([
            {'bot_kind': 'coderabbit', 'state': rc.STATE_REFUSED_AWAITABLE},
            {'bot_kind': 'sourcery', 'state': rc.STATE_REFUSED_HARD},
            {'bot_kind': 'pr-agent', 'state': rc.STATE_REFUSED_UNKNOWN},
        ])
        reviewed_clean = rc.compose_review_state_summary([
            {'bot_kind': 'coderabbit', 'state': rc.STATE_PARTICIPATED_BUT_EMPTY},
            {'bot_kind': 'sourcery', 'state': rc.STATE_PARTICIPATED_BUT_EMPTY},
            {'bot_kind': 'pr-agent', 'state': rc.STATE_PARTICIPATED_BUT_EMPTY},
        ])
        assert nobody == '3 refused'
        assert reviewed_clean == '3 empty'
        # The two facts MUST NOT share a rendering — this is the whole deliverable.
        assert nobody != reviewed_clean

    def test_all_three_refusal_members_share_the_refused_bucket(self):
        summary = rc.compose_review_state_summary([
            {'bot_kind': 'a', 'state': rc.STATE_REFUSED_AWAITABLE},
            {'bot_kind': 'b', 'state': rc.STATE_REFUSED_HARD},
            {'bot_kind': 'c', 'state': rc.STATE_REFUSED_UNKNOWN},
        ])
        assert summary == '3 refused'

    def test_mixed_distribution_lists_each_nonzero_bucket_in_order(self):
        summary = rc.compose_review_state_summary([
            {'bot_kind': 'a', 'state': rc.STATE_PARTICIPATED},
            {'bot_kind': 'b', 'state': rc.STATE_PARTICIPATED_BUT_EMPTY},
            {'bot_kind': 'c', 'state': rc.STATE_REFUSED_HARD},
        ])
        assert summary == '1 reviewed, 1 empty, 1 refused'

    def test_empty_roster_produces_no_summary(self):
        """An empty roster has nothing to distribute — the honest value is ''."""
        assert rc.compose_review_state_summary([]) == ''

    def test_check_output_carries_the_summary(self, plan_context):
        """The field reaches the check envelope so ``display_detail`` can interpolate it."""
        plan_id = 'rc-summary-in-output'
        plan_context.plan_dir_for(plan_id)
        result = rc.check_completeness(
            plan_id, ['coderabbit', 'sourcery', 'pr-agent'],
            refused_bots=['coderabbit', 'sourcery', 'pr-agent'],
        )
        assert result['review_state_summary'] == '3 refused'

    def test_check_output_summary_empty_for_empty_roster(self, plan_context):
        plan_id = 'rc-summary-empty-roster'
        plan_context.plan_dir_for(plan_id)
        result = rc.check_completeness(plan_id, [])
        assert result['review_state_summary'] == ''


# =============================================================================
# D2/D4 — the comparative deficit signal, fired only against a real baseline
# =============================================================================


class TestDeficitSignal:
    """The comparative deficit signal — a reviewer-quality bug, never a merge verdict.

    The five corpus rows share ``required_count == 0``, yet their verdicts differ:
    deficit / deficit / unassessable / unassessable / clean. The required count alone
    cannot tell them apart; the baseline — whether any OTHER reviewer reviewed the
    same diff, and how much — is what makes the deficit assessable. Cases (b) and (c)
    are load-bearing: a detector that fires on them manufactures reviewer-quality
    bugs out of the rate limiting we already accept as normal.
    """

    def _required(self, count, reviewed=True):
        return {'bot_kind': 'pr-agent', 'reviewed': reviewed, 'finding_count': count}

    def _baseline(self, count, reviewed=True, bot='coderabbit'):
        return {'bot_kind': bot, 'reviewed': reviewed, 'finding_count': count}

    def test_row_a_deficit_four_to_zero(self):
        # Row A: a baseline reviewer produced 4 findings; the required reviewer
        # reviewed and produced 0. 4 : 0 is a deficit.
        result = rc.assess_deficit(
            [self._required(0), self._baseline(4)], required_bots=['pr-agent']
        )
        assert result['verdict'] == rc.DEFICIT_DEFICIT
        assert result['deficit_reviewers'] == [{'bot_kind': 'pr-agent', 'findings': 0, 'deficit': 4}]
        assert result['baseline_max'] == 4

    def test_row_b_deficit_two_to_zero(self):
        result = rc.assess_deficit(
            [self._required(0), self._baseline(2)], required_bots=['pr-agent']
        )
        assert result['verdict'] == rc.DEFICIT_DEFICIT

    def test_row_e_clean_zero_to_zero_with_a_real_baseline(self):
        # Row E — the necessary counter-example. A baseline reviewer REVIEWED and
        # found nothing; the required reviewer found nothing. 0 : 0 against a real
        # baseline is CLEAN, never a deficit. The detector MUST NOT fire here.
        result = rc.assess_deficit(
            [self._required(0), self._baseline(0)], required_bots=['pr-agent']
        )
        assert result['verdict'] == rc.DEFICIT_CLEAN
        assert result['deficit_reviewers'] == []

    def test_rows_c_and_d_unassessable_when_every_baseline_refused(self):
        # Rows C and D — no baseline. Every other reviewer refused, so nothing
        # reviewed the diff besides the required bot; the run is evidence NEITHER
        # way. unassessable, NOT clean and NOT a deficit.
        result = rc.assess_deficit(
            [
                self._required(0, reviewed=False),
                self._baseline(0, reviewed=False, bot='coderabbit'),
                self._baseline(0, reviewed=False, bot='sourcery'),
            ],
            required_bots=['pr-agent'],
        )
        assert result['verdict'] == rc.DEFICIT_UNASSESSABLE
        assert result['verdict'] != rc.DEFICIT_CLEAN
        assert result['deficit_reviewers'] == []
        assert result['baseline_reviewers'] == []

    def test_required_count_alone_cannot_distinguish_the_rows(self):
        """``required_count == 0`` across all rows, yet the verdict differs.

        The sharp point of the plan: a detector keyed on the required reviewer's count
        alone would label all rows identically. Only the baseline separates deficit
        from clean from unassessable.
        """
        def verdict(baseline):
            return rc.assess_deficit(
                [{'bot_kind': 'pr-agent', 'reviewed': True, 'finding_count': 0}, *baseline],
                required_bots=['pr-agent'],
            )['verdict']

        # required_count is 0 in every call below; only the baseline varies.
        assert verdict([self._baseline(4)]) == rc.DEFICIT_DEFICIT
        assert verdict([self._baseline(0)]) == rc.DEFICIT_CLEAN
        assert verdict([self._baseline(0, reviewed=False)]) == rc.DEFICIT_UNASSESSABLE

    def test_min_deficit_threshold_is_honoured(self):
        # A 1-finding gap is a deficit at the default threshold; raising the
        # threshold above the gap makes the same shape clean.
        rows = [self._required(1), self._baseline(2)]
        assert rc.assess_deficit(rows, ['pr-agent'])['verdict'] == rc.DEFICIT_DEFICIT
        assert rc.assess_deficit(rows, ['pr-agent'], min_deficit=2)['verdict'] == rc.DEFICIT_CLEAN

    def test_signal_never_gates_the_merge(self):
        """Every deficit envelope declares itself non-gating — the cold-read requirement."""
        result = rc.assess_deficit(
            [self._required(0), self._baseline(4)], required_bots=['pr-agent']
        )
        assert result['gates_merge'] is False
        assert result['proves'] == 'reviewer_quality_only'

    def test_check_deficit_reads_finding_counts_from_the_store(self, plan_context):
        """Integration: ``check_deficit`` derives counts from the pr-comment store.

        Seed a reviewing baseline with four findings and a required reviewer proven to
        have participated-but-empty; the deficit is read off the store, not passed in.
        """
        plan_id = 'rc-deficit-integration'
        plan_context.plan_dir_for(plan_id)
        for _ in range(4):
            _seed(plan_id, 'coderabbit', resolution='fixed')

        result = rc.check_deficit(
            plan_id,
            ['pr-agent'],
            optional_bots=['coderabbit'],
            participated_bots=rc.parse_participation('pr-agent:issue_comment,coderabbit:inline'),
        )

        assert result['verdict'] == rc.DEFICIT_DEFICIT
        assert result['baseline_max'] == 4
        assert {'bot_kind': 'pr-agent', 'findings': 0, 'deficit': 4} in result['deficit_reviewers']

    def test_deficit_cli_declares_non_gating(self, plan_context):
        """The CLI TOON carries ``gates_merge: false`` so a cold read sees it is no gate."""
        plan_id = 'rc-deficit-cli'
        plan_context.plan_dir_for(plan_id)
        result = run_script(
            SCRIPT_PATH, 'deficit', '--plan-id', plan_id,
            '--required-bots', 'pr-agent',
            '--optional-bots', 'coderabbit,sourcery',
            '--refused-bots', 'coderabbit,sourcery',
        )
        assert result.returncode == 0
        assert 'gates_merge: false' in result.stdout
        # Both baseline candidates refused → no baseline → unassessable, never clean.
        assert 'verdict: unassessable' in result.stdout


# =============================================================================
# The refusal CAUSE overlay (size vs quota) — orthogonal to awaitability, advisory
# =============================================================================


class TestRefusalCauseOverlay:
    """The size/quota CAUSE axis rides alongside the awaitability member — never changes it.

    ``refusal_cause`` (in the producer) names the REMEDY a refusal calls for: ``size``
    means the diff is over a per-PR ceiling (a smaller diff), ``quota`` means a
    rate/budget limit (backoff). It is forwarded to ``--refused-causes`` and reported in
    ``refusal_causes[]``. It is advisory: it gates nothing and moves no awaitability
    member (``refused_awaitable`` / ``refused_hard`` / ``refused_unknown``).
    """

    def test_parse_causes_maps_pairs(self):
        assert rc.parse_causes('sourcery:size,coderabbit:quota') == {
            'sourcery': 'size',
            'coderabbit': 'quota',
        }

    def test_parse_causes_empty_forms_are_the_empty_map(self):
        assert rc.parse_causes('') == {}
        assert rc.parse_causes(None) == {}
        assert rc.parse_causes('  ,  ') == {}

    def test_parse_causes_rejects_a_shape_violation(self):
        # A bare bot_kind (no colon) or an empty side is a SHAPE violation — rejected
        # loudly like the other pair-form flags, never silently dropped.
        with pytest.raises(rc.MalformedBotFlag):
            rc.parse_causes('sourcery')
        with pytest.raises(rc.MalformedBotFlag):
            rc.parse_causes('sourcery:')
        with pytest.raises(rc.MalformedBotFlag):
            rc.parse_causes(':size')

    def test_cause_is_reported_only_for_a_refused_bot(self, plan_context):
        plan_id = 'rc-cause-refused'
        plan_context.plan_dir_for(plan_id)
        result = rc.check_completeness(
            plan_id, ['sourcery'], refused_bots=['sourcery'],
            refused_causes={'sourcery': 'size'},
        )
        # The awaitability member is unchanged — the cause is an overlay, not a member.
        assert _state_of(result, 'sourcery') == rc.STATE_REFUSED_HARD
        assert result['refusal_causes'] == [{'bot_kind': 'sourcery', 'cause': 'size'}]

    def test_cause_for_a_non_refused_bot_is_dropped(self, plan_context):
        # A cause supplied for a bot that did NOT resolve to a refusal state is not
        # reported — the overlay only annotates bots actually classified refused.
        plan_id = 'rc-cause-nonrefused'
        plan_context.plan_dir_for(plan_id)
        _seed(plan_id, 'coderabbit', resolution='fixed')
        result = rc.check_completeness(
            plan_id, ['coderabbit'],
            participated_bots=CODERABBIT_EVIDENCE,
            refused_causes={'coderabbit': 'size'},
        )
        assert _state_of(result, 'coderabbit') == rc.STATE_PARTICIPATED
        assert result['refusal_causes'] == []

    def test_cause_never_changes_the_awaitability_member(self, plan_context):
        # coderabbit's rate_limit_class is awaitable_window → refused_awaitable, whatever
        # cause is supplied. The two axes are independent.
        plan_id = 'rc-cause-advisory'
        plan_context.plan_dir_for(plan_id)
        result = rc.check_completeness(
            plan_id, ['coderabbit'], refused_bots=['coderabbit'],
            refused_causes={'coderabbit': 'quota'},
        )
        assert _state_of(result, 'coderabbit') == rc.STATE_REFUSED_AWAITABLE
        assert result['refusal_causes'] == [{'bot_kind': 'coderabbit', 'cause': 'quota'}]

    def test_no_causes_emits_no_refusal_causes(self, plan_context):
        plan_id = 'rc-cause-none'
        plan_context.plan_dir_for(plan_id)
        result = rc.check_completeness(plan_id, ['sourcery'], refused_bots=['sourcery'])
        assert result['refusal_causes'] == []

    def test_cli_emits_the_refusal_causes_block(self, plan_context):
        plan_id = 'rc-cause-cli'
        plan_context.plan_dir_for(plan_id)
        result = run_script(
            SCRIPT_PATH, 'check', '--plan-id', plan_id,
            '--required-bots', 'sourcery', '--refused-bots', 'sourcery',
            '--refused-causes', 'sourcery:size',
        )
        assert result.returncode == 0
        assert 'refusal_causes[1]{bot_kind,cause}:' in result.stdout
        assert 'sourcery,size' in result.stdout

    def test_cli_malformed_cause_is_an_unknown_verdict(self, plan_context):
        # A bare token on the pair-form --refused-causes is a caller error → status:
        # error, non-zero exit, and NO participation_complete field (UNKNOWN verdict).
        plan_id = 'rc-cause-malformed'
        plan_context.plan_dir_for(plan_id)
        result = run_script(
            SCRIPT_PATH, 'check', '--plan-id', plan_id,
            '--required-bots', 'sourcery', '--refused-causes', 'sourcery',
        )
        assert result.returncode == 1
        assert 'participation_complete' not in result.stdout

    def test_refused_causes_flag_reads_bare_as_empty(self, plan_context):
        plan_id = 'rc-cause-bare'
        plan_context.plan_dir_for(plan_id)
        result = run_script(
            SCRIPT_PATH, 'check', '--plan-id', plan_id,
            '--required-bots', 'sourcery', '--refused-bots', 'sourcery',
            '--refused-causes',
        )
        assert result.returncode == 0
        assert 'refusal_causes' not in result.stdout

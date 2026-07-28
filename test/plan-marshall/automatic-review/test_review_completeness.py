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

from conftest import get_script_path, run_script

SCRIPT_PATH = get_script_path('plan-marshall', 'automatic-review', 'review_completeness.py')
SCRIPTS_DIR = SCRIPT_PATH.parent

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import review_completeness as rc  # noqa: E402
import _findings_core as fc  # noqa: E402

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
        """A bare ``bot_kind`` with no evidence kind proves nothing.

        This is the contract that changed: the mere existence of a comment
        resolving to a bot's login used to credit it. Presence is not evidence.
        """
        assert rc.parse_participation('coderabbit') == {}
        assert rc.parse_participation('coderabbit,sourcery') == {}

    def test_unknown_bot_can_never_be_proven(self, plan_context):
        """A bot with no registry record declares no evidence → fail-closed."""
        assert rc.parse_participation('mystery-bot:inline') == {}

    def test_admissible_and_inadmissible_pairs_are_separated(self, plan_context):
        """A mixed list admits only the pairs that match their own bot's shapes."""
        assert rc.parse_participation('coderabbit:inline,pr-agent:inline') == CODERABBIT_EVIDENCE

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
# PR-Agent — the narrowest publish shape in the registry
# =============================================================================


class TestPRAgentParticipation:
    """PR-Agent is proven by its Guide comment plus movement — never by count or check state."""

    def test_guide_comment_is_its_evidence(self, plan_context):
        """Its single persistent `issue_comment` IS its review artifact."""
        plan_id = 'rc-pr-agent-guide'
        plan_context.plan_dir_for(plan_id)

        result = rc.check_completeness(
            plan_id, ['pr-agent'], participated_bots=PR_AGENT_EVIDENCE
        )

        assert result['participation_complete'] is True
        assert _state_of(result, 'pr-agent') == rc.STATE_PARTICIPATED_BUT_EMPTY

    def test_inline_comment_count_is_not_its_evidence(self, plan_context):
        """It publishes NO inline comments, so an inline count cannot prove it.

        Reading inline count as participation is the false-negative direction: it
        would score PR-Agent absent on every run no matter how well it reviewed.
        The predicate refuses the inline pair outright rather than encoding a count.
        """
        plan_id = 'rc-pr-agent-inline'
        plan_context.plan_dir_for(plan_id)
        # Findings exist in the store for this bot — a "count" would look healthy.
        _seed(plan_id, 'pr-agent', resolution='fixed')

        result = rc.check_completeness(
            plan_id, ['pr-agent'], participated_bots=rc.parse_participation('pr-agent:inline')
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

    def test_refusal_of_unknown_class_is_hard_not_awaitable(self, plan_context):
        """Fail-closed: an unknown rate-limit class is never treated as awaitable.

        Awaiting a quota that never reopens is the expensive failure, so the
        unknown class resolves to the non-awaiting member.
        """
        plan_id = 'rc-state-refused-unknown'
        plan_context.plan_dir_for(plan_id)

        result = rc.check_completeness(plan_id, ['pr-agent'], refused_bots=['pr-agent'])

        assert rc.bot_registry.rate_limit_class('pr-agent') == 'unknown'
        assert _state_of(result, 'pr-agent') == rc.STATE_REFUSED_HARD

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
            rc.STATE_PARTICIPATED_BUT_EMPTY,
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

    def test_unqualified_participated_bot_is_rejected_via_cli(self, plan_context):
        """A bare bot_kind on the CLI does not prove participation either."""
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

        assert result.success, result.stderr
        assert 'participation_complete: false' in result.stdout
        assert 'coderabbit,absent' in result.stdout

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

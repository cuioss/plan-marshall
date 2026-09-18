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


class TestCodeRabbitCleanReviewCredit:
    """A credited CodeRabbit clean review resolves ``participated_but_empty``.

    Every comment of a clean review is dropped as noise, so the store holds nothing for
    the bot while the producer still credits it — participation is derived before the
    noise filter runs. *Credited, zero findings* must land on the existing
    ``participated_but_empty`` member: never ``absent`` (which escalates a reviewer that
    did review) and never ``participated`` (which claims findings that do not exist).
    See ``bot-participation-contract.md`` § "A credited clean review resolves
    ``participated_but_empty``".
    """

    def test_the_clean_review_shape_is_coderabbits_marker_gated_evidence(self):
        """The credit rides the one shape CodeRabbit gates on its review-verdict marker.

        Guards the premise of the cases below: were the shape undeclared or ungated,
        the pair they feed would no longer stand for the marker-bearing verdict the
        producer credits on a clean review.
        """
        assert _CODERABBIT_CLEAN_REVIEW_SHAPE in rc.bot_registry.participation_evidence('coderabbit')
        assert rc.bot_registry.participation_evidence_marker('coderabbit', _CODERABBIT_CLEAN_REVIEW_SHAPE)

    def test_a_credited_clean_review_resolves_participated_but_empty_and_renders_empty(self, plan_context):
        """The clean review is an accounted-for success, shown as ``empty`` on the summary line."""
        plan_id = 'rc-coderabbit-clean-review'
        plan_context.plan_dir_for(plan_id)

        result = rc.check_completeness(
            plan_id,
            ['coderabbit'],
            participated_bots=rc.parse_participation(f'coderabbit:{_CODERABBIT_CLEAN_REVIEW_SHAPE}'),
        )

        assert _state_of(result, 'coderabbit') == rc.STATE_PARTICIPATED_BUT_EMPTY
        assert result['review_state_summary'] == '1 empty'
        assert result['participation_complete'] is True
        assert result['unproven_bots'] == []

    def test_the_same_observations_with_a_surviving_finding_resolve_participated(self, plan_context):
        """⛔ MATCHED CONTROL: one surviving finding is the only difference, and it moves the member.

        Same bot, same credited shape, same quorum — the store now holds one finding
        the noise filter let through. The member moves to ``participated`` and the
        summary to ``reviewed``, so the case above cannot pass by resolving every
        credited bot ``participated_but_empty`` regardless of what it filed.
        """
        plan_id = 'rc-coderabbit-clean-review-finding'
        plan_context.plan_dir_for(plan_id)
        _seed(plan_id, 'coderabbit')

        result = rc.check_completeness(
            plan_id,
            ['coderabbit'],
            participated_bots=rc.parse_participation(f'coderabbit:{_CODERABBIT_CLEAN_REVIEW_SHAPE}'),
        )

        assert _state_of(result, 'coderabbit') == rc.STATE_PARTICIPATED
        assert result['review_state_summary'] == '1 reviewed'
        assert result['participation_complete'] is True

    def test_the_same_empty_store_without_the_credit_is_absent(self, plan_context):
        """The credit alone separates a clean review from no review at all.

        The store is as empty as a clean review leaves it; only the credit is missing —
        which is what a verdict comment lacking its marker produces. The bot resolves
        ``absent`` and holds the quorum open, so the credit is load-bearing rather than
        incidental to the ``participated_but_empty`` verdict above.
        """
        plan_id = 'rc-coderabbit-clean-review-uncredited'
        plan_context.plan_dir_for(plan_id)

        result = rc.check_completeness(plan_id, ['coderabbit'])

        assert _state_of(result, 'coderabbit') == rc.STATE_ABSENT
        assert result['review_state_summary'] == '1 absent'
        assert result['participation_complete'] is False


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

        result = rc.check_completeness(plan_id, ['coderabbit', 'sourcery'], participated_bots=CODERABBIT_EVIDENCE)

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


class TestStateTaxonomy:
    """Each bot resolves to exactly one state; refusals split by registry class."""

    def test_proven_participant_with_findings_is_participated(self, plan_context):
        plan_id = 'rc-state-participated'
        plan_context.plan_dir_for(plan_id)
        _seed(plan_id, 'coderabbit', resolution='fixed')

        result = rc.check_completeness(plan_id, ['coderabbit'], participated_bots=CODERABBIT_EVIDENCE)

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

        result = rc.check_completeness(plan_id, ['coderabbit'], participated_bots=CODERABBIT_EVIDENCE)

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

        result = rc.check_completeness(plan_id, ['coderabbit', 'sourcery'], refused_bots=['coderabbit', 'sourcery'])

        assert _state_of(result, 'coderabbit') == rc.STATE_REFUSED_AWAITABLE
        assert _state_of(result, 'sourcery') == rc.STATE_REFUSED_HARD
        assert result['participation_complete'] is False
        assert result['unproven_bots'] == ['coderabbit', 'sourcery']

    def test_refusal_of_unknown_class_is_its_own_state_not_hard(self, plan_context):
        """An ``unknown`` rate-limit class resolves to ``refused_unknown``, never ``refused_hard``.

        With NEITHER override in play (no ``size`` cause and a refusal the stack could
        read), the three-valued ``rate_limit_class`` supplies the DEFAULT member:
        ``awaitable_window`` -> ``refused_awaitable``, ``hard_quota`` ->
        ``refused_hard``, ``unknown`` -> ``refused_unknown``. The overrides that
        displace that default are covered in ``test_structural_refusal.py`` (the
        ``size`` cause) and in ``TestUnrecognisedRefusalOverride`` below.

        Keeping ``refused_unknown`` its own member is load-bearing: folding it into
        ``refused_hard`` would render a declared *we-do-not-know* as a positive
        *hard quota*, steering an operator toward "waiting is futile, force it" when
        the refusal shape had simply never been observed. It is still an UNPROVEN,
        blocking state — a refusal is a refusal — but a DIFFERENT one.

        """
        plan_id = 'rc-state-refused-unknown'
        plan_context.plan_dir_for(plan_id)

        result = rc.check_completeness(plan_id, ['cuioss-review-bot'], refused_bots=['cuioss-review-bot'])

        assert rc.bot_registry.rate_limit_class('cuioss-review-bot') == 'unknown'
        assert _state_of(result, 'cuioss-review-bot') == rc.STATE_REFUSED_UNKNOWN
        assert _state_of(result, 'cuioss-review-bot') != rc.STATE_REFUSED_HARD
        assert rc.STATE_REFUSED_UNKNOWN in rc._UNPROVEN_STATES
        assert result['participation_complete'] is False

    def test_the_default_class_mapping_is_total_and_injective(self, plan_context):
        """``_refusal_state``'s DEFAULT mapping is total and injective over the classes.

        Asserted directly on the mapping so a future fold of any two classes into one
        member breaks here, not only via a downstream verdict. A value that is neither
        of the first two — including a malformed one — fails closed to
        ``refused_unknown`` rather than being asserted as a hard quota.

        This is the mapping BEFORE either override; the overrides are asserted
        separately, so a change to one cannot be mistaken for a change to the other.
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

        result = rc.check_completeness(plan_id, ['coderabbit'], stale_participation_bots=['coderabbit'])

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

        result = rc.check_completeness(plan_id, ['cuioss-review-bot'], declined_bots=['cuioss-review-bot'])

        assert _state_of(result, 'cuioss-review-bot') == rc.STATE_DECLINED
        assert result['unproven_bots'] == ['cuioss-review-bot']
        assert result['participation_complete'] is False

        control_id = 'rc-state-declined-absent-control'
        plan_context.plan_dir_for(control_id)
        control = rc.check_completeness(control_id, ['cuioss-review-bot'])

        assert control['participation_complete'] == result['participation_complete']
        assert control['unproven_bots'] == result['unproven_bots']
        assert _state_of(control, 'cuioss-review-bot') == rc.STATE_ABSENT

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
        decline = rc.check_completeness(decline_id, ['cuioss-review-bot'], declined_bots=['cuioss-review-bot'])
        assert decline['participation_complete'] is False
        assert 'cuioss-review-bot' in decline['unproven_bots']
        assert _state_of(decline, 'cuioss-review-bot') == rc.STATE_DECLINED

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

        # The expected member is derived from the bot's own three-valued
        # rate_limit_class through the DEFAULT mapping (neither override is in play
        # here), never written as a literal, so a bot whose class is ``unknown``
        # (cuioss-review-bot) is asserted as ``refused_unknown`` — not folded into
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
            optional_bots=['cuioss-review-bot'],
            participated_bots=CODERABBIT_EVIDENCE,
            refused_bots=['sourcery'],
        )

        classified = [r['bot_kind'] for r in result['bot_states']]
        assert classified == ['coderabbit', 'sourcery', 'cuioss-review-bot']
        assert len(set(classified)) == len(classified)
        # DERIVED from the classifier's own ``STATE_`` constants rather than
        # hand-listed. The hand-written set this replaces had already drifted: it
        # omitted ``refused_structural``, and because the assertion is a SUBSET test
        # the omission could never fail — a stale enumeration that reported green
        # precisely because it was incomplete. A derived population cannot drift.
        known_states = {
            value for name, value in vars(rc).items() if name.startswith('STATE_') and isinstance(value, str)
        }
        assert known_states, 'no STATE_ constants derived — the membership check is vacuous'
        assert {r['state'] for r in result['bot_states']} <= known_states


class TestTriageStateAwareness:
    """A pending finding blocks only once triage has run, and only for a required bot."""

    def test_pending_bot_does_not_block_pre_triage(self, plan_context):
        """At the FIND-only step a pending finding is the expected state."""
        plan_id = 'rc-pending-pre-triage'
        plan_context.plan_dir_for(plan_id)
        _seed(plan_id, 'coderabbit', resolution='pending')

        result = rc.check_completeness(plan_id, ['coderabbit'], participated_bots=CODERABBIT_EVIDENCE)

        assert result['participation_complete'] is True
        assert result['pending_bots'] == ['coderabbit']
        assert result['unproven_bots'] == []

    def test_pending_bot_blocks_after_triage(self, plan_context):
        """The SAME store loops back once triage has run."""
        plan_id = 'rc-pending-post-triage'
        plan_context.plan_dir_for(plan_id)
        _seed(plan_id, 'coderabbit', resolution='pending')

        result = rc.check_completeness(plan_id, ['coderabbit'], triage_ran=True, participated_bots=CODERABBIT_EVIDENCE)

        assert result['participation_complete'] is False
        assert result['pending_bots'] == ['coderabbit']

    def test_bot_with_multiple_findings_one_pending(self, plan_context):
        """A bot is pending if ANY of its findings is unresolved."""
        plan_id = 'rc-multi'
        plan_context.plan_dir_for(plan_id)
        _seed(plan_id, 'coderabbit', resolution='fixed')
        _seed(plan_id, 'coderabbit', resolution='pending')

        pre = rc.check_completeness(plan_id, ['coderabbit'], participated_bots=CODERABBIT_EVIDENCE)
        assert pre['participation_complete'] is True
        assert pre['pending_bots'] == ['coderabbit']

        post = rc.check_completeness(plan_id, ['coderabbit'], triage_ran=True, participated_bots=CODERABBIT_EVIDENCE)
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

        result = rc.check_completeness(plan_id, ['coderabbit', 'cuioss-review-bot'])

        assert result['participation_complete'] is False
        assert result['pending_bots'] == []
        assert result['unproven_bots'] == ['coderabbit', 'cuioss-review-bot']


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

        result = rc.check_completeness(plan_id, ['coderabbit'], participated_bots=CODERABBIT_EVIDENCE)

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

        result = rc.check_completeness(plan_id, ['coderabbit'], participated_bots=CODERABBIT_EVIDENCE)

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


class TestReviewStateSummary:
    """``compose_review_state_summary`` distinguishes reviewed-clean from nobody-reviewed.

    ``"0 comment(s) found"`` is the identical display string for a clean 27-file
    review and for a run where no reviewer produced any content. The summary is what
    a reader appends to tell those two facts apart — the whole point of D3.
    """

    def test_nobody_reviewed_and_reviewed_clean_render_differently(self):
        """The load-bearing distinction: three refusals is NOT three clean reviews."""
        nobody = rc.compose_review_state_summary(
            [
                {'bot_kind': 'coderabbit', 'state': rc.STATE_REFUSED_AWAITABLE},
                {'bot_kind': 'sourcery', 'state': rc.STATE_REFUSED_HARD},
                {'bot_kind': 'cuioss-review-bot', 'state': rc.STATE_REFUSED_UNKNOWN},
            ]
        )
        reviewed_clean = rc.compose_review_state_summary(
            [
                {'bot_kind': 'coderabbit', 'state': rc.STATE_PARTICIPATED_BUT_EMPTY},
                {'bot_kind': 'sourcery', 'state': rc.STATE_PARTICIPATED_BUT_EMPTY},
                {'bot_kind': 'cuioss-review-bot', 'state': rc.STATE_PARTICIPATED_BUT_EMPTY},
            ]
        )
        assert nobody == '3 refused'
        assert reviewed_clean == '3 empty'
        # The two facts MUST NOT share a rendering — this is the whole deliverable.
        assert nobody != reviewed_clean

    def test_all_three_refusal_members_share_the_refused_bucket(self):
        summary = rc.compose_review_state_summary(
            [
                {'bot_kind': 'a', 'state': rc.STATE_REFUSED_AWAITABLE},
                {'bot_kind': 'b', 'state': rc.STATE_REFUSED_HARD},
                {'bot_kind': 'c', 'state': rc.STATE_REFUSED_UNKNOWN},
            ]
        )
        assert summary == '3 refused'

    def test_mixed_distribution_lists_each_nonzero_bucket_in_order(self):
        summary = rc.compose_review_state_summary(
            [
                {'bot_kind': 'a', 'state': rc.STATE_PARTICIPATED},
                {'bot_kind': 'b', 'state': rc.STATE_PARTICIPATED_BUT_EMPTY},
                {'bot_kind': 'c', 'state': rc.STATE_REFUSED_HARD},
            ]
        )
        assert summary == '1 reviewed, 1 empty, 1 refused'

    def test_empty_roster_produces_no_summary(self):
        """An empty roster has nothing to distribute — the honest value is ''."""
        assert rc.compose_review_state_summary([]) == ''

    def test_check_output_carries_the_summary(self, plan_context):
        """The field reaches the check envelope so ``display_detail`` can interpolate it."""
        plan_id = 'rc-summary-in-output'
        plan_context.plan_dir_for(plan_id)
        result = rc.check_completeness(
            plan_id,
            ['coderabbit', 'sourcery', 'cuioss-review-bot'],
            refused_bots=['coderabbit', 'sourcery', 'cuioss-review-bot'],
        )
        assert result['review_state_summary'] == '3 refused'

    def test_check_output_summary_empty_for_empty_roster(self, plan_context):
        plan_id = 'rc-summary-empty-roster'
        plan_context.plan_dir_for(plan_id)
        result = rc.check_completeness(plan_id, [])
        assert result['review_state_summary'] == ''

    def test_every_declared_state_falls_in_exactly_one_bucket(self):
        """The buckets PARTITION the state taxonomy — both halves of that word.

        ``compose_review_state_summary`` tallies a roster by walking
        ``_STATE_SUMMARY_BUCKETS``, so the bucket table is the only thing standing
        between a classified bot and the line an operator reads. Each half of
        *exactly one* fails differently, and both fail SILENTLY — the summary still
        renders, it is just wrong:

        - a state in NO bucket contributes to no tally, so every bot that lands
          there vanishes from the summary. The rendered total is short by that many
          reviewers while still reading as a complete distribution — the same
          collapse this whole surface exists to undo, re-entered through an
          uncovered member.
        - a state in TWO buckets is counted twice, so the total exceeds the roster
          and a reader cannot reconcile the summary against ``bot_states``.

        Both populations are DERIVED (see the two helpers above) rather than
        restated, so equality holds in BOTH directions by construction: a state
        added with no bucket fails here, and a bucket naming a state that no longer
        exists fails here too. Neither direction needs its own hand-maintained list,
        which is what keeps this case from becoming the next thing to go stale.
        """
        declared = _declared_state_values()
        bucketed = _bucketed_state_values()

        # The population guard, in THIS case rather than beside it. Both sets are
        # produced by scanning a live declaration, so a derivation that silently
        # collected nothing — a renamed constant prefix, a bucket table emptied —
        # would leave every assertion below holding vacuously and report this
        # partition clean while covering no state whatsoever.
        assert declared, (
            'no STATE_* constant was derived from review_completeness, so the '
            'totality comparison below holds vacuously over an empty population '
            'and pins nothing'
        )
        assert bucketed, (
            '_STATE_SUMMARY_BUCKETS named no state, so the comparison below holds '
            'vacuously and a summary that buckets nothing would still read clean'
        )

        assert set(bucketed) == declared, (
            f'the display buckets must cover the state taxonomy exactly. Declared '
            f'states in no bucket (silently dropped from every tally): '
            f'{sorted(declared - set(bucketed))}. Bucketed names that are not a '
            f'declared state (a stale bucket entry): '
            f'{sorted(set(bucketed) - declared)}'
        )

        duplicated = sorted({state for state in bucketed if bucketed.count(state) > 1})
        assert not duplicated, (
            f'a state may appear in at most ONE bucket or the rendered totals '
            f'double-count it against the roster: {duplicated}'
        )


class TestUnregisteredKind:
    """A token outside ``bot_registry.bot_kinds()`` resolves to ``unregistered_kind``.

    The defect this closes is a COLLAPSE: a configured token that names no
    registered reviewer could only ever fall through to ``absent``, which is the
    state reserved for *"this bot did not review"*. The barrier then reported a true
    statement about the observed set beside a false steer about its cause — the
    review existed and was plainly visible, while the operator was sent to chase a
    reviewer that was never the problem.

    Every case here is paired with a MATCHED NEGATIVE CONTROL: a correctly-named
    required bot that genuinely did not review must still resolve to ``absent``.
    Without that control the new member is indistinguishable from a blanket
    reclassification of every silent bot, which would destroy the distinction the
    member exists to draw rather than sharpen it.
    """

    def test_an_unregistered_required_token_gets_its_own_state(self, plan_context):
        """The new member, pinned. FAILS pre-change, where this resolved ``absent``."""
        plan_id = 'rc-unregistered-kind'
        plan_context.plan_dir_for(plan_id)

        result = rc.check_completeness(plan_id, [_UNREGISTERED_TOKEN])

        assert _state_of(result, _UNREGISTERED_TOKEN) == rc.STATE_UNREGISTERED_KIND
        # The load-bearing half: it is NOT the state that means "did not review".
        assert _state_of(result, _UNREGISTERED_TOKEN) != rc.STATE_ABSENT

    def test_matched_negative_control_a_valid_silent_bot_is_still_absent(self, plan_context):
        """The control, which passes in BOTH the pre- and post-change forms.

        This is what proves the suite DISCRIMINATES rather than merely asserting: a
        refinement that also moved this case would be a blanket reclassification, and
        the case above alone could not tell the two apart.
        """
        plan_id = 'rc-unregistered-control'
        plan_context.plan_dir_for(plan_id)

        result = rc.check_completeness(plan_id, [_VALID_TOKEN])

        assert _state_of(result, _VALID_TOKEN) == rc.STATE_ABSENT
        assert _state_of(result, _VALID_TOKEN) != rc.STATE_UNREGISTERED_KIND

    def test_the_two_tokens_are_separated_within_one_run(self, plan_context):
        """Both tokens, one call, identical (empty) observations.

        Registry membership is then the ONLY difference between them, so the split
        cannot be attributed to anything else about the two invocations.
        """
        plan_id = 'rc-unregistered-both'
        plan_context.plan_dir_for(plan_id)

        result = rc.check_completeness(plan_id, [_VALID_TOKEN, _UNREGISTERED_TOKEN])

        assert _state_of(result, _VALID_TOKEN) == rc.STATE_ABSENT
        assert _state_of(result, _UNREGISTERED_TOKEN) == rc.STATE_UNREGISTERED_KIND

    def test_the_new_state_blocks_and_the_token_stays_in_the_roster(self, plan_context):
        """Fail-CLOSED: an unknown name blocks exactly as ``absent`` does.

        A silent drop would replace a confusing block with a silent PASS — the quorum
        satisfied through a reviewer nobody configured — which is strictly worse than
        the defect being fixed. So the token is still classified, still reported, and
        still holds the step open.
        """
        plan_id = 'rc-unregistered-blocks'
        plan_context.plan_dir_for(plan_id)

        result = rc.check_completeness(plan_id, [_UNREGISTERED_TOKEN])

        assert result['participation_complete'] is False
        assert result['unproven_bots'] == [_UNREGISTERED_TOKEN]
        assert rc.STATE_UNREGISTERED_KIND in rc._UNPROVEN_STATES

    def test_an_observation_outranks_the_membership_test(self, plan_context):
        """Ordering: a fact about the NAME never displaces something observed.

        The membership test is checked AFTER every observation branch, so an
        unregistered token that was nonetheless observed reports what was observed.
        Hoisting the test above the observations would erase real evidence on the
        strength of a config lookup.
        """
        plan_id = 'rc-unregistered-observed'
        plan_context.plan_dir_for(plan_id)

        in_progress = rc.check_completeness(plan_id, [_UNREGISTERED_TOKEN], in_progress_bots=[_UNREGISTERED_TOKEN])
        assert _state_of(in_progress, _UNREGISTERED_TOKEN) == rc.STATE_IN_PROGRESS

        # Passed as a dict directly: ``parse_participation`` admits a pair only when
        # the evidence kind is one the bot's registry record declares, and an
        # unregistered token has no record and therefore no admissible shape. Going
        # through the parser here would assert the fall-through rather than the
        # branch ordering this case exists to pin.
        participating = rc.check_completeness(
            plan_id, [_UNREGISTERED_TOKEN], participated_bots={_UNREGISTERED_TOKEN: 'inline'}
        )
        assert _state_of(participating, _UNREGISTERED_TOKEN) == rc.STATE_PARTICIPATED_BUT_EMPTY

    def test_the_payload_names_the_live_kind_set_it_checked_against(self, plan_context):
        """ADR-019: the verdict carries the POPULATION the token was checked against.

        "This name matches no reviewer we know" is only actionable beside the set of
        names we DO know — which is also the set the corrected token must come from.
        Derived from the registry here rather than spelled, so the assertion tracks a
        rename instead of pinning a stale roster.
        """
        plan_id = 'rc-unregistered-kind-set'
        plan_context.plan_dir_for(plan_id)

        result = rc.check_completeness(plan_id, [_UNREGISTERED_TOKEN])

        assert result['known_bot_kinds'] == _REGISTERED_BOTS

    def test_the_summary_gives_the_new_member_its_own_bucket(self):
        """``unregistered`` never renders as ``absent`` in the compact distribution.

        Collapsing it there would undo, at the summary line a reader actually sees,
        exactly the distinction the member was added to carry.
        """
        summary = rc.compose_review_state_summary(
            [
                {'bot_kind': _UNREGISTERED_TOKEN, 'state': rc.STATE_UNREGISTERED_KIND},
                {'bot_kind': _VALID_TOKEN, 'state': rc.STATE_ABSENT},
            ]
        )

        assert summary == '1 unregistered, 1 absent'

    def test_cli_publishes_the_kind_set_and_its_population_size(self, plan_context):
        """Through the REAL parser: the emitted TOON names the set AND its size.

        The size is PUBLISHED in the row header rather than left for the reader to
        count — a population whose size is implied is one a consumer cannot check it
        read completely.
        """
        plan_id = 'rc-cli-unregistered'
        plan_context.plan_dir_for(plan_id)

        result = run_script(SCRIPT_PATH, 'check', '--plan-id', plan_id, '--required-bots', _UNREGISTERED_TOKEN)

        assert result.success, result.stderr
        assert result.returncode != 2, result.stderr
        assert f'{_UNREGISTERED_TOKEN},unregistered_kind' in result.stdout
        assert f'known_bot_kinds[{len(_REGISTERED_BOTS)}]:' in result.stdout
        for kind in _REGISTERED_BOTS:
            assert f'  - {kind}' in result.stdout

    def test_cli_omits_the_kind_set_when_every_token_is_registered(self, plan_context):
        """The paired emission control: the remedy line is gated, not unconditional.

        When no token failed the membership test the same list is noise on every run
        — a population nobody is being asked to choose from, printed beside a verdict
        it did not shape. Isolating the token as the only difference between this
        invocation and the one above is what shows the gate keys on the FAILURE
        rather than on something else in the command line.
        """
        plan_id = 'rc-cli-unregistered-omitted'
        plan_context.plan_dir_for(plan_id)

        result = run_script(SCRIPT_PATH, 'check', '--plan-id', plan_id, '--required-bots', _VALID_TOKEN)

        assert result.success, result.stderr
        assert f'{_VALID_TOKEN},absent' in result.stdout
        assert 'known_bot_kinds' not in result.stdout
        assert 'unregistered_kind' not in result.stdout

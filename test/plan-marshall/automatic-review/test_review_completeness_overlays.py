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


class TestUnrecognisedRefusalOverride:
    """A refusal no recognition arm could read resolves ``refused_unknown``, always."""

    def test_the_swept_class_population_is_non_empty_and_published(self):
        """Guards every sweep below, and reports the two population sizes it derived.

        Both figures are read from INDEPENDENT sources — the bot population from the
        registry's bot list, the class population from each bot's declared class — so
        the comparison is not a count checked against itself.
        """
        assert _REGISTERED_BOTS, 'the registered bot population is empty'
        assert _DECLARED_RATE_LIMIT_CLASSES, 'the declared class population is empty'
        # The class population is derived FROM the bot population, so it can never be
        # larger; asserting the relation makes an empty or collapsed derivation visible.
        assert len(_DECLARED_RATE_LIMIT_CLASSES) <= len(_REGISTERED_BOTS), (
            f'{len(_DECLARED_RATE_LIMIT_CLASSES)} classes derived from {len(_REGISTERED_BOTS)} bots'
        )

    @pytest.mark.parametrize('bot_kind', _REGISTERED_BOTS)
    def test_the_override_applies_whatever_class_the_bot_declares(self, bot_kind, plan_context):
        """Swept over the WHOLE registered population, so every declared class is exercised.

        The population is registry-derived, so a bot added or reclassified in a
        standards doc is covered automatically. The assertion is the same for every
        bot precisely because the override ignores the class — which is the property
        under test.
        """
        plan_id = f'rc-unrecognised-{bot_kind}'
        plan_context.plan_dir_for(plan_id)

        result = rc.check_completeness(
            plan_id,
            [bot_kind],
            refused_bots=[bot_kind],
            unrecognised_refusal_bots=[bot_kind],
        )

        assert _state_of(result, bot_kind) == rc.STATE_REFUSED_UNKNOWN
        assert result['participation_complete'] is False
        assert bot_kind in result['unproven_bots']

    @pytest.mark.parametrize('bot_kind', _REGISTERED_BOTS)
    def test_the_matched_control_classifies_by_the_declared_class(self, bot_kind, plan_context):
        """Matched negative control: the SAME refusal without the override.

        Identical inputs but for ``unrecognised_refusal_bots``, so the override is
        isolated as the only difference. A recognised refusal keeps the member its
        declared class maps to — without this control the sweep above would pass just
        as happily against a classifier that returned ``refused_unknown`` for every
        refusal, which would destroy the awaitability split entirely.
        """
        plan_id = f'rc-unrecognised-control-{bot_kind}'
        plan_context.plan_dir_for(plan_id)

        result = rc.check_completeness(plan_id, [bot_kind], refused_bots=[bot_kind])

        expected = rc._refusal_state(rc.bot_registry.rate_limit_class(bot_kind))
        assert _state_of(result, bot_kind) == expected

    def test_an_awaitable_window_bot_is_the_case_the_override_exists_for(self, plan_context):
        """⭐ The load-bearing branch, asserted on a bot that declares ``awaitable_window``.

        Reading the class here would render ``refused_awaitable`` — *worth awaiting* —
        for a notice nobody could read, offering the operator a wait on a window that
        was never observed. The bot is selected FROM the registry by its declared
        class rather than named, and the selection is guarded so this cannot pass
        vacuously if no such bot exists.
        """
        awaitable = [b for b in _REGISTERED_BOTS if rc.bot_registry.rate_limit_class(b) == 'awaitable_window']
        assert awaitable, 'no registered bot declares awaitable_window — case is vacuous'
        bot_kind = awaitable[0]

        plan_id = f'rc-unrecognised-awaitable-{bot_kind}'
        plan_context.plan_dir_for(plan_id)
        result = rc.check_completeness(
            plan_id,
            [bot_kind],
            refused_bots=[bot_kind],
            unrecognised_refusal_bots=[bot_kind],
        )

        assert _state_of(result, bot_kind) == rc.STATE_REFUSED_UNKNOWN
        assert _state_of(result, bot_kind) != rc.STATE_REFUSED_AWAITABLE

    def test_the_override_is_asserted_on_the_mapping_itself(self):
        """Asserted directly on ``_refusal_state`` over every declared class value.

        A verdict-level sweep alone could pass for a downstream reason; this pins the
        mapping. Every class the registry declares is exercised, and the population
        size is reported in the failure message.
        """
        for rate_limit_class in _DECLARED_RATE_LIMIT_CLASSES:
            assert rc._refusal_state(rate_limit_class, None, True) == rc.STATE_REFUSED_UNKNOWN, (
                f'{rate_limit_class!r} did not take the override '
                f'(over {len(_DECLARED_RATE_LIMIT_CLASSES)} declared class values)'
            )

    def test_a_read_size_cause_outranks_the_unrecognised_override(self):
        """Both overrides CAN hold, and the positively-read one wins.

        They would be contradictory only if they described the SAME refusal. Both are
        per-BOT aggregates over that bot's refusals: the producer emits one
        ``unrecognised_refusal[]`` record per COMMENT and the consumer receives a
        bot-kind list, so a bot that published one refusal an arm READ as a size
        ceiling and another no arm could read satisfies both, from two different
        notices, with neither observation wrong.

        The size cause is taken first because it rests on text that WAS read; an
        absence observed on some other notice must not erase a ceiling the run
        actually extracted, leaving the operator without the one remedy already in
        hand.
        """
        assert rc._refusal_state('hard_quota', rc.CAUSE_SIZE, True) == rc.STATE_REFUSED_STRUCTURAL
        # The override still decides when NO cause was read — it is displaced, not retired.
        assert rc._refusal_state('hard_quota', None, True) == rc.STATE_REFUSED_UNKNOWN
        # ...and the cause still resolves structural without the override present.
        assert rc._refusal_state('hard_quota', rc.CAUSE_SIZE, False) == rc.STATE_REFUSED_STRUCTURAL

    def test_the_ordering_never_costs_awaitability(self):
        """The safety property that makes the ordering conservative, not merely richer.

        Whichever override wins, the member is non-awaitable — so no order of the two
        can ever offer a wait on a bot carrying an unreadable notice. This is what
        licenses preferring the more informative arm: the choice decides whether the
        operator is told WHY, never whether they are told to wait. Asserted on the
        awaitable-declaring class, the only one where a wrong answer would differ.
        """
        for cause in (rc.CAUSE_SIZE, None):
            state = rc._refusal_state('awaitable_window', cause, True)

            assert state != rc.STATE_REFUSED_AWAITABLE, (
                f'cause={cause!r} with the unrecognised override resolved {state} — '
                f'an awaitable member for a notice no arm could read'
            )

    def test_the_default_is_unchanged_when_no_bot_is_unrecognised(self, plan_context):
        """An empty override set moves no verdict — the parameter is opt-in.

        Pins that adding the input cannot disturb an existing caller that does not
        pass it.
        """
        plan_id = 'rc-unrecognised-empty'
        plan_context.plan_dir_for(plan_id)

        with_empty = rc.check_completeness(
            plan_id, ['coderabbit'], refused_bots=['coderabbit'], unrecognised_refusal_bots=[]
        )
        without = rc.check_completeness(plan_id, ['coderabbit'], refused_bots=['coderabbit'])

        assert with_empty['bot_states'] == without['bot_states']
        assert _state_of(with_empty, 'coderabbit') == rc.STATE_REFUSED_AWAITABLE

    @pytest.mark.parametrize('bot_kind', _REGISTERED_BOTS)
    def test_the_override_is_reachable_on_the_producers_real_output_shape(self, bot_kind, plan_context):
        """⭐ The override's OWN motivating case, staged as the producer really emits it.

        The producer reports the two sets DISJOINTLY: ``unrecognised_refusal[]`` names a
        bot and ``refused_bots`` does NOT ("an unrecognised one names no bot in
        refused_bots"). Every other case in this class supplies BOTH, which is a shape
        the producer never emits — so they exercised the override through a door only a
        test opens, and the branch that gates it was never reached by the input it exists
        for.

        Staged the real way, the bot must still resolve ``refused_unknown``. Resolving
        ``absent`` here is the failure the contract names in as many words: "the exact
        conflation that let a PR with two refusing required bots report a complete
        review".
        """
        plan_id = f'rc-unrecognised-only-{bot_kind}'
        plan_context.plan_dir_for(plan_id)

        result = rc.check_completeness(
            plan_id,
            [bot_kind],
            # refused_bots deliberately NOT supplied — this is the producer's shape.
            unrecognised_refusal_bots=[bot_kind],
        )

        assert _state_of(result, bot_kind) == rc.STATE_REFUSED_UNKNOWN, (
            'a bot whose only refusal no arm could read must resolve refused_unknown; '
            'absent would report a bot that DECLINED as one that stayed silent'
        )
        assert _state_of(result, bot_kind) != rc.STATE_ABSENT
        assert result['participation_complete'] is False
        assert bot_kind in result['unproven_bots']

    def test_a_bot_in_neither_refusal_set_keeps_its_own_state(self, plan_context):
        """The override never manufactures a refusal for a bot that was SILENT.

        The guard is real, but its subject is a bot the producer reported in NEITHER
        refusal set. Membership in ``unrecognised_refusal`` is itself the refusal
        OBSERVATION — the producer emits that record only on a detected refusal and
        counts it in ``count_skipped_refusal`` — so it is not a qualifier waiting for a
        separate one to arrive in ``refused_bots``. Reading it that way is what made the
        override unreachable on the producer's real, disjoint output shape (see
        ``test_the_override_is_reachable_on_the_producers_real_output_shape``).

        Staged with neither set, the bot must still resolve ``absent``.
        """
        plan_id = 'rc-neither-refusal-set'
        plan_context.plan_dir_for(plan_id)

        result = rc.check_completeness(plan_id, ['coderabbit'])

        assert _state_of(result, 'coderabbit') == rc.STATE_ABSENT

    def test_check_and_deficit_agree_on_the_overridden_member(self, plan_context):
        """Both commands name the SAME member for one unrecognised refusal.

        ``deficit`` publishes a per-reviewer ``state`` column, so an override consumed
        by only one command would make the two disagree about one refusal — a
        contradiction no reader of the output could adjudicate, and the exact failure
        the shared cause flag already exists to prevent.
        """
        plan_id = 'rc-unrecognised-both-commands'
        plan_context.plan_dir_for(plan_id)
        shared = {'refused_bots': ['coderabbit'], 'unrecognised_refusal_bots': ['coderabbit']}

        check = rc.check_completeness(plan_id, ['coderabbit'], **shared)
        deficit = rc.check_deficit(plan_id, ['coderabbit'], **shared)

        deficit_state = next(r['state'] for r in deficit['reviewers'] if r['bot_kind'] == 'coderabbit')
        assert deficit_state == _state_of(check, 'coderabbit') == rc.STATE_REFUSED_UNKNOWN

    def test_the_cli_accepts_the_flag_and_drives_the_verdict(self, plan_context):
        """Driven through the REAL parser, because that is what a caller reaches.

        An in-process call would pass even if the argparse declaration were missing
        entirely — the same gap the ``--not-triggered`` cases above exist to close.
        """
        plan_id = 'rc-cli-unrecognised'
        plan_context.plan_dir_for(plan_id)

        result = run_script(
            SCRIPT_PATH,
            'check',
            '--plan-id',
            plan_id,
            '--required-bots',
            'coderabbit',
            '--refused-bots',
            'coderabbit',
            '--unrecognised-refusal-bots',
            'coderabbit',
        )

        assert result.success, result.stderr
        assert result.returncode != 2, result.stderr
        assert 'coderabbit,refused_unknown' in result.stdout

    def test_omitting_the_flag_leaves_the_declared_class_verdict(self, plan_context):
        """The paired CLI control: without the flag the same command reports the default."""
        plan_id = 'rc-cli-unrecognised-omitted'
        plan_context.plan_dir_for(plan_id)

        result = run_script(
            SCRIPT_PATH,
            'check',
            '--plan-id',
            plan_id,
            '--required-bots',
            'coderabbit',
            '--refused-bots',
            'coderabbit',
        )

        assert result.success, result.stderr
        assert 'coderabbit,refused_awaitable' in result.stdout


class TestRefusalCauseOverlay:
    """The size/quota CAUSE axis: STATE-DETERMINING for ``size``, advisory otherwise.

    ``refusal_cause`` (in the producer) names the REMEDY a refusal calls for. It is
    forwarded to ``--refused-causes`` and reported in ``refusal_causes[]``, and it
    splits into two halves that must be pinned separately:

    - ``size`` resolves the bot to ``refused_structural`` **whatever its
      ``rate_limit_class`` declares** — the ceiling is on the diff, so no temporal
      member describes it and none of their remedies applies.
    - every other cause is ADVISORY: it is reported, and it moves no awaitability
      member (``refused_awaitable`` / ``refused_hard`` / ``refused_unknown``).

    Neither half gates: ``participation_complete`` is unmoved either way, because every
    refusal member is unproven regardless of which one it is.
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
            plan_id,
            ['sourcery'],
            refused_bots=['sourcery'],
            refused_causes={'sourcery': 'size'},
        )
        # A size cause resolves the STRUCTURAL member, not sourcery's hard_quota
        # awaitability member — and the row carries a cap column (unknown here, since
        # no cap was supplied).
        assert _state_of(result, 'sourcery') == rc.STATE_REFUSED_STRUCTURAL
        assert result['refusal_causes'] == [{'bot_kind': 'sourcery', 'cause': 'size', 'cap': ''}]

    def test_cause_for_a_non_refused_bot_is_dropped(self, plan_context):
        # A cause supplied for a bot that did NOT resolve to a refusal state is not
        # reported — the overlay only annotates bots actually classified refused.
        plan_id = 'rc-cause-nonrefused'
        plan_context.plan_dir_for(plan_id)
        _seed(plan_id, 'coderabbit', resolution='fixed')
        result = rc.check_completeness(
            plan_id,
            ['coderabbit'],
            participated_bots=CODERABBIT_EVIDENCE,
            refused_causes={'coderabbit': 'size'},
        )
        assert _state_of(result, 'coderabbit') == rc.STATE_PARTICIPATED
        assert result['refusal_causes'] == []

    def test_a_non_size_cause_never_changes_the_awaitability_member(self, plan_context):
        # coderabbit's rate_limit_class is awaitable_window → refused_awaitable. A
        # non-size cause is advisory and leaves that member alone.
        plan_id = 'rc-cause-advisory'
        plan_context.plan_dir_for(plan_id)
        result = rc.check_completeness(
            plan_id,
            ['coderabbit'],
            refused_bots=['coderabbit'],
            refused_causes={'coderabbit': 'quota'},
        )
        assert _state_of(result, 'coderabbit') == rc.STATE_REFUSED_AWAITABLE
        assert result['refusal_causes'] == [{'bot_kind': 'coderabbit', 'cause': 'quota', 'cap': ''}]

    def test_no_causes_emits_no_refusal_causes(self, plan_context):
        plan_id = 'rc-cause-none'
        plan_context.plan_dir_for(plan_id)
        result = rc.check_completeness(plan_id, ['sourcery'], refused_bots=['sourcery'])
        assert result['refusal_causes'] == []

    def test_cli_emits_the_refusal_causes_block(self, plan_context):
        plan_id = 'rc-cause-cli'
        plan_context.plan_dir_for(plan_id)
        result = run_script(
            SCRIPT_PATH,
            'check',
            '--plan-id',
            plan_id,
            '--required-bots',
            'sourcery',
            '--refused-bots',
            'sourcery',
            '--refused-causes',
            'sourcery:size',
        )
        assert result.returncode == 0
        assert 'refusal_causes[1]{bot_kind,cause,cap}:' in result.stdout
        # No --refusal-size-caps supplied, so the cap column reads the literal
        # ``unknown`` rather than an empty field or an invented figure.
        assert 'sourcery,size,unknown' in result.stdout

    def test_cli_malformed_cause_is_an_unknown_verdict(self, plan_context):
        # A bare token on the pair-form --refused-causes is a caller error → status:
        # error, non-zero exit, and NO participation_complete field (UNKNOWN verdict).
        plan_id = 'rc-cause-malformed'
        plan_context.plan_dir_for(plan_id)
        result = run_script(
            SCRIPT_PATH,
            'check',
            '--plan-id',
            plan_id,
            '--required-bots',
            'sourcery',
            '--refused-causes',
            'sourcery',
        )
        assert result.returncode == 1
        assert 'participation_complete' not in result.stdout

    def test_refused_causes_flag_reads_bare_as_empty(self, plan_context):
        plan_id = 'rc-cause-bare'
        plan_context.plan_dir_for(plan_id)
        result = run_script(
            SCRIPT_PATH,
            'check',
            '--plan-id',
            plan_id,
            '--required-bots',
            'sourcery',
            '--refused-bots',
            'sourcery',
            '--refused-causes',
        )
        assert result.returncode == 0
        assert 'refusal_causes' not in result.stdout

    def test_cause_does_not_change_the_verdict(self, plan_context):
        """The 'no gating' half: the VERDICT is identical with vs without a cause.

        A size cause moves the reported STATE (that is the point of the member), but it
        must move neither ``participation_complete`` nor the unproven/pending sets —
        every refusal member is unproven regardless of which one it is, so the cause
        selects a remedy, never an admission. Pinning this separately from the state is
        what stops a future edit turning the remedy signal into a gate.
        """
        plan_id = 'rc-cause-no-gate'
        plan_context.plan_dir_for(plan_id)
        without = rc.check_completeness(plan_id, ['sourcery'], refused_bots=['sourcery'])
        with_cause = rc.check_completeness(
            plan_id,
            ['sourcery'],
            refused_bots=['sourcery'],
            refused_causes={'sourcery': 'size'},
        )
        assert without['participation_complete'] == with_cause['participation_complete']
        assert without['unproven_bots'] == with_cause['unproven_bots']
        assert without['pending_bots'] == with_cause['pending_bots']
        # The state DOES move — from the temporal member to the structural one — and
        # that is the deliberate change, so it is asserted rather than tolerated.
        assert _state_of(without, 'sourcery') == rc.STATE_REFUSED_HARD
        assert _state_of(with_cause, 'sourcery') == rc.STATE_REFUSED_STRUCTURAL
        assert without['refusal_causes'] == []
        assert with_cause['refusal_causes'] == [{'bot_kind': 'sourcery', 'cause': 'size', 'cap': ''}]


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
            'cuioss-review-bot',
            '--stale-participation-bots',
            'cuioss-review-bot:issue_comment',
        )

        assert result.success, result.stderr
        assert 'participation_complete: false' in result.stdout
        assert 'cuioss-review-bot,participated_stale' in result.stdout

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
            'cuioss-review-bot',
            '--stale-participation-bots',
            'cuioss-review-bot',
        )

        assert result.returncode == 1, result.stderr
        assert 'malformed_bot_flag' in result.stdout
        assert 'participation_complete' not in result.stdout


class TestAbsentVersusInProgressDistinction:
    """An absent reviewer and an in-flight one are DIFFERENT facts (plan 130 D3).

    Retirement evidence for the carried lesson *"the completeness guard conflates
    an absent bot with an in-progress one"*. The distinction is shipped — the two
    are separate taxonomy members with separate `classify_bot` branches — but no
    single test pinned that they stay distinguishable all the way to what a reader
    sees, and a conflation would be invisible until it cost a run.

    It matters because the two call for OPPOSITE remedies. An in-flight review will
    land on its own: waiting is the correct action. An absent reviewer never
    started: waiting is pure loss and the correct action is to escalate or trigger.
    Both block the quorum, which is exactly why the blocking verdict alone cannot
    tell them apart — the discrimination has to survive into `bot_states` and into
    the rendered summary a reader acts on.
    """

    def test_the_two_states_are_distinct_taxonomy_members(self):
        assert rc.STATE_ABSENT != rc.STATE_IN_PROGRESS

    def test_both_block_but_classify_differently(self, plan_context):
        """Identical `participation_complete`, different `bot_states` — the whole point.

        Matched pair over one fixture: the ONLY input that differs is whether the
        bot was observed in-flight, so a difference in the reported state can come
        from nothing else.
        """
        plan_id = 'rc-absent-vs-inprogress'
        plan_context.plan_dir_for(plan_id)

        absent = rc.check_completeness(plan_id, ['coderabbit'])
        in_flight = rc.check_completeness(plan_id, ['coderabbit'], in_progress_bots=['coderabbit'])

        # Same gating outcome — which is why the verdict alone cannot separate them.
        assert absent['participation_complete'] is False
        assert in_flight['participation_complete'] is False
        assert absent['unproven_bots'] == in_flight['unproven_bots'] == ['coderabbit']
        # ...and yet the reported state differs.
        assert _state_of(absent, 'coderabbit') == rc.STATE_ABSENT
        assert _state_of(in_flight, 'coderabbit') == rc.STATE_IN_PROGRESS

    def test_the_distinction_survives_into_the_rendered_summary(self):
        """A reader of `display_detail` can tell "not started" from "still running".

        The classification being distinct buys nothing if both collapse into one
        display bucket, since the summary is what an operator actually reads.
        """
        absent = rc.compose_review_state_summary(
            [
                {'bot_kind': 'coderabbit', 'state': rc.STATE_ABSENT},
            ]
        )
        in_flight = rc.compose_review_state_summary(
            [
                {'bot_kind': 'coderabbit', 'state': rc.STATE_IN_PROGRESS},
            ]
        )

        assert absent == '1 absent'
        assert in_flight == '1 in-progress'
        assert absent != in_flight

    def test_not_triggered_is_a_third_fact_not_a_synonym_for_either(self, plan_context):
        """PR-wide "nothing ran" refines `absent` without collapsing into it.

        Its remedy differs again: trigger the review, rather than escalate a
        reviewer that was asked and stayed silent.
        """
        plan_id = 'rc-absent-vs-nottriggered'
        plan_context.plan_dir_for(plan_id)

        absent = rc.check_completeness(plan_id, ['coderabbit'])
        not_triggered = rc.check_completeness(plan_id, ['coderabbit'], not_triggered=True)

        assert _state_of(absent, 'coderabbit') == rc.STATE_ABSENT
        assert _state_of(not_triggered, 'coderabbit') == rc.STATE_NOT_TRIGGERED
        assert rc.STATE_NOT_TRIGGERED not in {rc.STATE_ABSENT, rc.STATE_IN_PROGRESS}

#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""The STRUCTURAL refusal member — a size-capped reviewer is never offered a wait.

The refusal taxonomy modelled only TEMPORAL refusal: every member said *not now*,
and every remedy set built on one offered *wait, or accept the gap*. A diff-size
ceiling is not temporal — the same PR is over the limit a minute later and an hour
later alike — so on the size branch that option pair contains a **non-option**: an
action the operator can take that is guaranteed not to work.

`refused_structural` is the member that closes it, and this suite pins the four
claims that make it more than a relabelling:

(a) **Classification.** A size-caused refusal resolves to ``refused_structural`` —
    not to a rate refusal, and not to the unexplained non-participation ``absent``.
    The cause DOMINATES the awaitability axis, which is the load-bearing half: a bot
    declaring ``awaitable_window`` that refuses on size must NOT land on
    ``refused_awaitable``, whose whole meaning is *worth awaiting*.
(b) **No await on the structural branch.** The documents that render a remedy set
    for this member offer split / accept / disable and never a wait — the case that
    distinguishes this from a relabelling exercise, so it is asserted against the
    real document text rather than against prose ABOUT the text.
(c) **The cap travels.** The finding carries the ceiling the bot's own notice
    stated, so an accepted gap is auditable against the measured diff size. An
    unstated cap reads ``unknown`` and is never defaulted.
(d) **The terminal-state population is DERIVED** — from the classifier's own
    ``STATE_`` constants and the contract's normative table — asserted NON-EMPTY
    first, and every member classified as passable-by-plan-action or not.

⛔ **No test here pins the real Sourcery cap figure.** Its value is a provider's to
change, and encoding it would make this suite assert a number nobody re-derived.
Every cap assertion uses a SYNTHETIC notice, so what is pinned is the extraction
MECHANISM — which is the part that can regress.
"""

from __future__ import annotations

import re
import sys

import pytest

from conftest import get_script_path, run_script

SCRIPT_PATH = get_script_path('plan-marshall', 'automatic-review', 'review_completeness.py')
SCRIPTS_DIR = SCRIPT_PATH.parent

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import bot_registry  # noqa: E402
import review_completeness as rc  # noqa: E402

_CONTRACT_DOC = SCRIPTS_DIR.parent / 'standards' / 'bot-participation-contract.md'
_AR_SKILL = SCRIPTS_DIR.parent / 'SKILL.md'
_BRANCH_CLEANUP = (
    SCRIPTS_DIR.parent.parent / 'phase-6-finalize' / 'standards' / 'branch-cleanup.md'
)
#: The dispatcher that actually FIRES the operator prompt (item 7a). The leaf only
#: returns an envelope, so this file — not the leaf's — is where a wrong remedy set
#: reaches a human.
_FINALIZE_SKILL = SCRIPTS_DIR.parent.parent / 'phase-6-finalize' / 'SKILL.md'


def _state_of(result: dict, bot: str) -> str:
    """The state ``bot`` resolved to in a ``check_completeness`` payload."""
    for record in result['bot_states']:
        if record['bot_kind'] == bot:
            return str(record['state'])
    raise AssertionError(f'{bot} missing from bot_states: {result["bot_states"]}')


# ---------------------------------------------------------------------------
# (d) The terminal-state population — DERIVED, non-empty-asserted, fully classified
# ---------------------------------------------------------------------------

#: Every state the guard can resolve a bot to, DERIVED from the classifier's own
#: constants rather than hand-listed. A hand-list is strictly worse than the source
#: here: the whole point of the population is to be complete, and a literal is
#: complete only until the next member is added.
_TERMINAL_STATES = frozenset(
    value
    for name, value in vars(rc).items()
    if name.startswith('STATE_') and isinstance(value, str)
)

#: Per member: can a plan exit this state by an action of its OWN — as opposed to
#: needing an operator ruling, a re-scope, or a change to the reviewer's
#: configuration? ``True`` means the plan has a move that can change the answer
#: (wait out a running review, re-trigger, generate the trigger event, await a window
#: that reopens); ``False`` means every remedy is outside the plan's own reach, so the
#: state is exited by an operator decision rather than by acting.
#:
#: Read against the SHIPPED branches, not against what is imaginable: the recovery
#: sequence escalates immediately for ``hard_quota`` and ``unknown``, so the plan does
#: not act on those — it asks.
_PASSABLE_BY_PLAN_ACTION = {
    rc.STATE_PARTICIPATED: True,             # not a block at all
    rc.STATE_PARTICIPATED_BUT_EMPTY: True,   # accounted-for, never a block
    rc.STATE_IN_PROGRESS: True,              # the run finishes; time is the remedy
    rc.STATE_NOT_TRIGGERED: True,            # generate the trigger event
    rc.STATE_PARTICIPATED_STALE: True,       # re-trigger a re-review
    rc.STATE_ABSENT: True,                   # loop back and re-trigger the silent bot
    rc.STATE_REFUSED_AWAITABLE: True,        # claim the window and await the reset
    rc.STATE_REFUSED_UNKNOWN: False,         # recovery escalates rather than awaiting
    rc.STATE_REFUSED_HARD: False,            # a budget the plan cannot restore
    rc.STATE_DECLINED: False,                # re-triggering yields another decline
    rc.STATE_REFUSED_STRUCTURAL: False,      # the ceiling is on the diff, not on time
}

#: Per member: could WAITING, in principle, ever produce the review? This is the axis
#: on which a remedy is a non-option rather than merely a slow option — a wait offered
#: for a ``False`` member is an action the operator can take that is guaranteed not to
#: work.
#:
#: ``refused_unknown`` is ``True`` because the registry declares IGNORANCE: waiting is
#: not known to fail, and recording it as a refuted remedy would assert the hard-quota
#: finding that member exists to avoid making.
#:
#: ⭐ ``refused_structural`` is the member this plan is about. It is the only ``False``
#: row whose falsity is a property of the DIFF rather than of a budget or a schedule,
#: and it is knowable in advance — which is why it earns both its own member and an
#: advance-disclosure surface.
_AWAIT_CAN_EVER_SUCCEED = {
    rc.STATE_PARTICIPATED: False,            # nothing to wait for
    rc.STATE_PARTICIPATED_BUT_EMPTY: False,  # nothing to wait for
    rc.STATE_IN_PROGRESS: True,              # the run is still going
    rc.STATE_NOT_TRIGGERED: False,           # nothing was asked; waiting asks nothing
    rc.STATE_PARTICIPATED_STALE: False,      # waiting alone refreshes no review
    rc.STATE_ABSENT: True,                   # the bot may still answer
    rc.STATE_REFUSED_AWAITABLE: True,        # the window reopens on its own
    rc.STATE_REFUSED_UNKNOWN: True,          # not known to fail — see above
    rc.STATE_REFUSED_HARD: False,            # does not reopen on a useful timescale
    rc.STATE_DECLINED: False,                # the bot answered and will answer the same
    rc.STATE_REFUSED_STRUCTURAL: False,      # ⭐ the diff is the limit; time is not
}


class TestTerminalStatePopulation:
    """(d) The population is derived, non-empty, and every member is classified."""

    def test_the_derived_population_is_non_empty(self):
        """Asserted FIRST and alone — every check below is vacuous over an empty set.

        Not theoretical: the derivation is a ``vars()`` sweep for a name prefix, so a
        rename of the ``STATE_`` convention yields zero members and silently disarms
        the whole module while it still reports green.
        """
        assert _TERMINAL_STATES, (
            'zero terminal states were derived from review_completeness — the sweep '
            'is vacuous and every classification below would pass over nothing'
        )

    @pytest.mark.parametrize(
        'classification, label',
        [
            (_PASSABLE_BY_PLAN_ACTION, 'passable-by-plan-action'),
            (_AWAIT_CAN_EVER_SUCCEED, 'await-can-ever-succeed'),
        ],
    )
    def test_every_derived_state_is_classified(self, classification, label):
        """Each classification is TOTAL over the derived population.

        Equality in both directions: a subset would let a newly added member sit
        outside every arm (the exact hole this plan found), and a superset would let
        a retired member's row stand as classification of nothing.
        """
        assert set(classification) == _TERMINAL_STATES, (
            f'{label}: derived ({len(_TERMINAL_STATES)}): {sorted(_TERMINAL_STATES)}; '
            f'classified ({len(classification)}): {sorted(classification)}; '
            f'unclassified: {sorted(_TERMINAL_STATES - set(classification))}; '
            f'no longer a state: {sorted(set(classification) - _TERMINAL_STATES)}'
        )

    def test_the_contract_documents_every_blocking_member(self):
        """Each blocking member appears in the contract's normative taxonomy table.

        The contract is the taxonomy's owner, so a member the classifier can emit but
        the contract never names is a member no consumer can be expected to handle.
        """
        table = _CONTRACT_DOC.read_text(encoding='utf-8')
        for state in sorted(rc._UNPROVEN_STATES):
            assert f'`{state}`' in table, (
                f'{state} blocks the merge but is undocumented in the contract'
            )

    def test_the_non_option_population_is_non_empty(self):
        """The members for which a wait CANNOT work — non-empty, so nothing is vacuous.

        These are D0's finding: every one of them is a state where offering "wait" is
        an action guaranteed not to work. ``refused_structural`` is the member this
        plan gives its own remedy set; the others are recorded so the population is
        complete rather than convenient.
        """
        non_options = {s for s, ok in _AWAIT_CAN_EVER_SUCCEED.items() if not ok}
        assert non_options, 'no member classified await-cannot-succeed — sweep is vacuous'
        assert rc.STATE_REFUSED_STRUCTURAL in non_options

    def test_a_blocking_member_that_no_action_and_no_wait_can_clear_is_operator_only(self):
        """Every member that is neither passable nor awaitable exits by a RULING.

        Stated over the whole population rather than for one member. This is what makes
        the merge-authorization surface load-bearing rather than optional: for these
        states there is no plan-side move at all, so without a sanctioned way to record
        an accepted gap they would be genuine deadlocks.
        """
        stuck = {
            state for state in _TERMINAL_STATES
            if not _PASSABLE_BY_PLAN_ACTION[state]
            and not _AWAIT_CAN_EVER_SUCCEED[state]
            and state in rc._UNPROVEN_STATES
        }
        assert stuck, 'no operator-only member — the authorization surface would be moot'
        assert rc.STATE_REFUSED_STRUCTURAL in stuck

    def test_a_state_the_plan_can_exit_by_waiting_is_also_passable_by_acting(self):
        """Waiting is an action, so an awaitable state must not be classified unpassable.

        The two classifications above are independent judgements, and this pins the one
        implication that MUST hold between them. Without it a row could be marked
        await-succeeds-but-not-passable, which is incoherent and would silently weaken
        the operator-only set derived above.
        """
        for state in _TERMINAL_STATES:
            if _AWAIT_CAN_EVER_SUCCEED[state] and state in rc._UNPROVEN_STATES:
                assert _PASSABLE_BY_PLAN_ACTION[state] or state in (
                    rc.STATE_REFUSED_UNKNOWN,
                ), (
                    f'{state} is marked await-can-succeed yet not passable by the plan '
                    f'acting — waiting IS an action, so the pair is incoherent'
                )

    def test_structural_is_a_blocking_member(self):
        """It is unproven participation, so it holds the gate exactly as its siblings do.

        The member changes which REMEDY is offered, never whether the merge is gated.
        A structural refusal that stopped blocking would be a fail-open change wearing
        this plan's clothes.
        """
        assert rc.STATE_REFUSED_STRUCTURAL in rc._UNPROVEN_STATES


# ---------------------------------------------------------------------------
# (a) Classification — a size refusal is structural, not temporal, not absent
# ---------------------------------------------------------------------------

class TestSizeRefusalClassifiesStructural:
    """(a) A size-caused refusal resolves to the structural member."""

    def test_size_refusal_is_structural_not_a_rate_refusal(self, plan_context):
        """sourcery declares ``hard_quota``; a SIZE refusal must not read as that.

        Pre-fix this returned ``refused_hard`` — whose interpretation ("not worth
        awaiting; whether the absence is tolerable is a required-vs-optional
        question") names neither the split nor the cap that a size ceiling calls for.
        """
        plan_id = 'struct-size-not-rate'
        plan_context.plan_dir_for(plan_id)
        result = rc.check_completeness(
            plan_id, ['sourcery'],
            refused_bots=['sourcery'],
            refused_causes={'sourcery': 'size'},
        )
        assert _state_of(result, 'sourcery') == rc.STATE_REFUSED_STRUCTURAL
        assert _state_of(result, 'sourcery') != rc.STATE_REFUSED_HARD

    def test_size_refusal_is_not_unexplained_non_participation(self, plan_context):
        """It must not read as ``absent`` — the bot spoke, and said why.

        ``absent`` means the reviewer was asked and never answered, whose remedy is to
        escalate it. A refusing bot answered; rendering that as silence prescribes
        chasing a reviewer that already replied.
        """
        plan_id = 'struct-size-not-absent'
        plan_context.plan_dir_for(plan_id)
        result = rc.check_completeness(
            plan_id, ['sourcery'],
            refused_bots=['sourcery'],
            refused_causes={'sourcery': 'size'},
        )
        assert _state_of(result, 'sourcery') not in (
            rc.STATE_ABSENT,
            rc.STATE_NOT_TRIGGERED,
        )

    def test_cause_dominates_an_awaitable_window_class(self, plan_context):
        """⭐ The load-bearing branch: an ``awaitable_window`` bot refusing on SIZE.

        ``coderabbit`` declares ``awaitable_window``, so reading the class first would
        resolve ``refused_awaitable`` — *worth awaiting* — for a refusal that waiting
        cannot move. This is the pairing that offers a wait for a ceiling, and it is
        latent rather than hypothetical: nothing but this precedence prevents it the
        moment any awaitable-window bot declares a size pattern.
        """
        plan_id = 'struct-cause-dominates'
        plan_context.plan_dir_for(plan_id)
        result = rc.check_completeness(
            plan_id, ['coderabbit'],
            refused_bots=['coderabbit'],
            refused_causes={'coderabbit': 'size'},
        )
        assert _state_of(result, 'coderabbit') == rc.STATE_REFUSED_STRUCTURAL
        assert _state_of(result, 'coderabbit') != rc.STATE_REFUSED_AWAITABLE

    @pytest.mark.parametrize('bot', bot_registry.bot_kinds())
    def test_a_size_refusal_is_structural_for_every_registered_bot(self, bot, plan_context):
        """Swept over the registry, so no bot's class is a special case.

        The population comes from ``bot_kinds()`` and is guarded non-empty below, so a
        bot added or reclassified in a standards doc is covered here automatically.
        """
        plan_id = f'struct-sweep-{bot}'
        plan_context.plan_dir_for(plan_id)
        result = rc.check_completeness(
            plan_id, [bot], refused_bots=[bot], refused_causes={bot: 'size'},
        )
        assert _state_of(result, bot) == rc.STATE_REFUSED_STRUCTURAL

    def test_the_swept_bot_population_is_non_empty(self):
        """Guards the parametrize above: zero cases would report SKIPPED, not failed."""
        assert bot_registry.bot_kinds(), (
            'the registry declared no bot — the per-bot sweep above would generate '
            'zero cases and silently cover nothing'
        )

    def test_a_quota_refusal_keeps_its_awaitability_member(self, plan_context):
        """The discriminator for (a): only ``size`` moves the member.

        Without this the classification test would also pass on a change that made
        EVERY refusal structural, which would destroy the awaitability split the
        earlier work built.
        """
        plan_id = 'struct-quota-untouched'
        plan_context.plan_dir_for(plan_id)
        result = rc.check_completeness(
            plan_id, ['coderabbit'],
            refused_bots=['coderabbit'],
            refused_causes={'coderabbit': 'quota'},
        )
        assert _state_of(result, 'coderabbit') == rc.STATE_REFUSED_AWAITABLE

    def test_no_cause_keeps_its_awaitability_member(self, plan_context):
        """The member is only ever asserted on a POSITIVELY observed size cause.

        A refusal whose cause was never observed must not drift into the structural
        member: that would claim a diff-size ceiling on no evidence, which is the same
        fail-open shape ``refused_unknown`` exists to prevent on the other axis.
        """
        plan_id = 'struct-no-cause'
        plan_context.plan_dir_for(plan_id)
        result = rc.check_completeness(plan_id, ['sourcery'], refused_bots=['sourcery'])
        assert _state_of(result, 'sourcery') == rc.STATE_REFUSED_HARD

    def test_a_structural_refusal_still_blocks_the_quorum(self, plan_context):
        """The remedy changes; the gate does not."""
        plan_id = 'struct-still-blocks'
        plan_context.plan_dir_for(plan_id)
        result = rc.check_completeness(
            plan_id, ['sourcery'], refused_bots=['sourcery'],
            refused_causes={'sourcery': 'size'},
        )
        assert result['participation_complete'] is False
        assert 'sourcery' in result['unproven_bots']

    def test_check_and_deficit_agree_on_the_member(self, plan_context):
        """Both commands read the cause, so neither can name a different member.

        ``deficit`` publishes a per-reviewer ``state`` column. If only ``check``
        consumed the cause, the two commands would report different states for one
        refusal and no reader of the output could adjudicate which was right.
        """
        plan_id = 'struct-both-commands'
        plan_context.plan_dir_for(plan_id)
        kwargs = {
            'refused_bots': ['sourcery'],
            'refused_causes': {'sourcery': 'size'},
        }
        check = rc.check_completeness(plan_id, ['sourcery'], **kwargs)
        deficit = rc.check_deficit(plan_id, ['sourcery'], **kwargs)
        deficit_state = next(
            r['state'] for r in deficit['reviewers'] if r['bot_kind'] == 'sourcery'
        )
        assert deficit_state == _state_of(check, 'sourcery') == rc.STATE_REFUSED_STRUCTURAL

    def test_the_summary_distinguishes_structural_from_temporal(self, plan_context):
        """``display_detail`` must not render a size refusal as a bare "1 refused".

        The compact summary exists to stop two different situations sharing one
        string. Folding the structural member into the ``refused`` bucket would
        re-create exactly that collapse for the one member whose remedy differs most.
        """
        plan_id = 'struct-summary'
        plan_context.plan_dir_for(plan_id)
        structural = rc.check_completeness(
            plan_id, ['sourcery'], refused_bots=['sourcery'],
            refused_causes={'sourcery': 'size'},
        )
        temporal = rc.check_completeness(
            plan_id, ['sourcery'], refused_bots=['sourcery'],
            refused_causes={'sourcery': 'quota'},
        )
        assert structural['review_state_summary'] != temporal['review_state_summary']
        assert 'structural' in structural['review_state_summary']


# ---------------------------------------------------------------------------
# (b) No await is offered on the structural branch
# ---------------------------------------------------------------------------

#: Phrasings that offer a WAIT as an operator option. Matched case-insensitively
#: against the rendered remedy text.
#:
#: Covers the plan's own list of EQUIVALENTS, not just the literal "wait": a remedy set
#: that swapped "Wait another 3600s" for "Retry later" or "Back off and try again" would
#: reproduce the non-option under a different name, and a regex that only knew the one
#: spelling would report clean on it.
_WAIT_OFFER = re.compile(
    r'"?\s*wait\s+(another|for|until)\b'
    r'|\bawait\s+(the\s+)?(window|reset|limit)\b'
    r'|\bretry\s+(later|in\b|after\b)'
    r'|\btry\s+again\b'
    r'|\bback\s*off\b',
    re.IGNORECASE,
)


def _section(doc: str, heading_pattern: str) -> str:
    """Return the body of the first section whose heading matches, to its next peer."""
    match = re.search(
        rf'^(?P<hashes>#{{2,6}})\s*{heading_pattern}.*?$(?P<body>.*?)(?=^#{{1,6}}\s)',
        doc,
        re.DOTALL | re.MULTILINE,
    )
    assert match, f'no section matching {heading_pattern!r}'
    return str(match.group('body'))


class TestNoAwaitOnTheStructuralBranch:
    """(b) The case that separates this from a relabelling exercise.

    Asserted against the REAL document text, because the defect was never in prose
    describing the remedy set — it was in the rendered option list an operator reads.
    """

    def test_the_structural_escalation_shape_offers_no_wait(self):
        """The ``refusal_structural`` return shape's options contain no wait.

        Pre-fix a size refusal escalated as ``rate_window_not_awaitable``, whose
        ``prompt_options[]`` lead with "Wait another {review_rate_window_timeout_seconds}s"
        — offered for a refusal the registry itself documents as unmoved by waiting.
        """
        skill = _AR_SKILL.read_text(encoding='utf-8')
        block = re.search(
            r'```toon\n(?P<body>[^`]*?reason: refusal_structural.*?)```',
            skill,
            re.DOTALL,
        )
        assert block, 'the refusal_structural escalate_ask shape is missing from SKILL.md'
        body = block.group('body')
        assert not _WAIT_OFFER.search(body), (
            f'the structural escalation offers a wait, which is the non-option this '
            f'member exists to remove:\n{body}'
        )

    def test_the_structural_shape_carries_no_timeout_budget(self):
        """No ``timeout_seconds``, so no consumer can render a wait from the payload.

        Removing the option while leaving the budget behind would be a half-fix: the
        field is the raw material a consumer builds a wait option out of.
        """
        skill = _AR_SKILL.read_text(encoding='utf-8')
        block = re.search(
            r'```toon\n(?P<body>[^`]*?reason: refusal_structural.*?)```',
            skill,
            re.DOTALL,
        )
        assert block
        assert 'timeout_seconds' not in block.group('body')

    def test_the_structural_shape_offers_the_three_real_remedies(self):
        """Split, accept, and disable-for-this-PR — the contract's remedy set, rendered.

        Asserting the ABSENCE of a wait alone would pass on an empty option list,
        which would be a worse prompt than the one being replaced.
        """
        skill = _AR_SKILL.read_text(encoding='utf-8')
        block = re.search(
            r'```toon\n(?P<body>[^`]*?reason: refusal_structural.*?)```',
            skill,
            re.DOTALL,
        )
        assert block
        body = block.group('body').lower()
        assert 'split' in body
        assert 'accept' in body
        assert 'disable' in body

    def test_the_recovery_branches_on_cause_before_class(self):
        """Branch 0 is the CAUSE branch and it precedes the class branches.

        Order is the whole mechanism: reading ``rate_limit_class`` first sends an
        ``awaitable_window`` bot's size refusal into the claim-and-await recovery.
        """
        skill = _AR_SKILL.read_text(encoding='utf-8')
        cause_branch = skill.index('#### Branch 0')
        class_branch = skill.index('#### Branch 1')
        awaitable_branch = skill.index('#### Branch 2')
        assert cause_branch < class_branch < awaitable_branch

    def test_the_structural_recovery_branch_neither_awaits_nor_generates(self):
        """Branch 0 claims no window, awaits nothing, and generates no event.

        All three negations asserted separately. An earlier form said
        ``'do NOT await' in branch or 'Do NOT' in branch``, whose second disjunct
        matches any ``Do NOT`` sentence at all — so the test would have passed on a
        branch that forbade something entirely unrelated and awaited freely.
        """
        skill = _AR_SKILL.read_text(encoding='utf-8')
        branch = _section(skill, r'Branch 0')
        lowered = ' '.join(branch.lower().split())
        assert 'do not claim a window' in lowered
        assert 'do not await' in lowered
        assert 'do not generate an event' in lowered

    def test_the_contract_forbids_an_await_on_the_member(self):
        """The taxonomy's own row names the remedy set and excludes awaiting."""
        row = _section(_CONTRACT_DOC.read_text(encoding='utf-8'), r'Failure taxonomy')
        structural = next(
            line for line in row.splitlines()
            if line.startswith('| `refused_structural`')
        )
        assert 'never await' in structural.lower()
        for remedy in ('split', 'accept', 'disable'):
            assert remedy in structural.lower(), f'{remedy} missing from the remedy set'

    def test_the_orchestrator_hook_knows_the_structural_reason(self):
        """⛔ The hook that actually FIRES the prompt must know this reason exists.

        The leaf returns an envelope; `phase-6-finalize` item 7a renders it. A run that
        fixed only the leaf's payload would leave the operator-visible prompt untouched —
        the non-option surviving one hop downstream of every file the fix edited. That is
        not hypothetical: item 7a enumerated exactly four reasons and hard-coded "the
        same three options" for all of them, so a `refusal_structural` envelope arrived
        as an unknown fifth reason whose three real remedies mapped to no branch at all.
        """
        hook = _FINALIZE_SKILL.read_text(encoding='utf-8')
        assert 'refusal_structural' in hook, (
            'phase-6-finalize item 7a does not name refusal_structural — the prompt the '
            'operator actually sees is rendered here, so the fix is incomplete without it'
        )

    def test_the_orchestrator_hook_does_not_offer_a_wait_for_the_structural_reason(self):
        """Its branch table must carry no wait, under any of the equivalent spellings.

        Scoped to the structural branch table rather than the whole document: the four
        TEMPORAL reasons legitimately offer "Wait another {timeout_seconds}s", so a
        document-wide sweep would be permanently red and prove nothing.
        """
        hook = _FINALIZE_SKILL.read_text(encoding='utf-8')
        start = hook.index('reason: refusal_structural` — its OWN branch table')
        table = hook[start:start + 2600]
        assert not _WAIT_OFFER.search(table), (
            f'the orchestrator hook offers a wait on the structural branch — the very '
            f'non-option this member exists to remove:\n{table[:600]}'
        )

    def test_the_orchestrator_hook_offers_the_three_real_remedies(self):
        """Asserting only the absence of a wait would pass on an empty branch table."""
        hook = _FINALIZE_SKILL.read_text(encoding='utf-8')
        start = hook.index('reason: refusal_structural` — its OWN branch table')
        table = hook[start:start + 2600].lower()
        assert 'split' in table
        assert 'accept the coverage gap' in table
        assert 'disable this reviewer' in table

    def test_the_orchestrator_hook_names_both_audit_figures(self):
        """The operator accepting a gap must be shown the cap AND the measured size."""
        hook = _FINALIZE_SKILL.read_text(encoding='utf-8')
        start = hook.index('reason: refusal_structural` — its OWN branch table')
        table = hook[start:start + 2600]
        assert 'cap' in table
        assert 'measured_diff_size' in table

    def test_the_barrier_names_the_structural_remedy(self):
        """branch-cleanup renders the member's remedy, not "the bot did not review".

        The barrier is the site that raises the operator prompt, so it is where a
        collapsed remedy set does the most damage. Scanned over EVERY mention rather
        than the first: the document names the member at several call sites, and
        anchoring on whichever happens to come first would make this pass or fail on
        paragraph order rather than on content.
        """
        barrier = _BRANCH_CLEANUP.read_text(encoding='utf-8').lower()
        mentions = [m.start() for m in re.finditer('refused_structural', barrier)]
        assert mentions, 'branch-cleanup never mentions the structural member'
        assert any(
            'split' in barrier[start:start + 1500]
            and 'cap' in barrier[start:start + 1500]
            for start in mentions
        ), 'no mention of the structural member names both its remedy and its cap'


# ---------------------------------------------------------------------------
# (c) The finding carries the cap
# ---------------------------------------------------------------------------

class TestTheCapIsRecorded:
    """(c) The stated ceiling travels with the finding, and an absent one stays absent."""

    def test_the_cap_is_reported_alongside_the_cause(self, plan_context):
        plan_id = 'struct-cap-reported'
        plan_context.plan_dir_for(plan_id)
        result = rc.check_completeness(
            plan_id, ['sourcery'],
            refused_bots=['sourcery'],
            refused_causes={'sourcery': 'size'},
            refusal_size_caps={'sourcery': '4242 diff characters'},
        )
        assert result['refusal_causes'] == [
            {'bot_kind': 'sourcery', 'cause': 'size', 'cap': '4242 diff characters'}
        ]

    def test_an_unstated_cap_reads_unknown_and_is_never_defaulted(self, plan_context):
        """A cap nobody observed must not be invented.

        The gap's whole value is being reconcilable against the measured diff size; a
        defaulted figure would make it look audited against a number that was made up
        here.
        """
        plan_id = 'struct-cap-unknown'
        plan_context.plan_dir_for(plan_id)
        result = rc.check_completeness(
            plan_id, ['sourcery'],
            refused_bots=['sourcery'],
            refused_causes={'sourcery': 'size'},
        )
        assert result['refusal_causes'][0]['cap'] == ''

    def test_the_cli_renders_the_cap_column(self, plan_context):
        plan_id = 'struct-cap-cli'
        plan_context.plan_dir_for(plan_id)
        result = run_script(
            SCRIPT_PATH, 'check', '--plan-id', plan_id,
            '--required-bots', 'sourcery', '--refused-bots', 'sourcery',
            '--refused-causes', 'sourcery:size',
            '--refusal-size-caps', 'sourcery:4242 diff characters',
        )
        assert result.returncode == 0
        assert 'refusal_causes[1]{bot_kind,cause,cap}:' in result.stdout
        assert 'sourcery,size,4242 diff characters' in result.stdout

    def test_the_cli_renders_an_unstated_cap_as_the_word_unknown(self, plan_context):
        """An empty column would be indistinguishable from a parse slip."""
        plan_id = 'struct-cap-cli-unknown'
        plan_context.plan_dir_for(plan_id)
        result = run_script(
            SCRIPT_PATH, 'check', '--plan-id', plan_id,
            '--required-bots', 'sourcery', '--refused-bots', 'sourcery',
            '--refused-causes', 'sourcery:size',
        )
        assert result.returncode == 0
        assert 'sourcery,size,unknown' in result.stdout

    def test_a_malformed_cap_token_is_an_unknown_verdict(self, plan_context):
        """Shape violations are rejected loudly, exactly as the sibling pair-form flags."""
        plan_id = 'struct-cap-malformed'
        plan_context.plan_dir_for(plan_id)
        result = run_script(
            SCRIPT_PATH, 'check', '--plan-id', plan_id,
            '--required-bots', 'sourcery', '--refusal-size-caps', 'sourcery',
        )
        assert result.returncode == 1
        assert 'participation_complete' not in result.stdout

    def test_a_cap_containing_a_colon_survives_the_parse(self):
        """Only the FIRST colon splits, so a value carrying one is not truncated."""
        assert rc.parse_causes('sourcery:1:2') == {'sourcery': '1:2'}

    def test_the_cap_flag_reads_bare_as_empty(self, plan_context):
        plan_id = 'struct-cap-bare'
        plan_context.plan_dir_for(plan_id)
        result = run_script(
            SCRIPT_PATH, 'check', '--plan-id', plan_id,
            '--required-bots', 'sourcery', '--refused-bots', 'sourcery',
            '--refused-causes', 'sourcery:size', '--refusal-size-caps',
        )
        assert result.returncode == 0
        assert 'sourcery,size,unknown' in result.stdout

    def test_the_measured_diff_size_is_reported_beside_the_cap(self, plan_context):
        """The OTHER half of an auditable gap.

        A cap on its own says what the ceiling was; without the size that hit it the
        reader can only take the refusal's word for how far over the PR actually was.
        """
        plan_id = 'struct-measured'
        plan_context.plan_dir_for(plan_id)
        result = rc.check_completeness(
            plan_id, ['sourcery'],
            refused_bots=['sourcery'],
            refused_causes={'sourcery': 'size'},
            refusal_size_caps={'sourcery': '4242 diff characters'},
            measured_diff_size='9001 changed lines',
        )
        assert result['measured_diff_size'] == '9001 changed lines'
        assert result['refusal_causes'][0]['cap'] == '4242 diff characters'

    def test_the_cli_emits_the_measured_diff_size(self, plan_context):
        plan_id = 'struct-measured-cli'
        plan_context.plan_dir_for(plan_id)
        result = run_script(
            SCRIPT_PATH, 'check', '--plan-id', plan_id,
            '--required-bots', 'sourcery', '--refused-bots', 'sourcery',
            '--refused-causes', 'sourcery:size',
            '--refusal-size-caps', 'sourcery:4242 diff characters',
            '--measured-diff-size', '9001 changed lines',
        )
        assert result.returncode == 0
        assert 'measured_diff_size: 9001 changed lines' in result.stdout
        assert 'sourcery,size,4242 diff characters' in result.stdout

    def test_an_unmeasured_diff_emits_no_size_line(self, plan_context):
        """Absent rather than zero: ``0`` would read as an empty diff being refused."""
        plan_id = 'struct-unmeasured'
        plan_context.plan_dir_for(plan_id)
        result = run_script(
            SCRIPT_PATH, 'check', '--plan-id', plan_id,
            '--required-bots', 'sourcery', '--refused-bots', 'sourcery',
            '--refused-causes', 'sourcery:size',
        )
        assert result.returncode == 0
        assert 'measured_diff_size' not in result.stdout

    def test_a_cap_arriving_without_its_cause_still_resolves_structural(self, plan_context):
        """⛔ Fail-CLOSED recovery: a lost cause overlay must not un-structure the member.

        The cause and the cap cross the CLI as two SEPARATE flags, and the barrier's
        contract lets either default to empty independently when a producer field is
        absent or malformed. A cap is only ever produced for a size refusal, so a cap
        with no cause means the cause was lost in transport — and without recovery the
        bot silently falls back to a TEMPORAL member and is offered a wait for a
        diff-size ceiling, which is the exact non-option this member removes.
        """
        plan_id = 'struct-cap-without-cause'
        plan_context.plan_dir_for(plan_id)
        result = rc.check_completeness(
            plan_id, ['sourcery'],
            refused_bots=['sourcery'],
            refusal_size_caps={'sourcery': '4242 diff characters'},
        )
        assert _state_of(result, 'sourcery') == rc.STATE_REFUSED_STRUCTURAL
        assert result['refusal_causes'] == [
            {'bot_kind': 'sourcery', 'cause': 'size', 'cap': '4242 diff characters'}
        ]

    def test_a_cause_without_a_cap_is_never_inferred_backwards(self, plan_context):
        """The recovery is one-directional. A cause with no cap is an ordinary unknown.

        Inferring in the other direction would invent a cap, which is precisely what the
        unknown-cap discipline exists to prevent.
        """
        plan_id = 'struct-cause-without-cap'
        plan_context.plan_dir_for(plan_id)
        result = rc.check_completeness(
            plan_id, ['sourcery'],
            refused_bots=['sourcery'],
            refused_causes={'sourcery': 'quota'},
        )
        assert _state_of(result, 'sourcery') == rc.STATE_REFUSED_HARD
        assert result['refusal_causes'][0]['cap'] == ''

    def test_the_measurement_carries_its_unit(self, plan_context):
        """The unit rides INSIDE the value, because it is not the reviewer's unit.

        A bare number next to a cap in ``diff characters`` invites a reader to treat
        an order-of-magnitude comparison as an exact reconciliation.
        """
        plan_id = 'struct-measured-unit'
        plan_context.plan_dir_for(plan_id)
        result = rc.check_completeness(
            plan_id, ['sourcery'],
            refused_bots=['sourcery'],
            refused_causes={'sourcery': 'size'},
            measured_diff_size='9001 changed lines',
        )
        assert not result['measured_diff_size'].strip().isdigit()


# ---------------------------------------------------------------------------
# Advance disclosure — the ceiling is knowable before the review is requested
# ---------------------------------------------------------------------------

class TestAdvanceDisclosure:
    """A structural ceiling is a property of the REVIEWER, so it is disclosable early.

    Every other verdict here is computed from an observed refusal, so the gap is
    otherwise discovered only at the merge gate. The exclusion also recurs by size
    rather than by chance — the ceiling is fixed, so every plan over it is excluded,
    predictably and forever.
    """

    def test_the_disclosure_covers_the_whole_registry(self):
        rows = rc.declared_size_caps()
        assert [r['bot_kind'] for r in rows] == bot_registry.bot_kinds()
        assert rows, 'the disclosure is vacuous over an empty registry'

    def test_a_bot_declaring_a_size_pattern_is_disclosed_as_capped(self):
        """DERIVED from ``refusal_size_patterns``, so it cannot disagree with the classifier.

        Asserted over the registry rather than for a named bot, so the property holds
        for whatever population the standards docs declare.
        """
        rows = {r['bot_kind']: r for r in rc.declared_size_caps()}
        for bot in bot_registry.bot_kinds():
            expected = bool(bot_registry.refusal_size_patterns(bot))
            assert rows[bot]['structural_cap'] is expected

    def test_at_least_one_reviewer_declares_a_structural_cap(self):
        """Guards the check above from passing over an all-false population."""
        assert any(r['structural_cap'] for r in rc.declared_size_caps()), (
            'no registered reviewer declares a size ceiling — the disclosure would '
            'be uniformly false and could not distinguish a working derivation from '
            'a broken one'
        )

    def test_declaring_a_ceiling_is_reported_apart_from_reading_its_value(self):
        """The two facts are independent and must not be collapsed.

        A reviewer can have a ceiling nobody has taught the registry to read;
        collapsing them would let "declares a ceiling" be misread as "its value is
        recoverable".
        """
        for row in rc.declared_size_caps():
            extractable = bool(bot_registry.refusal_size_cap_patterns(row['bot_kind']))
            assert row['cap_extractable'] is extractable

    def test_the_cli_emits_the_disclosure(self):
        result = run_script(SCRIPT_PATH, 'size-caps')
        assert result.returncode == 0
        assert 'size_capped_reviewers[' in result.stdout
        assert '{bot_kind,structural_cap,cap_extractable}' in result.stdout

    def test_the_disclosure_needs_no_plan(self):
        """It reads the registry, which is what makes it answerable before a PR exists."""
        result = run_script(SCRIPT_PATH, 'size-caps')
        assert result.returncode == 0
        assert 'status: success' in result.stdout


# ---------------------------------------------------------------------------
# The producer-side extraction seam
# ---------------------------------------------------------------------------

class TestCapExtraction:
    """``_github_pr.refusal_size_cap`` — the seam that READS the cap off the notice.

    Covered directly rather than only through the classifier, because everything
    downstream is a passthrough: if this returns the wrong string, every consumer
    faithfully reports the wrong cap and no other test notices.

    ⛔ Every body here is SYNTHETIC. The real provider's figure is its own to change,
    so pinning it would make this suite assert a number nobody re-derived — the plan
    labels that figure a lead, not a fact.
    """

    @staticmethod
    def _seam():
        gh_scripts = get_script_path(
            'plan-marshall', 'workflow-integration-github', 'github_pr.py'
        ).parent
        if str(gh_scripts) not in sys.path:
            sys.path.insert(0, str(gh_scripts))
        import github_ops  # noqa: F401 — import first; _github_pr closes a cycle with it
        import _github_pr

        return _github_pr

    def test_the_stated_cap_is_read_off_the_notice(self):
        seam = self._seam()
        body = 'your pull request is larger than the review limit of 4242 diff characters.'
        assert seam.refusal_size_cap(body, 'sourcery') == '4242 diff characters'

    def test_a_thousands_separator_is_stripped(self):
        """The value crosses a COMMA-separated CLI boundary, where a comma splits it.

        Stripping also leaves a figure that compares directly against a measured size.
        """
        seam = self._seam()
        body = 'your pull request is larger than the review limit of 4,242 diff characters.'
        assert seam.refusal_size_cap(body, 'sourcery') == '4242 diff characters'
        assert ',' not in seam.refusal_size_cap(body, 'sourcery')

    def test_a_notice_stating_no_figure_yields_unknown(self):
        seam = self._seam()
        body = 'your pull request is larger than the review limit of our plan.'
        assert seam.refusal_size_cap(body, 'sourcery') == ''

    def test_a_quota_notice_yields_no_cap(self):
        """A rate/budget notice names no DIFF ceiling, so reading one would invent it."""
        seam = self._seam()
        body = 'you have reached your weekly rate limit of 500000 diff characters.'
        assert seam.refusal_size_cap(body, 'sourcery') == ''

    def test_a_bot_declaring_no_cap_pattern_yields_unknown(self):
        """Fail-closed: no declared pattern can never produce a confident figure."""
        seam = self._seam()
        for bot in bot_registry.bot_kinds():
            if not bot_registry.refusal_size_cap_patterns(bot):
                assert seam.refusal_size_cap('review limit of 10 things', bot) == ''

    def test_an_empty_body_or_missing_bot_yields_unknown(self):
        seam = self._seam()
        assert seam.refusal_size_cap('', 'sourcery') == ''
        assert seam.refusal_size_cap('review limit of 10 things', None) == ''

    def test_a_malformed_registry_pattern_is_skipped_not_raised(self, monkeypatch):
        """A bad registry edit must not break the producer's return path."""
        seam = self._seam()
        monkeypatch.setattr(
            seam.bot_registry, 'refusal_size_cap_patterns', lambda _bot: ['([unclosed']
        )
        assert seam.refusal_size_cap('review limit of 10 things', 'sourcery') == ''

    def test_a_non_participating_group_does_not_crash_the_producer(self, monkeypatch):
        """⛔ A pattern whose first group sits in an unmatched branch must not raise.

        ``match.groups()`` is TRUTHY for a one-tuple holding ``None``, so a pattern like
        ``limit of (?:[0-9]+)|(other)`` matches, reports groups, and yields ``None`` —
        and ``None.strip()`` raises an ``AttributeError`` straight out of
        ``cmd_fetch_findings``, killing the producer's whole return path. The
        ``re.error`` guard above does NOT cover this: that pattern compiles fine.

        This is the exact failure the function's docstring promises cannot happen, so it
        is pinned rather than left to the docstring.
        """
        seam = self._seam()
        monkeypatch.setattr(
            seam.bot_registry,
            'refusal_size_cap_patterns',
            lambda _bot: [r'review limit of (?:[0-9]+)|(nevermatches)'],
        )
        # Falls back to the whole match rather than raising.
        assert seam.refusal_size_cap('review limit of 4242 chars', 'sourcery') == (
            'review limit of 4242'
        )

    def test_a_pattern_capturing_only_whitespace_yields_unknown(self, monkeypatch):
        """An empty capture is no figure, not an empty-string cap."""
        seam = self._seam()
        monkeypatch.setattr(
            seam.bot_registry, 'refusal_size_cap_patterns', lambda _bot: [r'limit of(\s*)']
        )
        assert seam.refusal_size_cap('review limit of 4242 chars', 'sourcery') == ''


class TestDiffMeasurement:
    """``_github_pr.measure_diff_size`` — the other half, and its UNKNOWN discipline."""

    @staticmethod
    def _seam():
        gh_scripts = get_script_path(
            'plan-marshall', 'workflow-integration-github', 'github_pr.py'
        ).parent
        if str(gh_scripts) not in sys.path:
            sys.path.insert(0, str(gh_scripts))
        import github_ops  # noqa: F401
        import _github_pr

        return _github_pr

    def test_the_measurement_sums_additions_and_deletions_with_its_unit(self, monkeypatch):
        seam = self._seam()
        monkeypatch.setattr(
            seam.github_ops, 'run_gh',
            lambda *_a, **_k: (0, '{"additions": 900, "deletions": 340}', ''),
        )
        assert seam.measure_diff_size(7) == '1240 changed lines'

    @pytest.mark.parametrize(
        'returncode, stdout',
        [
            (1, ''),                                   # the read failed
            (0, ''),                                   # empty output
            (0, 'not json'),                           # unparseable
            (0, '[]'),                                 # wrong shape
            (0, '{"additions": 900}'),                 # a field missing
            (0, '{"additions": "900", "deletions": 1}'),  # a field non-numeric
        ],
    )
    def test_an_unusable_read_is_unknown_never_zero(self, monkeypatch, returncode, stdout):
        """⛔ ``0`` would read as an empty diff refused for being too big.

        That is a claim the function has no evidence for, and it would make an
        unmeasurable gap look audited against a number nobody observed.
        """
        seam = self._seam()
        monkeypatch.setattr(
            seam.github_ops, 'run_gh', lambda *_a, **_k: (returncode, stdout, 'err')
        )
        assert seam.measure_diff_size(7) == ''

#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
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

import argparse
import ast
import importlib
import inspect
import re
import textwrap

import bot_registry
import pytest

from conftest import get_script_path, load_script_module, run_script

# ``register=False``: only the returned module is needed, and a sibling suite
# imports ``review_completeness`` plainly. Registering under that name would put two
# copies in play, reachable by different routes and differing by collection order.
rc = load_script_module(
    'plan-marshall', 'automatic-review', 'review_completeness.py', register=False
)

SCRIPT_PATH = get_script_path('plan-marshall', 'automatic-review', 'review_completeness.py')
SCRIPTS_DIR = SCRIPT_PATH.parent

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
    # The remedy is an edit to the reviewer CONFIGURATION — the third case this
    # classification's own docstring names as outside the plan's reach. No plan-side
    # move exists at all: the token names no reviewer, so there is nothing to
    # re-trigger, generate an event for, or await.
    rc.STATE_UNREGISTERED_KIND: False,
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
    # No reviewer answers to this NAME, and none ever could — participation is keyed
    # by a bot_kind derived from an author login, so a token outside that codomain
    # can never be credited however long the wait. This is the strongest ``False`` on
    # the axis: the others describe a reviewer that will not answer NOW, this one a
    # reviewer that does not exist.
    rc.STATE_UNREGISTERED_KIND: False,
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

    @pytest.mark.parametrize(
        'case, kwargs, expected_attr',
        [
            # The ordinary path: both commands are handed the cause.
            ('cause', {'refused_causes': {'sourcery': 'size'}}, 'STATE_REFUSED_STRUCTURAL'),
            # ⭐ The path that ACTUALLY tests the invariant: the cause was lost in
            # transport and only the cap survived, so the member depends entirely on the
            # fail-closed recovery. When that recovery lived on ``check`` alone, the two
            # commands disagreed here — and the ordinary case above could not see it,
            # because it hands both commands the cause directly.
            (
                'cap-only',
                {'refusal_size_caps': {'sourcery': '4242 diff characters'}},
                'STATE_REFUSED_STRUCTURAL',
            ),
            # And the discriminator: no overlay at all keeps the temporal member on BOTH.
            ('neither', {}, 'STATE_REFUSED_HARD'),
        ],
    )
    def test_check_and_deficit_agree_on_the_member(
        self, plan_context, case, kwargs, expected_attr
    ):
        """Both commands apply the SAME cause handling, so neither names a different member.

        ``deficit`` publishes a per-reviewer ``state`` column. If only ``check``
        consumed the cause — or only ``check`` ran the cap-recovery — the two commands
        would report different states for one refusal and no reader of the output could
        adjudicate which was right.
        """
        plan_id = f'struct-both-commands-{case}'
        plan_context.plan_dir_for(plan_id)
        shared = {'refused_bots': ['sourcery'], **kwargs}
        check = rc.check_completeness(plan_id, ['sourcery'], **shared)
        deficit = rc.check_deficit(plan_id, ['sourcery'], **shared)
        deficit_state = next(
            r['state'] for r in deficit['reviewers'] if r['bot_kind'] == 'sourcery'
        )
        assert deficit_state == _state_of(check, 'sourcery') == getattr(rc, expected_attr)

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


def _hook_structural_table() -> str:
    """The dispatcher's structural branch table, sliced to the NEXT heading.

    Bounded by the document's own structure rather than a character count. A fixed
    window silently stops covering whatever is appended past its end — so a wait added
    at the bottom of a grown table would go unchecked while the sweep still read clean.
    ``index`` raises when the anchor moves, which fails loudly rather than passing.
    """
    # Annotated because ``get_script_path`` is untyped, so the Path — and everything
    # derived from it, including ``read_text`` — propagates as ``Any``. Without the
    # annotation this helper returns ``Any`` from a ``-> str`` signature, which
    # ``./pw test-compile`` rejects and neither the quality gate nor a pytest run sees.
    hook: str = _FINALIZE_SKILL.read_text(encoding='utf-8')
    start = hook.index('reason: refusal_structural` — its OWN branch table')
    nxt = re.search(r'^\s{0,4}#{2,6}\s', hook[start:], re.MULTILINE)
    return hook[start:start + nxt.start()] if nxt else hook[start:]


def _barrier_structural_prompt() -> str:
    """The barrier's STRUCTURAL ``AskUserQuestion`` block, sliced to its own fence.

    Bounded by the fence rather than a character count, so the assertions cannot go
    quietly out of scope when the block grows — a fixed window silently stops covering
    whatever was appended past its end.
    """
    barrier: str = _BRANCH_CLEANUP.read_text(encoding='utf-8')
    anchor = barrier.index('Branch Cleanup — Structural review refusal')
    fence_start = barrier.rindex('```text', 0, anchor)
    fence_end = barrier.index('```', anchor)
    return barrier[fence_start:fence_end]


def _to_next_heading(text: str, start: int) -> str:
    """*text* from ``start`` to the next markdown heading, or to its end.

    THE structural bound, shared by every reader here that needs one. A character
    count is the alternative and it is the wrong one: a fixed window silently stops
    covering whatever is appended past its end, which is exactly how content added
    to a grown section escapes a sweep that still reports clean — the same reason
    ``_remedy_guard_text`` below bounds on a paragraph break rather than a length.
    """
    rest = text[start:]
    nxt = re.search(r'^#{1,6}\s', rest, re.MULTILINE)
    return rest[: nxt.start()] if nxt else rest


def _barrier_structural_section() -> str:
    """The barrier's structural-refusal SECTION, anchored on its heading.

    Anchored on the ``#####`` heading rather than the bare phrase, and sliced to the
    next heading rather than a character count. The phrase alone is not unique — the
    merge-authorization roster cross-references this section by name, and that
    reference appears EARLIER in the file, so a phrase-anchored slice silently reads
    the roster instead of the section it meant to check.
    """
    barrier: str = _BRANCH_CLEANUP.read_text(encoding='utf-8')
    match = re.search(
        r'^#{3,6}\s.*Structural refusal — RE-TRIAGE is not a remedy.*$',
        barrier,
        re.MULTILINE,
    )
    assert match, 'the barrier declares no structural-refusal section'
    return _to_next_heading(barrier, match.end())


def _barrier_structural_commands() -> str:
    """Only the fenced COMMAND blocks of the structural section, prose excluded.

    The section deliberately *names* the things it forbids ("Do NOT settle this with
    Branch C", "every remedy is an operator action (`merge-authorization grant`, …)"),
    so a substring search over the whole section matches the warning as readily as a
    violation. Scoping to the fences is what separates what the document INSTRUCTS
    from what it merely mentions — the same distinction `_barrier_structural_options`
    draws between a pickable option and its explanation.
    """
    return '\n'.join(_barrier_structural_section().split('```')[1::2])


def _barrier_structural_options() -> str:
    """Just the ``options:`` list of that prompt — what the operator can actually PICK.

    Separated from the surrounding ``description:`` on purpose. The description
    legitimately *explains* why re-triage is not offered, so a sweep over the whole
    block trips on the explanation and reports a defect that is really a correct
    warning. What must be free of a futile remedy is the list of selectable options.
    """
    block = _barrier_structural_prompt()
    return block[block.index('options:'):]


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
        table = _hook_structural_table()
        assert not _WAIT_OFFER.search(table), (
            f'the orchestrator hook offers a wait on the structural branch — the very '
            f'non-option this member exists to remove:\n{table[:600]}'
        )

    def test_the_orchestrator_hook_offers_the_three_real_remedies(self):
        """Asserting only the absence of a wait would pass on an empty branch table."""
        table = _hook_structural_table().lower()
        assert 'split' in table
        assert 'accept the coverage gap' in table
        assert 'disable this reviewer' in table

    def test_the_orchestrator_hook_names_both_audit_figures(self):
        """The operator accepting a gap must be shown the cap AND the measured size.

        Matched as interpolation placeholders, not bare words: ``cap`` alone appears in
        almost any prose about a ceiling, so asserting the substring would pass on a
        table that merely discussed caps without ever rendering one.
        """
        table = _hook_structural_table()
        assert '`cap`' in table or '{cap}' in table
        assert 'measured_diff_size' in table

    def test_the_orchestrator_hook_does_not_promise_settling_it_cannot_deliver(self):
        """The disable-reviewer branch must name the scoping that makes it terminate.

        The branch re-dispatches the leaf. That settles ONLY because the recovery is
        scoped to required bots — without that scoping the leaf re-detects the same
        refusal and re-escalates, so the operator choosing the one remedy that resolves
        the block loops on it forever. An earlier draft asserted the settling outcome
        with no mechanism behind it.
        """
        table = _hook_structural_table().lower()
        assert 'required_bots' in table, (
            'the disable-reviewer branch does not name the required-bots scoping its '
            'settling claim depends on'
        )
        recovery = _AR_SKILL.read_text(encoding='utf-8')
        assert 'Scope the recovery to REQUIRED bots' in recovery

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

    def test_the_barriers_own_prompt_offers_the_structural_remedies(self):
        """⛔ The barrier renders a REAL option list, and it is the one that fires by default.

        This is the surface round 1 did NOT reach. `review_rate_window_await` defaults
        to `false`, so the leaf's Branch 0 never fires on a default configuration and
        the dispatcher's structural branch table is unreachable — the prompt an operator
        actually sees is this one. A test that only greps the barrier's PROSE (as the
        sibling above does) passes while its rendered `options:` block still offers
        re-triage.
        """
        options = _barrier_structural_options().lower()
        assert 'split the pr' in options
        assert 'accept the coverage gap' in options
        assert 'disable this reviewer' in options

    def test_the_barriers_own_prompt_does_not_offer_a_retriage_remedy(self):
        """⛔ "Re-triage now" re-requests the review, and for this member that cannot work.

        A re-triage asks the reviewer again against a diff of the SAME SIZE, so it
        re-refuses and the barrier re-reaches this verdict — an action the operator can
        take that is guaranteed not to work, the plan's own definition of a non-option.
        It escapes a wait-worded sweep entirely because it is spelled "re-triage".

        ⚠ Two senses of "loop-back" must stay apart here, which is why this test asserts
        over the OPTION LIST only. The re-triage **remedy** is what must be absent; the
        `loop_back` control-flow **record** is what the branch legitimately emits, and a
        check written against the word rather than the sense would forbid it.
        """
        options = _barrier_structural_options()
        lowered = options.lower()
        assert not _WAIT_OFFER.search(options), (
            f'the barrier prompt offers a wait:\n{options}'
        )
        assert 're-triage' not in lowered, (
            'the structural prompt offers "Re-triage now" — re-requesting a review that '
            'is futile against an unchanged diff'
        )
        assert 'loop back' not in lowered, (
            'the structural OPTION LIST offers a loop-back as a remedy. The branch does '
            'emit a loop_back RECORD, which is correct — but an operator must not be '
            'handed re-running the review as a choice'
        )

    def test_the_barriers_own_prompt_quantifies_the_gap(self):
        """Both audit figures are shown, so an accepted gap is a quantified one."""
        block = _barrier_structural_prompt()
        assert '{cap}' in block
        assert '{measured_diff_size}' in block

    def test_the_cap_placeholder_has_a_stated_derivation(self):
        """⛔ The placeholder APPEARING is not the same as the reader knowing its value.

        `{cap}` is interpolated into an operator prompt and into a `--granted-over`
        string that becomes a durable authorization record, so a reader who cannot
        resolve it writes an unauditable record. Asserting only that the token
        appears — which the sibling test above does, correctly, for a different
        property — would pass on a document that interpolates a value it never says
        how to obtain. This asserts the DERIVATION exists.

        Its three load-bearing parts are checked separately because each fixes a
        different way the block could be present but useless: the SOURCE FIELD (and
        which of the two spellings it is), the multi-bot RENDERING, and the
        unknown-cap fallback.
        """
        barrier = _BRANCH_CLEANUP.read_text(encoding='utf-8')
        anchor = barrier.index('{structural_bots} = every bot in')
        # The derivation sits with its sibling, so the read is bounded by the
        # document's own next heading rather than by a character count — a fixed
        # window silently stops covering whatever is appended past its end. The
        # section legitimately renders `{cap}` again further down (the operator
        # prompt and the decision message both quote it), so the assertion that
        # actually pins the derivation is the pair-rendering one below, not the
        # bare-placeholder one.
        block = _to_next_heading(barrier, anchor)

        assert '{cap}' in block, 'the {cap} derivation is absent from the derivation block'
        # The SOURCE, named — and named as the CONSUMER's spelling. The producer
        # emits refused_size_caps[]; reading that name off the check return finds
        # nothing and renders every cap as absent.
        assert 'refusal_causes[]' in block, (
            'the derivation does not name the payload field it reads'
        )
        # The multi-bot RENDERING, decided rather than left to the renderer.
        assert '{bot_kind}:{cap} pairs' in block, (
            'the derivation does not state the multi-bot rendering as a pair list'
        )
        # The unknown fallback — a blank or a default would make an unquantified
        # gap read as a quantified one.
        assert 'unknown' in block, (
            'the derivation does not say what a bot stating no ceiling renders as'
        )

    def test_the_cap_derivation_disambiguates_the_two_spellings(self):
        """The producer's field name must be named as the WRONG one to read here.

        `refused_size_caps[]` and `refusal_causes[]` carry the same information at
        two seams. Naming only the right one leaves a reader who already knows the
        producer's spelling with no reason to doubt it, and the failure is silent:
        an absent field renders as an empty cap, so a quantified gap quietly becomes
        an unquantified one rather than erroring.
        """
        barrier = _BRANCH_CLEANUP.read_text(encoding='utf-8')

        assert 'refused_size_caps[]' in barrier and 'refusal_causes[]' in barrier
        # The read instruction names the consumer's spelling among the fields read.
        # Bounded on the document's own next heading rather than a character count,
        # for the same reason as the sibling above: a fixed window stops covering
        # whatever the instruction grows to carry, and says nothing when it does.
        read_instruction = _to_next_heading(
            barrier, barrier.index('Read `participation_complete`')
        )
        assert '`refusal_causes`' in read_instruction, (
            'refusal_causes is not among the fields the step is told to read from the '
            'review_completeness check return, so the {cap} derivation reads a field '
            'nothing instructed the reader to capture'
        )

    def test_the_two_blocked_paths_declare_a_precedence(self):
        """⛔ Both blocks can hold at once, and they mandate OPPOSITE actions.

        A PR with a structural refusal AND an unhandled comment satisfies the
        participation-incomplete path (which forbids the loop-back) and the
        pending-findings path (which mandates it). Before the structural member existed
        the two were behaviourally identical, so the missing precedence was harmless;
        it is now a contradiction, and a reader reaching either section first would act
        on it.
        """
        section = _barrier_structural_section()
        lowered = ' '.join(section.lower().split())
        assert 'precedence' in lowered, (
            'the structural sub-branch states no precedence against the pending-findings '
            'path, which mandates the loop-back it forbids'
        )
        assert '{count} == 0' in section, (
            'the structural disposition does not scope itself to the zero-pending case'
        )

    def test_the_structural_accept_branch_mints_an_authorization(self):
        """An option labelled "record reason" must actually record something.

        The dispatcher's accept branch stamps a step record, but the barrier re-derives
        participation and re-checks authorization at its OWN resolved HEAD — and on the
        default barrier mode it never re-asks. Without a grant minted at the hook, the
        operator selects "Accept the coverage gap" and gets no merge, no second prompt,
        and no record of what they accepted.
        """
        table = _hook_structural_table()
        assert 'merge-authorization grant' in table
        assert '--gap-class review-barrier-gap' in table
        assert '--kind barrier-ask-override' in table

    def test_the_deficit_invocation_block_documents_the_cap_flag(self):
        """The documented `deficit` call must pass the flag that drives the recovery.

        `--refusal-size-caps` is what makes a cap-without-cause resolve structurally. A
        caller following a block that omits it passes the cap to `check` and not to
        `deficit`, reproducing the exact cross-command disagreement the shared flag
        exists to prevent — and plugin-doctor cannot catch it, because it validates
        documented invocations against the parser, not the parser against the docs.
        """
        skill = _AR_SKILL.read_text(encoding='utf-8')
        start = skill.index('### review_completeness — deficit')
        block = skill[start:skill.index('```', skill.index('```bash', start) + 7)]
        assert '--refusal-size-caps' in block

    def test_the_default_path_uses_the_sibling_loop_back_not_a_new_semantic(self):
        """⛔ The default path must NOT settle with a terminal `done` record.

        Branch C is the "declined by user" settle: it lets the FOR loop continue to
        `archive-plan`, archiving the plan with the PR unmerged — and an already-`done`
        `branch-cleanup` is SKIPPED by the resumable re-entry check, so the remedies the
        message names ("grant at the HEAD the next pass will see", "reclassify then
        re-enter") would point at a pass that never runs.

        Two earlier drafts of this branch invented a disposition — first an absent
        record with a HALT, then Branch C — when the document already carried a fitting
        one. The sibling `loop_back` to `6-finalize` neither archives nor invents.
        """
        commands = _barrier_structural_commands()
        assert '--outcome loop_back' in commands
        assert '--loop-back-target 6-finalize' in commands
        assert '--outcome done' not in commands, (
            'the structural default path settles with a terminal done record, which '
            'archives the plan with the PR unmerged and forecloses the remedies its '
            'own message names'
        )

    def test_the_default_path_explains_why_its_loop_back_is_clearable(self):
        """The loop-back must be justified, not merely taken.

        Round 2 correctly found a loop-back here futile — but that loop-back rendered
        "{count} bot comment(s) are still unhandled" with count zero, offered re-triage,
        and named no cap, no size, and no remedy. What makes a loop-back legitimate for
        this member is that it re-runs the AUTHORIZATION check, which an operator
        remedy can clear; the re-review half stays futile and the text must say so.
        """
        section = ' '.join(_barrier_structural_section().split())
        assert 'AUTHORIZATION' in section or 'authorization' in section
        assert 'max_iterations' in section, (
            'the branch does not state what bounds an unattended run'
        )

    def test_the_default_paths_remedies_are_complete_invocations(self):
        """A remedy an operator cannot copy-run is no remedy.

        This decision-log is the ONLY operator-facing surface on the default
        configuration. An earlier draft named the verbs but omitted required arguments
        (`--plan-id`, `--granted-over`, `--reason`, `--param`, `--value`) and the
        executor prefix, so copying either remedy verbatim is an argparse rejection.
        """
        commands = _barrier_structural_commands()
        grant = commands[commands.index('merge-authorization grant'):]
        for required in (
            '--plan-id', '--kind', '--head', '--gap-class', '--granted-over', '--reason'
        ):
            assert required in grant[:1400], f'the grant remedy omits {required}'
        params = commands[commands.index('step-params set'):]
        for required in ('--plan-id', '--param', '--value'):
            assert required in params[:1400], f'the reclassify remedy omits {required}'
        # Both remedies must be reachable through the executor, not by raw path.
        assert commands.count('execute-script.py') >= 3

    def test_the_structural_prompt_discloses_every_unproven_bot(self):
        """⛔ Accepting the gap authorizes past ALL of them, not just the refusing one.

        A mixed gap — a size-capped bot plus one that was merely never heard from — is
        reachable on the FIRST barrier entry with zero pending findings. The grant
        covers the whole `review-barrier-gap`, so a prompt naming only the refusing bot
        asks the operator to accept a bot they were never shown.
        """
        block = _barrier_structural_prompt()
        assert '{unproven_bots}' in block, (
            'the structural prompt names only the refusing bots, while accepting the '
            'gap authorizes past every unproven one'
        )


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
        # ``github_ops`` MUST be resolved first — ``_github_pr`` closes an import
        # cycle with it. Reached through ``import_module`` rather than a second
        # ``import`` statement because isort sorts ``_github_pr`` ahead of
        # ``github_ops``, which would break the cycle.
        importlib.import_module('github_ops')
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
        # Yields UNKNOWN rather than raising — and rather than falling back to the whole
        # match, which would report the prose "review limit of 4242" as the cap.
        assert seam.refusal_size_cap('review limit of 4242 chars', 'sourcery') == ''

    def test_a_declared_group_that_captures_nothing_yields_unknown(self, monkeypatch):
        """⛔ NOT a fallback to the whole match — that would report prose as a cap.

        ``review limit of ([0-9]*)`` against a notice stating no number matches with an
        empty group. Falling back to ``group(0)`` returns ``"review limit of"``, which is
        comma-free, survives the CLI transport intact, and renders as
        ``cap: review limit of`` beside a real ``measured_diff_size`` — making the gap
        look audited against a figure nobody observed.
        """
        seam = self._seam()
        monkeypatch.setattr(
            seam.bot_registry, 'refusal_size_cap_patterns', lambda _bot: [r'review limit of ([0-9]*)']
        )
        assert seam.refusal_size_cap('review limit of  chars', 'sourcery') == ''

    def test_a_pattern_capturing_only_whitespace_yields_unknown(self, monkeypatch):
        """An empty capture is no figure, not an empty-string cap."""
        seam = self._seam()
        monkeypatch.setattr(
            seam.bot_registry, 'refusal_size_cap_patterns', lambda _bot: [r'limit of(\s*)']
        )
        assert seam.refusal_size_cap('review limit of 4242 chars', 'sourcery') == ''

    def test_a_pattern_declaring_no_group_uses_the_whole_match(self, monkeypatch):
        """The no-group convention is preserved — the fix narrows only the group case."""
        seam = self._seam()
        monkeypatch.setattr(
            seam.bot_registry, 'refusal_size_cap_patterns', lambda _bot: [r'[0-9]+ diff characters']
        )
        assert seam.refusal_size_cap(
            'review limit of 4242 diff characters', 'sourcery'
        ) == '4242 diff characters'


class TestUnrecognisedRefusalIsADistinctState:
    """The ENUMERATIVE arm's state sits ALONGSIDE a recognised refusal, never inside it.

    A recognised refusal names what the bot said; an unrecognised one records only that
    the stack could not read it. Collapsing the two would lose exactly the distinction
    that makes the second worth reporting — and would let a refusal nobody could parse
    borrow the remedy set of one that was parsed.
    """

    @staticmethod
    def _seam():
        # ``github_ops`` MUST be resolved first — ``_github_pr`` closes an import
        # cycle with it. Reached through ``import_module`` rather than a second
        # ``import`` statement because isort sorts ``_github_pr`` ahead of
        # ``github_ops``, which would break the cycle.
        importlib.import_module('github_ops')
        import _github_pr

        return _github_pr

    def test_a_structurally_recognised_refusal_is_declined_by_the_enumerative_arm(self, monkeypatch):
        """The arms are disjoint on a body the structural arm DID read.

        This is what keeps ``unrecognised_refusal`` empty for a refusal that was
        recognised: the enumerative arm never overrides an arm that read the notice, so
        a structurally-recognised refusal can never also be reported as unrecognised.
        Asserted with a threshold available, so the arm is live while it declines.
        """
        seam = self._seam()
        body = (
            '> [!WARNING]\n'
            '> ## Rate limit exceeded\n'
            '>\n'
            '> This reviewer has reached its limit and will try again later.'
        )
        # The structural arm reads it...
        assert seam._is_rate_limit_notice(body) is True
        assert seam._is_refusal_notice(body, 'sourcery') is True
        # ...so the enumerative arm declines it, whatever the threshold says.
        for threshold in (None, 4000):
            monkeypatch.setattr(seam, 'UNRECOGNISED_REFUSAL_MAX_CHARS', threshold)
            assert seam._is_unrecognised_refusal(body, 'sourcery') is False

    def test_a_size_refusal_is_likewise_never_unrecognised(self, monkeypatch):
        """The size-ceiling notice this suite is about stays a RECOGNISED refusal.

        It is read by the registry arm, so it keeps ``refused_structural`` and its own
        remedy set — split / accept / disable — rather than degrading into the
        declared-ignorance state whose only remedy is to teach the registry a phrasing.
        """
        seam = self._seam()
        body = 'your pull request is larger than the review limit of 150000 diff characters.'
        assert seam._is_refusal_notice(body, 'sourcery') is True
        monkeypatch.setattr(seam, 'UNRECOGNISED_REFUSAL_MAX_CHARS', 4000)
        assert seam._is_unrecognised_refusal(body, 'sourcery') is False

    def test_the_shipped_threshold_is_absent_so_the_arm_is_inert(self):
        """Recorded honestly: no threshold was derivable, so the arm never fires.

        D1 enumerated a corpus of one plan holding zero ``pr-comment`` findings, so no
        shortest-genuine-comment bound exists to derive. The arm errs in the
        merge-BLOCKING direction, so it stays off rather than running on a guessed
        bound — and this pins that the shipped value is the absent one.
        """
        seam = self._seam()
        assert seam.UNRECOGNISED_REFUSAL_MAX_CHARS is None


class TestDiffMeasurement:
    """``_github_pr.measure_diff_size`` — the other half, and its UNKNOWN discipline."""

    @staticmethod
    def _seam():
        # ``github_ops`` MUST be resolved first — ``_github_pr`` closes an import
        # cycle with it. Reached through ``import_module`` rather than a second
        # ``import`` statement because isort sorts ``_github_pr`` ahead of
        # ``github_ops``, which would break the cycle.
        importlib.import_module('github_ops')
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


# ---------------------------------------------------------------------------
# The stale-participation parse — an inadmissible evidence kind must not
# downgrade participated_stale to absent
# ---------------------------------------------------------------------------


class TestStaleParticipationSurvivesAnInadmissibleEvidenceKind:
    """A registry skew must not convert *stale* into *absent*.

    ``--stale-participation-bots`` used to route through ``parse_participation``,
    which re-applies the participation ADMISSIBILITY filter. The producer had
    ALREADY applied that filter before emitting the pair, so re-testing it here
    could only subtract — and when a publish shape was removed from a bot's
    ``participation_evidence`` between the producer's read and the consumer's, it
    did: the observation vanished and the bot fell through to ``absent``.

    The two states prescribe OPPOSITE remedies — ``absent`` says nothing was
    published, escalate; ``participated_stale`` says a review exists but predates
    the merge candidate, re-trigger it — so the downgrade handed the operator the
    wrong remedy with full confidence.
    """

    #: An evidence kind no bot declares, so it is inadmissible for every bot.
    _INADMISSIBLE = 'not-a-declared-kind'

    def test_the_probe_kind_really_is_inadmissible_for_pr_agent(self):
        """⛔ Control: the case below is only meaningful if the filter WOULD drop it.

        If this kind were ever added to cuioss-review-bot's declared publish shapes, the
        assertions below would pass through the old code path too and prove
        nothing.
        """
        assert self._INADMISSIBLE not in bot_registry.participation_evidence('cuioss-review-bot')
        # And the old parse — which still applies the filter — does drop it, which
        # is what made the downgrade reachable.
        assert rc.parse_participation(f'cuioss-review-bot:{self._INADMISSIBLE}') == {}

    def test_the_dedicated_parse_admits_the_pair(self):
        """The new parse keeps the observation the producer emitted."""
        assert rc.parse_stale_participation(f'cuioss-review-bot:{self._INADMISSIBLE}') == {
            'cuioss-review-bot': self._INADMISSIBLE
        }

    def test_the_cli_resolves_it_to_participated_stale_and_never_absent(self, plan_context):
        """End-to-end through the real parse — the case the deliverable names."""
        plan_id = 'stale-inadmissible-kind'
        plan_context.plan_dir_for(plan_id)

        result = run_script(
            SCRIPT_PATH, 'check', '--plan-id', plan_id,
            '--required-bots', 'cuioss-review-bot',
            '--stale-participation-bots', f'cuioss-review-bot:{self._INADMISSIBLE}',
        )

        assert result.returncode == 0
        assert f'cuioss-review-bot,{rc.STATE_PARTICIPATED_STALE}' in result.stdout
        assert f'cuioss-review-bot,{rc.STATE_ABSENT}' not in result.stdout

    def test_the_shape_check_still_rejects_a_bare_token(self, plan_context):
        """Dropping the admissibility filter did NOT drop the SHAPE check.

        A bare ``bot_kind`` carries no evidence kind and is still a loud caller
        error — otherwise this fix would have opened the silent-drop hole it exists
        to close, in the other direction.
        """
        plan_id = 'stale-bare-token'
        plan_context.plan_dir_for(plan_id)

        result = run_script(
            SCRIPT_PATH, 'check', '--plan-id', plan_id,
            '--required-bots', 'cuioss-review-bot', '--stale-participation-bots', 'cuioss-review-bot',
        )

        assert result.returncode == 1
        assert 'participation_complete' not in result.stdout

    def test_an_admissible_pair_is_unchanged(self):
        """Matched control: the fix widened admission, it did not alter the shape."""
        declared = bot_registry.participation_evidence('cuioss-review-bot')
        assert declared, 'cuioss-review-bot must declare a publish shape for this control'

        assert rc.parse_stale_participation(f'cuioss-review-bot:{declared[0]}') == {
            'cuioss-review-bot': declared[0]
        }


# ---------------------------------------------------------------------------
# The flag-FORM partition — derived from the parse routing, never remembered
# ---------------------------------------------------------------------------


def _registered_list_flags() -> set[str]:
    """The list flags ``_add_bot_observation_flags`` actually registers.

    Derived by building a throwaway parser and reading its actions, so the
    population is the parser's own rather than a list kept in a test.
    """
    parser = argparse.ArgumentParser()
    rc._add_bot_observation_flags(parser)
    return {
        action.option_strings[0]
        for action in parser._actions
        if action.option_strings and action.nargs == '?'
    }


def _routing() -> dict[str, str]:
    """Map each flag to the parse FUNCTION ``_parse_bot_observations`` routes it to.

    Read out of the routing function's own AST: every parse call passes its flag
    string as a literal argument, so the pairing is recovered from the code that
    performs it rather than restated.
    """
    source = textwrap.dedent(inspect.getsource(rc._parse_bot_observations))
    routing: dict[str, str] = {}
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
            continue
        for arg in node.args:
            if isinstance(arg, ast.Constant) and str(arg.value).startswith('--'):
                routing[str(arg.value)] = node.func.id
    return routing


def _form_of(parse_name: str) -> str:
    """Classify a parse function as pair-form or bare-form BY BEHAVIOUR.

    Probed rather than named: the function is fed a bare token and a pair token
    and classified by which one it rejects. A name-based mapping would itself be a
    remembered partition — exactly the thing this sweep exists to eliminate — and
    would go stale the moment a differently-named parse is added.
    """
    parse_fn = getattr(rc, parse_name)

    def _rejects(token: str) -> bool:
        try:
            parse_fn(token, '--probe')
        except rc.MalformedBotFlag:
            return True
        return False

    bare_rejected = _rejects('probebot')
    pair_rejected = _rejects('probebot:probeval')
    if bare_rejected and not pair_rejected:
        return 'pair'
    if pair_rejected and not bare_rejected:
        return 'bare'
    raise AssertionError(
        f'{parse_name} accepts or rejects both token shapes, so it declares no form'
    )


def _form_sets() -> tuple[set[str], set[str]]:
    """The derived (pair-form, bare-form) flag sets."""
    routing = _routing()
    pair = {flag for flag, fn in routing.items() if _form_of(fn) == 'pair'}
    bare = {flag for flag, fn in routing.items() if _form_of(fn) == 'bare'}
    return pair, bare


#: Spelled counts, so a prose sentence stating the size of a form-set can be
#: checked against the derived size rather than trusted.
_COUNT_WORDS = {1: 'ONE', 2: 'TWO', 3: 'THREE', 4: 'FOUR', 5: 'FIVE', 6: 'SIX'}

#: Slice markers bounding the pair-form CLAIM in each consuming doc. Uniqueness is
#: not assumed — ``_pair_form_claim`` VERIFIES each marker occurs exactly once in
#: the document it slices — and the parity assertion reads ONLY the text between
#: them. Checking the whole document instead makes the assertion vacuous: every
#: flag, of either form, is named somewhere in both docs, so a bare-form flag
#: listed among the pair-form ones would pass unnoticed — the exact drift the
#: assertion exists to block.
_PAIR_FORM_CLAIM_START = 'PAIRS'
_PAIR_FORM_CLAIM_END = 'take BARE `{bot_kind}` tokens'


def _pair_form_claim(text: str, doc_name: str) -> str:
    """Return ONLY the pair-form-claim slice of a consuming doc.

    Each marker is asserted to occur EXACTLY ONCE before it is used to slice:
    ``str.find`` takes the first occurrence silently, so a second copy of either
    marker would hand back a different paragraph than the one the parity
    assertion means to read, with nothing saying so. Fails loudly rather than
    returning an empty or whole-document string: a missing or unterminated marker
    means the paragraph was restructured, and a silent fallback would restore the
    vacuity this slicing removes.
    """
    for marker, role in ((_PAIR_FORM_CLAIM_START, 'start'), (_PAIR_FORM_CLAIM_END, 'end')):
        occurrences = text.count(marker)
        assert occurrences == 1, (
            f'{doc_name}: the pair-form claim {role} marker {marker!r} must occur '
            f'exactly once, found {occurrences} — zero means the paragraph was '
            f'restructured; more than one means the slice would silently take the '
            f'first of several candidates'
        )

    start = text.find(_PAIR_FORM_CLAIM_START)
    end = text.find(_PAIR_FORM_CLAIM_END, start)
    assert end != -1, (
        f'{doc_name}: pair-form claim is unterminated '
        f'(the single end marker {_PAIR_FORM_CLAIM_END!r} precedes the start marker)'
    )
    claim = text[start:end]
    assert claim.strip(), f'{doc_name}: the pair-form claim slice is empty'
    return claim


def _assert_pair_form_claim_parity(
    text: str, doc_name: str, pair: set[str], bare: set[str]
) -> None:
    """THE parity rule — one definition, called by the guard AND its control.

    The sliced pair-form claim must name every derived pair-form flag and no
    derived bare-form one. This lives in a helper rather than inline in the guard
    so the negative control can execute the guard's OWN assertions against a
    planted document instead of re-implementing a rule shaped like them: remove
    the ``assert not offenders`` below and both the guard and the control fail.
    """
    claim = _pair_form_claim(text, doc_name)
    for flag in sorted(pair):
        assert f'`{flag}`' in claim, (
            f'{doc_name} omits pair-form {flag} from its pair-form claim'
        )
    offenders = [flag for flag in sorted(bare) if f'`{flag}`' in claim]
    assert not offenders, (
        f'{doc_name} lists BARE-form {", ".join(offenders)} among the pair-form flags'
    )


class TestTheFlagFormPartitionIsDerivedNotRemembered:
    """No passage may name a form partition the parse routing contradicts.

    Every claim here is derived twice over: the flag population from the parser's
    own actions, and each flag's FORM from how its parse function behaves on a
    bare token versus a pair. Nothing in this class restates a partition.
    """

    def test_the_derived_population_is_non_empty_and_publishes_its_sizes(self):
        """⛔ Vacuity guard — an empty routing would make every sweep below pass."""
        pair, bare = _form_sets()

        assert pair, 'no pair-form flag derived — the sweeps below would be vacuous'
        assert bare, 'no bare-form flag derived — the sweeps below would be vacuous'
        # Published: the two sizes the prose assertions are checked against.
        assert len(pair) + len(bare) == len(_registered_list_flags())

    def test_every_registered_list_flag_is_routed(self):
        """A flag the parser accepts but nothing parses would silently do nothing."""
        pair, bare = _form_sets()

        assert pair | bare == _registered_list_flags()

    def test_the_two_forms_are_disjoint(self):
        """A flag cannot be both, and the behavioural probe must not say it is."""
        pair, bare = _form_sets()

        assert not (pair & bare)

    def test_the_module_docstring_names_exactly_the_derived_pair_form_set(self):
        """The prose partition is checked against the parser, not maintained by hand.

        This is the assertion the deliverable's 'no passage names a partition the
        sweep contradicts' criterion rests on: the docstring's pair-form paragraph
        must mention every derived pair-form flag and no bare-form one.
        """
        pair, bare = _form_sets()
        doc = rc.__doc__ or ''
        start = doc.index('flags are pair-form')
        end = doc.index('Every REMAINING list flag is bare-form')
        paragraph = doc[start:end]

        for flag in sorted(pair):
            assert f'``{flag}``' in paragraph, f'{flag} is pair-form but the docstring omits it'
        for flag in sorted(bare):
            assert f'``{flag}``' not in paragraph, (
                f'{flag} is BARE-form but the docstring lists it among the pair-form flags'
            )

    def test_the_module_docstring_states_the_derived_pair_form_count(self):
        """A stale count word is the exact drift that shipped before (TWO of four)."""
        pair, _bare = _form_sets()

        assert f'{_COUNT_WORDS[len(pair)]} flags are pair-form' in (rc.__doc__ or '')

    def test_the_two_usage_synopses_differ_only_by_genuinely_unique_flags(self):
        """Any shared flag missing from one synopsis is a documentation gap.

        Both subcommands build their observation flags from the same
        ``_add_bot_observation_flags``, so every one of those flags belongs on BOTH
        usage lines; only the per-subcommand extras may differ.
        """
        doc = rc.__doc__ or ''
        check_line = next(ln for ln in doc.splitlines() if 'review_completeness.py check' in ln)
        deficit_line = next(
            ln for ln in doc.splitlines() if 'review_completeness.py deficit' in ln
        )

        for flag in sorted(_registered_list_flags()):
            assert flag in check_line, f'{flag} is shared but missing from the check synopsis'
            assert flag in deficit_line, f'{flag} is shared but missing from the deficit synopsis'

        # What legitimately differs is only each subcommand's own extra flags.
        assert '--triage-ran' in check_line and '--triage-ran' not in deficit_line
        assert '--measured-diff-size' in check_line and '--measured-diff-size' not in deficit_line
        assert '--min-deficit' in deficit_line and '--min-deficit' not in check_line

    def test_the_rejection_message_names_the_pair_form_set_generically(self):
        """It must not name individual flags — that copy went stale at two of four."""
        try:
            rc._split_bots('bot:pair', '--required-bots')
        except rc.MalformedBotFlag as exc:
            message = str(exc)
        else:  # pragma: no cover - the call above must raise
            raise AssertionError('a pair token on a bare-form flag must be rejected')

        pair, _bare = _form_sets()
        for flag in sorted(pair):
            assert flag not in message, (
                f'the bare-form rejection message names {flag}; naming individual '
                f'pair-form flags is what went stale when the set grew'
            )

    def test_the_two_consuming_docs_carry_no_contradicted_partition(self):
        """The SKILL and branch-cleanup copies are held to the derived sets.

        Both sites carry their own restatement, which the deliverable permits only
        when a parity assertion covers it — this is that assertion. A bare-form
        flag described as pair-form at either site is the drift being blocked, so
        the membership assertions read the sliced pair-form CLAIM, not the whole
        document: every flag of either form is named somewhere in both docs, so a
        whole-document sweep can never observe that drift.
        """
        pair, bare = _form_sets()

        for doc_path in (_AR_SKILL, _BRANCH_CLEANUP):
            text = doc_path.read_text(encoding='utf-8')
            assert f'{_COUNT_WORDS[len(pair)].capitalize()} take' in text or (
                f'{_COUNT_WORDS[len(pair)]} take' in text
            ), f'{doc_path.name} does not state the derived pair-form count'
            _assert_pair_form_claim_parity(text, doc_path.name, pair, bare)
            for flag in sorted(bare):
                assert f'`{flag}`' in text, f'{doc_path.name} omits bare-form {flag}'

    def test_the_parity_assertion_rejects_a_bare_form_flag_listed_as_pair_form(self):
        """⛔ Negative control: the guard above must be able to FAIL.

        A parity assertion nobody watched reject is not a guard. This CALLS the
        guard's own rule — ``_assert_pair_form_claim_parity``, the single
        definition the guard above also calls — against a synthetic document in
        which one bare-form flag has been moved into the pair-form claim.
        Everything else about the document is well-formed, so only the planted
        drift can be what rejects it, and because the rule is executed rather than
        re-implemented, deleting the rule's membership assertion fails this control
        too.
        """
        pair, bare = _form_sets()
        planted = sorted(bare)[0]
        pair_listing = ', '.join(f'`{flag}`' for flag in sorted(pair))
        bare_listing = ', '.join(f'`{flag}`' for flag in sorted(bare))
        broken = (
            f'{_COUNT_WORDS[len(pair)]} take comma-separated PAIRS: '
            f'{pair_listing} and `{planted}`. '
            f'The rest take BARE `{{bot_kind}}` tokens: {bare_listing}.'
        )

        assert f'`{planted}`' in _pair_form_claim(broken, 'synthetic'), (
            'the planted flag must land inside the slice'
        )

        with pytest.raises(AssertionError) as rejection:
            _assert_pair_form_claim_parity(broken, 'synthetic', pair, bare)
        assert f'BARE-form {planted}' in str(rejection.value), (
            f'the guard must reject exactly the planted bare-form flag; '
            f'got {rejection.value}'
        )

        # And the matched POSITIVE control: the same rule ACCEPTS the real docs,
        # so the rejection above is the planted drift and not a rule that rejects
        # everything.
        for doc_path in (_AR_SKILL, _BRANCH_CLEANUP):
            _assert_pair_form_claim_parity(
                doc_path.read_text(encoding='utf-8'), doc_path.name, pair, bare
            )


# ---------------------------------------------------------------------------
# The consumer-doc REMEDY GUARD — every member a wait cannot serve must be
# exempted from the default await, in BOTH consuming docs
# ---------------------------------------------------------------------------


#: The paragraph opener both consuming docs use for the guard that tells a reader
#: which blocking members must NOT be awaited.
_REMEDY_GUARD_ANCHOR = 'Read `bot_states` before'


def _remedy_guard_text(text: str, doc_name: str) -> str:
    """The remedy-guard PARAGRAPH of a consuming doc, bounded by its own blank line.

    The anchor is asserted to occur EXACTLY ONCE before it is used to slice:
    ``str.index`` takes the first occurrence silently, so a second copy would hand
    back a different paragraph than the one the parity assertion means to read,
    with nothing saying so. The end is the document's own paragraph break rather
    than a character count — a fixed window silently stops covering whatever is
    appended past its end, which is exactly how a member added to a grown
    paragraph would escape the sweep while it still reported clean.
    """
    occurrences = text.count(_REMEDY_GUARD_ANCHOR)
    assert occurrences == 1, (
        f'{doc_name}: the remedy-guard anchor {_REMEDY_GUARD_ANCHOR!r} must occur '
        f'exactly once, found {occurrences} — zero means the paragraph was '
        f'restructured; more than one means the slice would silently take the '
        f'first of several candidates'
    )
    start = text.index(_REMEDY_GUARD_ANCHOR)
    end = text.find('\n\n', start)
    guard = text[start:end] if end != -1 else text[start:]
    assert guard.strip(), f'{doc_name}: the remedy-guard slice is empty'
    return guard


def _remedy_guard_members(guard: str) -> set[str]:
    """The terminal-state members a guard paragraph names.

    Matched in backticks, so ``participated_stale`` cannot be counted as a mention
    of ``participated``.
    """
    return {state for state in _TERMINAL_STATES if f'`{state}`' in guard}


def _members_no_wait_can_serve() -> set[str]:
    """DERIVED: the blocking members for which the default *await the bot* is futile.

    Not a list kept here. It is the intersection of the classifier's own blocking
    set with the await-can-never-succeed classification — which is itself asserted
    TOTAL over the derived population at the top of this module. A member added to
    the classifier therefore cannot enter the docs' obligation set unnoticed: it
    must first be classified, and classifying it await-futile immediately obliges
    BOTH consuming docs to exempt it from the default loop-back.
    """
    return {
        state for state in rc._UNPROVEN_STATES if not _AWAIT_CAN_EVER_SUCCEED[state]
    }


def _assert_remedy_guard_parity(text: str, doc_name: str, required: set[str]) -> None:
    """THE remedy-guard rule — one definition, called by the guard AND its controls.

    Lives in a helper rather than inline so the negative controls can execute the
    guard's OWN assertions against a planted document instead of re-implementing a
    rule shaped like them: delete either assertion below and both the guard and its
    control fail.
    """
    named = _remedy_guard_members(_remedy_guard_text(text, doc_name))
    missing = sorted(required - named)
    assert not missing, (
        f'{doc_name} enumerates {", ".join(missing)} as blocking but never exempts '
        f'it from the default await — a required bot in that state is awaited for '
        f'a review that will never arrive'
    )
    surplus = sorted(named - required)
    assert not surplus, (
        f'{doc_name} exempts {", ".join(surplus)} from awaiting, but a wait CAN '
        f'serve that member — the guard steers the reader off a remedy that works'
    )


def _synthetic_guard(members: list[str]) -> str:
    """A well-formed consumer-doc excerpt exempting exactly ``members``.

    Everything but the membership is correct — one anchor, a real paragraph break
    on each side — so only the planted drift can be what a control's rejection is
    about. The trailing paragraph deliberately names a member the guard must NOT
    claim, which makes an over-reaching slice fail the scaffold's own positive
    control rather than passing silently.
    """
    listing = '; '.join(
        f'a required bot on `{member}` names a remedy of its own' for member in members
    )
    return (
        'A preceding paragraph that the slice must not reach.\n\n'
        f'{_REMEDY_GUARD_ANCHOR} re-entering, because some blocking members name a '
        f'different remedy than awaiting: {listing}.\n\n'
        f'A following paragraph, which legitimately mentions `{rc.STATE_IN_PROGRESS}`, '
        f'and which the slice must not reach either.\n'
    )


class TestBothConsumerDocsExemptEveryAwaitFutileMember:
    """⛔ The recurring class: a member added as blocking but never exempted.

    ``declined`` shipped as a new blocking member: it was added to the
    ``unproven_bots`` enumeration in ``automatic-review/SKILL.md`` and to
    ``branch-cleanup.md``'s remedy guard — but not to the SKILL's own remedy guard,
    which still enumerated a stale subset behind a stale count word. The SKILL's
    default for an unproven bot is *loop back into FIND and await the bot*, so a
    required bot on ``declined`` was enumerated as blocking, left unexempted, and
    awaited forever — the precise outcome that guard exists to prevent.

    Nothing failed, because every remedy assertion in this file read ONE of the two
    consuming docs. These read both, and hold each to a population derived from the
    classifier rather than to a list anybody maintains.
    """

    def test_the_obligation_set_is_non_empty(self):
        """⛔ Vacuity guard, asserted FIRST — an empty set makes every sweep below pass."""
        assert _members_no_wait_can_serve(), (
            'no blocking member was derived as await-futile — the parity sweeps '
            'below would pass over nothing'
        )

    @pytest.mark.parametrize(
        'doc_path', [_AR_SKILL, _BRANCH_CLEANUP], ids=lambda path: str(path.name)
    )
    def test_the_doc_exempts_exactly_the_await_futile_members(self, doc_path):
        """Each consuming doc, held to the derived set in both directions.

        Equality rather than containment: a subset is the shipped defect, and a
        superset would exempt a member a wait CAN serve, steering the reader off the
        remedy that works.
        """
        _assert_remedy_guard_parity(
            doc_path.read_text(encoding='utf-8'),
            doc_path.name,
            _members_no_wait_can_serve(),
        )

    def test_the_two_consuming_docs_name_the_same_members(self):
        """Doc-to-doc parity, asserted directly and not only via the derived set.

        The two docs consume the SAME predicate, so a member exempted in one and not
        the other is a contradiction whichever of them the derivation agrees with.
        Asserted separately so the divergence fails mechanically even in the window
        where the derived obligation set is itself wrong.
        """
        skill = _remedy_guard_members(
            _remedy_guard_text(_AR_SKILL.read_text(encoding='utf-8'), _AR_SKILL.name)
        )
        barrier = _remedy_guard_members(
            _remedy_guard_text(
                _BRANCH_CLEANUP.read_text(encoding='utf-8'), _BRANCH_CLEANUP.name
            )
        )
        assert skill and barrier, 'a guard naming no member makes this comparison vacuous'
        assert skill == barrier, (
            f'the two consuming docs exempt different members; '
            f'only in the SKILL: {sorted(skill - barrier)}; '
            f'only in branch-cleanup: {sorted(barrier - skill)}'
        )

    def test_the_synthetic_scaffold_is_accepted_by_the_rule(self):
        """⛔ Matched control for the two rejections below.

        Without it a rejection proves nothing: a rule that rejected every synthetic
        document would produce the same red. It doubles as the slice-boundedness
        assertion, since the scaffold's trailing paragraph names a member the guard
        must not be credited with.
        """
        required = _members_no_wait_can_serve()
        _assert_remedy_guard_parity(_synthetic_guard(sorted(required)), 'synthetic', required)

    def test_the_rule_rejects_a_doc_that_omits_an_await_futile_member(self):
        """⛔ Negative control: the shipped defect, planted — the guard must FAIL on it.

        This is one doc exempting a member the other does not, which is exactly the
        divergence that shipped. The guard's OWN rule is executed rather than
        re-implemented, so deleting the rule's missing-member assertion fails this
        control too.
        """
        required = _members_no_wait_can_serve()
        omitted = sorted(required)[0]
        broken = _synthetic_guard(sorted(required - {omitted}))

        with pytest.raises(AssertionError) as rejection:
            _assert_remedy_guard_parity(broken, 'synthetic', required)
        assert omitted in str(rejection.value), (
            f'the guard must reject exactly the omitted member {omitted}; '
            f'got {rejection.value}'
        )

        # And the matched POSITIVE control: the same rule ACCEPTS the real docs, so
        # the rejection above is the planted omission and not a rule that rejects
        # everything.
        for doc_path in (_AR_SKILL, _BRANCH_CLEANUP):
            _assert_remedy_guard_parity(
                doc_path.read_text(encoding='utf-8'), doc_path.name, required
            )

    def test_the_rule_rejects_a_doc_that_exempts_a_member_a_wait_can_serve(self):
        """⛔ Negative control, other direction: over-listing is a defect too.

        A guard that exempted ``absent`` or ``in_progress`` would tell the reader not
        to await a bot that may still answer — the same wrong-remedy failure with the
        polarity reversed, and a containment-only assertion would pass on it.
        """
        required = _members_no_wait_can_serve()
        serviceable = sorted(
            state for state in rc._UNPROVEN_STATES if _AWAIT_CAN_EVER_SUCCEED[state]
        )
        assert serviceable, (
            'no blocking member is await-serviceable — this control would plant nothing'
        )
        planted = serviceable[0]
        broken = _synthetic_guard(sorted(required) + [planted])

        with pytest.raises(AssertionError) as rejection:
            _assert_remedy_guard_parity(broken, 'synthetic', required)
        assert planted in str(rejection.value), (
            f'the guard must reject exactly the planted awaitable member {planted}; '
            f'got {rejection.value}'
        )

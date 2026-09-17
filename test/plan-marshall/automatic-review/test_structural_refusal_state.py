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
rc = load_script_module('plan-marshall', 'automatic-review', 'review_completeness.py', register=False)

# ⛔ Vacuity guard — the bot-kind population is read off the live registry, so an
# empty registry collects zero cases at the parametrize below and reports green.
assert bot_registry.bot_kinds(), 'bot_registry.bot_kinds() is empty'

SCRIPT_PATH = get_script_path('plan-marshall', 'automatic-review', 'review_completeness.py')
SCRIPTS_DIR = SCRIPT_PATH.parent

_CONTRACT_DOC = SCRIPTS_DIR.parent / 'standards' / 'bot-participation-contract.md'
_AR_SKILL = SCRIPTS_DIR.parent / 'SKILL.md'
_BRANCH_CLEANUP = SCRIPTS_DIR.parent.parent / 'phase-6-finalize' / 'standards' / 'branch-cleanup.md'
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
    value for name, value in vars(rc).items() if name.startswith('STATE_') and isinstance(value, str)
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
    rc.STATE_PARTICIPATED: True,  # not a block at all
    rc.STATE_PARTICIPATED_BUT_EMPTY: True,  # accounted-for, never a block
    rc.STATE_IN_PROGRESS: True,  # the run finishes; time is the remedy
    rc.STATE_NOT_TRIGGERED: True,  # generate the trigger event
    rc.STATE_PARTICIPATED_STALE: True,  # re-trigger a re-review
    rc.STATE_ABSENT: True,  # loop back and re-trigger the silent bot
    rc.STATE_REFUSED_AWAITABLE: True,  # claim the window and await the reset
    rc.STATE_REFUSED_UNKNOWN: False,  # recovery escalates rather than awaiting
    rc.STATE_REFUSED_HARD: False,  # a budget the plan cannot restore
    rc.STATE_DECLINED: False,  # re-triggering yields another decline
    rc.STATE_REFUSED_STRUCTURAL: False,  # the ceiling is on the diff, not on time
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
    rc.STATE_PARTICIPATED: False,  # nothing to wait for
    rc.STATE_PARTICIPATED_BUT_EMPTY: False,  # nothing to wait for
    rc.STATE_IN_PROGRESS: True,  # the run is still going
    rc.STATE_NOT_TRIGGERED: False,  # nothing was asked; waiting asks nothing
    rc.STATE_PARTICIPATED_STALE: False,  # waiting alone refreshes no review
    rc.STATE_ABSENT: True,  # the bot may still answer
    rc.STATE_REFUSED_AWAITABLE: True,  # the window reopens on its own
    rc.STATE_REFUSED_UNKNOWN: True,  # not known to fail — see above
    rc.STATE_REFUSED_HARD: False,  # does not reopen on a useful timescale
    rc.STATE_DECLINED: False,  # the bot answered and will answer the same
    rc.STATE_REFUSED_STRUCTURAL: False,  # ⭐ the diff is the limit; time is not
    # No reviewer answers to this NAME, and none ever could — participation is keyed
    # by a bot_kind derived from an author login, so a token outside that codomain
    # can never be credited however long the wait. This is the strongest ``False`` on
    # the axis: the others describe a reviewer that will not answer NOW, this one a
    # reviewer that does not exist.
    rc.STATE_UNREGISTERED_KIND: False,
}




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
    return hook[start : start + nxt.start()] if nxt else hook[start:]


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
    return block[block.index('options:') :]


def _section(doc: str, heading_pattern: str) -> str:
    """Return the body of the first section whose heading matches, to its next peer."""
    match = re.search(
        rf'^(?P<hashes>#{{2,6}})\s*{heading_pattern}.*?$(?P<body>.*?)(?=^#{{1,6}}\s)',
        doc,
        re.DOTALL | re.MULTILINE,
    )
    assert match, f'no section matching {heading_pattern!r}'
    return str(match.group('body'))


def _registered_list_flags() -> set[str]:
    """The list flags ``_add_bot_observation_flags`` actually registers.

    Derived by building a throwaway parser and reading its actions, so the
    population is the parser's own rather than a list kept in a test.
    """
    parser = argparse.ArgumentParser()
    rc._add_bot_observation_flags(parser)
    return {action.option_strings[0] for action in parser._actions if action.option_strings and action.nargs == '?'}


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
    raise AssertionError(f'{parse_name} accepts or rejects both token shapes, so it declares no form')


def _form_sets() -> tuple[set[str], set[str]]:
    """The derived (pair-form, bare-form) flag sets."""
    routing = _routing()
    pair = {flag for flag, fn in routing.items() if _form_of(fn) == 'pair'}
    bare = {flag for flag, fn in routing.items() if _form_of(fn) == 'bare'}
    return pair, bare


_COUNT_WORDS = {1: 'ONE', 2: 'TWO', 3: 'THREE', 4: 'FOUR', 5: 'FIVE', 6: 'SIX'}


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


def _assert_pair_form_claim_parity(text: str, doc_name: str, pair: set[str], bare: set[str]) -> None:
    """THE parity rule — one definition, called by the guard AND its control.

    The sliced pair-form claim must name every derived pair-form flag and no
    derived bare-form one. This lives in a helper rather than inline in the guard
    so the negative control can execute the guard's OWN assertions against a
    planted document instead of re-implementing a rule shaped like them: remove
    the ``assert not offenders`` below and both the guard and the control fail.
    """
    claim = _pair_form_claim(text, doc_name)
    for flag in sorted(pair):
        assert f'`{flag}`' in claim, f'{doc_name} omits pair-form {flag} from its pair-form claim'
    offenders = [flag for flag in sorted(bare) if f'`{flag}`' in claim]
    assert not offenders, f'{doc_name} lists BARE-form {", ".join(offenders)} among the pair-form flags'


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
    return {state for state in rc._UNPROVEN_STATES if not _AWAIT_CAN_EVER_SUCCEED[state]}


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
    listing = '; '.join(f'a required bot on `{member}` names a remedy of its own' for member in members)
    return (
        'A preceding paragraph that the slice must not reach.\n\n'
        f'{_REMEDY_GUARD_ANCHOR} re-entering, because some blocking members name a '
        f'different remedy than awaiting: {listing}.\n\n'
        f'A following paragraph, which legitimately mentions `{rc.STATE_IN_PROGRESS}`, '
        f'and which the slice must not reach either.\n'
    )


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
            assert f'`{state}`' in table, f'{state} blocks the merge but is undocumented in the contract'

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
            state
            for state in _TERMINAL_STATES
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
                assert _PASSABLE_BY_PLAN_ACTION[state] or state in (rc.STATE_REFUSED_UNKNOWN,), (
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
            plan_id,
            ['sourcery'],
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
            plan_id,
            ['sourcery'],
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
            plan_id,
            ['coderabbit'],
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
            plan_id,
            [bot],
            refused_bots=[bot],
            refused_causes={bot: 'size'},
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
            plan_id,
            ['coderabbit'],
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
            plan_id,
            ['sourcery'],
            refused_bots=['sourcery'],
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
    def test_check_and_deficit_agree_on_the_member(self, plan_context, case, kwargs, expected_attr):
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
        deficit_state = next(r['state'] for r in deficit['reviewers'] if r['bot_kind'] == 'sourcery')
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
            plan_id,
            ['sourcery'],
            refused_bots=['sourcery'],
            refused_causes={'sourcery': 'size'},
        )
        temporal = rc.check_completeness(
            plan_id,
            ['sourcery'],
            refused_bots=['sourcery'],
            refused_causes={'sourcery': 'quota'},
        )
        assert structural['review_state_summary'] != temporal['review_state_summary']
        assert 'structural' in structural['review_state_summary']


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
            '> [!WARNING]\n> ## Rate limit exceeded\n>\n> This reviewer has reached its limit and will try again later.'
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

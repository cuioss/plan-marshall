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
            f'the structural escalation offers a wait, which is the non-option this member exists to remove:\n{body}'
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
        structural = next(line for line in row.splitlines() if line.startswith('| `refused_structural`'))
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
            'the disable-reviewer branch does not name the required-bots scoping its settling claim depends on'
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
            'split' in barrier[start : start + 1500] and 'cap' in barrier[start : start + 1500] for start in mentions
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
        assert not _WAIT_OFFER.search(options), f'the barrier prompt offers a wait:\n{options}'
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
        assert 'refusal_causes[]' in block, 'the derivation does not name the payload field it reads'
        # The multi-bot RENDERING, decided rather than left to the renderer.
        assert '{bot_kind}:{cap} pairs' in block, 'the derivation does not state the multi-bot rendering as a pair list'
        # The unknown fallback — a blank or a default would make an unquantified
        # gap read as a quantified one.
        assert 'unknown' in block, 'the derivation does not say what a bot stating no ceiling renders as'

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
        read_instruction = _to_next_heading(barrier, barrier.index('Read `participation_complete`'))
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
        assert '{count} == 0' in section, 'the structural disposition does not scope itself to the zero-pending case'

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
        block = skill[start : skill.index('```', skill.index('```bash', start) + 7)]
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
        assert 'max_iterations' in section, 'the branch does not state what bounds an unattended run'

    def test_the_default_paths_remedies_are_complete_invocations(self):
        """A remedy an operator cannot copy-run is no remedy.

        This decision-log is the ONLY operator-facing surface on the default
        configuration. An earlier draft named the verbs but omitted required arguments
        (`--plan-id`, `--granted-over`, `--reason`, `--param`, `--value`) and the
        executor prefix, so copying either remedy verbatim is an argparse rejection.
        """
        commands = _barrier_structural_commands()
        grant = commands[commands.index('merge-authorization grant') :]
        for required in ('--plan-id', '--kind', '--head', '--gap-class', '--granted-over', '--reason'):
            assert required in grant[:1400], f'the grant remedy omits {required}'
        params = commands[commands.index('step-params set') :]
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
            seam.github_ops,
            'run_gh',
            lambda *_a, **_k: (0, '{"additions": 900, "deletions": 340}', ''),
        )
        assert seam.measure_diff_size(7) == '1240 changed lines'

    @pytest.mark.parametrize(
        'returncode, stdout',
        [
            (1, ''),  # the read failed
            (0, ''),  # empty output
            (0, 'not json'),  # unparseable
            (0, '[]'),  # wrong shape
            (0, '{"additions": 900}'),  # a field missing
            (0, '{"additions": "900", "deletions": 1}'),  # a field non-numeric
        ],
    )
    def test_an_unusable_read_is_unknown_never_zero(self, monkeypatch, returncode, stdout):
        """⛔ ``0`` would read as an empty diff refused for being too big.

        That is a claim the function has no evidence for, and it would make an
        unmeasurable gap look audited against a number nobody observed.
        """
        seam = self._seam()
        monkeypatch.setattr(seam.github_ops, 'run_gh', lambda *_a, **_k: (returncode, stdout, 'err'))
        assert seam.measure_diff_size(7) == ''


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
            SCRIPT_PATH,
            'check',
            '--plan-id',
            plan_id,
            '--required-bots',
            'cuioss-review-bot',
            '--stale-participation-bots',
            f'cuioss-review-bot:{self._INADMISSIBLE}',
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
            SCRIPT_PATH,
            'check',
            '--plan-id',
            plan_id,
            '--required-bots',
            'cuioss-review-bot',
            '--stale-participation-bots',
            'cuioss-review-bot',
        )

        assert result.returncode == 1
        assert 'participation_complete' not in result.stdout

    def test_an_admissible_pair_is_unchanged(self):
        """Matched control: the fix widened admission, it did not alter the shape."""
        declared = bot_registry.participation_evidence('cuioss-review-bot')
        assert declared, 'cuioss-review-bot must declare a publish shape for this control'

        assert rc.parse_stale_participation(f'cuioss-review-bot:{declared[0]}') == {'cuioss-review-bot': declared[0]}

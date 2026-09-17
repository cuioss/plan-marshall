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
        deficit_line = next(ln for ln in doc.splitlines() if 'review_completeness.py deficit' in ln)

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

        assert f'`{planted}`' in _pair_form_claim(broken, 'synthetic'), 'the planted flag must land inside the slice'

        with pytest.raises(AssertionError) as rejection:
            _assert_pair_form_claim_parity(broken, 'synthetic', pair, bare)
        assert f'BARE-form {planted}' in str(rejection.value), (
            f'the guard must reject exactly the planted bare-form flag; got {rejection.value}'
        )

        # And the matched POSITIVE control: the same rule ACCEPTS the real docs,
        # so the rejection above is the planted drift and not a rule that rejects
        # everything.
        for doc_path in (_AR_SKILL, _BRANCH_CLEANUP):
            _assert_pair_form_claim_parity(doc_path.read_text(encoding='utf-8'), doc_path.name, pair, bare)


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
            'no blocking member was derived as await-futile — the parity sweeps below would pass over nothing'
        )

    @pytest.mark.parametrize('doc_path', [_AR_SKILL, _BRANCH_CLEANUP], ids=lambda path: str(path.name))
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
        skill = _remedy_guard_members(_remedy_guard_text(_AR_SKILL.read_text(encoding='utf-8'), _AR_SKILL.name))
        barrier = _remedy_guard_members(
            _remedy_guard_text(_BRANCH_CLEANUP.read_text(encoding='utf-8'), _BRANCH_CLEANUP.name)
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
            f'the guard must reject exactly the omitted member {omitted}; got {rejection.value}'
        )

        # And the matched POSITIVE control: the same rule ACCEPTS the real docs, so
        # the rejection above is the planted omission and not a rule that rejects
        # everything.
        for doc_path in (_AR_SKILL, _BRANCH_CLEANUP):
            _assert_remedy_guard_parity(doc_path.read_text(encoding='utf-8'), doc_path.name, required)

    def test_the_rule_rejects_a_doc_that_exempts_a_member_a_wait_can_serve(self):
        """⛔ Negative control, other direction: over-listing is a defect too.

        A guard that exempted ``absent`` or ``in_progress`` would tell the reader not
        to await a bot that may still answer — the same wrong-remedy failure with the
        polarity reversed, and a containment-only assertion would pass on it.
        """
        required = _members_no_wait_can_serve()
        serviceable = sorted(state for state in rc._UNPROVEN_STATES if _AWAIT_CAN_EVER_SUCCEED[state])
        assert serviceable, 'no blocking member is await-serviceable — this control would plant nothing'
        planted = serviceable[0]
        broken = _synthetic_guard(sorted(required) + [planted])

        with pytest.raises(AssertionError) as rejection:
            _assert_remedy_guard_parity(broken, 'synthetic', required)
        assert planted in str(rejection.value), (
            f'the guard must reject exactly the planted awaitable member {planted}; got {rejection.value}'
        )

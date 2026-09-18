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


class TestTheCapIsRecorded:
    """(c) The stated ceiling travels with the finding, and an absent one stays absent."""

    def test_the_cap_is_reported_alongside_the_cause(self, plan_context):
        plan_id = 'struct-cap-reported'
        plan_context.plan_dir_for(plan_id)
        result = rc.check_completeness(
            plan_id,
            ['sourcery'],
            refused_bots=['sourcery'],
            refused_causes={'sourcery': 'size'},
            refusal_size_caps={'sourcery': '4242 diff characters'},
        )
        assert result['refusal_causes'] == [{'bot_kind': 'sourcery', 'cause': 'size', 'cap': '4242 diff characters'}]

    def test_an_unstated_cap_reads_unknown_and_is_never_defaulted(self, plan_context):
        """A cap nobody observed must not be invented.

        The gap's whole value is being reconcilable against the measured diff size; a
        defaulted figure would make it look audited against a number that was made up
        here.
        """
        plan_id = 'struct-cap-unknown'
        plan_context.plan_dir_for(plan_id)
        result = rc.check_completeness(
            plan_id,
            ['sourcery'],
            refused_bots=['sourcery'],
            refused_causes={'sourcery': 'size'},
        )
        assert result['refusal_causes'][0]['cap'] == ''

    def test_the_cli_renders_the_cap_column(self, plan_context):
        plan_id = 'struct-cap-cli'
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
            '--refusal-size-caps',
            'sourcery:4242 diff characters',
        )
        assert result.returncode == 0
        assert 'refusal_causes[1]{bot_kind,cause,cap}:' in result.stdout
        assert 'sourcery,size,4242 diff characters' in result.stdout

    def test_the_cli_renders_an_unstated_cap_as_the_word_unknown(self, plan_context):
        """An empty column would be indistinguishable from a parse slip."""
        plan_id = 'struct-cap-cli-unknown'
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
        assert 'sourcery,size,unknown' in result.stdout

    def test_a_malformed_cap_token_is_an_unknown_verdict(self, plan_context):
        """Shape violations are rejected loudly, exactly as the sibling pair-form flags."""
        plan_id = 'struct-cap-malformed'
        plan_context.plan_dir_for(plan_id)
        result = run_script(
            SCRIPT_PATH,
            'check',
            '--plan-id',
            plan_id,
            '--required-bots',
            'sourcery',
            '--refusal-size-caps',
            'sourcery',
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
            '--refusal-size-caps',
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
            plan_id,
            ['sourcery'],
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
            '--refusal-size-caps',
            'sourcery:4242 diff characters',
            '--measured-diff-size',
            '9001 changed lines',
        )
        assert result.returncode == 0
        assert 'measured_diff_size: 9001 changed lines' in result.stdout
        assert 'sourcery,size,4242 diff characters' in result.stdout

    def test_an_unmeasured_diff_emits_no_size_line(self, plan_context):
        """Absent rather than zero: ``0`` would read as an empty diff being refused."""
        plan_id = 'struct-unmeasured'
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
            plan_id,
            ['sourcery'],
            refused_bots=['sourcery'],
            refusal_size_caps={'sourcery': '4242 diff characters'},
        )
        assert _state_of(result, 'sourcery') == rc.STATE_REFUSED_STRUCTURAL
        assert result['refusal_causes'] == [{'bot_kind': 'sourcery', 'cause': 'size', 'cap': '4242 diff characters'}]

    def test_a_cause_without_a_cap_is_never_inferred_backwards(self, plan_context):
        """The recovery is one-directional. A cause with no cap is an ordinary unknown.

        Inferring in the other direction would invent a cap, which is precisely what the
        unknown-cap discipline exists to prevent.
        """
        plan_id = 'struct-cause-without-cap'
        plan_context.plan_dir_for(plan_id)
        result = rc.check_completeness(
            plan_id,
            ['sourcery'],
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
            plan_id,
            ['sourcery'],
            refused_bots=['sourcery'],
            refused_causes={'sourcery': 'size'},
            measured_diff_size='9001 changed lines',
        )
        assert not result['measured_diff_size'].strip().isdigit()


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
        monkeypatch.setattr(seam.bot_registry, 'refusal_size_cap_patterns', lambda _bot: ['([unclosed'])
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
        monkeypatch.setattr(seam.bot_registry, 'refusal_size_cap_patterns', lambda _bot: [r'review limit of ([0-9]*)'])
        assert seam.refusal_size_cap('review limit of  chars', 'sourcery') == ''

    def test_a_pattern_capturing_only_whitespace_yields_unknown(self, monkeypatch):
        """An empty capture is no figure, not an empty-string cap."""
        seam = self._seam()
        monkeypatch.setattr(seam.bot_registry, 'refusal_size_cap_patterns', lambda _bot: [r'limit of(\s*)'])
        assert seam.refusal_size_cap('review limit of 4242 chars', 'sourcery') == ''

    def test_a_pattern_declaring_no_group_uses_the_whole_match(self, monkeypatch):
        """The no-group convention is preserved — the fix narrows only the group case."""
        seam = self._seam()
        monkeypatch.setattr(seam.bot_registry, 'refusal_size_cap_patterns', lambda _bot: [r'[0-9]+ diff characters'])
        assert seam.refusal_size_cap('review limit of 4242 diff characters', 'sourcery') == '4242 diff characters'

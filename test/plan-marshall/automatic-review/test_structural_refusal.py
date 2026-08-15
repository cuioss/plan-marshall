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
_WAIT_OFFER = re.compile(
    r'"?\s*wait\s+(another|for|until)\b|\bawait\s+(the\s+)?(window|reset|limit)\b',
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
        """Branch 0 claims no window, awaits nothing, and generates no event."""
        skill = _AR_SKILL.read_text(encoding='utf-8')
        branch = _section(skill, r'Branch 0')
        assert 'do NOT await' in branch or 'Do NOT' in branch
        assert not _WAIT_OFFER.search(branch), (
            f'the structural recovery branch offers a wait:\n{branch}'
        )

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

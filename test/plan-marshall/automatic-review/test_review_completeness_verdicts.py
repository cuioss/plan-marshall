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


class TestBareListFlags:
    """Every list flag accepts a bare form that reads as the empty list."""

    def test_every_list_flag_bare_is_accepted(self, plan_context):
        """All five bare at once — the exact shape the callers produce when empty.

        Exits 0 with a real verdict instead of the pre-fix argparse rejection. An
        empty ``required_bots`` is the vacuously-satisfied quorum, so the honest
        verdict here is ``true``: there is nothing to await. The point of the case
        is that a verdict is PRODUCED at all — see
        ``test_zero_participation_with_required_bots_blocks`` for the arm where
        zero observations must block.
        """
        plan_id = 'rc-bare-all'
        plan_context.plan_dir_for(plan_id)

        result = run_script(
            SCRIPT_PATH,
            'check',
            '--plan-id',
            plan_id,
            '--required-bots',
            '--optional-bots',
            '--participated-bots',
            '--in-progress-bots',
            '--refused-bots',
        )

        assert result.success, result.stderr
        assert 'expected one argument' not in result.stderr
        assert 'status: success' in result.stdout
        assert 'participation_complete: true' in result.stdout
        assert 'proves: participation_only' in result.stdout

    def test_zero_participation_with_required_bots_blocks(self, plan_context):
        """Zero observations against a real required set is a BLOCK, never a pass.

        The four observation flags are bare — no proven participant, nothing in
        progress, nothing refused — while ``required_bots`` names two bots. The
        relaxation must not buy a pass: the run completes with exit 0 and
        ``participation_complete: false``, naming both required bots unproven.
        """
        plan_id = 'rc-bare-zero-participation'
        plan_context.plan_dir_for(plan_id)

        result = run_script(
            SCRIPT_PATH,
            'check',
            '--plan-id',
            plan_id,
            '--required-bots',
            'coderabbit,cuioss-review-bot',
            '--optional-bots',
            '--participated-bots',
            '--in-progress-bots',
            '--refused-bots',
        )

        assert result.success, result.stderr
        assert 'status: success' in result.stdout
        assert 'participation_complete: false' in result.stdout
        assert 'unproven_bots[2]' in result.stdout
        assert 'coderabbit,absent' in result.stdout
        assert 'cuioss-review-bot,absent' in result.stdout

    @pytest.mark.parametrize(('flag', 'dest'), _LIST_FLAGS)
    def test_each_flag_bare_followed_by_another_flag(self, monkeypatch, flag, dest):
        """A bare flag does not swallow the NEXT flag as its value.

        The interpolation collapse rarely leaves the bare flag last on the line —
        it is normally followed by the next ``--flag``. ``argparse`` treats a
        ``-``-prefixed token as an option rather than an optional value, so the
        bare flag still takes ``const=''`` and the following flag parses normally.
        """
        args = _parsed_check_args(
            monkeypatch,
            ['check', '--plan-id', 'rc-bare-then-flag', flag, '--triage-ran'],
        )

        assert getattr(args, dest) == ''
        assert args.triage_ran is True

    @pytest.mark.parametrize(('flag', 'dest'), _LIST_FLAGS)
    def test_each_flag_value_form_is_unchanged(self, monkeypatch, flag, dest):
        """The existing ``--flag value`` form parses exactly as before.

        Pairs with the bare-form cases so the relaxation is shown to ADD a form
        rather than replace one.
        """
        args = _parsed_check_args(monkeypatch, ['check', '--plan-id', 'rc-value-form', flag, 'coderabbit'])

        assert getattr(args, dest) == 'coderabbit'

    @pytest.mark.parametrize(('flag', 'dest'), _LIST_FLAGS)
    def test_bare_omitted_and_explicit_empty_agree(self, monkeypatch, flag, dest):
        """Bare, omitted, and explicitly-empty are the same parse: ``''``.

        This three-way agreement is what makes the bare form safe to reach by
        accident — a caller whose interpolation collapsed gets the reading it
        would have got had it quoted the placeholder or omitted the flag.
        """
        bare = _parsed_check_args(monkeypatch, ['check', '--plan-id', 'rc-agree', flag])
        omitted = _parsed_check_args(monkeypatch, ['check', '--plan-id', 'rc-agree'])
        explicit = _parsed_check_args(monkeypatch, ['check', '--plan-id', 'rc-agree', flag, ''])

        assert getattr(bare, dest) == getattr(omitted, dest) == getattr(explicit, dest) == ''

    def test_bare_flag_still_swallows_a_following_plain_value(self, monkeypatch):
        """WHY quoting is still mandatory: a bare flag DOES take a following plain token.

        ``nargs='?'`` is a parser-side backstop, not a substitute for quoting the
        interpolated placeholder. When the collapsed flag is followed by a plain
        (non ``-``-prefixed) token, argparse hands that token to the bare flag —
        so an unquoted empty ``--optional-bots`` silently steals the NEXT flag's
        value and the value-bearing flag is left empty. The docs state the two
        defences are complementary; this is the case that makes that concrete.
        """
        args = _parsed_check_args(
            monkeypatch,
            [
                'check',
                '--plan-id',
                'rc-swallow',
                '--optional-bots',
                # `--required-bots "coderabbit"` with the value collapsed away in
                # front of it: the bare --optional-bots eats 'coderabbit'.
                'coderabbit',
            ],
        )

        assert args.optional_bots == 'coderabbit'
        assert args.required_bots == ''


class TestUnknownVerdictEmitsNoParticipationField:
    """A non-zero exit never carries a ``participation_complete`` a caller could read.

    The callers treat "non-zero exit, or a return with no ``participation_complete``
    field" as an UNKNOWN verdict — explicitly not ``false`` and emphatically not
    ``true``. That routing is only sound if a crashed run cannot emit a verdict
    field at all, which is what these cases pin.
    """

    def test_argparse_rejection_emits_no_verdict(self, plan_context):
        """An unrecognised flag exits 2 with no verdict on stdout."""
        plan_id = 'rc-unknown-argparse'
        plan_context.plan_dir_for(plan_id)

        result = run_script(SCRIPT_PATH, 'check', '--plan-id', plan_id, '--not-a-real-flag', 'x')

        assert result.returncode == 2
        assert 'participation_complete' not in result.stdout

    def test_load_failure_emits_no_verdict(self, plan_context, monkeypatch, capsys):
        """The store-failure error branch exits 1 and emits no verdict field.

        ``_emit_toon`` returns immediately on the error branch, so ``status:
        error`` is the whole payload — there is no ``participation_complete`` line
        for a caller to mistake for a verdict.
        """
        plan_id = 'rc-unknown-load-failure'
        plan_context.plan_dir_for(plan_id)

        def _raise(*_args, **_kwargs):
            raise OSError('store gone')

        monkeypatch.setattr(rc, 'query_findings', _raise)

        rc_exit = rc.main(['check', '--plan-id', plan_id, '--required-bots', 'coderabbit'])

        captured = capsys.readouterr()
        assert rc_exit == 1
        assert 'participation_complete' not in captured.out


class TestDeficitSignal:
    """The comparative deficit signal — a reviewer-quality bug, never a merge verdict.

    The five corpus rows share ``required_count == 0``, yet their verdicts differ:
    deficit / deficit / unassessable / unassessable / clean. The required count alone
    cannot tell them apart; the baseline — whether any OTHER reviewer reviewed the
    same diff, and how much — is what makes the deficit assessable. Cases (b) and (c)
    are load-bearing: a detector that fires on them manufactures reviewer-quality
    bugs out of the rate limiting we already accept as normal.
    """

    def _required(self, count, reviewed=True):
        return {'bot_kind': 'cuioss-review-bot', 'reviewed': reviewed, 'finding_count': count}

    def _baseline(self, count, reviewed=True, bot='coderabbit'):
        return {'bot_kind': bot, 'reviewed': reviewed, 'finding_count': count}

    def test_row_a_deficit_four_to_zero(self):
        # Row A: a baseline reviewer produced 4 findings; the required reviewer
        # reviewed and produced 0. 4 : 0 is a deficit.
        result = rc.assess_deficit([self._required(0), self._baseline(4)], required_bots=['cuioss-review-bot'])
        assert result['verdict'] == rc.DEFICIT_DEFICIT
        assert result['deficit_reviewers'] == [{'bot_kind': 'cuioss-review-bot', 'findings': 0, 'deficit': 4}]
        assert result['baseline_max'] == 4

    def test_row_b_deficit_two_to_zero(self):
        result = rc.assess_deficit([self._required(0), self._baseline(2)], required_bots=['cuioss-review-bot'])
        assert result['verdict'] == rc.DEFICIT_DEFICIT

    def test_row_e_clean_zero_to_zero_with_a_real_baseline(self):
        # Row E — the necessary counter-example. A baseline reviewer REVIEWED and
        # found nothing; the required reviewer found nothing. 0 : 0 against a real
        # baseline is CLEAN, never a deficit. The detector MUST NOT fire here.
        result = rc.assess_deficit([self._required(0), self._baseline(0)], required_bots=['cuioss-review-bot'])
        assert result['verdict'] == rc.DEFICIT_CLEAN
        assert result['deficit_reviewers'] == []

    def test_rows_c_and_d_unassessable_when_every_baseline_refused(self):
        # Rows C and D — no baseline. Every other reviewer refused, so nothing
        # reviewed the diff besides the required bot; the run is evidence NEITHER
        # way. unassessable, NOT clean and NOT a deficit.
        result = rc.assess_deficit(
            [
                self._required(0, reviewed=False),
                self._baseline(0, reviewed=False, bot='coderabbit'),
                self._baseline(0, reviewed=False, bot='sourcery'),
            ],
            required_bots=['cuioss-review-bot'],
        )
        assert result['verdict'] == rc.DEFICIT_UNASSESSABLE
        assert result['verdict'] != rc.DEFICIT_CLEAN
        assert result['deficit_reviewers'] == []
        assert result['baseline_reviewers'] == []

    def test_required_count_alone_cannot_distinguish_the_rows(self):
        """``required_count == 0`` across all rows, yet the verdict differs.

        The sharp point of the plan: a detector keyed on the required reviewer's count
        alone would label all rows identically. Only the baseline separates deficit
        from clean from unassessable.
        """

        def verdict(baseline):
            return rc.assess_deficit(
                [{'bot_kind': 'cuioss-review-bot', 'reviewed': True, 'finding_count': 0}, *baseline],
                required_bots=['cuioss-review-bot'],
            )['verdict']

        # required_count is 0 in every call below; only the baseline varies.
        assert verdict([self._baseline(4)]) == rc.DEFICIT_DEFICIT
        assert verdict([self._baseline(0)]) == rc.DEFICIT_CLEAN
        assert verdict([self._baseline(0, reviewed=False)]) == rc.DEFICIT_UNASSESSABLE

    def test_min_deficit_threshold_is_honoured(self):
        # A 1-finding gap is a deficit at the default threshold; raising the
        # threshold above the gap makes the same shape clean.
        rows = [self._required(1), self._baseline(2)]
        assert rc.assess_deficit(rows, ['cuioss-review-bot'])['verdict'] == rc.DEFICIT_DEFICIT
        assert rc.assess_deficit(rows, ['cuioss-review-bot'], min_deficit=2)['verdict'] == rc.DEFICIT_CLEAN

    def test_signal_never_gates_the_merge(self):
        """Every deficit envelope declares itself non-gating — the cold-read requirement."""
        result = rc.assess_deficit([self._required(0), self._baseline(4)], required_bots=['cuioss-review-bot'])
        assert result['gates_merge'] is False
        assert result['proves'] == 'reviewer_quality_only'

    def test_check_deficit_reads_finding_counts_from_the_store(self, plan_context):
        """Integration: ``check_deficit`` derives counts from the pr-comment store.

        Seed a reviewing baseline with four findings and a required reviewer proven to
        have participated-but-empty; the deficit is read off the store, not passed in.
        """
        plan_id = 'rc-deficit-integration'
        plan_context.plan_dir_for(plan_id)
        for _ in range(4):
            _seed(plan_id, 'coderabbit', resolution='fixed')

        result = rc.check_deficit(
            plan_id,
            ['cuioss-review-bot'],
            optional_bots=['coderabbit'],
            participated_bots=rc.parse_participation('cuioss-review-bot:issue_comment,coderabbit:inline'),
        )

        assert result['verdict'] == rc.DEFICIT_DEFICIT
        assert result['baseline_max'] == 4
        assert {'bot_kind': 'cuioss-review-bot', 'findings': 0, 'deficit': 4} in result['deficit_reviewers']

    def test_deficit_cli_declares_non_gating(self, plan_context):
        """The CLI TOON carries ``gates_merge: false`` so a cold read sees it is no gate."""
        plan_id = 'rc-deficit-cli'
        plan_context.plan_dir_for(plan_id)
        result = run_script(
            SCRIPT_PATH,
            'deficit',
            '--plan-id',
            plan_id,
            '--required-bots',
            'cuioss-review-bot',
            '--optional-bots',
            'coderabbit,sourcery',
            '--refused-bots',
            'coderabbit,sourcery',
        )
        assert result.returncode == 0
        assert 'gates_merge: false' in result.stdout
        # Both baseline candidates refused → no baseline → unassessable, never clean.
        assert 'verdict: unassessable' in result.stdout


class TestEmittedToonRoundTrips:
    """Each of the three emitters parses back into the payload it was given."""

    def test_check_block_round_trips(self, capsys):
        from toon_parser import parse_toon

        rc._emit_toon(
            {
                'status': 'success',
                'participation_complete': False,
                'proves': 'participation_only',
                # Carries a comma, so it is quoted on the way out — the case the
                # hand-rolled emitter wrote bare.
                'review_state_summary': '2 reviewed, 1 refused',
                'pending_bots': ['sourcery'],
                'unproven_bots': ['coderabbit'],
                'bot_states': [
                    {'bot_kind': 'coderabbit', 'state': rc.STATE_ABSENT},
                    {'bot_kind': 'sourcery', 'state': rc.STATE_IN_PROGRESS},
                ],
                'measured_diff_size': '4,200 lines',
                'refusal_causes': [{'bot_kind': 'sourcery', 'cause': 'size', 'cap': ''}],
            }
        )

        emitted = parse_toon(capsys.readouterr().out)
        assert emitted['participation_complete'] is False
        assert emitted['proves'] == 'participation_only'
        assert emitted['review_state_summary'] == '2 reviewed, 1 refused'
        assert emitted['pending_bots'] == ['sourcery']
        assert emitted['unproven_bots'] == ['coderabbit']
        assert emitted['bot_states'] == [
            {'bot_kind': 'coderabbit', 'state': rc.STATE_ABSENT},
            {'bot_kind': 'sourcery', 'state': rc.STATE_IN_PROGRESS},
        ]
        assert emitted['measured_diff_size'] == '4,200 lines'
        # An unstated cap still renders as the literal ``unknown``.
        assert emitted['refusal_causes'] == [{'bot_kind': 'sourcery', 'cause': 'size', 'cap': 'unknown'}]

    def test_deficit_block_round_trips(self, capsys):
        from toon_parser import parse_toon

        rc._emit_deficit_toon(
            {
                'status': 'success',
                'verdict': 'deficit',
                'proves': 'finding_yield_only',
                'gates_merge': False,
                'baseline_max': 7,
                'baseline_reviewers': ['coderabbit'],
                'required_reviewed': ['coderabbit'],
                'deficit_reviewers': [{'bot_kind': 'sourcery', 'findings': 0, 'deficit': 7}],
                'reviewers': [
                    {
                        'bot_kind': 'sourcery',
                        'reviewed': True,
                        'finding_count': 0,
                        'state': rc.STATE_PARTICIPATED_BUT_EMPTY,
                    }
                ],
            }
        )

        emitted = parse_toon(capsys.readouterr().out)
        assert emitted['gates_merge'] is False
        assert emitted['baseline_max'] == 7
        assert emitted['deficit_reviewers'] == [{'bot_kind': 'sourcery', 'findings': 0, 'deficit': 7}]
        assert emitted['reviewers'] == [
            {
                'bot_kind': 'sourcery',
                'reviewed': True,
                'finding_count': 0,
                'state': rc.STATE_PARTICIPATED_BUT_EMPTY,
            }
        ]

    def test_size_caps_block_round_trips_the_registry_population(self, capsys):
        """The disclosure parses back over the REGISTRY's own population."""
        from toon_parser import parse_toon

        declared = rc.declared_size_caps()
        assert declared, 'the registry declares no reviewers — the round trip would be vacuous'

        rc._emit_size_caps_toon({'status': 'success', 'size_capped_reviewers': declared})

        emitted = parse_toon(capsys.readouterr().out)
        assert [row['bot_kind'] for row in emitted['size_capped_reviewers']] == [row['bot_kind'] for row in declared]
        assert [row['structural_cap'] for row in emitted['size_capped_reviewers']] == [
            bool(row['structural_cap']) for row in declared
        ]

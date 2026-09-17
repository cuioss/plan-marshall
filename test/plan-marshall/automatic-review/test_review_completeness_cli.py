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


class TestCLI:
    """The check verb's argparse surface and emitted TOON block."""

    def test_emits_toon_and_zero_exit(self, plan_context):
        plan_id = 'rc-cli'
        plan_context.plan_dir_for(plan_id)
        _seed(plan_id, 'coderabbit', resolution='pending')

        result = run_script(
            SCRIPT_PATH,
            'check',
            '--plan-id',
            plan_id,
            '--required-bots',
            'coderabbit,sourcery',
            '--participated-bots',
            'coderabbit:inline',
        )

        assert result.success, result.stderr
        assert 'status: success' in result.stdout
        assert 'participation_complete: false' in result.stdout
        assert 'proves: participation_only' in result.stdout
        assert 'pending_bots[1]' in result.stdout
        assert 'unproven_bots[1]' in result.stdout
        assert 'sourcery' in result.stdout

    def test_emits_bot_states_rows(self, plan_context):
        plan_id = 'rc-cli-states'
        plan_context.plan_dir_for(plan_id)

        result = run_script(
            SCRIPT_PATH,
            'check',
            '--plan-id',
            plan_id,
            '--required-bots',
            'coderabbit,sourcery',
            '--participated-bots',
            'coderabbit:inline',
            '--refused-bots',
            'sourcery',
        )

        assert result.success, result.stderr
        assert 'bot_states[2]{bot_kind,state}:' in result.stdout
        assert 'coderabbit,participated_but_empty' in result.stdout
        assert 'sourcery,refused_hard' in result.stdout

    def test_participated_bots_flag_proves_participation(self, plan_context):
        """Without evidence the required bots are absent; with it they are proven."""
        plan_id = 'rc-cli-participated'
        plan_context.plan_dir_for(plan_id)

        without = run_script(SCRIPT_PATH, 'check', '--plan-id', plan_id, '--required-bots', 'coderabbit,sourcery')
        assert without.success, without.stderr
        assert 'participation_complete: false' in without.stdout
        assert 'unproven_bots[2]' in without.stdout

        with_evidence = run_script(
            SCRIPT_PATH,
            'check',
            '--plan-id',
            plan_id,
            '--required-bots',
            'coderabbit,sourcery',
            '--participated-bots',
            'coderabbit:inline,sourcery:review_body',
        )
        assert with_evidence.success, with_evidence.stderr
        assert 'participation_complete: true' in with_evidence.stdout
        assert 'unproven_bots' not in with_evidence.stdout

    # -----------------------------------------------------------------------
    # --not-triggered: a BOOLEAN flag, hand-covered by necessity
    # -----------------------------------------------------------------------
    #
    # These four cases are written out rather than swept, and that is the point.
    # ``_bot_flag_derivation.derive_bot_flags`` builds its population from the live
    # parser with the regex ``--[a-z][a-z-]*-bots``, so every flag in the
    # ``--*-bots`` FAMILY inherits the bare-form / advertised-form sweeps
    # automatically — ``--stale-participation-bots`` did, gaining its coverage with
    # no edit to any suite. ``--not-triggered`` is a ``store_true`` bool and matches
    # that regex nowhere, so it inherits NOTHING and would ship entirely untested
    # while every derived sweep still reported clean. The flag is a bool because the
    # observable is PR-wide, so this gap is structural rather than incidental: any
    # future PR-wide boolean needs its own hand-written cases too.

    def test_not_triggered_flag_is_accepted_and_drives_the_verdict(self, plan_context):
        """The flag parses through the REAL CLI and changes the reported state.

        Driven through the constructed-argv subprocess runner rather than an
        in-process call, because the parser is the part no derived sweep covers for
        this flag: an in-process ``check_completeness`` call would pass even if the
        argparse declaration were missing entirely.
        """
        plan_id = 'rc-cli-not-triggered'
        plan_context.plan_dir_for(plan_id)

        result = run_script(
            SCRIPT_PATH,
            'check',
            '--plan-id',
            plan_id,
            '--required-bots',
            'coderabbit',
            '--not-triggered',
        )

        assert result.success, result.stderr
        assert result.returncode != 2, result.stderr
        assert 'participation_complete: false' in result.stdout
        assert 'coderabbit,not_triggered' in result.stdout

    def test_omitting_not_triggered_reports_absent_instead(self, plan_context):
        """The paired control through the same CLI: omitted flag keeps ``absent``.

        Isolates the flag as the only difference between the two invocations, so the
        state change cannot be attributed to anything else in the command line.
        """
        plan_id = 'rc-cli-not-triggered-omitted'
        plan_context.plan_dir_for(plan_id)

        result = run_script(SCRIPT_PATH, 'check', '--plan-id', plan_id, '--required-bots', 'coderabbit')

        assert result.success, result.stderr
        assert 'coderabbit,absent' in result.stdout
        assert 'not_triggered' not in result.stdout

    def test_not_triggered_takes_no_value(self, plan_context):
        """It is ``store_true``: a value after it is not consumed as its own.

        Pins the shape deliberately. Its list-flag siblings all declare
        ``nargs='?'``, so a reader (or a caller copying a sibling's call shape) could
        reasonably expect a value here; asserting the bool shape stops a value from
        being silently swallowed.
        """
        plan_id = 'rc-cli-not-triggered-novalue'
        plan_context.plan_dir_for(plan_id)

        result = run_script(
            SCRIPT_PATH,
            'check',
            '--plan-id',
            plan_id,
            '--required-bots',
            'coderabbit',
            '--not-triggered',
            '--optional-bots',
            'sourcery',
        )

        assert result.success, result.stderr
        # The sibling flag after it parsed its own value normally.
        assert 'coderabbit,not_triggered' in result.stdout
        assert 'sourcery,not_triggered' in result.stdout

    def test_not_triggered_is_advertised_on_the_usage_line(self):
        """The bool is advertised in the module docstring's ``Usage:`` line.

        The advertised-form agreement tests in
        ``test_bot_participation_contract.py`` are parametrized over the derived
        ``--*-bots`` family and therefore never see this flag. Without this case the
        docs could omit it indefinitely while every derived advertised-form
        assertion stayed green.
        """
        docstring = rc.__doc__ or ''

        assert '--not-triggered' in docstring

    def test_unqualified_participated_bot_is_rejected_via_cli(self, plan_context):
        """A bare bot_kind on the CLI is a VISIBLE caller error, not an absent verdict.

        The D1 disposition through the real parser: a bare kind fed to the pair-form
        ``--participated-bots`` exits non-zero with ``status: error`` and NO
        ``participation_complete`` field (read as an UNKNOWN verdict), instead of the
        pre-fix silent ``coderabbit,absent`` verdict that manufactured a false merge
        block over a bot the caller meant to record as a participant.
        """
        plan_id = 'rc-cli-bare'
        plan_context.plan_dir_for(plan_id)

        result = run_script(
            SCRIPT_PATH,
            'check',
            '--plan-id',
            plan_id,
            '--required-bots',
            'coderabbit',
            '--participated-bots',
            'coderabbit',
        )

        assert result.returncode == 1, result.stderr
        assert 'status: error' in result.stdout
        assert 'malformed_bot_flag' in result.stdout
        assert 'participation_complete' not in result.stdout

    def test_optional_bots_flag_does_not_gate(self, plan_context):
        plan_id = 'rc-cli-optional'
        plan_context.plan_dir_for(plan_id)

        result = run_script(
            SCRIPT_PATH,
            'check',
            '--plan-id',
            plan_id,
            '--required-bots',
            '',
            '--optional-bots',
            'sourcery',
        )

        assert result.success, result.stderr
        assert 'participation_complete: true' in result.stdout
        assert 'unproven_bots[1]' in result.stdout

    def test_triage_ran_flips_pending_to_incomplete(self, plan_context):
        plan_id = 'rc-cli-triage-ran'
        plan_context.plan_dir_for(plan_id)
        _seed(plan_id, 'coderabbit', resolution='pending')

        pre = run_script(
            SCRIPT_PATH,
            'check',
            '--plan-id',
            plan_id,
            '--required-bots',
            'coderabbit',
            '--participated-bots',
            'coderabbit:inline',
        )
        assert pre.success, pre.stderr
        assert 'participation_complete: true' in pre.stdout

        post = run_script(
            SCRIPT_PATH,
            'check',
            '--plan-id',
            plan_id,
            '--required-bots',
            'coderabbit',
            '--participated-bots',
            'coderabbit:inline',
            '--triage-ran',
        )
        assert post.success, post.stderr
        assert 'participation_complete: false' in post.stdout
        assert 'pending_bots[1]' in post.stdout

    def test_whitespace_in_bot_tokens_tolerated(self, plan_context):
        plan_id = 'rc-cli-ws'
        plan_context.plan_dir_for(plan_id)
        _seed(plan_id, 'coderabbit', resolution='fixed')

        result = run_script(
            SCRIPT_PATH,
            'check',
            '--plan-id',
            plan_id,
            '--required-bots',
            ' coderabbit , ',
            '--participated-bots',
            ' coderabbit : inline ',
        )

        assert result.success, result.stderr
        assert 'participation_complete: true' in result.stdout


class TestMalformedBotFlagRejection:
    """A token forwarded to the wrong flag FORM is a loud caller error, both directions.

    D1's ``Done when``, pinned end to end: a pair fed to a bare-form flag, and a bare
    kind fed to a pair-form flag. Each is a VISIBLE caller error — non-zero exit,
    ``status: error``, and NO ``participation_complete`` field, so the caller reads it
    as an UNKNOWN verdict — never the pre-fix silent ``absent`` verdict that
    manufactured a confident false merge block over a misparsed population.
    """

    # --- Unit level: the two parsers reject the wrong form ---

    def test_parse_participation_rejects_a_bare_kind(self, plan_context):
        """The pair-form parser rejects a colonless token."""
        with pytest.raises(rc.MalformedBotFlag):
            rc.parse_participation('coderabbit')

    def test_parse_participation_rejects_an_empty_sided_pair(self, plan_context):
        """An empty bot_kind or evidence_kind is a shape violation."""
        for bad in ('coderabbit:', ':inline'):
            with pytest.raises(rc.MalformedBotFlag):
                rc.parse_participation(bad)

    def test_parse_participation_names_the_flag_in_the_error(self, plan_context):
        """The caller error names WHICH flag was misused, so the fix is obvious."""
        with pytest.raises(rc.MalformedBotFlag, match='--stale-participation-bots'):
            rc.parse_participation('coderabbit', '--stale-participation-bots')

    def test_split_bots_rejects_a_pair(self, plan_context):
        """The bare-form splitter rejects a pair-shaped (colon-bearing) token."""
        with pytest.raises(rc.MalformedBotFlag):
            rc._split_bots('coderabbit:inline', '--refused-bots')

    def test_split_bots_accepts_bare_and_empty(self, plan_context):
        """The bare and empty-list forms are never malformed — only a pair is."""
        assert rc._split_bots('coderabbit,sourcery', '--refused-bots') == ['coderabbit', 'sourcery']
        assert rc._split_bots('', '--refused-bots') == []
        assert rc._split_bots('  ,  ', '--refused-bots') == []

    # --- CLI level: both directions are visible caller errors ---

    def test_bare_kind_to_pair_form_flag_is_a_caller_error(self, plan_context):
        """Direction 1 — a bare kind fed to a pair-form flag exits non-zero, no verdict."""
        plan_id = 'rc-malformed-bare-to-pair'
        plan_context.plan_dir_for(plan_id)

        result = run_script(
            SCRIPT_PATH,
            'check',
            '--plan-id',
            plan_id,
            '--required-bots',
            'coderabbit',
            '--participated-bots',
            'coderabbit',
        )

        assert result.returncode == 1, result.stderr
        assert 'status: error' in result.stdout
        assert 'malformed_bot_flag' in result.stdout
        assert 'participation_complete' not in result.stdout

    def test_pair_to_bare_form_flag_is_a_caller_error(self, plan_context):
        """Direction 2 — a pair fed to a bare-form flag exits non-zero, no verdict.

        ``--refused-bots`` is bare-form; the producer emits ``refused_bots[]`` as bare
        kinds, so a pair here is a caller error, symmetric with direction 1.
        """
        plan_id = 'rc-malformed-pair-to-bare'
        plan_context.plan_dir_for(plan_id)

        result = run_script(
            SCRIPT_PATH,
            'check',
            '--plan-id',
            plan_id,
            '--required-bots',
            'coderabbit',
            '--refused-bots',
            'coderabbit:inline',
        )

        assert result.returncode == 1, result.stderr
        assert 'status: error' in result.stdout
        assert 'malformed_bot_flag' in result.stdout
        assert 'participation_complete' not in result.stdout


class TestLoadFailure:
    """A findings-store failure is rendered as a structured error, never swallowed."""

    def test_oserror_returns_structured_error(self, plan_context, monkeypatch):
        plan_id = 'rc-oserror'
        plan_context.plan_dir_for(plan_id)

        def _raise(*_args, **_kwargs):
            raise OSError('store unreadable')

        monkeypatch.setattr(rc, 'query_findings', _raise)

        result = rc.check_completeness(plan_id, ['coderabbit'])

        assert result['status'] == 'error'
        assert result['error'] == 'load_failure'
        assert 'store unreadable' in result['detail']

    def test_valueerror_returns_structured_error(self, plan_context, monkeypatch):
        plan_id = 'rc-valueerror'
        plan_context.plan_dir_for(plan_id)

        def _raise(*_args, **_kwargs):
            raise ValueError('bad json')

        monkeypatch.setattr(rc, 'query_findings', _raise)

        result = rc.check_completeness(plan_id, ['coderabbit'])

        assert result['status'] == 'error'
        assert result['error'] == 'load_failure'
        assert 'bad json' in result['detail']

    def test_cmd_check_load_failure_nonzero_exit(self, plan_context, monkeypatch, capsys):
        plan_id = 'rc-cmd-load-fail'
        plan_context.plan_dir_for(plan_id)

        def _raise(*_args, **_kwargs):
            raise OSError('store gone')

        monkeypatch.setattr(rc, 'query_findings', _raise)

        rc_exit = rc.main(['check', '--plan-id', plan_id, '--required-bots', 'coderabbit'])

        captured = capsys.readouterr()
        assert rc_exit == 1
        assert 'status: error' in captured.out
        assert 'error: load_failure' in captured.out
        assert 'detail:' in captured.out

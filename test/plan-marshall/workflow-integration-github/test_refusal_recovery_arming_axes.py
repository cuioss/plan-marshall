"""Cross-cutting suite: a NON-CodeRabbit refusal arms the right recovery.

Detection answers per REGISTERED bot rather than for one privileged bot, and a
detected refusal is REPORTED as a refusal rather than collapsing into an
indistinguishable bare timeout. Both properties are swept over the whole registry
population here, so no bot is detection-privileged and none is left uncovered.

Cross-cutting counterpart to the co-located suites: ``test_comments_stage.py``
owns the producer's noise filters and ``test_re_review_strategy.py`` owns the
discriminators' match/no-match behaviour and the trigger-chokepoint guard. This
suite pins the ARMING — the recovery a detected refusal selects — with no
bot-name literal in the path, and the DISCLOSURE of what armed it: both producers'
refusal records carry one observation shape, and the ``automatic-review`` step
discloses that observation only when a wait was actually armed.

⛔ **The arming rule has exactly ONE definition, and it is the shipped selector.**
Every case below reaches it through :func:`github_re_review.resolve_recovery_action`;
this module keeps no class-to-recovery table of its own. A test-local model of the
rule is a second definition that can agree with the docs while the shipped code
does something else — the two drift apart silently, and the suite keeps reporting
green on the model rather than on what ships.

The selector consults the CAUSE axis first, and it dominates: a ``size`` refusal
resolves ``escalate_structural`` whatever the bot's class declares, because a
cause is observed per REFUSAL while a class is declared per BOT and one bot can
refuse for both at one class. Only a ``quota`` cause falls through to the class,
and only ``awaitable_window`` reaches the window arms — which additionally
require BOTH a window observation and an attempt budget, so an unobserved input
yields ``unmeasured`` rather than an authorizing verdict.

The bot population and every expectation are DERIVED from ``bot_registry`` and
from the selector's own published ``RECOVERY_ACTIONS`` vocabulary, never
hard-coded, so a bot added or reclassified in a standards doc is swept here
automatically.
"""
from __future__ import annotations

import importlib
import re

importlib.import_module('github_ops')
import _github_pr  # noqa: E402
import bot_registry  # noqa: E402
import github_re_review  # noqa: E402
import pytest  # noqa: E402
from _github_pr import (  # noqa: E402
    REFUSAL_LAYER_REGISTRY,
    REFUSAL_LAYER_STRUCTURAL,
    REFUSAL_LAYERS,
    _detect_rate_limited_bots,
    _extract_rate_limit_eta,
    _is_refusal_notice,
    refusal_layers,
)

from conftest import get_script_path  # noqa: E402

_ATTEMPTS_REMAINING = 2
def _verdict(
    bot_kind: str,
    cause: str = _github_pr.REFUSAL_CAUSE_QUOTA,
    *,
    window_expired: bool | None = False,
    attempts_remaining: int | None = _ATTEMPTS_REMAINING,
) -> dict:
    """The SHIPPED selector's verdict for a detected refusal from ``bot_kind``.

    The single definition of the arming rule: this module states no class-to-
    recovery table of its own, so a rule change lands here as a failing assertion
    rather than as a silent disagreement between a test-local model and the code.

    ``cause`` defaults to ``quota`` — the producer's own default for a refusal
    matching no declared size marker — so a call site passing only a bot kind
    expresses the quota case. ``window_expired=False`` is the freshly-claimed
    clock, which is the observation under which the class axis is visible: it is
    the only one where an ``awaitable_window`` bot's answer differs from an
    escalating one.
    """
    return github_re_review.resolve_recovery_action(
        bot_kind,
        cause=cause,
        window_expired=window_expired,
        attempts_remaining=attempts_remaining,
    )
def _action(bot_kind: str, cause: str = _github_pr.REFUSAL_CAUSE_QUOTA, **kwargs) -> str:
    """The recovery ACTION the shipped selector derives for ``bot_kind``."""
    return str(_verdict(bot_kind, cause, **kwargs)['action'])
def _reason(bot_kind: str, cause: str = _github_pr.REFUSAL_CAUSE_QUOTA, **kwargs) -> str:
    """The REASON the shipped selector publishes beside the action.

    Pinned separately because the action alone cannot distinguish two escalations
    that share a value: a ``hard_quota`` bot escalates for BOTH causes, and only
    the reason says which remedies the operator should be offered.
    """
    return str(_verdict(bot_kind, cause, **kwargs)['reason'])
def _declare_size_refusal(monkeypatch, bot_kind: str) -> str:
    """Make ``bot_kind`` declare a SIZE-caused refusal; return a body that matches it.

    Patched at the registry accessors the producer actually reads through
    (``bot_registry.refusal_size_patterns`` / ``refusal_size_cap_patterns``, resolved
    as module attributes at call time). That is what lets the sweep put a size
    refusal on a bot whose SHIPPED record declares none — the load-bearing case,
    because the cause axis can only be shown to dominate the class axis on a bot
    whose declared class would otherwise give a DIFFERENT answer.

    The declared size marker is one of the bot's own ``refusal_patterns``, which
    preserves the shipped subset invariant (``refusal_size_patterns`` ⊆
    ``refusal_patterns``) so detection still fires through the registry arm rather
    than depending on a marker no arm would recognise.
    """
    declared = bot_registry.refusal_patterns(bot_kind)
    assert declared, f'{bot_kind} declares no refusal phrasing to build a size refusal from'
    marker = declared[0]
    cap_regex = r'review limit of ([0-9][0-9,]*(?: [A-Za-z]+){0,2})'
    monkeypatch.setattr(
        bot_registry,
        'refusal_size_patterns',
        lambda kind, _m=marker, _b=bot_kind: [_m] if kind == _b else [],
    )
    monkeypatch.setattr(
        bot_registry,
        'refusal_size_cap_patterns',
        lambda kind, _r=cap_regex, _b=bot_kind: [_r] if kind == _b else [],
    )
    return f'{marker} — your pull request is larger than the review limit of 150,000 characters.'
_STRUCTURAL_NOTICE_BODY = (
    '> [!WARNING] > ## Usage limit reached > '
    'This reviewer has reached its usage limit. Reviews will resume after the limit resets.'
)
def _wording_body(pattern: str) -> str:
    """Wrap a declared refusal ``pattern`` in a body carrying no notice SHAPE.

    Shape-free on purpose: it isolates the REGISTRY arm, so a sweep built on this
    proves the declared WORDING was matched rather than the surrounding
    presentation rescuing it.

    The wrapper text is deliberately bland. An earlier version ended "— please try
    again later", which is itself a service-notice tail in
    ``_RATE_LIMIT_NOTICE_SHAPE_MARKERS``: it handed the structural arm its second
    condition, so bodies meant to isolate the registry arm matched BOTH and the
    isolation was silently lost. Keep this string free of callouts, limit-phrase
    headings, and any resume / reset / try-again / unable-to / paused phrasing.
    """
    return f'Context from the reviewer: {pattern}.'
def _refusal_body(bot_kind: str) -> str:
    """A refusal body SOME arm recognises for ``bot_kind``.

    Returns the bot's own first declared wording when it has one, and otherwise the
    shape-recognised :data:`_STRUCTURAL_NOTICE_BODY`.

    ⛔ **Never use this to claim REGISTRY-layer coverage.** For a bot declaring no
    wording it returns a body only the STRUCTURAL arm reads, so a sweep built on it
    reports that bot as covered while its declared-wording coverage is in fact
    ZERO — coverage borrowed from a fallback, which is exactly how an uncovered bot
    hides. The declared-wording sweep therefore parametrizes over
    :data:`_DECLARED_WORDING_PAIRS` instead, and the bots declaring nothing are
    named by their own test (:class:`TestTheDeclaredWordingSweep`).
    """
    declared = bot_registry.refusal_patterns(bot_kind)
    if declared:
        return _wording_body(declared[0])
    return _STRUCTURAL_NOTICE_BODY
_DECLARED_WORDING_PAIRS: list[tuple[str, str]] = [
    (bot_kind, pattern) for bot_kind in bot_registry.bot_kinds() for pattern in bot_registry.refusal_patterns(bot_kind)
]
_DECLARED_WORDING_POPULATION_SIZE = len(_DECLARED_WORDING_PAIRS)
_DECLARED_WORDING_POPULATION_BASELINE = 7
def _quota_refusal_body(bot_kind: str) -> str:
    """A refusal body for ``bot_kind`` whose cause is QUOTA rather than size.

    The marker is chosen by SUBTRACTING the declared size markers from the declared
    refusal markers, never by taking the first one. Sourcery's first declared
    refusal pattern is its per-PR size ceiling, so building from ``[0]`` would yield
    a size refusal and make a population-wide ``quota`` expectation false.

    Falls back to the structurally-shaped notice for a bot that declares no
    quota-only phrasing, which keeps the sweep over the whole population.
    """
    size = set(bot_registry.refusal_size_patterns(bot_kind))
    quota_markers = [m for m in bot_registry.refusal_patterns(bot_kind) if m not in size]
    if quota_markers:
        return f'This reviewer could not proceed: {quota_markers[0]} — please try again later.'
    return _STRUCTURAL_NOTICE_BODY
def _login(bot_kind: str) -> str:
    """The author login that resolves back to ``bot_kind``, from the registry map."""
    for login, kind in bot_registry.login_to_bot_kind().items():
        if kind == bot_kind:
            return login
    raise AssertionError(f'{bot_kind} declares no author_login')
def _registered_bots() -> list[str]:
    bots = bot_registry.bot_kinds()
    assert bots, 'registry must declare at least one bot'
    return bots
def _comment(bot_kind: str, body: str, created_at: str = '2026-01-09T00:00:00Z') -> dict:
    return {'author': f'{_login(bot_kind)}[bot]', 'body': body, 'created_at': created_at}
def _arm_enumerative(monkeypatch, max_chars: int = 200) -> None:
    """Give the enumerative arm a threshold, patched where the predicate READS it.

    ``github_re_review`` binds the predicate with ``from _github_pr import
    _is_unrecognised_refusal``, so the threshold name is resolved in the DEFINING
    module's namespace at call time. Patching the function's own ``__globals__``
    targets exactly that namespace, which holds whichever ``_github_pr`` object the
    SUT actually imported — patching a module object this test resolved separately
    would be a silent no-op that leaves the arm inert and fails every case below for
    a reason unrelated to the arm.
    """
    monkeypatch.setitem(
        github_re_review._is_unrecognised_refusal.__globals__,
        'UNRECOGNISED_REFUSAL_MAX_CHARS',
        max_chars,
    )
_PRODUCER_ONLY_FIELDS = {'rate_limited_bots': {'rate_limit_class'}, 'refusals': {'source'}}
_AR_SKILL = (
    get_script_path('plan-marshall', 'workflow-integration-github', '_github_pr.py').parents[4]
    / 'plan-marshall'
    / 'skills'
    / 'automatic-review'
    / 'SKILL.md'
)
_DISCLOSED = {'producer', 'layer', 'eta', 'body'}
_LOGGED = _DISCLOSED - {'body'}


class TestRecoveryArmingFollowsTheTwoAxisRule:
    """The recovery is chosen by the refusal's CAUSE first, then the bot's class.

    The cases in this class all exercise the ``quota`` arm of the rule — the one
    that reaches the class map. The cause arm, where a ``size`` refusal overrides
    the class outright, is pinned in
    :class:`TestTheCauseAxisDominatesTheClassAxis` below.
    """

    @pytest.mark.parametrize('bot_kind', _registered_bots())
    def test_detected_refusal_reports_the_bots_own_class(self, bot_kind):
        """The record carries the class, so the caller need not re-derive it."""
        detected = _detect_rate_limited_bots([_comment(bot_kind, _refusal_body(bot_kind))])

        assert detected[0]['rate_limit_class'] == bot_registry.rate_limit_class(bot_kind)

    @pytest.mark.parametrize('bot_kind', _registered_bots())
    def test_the_class_arms_exactly_one_recovery(self, bot_kind):
        """Every declared class maps to a defined recovery — none is unhandled.

        The admissible pair is the CLASS partition of a quota refusal made with
        both observations present: wait, or escalate as not-awaitable. Reaching
        ``unmeasured`` here would mean the class axis never decided anything.
        """
        detected = _detect_rate_limited_bots([_comment(bot_kind, _refusal_body(bot_kind))])

        assert detected[0]['rate_limit_class'] == bot_registry.rate_limit_class(bot_kind)
        assert _action(bot_kind) in (
            github_re_review.RECOVERY_ACTION_AWAIT_WINDOW,
            github_re_review.RECOVERY_ACTION_ESCALATE_NOT_AWAITABLE,
        )

    def test_an_awaitable_window_arms_a_wait_on_the_claim(self):
        """A window that reopens on its own makes waiting productive work."""
        awaitable = [b for b in _registered_bots() if bot_registry.rate_limit_class(b) == 'awaitable_window']
        assert awaitable, 'registry must declare at least one awaitable_window bot'

        for bot in awaitable:
            assert _action(bot) == github_re_review.RECOVERY_ACTION_AWAIT_WINDOW

    def test_a_hard_quota_escalates_immediately(self):
        """A rate/budget quota that does not reopen usefully, so awaiting burns it.

        ``hard_quota`` is an AWAITABILITY verdict about a rate or budget limit — a
        weekly cap, a plan-level allowance — and deliberately NOT a per-PR size
        ceiling. The size ceiling lives on the orthogonal CAUSE axis
        (``refused_structural``), which this class cannot answer: Sourcery declares
        ``hard_quota`` and refuses for BOTH causes, so reading a per-PR ceiling off
        the class conflates two remedies that have nothing in common.

        This is the distinction the class exists to carry: treating every bot's
        refusal as awaitable would spend the full window timeout here and still
        time out.
        """
        hard = [b for b in _registered_bots() if bot_registry.rate_limit_class(b) == 'hard_quota']
        assert hard, 'registry must declare at least one hard_quota bot'

        for bot in hard:
            assert _action(bot) == github_re_review.RECOVERY_ACTION_ESCALATE_NOT_AWAITABLE

    def test_an_unknown_class_escalates_immediately(self):
        """FAIL-CLOSED (ADR-009): an unverified class is never treated as awaitable.

        Awaiting a quota that never reopens is the expensive failure, so a bot with
        no observed refusal escalates rather than waits.
        """
        unknown = [b for b in _registered_bots() if bot_registry.rate_limit_class(b) == 'unknown']
        assert unknown, 'registry must declare at least one unknown-class bot'

        for bot in unknown:
            assert _action(bot) == github_re_review.RECOVERY_ACTION_ESCALATE_NOT_AWAITABLE

    def test_no_registered_bot_has_an_unhandled_class(self):
        """Totality: the selector names a recovery for every declared class.

        The admissible population is the selector's OWN published vocabulary, so a
        recovery added there joins this check with no test edit — and
        ``unmeasured`` is excluded, because "no verdict was computed" is not a
        recovery the class arms.
        """
        assert github_re_review.RECOVERY_ACTIONS, 'the action vocabulary is empty — this is vacuous'

        for bot in _registered_bots():
            action = _action(bot)
            assert action in github_re_review.RECOVERY_ACTIONS, bot
            assert action != github_re_review.RECOVERY_ACTION_UNMEASURED, bot
class TestTheCauseAxisDominatesTheClassAxis:
    """A SIZE refusal escalates structurally, whatever the bot's class declares.

    The discriminating population is bots whose declared class is NOT already an
    escalating one: on a ``hard_quota`` bot both axes escalate, so the value would
    be right for the wrong reason and the case could not show the cause was read at
    all. An ``awaitable_window`` bot is the only place the two axes give DIFFERENT
    answers, which is what makes it load-bearing here.
    """

    @staticmethod
    def _awaitable_bots() -> list[str]:
        bots = [b for b in _registered_bots() if bot_registry.rate_limit_class(b) == 'awaitable_window']
        assert bots, 'registry must declare an awaitable_window bot for this to discriminate'
        return bots

    def test_a_size_refusal_from_an_awaitable_bot_reports_cause_size_and_its_cap(self, monkeypatch):
        """The producer record carries the cause and the ceiling the notice stated."""
        for bot in self._awaitable_bots():
            body = _declare_size_refusal(monkeypatch, bot)

            detected = _detect_rate_limited_bots([_comment(bot, body)])

            assert [r['bot_kind'] for r in detected] == [bot]
            assert detected[0]['cause'] == _github_pr.REFUSAL_CAUSE_SIZE
            # The class is UNCHANGED and still awaitable — the record carries both
            # axes, so the cause is demonstrably not derived from the class.
            assert detected[0]['rate_limit_class'] == 'awaitable_window'
            # Read off the notice, comma-stripped for the CLI boundary.
            assert detected[0]['cap'] == '150000 characters'

    def test_that_size_refusal_arms_structural_escalation_not_a_window_wait(self, monkeypatch):
        """The whole point: waiting is not offered for a ceiling waiting cannot move.

        Paired with its matched negative control — the SAME bot, same class, same
        window observation, whose refusal is a QUOTA — which must still arm the
        wait. Without the control this would also pass on an implementation that
        escalated every refusal structurally.
        """
        for bot in self._awaitable_bots():
            body = _declare_size_refusal(monkeypatch, bot)
            detected = _detect_rate_limited_bots([_comment(bot, body)])
            cause = detected[0]['cause']

            assert _action(bot, cause) == github_re_review.RECOVERY_ACTION_ESCALATE_STRUCTURAL
            assert _action(bot, cause) != github_re_review.RECOVERY_ACTION_AWAIT_WINDOW
            # Matched negative control: same bot, same declared class, quota cause.
            assert _action(bot, _github_pr.REFUSAL_CAUSE_QUOTA) == github_re_review.RECOVERY_ACTION_AWAIT_WINDOW

    def test_a_hard_quota_bots_size_refusal_escalates_for_the_size_ceiling(self, monkeypatch):
        """Its reason is ``size_ceiling``, never ``class_not_awaitable``.

        Both causes escalate for a ``hard_quota`` bot, so the ACTION alone cannot
        tell them apart — the REASON is what distinguishes them, and it decides
        which remedies the operator is offered. Reporting a size refusal as
        ``class_not_awaitable`` describes a window that was never the problem.
        """
        hard = [b for b in _registered_bots() if bot_registry.rate_limit_class(b) == 'hard_quota']
        assert hard, 'registry must declare at least one hard_quota bot'

        for bot in hard:
            _declare_size_refusal(monkeypatch, bot)

            assert _reason(bot, _github_pr.REFUSAL_CAUSE_SIZE) == 'size_ceiling'
            assert _reason(bot, _github_pr.REFUSAL_CAUSE_SIZE) != 'class_not_awaitable'
            # Matched negative control: the same bot's QUOTA refusal keeps the
            # temporal reason, so the size branch is not simply relabelling both.
            assert _reason(bot, _github_pr.REFUSAL_CAUSE_QUOTA) == 'class_not_awaitable'
            # ...and the ACTION is identical across both, which is exactly why the
            # reason has to carry the distinction.
            assert _action(bot, _github_pr.REFUSAL_CAUSE_QUOTA) == (
                github_re_review.RECOVERY_ACTION_ESCALATE_NOT_AWAITABLE
            )

    def test_a_quota_refusal_reports_cause_quota_and_an_empty_cap(self):
        """Swept over the whole population, on a body chosen to BE a quota refusal.

        The quota marker is selected by SUBTRACTING the declared size markers from
        the declared refusal markers, never by taking the first one: Sourcery's
        first declared refusal pattern IS its per-PR size ceiling, so a blanket
        "every shipped refusal is quota" assertion over this population is simply
        false. The empty cap is the UNKNOWN reading, never a fabricated figure.
        """
        for bot in _registered_bots():
            detected = _detect_rate_limited_bots([_comment(bot, _quota_refusal_body(bot))])
            assert detected, bot

            assert detected[0]['cause'] == _github_pr.REFUSAL_CAUSE_QUOTA, bot
            assert detected[0]['cap'] == '', bot

    def test_the_shipped_size_refusal_reports_its_cause_and_its_stated_cap(self):
        """The real registry config end-to-end — nothing monkeypatched.

        The cases above patch a size marker onto a bot to isolate the axis
        interaction; this one asserts that a bot which ALREADY declares a size
        ceiling in its shipped standards doc is classified from that declaration,
        with the ceiling read off the notice it posted. Without it the whole cause
        axis could pass on patched data while the shipped registry wired nothing.

        EVERY declared size marker is swept, not just the first: a bot may declare
        several size-caused refusals (Sourcery declares its own character ceiling
        and the GitHub API's file-count one), and asserting only ``[0]`` would let a
        later addition ship unexercised.

        The body is synthesised from BOTH declarations because they are not one
        string. A detection marker need not be a prefix of the cap phrase — CodeRabbit
        detects on ``Too many files!`` and states its ceiling as ``over the limit of
        N`` — so the cap pattern's literal lead-in is derived from the pattern itself
        rather than assumed to follow the marker.
        """
        sized = [b for b in _registered_bots() if bot_registry.refusal_size_patterns(b)]
        assert sized, 'registry must ship at least one bot declaring a size ceiling'

        for bot in sized:
            cap_patterns = bot_registry.refusal_size_cap_patterns(bot)
            assert cap_patterns, f'{bot} declares a size cause but no cap extractor'
            # The literal text each cap regex reads its figure after.
            lead = cap_patterns[0].split('(')[0]

            for marker in bot_registry.refusal_size_patterns(bot):
                body = f'Sorry, {marker} — {lead}150,000 characters.'

                detected = _detect_rate_limited_bots([_comment(bot, body)])

                assert [r['bot_kind'] for r in detected] == [bot], (bot, marker)
                assert detected[0]['cause'] == _github_pr.REFUSAL_CAUSE_SIZE, (bot, marker)
                assert detected[0]['cap'].startswith('150000'), (bot, marker, detected[0]['cap'])

    def test_both_axis_keys_are_present_on_every_record(self):
        """One record shape whatever the cause — a consumer never probes for a key."""
        for bot in _registered_bots():
            detected = _detect_rate_limited_bots([_comment(bot, _refusal_body(bot))])
            assert detected, bot

            assert 'cause' in detected[0], bot
            assert 'cap' in detected[0], bot
class TestTheEnumerativeArmOnTheReReviewPath:
    """An unrecognised refusal is RECORDED here too — never admitted as a review.

    This is the worse half of the blind spot. On the producer path an unrecognised
    refusal became a finding a human could at least read; here it reached
    ``_match_review``, which admits any body that is "not a refusal notice" — so the
    envelope asserted ``head_sha_verified: true`` for a HEAD the bot had declined.
    """

    def test_with_no_threshold_the_record_producer_is_unchanged(self):
        """The fail-safe: at the SHIPPED value the enumerative arm never fires.

        D1 derived no threshold, so ``_refusal_record`` behaves byte-identically to
        how it behaved before this arm existed — an unrecognised body still returns
        ``None``. Asserted at the shipped value rather than a patched one, so this
        pins what actually ships.
        """
        assert github_re_review._is_unrecognised_refusal.__globals__['UNRECOGNISED_REFUSAL_MAX_CHARS'] is None
        for bot in _registered_bots():
            assert (
                github_re_review._ReReviewStrategy._refusal_record('Skipping this one.', bot, 'issue_comment') is None
            )

    @pytest.mark.parametrize('bot_kind', _registered_bots())
    def test_an_unrecognised_refusal_is_recorded_under_the_enumerative_arm(self, bot_kind, monkeypatch):
        """With a threshold available the reworded refusal is recorded, not returned None.

        The body reaches no earlier arm — asserted — so the record can only come from
        the enumerative one, and its ``layer`` is read from the shared vocabulary.
        """
        _arm_enumerative(monkeypatch)
        body = 'Skipping this one.'

        # Neither earlier arm sees it — that is what makes the record enumerative.
        assert _github_pr._is_refusal_notice(body, bot_kind) is False

        record = github_re_review._ReReviewStrategy._refusal_record(body, bot_kind, 'issue_comment')

        assert record is not None
        assert record['layer'] == _github_pr.REFUSAL_LAYER_ENUMERATIVE
        assert record['bot_kind'] == bot_kind

    @pytest.mark.parametrize('bot_kind', _registered_bots())
    def test_an_unrecognised_refusal_is_still_a_refusal_and_states_no_eta(self, bot_kind, monkeypatch):
        """It arms A recovery rather than vanishing into a timeout — and claims no ETA.

        What the enumerative arm supports is deliberately narrow: the body was not
        review feedback. It read nothing further, so the record states no ETA —
        nothing can be claimed about when the window reopens. Which recovery the
        envelope then arms is a separate question, settled by
        ``_resolve_refusal_class`` and pinned below rather than here.
        """
        _arm_enumerative(monkeypatch)
        record = github_re_review._ReReviewStrategy._refusal_record('Skipping this one.', bot_kind, 'issue_comment')

        assert record is not None
        # It is a refusal, so it arms a recovery rather than vanishing into a timeout.
        assert _action(bot_kind) in (
            github_re_review.RECOVERY_ACTION_AWAIT_WINDOW,
            github_re_review.RECOVERY_ACTION_ESCALATE_NOT_AWAITABLE,
        )
        # And it states no ETA — nothing was read, so nothing can be claimed about
        # when the window reopens.
        assert record['eta'] == ''

    @pytest.mark.parametrize('bot_kind', _registered_bots())
    def test_a_genuine_short_review_with_an_anchor_is_still_not_a_refusal(self, bot_kind, monkeypatch):
        """Matched negative control: the arm does not swallow a real short review.

        Same bot, same length class, same armed threshold — the only difference is a
        code anchor, which is what a genuine review carries and a status notice does
        not. Without this control the positive case above would also pass on an arm
        that classified every short comment as a refusal.
        """
        _arm_enumerative(monkeypatch)

        record = github_re_review._ReReviewStrategy._refusal_record(
            'Guard the bound at `src/idx.py:12`.', bot_kind, 'review'
        )

        assert record is None

    def test_a_genuine_review_is_not_recorded_as_a_refusal(self):
        """Precision guard on the recording path, across the whole population."""
        for bot in _registered_bots():
            record = github_re_review._ReReviewStrategy._refusal_record(
                'Reviewed the new HEAD. Guard the backoff cap before the loop.',
                bot,
                'review',
            )
            assert record is None, bot

    def test_a_human_quoting_a_refusal_never_arms_a_recovery(self):
        """Authorship is resolved through the registry map, so a human contributes nothing."""
        bots = _registered_bots()
        human = [
            {
                'author': 'octocat',
                'body': _refusal_body(bots[0]),
                'created_at': '2026-01-09T00:00:00Z',
            }
        ]

        assert _detect_rate_limited_bots(human) == []
class TestUnreadRefusalNeverReportsAnAwaitableClass:
    """``refusal_class`` on the envelope, when an arm could not read the notice.

    The envelope publishes ``layer`` and ``refusal_class`` side by side, so the pair
    must not contradict itself: ``enumerative_unrecognised`` beside
    ``awaitable_window`` asserts a window nobody observed, and the caller arms a wait
    on it. This is the re-review half of the override ``review_completeness`` applies
    through ``--unrecognised-refusal-bots``; the contract requires both recognition
    sites to name the same state for one refusal, which is why the quantifier here is
    pinned to the sibling's rather than chosen independently.
    """

    @staticmethod
    def _enumerative(bot_kind: str) -> dict:
        return {'bot_kind': bot_kind, 'layer': _github_pr.REFUSAL_LAYER_ENUMERATIVE, 'eta': ''}

    @staticmethod
    def _registry(bot_kind: str) -> dict:
        return {'bot_kind': bot_kind, 'layer': _github_pr.REFUSAL_LAYER_REGISTRY, 'eta': ''}

    def test_no_refusal_resolves_to_the_empty_string(self):
        """Nothing was detected, so there is no recovery to arm."""
        assert github_re_review._resolve_refusal_class('coderabbit', []) == ''

    @pytest.mark.parametrize('bot_kind', _registered_bots())
    def test_an_unread_refusal_resolves_unknown(self, bot_kind):
        """Swept over the WHOLE population — no bot is exempt from the override."""
        resolved = github_re_review._resolve_refusal_class(bot_kind, [self._enumerative(bot_kind)])

        assert resolved == 'unknown'

    def test_the_awaitable_window_bot_is_the_load_bearing_case(self):
        """The case the override exists for, with its matched negative control.

        A ``hard_quota`` bot resolves ``unknown`` either way, so sweeping the
        population alone cannot show the override does anything: the value would be
        right for the wrong reason. The discriminator is a bot whose DECLARED class
        differs from ``unknown`` — only there does reading the declared class produce
        a different, wrong answer. The control is the SAME bot with a refusal an
        earlier arm DID read, which must still report the declared class.
        """
        awaitable = [b for b in _registered_bots() if bot_registry.rate_limit_class(b) == 'awaitable_window']
        assert awaitable, 'registry must declare an awaitable_window bot for this to discriminate'

        for bot in awaitable:
            # Unread notice: the declared awaitability is NOT asserted.
            assert github_re_review._resolve_refusal_class(bot, [self._enumerative(bot)]) == 'unknown'
            # Matched negative control — same bot, a notice the registry arm READ.
            assert github_re_review._resolve_refusal_class(bot, [self._registry(bot)]) == 'awaitable_window'

    def test_a_mixed_set_matches_the_completeness_sites_quantifier(self):
        """The parity case: one readable refusal alongside an unreadable one.

        ``review_completeness`` receives this observation as a per-BOT membership test
        over a list the producer fills one record per COMMENT, so such a bot IS inside
        its override and classifies ``refused_unknown``. An ``all``-quantifier here
        would report the declared class instead, leaving the two recognition sites
        naming different states for one bot — the divergence the contract forbids.

        This case is therefore a PARITY assertion, not a preference: it fails if this
        side is quantified independently of the sibling, in either direction.
        """
        for bot in _registered_bots():
            mixed = [self._registry(bot), self._enumerative(bot)]

            assert github_re_review._resolve_refusal_class(bot, mixed) == 'unknown'

    def test_an_unattributable_refusal_fails_closed_to_unknown(self):
        """No bot_kind means no declared class to read — never an awaitable guess."""
        assert github_re_review._resolve_refusal_class(None, [self._registry('')]) == 'unknown'

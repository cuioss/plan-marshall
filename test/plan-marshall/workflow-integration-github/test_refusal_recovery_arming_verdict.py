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
def _bots_declaring_no_wording() -> list[str]:
    """The registered bots whose declared-wording coverage is ZERO."""
    return [b for b in _registered_bots() if not bot_registry.refusal_patterns(b)]
_DECLARED_WORDING_PAIRS: list[tuple[str, str]] = [
    (bot_kind, pattern) for bot_kind in bot_registry.bot_kinds() for pattern in bot_registry.refusal_patterns(bot_kind)
]
_DECLARED_WORDING_POPULATION_SIZE = len(_DECLARED_WORDING_PAIRS)
_DECLARED_WORDING_POPULATION_BASELINE = 7
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
def _bots_of_class(rate_class: str) -> list[str]:
    """The registered bots declaring ``rate_class``, asserted non-empty."""
    bots = [b for b in _registered_bots() if bot_registry.rate_limit_class(b) == rate_class]
    assert bots, f'registry must declare at least one {rate_class} bot for this to discriminate'
    return bots
def _set_trigger_semantics(monkeypatch, bot_kind: str, value: str) -> None:
    """Re-declare ``bot_kind``'s ``trigger_semantics`` in the parsed registry record.

    Patched at the RECORD rather than at the accessor, so the real
    ``trigger_semantics`` read — including its closed-set validation and its
    fail-closed default — is the one the selector still travels through.
    """
    record = dict(bot_registry.REGISTRY._by_kind[bot_kind])
    record['trigger_semantics'] = value
    monkeypatch.setitem(bot_registry.REGISTRY._by_kind, bot_kind, record)
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
def _section(heading_prefix: str) -> str:
    """Return the ``automatic-review`` SKILL.md section whose heading starts ``heading_prefix``.

    The section runs to the next heading at the same or a shallower level, with
    fenced code skipped so a ``#`` inside a block never ends it early.
    """
    lines = _AR_SKILL.read_text(encoding='utf-8').splitlines()
    starts = [i for i, line in enumerate(lines) if line.startswith(heading_prefix)]
    assert len(starts) == 1, f'expected one heading starting {heading_prefix!r}, found {len(starts)}'
    start = starts[0]
    level = len(heading_prefix) - len(heading_prefix.lstrip('#'))
    in_fence = False
    for end in range(start + 1, len(lines)):
        line = lines[end]
        if line.lstrip().startswith('```'):
            in_fence = not in_fence
            continue
        if not in_fence and re.match(rf'#{{1,{level}}} ', line):
            return '\n'.join(lines[start:end])
    return '\n'.join(lines[start:])
def _armed_line() -> str:
    """The ARMED decision-log ``--message`` line in Branch 2."""
    matches = [line for line in _section('#### Branch 2').splitlines() if 'refusal recovery ARMED' in line]
    assert len(matches) == 1, f'expected one ARMED message line in Branch 2, found {len(matches)}'
    return matches[0]


class TestTheDeclaredWordingSweep:
    """Every DECLARED refusal wording is matched by the registry arm — all of them.

    Parametrized over the ``(bot_kind, pattern)`` pair population rather than over
    bots, because a per-bot sweep reaches only each bot's FIRST wording and leaves
    every later one unswept.
    """

    def test_the_pair_population_is_non_empty_and_publishes_its_size(self):
        """⛔ Vacuity guard for the derived sweep below, with the size STATED.

        A ``parametrize`` over an empty population produces zero cases and reports
        green — the sweep would look like coverage while certifying nothing. The
        population is therefore asserted non-empty AND its size published, so the
        breadth of the sweep is a number a reader can reconcile against the
        registry instead of an implicit one.
        """
        assert _DECLARED_WORDING_PAIRS, (
            'no registered bot declares any refusal_patterns — the declared-wording sweep below would be vacuous'
        )
        assert _DECLARED_WORDING_POPULATION_SIZE == len(_DECLARED_WORDING_PAIRS)
        # Every pair belongs to a registered bot — the population cannot drift onto
        # a bot the registry does not declare.
        assert {bot for bot, _ in _DECLARED_WORDING_PAIRS} <= set(_registered_bots())

    def test_the_population_size_matches_its_reconciled_baseline(self):
        """⛔ Shrinkage tripwire: a DELETED wording must fail, not silently vanish.

        The sweep derives its cases, which is what keeps an ADDED wording covered
        automatically — but it also means a wording removed from a registry doc
        simply removes a case, leaving a smaller sweep passing green. Comparing the
        derived size against the reconciled baseline is what makes that removal a
        named failure instead of invisible coverage loss.
        """
        assert _DECLARED_WORDING_POPULATION_SIZE == _DECLARED_WORDING_POPULATION_BASELINE, (
            f'declared refusal wordings moved from {_DECLARED_WORDING_POPULATION_BASELINE} '
            f'to {_DECLARED_WORDING_POPULATION_SIZE}. If a wording was added or removed on '
            f'purpose, update _DECLARED_WORDING_POPULATION_BASELINE in the same commit. '
            f'Current population: {_DECLARED_WORDING_PAIRS}'
        )

    def test_the_wrapper_itself_contributes_no_notice_shape(self):
        """⛔ Fixture control: the isolation must come from the wording, not the wrapper.

        Every "registry arm only" assertion in this suite depends on
        :func:`_wording_body` being shape-free. If the wrapper ever supplies a
        notice shape, those assertions quietly widen to "registry OR structural"
        and isolate nothing — which already happened once, with a "please try again
        later" tail.

        The probe carries a phrase that satisfies the structural arm's
        LIMIT-EXCEEDED condition and is attributed to no bot, so the registry arm
        cannot fire. The only thing that could add ``structural_fallback`` is a
        SHAPE contributed by the wrapper itself.
        """
        probe = _wording_body('usage limit reached')

        assert refusal_layers(probe, None) == []

    @pytest.mark.parametrize(
        ('bot_kind', 'pattern'),
        _DECLARED_WORDING_PAIRS,
        ids=[f'{bot}-{pattern[:38]}' for bot, pattern in _DECLARED_WORDING_PAIRS],
    )
    def test_each_declared_wording_is_detected_by_the_registry_layer(self, bot_kind, pattern):
        """Each wording is matched by the bot's OWN declaration, not by shape.

        The body deliberately carries no notice shape, so the structural arm cannot
        rescue a wording the registry failed to match — the registry layer is
        isolated and the assertion is about the declaration itself.
        """
        body = _wording_body(pattern)

        layers = refusal_layers(body, bot_kind)

        assert REFUSAL_LAYER_REGISTRY in layers, (
            f'{bot_kind} declares {pattern!r} but the registry arm did not match it'
        )
        # The boolean seam agrees — a declared wording is a refusal.
        assert _is_refusal_notice(body, bot_kind) is True

    def test_a_declared_wording_does_not_leak_across_bots(self):
        """One bot's wording must not mark ANOTHER bot's comment as refusing.

        The registry arm is bot-scoped. Without this, a shared marker would let a
        bot that reviewed fine be recorded as having declined.
        """
        for bot_kind, pattern in _DECLARED_WORDING_PAIRS:
            for other in _registered_bots():
                if other == bot_kind or pattern in bot_registry.refusal_patterns(other):
                    continue
                assert REFUSAL_LAYER_REGISTRY not in refusal_layers(_wording_body(pattern), other)

    def test_a_bot_declaring_no_wording_is_named_and_covered_only_structurally(self):
        """Uncovered bots are NAMED here rather than hidden behind a fallback.

        ``_refusal_body`` substitutes a shape-recognised notice for a bot declaring
        no wording, which would let that bot appear covered by the declared-wording
        sweep while contributing zero pairs to it. This test states which bots those
        are and what their coverage actually is: the structural arm only, with no
        declared wording to sweep. Its count is published for the same reason the
        pair population's is — an empty list here is a real state (every bot
        declares wording), not a skipped check.
        """
        uncovered = _bots_declaring_no_wording()
        # Published: how many registered bots contribute NOTHING to the sweep above.
        assert len(uncovered) == len(_registered_bots()) - len({bot for bot, _ in _DECLARED_WORDING_PAIRS})

        for bot in uncovered:
            assert bot_registry.refusal_patterns(bot) == []
            # Only shape can recognise a refusal from this bot.
            assert refusal_layers(_STRUCTURAL_NOTICE_BODY, bot) == [REFUSAL_LAYER_STRUCTURAL]
            # And a shape-free body reaches NO arm at this position.
            assert refusal_layers('Skipping this one.', bot) == []
class TestTheRecoveryActionSelectorDerivesItsVerdict:
    """``resolve_recovery_action`` reads the registry rather than assuming a bot.

    The ORDER of its arms is load-bearing, and each case below is the one that
    fails when its step is moved: an empty population must not be answered with a
    verdict that reads as derived; an observed size CAUSE must outrank a declared
    class; a class that is not awaitable must never reach a window arm; and a
    missing observation must yield no verdict at all rather than an authorizing
    one.
    """

    def test_an_empty_registry_is_unmeasured_rather_than_a_derived_verdict(self, monkeypatch):
        """⛔ A verdict over an empty population would read as derived while being blind.

        With no bots registered ``rate_limit_class`` fails closed to ``unknown``
        and the class arm would answer ``escalate_not_awaitable`` — a real-looking
        escalation computed over nothing. Publishing the population and declining
        to name a verdict is the honest answer.

        Its matched control is the SAME call against the real registry, which must
        NOT be ``unmeasured``: without it this would pass on a selector that
        answered ``unmeasured`` for everything.
        """
        bot_kind = _registered_bots()[0]
        assert _action(bot_kind) != github_re_review.RECOVERY_ACTION_UNMEASURED

        monkeypatch.setattr(bot_registry.REGISTRY, '_by_kind', {})
        verdict = _verdict(bot_kind)

        assert verdict['action'] == github_re_review.RECOVERY_ACTION_UNMEASURED
        assert verdict['reason'] == 'registry_empty'
        assert verdict['known_bot_kinds'] == []
        assert verdict['known_bot_kind_count'] == 0

    def test_a_non_awaitable_class_never_reaches_a_window_arm(self):
        """Fail-closed: the window observations cannot buy a wait for a class that has none.

        Swept over BOTH window states and both budget states, because reaching a
        window arm is exactly what these inputs would do for an awaitable bot —
        the matched control below shows they do.
        """
        non_awaitable = _bots_of_class('hard_quota') + _bots_of_class('unknown')
        window_arms = (
            github_re_review.RECOVERY_ACTION_AWAIT_WINDOW,
            github_re_review.RECOVERY_ACTION_CLOSE_AND_REOPEN,
            github_re_review.RECOVERY_ACTION_GENERATE_TRIGGER,
        )

        for bot in non_awaitable:
            for expired in (True, False):
                for attempts in (0, _ATTEMPTS_REMAINING):
                    action = _action(bot, window_expired=expired, attempts_remaining=attempts)

                    assert action not in window_arms, (bot, expired, attempts)
                    assert action == github_re_review.RECOVERY_ACTION_ESCALATE_NOT_AWAITABLE

    def test_the_same_window_inputs_do_reach_a_window_arm_for_an_awaitable_class(self):
        """MATCHED CONTROL — the inputs above are genuinely window-arm-reaching.

        Without this the sweep above would pass on a selector that never reached a
        window arm for anyone, which is a different (and equally broken) code.
        """
        for bot in _bots_of_class('awaitable_window'):
            assert _action(bot, window_expired=False) == github_re_review.RECOVERY_ACTION_AWAIT_WINDOW
            assert _action(bot, window_expired=True) in (
                github_re_review.RECOVERY_ACTION_CLOSE_AND_REOPEN,
                github_re_review.RECOVERY_ACTION_GENERATE_TRIGGER,
            )

    def test_close_and_reopen_needs_an_elapsed_window_on_an_explicit_trigger_bot(self, monkeypatch):
        """Re-DELIVERING a dropped request is worth nothing before the claim is up.

        Close-and-reopen buys back no quota — the limit is ACCOUNT-scoped and no
        PR-level move touches it — so an OPEN claim must still resolve the wait.
        The matched control is the same bot with the same elapsed window and an
        ``auto_on_push`` declaration, which gets ``generate_trigger`` instead:
        that is what shows the arm is chosen from the registry's trigger semantics
        rather than being the fixed answer for an elapsed window.
        """
        for bot in _bots_of_class('awaitable_window'):
            _set_trigger_semantics(monkeypatch, bot, bot_registry.TRIGGER_SEMANTICS_REQUIRES_EXPLICIT_TRIGGER)
            assert _action(bot, window_expired=True) == github_re_review.RECOVERY_ACTION_CLOSE_AND_REOPEN
            # Same bot, same semantics, claim still running: no close-and-reopen.
            assert _action(bot, window_expired=False) == github_re_review.RECOVERY_ACTION_AWAIT_WINDOW

            _set_trigger_semantics(monkeypatch, bot, bot_registry.TRIGGER_SEMANTICS_AUTO_ON_PUSH)
            assert _action(bot, window_expired=True) == github_re_review.RECOVERY_ACTION_GENERATE_TRIGGER

    def test_the_elapsed_arm_is_named_for_the_claim_clock_not_the_bots_readiness(self, monkeypatch):
        """⛔ ``claim_window_elapsed`` — what elapsed is the CLAIM, not the bot's window.

        A stated ETA is an estimate and the real window slides, so a reason
        claiming the bot has reopened would assert something nobody observed. The
        evidence that the name describes the CLAIM is that both elapsed arms —
        close-and-reopen and generate-trigger — publish the SAME reason while
        naming different moves: the reason cannot be a property of the bot's
        readiness if it does not vary with the bot's trigger semantics.
        """
        for bot in _bots_of_class('awaitable_window'):
            _set_trigger_semantics(monkeypatch, bot, bot_registry.TRIGGER_SEMANTICS_REQUIRES_EXPLICIT_TRIGGER)
            explicit = _verdict(bot, window_expired=True)

            _set_trigger_semantics(monkeypatch, bot, bot_registry.TRIGGER_SEMANTICS_AUTO_ON_PUSH)
            auto = _verdict(bot, window_expired=True)

            assert explicit['reason'] == 'claim_window_elapsed'
            assert auto['reason'] == explicit['reason']
            assert explicit['action'] != auto['action']
            # The OPEN claim names the clock too, from the other side.
            assert _reason(bot, window_expired=False) == 'claim_window_open'

    def test_an_unregistered_bot_kind_fails_closed_by_derivation(self):
        """The stale token lands on the class arm because the REGISTRY resolves it there.

        There is no unknown-bot list: ``rate_limit_class`` fails closed to
        ``unknown`` for a kind it does not know, and the ordinary class arm does
        the rest. The matched control is a REGISTERED bot whose declared class is
        also ``unknown`` — it must reach the identical action and reason, so the
        two verdicts differ ONLY in ``bot_kind_registered``. A special-cased
        unknown-bot branch could not produce that agreement.
        """
        stale = _verdict('some-retired-bot')
        registered_unknown = _verdict(_bots_of_class('unknown')[0])

        assert stale['action'] == github_re_review.RECOVERY_ACTION_ESCALATE_NOT_AWAITABLE
        assert stale['reason'] == registered_unknown['reason'] == 'class_not_awaitable'
        assert stale['action'] == registered_unknown['action']
        assert stale['rate_limit_class'] == bot_registry.rate_limit_class('some-retired-bot')
        assert stale['bot_kind_registered'] is False
        assert registered_unknown['bot_kind_registered'] is True

    def test_every_arm_publishes_the_inputs_its_derivation_read(self):
        """One verdict SHAPE across every arm, and the whole vocabulary is reached.

        A consumer must never probe for a key, so the derived-input fields are
        asserted present on every arm rather than on the happy one. The arm table
        is also checked to COVER the selector's published ``RECOVERY_ACTIONS``: a
        member no case reaches is either an arm nothing can select or one this
        suite forgot, and both are worth failing on.
        """
        awaitable = _bots_of_class('awaitable_window')[0]
        not_awaitable = _bots_of_class('hard_quota')[0]
        size = _github_pr.REFUSAL_CAUSE_SIZE
        arms = [
            (_verdict(awaitable, size), github_re_review.RECOVERY_ACTION_ESCALATE_STRUCTURAL, 'size_ceiling'),
            (
                _verdict(not_awaitable),
                github_re_review.RECOVERY_ACTION_ESCALATE_NOT_AWAITABLE,
                'class_not_awaitable',
            ),
            (
                _verdict(awaitable, window_expired=None),
                github_re_review.RECOVERY_ACTION_UNMEASURED,
                'no_window_observation',
            ),
            (
                _verdict(awaitable, attempts_remaining=None),
                github_re_review.RECOVERY_ACTION_UNMEASURED,
                'no_attempt_budget_observation',
            ),
            (
                _verdict(awaitable, attempts_remaining=0),
                github_re_review.RECOVERY_ACTION_ESCALATE_EXHAUSTED,
                'attempt_cap_exhausted',
            ),
            (_verdict(awaitable), github_re_review.RECOVERY_ACTION_AWAIT_WINDOW, 'claim_window_open'),
            (
                _verdict(awaitable, window_expired=True),
                github_re_review.RECOVERY_ACTION_CLOSE_AND_REOPEN,
                'claim_window_elapsed',
            ),
        ]
        derived_inputs = (
            'bot_kind',
            'cause',
            'rate_limit_class',
            'trigger_semantics',
            'known_bot_kinds',
            'known_bot_kind_count',
            'bot_kind_registered',
            'window_expired',
            'attempts_remaining',
            'attempt_held',
            'recovery_actions',
        )

        for verdict, expected_action, expected_reason in arms:
            assert verdict['action'] == expected_action
            assert verdict['reason'] == expected_reason
            for field in derived_inputs:
                assert field in verdict, (expected_action, field)
            assert verdict['recovery_actions'] == list(github_re_review.RECOVERY_ACTIONS)

        reached = {verdict['action'] for verdict, _a, _r in arms}
        # ``generate_trigger`` is unreachable without re-declaring a bot's trigger
        # semantics, which is the neighbouring test's subject; it is named here so
        # the coverage claim states its one exclusion rather than hiding it.
        assert reached | {github_re_review.RECOVERY_ACTION_GENERATE_TRIGGER} == set(
            github_re_review.RECOVERY_ACTIONS
        ), f'arms reached {sorted(reached)} of {sorted(github_re_review.RECOVERY_ACTIONS)}'
class TestBothProducersCarryOneObservationShape:
    """``rate_limited_bots[]`` and ``refusals[]`` record a refusal in ONE shape.

    A wait can be armed off either producer's record, so the arming disclosure can
    name the layer that read the notice and what the notice said only if BOTH
    records carry them. Before the widening only ``refusals[]`` did, and a wait
    armed off ``rate_limited_bots[]`` could not say what it was waiting on.
    """

    @staticmethod
    def _both(bot_kind: str, body: str) -> tuple[dict, dict]:
        [detected] = _detect_rate_limited_bots([_comment(bot_kind, body)])
        refusal = github_re_review._ReReviewStrategy._refusal_record(body, bot_kind, 'issue_comment')
        assert refusal is not None, bot_kind
        return detected, refusal

    @pytest.mark.parametrize('bot_kind', _registered_bots())
    def test_the_records_differ_only_in_their_producer_specific_field(self, bot_kind):
        """Swept over the whole population — one shape whatever the bot."""
        detected, refusal = self._both(bot_kind, _refusal_body(bot_kind))

        assert set(detected) - _PRODUCER_ONLY_FIELDS['rate_limited_bots'] == (
            set(refusal) - _PRODUCER_ONLY_FIELDS['refusals']
        )
        assert {'layer', 'body'} <= set(detected)

    @pytest.mark.parametrize('bot_kind', _registered_bots())
    @pytest.mark.parametrize('body_kind', ['declared_or_shape', 'shape_only'])
    def test_the_two_producers_name_one_observation_for_one_notice(self, bot_kind, body_kind):
        """Same notice, same bot: the same layer, excerpt, ETA, cause and cap.

        Swept over a body the bot's own wording reads (where it declares any) AND
        the shape-only notice, so both pre-filter arms are exercised — a producer
        resolving the layer precedence differently would disagree on the first.
        """
        body = _refusal_body(bot_kind) if body_kind == 'declared_or_shape' else _STRUCTURAL_NOTICE_BODY
        detected, refusal = self._both(bot_kind, body)

        shared = set(detected) - _PRODUCER_ONLY_FIELDS['rate_limited_bots']
        for field in sorted(shared):
            assert detected[field] == refusal[field], (bot_kind, body_kind, field)

    def test_the_excerpt_is_one_line_and_bounded_on_both_producers(self):
        """A multi-line notice never reaches either record raw."""
        bot = _registered_bots()[0]
        raw = _STRUCTURAL_NOTICE_BODY + '\n\n' + '\n'.join(['Reviews will resume after the limit resets.'] * 20)

        detected, refusal = self._both(bot, raw)

        for record in (detected, refusal):
            assert '\n' not in record['body']
            assert record['body'].endswith('...')
        assert detected['body'] == refusal['body']
class TestTheArmingDisclosureIsEmittedOnlyWhenAWaitIsArmed:
    """The emit / no-emit control pair over the ``automatic-review`` step contract.

    The disclosure is workflow prose executed by the step, so its contract is the
    document: the arming branch must name the observation on the decision log AND
    declare it on the envelope, and the branches that escalate WITHOUT arming must
    carry no arming record at all — not an empty one.
    """

    def test_the_armed_line_names_the_observation_that_armed_the_wait(self):
        """EMIT: producer, layer and ETA ride the ARMED decision-log line."""
        placeholders = dict(re.findall(r'(\w+)=\{(\w+)\}', _armed_line()))

        assert _LOGGED <= set(placeholders), sorted(placeholders)
        for fact in _LOGGED:
            assert placeholders[fact] == fact

    def test_the_untrusted_excerpt_is_never_interpolated_into_the_log_command(self):
        """⛔ The excerpt is bot text and ``--message`` is a shell argument.

        The matched negative half of the case above: the log line must name the
        other disclosed facts AND must not carry this one. Pinned as its own
        assertion because ``_LOGGED <= placeholders`` is satisfied by a line that
        also interpolates the excerpt — a subset test cannot refuse an extra field,
        so the exclusion has to be asserted rather than implied.

        Escaping was the rejected alternative: an apostrophe is ordinary English
        ("doesn't", "your plan's limit"), so a prose instruction to rewrite each one
        fires on routine input rather than only on a crafted notice. The excerpt is
        carried on the envelope row instead, which the next case pins.
        """
        placeholders = dict(re.findall(r'(\w+)=\{(\w+)\}', _armed_line()))

        assert 'body' not in placeholders, _armed_line()

    def test_the_armed_line_quotes_its_remaining_bot_supplied_field_safely(self):
        """The ``--message`` value must be single-quoted even without the excerpt.

        ``{eta}`` is still the reset time the NOTICE stated, so bot-supplied text
        remains in the command. Inside double quotes a backtick or ``$`` is command
        substitution, and refusal notices quote the bot's own trigger command.
        """
        armed = _armed_line().strip()

        assert armed.startswith("--message '"), armed
        assert armed.endswith("'"), armed

    def test_the_envelope_declares_the_full_disclosure_including_the_excerpt(self):
        """EMIT: the envelope row is the COMPLETE record, so it survives a resume.

        It is a superset of what the log names — the excerpt is carried here and
        nowhere else, which is what makes its removal from the log line a relocation
        rather than a loss of the fact.
        """
        output = _section('## Output')
        match = re.search(r'rate_window_arming\[N\]\{([^}]*)\}', output)
        assert match, 'Output declares no rate_window_arming[] field'

        declared = {field.strip() for field in match.group(1).split(',')}

        assert declared == _DISCLOSED | {'bot_kind'}
        assert _LOGGED < declared

    def test_every_disclosed_fact_but_the_producer_is_read_off_a_refusal_record(self):
        """Read, never re-derived: each disclosed fact is a field BOTH producers emit."""
        bot = _registered_bots()[0]
        [detected] = _detect_rate_limited_bots([_comment(bot, _STRUCTURAL_NOTICE_BODY)])
        refusal = github_re_review._ReReviewStrategy._refusal_record(_STRUCTURAL_NOTICE_BODY, bot, 'issue_comment')

        record_facts = _DISCLOSED - {'producer'}

        assert record_facts <= set(detected)
        assert record_facts <= set(refusal)

    @pytest.mark.parametrize(
        'heading',
        [
            pytest.param('#### Branch 0', id='branch-0-structural'),
            pytest.param('#### Branch 1', id='branch-1-not-awaitable'),
        ],
    )
    def test_a_branch_that_escalates_without_arming_discloses_no_arming_record(self, heading):
        """NO-EMIT — the matched negative control.

        Branches 0 and 1 escalate without claiming a window, so they arm nothing and
        must disclose nothing: no ARMED line, no arming placeholders, and no envelope
        field. An empty or defaulted record would read as a wait armed on nothing.
        """
        branch = _section(heading)

        assert 'refusal recovery ARMED' not in branch
        assert 'rate_window_arming' not in branch
        assert not {fact for fact in _DISCLOSED if f'{fact}={{{fact}}}' in branch}

    def test_the_output_contract_states_the_field_is_absent_when_nothing_was_armed(self):
        """The absence is the contract, stated where the field is declared."""
        output = _section('## Output')

        assert 'ABSENT' in output
        assert 'Branch 0 and Branch 1' in output

#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Cross-cutting suite: a NON-CodeRabbit refusal arms the right recovery.

Fail-first suite for D2 (registry-driven per-bot detection) and D4 (refusal
recovery). Against the pre-fix code the detector selected CodeRabbit-authored
comments only and a detected refusal was ``continue``-d into an indistinguishable
bare timeout, so every assertion below about a non-CodeRabbit bot's refusal — and
every assertion that a refusal is not reported as a bare timeout — was red.

Cross-cutting counterpart to the co-located suites: ``test_comments_stage.py``
owns the producer's noise filters and ``test_re_review_strategy.py`` owns the
discriminators' match/no-match behaviour. This suite pins the ARMING — the recovery a
detected refusal selects — under the shipped TWO-AXIS rule, with no bot-name
literal in the path. The CAUSE axis is consulted first and dominates:

    cause == size  -> escalate structurally (split / accept / disable; NEVER wait)

Only a ``quota`` cause falls through to the refusing bot's own declared
``rate_limit_class``:

    awaitable_window -> claim and await the window
    hard_quota       -> escalate immediately (nothing reopens by waiting)
    unknown          -> escalate immediately (fail-closed, ADR-009)

The cause outranks the class because a cause is observed per REFUSAL while a
class is declared per BOT, and one bot can refuse for both causes at one class.
Reading the class alone is the defect this ordering closes: an
``awaitable_window`` bot refusing because the DIFF is too big would otherwise be
handed a claim-and-await for a ceiling no amount of waiting moves.

The bot population and every class expectation are DERIVED from
``bot_registry``, never hard-coded, so a bot added or reclassified in a standards
doc is swept here automatically.
"""

from __future__ import annotations

import importlib

# ``github_ops`` MUST be resolved FIRST: importing ``_github_pr`` before it fails
# outright with a partially-initialised-module ImportError, because the two close
# an import cycle. It is reached through ``import_module`` rather than an
# ``import`` statement because isort sorts ``_github_pr`` ahead of ``github_ops``,
# so no arrangement of plain imports can express the ordering. That one statement
# is what puts the imports below out of the file's import block, which is the
# whole of the per-line ``E402`` waivers they carry.
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

# The recovery each rate-limit class arms. This is the CLASS axis of the mapping
# under test; it is expressed once here and applied to whatever population the
# registry declares. It is reached only for a ``quota``-caused refusal.
_RECOVERY_BY_CLASS = {
    'awaitable_window': 'claim_and_await',
    'hard_quota': 'escalate_immediately',
    'unknown': 'escalate_immediately',
}

# The recovery a SIZE-caused refusal arms, on the cause axis. Its own value rather
# than a reuse of ``escalate_immediately``: the remedy sets are disjoint — a
# temporal refusal may be waited out or accepted, a structural one is answered by
# splitting the diff, accepting the gap, or disabling the reviewer for this PR.
_RECOVERY_STRUCTURAL = 'escalate_structural'

# The escalation ``reason`` each arming surfaces on the envelope, so a test can
# pin WHICH escalation fired rather than only that one did. ``claim_and_await``
# is absent because it escalates nothing.
_ESCALATION_REASON = {
    _RECOVERY_STRUCTURAL: 'refusal_structural',
    'escalate_immediately': 'rate_window_not_awaitable',
}


def _arms(bot_kind: str, cause: str = _github_pr.REFUSAL_CAUSE_QUOTA) -> str:
    """The recovery a detected refusal from ``bot_kind`` arms, under the two-axis rule.

    The CAUSE axis is consulted FIRST and dominates: a ``size`` refusal is over a
    per-PR diff ceiling, so the same request never succeeds while the diff is this
    size — it arms a structural escalation whatever the bot's declared class says.
    Only a ``quota`` cause falls through to the per-bot class map.

    ``cause`` defaults to ``quota`` because that is the producer's own default for a
    refusal matching no declared size marker, so an existing call site that passes
    only a bot kind still expresses the case it always expressed.
    """
    if cause == _github_pr.REFUSAL_CAUSE_SIZE:
        return _RECOVERY_STRUCTURAL
    return _RECOVERY_BY_CLASS[bot_registry.rate_limit_class(bot_kind)]


def _escalation_reason(bot_kind: str, cause: str) -> str:
    """The ``reason`` the envelope escalates with, or ``''`` when it awaits instead."""
    return _ESCALATION_REASON.get(_arms(bot_kind, cause), '')


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


#: A notice recognised by SHAPE alone — no bot declares this phrasing, so only the
#: structural arm can match it. Hoisted out of :func:`_refusal_body` so the
#: structural case is reachable by name instead of only as a silent fallback.
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


#: The ``(bot_kind, pattern)`` PAIR population — every refusal wording the registry
#: declares, across every registered bot. Re-derived here from the same accessors
#: the producer reads, never restated: a wording added to a ``standards/{bot}.md``
#: doc joins the sweep below with no test edit.
#:
#: The sweep is parametrized over PAIRS rather than over bots because a per-bot
#: sweep tests only each bot's FIRST wording — Sourcery declares two, and the
#: second (its weekly quota notice) went unswept entirely under a per-bot loop.
_DECLARED_WORDING_PAIRS: list[tuple[str, str]] = [
    (bot_kind, pattern)
    for bot_kind in bot_registry.bot_kinds()
    for pattern in bot_registry.refusal_patterns(bot_kind)
]

#: PUBLISHED population size. A parametrized sweep over an empty population yields
#: zero cases and still reports green, so the count is stated rather than implied —
#: the guard below fails loudly instead of certifying nothing.
_DECLARED_WORDING_POPULATION_SIZE = len(_DECLARED_WORDING_PAIRS)

#: The population size this suite was last RECONCILED against. A deliberate
#: tripwire, not a derivation: because the sweep derives its cases, DELETING a
#: wording from a registry doc silently removes a case and the sweep still passes
#: at a smaller size. Comparing against this constant converts that silent
#: shrinkage into a named failure. When a wording is added or removed on purpose,
#: update this number in the same commit — the mismatch message says so.
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


class TestNonCodeRabbitRefusalIsDetected:
    """Detection answers per REGISTERED bot, not for one privileged bot."""

    @pytest.mark.parametrize('bot_kind', _registered_bots())
    def test_every_registered_bots_refusal_is_detected(self, bot_kind):
        """Sweep the WHOLE population — no bot is detection-privileged.

        The retired discriminator selected CodeRabbit-authored comments only, so a
        refusing Sourcery or PR-Agent scored negative outright. Deriving the sweep
        from ``bot_kinds()`` means a bot added later cannot silently reintroduce
        that blind spot.
        """
        detected = _detect_rate_limited_bots([_comment(bot_kind, _refusal_body(bot_kind))])

        assert [r['bot_kind'] for r in detected] == [bot_kind]

    def test_one_bots_refusal_does_not_mask_another_bots_healthy_review(self):
        """Each bot is answered independently, never collapsed into one verdict.

        The retired detector collapsed the bots' states: a refusing Sourcery
        scored negative whenever CodeRabbit's own newest comment was a real review.
        """
        bots = _registered_bots()
        refuser, *others = bots
        comments = [_comment(refuser, _refusal_body(refuser), '2026-01-09T00:00:00Z')]
        for other in others:
            comments.append(
                _comment(other, 'Actionable comment: guard the array bound.', '2026-01-02T00:00:00Z')
            )

        detected = _detect_rate_limited_bots(comments)

        assert [r['bot_kind'] for r in detected] == [refuser]

    def test_a_healthy_review_from_every_bot_detects_nothing(self):
        """Precision guard: a real review is never reported as a refusal."""
        comments = [
            _comment(bot, 'Reviewed the diff. One issue: the retry cap can be zero.')
            for bot in _registered_bots()
        ]

        assert _detect_rate_limited_bots(comments) == []

    def test_a_successful_review_section_is_not_a_refusal(self):
        """A bot's ``ignore_patterns`` sections must NOT read as a refusal.

        ``ignore_patterns`` names routine parts of a SUCCESSFUL review (a
        walkthrough heading, a learnings notice). Detecting refusals off that list
        would report a bot that reviewed fine as having declined — the reason
        ``refusal_patterns`` is a separate field.
        """
        for bot in _registered_bots():
            for marker in bot_registry.ignore_patterns(bot):
                detected = _detect_rate_limited_bots([_comment(bot, marker)])
                assert detected == [], f'{bot}: ignore marker {marker!r} read as a refusal'


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
        """Every declared class maps to a defined recovery — none is unhandled."""
        detected = _detect_rate_limited_bots([_comment(bot_kind, _refusal_body(bot_kind))])

        assert detected[0]['rate_limit_class'] in _RECOVERY_BY_CLASS
        assert _arms(bot_kind) in ('claim_and_await', 'escalate_immediately')

    def test_an_awaitable_window_arms_claim_and_await(self):
        """A window that reopens on its own makes waiting productive work."""
        awaitable = [b for b in _registered_bots() if bot_registry.rate_limit_class(b) == 'awaitable_window']
        assert awaitable, 'registry must declare at least one awaitable_window bot'

        for bot in awaitable:
            assert _arms(bot) == 'claim_and_await'

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
            assert _arms(bot) == 'escalate_immediately'

    def test_an_unknown_class_escalates_immediately(self):
        """FAIL-CLOSED (ADR-009): an unverified class is never treated as awaitable.

        Awaiting a quota that never reopens is the expensive failure, so a bot with
        no observed refusal escalates rather than waits.
        """
        unknown = [b for b in _registered_bots() if bot_registry.rate_limit_class(b) == 'unknown']
        assert unknown, 'registry must declare at least one unknown-class bot'

        for bot in unknown:
            assert _arms(bot) == 'escalate_immediately'

    def test_no_registered_bot_has_an_unhandled_class(self):
        """Totality: the class→recovery mapping covers the whole population."""
        for bot in _registered_bots():
            assert bot_registry.rate_limit_class(bot) in _RECOVERY_BY_CLASS


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
            'no registered bot declares any refusal_patterns — the declared-wording '
            'sweep below would be vacuous'
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
        assert len(uncovered) == len(_registered_bots()) - len(
            {bot for bot, _ in _DECLARED_WORDING_PAIRS}
        )

        for bot in uncovered:
            assert bot_registry.refusal_patterns(bot) == []
            # Only shape can recognise a refusal from this bot.
            assert refusal_layers(_STRUCTURAL_NOTICE_BODY, bot) == [REFUSAL_LAYER_STRUCTURAL]
            # And a shape-free body reaches NO arm at this position.
            assert refusal_layers('Skipping this one.', bot) == []


class TestTheProvenanceSeam:
    """``refusal_layers`` tells the arms apart where the boolean cannot."""

    def test_a_registry_only_body_and_a_structural_only_body_are_told_apart(self):
        """The seam's whole purpose: two refusals the boolean reports identically.

        Both bodies are refusals and ``_is_refusal_notice`` returns ``True`` for
        each, so the boolean cannot distinguish a wording the bot DECLARED from one
        recognised by shape alone. The seam reports which arm fired, which is what
        makes the difference actionable.
        """
        sized = [b for b in _registered_bots() if bot_registry.refusal_patterns(b)]
        assert sized, 'registry must declare a bot with refusal wording'

        for bot in sized:
            registry_only = _wording_body(bot_registry.refusal_patterns(bot)[0])

            assert refusal_layers(registry_only, bot) == [REFUSAL_LAYER_REGISTRY]
            assert refusal_layers(_STRUCTURAL_NOTICE_BODY, bot) == [REFUSAL_LAYER_STRUCTURAL]
            # ...while the boolean reports the SAME verdict for both.
            assert _is_refusal_notice(registry_only, bot) is True
            assert _is_refusal_notice(_STRUCTURAL_NOTICE_BODY, bot) is True

    def test_the_boolean_is_exactly_the_any_projection_of_the_seam(self):
        """The boolean is DERIVED, so the two can never disagree.

        Swept over every body shape this suite uses, in both bot-scoped and
        unattributed form. A parallel implementation would be free to drift; this
        pins that it is a projection.
        """
        bodies = [
            _STRUCTURAL_NOTICE_BODY,
            'Skipping this one.',
            'Reviewed the diff. Guard the retry cap before the loop.',
            '',
        ] + [_wording_body(p) for _, p in _DECLARED_WORDING_PAIRS]

        for bot in [*_registered_bots(), None]:
            for body in bodies:
                assert _is_refusal_notice(body, bot) is bool(refusal_layers(body, bot))

    def test_every_reported_layer_is_from_the_shared_vocabulary(self):
        """The seam names arms from ``REFUSAL_LAYERS``, never its own spellings."""
        assert REFUSAL_LAYERS, 'the layer vocabulary is empty — this check is vacuous'

        for bot in _registered_bots():
            for body in (_refusal_body(bot), _STRUCTURAL_NOTICE_BODY):
                for layer in refusal_layers(body, bot):
                    assert layer in REFUSAL_LAYERS

    def test_an_unattributed_body_can_only_reach_the_structural_arm(self):
        """With no ``bot_kind`` there is no declaration to read."""
        assert refusal_layers(_STRUCTURAL_NOTICE_BODY, None) == [REFUSAL_LAYER_STRUCTURAL]
        for _bot, pattern in _DECLARED_WORDING_PAIRS:
            assert refusal_layers(_wording_body(pattern), None) == []


class TestTriggerSemanticsIsDeclaredByEveryBot:
    """Every registered bot declares a value from the CLOSED trigger-semantics set."""

    def test_every_registered_bot_declares_a_value_in_the_closed_set(self):
        """Registry-derived: the population is the bot set, the set is the vocabulary.

        Both sides derived — the bots from ``bot_kinds()`` and the admissible values
        from ``TRIGGER_SEMANTICS_VALUES`` — so neither a new bot nor a new value can
        leave this assertion silently stale.
        """
        assert bot_registry.TRIGGER_SEMANTICS_VALUES, 'the vocabulary is empty'

        for bot in _registered_bots():
            assert bot_registry.trigger_semantics(bot) in bot_registry.TRIGGER_SEMANTICS_VALUES

    def test_the_declared_value_is_read_from_the_doc_not_the_fail_closed_default(self):
        """⛔ Matched control: proves the docs DECLARE it rather than defaulting.

        Every shipped bot declares ``requires_explicit_trigger``, which is also the
        fail-closed default — so the sweep above passes identically on three docs
        that declare nothing at all. Reading the RAW parsed record is what
        discriminates a real declaration from an absent one.
        """
        for bot in _registered_bots():
            raw = bot_registry.REGISTRY._by_kind.get(bot, {}).get('trigger_semantics')
            assert isinstance(raw, str) and raw.strip(), (
                f'{bot} does not DECLARE trigger_semantics — it is only inheriting the '
                f'fail-closed default, which this test exists to distinguish'
            )

    def test_an_unregistered_bot_fails_closed_to_requires_explicit_trigger(self):
        """The safe direction: never assume a bot reviews on push."""
        assert (
            bot_registry.trigger_semantics('no-such-bot')
            == bot_registry.TRIGGER_SEMANTICS_REQUIRES_EXPLICIT_TRIGGER
        )

    def test_a_value_outside_the_closed_set_fails_closed(self, monkeypatch):
        """A malformed doc edit degrades safely rather than propagating a bad value."""
        bot = _registered_bots()[0]
        record = dict(bot_registry.REGISTRY._by_kind[bot])
        record['trigger_semantics'] = 'sometimes_maybe'
        monkeypatch.setitem(bot_registry.REGISTRY._by_kind, bot, record)

        assert (
            bot_registry.trigger_semantics(bot)
            == bot_registry.TRIGGER_SEMANTICS_REQUIRES_EXPLICIT_TRIGGER
        )


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
        bots = [
            b for b in _registered_bots() if bot_registry.rate_limit_class(b) == 'awaitable_window'
        ]
        assert bots, 'registry must declare an awaitable_window bot for this to discriminate'
        return bots

    def test_a_size_refusal_from_an_awaitable_bot_reports_cause_size_and_its_cap(
        self, monkeypatch
    ):
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

    def test_that_size_refusal_arms_structural_escalation_not_claim_and_await(self, monkeypatch):
        """The whole point: waiting is not offered for a ceiling waiting cannot move.

        Paired with its matched negative control — the SAME bot, same class, whose
        refusal is a QUOTA — which must still arm ``claim_and_await``. Without the
        control this would also pass on an implementation that escalated every
        refusal structurally.
        """
        for bot in self._awaitable_bots():
            body = _declare_size_refusal(monkeypatch, bot)
            detected = _detect_rate_limited_bots([_comment(bot, body)])
            cause = detected[0]['cause']

            assert _arms(bot, cause) == _RECOVERY_STRUCTURAL
            assert _arms(bot, cause) != 'claim_and_await'
            # Matched negative control: same bot, same declared class, quota cause.
            assert _arms(bot, _github_pr.REFUSAL_CAUSE_QUOTA) == 'claim_and_await'

    def test_a_hard_quota_bots_size_refusal_escalates_as_refusal_structural(self, monkeypatch):
        """Its reason is ``refusal_structural``, never ``rate_window_not_awaitable``.

        Both causes escalate for a ``hard_quota`` bot, so the arming alone cannot
        tell them apart — the REASON is what distinguishes them, and it decides
        which remedies the operator is offered. Reporting a size refusal as
        ``rate_window_not_awaitable`` describes a window that was never the problem.
        """
        hard = [b for b in _registered_bots() if bot_registry.rate_limit_class(b) == 'hard_quota']
        assert hard, 'registry must declare at least one hard_quota bot'

        for bot in hard:
            _declare_size_refusal(monkeypatch, bot)

            assert _escalation_reason(bot, _github_pr.REFUSAL_CAUSE_SIZE) == 'refusal_structural'
            assert _escalation_reason(bot, _github_pr.REFUSAL_CAUSE_SIZE) != 'rate_window_not_awaitable'
            # Matched negative control: the same bot's QUOTA refusal keeps the
            # temporal reason, so the size branch is not simply relabelling both.
            assert (
                _escalation_reason(bot, _github_pr.REFUSAL_CAUSE_QUOTA)
                == 'rate_window_not_awaitable'
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


class TestTheEtaExtractorCannotRaise:
    """A registry pattern that COMPILES but captures nothing must not crash the poll.

    ``match.groups()`` is truthy for a one-tuple holding ``None``, so a pattern whose
    declared group sits in a branch that did not participate matched, reported
    groups, and yielded ``None`` — and ``.strip()`` on that raised an AttributeError
    out of the producer's whole return path. The ``re.error`` guard does not cover
    it: that guard catches a pattern that will not COMPILE, not one that compiles and
    captures nothing.
    """

    _BODY = 'Usage limit reached. Try again in 18 minutes.'

    def test_a_declared_group_that_captured_nothing_yields_no_eta(self, monkeypatch):
        """The crash case: the first branch matches, the group is in the second."""
        monkeypatch.setattr(
            bot_registry, 'rate_limit_eta_patterns', lambda _kind: [r'limit reached|(ZZZ)']
        )

        for bot in _registered_bots():
            # The assertion is that this RETURNS at all — pre-fix it raised.
            assert _extract_rate_limit_eta(self._BODY, bot) == ''

    def test_an_empty_group_moves_to_the_next_pattern_never_to_group_zero(self, monkeypatch):
        """No fallback from an empty group to the whole match.

        The group(0) fallback is the wrong kind of graceful: it would return the
        prose ``"limit reached"`` as though the notice had stated that as its ETA.
        The honest behaviour is to yield nothing and let the NEXT pattern answer,
        which is what this pins — the returned figure is the second pattern's.
        """
        monkeypatch.setattr(
            bot_registry,
            'rate_limit_eta_patterns',
            lambda _kind: [r'limit reached|(ZZZ)', r'in ([0-9]+ minutes)'],
        )

        for bot in _registered_bots():
            assert _extract_rate_limit_eta(self._BODY, bot) == '18 minutes'

    def test_the_matched_control_a_capturing_pattern_still_yields_its_figure(self, monkeypatch):
        """Matched positive control: the fix did not simply disable extraction."""
        monkeypatch.setattr(
            bot_registry, 'rate_limit_eta_patterns', lambda _kind: [r'in ([0-9]+ minutes)']
        )

        for bot in _registered_bots():
            assert _extract_rate_limit_eta(self._BODY, bot) == '18 minutes'

    def test_a_group_less_pattern_still_returns_the_whole_match(self, monkeypatch):
        """The no-group convention is preserved — group(0) remains the answer there."""
        monkeypatch.setattr(
            bot_registry, 'rate_limit_eta_patterns', lambda _kind: [r'[0-9]+ minutes']
        )

        for bot in _registered_bots():
            assert _extract_rate_limit_eta(self._BODY, bot) == '18 minutes'


class TestRefusalIsNeverABareTimeout:
    """End-to-end: a detected refusal is reported AS a refusal, not as silence."""

    @pytest.mark.parametrize('bot_kind', _registered_bots())
    def test_every_registered_bot_resolves_a_re_review_strategy(self, bot_kind):
        """A refusal can only arm a recovery for a bot the pipeline can re-trigger."""
        assert github_re_review.resolve_strategy(bot_kind) is not None

    @pytest.mark.parametrize('bot_kind', _registered_bots())
    def test_a_refusal_is_recorded_not_swallowed(self, bot_kind):
        """The refusal record is what distinguishes "declined" from "never answered".

        Before D4 both were the same bare ``matched: false`` / ``timed_out: true``
        and the refusal vanished, so the caller could not tell a bot that
        explicitly declined from one that simply never responded.
        """
        record = github_re_review._ReReviewStrategy._refusal_record(
            _refusal_body(bot_kind), bot_kind, 'issue_comment'
        )

        assert record is not None, f'{bot_kind} refusal must be recorded'
        assert record['bot_kind'] == bot_kind
        # The admissible population is DERIVED from the shared vocabulary, never
        # restated as a literal pair: a hand-written tuple here would keep passing
        # while the producer emitted an arm the tuple had never heard of, which is
        # the drift this vocabulary exists to prevent.
        assert REFUSAL_LAYERS, 'the layer vocabulary is empty — this check is vacuous'
        assert record['layer'] in REFUSAL_LAYERS

    @pytest.mark.parametrize('bot_kind', _registered_bots())
    def test_a_bots_declared_refusal_is_recognized_as_DATA(self, bot_kind):
        """A bot with declared refusal phrasing is matched by the registry layer.

        The distinction matters, and the arms are ordered by how much they KNOW:
        recognition as DATA means the bot's own observed text is on file, the
        structural arm merely inferred a notice from its shape, and the enumerative
        arm knows only that the body was not review feedback. Sourcery's real
        refusal is the motivating case — the structural recognizer is blind to it,
        so only the registry arm can see it.
        """
        if not bot_registry.refusal_patterns(bot_kind):
            pytest.skip(f'{bot_kind} declares no observed refusal phrasing')

        record = github_re_review._ReReviewStrategy._refusal_record(
            _refusal_body(bot_kind), bot_kind, 'issue_comment'
        )

        assert record['layer'] == _github_pr.REFUSAL_LAYER_REGISTRY


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
        assert (
            github_re_review._is_unrecognised_refusal.__globals__['UNRECOGNISED_REFUSAL_MAX_CHARS']
            is None
        )
        for bot in _registered_bots():
            assert (
                github_re_review._ReReviewStrategy._refusal_record(
                    'Skipping this one.', bot, 'issue_comment'
                )
                is None
            )

    @pytest.mark.parametrize('bot_kind', _registered_bots())
    def test_an_unrecognised_refusal_is_recorded_under_the_enumerative_arm(
        self, bot_kind, monkeypatch
    ):
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
    def test_an_unrecognised_refusal_is_still_a_refusal_and_states_no_eta(
        self, bot_kind, monkeypatch
    ):
        """It arms A recovery rather than vanishing into a timeout — and claims no ETA.

        What the enumerative arm supports is deliberately narrow: the body was not
        review feedback. It read nothing further, so the record states no ETA —
        nothing can be claimed about when the window reopens. Which recovery the
        envelope then arms is a separate question, settled by
        ``_resolve_refusal_class`` and pinned below rather than here.
        """
        _arm_enumerative(monkeypatch)
        record = github_re_review._ReReviewStrategy._refusal_record(
            'Skipping this one.', bot_kind, 'issue_comment'
        )

        assert record is not None
        # It is a refusal, so it arms a recovery rather than vanishing into a timeout.
        assert _arms(bot_kind) in ('claim_and_await', 'escalate_immediately')
        # And it states no ETA — nothing was read, so nothing can be claimed about
        # when the window reopens.
        assert record['eta'] == ''

    @pytest.mark.parametrize('bot_kind', _registered_bots())
    def test_a_genuine_short_review_with_an_anchor_is_still_not_a_refusal(
        self, bot_kind, monkeypatch
    ):
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
        awaitable = [
            b for b in _registered_bots() if bot_registry.rate_limit_class(b) == 'awaitable_window'
        ]
        assert awaitable, 'registry must declare an awaitable_window bot for this to discriminate'

        for bot in awaitable:
            # Unread notice: the declared awaitability is NOT asserted.
            assert github_re_review._resolve_refusal_class(bot, [self._enumerative(bot)]) == 'unknown'
            # Matched negative control — same bot, a notice the registry arm READ.
            assert (
                github_re_review._resolve_refusal_class(bot, [self._registry(bot)])
                == 'awaitable_window'
            )

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

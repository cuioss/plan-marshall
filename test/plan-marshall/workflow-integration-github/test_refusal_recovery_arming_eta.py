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
_STRUCTURAL_NOTICE_BODY = (
    '> [!WARNING] > ## Usage limit reached > '
    'This reviewer has reached its usage limit. Reviews will resume after the limit resets.'
)
_DECLARED_WORDING_PAIRS: list[tuple[str, str]] = [
    (bot_kind, pattern) for bot_kind in bot_registry.bot_kinds() for pattern in bot_registry.refusal_patterns(bot_kind)
]
_DECLARED_WORDING_POPULATION_SIZE = len(_DECLARED_WORDING_PAIRS)
_DECLARED_WORDING_POPULATION_BASELINE = 7
def _registered_bots() -> list[str]:
    bots = bot_registry.bot_kinds()
    assert bots, 'registry must declare at least one bot'
    return bots
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
        assert bot_registry.trigger_semantics('no-such-bot') == bot_registry.TRIGGER_SEMANTICS_REQUIRES_EXPLICIT_TRIGGER

    def test_a_value_outside_the_closed_set_fails_closed(self, monkeypatch):
        """A malformed doc edit degrades safely rather than propagating a bad value."""
        bot = _registered_bots()[0]
        record = dict(bot_registry.REGISTRY._by_kind[bot])
        record['trigger_semantics'] = 'sometimes_maybe'
        monkeypatch.setitem(bot_registry.REGISTRY._by_kind, bot, record)

        assert bot_registry.trigger_semantics(bot) == bot_registry.TRIGGER_SEMANTICS_REQUIRES_EXPLICIT_TRIGGER
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
        monkeypatch.setattr(bot_registry, 'rate_limit_eta_patterns', lambda _kind: [r'limit reached|(ZZZ)'])

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
        monkeypatch.setattr(bot_registry, 'rate_limit_eta_patterns', lambda _kind: [r'in ([0-9]+ minutes)'])

        for bot in _registered_bots():
            assert _extract_rate_limit_eta(self._BODY, bot) == '18 minutes'

    def test_a_group_less_pattern_still_returns_the_whole_match(self, monkeypatch):
        """The no-group convention is preserved — group(0) remains the answer there."""
        monkeypatch.setattr(bot_registry, 'rate_limit_eta_patterns', lambda _kind: [r'[0-9]+ minutes'])

        for bot in _registered_bots():
            assert _extract_rate_limit_eta(self._BODY, bot) == '18 minutes'

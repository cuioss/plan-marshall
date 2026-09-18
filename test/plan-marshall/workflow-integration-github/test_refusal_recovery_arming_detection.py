# SPDX-License-Identifier: FSL-1.1-ALv2
"""Refusal detection answered per REGISTERED bot, plus the provenance seam.

Detection is swept over the whole registry population — no bot is
detection-privileged and none is left uncovered — and a detected refusal is
REPORTED as a refusal rather than collapsing into an indistinguishable bare
timeout (the end-to-end never-bare-timeout contract). The provenance seam
records how each detection was reached. The arming rule itself (cause dominance,
window arms, disclosure) lives in the co-located arming suites; this module
pins detection only.

The bot population is DERIVED from ``bot_registry``, never hard-coded, so a bot
added or reclassified in a standards doc is swept here automatically.
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
            comments.append(_comment(other, 'Actionable comment: guard the array bound.', '2026-01-02T00:00:00Z'))

        detected = _detect_rate_limited_bots(comments)

        assert [r['bot_kind'] for r in detected] == [refuser]

    def test_a_healthy_review_from_every_bot_detects_nothing(self):
        """Precision guard: a real review is never reported as a refusal."""
        comments = [
            _comment(bot, 'Reviewed the diff. One issue: the retry cap can be zero.') for bot in _registered_bots()
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
        record = github_re_review._ReReviewStrategy._refusal_record(_refusal_body(bot_kind), bot_kind, 'issue_comment')

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

        record = github_re_review._ReReviewStrategy._refusal_record(_refusal_body(bot_kind), bot_kind, 'issue_comment')

        assert record['layer'] == _github_pr.REFUSAL_LAYER_REGISTRY

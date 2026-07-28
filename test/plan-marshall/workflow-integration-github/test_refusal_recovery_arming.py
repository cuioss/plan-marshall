#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Cross-cutting suite: a NON-CodeRabbit refusal arms the right recovery.

Fail-first suite for D2 (registry-driven per-bot detection) and D4 (refusal
recovery). Against the pre-fix code the detector selected CodeRabbit-authored
comments only and a detected refusal was ``continue``-d into an indistinguishable
bare timeout, so every assertion below about a non-CodeRabbit bot's refusal — and
every assertion that a refusal is not reported as a bare timeout — was red.

Cross-cutting counterpart to the co-located suites: ``test_comments_stage.py``
owns the producer's noise filters and ``test_re_review_strategy.py`` owns the
discriminators' match/no-match behaviour. This suite pins the ARMING — that the
recovery a detected refusal selects follows the refusing bot's own declared
``rate_limit_class``, with no bot-name literal in the path:

    awaitable_window -> claim and await the window
    hard_quota       -> escalate immediately (nothing reopens by waiting)
    unknown          -> escalate immediately (fail-closed, ADR-009)

The bot population and every class expectation are DERIVED from
``bot_registry``, never hard-coded, so a bot added or reclassified in a standards
doc is swept here automatically.
"""

from __future__ import annotations

import sys

import pytest

from conftest import get_script_path

_GH_SCRIPTS = get_script_path('plan-marshall', 'workflow-integration-github', 'github_pr.py').parent
_AR_SCRIPTS = get_script_path('plan-marshall', 'automatic-review', 'review_completeness.py').parent

for _dir in (_GH_SCRIPTS, _AR_SCRIPTS):
    if str(_dir) not in sys.path:
        sys.path.insert(0, str(_dir))

import bot_registry  # noqa: E402
import github_ops  # noqa: E402, F401 — import first; _github_pr closes a cycle with it
import github_re_review  # noqa: E402
from _github_pr import _detect_rate_limited_bots  # noqa: E402

# The recovery each rate-limit class arms. This is the mapping under test; it is
# expressed once here and applied to whatever population the registry declares.
_RECOVERY_BY_CLASS = {
    'awaitable_window': 'claim_and_await',
    'hard_quota': 'escalate_immediately',
    'unknown': 'escalate_immediately',
}


def _arms(bot_kind: str) -> str:
    """The recovery a detected refusal from ``bot_kind`` arms, per its registry class."""
    return _RECOVERY_BY_CLASS[bot_registry.rate_limit_class(bot_kind)]


def _refusal_body(bot_kind: str) -> str:
    """A refusal body this bot's OWN registry record recognizes.

    Falls back to a structurally-shaped notice for a bot that declares no refusal
    phrasing, so the sweep covers every registered bot rather than only the ones
    with observed refusals.
    """
    declared = bot_registry.refusal_patterns(bot_kind)
    if declared:
        return f'This reviewer could not proceed: {declared[0]} — please try again later.'
    return (
        '> [!WARNING] > ## Usage limit reached > '
        'This reviewer has reached its usage limit. Reviews will resume after the limit resets.'
    )


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


class TestRecoveryArmingFollowsTheRegistryClass:
    """The recovery is chosen by the refusing bot's own declared class."""

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
        """A per-PR ceiling does not reopen, so awaiting only burns the budget.

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
        assert record['layer'] in ('registry_refusal_patterns', 'structural_fallback')

    @pytest.mark.parametrize('bot_kind', _registered_bots())
    def test_a_bots_declared_refusal_is_recognized_as_DATA(self, bot_kind):
        """A bot with declared refusal phrasing is matched by the registry layer.

        The distinction matters: recognition as DATA means the bot's own observed
        text is on file, whereas the structural fallback merely inferred it from
        shape. Sourcery's real refusal is the motivating case — the structural
        recognizer is blind to it, so only the data layer can see it.
        """
        if not bot_registry.refusal_patterns(bot_kind):
            pytest.skip(f'{bot_kind} declares no observed refusal phrasing')

        record = github_re_review._ReReviewStrategy._refusal_record(
            _refusal_body(bot_kind), bot_kind, 'issue_comment'
        )

        assert record['layer'] == 'registry_refusal_patterns'

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

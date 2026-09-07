#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The recovery attempt a claim ALREADY bought is delivered, never re-gated.

``attempts_remaining`` answers *may a FURTHER claim be made?* — it never answers
*may the event this claim already bought be delivered?* The two questions read the
same number, and the arithmetic cannot recover which is being asked, because
``rate-window claim`` INCREMENTS the per-``(bot, PR)`` ledger before it returns. The
cap-final claim — the one the primitive deliberately admitted — therefore reports
``attempts_remaining: 0`` at the instant it succeeds.

The recovery sequence consults the selector TWICE: once before claiming, and once
at the jittered wake boundary after the claim's window elapsed. Feeding the second
consult that post-claim zero routed it to ``escalate_exhausted``, and the workflow
released the claim without ever generating the event — so an ``attempt_cap`` of 1
delivered ZERO recovery events and the default cap of 6 delivered five. The bug is
silent by construction: every observable says the budget is spent, and the missing
event is the last one rather than the first.

``attempt_held`` is the caller stating which question it is asking. Every case here
is paired with its matched control, because the flag's whole value is that it
DISCRIMINATES — an assertion on the held arm alone passes equally on a selector
that had simply stopped escalating.

⛔ **The flag is not a blanket authorization, and the cap is not enforced here.**
Exhaustion is decided by ``rate-window claim``'s own ``recovery_cap_exhausted``
refusal; this selector only chooses a move once a refusal has been seen. The
non-bypass sweep below is what pins that a held attempt still cannot buy a trigger
past a size cause, a non-awaitable class, an unmeasured input, or an open window.
"""

from __future__ import annotations

import importlib

# ``github_ops`` MUST be resolved FIRST: importing ``_github_pr`` before it fails
# outright with a partially-initialised-module ImportError, because the two close
# an import cycle. Reached through ``import_module`` rather than an ``import``
# statement because isort sorts ``_github_pr`` ahead of ``github_ops``, so no
# arrangement of plain imports can express the ordering.
importlib.import_module('github_ops')

import bot_registry  # noqa: E402
import github_re_review  # noqa: E402
import pytest  # noqa: E402
from _github_pr import REFUSAL_CAUSE_QUOTA, REFUSAL_CAUSE_SIZE  # noqa: E402
from toon_parser import parse_toon  # noqa: E402

#: The two arms that actually DELIVER a recovery event. Named as a pair because
#: which one fires is a registry fact (``trigger_semantics``) that no case here
#: re-declares — the claim under test is that an event is delivered at all.
_TRIGGER_ARMS = (
    github_re_review.RECOVERY_ACTION_CLOSE_AND_REOPEN,
    github_re_review.RECOVERY_ACTION_GENERATE_TRIGGER,
)

#: The post-claim budget reading a SUCCESSFUL cap-final claim publishes. Zero is the
#: literal that IS the contract here: it is the exact value the primitive returns on
#: the claim the cap admits, and the whole defect lives at that boundary.
_CAP_FINAL_REMAINING = 0


def _awaitable_bots() -> list[str]:
    """The registered bots whose class reaches the window arms at all.

    Derived from the registry rather than named: only ``awaitable_window`` bots get
    past the class arm, so a case built on any other bot would pass for the wrong
    reason — the escalation it observed would be the class's, not the budget's.
    """
    bots = [b for b in bot_registry.bot_kinds() if bot_registry.rate_limit_class(b) == 'awaitable_window']
    assert bots, 'registry must declare an awaitable_window bot for these cases to discriminate'
    return bots


def _verdict(bot_kind: str, **kwargs) -> dict:
    """The shipped selector's verdict at the POST-CLAIM boundary.

    The defaults place the call exactly where the defect lived: an elapsed window,
    a quota cause, and the cap-final budget a successful claim reports. Each case
    varies one input from there, so what a case pins is the effect of that input.
    """
    return github_re_review.resolve_recovery_action(
        bot_kind,
        cause=kwargs.pop('cause', REFUSAL_CAUSE_QUOTA),
        window_expired=kwargs.pop('window_expired', True),
        attempts_remaining=kwargs.pop('attempts_remaining', _CAP_FINAL_REMAINING),
        **kwargs,
    )


class TestTheHeldAttemptIsDelivered:
    """A successful claim's event is generated, not re-tested against its own spend."""

    @pytest.mark.parametrize('bot_kind', _awaitable_bots())
    def test_a_cap_final_claim_still_reaches_a_trigger_arm(self, bot_kind):
        """The defect case: cap 1 delivered zero events, cap 6 delivered five.

        The claim succeeded, so the attempt is spent and the event it bought is
        owed. Reaching a trigger arm is the whole point of having waited.
        """
        verdict = _verdict(bot_kind, attempt_held=True)

        assert verdict['action'] in _TRIGGER_ARMS, verdict
        assert verdict['action'] != github_re_review.RECOVERY_ACTION_ESCALATE_EXHAUSTED
        assert verdict['reason'] == 'claim_window_elapsed'

    @pytest.mark.parametrize('bot_kind', _awaitable_bots())
    def test_the_matched_control_the_same_zero_escalates_when_no_attempt_is_held(self, bot_kind):
        """MATCHED CONTROL — identical inputs, ``attempt_held`` the only difference.

        This is the pre-claim budget read, where a zero genuinely does mean no
        further claim is allowed. Without this arm the case above would pass on a
        selector that had simply deleted the exhausted branch, which would let a
        genuinely exhausted recovery loop instead of escalating.
        """
        verdict = _verdict(bot_kind, attempt_held=False)

        assert verdict['action'] == github_re_review.RECOVERY_ACTION_ESCALATE_EXHAUSTED
        assert verdict['reason'] == 'attempt_cap_exhausted'

    @pytest.mark.parametrize('bot_kind', _awaitable_bots())
    def test_the_shipped_default_is_not_held(self, bot_kind):
        """Omitting the argument reads as NOT held — the conservative direction.

        Asserted by calling without the keyword at all rather than by passing
        ``False``, so what is pinned is the DEFAULT a caller inherits. Escalating is
        the safe way to be wrong here: it asks the operator instead of triggering a
        bot whose budget may really be gone.
        """
        assert _verdict(bot_kind)['action'] == github_re_review.RECOVERY_ACTION_ESCALATE_EXHAUSTED

    @pytest.mark.parametrize('bot_kind', _awaitable_bots())
    def test_a_positive_budget_is_unaffected_by_either_setting(self, bot_kind):
        """The flag changes nothing away from the boundary it exists for.

        With budget genuinely remaining the exhausted arm was never eligible, so
        both settings must agree. A flag that also moved the non-boundary cases
        would be a second authority over the window arms rather than a reading of
        one number.
        """
        held = _verdict(bot_kind, attempts_remaining=2, attempt_held=True)
        not_held = _verdict(bot_kind, attempts_remaining=2, attempt_held=False)

        assert held['action'] == not_held['action']
        assert held['action'] in _TRIGGER_ARMS

    @pytest.mark.parametrize('bot_kind', _awaitable_bots())
    def test_the_verdict_publishes_which_question_the_budget_was_read_for(self, bot_kind):
        """``attempt_held`` rides the verdict on BOTH settings, never only one.

        A consumer must not have to probe for the key to learn whether the
        exhausted arm was eligible, and the field is what makes the two readings of
        one number distinguishable in a decision log after the fact.
        """
        assert _verdict(bot_kind, attempt_held=True)['attempt_held'] is True
        assert _verdict(bot_kind, attempt_held=False)['attempt_held'] is False
        assert _verdict(bot_kind)['attempt_held'] is False


class TestAHeldAttemptAuthorizesNothingElse:
    """The flag lifts ONE arm. Every other refusal to trigger still refuses.

    Swept rather than sampled: the danger of an input that suppresses a guard is
    that it suppresses a neighbouring one too, and the neighbours here are the arms
    that stop a recovery spending quota on a move guaranteed to fail.
    """

    @pytest.mark.parametrize('bot_kind', _awaitable_bots())
    def test_a_size_cause_still_escalates_structurally(self, bot_kind):
        """A diff-size ceiling is not moved by holding an attempt."""
        verdict = _verdict(bot_kind, cause=REFUSAL_CAUSE_SIZE, attempt_held=True)

        assert verdict['action'] == github_re_review.RECOVERY_ACTION_ESCALATE_STRUCTURAL
        assert verdict['reason'] == 'size_ceiling'

    @pytest.mark.parametrize('bot_kind', _awaitable_bots())
    def test_an_open_claim_still_resolves_a_wait(self, bot_kind):
        """⛔ The ordering the whole section exists to enforce.

        A trigger issued while the claim is still running RESETS the bot's window
        instead of shortening it, and spends quota doing so. Holding an attempt
        says the event is owed — it does not say it is owed YET.
        """
        verdict = _verdict(bot_kind, window_expired=False, attempt_held=True)

        assert verdict['action'] == github_re_review.RECOVERY_ACTION_AWAIT_WINDOW
        assert verdict['reason'] == 'claim_window_open'

    @pytest.mark.parametrize('bot_kind', _awaitable_bots())
    def test_a_missing_window_observation_is_still_unmeasured(self, bot_kind):
        """An unobserved window authorizes nothing, held attempt or not."""
        verdict = _verdict(bot_kind, window_expired=None, attempt_held=True)

        assert verdict['action'] == github_re_review.RECOVERY_ACTION_UNMEASURED
        assert verdict['reason'] == 'no_window_observation'

    @pytest.mark.parametrize('bot_kind', _awaitable_bots())
    def test_a_missing_budget_observation_is_still_unmeasured(self, bot_kind):
        """A held attempt is not a substitute for having READ the budget.

        The flag says how to interpret the number; it does not supply one. Reading
        it as an implicit budget would let a caller that never polled the ledger
        trigger anyway.
        """
        verdict = _verdict(bot_kind, attempts_remaining=None, attempt_held=True)

        assert verdict['action'] == github_re_review.RECOVERY_ACTION_UNMEASURED
        assert verdict['reason'] == 'no_attempt_budget_observation'

    def test_a_non_awaitable_class_still_escalates(self):
        """The class arm precedes every window arm and is unmoved by the flag.

        Swept over both non-awaitable classes, derived from the registry — a bot
        whose limit does not reopen must never reach a trigger arm, since asking it
        again cannot produce a review.
        """
        non_awaitable = [
            b
            for b in bot_registry.bot_kinds()
            if bot_registry.rate_limit_class(b) in ('hard_quota', 'unknown')
        ]
        assert non_awaitable, 'registry must declare a non-awaitable bot for this to discriminate'

        for bot in non_awaitable:
            verdict = _verdict(bot, attempt_held=True)

            assert verdict['action'] == github_re_review.RECOVERY_ACTION_ESCALATE_NOT_AWAITABLE
            assert verdict['action'] not in _TRIGGER_ARMS


class TestTheFlagIsReachableFromTheCommandLine:
    """The CLI declares ``--attempt-held``, and the workflow's own form parses.

    Driven through ``main()`` — argparse included — rather than through a
    hand-built ``Namespace``. The failure this guards is an undeclared flag, and a
    ``Namespace`` constructed in the test declares it by construction: such a test
    passes while the documented invocation exits 2 and takes the recovery with it.
    """

    @staticmethod
    def _run(monkeypatch, capsys, *args: str) -> dict:
        """Invoke ``recovery-action`` through argparse; return the parsed TOON."""
        bot = _awaitable_bots()[0]
        monkeypatch.setattr(
            'sys.argv',
            ['github_re_review.py', 'recovery-action', '--bot-kind', bot, *args],
        )

        assert github_re_review.main() == 0

        return parse_toon(capsys.readouterr().out)

    def test_the_documented_post_claim_invocation_reaches_a_trigger_arm(self, monkeypatch, capsys):
        """The exact flag set ``automatic-review``'s second consult sends."""
        payload = self._run(
            monkeypatch,
            capsys,
            '--cause',
            REFUSAL_CAUSE_QUOTA,
            '--window-expired',
            'true',
            '--attempts-remaining',
            str(_CAP_FINAL_REMAINING),
            '--attempt-held',
            'true',
        )

        assert payload['status'] == 'success'
        assert payload['attempt_held'] is True
        assert payload['action'] in _TRIGGER_ARMS

    def test_the_same_invocation_without_the_flag_escalates(self, monkeypatch, capsys):
        """MATCHED CONTROL at the CLI boundary — the flag is what carries it.

        Identical argv minus ``--attempt-held``. Without this the case above could
        be passing because the CLI ignores the flag entirely and something else
        moved the verdict.
        """
        payload = self._run(
            monkeypatch,
            capsys,
            '--cause',
            REFUSAL_CAUSE_QUOTA,
            '--window-expired',
            'true',
            '--attempts-remaining',
            str(_CAP_FINAL_REMAINING),
        )

        assert payload['attempt_held'] is False
        assert payload['action'] == github_re_review.RECOVERY_ACTION_ESCALATE_EXHAUSTED

    def test_an_explicit_false_is_accepted_and_reads_as_not_held(self, monkeypatch, capsys):
        """Both declared choices parse — the flag is not a bare store-true."""
        payload = self._run(
            monkeypatch,
            capsys,
            '--window-expired',
            'true',
            '--attempts-remaining',
            str(_CAP_FINAL_REMAINING),
            '--attempt-held',
            'false',
        )

        assert payload['attempt_held'] is False
        assert payload['action'] == github_re_review.RECOVERY_ACTION_ESCALATE_EXHAUSTED

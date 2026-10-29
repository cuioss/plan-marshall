#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The review loop's DEFAULTS are the operator's policy (D4).

``automatic-review/standards/coderabbit.md`` § "Operator review policy" is the standing
ruling for a required reviewer: a quota refusal is waited out (ONE window is 90 minutes,
up to ten windows), and the operator is asked only after those are spent. The tree used
to contradict it in the smallest possible way — the recovery was opt-in and OFF, its
window defaulted to an hour (shorter than a policy window) and the cap to six (fewer
than the policy allows) — so the default configuration never entered the loop at all.

This suite pins the policy AS THE SOURCE of the defaults rather than restating the
numbers:

* the window length and the number of windows are READ off the policy document, and the
  knobs plus ``merge_lock``'s defaults must equal them;
* the gate is ON by default, and the documented off-switch still exists;
* ``close-and-reopen`` is chosen only when the bot has NO review on record.

The selector cases reach the SHIPPED ``resolve_recovery_action``; nothing here
re-implements the routing it is checking.
"""

from __future__ import annotations

import importlib
import re

importlib.import_module('github_ops')

import bot_registry  # noqa: E402
import github_re_review  # noqa: E402
import pytest  # noqa: E402

from conftest import get_skill_dir, load_script_module  # noqa: E402

ml = load_script_module('plan-marshall', 'manage-locks', 'merge_lock.py', register=False)

_AR_SKILL = get_skill_dir('plan-marshall', 'automatic-review') / 'SKILL.md'
_CODERABBIT = get_skill_dir('plan-marshall', 'automatic-review') / 'standards' / 'coderabbit.md'
_BRANCH_CLEANUP = get_skill_dir('plan-marshall', 'phase-6-finalize') / 'standards' / 'branch-cleanup.md'


def _frontmatter_default(document_text: str, key: str) -> str:
    """The ``default:`` value a configurable key declares in the YAML frontmatter."""
    frontmatter = document_text.split('---', 2)[1]
    match = re.search(rf'^\s*- key: {re.escape(key)}\s*$\n\s+default:\s*(\S+)\s*$', frontmatter, re.MULTILINE)
    assert match, f'no frontmatter default for {key}'
    return match.group(1).strip().strip('"\'')


def _policy_window_minutes(policy_text: str) -> int:
    match = re.search(r'One window is \*\*(\d+) minutes\*\*', policy_text)
    assert match, 'the policy states no window length'
    return int(match.group(1))


def _policy_windows(policy_text: str) -> int:
    match = re.search(r'repeat up to \*\*(\d+) windows\*\*', policy_text)
    assert match, 'the policy states no window count'
    return int(match.group(1))


class TestThePolicyIsTheSourceOfTheDefaults:
    def test_the_window_default_is_the_policys_own_window(self):
        policy_window = _policy_window_minutes(_CODERABBIT.read_text(encoding='utf-8'))
        knob = int(_frontmatter_default(_AR_SKILL.read_text(encoding='utf-8'), 'review_rate_window_timeout_seconds'))

        assert policy_window == 90, f'the policy window moved to {policy_window} minutes; re-derive the defaults'
        assert knob == policy_window * 60, f'the wait budget is {knob}s but one policy window is {policy_window * 60}s'
        assert ml._DEFAULT_WINDOW_SECONDS == float(policy_window * 60), (
            'the claim default falls back to a window that is not one policy window'
        )

    def test_the_attempt_cap_is_the_policys_own_count(self):
        policy_windows = _policy_windows(_CODERABBIT.read_text(encoding='utf-8'))

        assert policy_windows == 10, f'the policy count moved to {policy_windows}; re-derive the cap'
        assert ml._DEFAULT_RECOVERY_ATTEMPT_CAP == policy_windows, (
            'the recursion cap gives up before the policy says the reviewer is unavailable'
        )

    def test_the_module_records_why_its_defaults_follow_the_policy(self):
        """A default that changed must say where it came from, or the next edit drifts again."""
        source = _AR_SKILL.parents[1] / 'manage-locks' / 'scripts' / 'merge_lock.py'
        text = source.read_text(encoding='utf-8')

        assert 'Operator review policy' in text
        assert 'reason for the change' in text or 'reason' in text


class TestTheLoopIsOnByDefault:
    def test_the_gate_defaults_to_true(self):
        assert _frontmatter_default(_AR_SKILL.read_text(encoding='utf-8'), 'review_rate_window_await') == 'true'

    def test_the_documented_off_switch_survives(self):
        """The knob stays a knob: a project can still turn the loop off, in writing."""
        text = _AR_SKILL.read_text(encoding='utf-8')

        assert 'review_rate_window_await == false' in text
        assert 'sets it `false`' in text or 'sets it false' in text, (
            'the document no longer says how a project turns the loop off'
        )

    def test_an_optional_bot_refusal_never_arms_a_wait(self):
        """The scope rule the arm depends on: only a REQUIRED bot's refusal is recovered."""
        text = _AR_SKILL.read_text(encoding='utf-8')

        assert 'Scope the recovery to REQUIRED bots' in text
        assert 'an optional bot' in text and 'ordinary settle' in text


def _awaitable_bot() -> str:
    bots = [bot for bot in bot_registry.bot_kinds() if bot_registry.rate_limit_class(bot) == 'awaitable_window']
    assert bots, 'no awaitable-window bot is registered — the selector cases would be vacuous'
    return bots[0]


def _elapsed_verdict(review_on_record: str) -> dict:
    return github_re_review.resolve_recovery_action(
        _awaitable_bot(),
        cause='quota',
        window_expired=True,
        attempts_remaining=2,
        attempt_held=True,
        review_on_record=review_on_record,
    )


class TestCloseAndReopenIsBoundToNoReviewOnRecord:
    def test_a_bot_with_no_review_on_record_re_delivers_its_dropped_request(self, monkeypatch):
        bot = _awaitable_bot()
        monkeypatch.setattr(
            bot_registry,
            'trigger_semantics',
            lambda kind: bot_registry.TRIGGER_SEMANTICS_REQUIRES_EXPLICIT_TRIGGER if kind == bot else 'auto_on_push',
        )

        assert _elapsed_verdict(github_re_review.REVIEW_ON_RECORD_ABSENT)['action'] == (
            github_re_review.RECOVERY_ACTION_CLOSE_AND_REOPEN
        )

    def test_a_bot_that_already_reviewed_is_re_triggered_instead(self, monkeypatch):
        bot = _awaitable_bot()
        monkeypatch.setattr(
            bot_registry,
            'trigger_semantics',
            lambda kind: bot_registry.TRIGGER_SEMANTICS_REQUIRES_EXPLICIT_TRIGGER if kind == bot else 'auto_on_push',
        )

        for review_state in (github_re_review.REVIEW_ON_RECORD_CREDITED, github_re_review.REVIEW_ON_RECORD_STALE):
            verdict = _elapsed_verdict(review_state)
            assert verdict['action'] == github_re_review.RECOVERY_ACTION_GENERATE_TRIGGER, review_state
            assert verdict['action'] != github_re_review.RECOVERY_ACTION_CLOSE_AND_REOPEN

    def test_an_unobserved_review_state_keeps_the_dropped_request_arm(self, monkeypatch):
        """Fail-closed: the restriction names an OBSERVED review, so no observation keeps the arm."""
        bot = _awaitable_bot()
        monkeypatch.setattr(
            bot_registry,
            'trigger_semantics',
            lambda kind: bot_registry.TRIGGER_SEMANTICS_REQUIRES_EXPLICIT_TRIGGER if kind == bot else 'auto_on_push',
        )

        assert _elapsed_verdict('')['action'] == github_re_review.RECOVERY_ACTION_CLOSE_AND_REOPEN

    def test_a_push_triggering_bot_is_unaffected(self, monkeypatch):
        _awaitable_bot()  # asserts an awaitable bot exists, so the case is not vacuous
        monkeypatch.setattr(bot_registry, 'trigger_semantics', lambda kind: bot_registry.TRIGGER_SEMANTICS_AUTO_ON_PUSH)

        assert _elapsed_verdict(github_re_review.REVIEW_ON_RECORD_CREDITED)['action'] == (
            github_re_review.RECOVERY_ACTION_GENERATE_TRIGGER
        )


class TestTheBarrierSpendsTheLoopBeforeItAsks:
    """D2 + D4 at the barrier: refresh first, wait a quota out, and only then ask."""

    def _participation_section(self) -> str:
        text = _BRANCH_CLEANUP.read_text(encoding='utf-8')
        start = text.index('#### Blocked path — participation incomplete')
        end = text.index('##### ⛔ Structural refusal', start)
        return text[start:end]

    def test_a_stale_required_bot_is_triggered_before_the_question(self):
        section = self._participation_section()
        trigger = section.index('A stale required reviewer gets its ordinary trigger')
        ask = section.index('Branch on `{barrier_mode}`')

        assert trigger < ask, 'the stale trigger is documented after the barrier branches to its question'
        assert 'participated_stale' in section[trigger:ask]
        assert 'github_re_review re-review' in section[trigger:ask]

    def test_the_question_carries_whether_a_trigger_was_attempted(self):
        prompt_block = _BRANCH_CLEANUP.read_text(encoding='utf-8')
        start = prompt_block.index('Branch Cleanup — Pre-merge comment barrier')
        fence_start = prompt_block.rindex('```text', 0, start)
        fence_end = prompt_block.index('```', start)
        prompt = prompt_block[fence_start:fence_end]

        assert '{trigger_state}' in prompt
        assert 'none attempted' in prompt

    def test_an_awaitable_refusal_is_waited_out_before_the_question(self):
        section = self._participation_section()
        wait = section.index('An awaitable quota refusal is waited out')
        ask = section.index('Branch on `{barrier_mode}`')

        assert wait < ask, 'the quota wait is documented after the barrier branches to its question'
        assert 'refused_awaitable' in section[wait:ask]
        assert '`sleep`' in section[wait:ask] and 'rate-window wait' in section[wait:ask], (
            'the wait must be the merge_lock wait verb, never a raw sleep'
        )
        assert 'rate_window_exhausted' in section[wait:ask], (
            'the cap must escalate back to the operator rather than looping silently'
        )

    def test_the_trigger_scope_names_only_the_stale_member(self):
        section = self._participation_section()
        trigger_paragraph = section[
            section.index('A stale required reviewer gets its ordinary trigger') : section.index(
                'An awaitable quota refusal is waited out'
            )
        ]

        assert 'participated_stale` ONLY' in trigger_paragraph or '`participated_stale` ONLY' in trigger_paragraph
        for excluded in ('declined', 'refused_hard', 'refused_structural'):
            assert excluded in trigger_paragraph, (
                f'the scope paragraph must say that a {excluded} bot gets no extra trigger'
            )

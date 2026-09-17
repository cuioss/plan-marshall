#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Cross-cutting regression suite for PLAN-03 review-currency holes.

One test per hole, exercised from a user-visible angle distinct from the D1
co-located unit surface in ``test_review_completeness.py``: a force-push after a
bot review is not credited, an issue_comment naming the HEAD reads as approving,
an awaitable refusal awaits with CodeRabbit required, and Trigger-B reaches the
stale bot.
"""

from __future__ import annotations

from conftest import load_script_module

rc = load_script_module('plan-marshall', 'automatic-review', 'review_completeness.py', register=False)
gpr = load_script_module('plan-marshall', 'workflow-integration-github', '_github_pr.py', register=False)
gci = load_script_module('plan-marshall', 'workflow-integration-github', '_github_ci.py', register=False)
gchk = load_script_module('plan-marshall', 'workflow-integration-github', '_github_checks.py', register=False)
rgd = load_script_module('plan-marshall', 'automatic-review', 'review_gate_delta.py', register=False)


class TestReviewCurrencyHolesRegression:
    """One failing-without-fix, passing-with-fix test per PLAN-03 hole."""

    def test_stale_sha_force_push_not_credited(self):
        """A force-push after a bot review no longer credits the stale review."""
        old_head = 'a' * 40
        new_head = 'b' * 40
        body = f'bot reviewed {old_head}'

        assert gpr.bot_claimed_sha_matches_head(body, old_head) is True
        assert gpr.bot_claimed_sha_matches_head(body, new_head) is False
        assert gchk.carry_currency_verdict_to_check_state(False) == 'STALE'

    def test_issue_comment_head_read_approving(self, plan_context):
        """A current review on the issue_comment path reads as approving."""
        plan_id = 'regression-issue-comment-approving'
        plan_context.plan_dir_for(plan_id)
        head = 'd' * 40

        assert gci.issue_comment_verifies_head(f'reviewed .../commit/{head}', head) is True

        result = rc.check_completeness(
            plan_id,
            ['cuioss-review-bot'],
            participated_bots=rc.parse_participation('cuioss-review-bot:issue_comment'),
        )
        assert result['participation_complete'] is True

    def test_awaitable_refusal_awaits_with_coderabbit_required(self, plan_context):
        """The awaitable refusal awaits with CodeRabbit required, never demoted."""
        plan_id = 'regression-awaitable-coderabbit-required'
        plan_context.plan_dir_for(plan_id)

        assert rgd.should_await_refusal('awaitable_window') is True
        assert rgd.should_await_refusal('hard_quota') is False
        assert 'coderabbit' in rc.bot_registry.bot_kinds()

        result = rc.check_completeness(plan_id, ['coderabbit'], refused_bots=['coderabbit'])
        assert result['participation_complete'] is False
        states = [r['state'] for r in result['bot_states'] if r['bot_kind'] == 'coderabbit']
        assert states == [rc.STATE_REFUSED_AWAITABLE]

    def test_trigger_reaches_stale_bot(self, plan_context):
        """Trigger-B selects the actually-stale bot for re-review."""
        plan_id = 'regression-trigger-stale-bot'
        plan_context.plan_dir_for(plan_id)

        assert rc.select_stale_bot_for_trigger(['sourcery'], 'coderabbit') == 'sourcery'

        result = rc.check_completeness(plan_id, ['sourcery'], stale_participation_bots=['sourcery'])
        assert result['participation_complete'] is False
        states = [r['state'] for r in result['bot_states'] if r['bot_kind'] == 'sourcery']
        assert states == [rc.STATE_PARTICIPATED_STALE]

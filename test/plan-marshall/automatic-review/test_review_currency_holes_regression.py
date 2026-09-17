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

from conftest import get_script_path, load_script_module, run_script

rc = load_script_module('plan-marshall', 'automatic-review', 'review_completeness.py', register=False)
gpr = load_script_module('plan-marshall', 'workflow-integration-github', '_github_pr.py', register=False)
gci = load_script_module('plan-marshall', 'workflow-integration-github', '_github_ci.py', register=False)
gchk = load_script_module('plan-marshall', 'workflow-integration-github', '_github_checks.py', register=False)
rgd = load_script_module('plan-marshall', 'automatic-review', 'review_gate_delta.py', register=False)

RC_SCRIPT_PATH = get_script_path('plan-marshall', 'automatic-review', 'review_completeness.py')


class TestReviewCurrencyHolesRegression:
    """One failing-without-fix, passing-with-fix test per PLAN-03 hole."""

    def test_stale_sha_force_push_not_credited(self):
        """A force-push after a bot review fails the check state via the currency guard."""
        old_head = 'a' * 40
        new_head = 'b' * 40
        body = f'bot reviewed {old_head}'

        currency_current_old = gpr.bot_claimed_sha_matches_head(body, old_head)
        assert currency_current_old is True
        currency_current_new = gpr.bot_claimed_sha_matches_head(body, new_head)
        assert currency_current_new is False

        checks = [{'state': 'SUCCESS', 'bucket': 'pass', 'name': 'review', 'link': ''}]
        overall_current, _, _ = gchk._derive_overall_status(checks, currency_current=currency_current_old)
        assert overall_current == 'success'

        overall_stale, _, _ = gchk._derive_overall_status(checks, currency_current=currency_current_new)
        assert overall_stale == 'failure'

    def test_issue_comment_head_read_approving(self, plan_context):
        """A current review on the issue_comment path participates via the head check."""
        plan_id = 'regression-issue-comment-approving'
        plan_context.plan_dir_for(plan_id)
        head = 'd' * 40
        body = f'reviewed .../commit/{head}'

        verified = gci.issue_comment_verifies_head(body, head)
        assert verified is True

        participated = rc.parse_participation('cuioss-review-bot:issue_comment') if verified else {}
        result = rc.check_completeness(
            plan_id,
            ['cuioss-review-bot'],
            participated_bots=participated,
        )
        assert result['participation_complete'] is True

        stale_plan_id = 'regression-issue-comment-unverified'
        plan_context.plan_dir_for(stale_plan_id)
        unverified = gci.issue_comment_verifies_head('no commit reference here', head)
        assert unverified is False
        unproven = rc.check_completeness(
            stale_plan_id,
            ['cuioss-review-bot'],
            participated_bots={} if not unverified else rc.parse_participation('cuioss-review-bot:issue_comment'),
        )
        assert unproven['participation_complete'] is False

    def test_awaitable_refusal_awaits_with_coderabbit_required(self, plan_context):
        """The awaitable refusal classifies awaitable through the production refusal path."""
        plan_id = 'regression-awaitable-coderabbit-required'
        plan_context.plan_dir_for(plan_id)

        assert rgd.should_await_refusal('awaitable_window') is True
        assert rgd.should_await_refusal('hard_quota') is False
        assert 'coderabbit' in rc.bot_registry.bot_kinds()

        rate_class = rc.bot_registry.rate_limit_class('coderabbit')
        assert rgd.should_await_refusal(rate_class) is True

        result = rc.check_completeness(plan_id, ['coderabbit'], refused_bots=['coderabbit'])
        assert result['participation_complete'] is False
        states = [r['state'] for r in result['bot_states'] if r['bot_kind'] == 'coderabbit']
        assert states == [rc.STATE_REFUSED_AWAITABLE]
        assert (states[0] == rc.STATE_REFUSED_AWAITABLE) == rgd.should_await_refusal(rate_class)

    def test_trigger_reaches_stale_bot(self, plan_context):
        """Trigger-B resolves the actually-stale bot through the production trigger entry point."""
        plan_id = 'regression-trigger-stale-bot'
        plan_context.plan_dir_for(plan_id)

        trigger = run_script(
            RC_SCRIPT_PATH,
            'trigger-bot',
            '--plan-id',
            plan_id,
            '--stale-bots',
            'sourcery',
            '--newest-kind',
            'coderabbit',
        )
        assert trigger.success, trigger.stderr
        assert 'sourcery' in trigger.stdout

        result = rc.check_completeness(plan_id, ['sourcery'], stale_participation_bots=['sourcery'])
        assert result['participation_complete'] is False
        states = [r['state'] for r in result['bot_states'] if r['bot_kind'] == 'sourcery']
        assert states == [rc.STATE_PARTICIPATED_STALE]

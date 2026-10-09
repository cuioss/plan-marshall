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

import re

import pytest

from conftest import get_script_path, get_skill_dir, load_script_module, run_script

rc = load_script_module('plan-marshall', 'automatic-review', 'review_completeness.py', register=False)
gpr = load_script_module('plan-marshall', 'workflow-integration-github', '_github_pr.py', register=False)
gci = load_script_module('plan-marshall', 'workflow-integration-github', '_github_ci.py', register=False)
rgd = load_script_module('plan-marshall', 'automatic-review', 'review_gate_delta.py', register=False)

RC_SCRIPT_PATH = get_script_path('plan-marshall', 'automatic-review', 'review_completeness.py')

_OLD_HEAD = 'a' * 40
_NEW_HEAD = 'b' * 40

#: Every script of the GitHub provider skill. The one-recogniser case below sweeps the
#: whole directory rather than naming the files a recogniser used to live in, so a copy
#: added to any sibling script is counted too.
_GITHUB_SCRIPTS_DIR = get_skill_dir('plan-marshall', 'workflow-integration-github') / 'scripts'
_GITHUB_SCRIPT_SOURCES = {
    path.name: path.read_text(encoding='utf-8') for path in sorted(_GITHUB_SCRIPTS_DIR.glob('*.py'))
}
#: A regex quantifier that sizes a commit id: a full one, or the abbreviated-to-full range.
_COMMIT_LENGTH_QUANTIFIER = re.compile(r'\{(?:7,)?40\}')


class TestReviewCurrencyHolesRegression:
    """One failing-without-fix, passing-with-fix test per PLAN-03 hole."""

    def test_stale_sha_force_push_not_credited(self):
        """A review naming the pre-force-push commit matches that commit and not the new HEAD.

        The helper has a production caller on each path that reads a commit out of a
        comment body: the participation loop reaches it through
        ``named_commit_currency``, and the issue-comment head read delegates to it.
        """
        body = f'bot reviewed {_OLD_HEAD}'

        assert gpr.bot_claimed_sha_matches_head(body, _OLD_HEAD) is True
        assert gpr.bot_claimed_sha_matches_head(body, _NEW_HEAD) is False
        # The participation loop's reading of the same two comparisons.
        assert gpr.named_commit_currency(body, _OLD_HEAD) is True
        assert gpr.named_commit_currency(body, _NEW_HEAD) is False

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
        """Trigger-B lists the stale bot through the production trigger entry point.

        The bot has no stored finding in this plan: it is listed on the strength of
        its participation state alone, forwarded in the producer's pair form.
        """
        plan_id = 'regression-trigger-stale-bot'
        plan_context.plan_dir_for(plan_id)

        trigger = run_script(
            RC_SCRIPT_PATH,
            'trigger-bot',
            '--plan-id',
            plan_id,
            '--required-bots',
            'sourcery',
            '--stale-participation-bots',
            'sourcery:review_body',
        )
        assert trigger.success, trigger.stderr
        assert 'trigger_bots[1]' in trigger.stdout
        assert 'required_stale_bots[1]' in trigger.stdout
        assert 'sourcery' in trigger.stdout

        result = rc.check_completeness(plan_id, ['sourcery'], stale_participation_bots=['sourcery'])
        assert result['participation_complete'] is False
        states = [r['state'] for r in result['bot_states'] if r['bot_kind'] == 'sourcery']
        assert states == [rc.STATE_PARTICIPATED_STALE]


_ABBREVIATED = 'abc1234'
_DIGEST_STARTING_WITH_THE_HEAD = _NEW_HEAD + 'c' * 24

_BODIES_NAMING_THE_HEAD = [
    pytest.param(_NEW_HEAD, id='bare'),
    pytest.param(f'Reviewed until commit {_NEW_HEAD}.', id='in-prose'),
    pytest.param(f'https://github.com/o/r/commit/{_NEW_HEAD}', id='permalink'),
    pytest.param(f'[`{_NEW_HEAD[:7]}`](https://github.com/o/r/commit/{_NEW_HEAD})', id='markdown-link'),
    pytest.param(f'reviewed {_NEW_HEAD.upper()}', id='upper-case'),
    pytest.param(f'base {_OLD_HEAD} head {_NEW_HEAD}', id='beside-another-commit'),
]
_BODIES_NOT_NAMING_THE_HEAD = [
    pytest.param('', id='empty'),
    pytest.param('Reviewed the change; nothing to report.', id='no-commit'),
    pytest.param(f'reviewed {_OLD_HEAD}', id='another-commit'),
    pytest.param(f'reviewed {_NEW_HEAD[:-1]}a', id='shares-a-leading-run'),
    pytest.param(f'reviewed {_NEW_HEAD[:12]}', id='abbreviation-of-the-head'),
    pytest.param(f'sha256:{_DIGEST_STARTING_WITH_THE_HEAD}', id='longer-digest-starting-with-the-head'),
]


class TestTheOneCommitRecogniser:
    """The commit recogniser every reader of a bot-written commit reference shares."""

    def test_the_github_scripts_define_exactly_one_commit_length_pattern(self):
        """One pattern sizes a commit id across the provider's scripts, and it lives in ``_github_pr``.

        Two recognisers with different lengths and different anchoring are how the
        participation test and the re-review matcher came to disagree about where a
        commit id may sit. The population is every script of the skill, so a copy
        added to any of them is counted.
        """
        assert len(_GITHUB_SCRIPT_SOURCES) > 1, 'a one-file population cannot show the pattern is not duplicated'
        hits = {
            name: len(_COMMIT_LENGTH_QUANTIFIER.findall(source))
            for name, source in _GITHUB_SCRIPT_SOURCES.items()
            if _COMMIT_LENGTH_QUANTIFIER.search(source)
        }

        assert hits == {'_github_pr.py': 1}

    @pytest.mark.parametrize('body', _BODIES_NAMING_THE_HEAD)
    def test_a_body_naming_the_head_matches_it(self, body):
        """Bare, in prose, inside a permalink, upper-cased, or beside another commit."""
        assert gpr.bot_claimed_sha_matches_head(body, _NEW_HEAD) is True

    @pytest.mark.parametrize('body', _BODIES_NOT_NAMING_THE_HEAD)
    def test_a_body_not_naming_the_head_does_not_match_it(self, body):
        """⛔ MATCHED NEGATIVE CONTROL — equality, never a prefix and never a slice.

        ``shares-a-leading-run`` and ``abbreviation-of-the-head`` differ from the head
        only at the tail, and ``longer-digest-starting-with-the-head`` contains the
        head as its first forty characters: the surrounding-character guards are what
        keep that slice from being read as a commit id.
        """
        assert gpr.bot_claimed_sha_matches_head(body, _NEW_HEAD) is False

    def test_an_unreadable_head_matches_nothing(self):
        """No head to compare against is never a match, whatever the body names."""
        assert gpr.bot_claimed_sha_matches_head(f'reviewed {_NEW_HEAD}', '') is False
        assert gpr.bot_claimed_sha_matches_head(f'reviewed {_NEW_HEAD}', '   ') is False

    def test_an_abbreviated_head_is_compared_at_the_length_it_was_supplied(self):
        """The recogniser admits abbreviated runs because its equality consumers need them.

        A caller holding an abbreviated id matches the same abbreviation in the body,
        and nothing longer or shorter.
        """
        assert gpr.commit_tokens(f'see {_ABBREVIATED} and {_NEW_HEAD.upper()}') == [_ABBREVIATED, _NEW_HEAD]
        assert gpr.bot_claimed_sha_matches_head(f'reviewed {_ABBREVIATED}', _ABBREVIATED) is True
        assert gpr.bot_claimed_sha_matches_head(f'reviewed {_ABBREVIATED}f', _ABBREVIATED) is False

    def test_only_a_full_id_names_a_commit(self):
        """An abbreviated run and a long number are commit-shaped and name nothing.

        ``12345678`` is the case the narrowing exists for: a run id or a byte size is
        hex-shaped, and reading it as a named commit would report a review stale on
        the strength of a number.
        """
        body = f'run 12345678 touched {_ABBREVIATED}; reviewed {_NEW_HEAD.upper()}'

        assert gpr.commit_tokens(body) == ['12345678', _ABBREVIATED, _NEW_HEAD]
        assert gpr.named_commits(body) == [_NEW_HEAD]
        assert gpr.named_commits(f'run 12345678 touched {_ABBREVIATED}') == []

    @pytest.mark.parametrize(
        ('body', 'head', 'expected'),
        [
            pytest.param(f'reviewed {_NEW_HEAD}', _NEW_HEAD, True, id='names-the-head'),
            pytest.param(f'base {_OLD_HEAD} head {_NEW_HEAD}', _NEW_HEAD, True, id='names-several-one-is-the-head'),
            pytest.param(f'reviewed {_OLD_HEAD}', _NEW_HEAD, False, id='names-another-commit'),
            pytest.param('Reviewed the change.', _NEW_HEAD, None, id='names-no-commit'),
            pytest.param(f'run 12345678 touched {_ABBREVIATED}', _NEW_HEAD, None, id='only-abbreviated-runs'),
            pytest.param(f'reviewed {_OLD_HEAD}', '', None, id='unreadable-head'),
            pytest.param(f'reviewed {_OLD_HEAD}', '  ', None, id='blank-head'),
        ],
    )
    def test_what_the_named_commits_say_about_a_review_of_the_head(self, body, head, expected):
        """Three answers: current, about another commit, or no verdict at all.

        ``None`` is the answer the caller falls back on, so it must never be produced
        for a body that names a commit against a readable head, and never be replaced
        by ``False`` for a body that names none — that would report every comment
        without a commit reference stale.
        """
        assert gpr.named_commit_currency(body, head) is expected

    @pytest.mark.parametrize('body', [*_BODIES_NAMING_THE_HEAD, *_BODIES_NOT_NAMING_THE_HEAD])
    def test_the_issue_comment_head_read_agrees_with_the_shared_recogniser(self, body):
        """The issue-comment path reads a commit reference exactly where the helper does."""
        assert gci.issue_comment_verifies_head(body, _NEW_HEAD) is gpr.bot_claimed_sha_matches_head(body, _NEW_HEAD)

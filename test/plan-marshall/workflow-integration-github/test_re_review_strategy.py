#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for github_re_review.py — the bot_kind-keyed re-review strategy registry.

Covers the three concerns of the post-merge re-review registry:

    1. Strategy resolution — each bot_kind key resolves to the correct strategy
       object; an unknown key resolves to None.
    2. Trigger posting — ``request_fresh_review`` posts an explicit trigger
       comment per strategy and returns the comment-post time:
         coderabbit: posts ``@coderabbitai review``.
         sourcery:   posts ``@sourcery-ai review``.
         pr-agent:   posts ``/review``.
    3. Two-signal completion matching — ``await_fresh_review`` is satisfied by
       EITHER ``_match_review`` (a review whose reviewed commit SHA matches the
       pushed HEAD AND whose ``submitted_at`` post-dates the trigger time,
       reported with ``head_sha_verified: true``) OR ``_match_bot_comment`` (an
       issue comment from the awaited bot post-dating the trigger, reported with
       ``head_sha_verified: false``). The review signal wins when both are
       present. Fail-closed on every missing or unparseable input.

Plus the ``cmd_re_review`` CLI handler that wires request → await together.

Tests never shell out to the real ``gh`` CLI: every ``_github`` helper the
registry calls (``post_pr_comment``, ``fetch_pr_reviews_with_commits``,
``fetch_pr_comments_data``) is monkeypatched — the last one by the autouse
``_no_provider_comments`` guard below, so no test can silently reach the network
through the comment matcher — and ``time.sleep`` inside ``poll_until`` is
neutralised so the timeout branch runs in constant time. Module import resolves
via the root conftest's marketplace PYTHONPATH setup (``import
github_re_review``).
"""

import argparse
import sys
import time

import ci_base
import github_re_review
import pytest


@pytest.fixture(autouse=True)
def _no_provider_comments(monkeypatch):
    """Default every test to an empty provider comment list.

    ``await_fresh_review`` fetches PR comments whenever a ``bot_kind`` is
    supplied (the comment-signal matcher). Without this guard a test that patches
    only ``fetch_pr_reviews_with_commits`` would fall through to the real ``gh``
    CLI. Tests exercising the comment signal override it via ``_patch_comments``.
    """
    monkeypatch.setattr(
        github_re_review._github,
        'fetch_pr_comments_data',
        lambda pr_number, unresolved_only=False: {'status': 'success', 'comments': []},
    )


def _patch_comments(monkeypatch, comments):
    """Override the provider comment list for the comment-signal tests."""
    monkeypatch.setattr(
        github_re_review._github,
        'fetch_pr_comments_data',
        lambda pr_number, unresolved_only=False: {'status': 'success', 'comments': list(comments)},
    )


def _noop_sleep(monkeypatch):
    """Make poll_until's sleep a no-op so timeout-path tests finish fast."""
    monkeypatch.setattr(ci_base.time, 'sleep', lambda *_a, **_kw: None)
    monkeypatch.setattr(time, 'sleep', lambda *_a, **_kw: None)


def _review(commit_sha, submitted_at, *, user='coderabbit[bot]', state='COMMENTED'):
    """Build a review row in the shape fetch_pr_reviews_with_commits returns."""
    return {
        'user': user,
        'state': state,
        'submitted_at': submitted_at,
        'commit_sha': commit_sha,
    }


def _comment(author, *, created_at, updated_at='', body='## PR Reviewer Guide', kind='issue_comment'):
    """Build a comment row in the shape fetch_pr_comments_data returns."""
    return {
        'kind': kind,
        'id': f'IC_{author}_{created_at}',
        'thread_id': '',
        'author': author,
        'body': body,
        'path': '',
        'line': 0,
        'resolved': False,
        'created_at': created_at,
        'updated_at': updated_at,
    }


# =============================================================================
# Concern 1: Strategy resolution
# =============================================================================


def test_resolve_strategy_coderabbit_is_generic_with_coderabbit_trigger():
    """coderabbit resolves to the ONE generic strategy carrying its trigger comment."""
    strategy = github_re_review.resolve_strategy('coderabbit')

    assert strategy is not None
    assert isinstance(strategy, github_re_review._ReReviewStrategy)
    assert strategy.trigger_comment == '@coderabbitai review'


def test_resolve_strategy_pr_agent_is_generic_with_pr_agent_trigger():
    """pr-agent resolves to the same generic strategy class, carrying its own trigger."""
    strategy = github_re_review.resolve_strategy('pr-agent')

    assert strategy is not None
    assert isinstance(strategy, github_re_review._ReReviewStrategy)
    assert strategy.trigger_comment == '/review'


def test_resolve_strategy_sourcery_is_generic_with_sourcery_trigger():
    """sourcery resolves to the same generic strategy class, carrying its own trigger."""
    strategy = github_re_review.resolve_strategy('sourcery')

    assert strategy is not None
    assert isinstance(strategy, github_re_review._ReReviewStrategy)
    assert strategy.trigger_comment == '@sourcery-ai review'


def test_no_bot_specific_strategy_classes_remain():
    """The refactor removed every per-bot strategy subclass — only the generic one exists."""
    assert not hasattr(github_re_review, '_CodeRabbitStrategy')
    assert not hasattr(github_re_review, '_SourceryStrategy')
    assert not hasattr(github_re_review, '_PrAgentStrategy')


def test_no_hardcoded_trigger_constants_remain():
    """The per-bot trigger constants were collapsed into registry-loaded data."""
    assert not hasattr(github_re_review, 'CODERABBIT_TRIGGER_COMMENT')
    assert not hasattr(github_re_review, 'SOURCERY_TRIGGER_COMMENT')
    assert not hasattr(github_re_review, 'PR_AGENT_TRIGGER_COMMENT')


def test_strategy_triggers_derive_from_bot_registry():
    """Every strategy's trigger equals the registry-declared trigger for its bot."""
    import bot_registry

    for bot_kind in bot_registry.bot_kinds():
        strategy = github_re_review.resolve_strategy(bot_kind)
        assert strategy is not None
        assert strategy.trigger_comment == bot_registry.trigger_comment(bot_kind)


def test_author_login_map_derives_from_bot_registry():
    """The login->bot_kind map is derived from the registry, not inline-copied."""
    import bot_registry

    assert github_re_review._AUTHOR_LOGIN_TO_BOT_KIND == bot_registry.login_to_bot_kind()


def test_sourcery_is_a_valid_bot_kind():
    """``sourcery`` is a first-class member of the canonical BOT_KINDS enum."""
    from _findings_core import BOT_KINDS

    assert 'sourcery' in BOT_KINDS


def test_resolve_strategy_unknown_bot_kind_returns_none():
    assert github_re_review.resolve_strategy('copilot') is None


def test_resolve_strategy_covers_every_bot_kind():
    """Every canonical BOT_KINDS key must resolve to a registered strategy.

    The registry imports BOT_KINDS rather than inline-copying the enum, so this
    asserts the registry stays complete when a new bot_kind is added upstream.
    """
    from _findings_core import BOT_KINDS

    for bot_kind in BOT_KINDS:
        assert github_re_review.resolve_strategy(bot_kind) is not None, bot_kind


def test_strategies_are_distinct_objects():
    """coderabbit and pr-agent must not collapse onto the same strategy object."""
    coderabbit = github_re_review.resolve_strategy('coderabbit')
    pr_agent = github_re_review.resolve_strategy('pr-agent')

    assert coderabbit is not pr_agent


# =============================================================================
# Concern 2: Trigger posting (request_fresh_review)
# =============================================================================


def test_coderabbit_request_fresh_review_posts_trigger_comment(monkeypatch):
    """CodeRabbit posts exactly ``@coderabbitai review`` as the explicit trigger."""
    post_calls = {'args': []}

    def fake_post(pr_number, body):
        post_calls['args'].append((pr_number, body))
        return {'status': 'success', 'operation': 'post_pr_comment', 'pr_number': pr_number}

    monkeypatch.setattr(github_re_review._github, 'post_pr_comment', fake_post)

    strategy = github_re_review.resolve_strategy('coderabbit')
    result = strategy.request_fresh_review(42, '2026-01-01T00:00:00Z')

    assert result['status'] == 'success'
    # Exactly one comment posted, with the exact trigger literal (the strategy's
    # trigger comes from the registry data block, not a hard-coded constant).
    assert post_calls['args'] == [(42, strategy.trigger_comment)]
    assert strategy.trigger_comment == '@coderabbitai review'


def test_coderabbit_request_fresh_review_trigger_time_is_post_time_not_push_time(monkeypatch):
    """CodeRabbit's trigger time is the comment-post time, never the push time."""
    monkeypatch.setattr(
        github_re_review._github,
        'post_pr_comment',
        lambda *_a, **_kw: {'status': 'success'},
    )
    monkeypatch.setattr(github_re_review, '_now_iso', lambda: '2026-06-01T12:00:00+00:00')

    strategy = github_re_review.resolve_strategy('coderabbit')
    result = strategy.request_fresh_review(42, '2020-01-01T00:00:00Z')

    assert result['trigger_time'] == '2026-06-01T12:00:00+00:00'
    # The supplied push_time is deliberately discarded.
    assert result['trigger_time'] != '2020-01-01T00:00:00Z'


def test_coderabbit_request_fresh_review_propagates_post_failure(monkeypatch):
    """A failed trigger-comment post surfaces as an error envelope."""
    monkeypatch.setattr(
        github_re_review._github,
        'post_pr_comment',
        lambda *_a, **_kw: {'status': 'error', 'error': 'comment failed'},
    )

    strategy = github_re_review.resolve_strategy('coderabbit')
    result = strategy.request_fresh_review(42, '2026-01-01T00:00:00Z')

    assert result['status'] == 'error'
    assert result['operation'] == 'request_fresh_review'


def test_pr_agent_request_fresh_review_posts_trigger_comment(monkeypatch):
    """PR-Agent does NOT auto-review on push — it posts exactly ``/review``."""
    post_calls = {'args': []}

    def fake_post(pr_number, body):
        post_calls['args'].append((pr_number, body))
        return {'status': 'success', 'operation': 'post_pr_comment', 'pr_number': pr_number}

    monkeypatch.setattr(github_re_review._github, 'post_pr_comment', fake_post)

    strategy = github_re_review.resolve_strategy('pr-agent')
    result = strategy.request_fresh_review(99, '2026-01-01T00:00:00Z')

    assert result['status'] == 'success'
    # Exactly one comment posted, with the exact trigger literal (registry-derived).
    assert post_calls['args'] == [(99, strategy.trigger_comment)]
    assert strategy.trigger_comment == '/review'


def test_pr_agent_request_fresh_review_trigger_time_is_post_time_not_push_time(monkeypatch):
    """PR-Agent's trigger time is the comment-post time, never the push time."""
    monkeypatch.setattr(
        github_re_review._github,
        'post_pr_comment',
        lambda *_a, **_kw: {'status': 'success'},
    )
    monkeypatch.setattr(github_re_review, '_now_iso', lambda: '2026-06-01T12:00:00+00:00')

    strategy = github_re_review.resolve_strategy('pr-agent')
    result = strategy.request_fresh_review(99, '2020-01-01T00:00:00Z')

    assert result['trigger_time'] == '2026-06-01T12:00:00+00:00'
    # The supplied push_time is deliberately discarded.
    assert result['trigger_time'] != '2020-01-01T00:00:00Z'


def test_pr_agent_request_fresh_review_propagates_post_failure(monkeypatch):
    """A failed trigger-comment post surfaces as an error envelope."""
    monkeypatch.setattr(
        github_re_review._github,
        'post_pr_comment',
        lambda *_a, **_kw: {'status': 'error', 'error': 'comment failed'},
    )

    strategy = github_re_review.resolve_strategy('pr-agent')
    result = strategy.request_fresh_review(99, '2026-01-01T00:00:00Z')

    assert result['status'] == 'error'
    assert result['operation'] == 'request_fresh_review'


def test_sourcery_request_fresh_review_posts_trigger_comment(monkeypatch):
    """Sourcery posts exactly ``@sourcery-ai review`` as the explicit trigger."""
    post_calls = {'args': []}

    def fake_post(pr_number, body):
        post_calls['args'].append((pr_number, body))
        return {'status': 'success', 'operation': 'post_pr_comment', 'pr_number': pr_number}

    monkeypatch.setattr(github_re_review._github, 'post_pr_comment', fake_post)

    strategy = github_re_review.resolve_strategy('sourcery')
    result = strategy.request_fresh_review(77, '2026-01-01T00:00:00Z')

    assert result['status'] == 'success'
    # Exactly one comment posted, with the exact trigger literal (registry-derived).
    assert post_calls['args'] == [(77, strategy.trigger_comment)]
    assert strategy.trigger_comment == '@sourcery-ai review'


def test_sourcery_request_fresh_review_trigger_time_is_post_time_not_push_time(monkeypatch):
    """Sourcery's trigger time is the comment-post time, never the push time."""
    monkeypatch.setattr(
        github_re_review._github,
        'post_pr_comment',
        lambda *_a, **_kw: {'status': 'success'},
    )
    monkeypatch.setattr(github_re_review, '_now_iso', lambda: '2026-06-01T12:00:00+00:00')

    strategy = github_re_review.resolve_strategy('sourcery')
    result = strategy.request_fresh_review(77, '2020-01-01T00:00:00Z')

    assert result['trigger_time'] == '2026-06-01T12:00:00+00:00'
    # The supplied push_time is deliberately discarded.
    assert result['trigger_time'] != '2020-01-01T00:00:00Z'


def test_sourcery_request_fresh_review_propagates_post_failure(monkeypatch):
    """A failed trigger-comment post surfaces as an error envelope."""
    monkeypatch.setattr(
        github_re_review._github,
        'post_pr_comment',
        lambda *_a, **_kw: {'status': 'error', 'error': 'comment failed'},
    )

    strategy = github_re_review.resolve_strategy('sourcery')
    result = strategy.request_fresh_review(77, '2026-01-01T00:00:00Z')

    assert result['status'] == 'error'
    assert result['operation'] == 'request_fresh_review'


# =============================================================================
# Concern 3: Fresh-review matching (_match_review / await_fresh_review)
# =============================================================================


def _parse(value):
    return github_re_review._parse_iso(value)


def test_match_review_matches_when_sha_and_time_satisfy():
    """A review matching HEAD and post-dating the trigger is returned."""
    reviews = [_review('headsha', '2026-01-01T00:05:00Z')]
    trigger_dt = _parse('2026-01-01T00:00:00Z')

    matched = github_re_review._ReReviewStrategy._match_review(reviews, 'headsha', trigger_dt)

    assert matched is not None
    assert matched['commit_sha'] == 'headsha'


def test_match_review_rejects_wrong_commit_sha():
    """A review on a stale commit never matches even if it post-dates trigger."""
    reviews = [_review('oldsha', '2026-01-01T00:05:00Z')]
    trigger_dt = _parse('2026-01-01T00:00:00Z')

    assert github_re_review._ReReviewStrategy._match_review(reviews, 'headsha', trigger_dt) is None


def test_match_review_rejects_review_at_or_before_trigger_time():
    """A review submitted before the trigger (a pre-existing review) never matches."""
    reviews = [_review('headsha', '2026-01-01T00:00:00Z')]
    trigger_dt = _parse('2026-01-01T00:05:00Z')

    assert github_re_review._ReReviewStrategy._match_review(reviews, 'headsha', trigger_dt) is None


def test_match_review_fail_closed_on_unparseable_submitted_at():
    """A review whose submitted_at cannot be parsed never matches (fail-closed)."""
    reviews = [_review('headsha', 'not-a-timestamp')]
    trigger_dt = _parse('2026-01-01T00:00:00Z')

    assert github_re_review._ReReviewStrategy._match_review(reviews, 'headsha', trigger_dt) is None


def test_match_review_returns_first_eligible_among_many():
    """The first SHA-and-time eligible review is returned."""
    reviews = [
        _review('oldsha', '2026-01-01T00:09:00Z'),
        _review('headsha', '2026-01-01T00:06:00Z'),
        _review('headsha', '2026-01-01T00:07:00Z'),
    ]
    trigger_dt = _parse('2026-01-01T00:00:00Z')

    matched = github_re_review._ReReviewStrategy._match_review(reviews, 'headsha', trigger_dt)

    assert matched is not None
    assert matched['submitted_at'] == '2026-01-01T00:06:00Z'


def test_await_fresh_review_returns_matched_when_review_lands(monkeypatch):
    """await_fresh_review polls until a fresh review for HEAD lands → matched=True."""
    _noop_sleep(monkeypatch)
    call_counts = {'fetch': 0}

    def fake_fetch(pr_number):
        call_counts['fetch'] += 1
        if call_counts['fetch'] == 1:
            # First poll: only a stale pre-trigger review exists.
            return {'status': 'success', 'reviews': [_review('headsha', '2026-01-01T00:00:00Z')]}
        # Second poll: the fresh review for HEAD has landed.
        return {'status': 'success', 'reviews': [_review('headsha', '2026-01-01T00:05:00Z')]}

    monkeypatch.setattr(github_re_review._github, 'fetch_pr_reviews_with_commits', fake_fetch)

    strategy = github_re_review.resolve_strategy('coderabbit')
    result = strategy.await_fresh_review(42, 'headsha', '2026-01-01T00:02:00Z', timeout=5, interval=0)

    assert result['status'] == 'success'
    assert result['matched'] is True
    assert result['matched_review']['commit_sha'] == 'headsha'
    assert result['timed_out'] is False
    assert call_counts['fetch'] >= 2


def test_await_fresh_review_times_out_when_no_fresh_review_lands(monkeypatch):
    """When only stale reviews ever exist, await times out with matched=False."""
    _noop_sleep(monkeypatch)

    def fake_fetch(pr_number):
        # Always the same pre-trigger review — never a fresh one for HEAD.
        return {'status': 'success', 'reviews': [_review('headsha', '2026-01-01T00:00:00Z')]}

    monkeypatch.setattr(github_re_review._github, 'fetch_pr_reviews_with_commits', fake_fetch)

    strategy = github_re_review.resolve_strategy('coderabbit')
    result = strategy.await_fresh_review(42, 'headsha', '2026-01-01T00:02:00Z', timeout=1, interval=0)

    assert result['status'] == 'success'
    assert result['matched'] is False
    assert result['timed_out'] is True


def test_await_fresh_review_propagates_fetch_failure(monkeypatch):
    """A fetch error short-circuits await with an error envelope."""
    _noop_sleep(monkeypatch)
    monkeypatch.setattr(
        github_re_review._github,
        'fetch_pr_reviews_with_commits',
        lambda *_a, **_kw: {'status': 'error', 'error': 'fetch failed'},
    )

    strategy = github_re_review.resolve_strategy('coderabbit')
    result = strategy.await_fresh_review(42, 'headsha', '2026-01-01T00:00:00Z', timeout=1, interval=0)

    assert result['status'] == 'error'
    assert result['operation'] == 'await_fresh_review'


# =============================================================================
# Two-signal completion: the issue-comment fallback (_match_bot_comment)
# =============================================================================
#
# A bot that posts one persistent issue comment and submits NO review object
# could previously only ever exhaust its await budget. These cases pin the
# fallback AND its negative boundaries — the negatives are the real hazard, since
# an over-permissive matcher would report any PR chatter as a completed review.

_PR_AGENT_LOGIN = 'cuioss-review-bot'
_TRIGGER = '2026-01-01T00:02:00Z'


def _await_with_comments(monkeypatch, comments, *, reviews=None, bot_kind='pr-agent'):
    """Run ``await_fresh_review`` over a fixed comment (and review) set."""
    _noop_sleep(monkeypatch)
    monkeypatch.setattr(
        github_re_review._github,
        'fetch_pr_reviews_with_commits',
        lambda pr_number: {'status': 'success', 'reviews': list(reviews or [])},
    )
    _patch_comments(monkeypatch, comments)
    strategy = github_re_review.resolve_strategy(bot_kind)
    return strategy.await_fresh_review(
        42, 'headsha', _TRIGGER, bot_kind=bot_kind, timeout=1, interval=0
    )


def test_await_matches_bot_issue_comment_when_no_review_exists(monkeypatch):
    """A bot-authored comment post-dating the trigger satisfies await with no review.

    This is the case that used to be a guaranteed timeout. The envelope must name
    the weaker signal: ``matched_signal: issue_comment`` and
    ``head_sha_verified: false``, because a comment carries no reviewed-commit SHA.
    """
    result = _await_with_comments(
        monkeypatch, [_comment(_PR_AGENT_LOGIN, created_at='2026-01-01T00:05:00Z')]
    )

    assert result['status'] == 'success'
    assert result['matched'] is True
    assert result['matched_signal'] == 'issue_comment'
    assert result['head_sha_verified'] is False
    assert result['matched_comment']['author'] == _PR_AGENT_LOGIN
    # The review slot stays empty — no review was matched.
    assert result['matched_review'] == {}
    assert result['timed_out'] is False


def test_await_does_not_match_a_different_bots_comment(monkeypatch):
    """A comment from a DIFFERENT registered bot does not satisfy this bot's await."""
    result = _await_with_comments(
        monkeypatch, [_comment('coderabbitai', created_at='2026-01-01T00:05:00Z')]
    )

    assert result['matched'] is False
    assert result['matched_signal'] == ''
    assert result['timed_out'] is True


def test_await_does_not_match_a_human_comment(monkeypatch):
    """A human comment post-dating the trigger does not satisfy await.

    An unresolvable author yields no ``bot_kind``, so it can never equal the
    awaited one — human PR chatter cannot be mistaken for a completed review.
    """
    result = _await_with_comments(
        monkeypatch, [_comment('alice', created_at='2026-01-01T00:05:00Z')]
    )

    assert result['matched'] is False
    assert result['matched_signal'] == ''


def test_await_does_not_match_a_comment_predating_the_trigger(monkeypatch):
    """A pre-existing bot comment (older than the trigger) does not satisfy await."""
    result = _await_with_comments(
        monkeypatch, [_comment(_PR_AGENT_LOGIN, created_at='2026-01-01T00:00:00Z')]
    )

    assert result['matched'] is False
    assert result['matched_signal'] == ''


def test_await_does_not_match_a_rate_limit_notice_from_the_awaited_bot(monkeypatch):
    """A rate-limit / service notice from the awaited bot is NOT a completed review.

    Without this exclusion a "the bot is rate-limited" comment would be reported
    as a fresh review — precisely the false-green the two-signal match must avoid.
    """
    notice = (
        '> [!WARNING]\n'
        '> ## Rate limit exceeded\n'
        '>\n'
        '> This bot has exceeded the limit for the number of files that can be '
        'reviewed per hour.'
    )
    result = _await_with_comments(
        monkeypatch,
        [_comment(_PR_AGENT_LOGIN, created_at='2026-01-01T00:05:00Z', body=notice)],
    )

    assert result['matched'] is False
    assert result['matched_signal'] == ''


def test_await_matches_an_edited_persistent_comment_via_updated_at(monkeypatch):
    """A comment created BEFORE but edited AFTER the trigger matches on ``updated_at``.

    The edited-persistent-comment regression guard: a bot that updates ONE comment
    in place stops advancing ``created_at``, so a ``created_at``-only comparison
    would silently fail from the second re-review onward.
    """
    result = _await_with_comments(
        monkeypatch,
        [
            _comment(
                _PR_AGENT_LOGIN,
                created_at='2026-01-01T00:00:00Z',
                updated_at='2026-01-01T00:05:00Z',
            )
        ],
    )

    assert result['matched'] is True
    assert result['matched_signal'] == 'issue_comment'
    assert result['head_sha_verified'] is False


def test_await_prefers_the_review_signal_when_both_are_present(monkeypatch):
    """A matching review WINS over a matching comment, and verifies the HEAD.

    The review path is strictly stronger evidence, so the `commit_sha` +
    `submitted_at` contract is not weakened for bots that do submit reviews.
    """
    result = _await_with_comments(
        monkeypatch,
        [_comment(_PR_AGENT_LOGIN, created_at='2026-01-01T00:05:00Z')],
        reviews=[_review('headsha', '2026-01-01T00:06:00Z')],
    )

    assert result['matched'] is True
    assert result['matched_signal'] == 'review'
    assert result['head_sha_verified'] is True
    assert result['matched_review']['commit_sha'] == 'headsha'
    # The comment slot stays empty — the review signal won.
    assert result['matched_comment'] == {}


def test_await_without_bot_kind_never_matches_a_comment(monkeypatch):
    """Omitting ``bot_kind`` fails closed to review-only matching.

    There is no authorship to gate on, so the comment matcher must decline rather
    than accept any comment — "any comment counts" would be a false-green.
    """
    _noop_sleep(monkeypatch)
    monkeypatch.setattr(
        github_re_review._github,
        'fetch_pr_reviews_with_commits',
        lambda pr_number: {'status': 'success', 'reviews': []},
    )

    def exploding_fetch(*_a, **_kw):  # pragma: no cover - must not run
        raise AssertionError('comments must not be fetched without a bot_kind')

    monkeypatch.setattr(github_re_review._github, 'fetch_pr_comments_data', exploding_fetch)

    strategy = github_re_review.resolve_strategy('pr-agent')
    result = strategy.await_fresh_review(42, 'headsha', _TRIGGER, timeout=1, interval=0)

    assert result['matched'] is False
    assert result['matched_signal'] == ''


def test_match_bot_comment_fail_closed_on_unparseable_timestamps():
    """A comment whose only timestamps are unparseable never matches (fail-closed)."""
    trigger_dt = _parse(_TRIGGER)
    comments = [_comment(_PR_AGENT_LOGIN, created_at='not-a-timestamp', updated_at='')]

    assert (
        github_re_review._ReReviewStrategy._match_bot_comment(comments, 'pr-agent', trigger_dt)
        is None
    )


def test_match_bot_comment_fail_closed_on_missing_trigger_time():
    """An unparseable trigger time yields no comment match (fail-closed)."""
    comments = [_comment(_PR_AGENT_LOGIN, created_at='2026-01-01T00:05:00Z')]

    assert github_re_review._ReReviewStrategy._match_bot_comment(comments, 'pr-agent', None) is None


# =============================================================================
# CLI handler: cmd_re_review (wires request → await)
# =============================================================================


def _re_review_args(
    *,
    pr_number=42,
    bot_kind='coderabbit',
    head_sha='headsha',
    push_time='2026-01-01T00:00:00Z',
    timeout=ci_base.DEFAULT_CI_TIMEOUT,
):
    return argparse.Namespace(
        pr_number=pr_number,
        bot_kind=bot_kind,
        head_sha=head_sha,
        push_time=push_time,
        timeout=timeout,
        plan_id=None,
    )


def test_cmd_re_review_unknown_bot_kind_errors():
    result = github_re_review.cmd_re_review(_re_review_args(bot_kind='copilot'))

    assert result['status'] == 'error'
    assert 'copilot' in result['error']


def test_cmd_re_review_coderabbit_posts_then_awaits(monkeypatch):
    """coderabbit: posts @coderabbitai review, then awaits the fresh review for HEAD."""
    _noop_sleep(monkeypatch)
    post_calls = {'args': []}

    def fake_post(pr_number, body):
        post_calls['args'].append((pr_number, body))
        return {'status': 'success'}

    monkeypatch.setattr(github_re_review._github, 'post_pr_comment', fake_post)
    monkeypatch.setattr(github_re_review, '_now_iso', lambda: '2026-01-01T00:00:00+00:00')
    monkeypatch.setattr(
        github_re_review._github,
        'fetch_pr_reviews_with_commits',
        lambda pr_number: {'status': 'success', 'reviews': [_review('headsha', '2026-01-01T00:05:00Z')]},
    )

    result = github_re_review.cmd_re_review(_re_review_args(bot_kind='coderabbit'))

    assert result['status'] == 'success'
    assert result['matched'] is True
    assert result['bot_kind'] == 'coderabbit'
    assert result['head_sha'] == 'headsha'
    assert post_calls['args'] == [(42, '@coderabbitai review')]


def test_cmd_re_review_pr_agent_posts_then_awaits(monkeypatch):
    """pr-agent: posts /review, then awaits a fresh review for HEAD."""
    _noop_sleep(monkeypatch)
    post_calls = {'args': []}

    def fake_post(pr_number, body):
        post_calls['args'].append((pr_number, body))
        return {'status': 'success'}

    monkeypatch.setattr(github_re_review._github, 'post_pr_comment', fake_post)
    monkeypatch.setattr(github_re_review, '_now_iso', lambda: '2026-01-01T00:00:00+00:00')
    monkeypatch.setattr(
        github_re_review._github,
        'fetch_pr_reviews_with_commits',
        lambda pr_number: {'status': 'success', 'reviews': [_review('headsha', '2026-01-01T00:05:00Z')]},
    )

    result = github_re_review.cmd_re_review(_re_review_args(bot_kind='pr-agent'))

    assert result['status'] == 'success'
    assert result['matched'] is True
    assert result['bot_kind'] == 'pr-agent'
    assert post_calls['args'] == [(42, '/review')]


def test_cmd_re_review_threads_bot_kind_into_await(monkeypatch):
    """The resolved ``bot_kind`` MUST reach ``await_fresh_review``.

    Without it the comment matcher has no authorship to gate on and silently
    degrades to review-only matching — reinstating the vacuous timeout for a bot
    that submits no review object.
    """
    captured = {}

    def fake_await(self, pr_number, head_sha, trigger_time, *, bot_kind=None, timeout, interval=0):
        captured['bot_kind'] = bot_kind
        return {'status': 'success', 'matched': True, 'head_sha': head_sha}

    monkeypatch.setattr(
        github_re_review._github,
        'post_pr_comment',
        lambda *_a, **_kw: {'status': 'success'},
    )
    monkeypatch.setattr(github_re_review._ReReviewStrategy, 'await_fresh_review', fake_await)

    result = github_re_review.cmd_re_review(_re_review_args(bot_kind='pr-agent'))

    assert result['status'] == 'success'
    assert captured['bot_kind'] == 'pr-agent'


def test_cmd_re_review_sourcery_posts_then_awaits(monkeypatch):
    """sourcery: posts @sourcery-ai review, then awaits a fresh review for HEAD."""
    _noop_sleep(monkeypatch)
    post_calls = {'args': []}

    def fake_post(pr_number, body):
        post_calls['args'].append((pr_number, body))
        return {'status': 'success'}

    monkeypatch.setattr(github_re_review._github, 'post_pr_comment', fake_post)
    monkeypatch.setattr(github_re_review, '_now_iso', lambda: '2026-01-01T00:00:00+00:00')
    monkeypatch.setattr(
        github_re_review._github,
        'fetch_pr_reviews_with_commits',
        lambda pr_number: {'status': 'success', 'reviews': [_review('headsha', '2026-01-01T00:05:00Z')]},
    )

    result = github_re_review.cmd_re_review(_re_review_args(bot_kind='sourcery'))

    assert result['status'] == 'success'
    assert result['matched'] is True
    assert result['bot_kind'] == 'sourcery'
    assert post_calls['args'] == [(42, '@sourcery-ai review')]


def test_cmd_re_review_short_circuits_on_request_failure(monkeypatch):
    """A failed pr-agent trigger post aborts before await is ever called."""
    _noop_sleep(monkeypatch)
    monkeypatch.setattr(
        github_re_review._github,
        'post_pr_comment',
        lambda *_a, **_kw: {'status': 'error', 'error': 'comment failed'},
    )

    def exploding_fetch(*_a, **_kw):  # pragma: no cover - must not run
        raise AssertionError('await must not run when request_fresh_review fails')

    monkeypatch.setattr(github_re_review._github, 'fetch_pr_reviews_with_commits', exploding_fetch)

    result = github_re_review.cmd_re_review(_re_review_args(bot_kind='pr-agent'))

    assert result['status'] == 'error'


def test_cmd_re_review_short_circuits_on_await_failure(monkeypatch):
    """request succeeds but await errors → the await error envelope is returned.

    coderabbit's request posts its trigger comment successfully, so the only
    failure surface here is the await fetch. The handler must return that error
    without stamping bot_kind.
    """
    _noop_sleep(monkeypatch)
    monkeypatch.setattr(
        github_re_review._github,
        'post_pr_comment',
        lambda *_a, **_kw: {'status': 'success'},
    )
    monkeypatch.setattr(
        github_re_review._github,
        'fetch_pr_reviews_with_commits',
        lambda *_a, **_kw: {'status': 'error', 'error': 'fetch failed'},
    )

    result = github_re_review.cmd_re_review(_re_review_args(bot_kind='coderabbit'))

    assert result['status'] == 'error'
    assert result['operation'] == 'await_fresh_review'
    # bot_kind is only stamped on a successful await envelope.
    assert 'bot_kind' not in result


# =============================================================================
# --timeout threading: args.timeout flows into await_fresh_review
# =============================================================================


def test_cmd_re_review_threads_timeout_into_await(monkeypatch):
    """The CLI ``--timeout`` value must reach ``await_fresh_review`` verbatim.

    The handler reads ``args.timeout`` and forwards it as the ``timeout`` kwarg
    on the strategy's await call. Capture the kwarg the strategy receives and
    assert it equals the value supplied on the args namespace.
    """
    captured = {}

    def fake_await(self, pr_number, head_sha, trigger_time, *, bot_kind=None, timeout, interval=0):
        captured['timeout'] = timeout
        return {'status': 'success', 'matched': True, 'head_sha': head_sha}

    monkeypatch.setattr(
        github_re_review._github,
        'post_pr_comment',
        lambda *_a, **_kw: {'status': 'success'},
    )
    monkeypatch.setattr(github_re_review._ReReviewStrategy, 'await_fresh_review', fake_await)

    result = github_re_review.cmd_re_review(_re_review_args(bot_kind='coderabbit', timeout=37))

    assert result['status'] == 'success'
    assert captured['timeout'] == 37


def test_cmd_re_review_threads_default_timeout_into_await(monkeypatch):
    """When the default timeout is supplied, that exact default reaches await.

    Guards against the handler hard-coding a different constant instead of
    forwarding ``args.timeout``.
    """
    captured = {}

    def fake_await(self, pr_number, head_sha, trigger_time, *, bot_kind=None, timeout, interval=0):
        captured['timeout'] = timeout
        return {'status': 'success', 'matched': False, 'head_sha': head_sha}

    monkeypatch.setattr(
        github_re_review._github,
        'post_pr_comment',
        lambda *_a, **_kw: {'status': 'success'},
    )
    monkeypatch.setattr(github_re_review._ReReviewStrategy, 'await_fresh_review', fake_await)

    result = github_re_review.cmd_re_review(_re_review_args(bot_kind='coderabbit'))

    assert result['status'] == 'success'
    assert captured['timeout'] == ci_base.DEFAULT_CI_TIMEOUT


# =============================================================================
# _parse_iso edge cases
# =============================================================================


def test_parse_iso_empty_string_returns_none():
    """An empty timestamp parses to None (the early-return guard)."""
    assert github_re_review._parse_iso('') is None


def test_parse_iso_unparseable_returns_none():
    """A non-ISO timestamp parses to None rather than raising."""
    assert github_re_review._parse_iso('not-a-timestamp') is None


def test_parse_iso_normalizes_trailing_z():
    """A GitHub ``...Z`` timestamp is normalized and parsed to a UTC datetime."""
    parsed = github_re_review._parse_iso('2026-01-01T00:00:00Z')

    assert parsed is not None
    assert parsed.utcoffset().total_seconds() == 0


def test_parse_iso_naive_datetime_is_normalized_to_utc():
    """A timezone-naive ISO timestamp is coerced to UTC rather than returning None.

    Without this, comparing a naive datetime with a timezone-aware GitHub API
    timestamp raises ``TypeError: can't compare offset-naive and offset-aware
    datetimes``, crashing the re-review polling loop.
    """
    parsed = github_re_review._parse_iso('2026-01-01T00:00:00')

    assert parsed is not None
    assert parsed.utcoffset().total_seconds() == 0


# =============================================================================
# bot_kind_for_author (login -> canonical bot_kind)
# =============================================================================


def test_bot_kind_for_author_none_returns_none():
    """A falsy author login resolves to None (the guard branch)."""
    assert github_re_review.bot_kind_for_author(None) is None
    assert github_re_review.bot_kind_for_author('') is None


def test_bot_kind_for_author_strips_bot_suffix():
    """A ``[bot]``-suffixed login is normalized before lookup."""
    assert github_re_review.bot_kind_for_author('coderabbitai[bot]') == 'coderabbit'


def test_bot_kind_for_author_is_case_insensitive():
    """Login casing drift is tolerated via lower-casing."""
    assert github_re_review.bot_kind_for_author('CodeRabbitAI') == 'coderabbit'


def test_bot_kind_for_author_known_pr_agent_login():
    """The PR-Agent bot account login maps to the pr-agent bot_kind."""
    assert github_re_review.bot_kind_for_author('cuioss-review-bot') == 'pr-agent'


def test_bot_kind_for_author_unregistered_bot_returns_none():
    """A login absent from the registry resolves to None, exactly like a human.

    This is the retirement contract at its source: a retired or renamed bot's
    login yields no ``bot_kind``, so its comment travels the human-author path and
    is FILED unattributed rather than dropped. Asserted here at the resolver so
    the guarantee does not depend on a producer-level test.
    """
    assert github_re_review.bot_kind_for_author('some-retired-bot') is None
    assert github_re_review.bot_kind_for_author('some-retired-bot[bot]') is None


def test_bot_kind_for_author_known_sourcery_login():
    """The sourcery bot account login maps to the sourcery bot_kind."""
    assert github_re_review.bot_kind_for_author('sourcery-ai') == 'sourcery'


def test_bot_kind_for_author_sourcery_strips_bot_suffix():
    """A ``[bot]``-suffixed sourcery login is normalized before lookup."""
    assert github_re_review.bot_kind_for_author('sourcery-ai[bot]') == 'sourcery'


def test_bot_kind_for_author_human_returns_none():
    """A human (non-bot) author login resolves to None."""
    assert github_re_review.bot_kind_for_author('octocat') is None


# =============================================================================
# main() CLI entrypoint (argparse wiring → handler → TOON print)
# =============================================================================


def test_main_re_review_wires_args_and_prints_toon(monkeypatch, capsys):
    """main() parses argv, runs cmd_re_review, and prints a TOON envelope.

    All gh I/O is mocked: coderabbit's request posts its trigger comment and the
    fetch returns a fresh review for HEAD so the handler reports matched=True.
    """
    _noop_sleep(monkeypatch)
    # Freeze the trigger clock: request_fresh_review stamps trigger_time via
    # _now_iso(), and _match_review only accepts a review whose submitted_at
    # post-dates it. Without freezing, once the real wall clock passes the
    # hardcoded 2026-01-01 review timestamp the match can never succeed and
    # poll_until busy-loops (sleep is a no-op here) until timeout — a time-bomb
    # that turns this into a multi-minute CPU spin. Pin trigger just before the
    # mocked review's 00:05 stamp so the match is deterministic and instant.
    monkeypatch.setattr(github_re_review, '_now_iso', lambda: '2026-01-01T00:00:00Z')
    monkeypatch.setattr(
        github_re_review._github,
        'post_pr_comment',
        lambda *_a, **_kw: {'status': 'success'},
    )
    monkeypatch.setattr(
        github_re_review._github,
        'fetch_pr_reviews_with_commits',
        lambda pr_number: {'status': 'success', 'reviews': [_review('headsha', '2026-01-01T00:05:00Z')]},
    )
    monkeypatch.setattr(
        sys,
        'argv',
        [
            'github_re_review.py',
            're-review',
            '--pr-number',
            '42',
            '--bot-kind',
            'coderabbit',
            '--head-sha',
            'headsha',
            '--push-time',
            '2026-01-01T00:00:00Z',
        ],
    )

    rc = github_re_review.main()

    assert rc == 0
    out = capsys.readouterr().out
    assert 'success' in out
    assert 'coderabbit' in out
    assert 'headsha' in out


def test_main_re_review_accepts_sourcery_bot_kind(monkeypatch, capsys):
    """main() accepts ``--bot-kind sourcery`` through argparse and posts its trigger.

    Proves sourcery is a valid ``--bot-kind`` argparse choice end-to-end (a value
    outside ``choices=BOT_KINDS`` would raise SystemExit at parse time).
    """
    _noop_sleep(monkeypatch)
    # Freeze the trigger clock so the match is deterministic and instant — see
    # test_main_re_review_wires_args_and_prints_toon for the time-bomb rationale.
    monkeypatch.setattr(github_re_review, '_now_iso', lambda: '2026-01-01T00:00:00Z')
    post_calls = {'args': []}

    def fake_post(pr_number, body):
        post_calls['args'].append((pr_number, body))
        return {'status': 'success'}

    monkeypatch.setattr(github_re_review._github, 'post_pr_comment', fake_post)
    monkeypatch.setattr(
        github_re_review._github,
        'fetch_pr_reviews_with_commits',
        lambda pr_number: {'status': 'success', 'reviews': [_review('headsha', '2026-01-01T00:05:00Z')]},
    )
    monkeypatch.setattr(
        sys,
        'argv',
        [
            'github_re_review.py',
            're-review',
            '--pr-number',
            '42',
            '--bot-kind',
            'sourcery',
            '--head-sha',
            'headsha',
            '--push-time',
            '2026-01-01T00:00:00Z',
        ],
    )

    rc = github_re_review.main()

    assert rc == 0
    out = capsys.readouterr().out
    assert 'success' in out
    assert 'sourcery' in out
    assert post_calls['args'] == [(42, '@sourcery-ai review')]


def test_main_parses_timeout_flag_and_threads_it(monkeypatch):
    """main() must parse ``--timeout`` and thread the value into the handler.

    Capture the parsed args the handler receives by stubbing cmd_re_review, and
    assert the namespace carries the exact ``--timeout`` integer from argv.
    """
    captured = {}

    def fake_handler(args):
        captured['timeout'] = args.timeout
        return {'status': 'success'}

    monkeypatch.setattr(github_re_review, 'cmd_re_review', fake_handler)
    monkeypatch.setattr(
        sys,
        'argv',
        [
            'github_re_review.py',
            're-review',
            '--pr-number',
            '42',
            '--bot-kind',
            'coderabbit',
            '--head-sha',
            'headsha',
            '--push-time',
            '2026-01-01T00:00:00Z',
            '--timeout',
            '77',
        ],
    )

    rc = github_re_review.main()

    assert rc == 0
    assert captured['timeout'] == 77


def test_main_timeout_defaults_when_flag_omitted(monkeypatch):
    """When ``--timeout`` is absent, main() supplies the canonical default.

    Asserts the argparse default is ``DEFAULT_CI_TIMEOUT`` rather than None, so
    the handler always has a concrete integer to forward to await.
    """
    captured = {}

    def fake_handler(args):
        captured['timeout'] = args.timeout
        return {'status': 'success'}

    monkeypatch.setattr(github_re_review, 'cmd_re_review', fake_handler)
    monkeypatch.setattr(
        sys,
        'argv',
        [
            'github_re_review.py',
            're-review',
            '--pr-number',
            '42',
            '--bot-kind',
            'coderabbit',
            '--head-sha',
            'headsha',
            '--push-time',
            '2026-01-01T00:00:00Z',
        ],
    )

    rc = github_re_review.main()

    assert rc == 0
    assert captured['timeout'] == ci_base.DEFAULT_CI_TIMEOUT

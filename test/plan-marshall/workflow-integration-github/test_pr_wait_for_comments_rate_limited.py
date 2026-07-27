#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``rate_limited`` discriminator on ``pr wait-for-comments``.

``cmd_pr_wait_for_comments`` (in ``_github_pr.py``, dispatched via
``github_ops``) surfaces an additive ``rate_limited: true|false`` field: after
the poll settles it inspects the newest CodeRabbit-bot comment for a rate-limit
status notice. Comment SELECTION stays provider-scoped (GitHub/CodeRabbit —
author-scoped, newest by ``created_at``); the body CLASSIFIER is the shared
bot-agnostic ``_is_rate_limit_notice``, which requires BOTH a limit-exceeded
statement AND a notice shape (callout / limit heading / service tail). The
discriminator must never alter the pre-existing poll fields (``timed_out`` /
``new_count`` / …).

Scope (AAA against fixture comment payloads):
    - newest bot comment is a rate-limit status notice → rate_limited: true
      (fixture uses the FLATTENED production body shape — see _RATE_LIMIT_NOTICE)
    - CodeRabbit's CURRENT ``Review limit reached`` refusal → rate_limited: true
      (the phrasing the retired CodeRabbit-exact marker island missed)
    - newest bot comment is a genuine review          → rate_limited: false
    - no bot comment / empty comment list             → rate_limited: false
    - a newer genuine review supersedes an older notice → rate_limited: false
    - a bot review carrying only the body sentence (no notice shape) →
      rate_limited: false
    - author-scoped newest-comment selection and the pre-existing
      timed_out / new_count fields are unchanged by the re-pointing

Tests never shell out to the real ``gh`` CLI: ``check_auth``,
``fetch_pr_comments_data``, and ``poll_until`` are monkeypatched so the handler
runs deterministically in constant time.
"""

import argparse

import github_ops


def _ok_auth():
    return True, ''


# A CodeRabbit rate-limit status notice (posted in place of a review), in the
# FLATTENED shape the detector actually sees. ``fetch_pr_comments_data`` collapses
# every comment body's newlines to spaces before ``_detect_coderabbit_rate_limited``
# inspects it, so the ``## Rate limit exceeded`` heading no longer sits at a line
# start — it appears mid-body after the ``> [!WARNING]`` callout prefix. Using the
# flattened production shape here proves the heading marker fires WITHOUT relying
# on a ``^``/``re.MULTILINE`` line-start anchor (which could only match at offset 0
# on a single-line body and therefore never fired against a real notice).
_RATE_LIMIT_NOTICE = {
    'author': 'coderabbitai[bot]',
    'body': (
        '> [!WARNING] > ## Rate limit exceeded > '
        '@octocat has exceeded the limit for the number of commits or files '
        'that can be reviewed per hour. Please wait before requesting another review.'
    ),
    'created_at': '2026-01-02T00:00:00Z',
}

# CodeRabbit's CURRENT refusal notice — the phrasing the retired CodeRabbit-exact
# marker island MISSED. It carries neither the old ``## Rate limit exceeded``
# heading nor the ``exceeded the limit for the number of`` body sentence, so the
# two-marker island scored it False. The shared recognizer matches it on a
# limit-exceeded statement (``Review limit reached``) paired with a notice shape.
_REVIEW_LIMIT_REACHED_NOTICE = {
    'author': 'coderabbitai[bot]',
    'body': (
        '> [!WARNING] > ## Review limit reached > '
        'You have reached your review limit for the current billing cycle. '
        'Reviews will resume once the limit resets.'
    ),
    'created_at': '2026-01-02T00:00:00Z',
}

# A genuine CodeRabbit review comment (actual feedback, not a status notice).
_GENUINE_REVIEW = {
    'author': 'coderabbitai[bot]',
    'body': 'Actionable comments posted: 2. Consider extracting the helper in foo().',
    'created_at': '2026-01-02T00:00:00Z',
}

# A human review comment — never a rate-limit notice regardless of body.
_HUMAN_COMMENT = {
    'author': 'octocat',
    'body': 'Please add a test for the rate limit exceeded branch.',
    'created_at': '2026-01-01T00:00:00Z',
}


def _wait_comments_args(*, pr_number=123, timeout=5, interval=0):
    return argparse.Namespace(pr_number=pr_number, timeout=timeout, interval=interval)


def _wire(monkeypatch, *, post_comments):
    """Monkeypatch auth / fetch / poll so the handler runs deterministically.

    ``fetch_pr_comments_data`` answers the initial ``unresolved_only=True`` probe
    with a baseline count of 1, and the post-poll full fetch with
    ``post_comments``. ``poll_until`` returns a canned grown-count result so the
    poll fields are stable and the timeout branch never sleeps.
    """
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)

    def fake_fetch(pr_number, unresolved_only=False):
        assert pr_number == 123
        if unresolved_only:
            return {'status': 'success', 'unresolved': 1}
        return {'status': 'success', 'comments': post_comments}

    monkeypatch.setattr(github_ops, 'fetch_pr_comments_data', fake_fetch)

    def fake_poll(check_fn, is_complete_fn, timeout=None, interval=None):
        return {'timed_out': False, 'duration_sec': 1, 'polls': 1, 'last_data': {'unresolved': 2}}

    monkeypatch.setattr(github_ops, 'poll_until', fake_poll)


def test_rate_limit_notice_sets_rate_limited_true(monkeypatch):
    _wire(monkeypatch, post_comments=[_HUMAN_COMMENT, _RATE_LIMIT_NOTICE])

    result = github_ops.cmd_pr_wait_for_comments(_wait_comments_args())

    assert result['status'] == 'success'
    assert result['rate_limited'] is True
    # Pre-existing poll fields are unchanged by the additive discriminator.
    assert result['timed_out'] is False
    assert result['new_count'] == 1
    assert result['final_count'] == 2
    assert result['baseline_count'] == 1


def test_current_review_limit_reached_notice_sets_rate_limited_true(monkeypatch):
    # Regression pin for the collapse: CodeRabbit's CURRENT refusal phrasing.
    # The retired two-marker island required the "## Rate limit exceeded" heading
    # AND the "exceeded the limit for the number of" sentence — this notice has
    # NEITHER (asserted below), so the island silently scored it False. The shared
    # recognizer classifies it on structure instead, and the discriminator fires.
    assert 'exceeded the limit for the number of' not in _REVIEW_LIMIT_REACHED_NOTICE['body']
    assert '## Rate limit exceeded' not in _REVIEW_LIMIT_REACHED_NOTICE['body']

    _wire(monkeypatch, post_comments=[_HUMAN_COMMENT, _REVIEW_LIMIT_REACHED_NOTICE])

    result = github_ops.cmd_pr_wait_for_comments(_wait_comments_args())

    assert result['status'] == 'success'
    assert result['rate_limited'] is True


def test_newest_bot_selection_and_human_exclusion_survive_repointing(monkeypatch):
    # The re-pointing changed ONLY the body classifier. This pins the three
    # behaviours that must be unchanged by it:
    #   1. human-author exclusion — the newest comment overall is human-authored
    #      and must not be considered at all;
    #   2. newest-by-created_at selection AMONG bot comments — an older genuine
    #      bot review must not displace the newer bot notice;
    #   3. the additive contract — every pre-existing poll field is untouched.
    newest_human = dict(_HUMAN_COMMENT, created_at='2026-01-09T00:00:00Z')
    older_bot_review = dict(_GENUINE_REVIEW, created_at='2026-01-01T00:00:00Z')
    _wire(monkeypatch, post_comments=[newest_human, older_bot_review, _REVIEW_LIMIT_REACHED_NOTICE])

    result = github_ops.cmd_pr_wait_for_comments(_wait_comments_args())

    assert result['rate_limited'] is True
    assert result['timed_out'] is False
    assert result['new_count'] == 1
    assert result['baseline_count'] == 1
    assert result['final_count'] == 2
    assert result['duration_sec'] == 1
    assert result['polls'] == 1


def test_genuine_review_sets_rate_limited_false(monkeypatch):
    _wire(monkeypatch, post_comments=[_HUMAN_COMMENT, _GENUINE_REVIEW])

    result = github_ops.cmd_pr_wait_for_comments(_wait_comments_args())

    assert result['status'] == 'success'
    assert result['rate_limited'] is False
    assert result['timed_out'] is False
    assert result['new_count'] == 1


def test_no_bot_comment_sets_rate_limited_false(monkeypatch):
    _wire(monkeypatch, post_comments=[])

    result = github_ops.cmd_pr_wait_for_comments(_wait_comments_args())

    assert result['status'] == 'success'
    assert result['rate_limited'] is False
    # Field is present (not merely absent) so consumers can rely on it.
    assert 'rate_limited' in result
    assert result['new_count'] == 1


def test_newer_review_supersedes_older_rate_limit_notice(monkeypatch):
    # An older rate-limit notice followed by a NEWER genuine review — the newest
    # bot comment wins, so the poll observed real feedback, not a status notice.
    older_notice = dict(_RATE_LIMIT_NOTICE, created_at='2026-01-01T00:00:00Z')
    newer_review = dict(_GENUINE_REVIEW, created_at='2026-01-03T00:00:00Z')
    _wire(monkeypatch, post_comments=[older_notice, newer_review])

    result = github_ops.cmd_pr_wait_for_comments(_wait_comments_args())

    assert result['rate_limited'] is False


def test_human_comment_with_rate_limit_prose_not_flagged(monkeypatch):
    # A human comment quoting "rate limit exceeded" is not a CodeRabbit notice.
    _wire(monkeypatch, post_comments=[_HUMAN_COMMENT])

    result = github_ops.cmd_pr_wait_for_comments(_wait_comments_args())

    assert result['rate_limited'] is False


def test_bot_review_quoting_rate_limit_prose_not_flagged(monkeypatch):
    # A GENUINE CodeRabbit review whose body merely QUOTES the phrase "rate limit
    # exceeded" in prose (not the ``## Rate limit exceeded`` notice heading) must
    # not be misclassified as a status notice — the markers are anchored to the
    # notice's heading/body structure, not a bare phrase match.
    bot_prose = {
        'author': 'coderabbitai[bot]',
        'body': (
            'Actionable comments posted: 1. The handler returns the literal '
            'string "Rate limit exceeded" when the quota is hit — please add a '
            'test covering that rate limit exceeded branch.'
        ),
        'created_at': '2026-01-02T00:00:00Z',
    }
    _wire(monkeypatch, post_comments=[_HUMAN_COMMENT, bot_prose])

    result = github_ops.cmd_pr_wait_for_comments(_wait_comments_args())

    assert result['rate_limited'] is False


def test_bot_body_sentence_without_heading_not_flagged(monkeypatch):
    # gemini-code-assist false-positive guard: a genuine CodeRabbit review whose
    # flattened body merely contains the "exceeded the limit for the number of"
    # body sentence (e.g. discussing a parameter/line limit) in plain prose must
    # not be flagged. The shared recognizer requires a limit-exceeded statement
    # AND a notice shape — with no callout, no limit heading and no service tail,
    # the body sentence alone is insufficient.
    body_only = {
        'author': 'coderabbitai[bot]',
        'body': (
            'Actionable comments posted: 1. This function has exceeded the limit '
            'for the number of parameters recommended by the style guide; '
            'consider grouping them into a dataclass.'
        ),
        'created_at': '2026-01-02T00:00:00Z',
    }
    _wire(monkeypatch, post_comments=[_HUMAN_COMMENT, body_only])

    result = github_ops.cmd_pr_wait_for_comments(_wait_comments_args())

    assert result['rate_limited'] is False

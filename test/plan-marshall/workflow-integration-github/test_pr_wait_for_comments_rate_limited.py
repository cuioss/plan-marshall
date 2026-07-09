#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``rate_limited`` discriminator on ``pr wait-for-comments``.

``cmd_pr_wait_for_comments`` (in ``_github_pr.py``, dispatched via
``github_ops``) surfaces an additive ``rate_limited: true|false`` field: after
the poll settles it inspects the newest CodeRabbit-bot comment for a rate-limit
status notice. The discriminator is provider-scoped (GitHub/CodeRabbit) and must
never alter the pre-existing poll fields (``timed_out`` / ``new_count`` / …).

Scope (AAA against fixture comment payloads):
    - newest bot comment is a rate-limit status notice → rate_limited: true
    - newest bot comment is a genuine review          → rate_limited: false
    - no bot comment / empty comment list             → rate_limited: false
    - a newer genuine review supersedes an older notice → rate_limited: false
    - the pre-existing timed_out / new_count fields are unchanged

Tests never shell out to the real ``gh`` CLI: ``check_auth``,
``fetch_pr_comments_data``, and ``poll_until`` are monkeypatched so the handler
runs deterministically in constant time.
"""

import argparse

import github_ops


def _ok_auth():
    return True, ''


# A CodeRabbit rate-limit status notice (posted in place of a review).
_RATE_LIMIT_NOTICE = {
    'author': 'coderabbitai[bot]',
    'body': (
        '> [!WARNING]\n> ## Rate limit exceeded\n>\n'
        '> @octocat has exceeded the limit for the number of commits or files '
        'that can be reviewed per hour. Please wait before requesting another review.'
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

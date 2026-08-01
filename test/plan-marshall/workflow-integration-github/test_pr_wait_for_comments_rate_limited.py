#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``rate_limited_bots[]`` discriminator on ``pr wait-for-comments``.

``cmd_pr_wait_for_comments`` (in ``_github_pr.py``, dispatched via ``github_ops``)
surfaces a ``rate_limited_bots[]`` field: after the poll settles it inspects EVERY
REGISTERED bot's newest comment for a rate-limit status notice and returns one
``{bot_kind, rate_limit_class, eta}`` record per detected bot. A single boolean
cannot carry that answer: it collapses a three-bot pipeline into one
CodeRabbit-shaped verdict, leaving a rate-limited Sourcery or PR-Agent invisible.

The generalization is registry-driven end to end and carries NO bot-name literal
in the detection path:

- the bot set and each bot's login come from ``bot_registry`` (resolved through
  ``github_re_review.bot_kind_for_author``, which owns ``[bot]``-suffix stripping);
- ``rate_limit_class`` is registry data (``awaitable_window`` / ``hard_quota``),
  fail-closed to ``unknown`` for a bot that declares none (ADR-009);
- ``eta`` is extracted with that bot's registry ``rate_limit_eta_patterns``, and is
  ``''`` when the bot declares none or its notice states none;
- body CLASSIFICATION stays the shared bot-agnostic ``_is_rate_limit_notice``,
  which requires BOTH a limit-exceeded statement AND a notice shape.

Scope (AAA against fixture comment payloads):
    - a NON-CodeRabbit bot's rate-limit notice is detected, with its own class
    - a bot whose registry record declares no class fails closed to ``unknown``
    - CodeRabbit's notice yields its registry-extracted ``eta``
    - several bots rate-limited at once each yield their own record
    - per-bot newest-by-``created_at`` selection: a newer genuine review from the
      SAME bot supersedes that bot's older notice, without hiding another bot
    - a genuine review merely mentioning a rate limit in prose is NOT a notice
    - human comments never contribute a record
    - the pre-existing poll fields (``timed_out`` / ``new_count`` / …) are unchanged
    - the completion-predicate fields (``movement_matched_bots`` /
      ``detector_answerable`` / ``unanswerable_reason``) are present and orthogonal
      to the discriminator: a refusal is never a re-review arrival, and an await
      that merely saw no movement stays ``detector_answerable: true``

Tests never shell out to the real ``gh`` CLI: ``check_auth``,
``fetch_pr_comments_data``, and ``poll_until`` are monkeypatched so the handler
runs deterministically in constant time.
"""

import argparse

import github_ops


def _ok_auth():
    return True, ''


# --- CodeRabbit (registry class: awaitable_window, declares ETA patterns) ----
#
# The FLATTENED body shape the detector actually sees: ``fetch_pr_comments_data``
# collapses every comment body's newlines to spaces before classification, so the
# ``## Rate limit exceeded`` heading sits mid-body after the ``> [!WARNING]``
# callout prefix rather than at a line start. The trailing "Please wait N minutes
# and M seconds before requesting another review" sentence is what CodeRabbit's
# registry ``rate_limit_eta_patterns`` extract.
_CODERABBIT_NOTICE = {
    'author': 'coderabbitai[bot]',
    'body': (
        '> [!WARNING] > ## Rate limit exceeded > '
        '@octocat has exceeded the limit for the number of commits or files '
        'that can be reviewed per hour. Please wait 12 minutes and 30 seconds '
        'before requesting another review.'
    ),
    'created_at': '2026-01-02T00:00:00Z',
}

# CodeRabbit's CURRENT refusal phrasing — no ``## Rate limit exceeded`` heading and
# no ``exceeded the limit for the number of`` sentence, and no stated reset time.
_CODERABBIT_REVIEW_LIMIT_REACHED = {
    'author': 'coderabbitai[bot]',
    'body': (
        '> [!WARNING] > ## Review limit reached > '
        'You have reached your review limit for the current billing cycle. '
        'Reviews will resume once the limit resets.'
    ),
    'created_at': '2026-01-02T00:00:00Z',
}

# A genuine CodeRabbit review comment (actual feedback, not a status notice).
_CODERABBIT_GENUINE_REVIEW = {
    'author': 'coderabbitai[bot]',
    'body': 'Actionable comments posted: 2. Consider extracting the helper in foo().',
    'created_at': '2026-01-02T00:00:00Z',
}

# --- Sourcery (registry class: hard_quota, declares NO ETA patterns) ---------
_SOURCERY_NOTICE = {
    'author': 'sourcery-ai[bot]',
    'body': (
        '> [!WARNING] Sourcery has reached your review limit for this pull request. '
        'Reviews will resume once the limit resets.'
    ),
    'created_at': '2026-01-02T00:00:00Z',
}

# --- PR-Agent (registry class: absent -> fail-closed ``unknown``) ------------
_PR_AGENT_NOTICE = {
    'author': 'cuioss-review-bot',
    'body': (
        '> [!WARNING] The review request could not be served: this account has '
        'exceeded the limit for the number of commits or files that can be '
        'reviewed. Please try again later.'
    ),
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

    The ``unresolved_only=True`` branch carries a ``comments`` key because the real
    ``fetch_pr_comments_data`` always does — ``unresolved_only`` filters resolved
    review THREADS, it never drops the record list. The completion predicate's
    movement arm reads that list, so a fixture omitting the key would diverge from
    the shape production returns and quietly exercise only the count arm. It is
    EMPTY here on purpose: this file pins the rate-limit discriminator, so the
    movement arm must contribute nothing and the count arm alone must end the poll.
    """
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)

    def fake_fetch(pr_number, unresolved_only=False):
        assert pr_number == 123
        if unresolved_only:
            return {'status': 'success', 'unresolved': 1, 'comments': []}
        return {'status': 'success', 'comments': post_comments}

    monkeypatch.setattr(github_ops, 'fetch_pr_comments_data', fake_fetch)

    def fake_poll(check_fn, is_complete_fn, timeout=None, interval=None):
        return {'timed_out': False, 'duration_sec': 1, 'polls': 1, 'last_data': {'unresolved': 2}}

    monkeypatch.setattr(github_ops, 'poll_until', fake_poll)


def _records_by_kind(result):
    return {record['bot_kind']: record for record in result['rate_limited_bots']}


def test_non_coderabbit_bot_rate_limit_is_detected(monkeypatch):
    # THE generalization pin. Pre-fix, detection was author-scoped to the two
    # CodeRabbit logins, so a rate-limited Sourcery scored negative — the bot's
    # non-participation was silently indistinguishable from a clean run.
    # The registry-driven detector reports it as its own record, carrying the class
    # Sourcery's registry record declares (hard_quota: a per-PR size budget that
    # does NOT reopen, so awaiting it would burn the full budget and still fail).
    _wire(monkeypatch, post_comments=[_HUMAN_COMMENT, _SOURCERY_NOTICE])

    result = github_ops.cmd_pr_wait_for_comments(_wait_comments_args())

    assert result['status'] == 'success'
    assert result['rate_limited_bots'] == [
        {'bot_kind': 'sourcery', 'rate_limit_class': 'hard_quota', 'eta': ''}
    ]
    # Pre-existing poll fields are unchanged by the discriminator.
    assert result['timed_out'] is False
    assert result['new_count'] == 1
    assert result['final_count'] == 2
    assert result['baseline_count'] == 1
    # The completion predicate's own fields: this poll ended on the COUNT arm, so
    # the movement arm matched nothing. A refusing bot must never register as a
    # re-review arrival — the two signals stay orthogonal.
    assert result['movement_matched_bots'] == []


def test_bot_without_declared_class_fails_closed_to_unknown(monkeypatch):
    # ADR-009 fail-closed default: PR-Agent's registry record declares
    # rate_limit_class: unknown because no refusal has ever been OBSERVED for it.
    # A bot whose refusal shape is unknown must never be reported as awaitable —
    # awaiting a quota that does not reopen is the expensive failure mode.
    _wire(monkeypatch, post_comments=[_PR_AGENT_NOTICE])

    result = github_ops.cmd_pr_wait_for_comments(_wait_comments_args())

    assert result['rate_limited_bots'] == [
        {'bot_kind': 'pr-agent', 'rate_limit_class': 'unknown', 'eta': ''}
    ]


def test_coderabbit_notice_yields_registry_extracted_eta(monkeypatch):
    # The ETA phrasings are registry data (rate_limit_eta_patterns), not a literal
    # in the detection path: the notice's own stated reset time is surfaced so a
    # caller can report a concrete wait instead of an opaque "rate-limited".
    _wire(monkeypatch, post_comments=[_HUMAN_COMMENT, _CODERABBIT_NOTICE])

    result = github_ops.cmd_pr_wait_for_comments(_wait_comments_args())

    assert result['rate_limited_bots'] == [
        {
            'bot_kind': 'coderabbit',
            'rate_limit_class': 'awaitable_window',
            'eta': '12 minutes and 30 seconds',
        }
    ]


def test_notice_stating_no_eta_yields_empty_eta(monkeypatch):
    # CodeRabbit's CURRENT refusal phrasing carries neither the old heading nor the
    # old body sentence (asserted here so the fixture cannot silently drift back to
    # the retired shape) and states no reset time. An absent ETA is reported as
    # absent — never invented, and never read as "reopens now".
    assert 'exceeded the limit for the number of' not in _CODERABBIT_REVIEW_LIMIT_REACHED['body']
    assert '## Rate limit exceeded' not in _CODERABBIT_REVIEW_LIMIT_REACHED['body']

    _wire(monkeypatch, post_comments=[_CODERABBIT_REVIEW_LIMIT_REACHED])

    result = github_ops.cmd_pr_wait_for_comments(_wait_comments_args())

    assert result['rate_limited_bots'] == [
        {'bot_kind': 'coderabbit', 'rate_limit_class': 'awaitable_window', 'eta': ''}
    ]


def test_several_rate_limited_bots_each_yield_their_own_record(monkeypatch):
    # The scalar could only ever answer for one bot. The list answers per bot, and
    # each record carries that bot's own class — which is the whole point: the
    # await decision differs between an awaitable_window and a hard_quota.
    _wire(
        monkeypatch,
        post_comments=[_HUMAN_COMMENT, _CODERABBIT_NOTICE, _SOURCERY_NOTICE, _PR_AGENT_NOTICE],
    )

    result = github_ops.cmd_pr_wait_for_comments(_wait_comments_args())

    records = _records_by_kind(result)
    assert set(records) == {'coderabbit', 'sourcery', 'pr-agent'}
    assert records['coderabbit']['rate_limit_class'] == 'awaitable_window'
    assert records['sourcery']['rate_limit_class'] == 'hard_quota'
    assert records['pr-agent']['rate_limit_class'] == 'unknown'


def test_no_rate_limited_bot_yields_empty_list(monkeypatch):
    _wire(monkeypatch, post_comments=[_HUMAN_COMMENT, _CODERABBIT_GENUINE_REVIEW])

    result = github_ops.cmd_pr_wait_for_comments(_wait_comments_args())

    assert result['status'] == 'success'
    # Field is present (not merely absent) so consumers can rely on it: an empty
    # list is the positive "no registered bot is rate-limited" signal.
    assert 'rate_limited_bots' in result
    assert result['rate_limited_bots'] == []
    assert result['new_count'] == 1


def test_empty_comment_list_yields_empty_list(monkeypatch):
    _wire(monkeypatch, post_comments=[])

    result = github_ops.cmd_pr_wait_for_comments(_wait_comments_args())

    assert result['rate_limited_bots'] == []


def test_newer_review_supersedes_that_bots_older_notice_only(monkeypatch):
    # Selection is newest-by-created_at PER BOT, not globally. CodeRabbit's older
    # notice is superseded by its own newer genuine review, while Sourcery — whose
    # newest comment is still a notice — remains detected. A global "newest
    # comment" pick would have hidden Sourcery behind CodeRabbit's recovery.
    older_coderabbit_notice = dict(_CODERABBIT_NOTICE, created_at='2026-01-01T00:00:00Z')
    newer_coderabbit_review = dict(_CODERABBIT_GENUINE_REVIEW, created_at='2026-01-03T00:00:00Z')
    newest_human = dict(_HUMAN_COMMENT, created_at='2026-01-09T00:00:00Z')
    _wire(
        monkeypatch,
        post_comments=[
            older_coderabbit_notice,
            newer_coderabbit_review,
            _SOURCERY_NOTICE,
            newest_human,
        ],
    )

    result = github_ops.cmd_pr_wait_for_comments(_wait_comments_args())

    assert [record['bot_kind'] for record in result['rate_limited_bots']] == ['sourcery']
    # The additive contract: every pre-existing poll field is untouched.
    assert result['timed_out'] is False
    assert result['baseline_count'] == 1
    assert result['final_count'] == 2
    assert result['new_count'] == 1
    assert result['duration_sec'] == 1
    assert result['polls'] == 1
    # …and every field the widened completion predicate added is PRESENT, so this
    # file keeps pinning the whole return shape rather than silently stopping at
    # the fields that existed when it was written.
    assert result['movement_matched_bots'] == []
    # Answerability is derived from the REGISTRY alone, never from the observed
    # comment set: these fixtures stage no bot movement at all, yet the shipped
    # registry declares bot kinds WITH participation evidence, so the await was
    # genuinely answerable and simply saw no movement. This asserts the
    # not-widened boundary the operator settled — a silent await is a real
    # timeout, not an unanswerable detector.
    assert result['detector_answerable'] is True
    assert result['unanswerable_reason'] == ''


def test_human_comment_quoting_a_refusal_is_not_a_notice(monkeypatch):
    # A human quoting "rate limit exceeded" resolves to no bot_kind at all, so it
    # can never contribute a record regardless of its body.
    _wire(monkeypatch, post_comments=[_HUMAN_COMMENT])

    result = github_ops.cmd_pr_wait_for_comments(_wait_comments_args())

    assert result['rate_limited_bots'] == []


def test_genuine_review_mentioning_a_rate_limit_in_prose_is_not_a_notice(monkeypatch):
    # Precision guard on the shared classifier, unchanged by the generalization: a
    # GENUINE review whose body merely QUOTES the phrase in prose — no notice shape
    # — is real feedback, and must not be reported as the bot refusing to review.
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

    assert result['rate_limited_bots'] == []


def test_bot_body_sentence_without_notice_shape_is_not_a_notice(monkeypatch):
    # gemini-code-assist false-positive guard: a genuine review whose flattened
    # body contains the "exceeded the limit for the number of" sentence (discussing
    # a parameter limit) but carries no callout, no limit heading and no service
    # tail is insufficient — the recognizer requires BOTH signals conjunctively.
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

    assert result['rate_limited_bots'] == []

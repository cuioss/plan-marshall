# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``rate_limited_bots[]`` discriminator on ``pr wait-for-comments``.

``cmd_pr_wait_for_comments`` (in ``_github_pr.py``, dispatched via ``github_ops``)
surfaces a ``rate_limited_bots[]`` field: after the poll settles it inspects EVERY
REGISTERED bot's most recently written comment for a refusal notice and returns one
``{bot_kind, rate_limit_class, condition, eta, eta_seconds, eta_extracted, written_at,
stale, cause, cap, layer, body}`` record per detected bot. ``condition`` says what the notice reports:
``rate_limited`` for a limit, ``no_unreviewed_commit`` for a reply saying nothing new
is left to review. A boolean cannot carry that answer: it collapses a three-bot pipeline into one
CodeRabbit-shaped verdict, leaving a rate-limited Sourcery or PR-Agent invisible.

The generalization is registry-driven end to end and carries NO bot-name literal
in the detection path:

- the bot set and each bot's login come from ``bot_registry`` (resolved through
  ``github_re_review.bot_kind_for_author``, which owns ``[bot]``-suffix stripping);
- ``rate_limit_class`` is registry data (``awaitable_window`` / ``hard_quota``),
  fail-closed to ``unknown`` for a bot that declares none (ADR-009);
- ``eta`` is extracted with that bot's registry ``rate_limit_eta_patterns``, and is
  ``''`` when the bot declares none or its notice states none; ``eta_seconds`` is
  that time as whole seconds (``None`` when none was read) and ``eta_extracted``
  states which of the two it is;
- ``written_at`` is the instant the notice was last written — the later of the
  comment's ``updated_at`` and ``created_at`` — and ``stale`` is ``True`` when the
  window the notice stated had already elapsed when the notice was read;
- ``cause`` / ``cap`` are the orthogonal SIZE-vs-QUOTA axis, derived from that bot's
  ``refusal_size_patterns`` / ``refusal_size_cap_patterns``. They are INDEPENDENT of
  ``rate_limit_class``: one bot can refuse for both causes at one class, so the
  class cannot answer which remedy applies. Both keys ride every record, and an
  empty ``cap`` reads as UNKNOWN rather than as a figure;
- ``layer`` / ``body`` are the OBSERVATION behind the refusal — the recognition arm
  that read the notice (the first of ``_github_pr.refusal_layers`` in consult
  order) and the notice's truncated excerpt — the observation fields this record
  shares with ``github_re_review``'s ``refusals[]`` record;
- body CLASSIFICATION stays the shared bot-agnostic ``_is_rate_limit_notice``,
  which requires BOTH a limit-exceeded statement AND a notice shape.

Scope (AAA against fixture comment payloads):
    - a NON-CodeRabbit bot's rate-limit notice is detected, with its own class
    - a bot whose registry record declares no class fails closed to ``unknown``
    - CodeRabbit's notice yields its registry-extracted ``eta``
    - several bots rate-limited at once each yield their own record
    - per-bot selection of the comment written last: a newer genuine review from
      the SAME bot supersedes that bot's older notice, without hiding another bot,
      and an older-created comment EDITED into a refusal after a newer one was
      posted is the one sampled
    - a notice whose stated window elapsed before it was read reports ``stale``,
      and one read inside its window, or stating no reset time, does not
    - a genuine review merely mentioning a rate limit in prose is NOT a notice
    - human comments never contribute a record
    - a registry-declared refusal reports the registry ``layer`` even when the
      structural arm also fired, and a long multi-line notice is carried as the same
      collapsed, truncated excerpt ``refusals[]`` carries
    - every bundle document that restates the record's field set restates the one
      the detector actually emits
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
import importlib
import re
from datetime import UTC, datetime

import github_ops

from conftest import get_script_path

_github_pr = importlib.import_module('_github_pr')
github_re_review = importlib.import_module('github_re_review')


def _ok_auth():
    return True, ''


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
_CODERABBIT_REVIEW_LIMIT_REACHED = {
    'author': 'coderabbitai[bot]',
    'body': (
        '> [!WARNING] > ## Review limit reached > '
        'You have reached your review limit for the current billing cycle. '
        'Reviews will resume once the limit resets.'
    ),
    'created_at': '2026-01-02T00:00:00Z',
}
_CODERABBIT_GENUINE_REVIEW = {
    'author': 'coderabbitai[bot]',
    'body': 'Actionable comments posted: 2. Consider extracting the helper in foo().',
    'created_at': '2026-01-02T00:00:00Z',
}
_SOURCERY_NOTICE = {
    'author': 'sourcery-ai[bot]',
    'body': (
        '> [!WARNING] Sourcery has reached your review limit for this pull request. '
        'Reviews will resume once the limit resets.'
    ),
    'created_at': '2026-01-02T00:00:00Z',
}
_PR_AGENT_NOTICE = {
    'author': 'cuioss-review-bot',
    'body': (
        '> [!WARNING] The review request could not be served: this account has '
        'exceeded the limit for the number of commits or files that can be '
        'reviewed. Please try again later.'
    ),
    'created_at': '2026-01-02T00:00:00Z',
}
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


_FIELD_SET_RE = re.compile(r'\{bot_kind,\s*rate_limit_class,[^}]*\}')
_BUNDLES = get_script_path('plan-marshall', 'workflow-integration-github', '_github_pr.py').parents[4]


def test_bot_without_declared_class_fails_closed_to_unknown(monkeypatch):
    # ADR-009 fail-closed default: PR-Agent's registry record declares
    # rate_limit_class: unknown because no refusal has ever been OBSERVED for it.
    # A bot whose refusal shape is unknown must never be reported as awaitable —
    # awaiting a quota that does not reopen is the expensive failure mode.
    _wire(monkeypatch, post_comments=[_PR_AGENT_NOTICE])

    result = github_ops.cmd_pr_wait_for_comments(_wait_comments_args())

    assert result['rate_limited_bots'] == [
        {
            'bot_kind': 'cuioss-review-bot',
            'rate_limit_class': 'unknown',
            # A limit notice. PR-Agent declares no no-unreviewed-commit wording, so
            # nothing it posts can carry the other condition.
            'condition': _github_pr.REFUSAL_CONDITION_RATE_LIMITED,
            'eta': '',
            # PR-Agent declares no reset-time patterns, so none can be read.
            'eta_seconds': None,
            'eta_extracted': False,
            # The fixture carries no ``updated_at``, so the last write is its creation.
            'written_at': _PR_AGENT_NOTICE['created_at'],
            # No reset time was read, so nothing says the window is over.
            'stale': False,
            'cause': 'quota',
            'cap': '',
            # PR-Agent declares no refusal_patterns, so only the notice SHAPE can
            # have read this one.
            'layer': _github_pr.REFUSAL_LAYER_STRUCTURAL,
            'body': _PR_AGENT_NOTICE['body'],
        }
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
            'condition': _github_pr.REFUSAL_CONDITION_RATE_LIMITED,
            'eta': '12 minutes and 30 seconds',
            # The stated duration converted to seconds: 12 * 60 + 30.
            'eta_seconds': 750,
            'eta_extracted': True,
            'written_at': _CODERABBIT_NOTICE['created_at'],
            # The handler judges the window against the real clock. The fixture's
            # write instant is a fixed past date and the window it states is 750
            # seconds, so that window is over on any run. The stale cases below
            # pass the read instant explicitly instead of relying on the clock.
            'stale': True,
            'cause': 'quota',
            'cap': '',
            # The "## Rate limit exceeded" phrasing is not among CodeRabbit's
            # declared refusal_patterns, so only the shape arm can have read it.
            'layer': _github_pr.REFUSAL_LAYER_STRUCTURAL,
            'body': _CODERABBIT_NOTICE['body'],
        }
    ]


def test_a_registry_declared_refusal_reports_the_registry_layer_over_the_shape(monkeypatch):
    # The current CodeRabbit phrasing is read by BOTH arms: it carries the declared
    # "Review limit reached" wording AND a notice shape. The record reports the arm
    # that read it as DATA — the first in consult order — exactly as
    # ``github_re_review._refusal_record`` resolves the same body, so the two
    # producers name one layer for one notice.
    body = _CODERABBIT_REVIEW_LIMIT_REACHED['body']
    assert _github_pr.refusal_layers(body, 'coderabbit') == [
        _github_pr.REFUSAL_LAYER_REGISTRY,
        _github_pr.REFUSAL_LAYER_STRUCTURAL,
    ]
    _wire(monkeypatch, post_comments=[_CODERABBIT_REVIEW_LIMIT_REACHED])

    result = github_ops.cmd_pr_wait_for_comments(_wait_comments_args())

    [record] = result['rate_limited_bots']
    assert record['layer'] == _github_pr.REFUSAL_LAYER_REGISTRY
    assert (
        record['layer']
        == github_re_review._ReReviewStrategy._refusal_record(body, 'coderabbit', 'issue_comment')['layer']
    )
    # Matched control — the retired phrasing reaches only the shape arm, and the
    # record says so rather than borrowing the stronger layer.
    _wire(monkeypatch, post_comments=[_CODERABBIT_NOTICE])
    [structural] = github_ops.cmd_pr_wait_for_comments(_wait_comments_args())['rate_limited_bots']
    assert structural['layer'] == _github_pr.REFUSAL_LAYER_STRUCTURAL


def test_every_documented_field_set_is_the_one_the_detector_emits():
    # A record shape restated in a doc is a second source of truth: widen the record
    # and every restatement the diff did not touch reads as current while it lies.
    # The expected set is DERIVED from a real detection, never hand-copied, and the
    # population is DERIVED by scanning the bundles — with the known restatement
    # sites asserted present so a misrooted scan fails instead of passing vacuously.
    [record] = _github_pr._detect_rate_limited_bots([_SOURCERY_NOTICE])
    emitted = set(record)

    sites = {}
    for path in sorted(_BUNDLES.rglob('*.md')):
        for match in _FIELD_SET_RE.finditer(path.read_text(encoding='utf-8')):
            documented = {field.strip() for field in match.group(0).strip('{}').split(',')}
            sites.setdefault(path.relative_to(_BUNDLES).as_posix(), []).append(documented)

    for known in (
        'plan-marshall/skills/workflow-integration-github/SKILL.md',
        'plan-marshall/skills/tools-integration-ci/standards/api-contract.md',
        'plan-marshall/skills/tools-integration-ci/standards/pr-review-operations.md',
        'plan-marshall/skills/automatic-review/SKILL.md',
    ):
        assert known in sites, f'{known} no longer restates the field set — re-derive the known sites'
    for site, documented_sets in sites.items():
        for documented in documented_sets:
            assert documented == emitted, f'{site} documents {sorted(documented)}, the detector emits {sorted(emitted)}'


def test_empty_comment_list_yields_empty_list(monkeypatch):
    _wire(monkeypatch, post_comments=[])

    result = github_ops.cmd_pr_wait_for_comments(_wait_comments_args())

    assert result['rate_limited_bots'] == []


def test_newer_review_supersedes_that_bots_older_notice_only(monkeypatch):
    # Selection is the comment written last PER BOT, not globally. CodeRabbit's older
    # notice is superseded by its own newer genuine review, while Sourcery — whose
    # last-written comment is still a notice — remains detected. A global pick of
    # the last comment would have hidden Sourcery behind CodeRabbit's recovery.
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


def test_an_older_comment_edited_into_a_refusal_after_a_newer_one_reports_the_bot(monkeypatch):
    # The bot posted a summary first and a genuine review after it, then rewrote the
    # SUMMARY into a refusal. The refusal is the older-created comment, so sampling
    # by ``created_at`` reads the review and reports nothing.
    summary_turned_refusal = dict(
        _CODERABBIT_REVIEW_LIMIT_REACHED,
        created_at='2026-01-01T00:00:00Z',
        updated_at='2026-01-03T00:00:00Z',
    )
    newer_review = dict(
        _CODERABBIT_GENUINE_REVIEW,
        created_at='2026-01-02T00:00:00Z',
        updated_at='2026-01-02T00:00:00Z',
    )
    _wire(monkeypatch, post_comments=[summary_turned_refusal, newer_review])

    result = github_ops.cmd_pr_wait_for_comments(_wait_comments_args())

    [record] = result['rate_limited_bots']
    assert record['bot_kind'] == 'coderabbit'
    assert record['body'] == _CODERABBIT_REVIEW_LIMIT_REACHED['body']
    # The instant reported is the edit, not the creation.
    assert record['written_at'] == '2026-01-03T00:00:00Z'


def test_the_same_two_comments_without_the_edit_report_no_bot(monkeypatch):
    # MATCHED CONTROL for the case above: the same bodies and creation times, with
    # the older comment never edited. The review is then the comment written last,
    # so the bot is not reported — the edit alone is what moved the verdict.
    unedited_older_refusal = dict(
        _CODERABBIT_REVIEW_LIMIT_REACHED,
        created_at='2026-01-01T00:00:00Z',
        updated_at='2026-01-01T00:00:00Z',
    )
    newer_review = dict(
        _CODERABBIT_GENUINE_REVIEW,
        created_at='2026-01-02T00:00:00Z',
        updated_at='2026-01-02T00:00:00Z',
    )
    _wire(monkeypatch, post_comments=[unedited_older_refusal, newer_review])

    result = github_ops.cmd_pr_wait_for_comments(_wait_comments_args())

    assert result['rate_limited_bots'] == []


_TWELVE_MINUTE_NOTICE_BODY = (
    '> [!WARNING] > ## Rate limit exceeded > '
    '@octocat has exceeded the limit for the number of commits or files '
    'that can be reviewed per hour. Please wait 12 minutes '
    'before requesting another review.'
)
_NOTICE_UPDATED_AT = '2026-01-02T12:00:00Z'


def _twelve_minute_notice(**overrides):
    """A CodeRabbit notice stating a 12-minute window, last written at ``_NOTICE_UPDATED_AT``."""
    notice = {
        'author': 'coderabbitai[bot]',
        'body': _TWELVE_MINUTE_NOTICE_BODY,
        'created_at': '2026-01-02T10:00:00Z',
        'updated_at': _NOTICE_UPDATED_AT,
    }
    notice.update(overrides)
    return notice


def test_a_notice_stating_twelve_minutes_read_two_hours_after_its_last_write_is_stale():
    # The notice states a 12-minute window and was last written at 12:00. Read at
    # 14:00, that window closed 108 minutes ago: there is nothing left to wait for.
    read_at = datetime(2026, 1, 2, 14, 0, 0, tzinfo=UTC)

    [record] = _github_pr._detect_rate_limited_bots([_twelve_minute_notice()], now=read_at)

    assert record['eta'] == '12 minutes'
    assert record['eta_seconds'] == 720
    assert record['written_at'] == _NOTICE_UPDATED_AT
    assert record['stale'] is True


def test_the_same_notice_read_inside_its_window_is_not_stale():
    # MATCHED CONTROL: the same notice, read five minutes after its last write. Its
    # window is still open, so the record must not be called stale — a detector
    # that marked every notice with a reset time stale would fail here.
    read_at = datetime(2026, 1, 2, 12, 5, 0, tzinfo=UTC)

    [record] = _github_pr._detect_rate_limited_bots([_twelve_minute_notice()], now=read_at)

    assert record['eta_seconds'] == 720
    assert record['stale'] is False


def test_the_window_is_over_at_the_instant_it_ends():
    # The boundary: written at 12:00 with a 720-second window, read at 12:12:00
    # exactly. The stated time has fully passed, so the record is stale; one second
    # earlier it is not.
    at_the_end = datetime(2026, 1, 2, 12, 12, 0, tzinfo=UTC)
    one_second_before = datetime(2026, 1, 2, 12, 11, 59, tzinfo=UTC)

    [ended] = _github_pr._detect_rate_limited_bots([_twelve_minute_notice()], now=at_the_end)
    [open_still] = _github_pr._detect_rate_limited_bots([_twelve_minute_notice()], now=one_second_before)

    assert ended['stale'] is True
    assert open_still['stale'] is False


def test_staleness_counts_from_the_last_write_not_from_the_creation():
    # Created at 10:00 and rewritten at 12:00. Read at 12:05 the comment is more
    # than two hours old by creation, but the text stating the window is five
    # minutes old, and that is the window that counts.
    read_at = datetime(2026, 1, 2, 12, 5, 0, tzinfo=UTC)
    notice = _twelve_minute_notice(created_at='2026-01-02T10:00:00Z', updated_at=_NOTICE_UPDATED_AT)

    [record] = _github_pr._detect_rate_limited_bots([notice], now=read_at)

    assert record['written_at'] == _NOTICE_UPDATED_AT
    assert record['stale'] is False


def test_a_notice_stating_no_reset_time_is_never_stale():
    # No window was stated, so there is none to have elapsed, however old the
    # notice is. Stale is asserted only on a figure that was read.
    read_at = datetime(2026, 6, 1, 0, 0, 0, tzinfo=UTC)

    [record] = _github_pr._detect_rate_limited_bots([_CODERABBIT_REVIEW_LIMIT_REACHED], now=read_at)

    assert record['eta_extracted'] is False
    assert record['written_at'] == _CODERABBIT_REVIEW_LIMIT_REACHED['created_at']
    assert record['stale'] is False


def test_a_notice_with_no_readable_write_instant_is_not_stale():
    # Neither stamp parses, so when the notice was written is unknown. The record
    # says so with an empty ``written_at`` and does not call the notice stale,
    # although it states a reset time.
    read_at = datetime(2026, 6, 1, 0, 0, 0, tzinfo=UTC)
    notice = _twelve_minute_notice(created_at='not-a-timestamp', updated_at='')

    [record] = _github_pr._detect_rate_limited_bots([notice], now=read_at)

    assert record['eta_seconds'] == 720
    assert record['written_at'] == ''
    assert record['stale'] is False


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

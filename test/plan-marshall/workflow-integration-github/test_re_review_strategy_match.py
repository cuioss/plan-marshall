# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for github_re_review.py — the bot_kind-keyed re-review strategy registry.

Covers the three concerns of the post-merge re-review registry:

    1. Strategy resolution — each bot_kind key resolves to the correct strategy
       object; an unknown key resolves to None.
    2. Trigger posting — ``request_fresh_review`` posts an explicit trigger
       comment per strategy and returns the comment-post time:
         coderabbit: posts ``@coderabbitai review``.
         sourcery:   posts ``@sourcery-ai review``.
         cuioss-review-bot:   posts ``/review``.
    3. Two-signal completion matching — ``await_fresh_review`` is satisfied by
       EITHER ``_match_review`` (a review whose reviewed-commit evidence REFERENCES
       the pushed HEAD — recognised as a bare token or embedded in a commit URL, and
       compared for EQUALITY either way, so a differing commit still fails — whose
       ``submitted_at`` post-dates the trigger time, AND whose
       body is not a refusal notice; reported with ``head_sha_verified: true``)
       OR ``_match_bot_comment`` (an issue comment from the awaited bot
       post-dating the trigger and likewise not a refusal notice). ``head_sha_verified``
       is decided on BOTH paths by that SAME ``_references_head_sha`` predicate, run
       over whichever field carries the reviewed-commit claim — the review's
       ``commit_sha``, or the comment's BODY. It is NOT "true only on the review
       path": that shortcut manufactured a decline for every bot whose sole declared
       publish shape is an issue comment naming its reviewed commit as a permalink.
       Where SEVERAL of the bot's comments are eligible, the one whose body names the
       pushed HEAD is SELECTED, so list order cannot manufacture a decline either.
       BOTH paths run the same refusal-recognition
       STACK as the producer — the arms are named once in
       ``_github_pr.REFUSAL_LAYERS`` and the list is open — so a bot that answers
       the trigger by declining to review is never a completed review, however
       weakly the decline was recognized. The review signal wins when both are
       present. Fail-closed on every missing or unparseable input.
    4. Refusal RECORDING — a rejected refusal is not a bare ``continue``. Both
       discriminators append every refusal they skip to an accumulator, and the
       envelope surfaces ``refusal_detected`` / ``refusal_class`` /
       ``refusal_eta`` / ``refusals[]`` so a caller can distinguish "the bot
       refused, and here is the recovery this arms" from "the bot never
       responded". A refusal still does not count as a completed review.
    5. The refusal RE-TRIGGER GUARD at the trigger chokepoint — there is exactly
       ONE ``_github.post_pr_comment`` call site in the module, and
       ``request_fresh_review`` consults the rate window before reaching it. The
       load-bearing assertion for every guard case is that ``post_pr_comment``
       was NOT CALLED: the guard exists so that no comment reaches the PR, and a
       test that only inspects the returned envelope passes just as well on an
       implementation that posts first and computes the status afterwards.

Plus the ``cmd_re_review`` CLI handler that wires request → await together.

Tests never shell out to the real ``gh`` CLI: every ``_github`` helper the
registry calls (``post_pr_comment``, ``fetch_pr_reviews_with_commits``,
``fetch_pr_comments_data``) is monkeypatched — the last one by the autouse
``_no_provider_comments`` guard below, so no test can silently reach the network
through the comment matcher — and ``time.sleep`` inside ``poll_until`` is
neutralised so the timeout branch runs in constant time. Module import resolves
via the root conftest's marketplace PYTHONPATH setup (``import
github_re_review``).

Tests never reach the real lock store either. ``request_fresh_review`` consults
``read_rate_window``, which reads the machine-global main-anchored
``merge-queue.json``; the autouse ``_neutralize_rate_window`` fixture below holds
that seam at the NO-STORED-RECORD observation for every test in this module, so
no test's verdict is a function of what some other plan happened to claim on this
machine. The fixture is default-on and structural: a test added later inherits it
without remembering anything, and a test that needs the other side of the
predicate injects its own ``window_reader`` rather than depending on the store.

The matched pair proving that fixture (neutralized-posts vs unneutralized-refuses
over the same claimed window) lives in ``test_re_review_strategy_await.py``;
this module relies on the same autouse fixture without re-proving it.

Tests never reach the provider's check-runs either. A poll that would end on a
comment naming no commit consults ``read_bot_in_progress``, which reads the awaited
bot's completion check-run through ``gh``. The autouse
``_neutralize_in_progress_read`` fixture below holds that seam at NOT OBSERVED
RUNNING for every test here; a test that needs the other side injects its own
``in_progress_reader``. ``test_the_neutralized_in_progress_read_leaves_the_answer_matched``
and ``test_the_unneutralized_in_progress_read_withholds_the_same_answer`` are the
matched pair standing guard over it — they differ only in whether the fixture is
engaged, so deleting either arm voids the other's evidence.
"""

import argparse
import sys
import time
import types

import _github_pr
import bot_registry
import ci_base
import github_re_review
import pytest
from _github_pr_fixtures import (
    ACKNOWLEDGMENT_BOT_KIND,
    ACKNOWLEDGMENT_BOT_LOGIN,
    CODERABBIT_ACKNOWLEDGMENT_COUNT,
    CODERABBIT_ACKNOWLEDGMENTS,
    CODERABBIT_GENUINE_SHORT_REVIEW_COMMENT,
    HUMAN_COMMENT_QUOTING_AN_ACKNOWLEDGMENT,
)

_LIVE_IN_PROGRESS_READER = github_re_review.read_bot_in_progress
_ACKNOWLEDGMENT_PARAMS = [pytest.param(body, id=case_id) for case_id, body, _provenance in CODERABBIT_ACKNOWLEDGMENTS]

_NO_RECORD_WINDOW = {'status': 'free', 'expired': True, 'holder': '', 'seconds_remaining': 0.0}
_OPEN_WINDOW = {
    'status': 'claimed',
    'expired': False,
    'holder': 'a-concurrently-finalizing-plan',
    'seconds_remaining': 1800.0,
}
_EXPIRED_WINDOW = {
    'status': 'claimed',
    'expired': True,
    'holder': 'a-concurrently-finalizing-plan',
    'seconds_remaining': 0.0,
}
_LIVE_WINDOW_READER = github_re_review.read_rate_window


def _window_reader(observation):
    """Build a ``(plan_id, bot_kind, pr_number) -> dict`` reader for ``observation``.

    The injected seam ``request_fresh_review`` documents, so a test drives both
    sides of the guard predicate without a real lock store.
    """

    def _read(_plan_id, _bot_kind, _pr_number):
        return dict(observation)

    return _read


@pytest.fixture(autouse=True)
def _neutralize_rate_window(monkeypatch):
    """Hold the trigger guard's window read at NO STORED RECORD for every test here.

    ``request_fresh_review`` consults ``read_rate_window``, which reads the
    machine-global main-anchored lock store. Left alone, every call site in this
    module that passes neither ``plan_id`` nor ``window_reader`` would reach that
    store: the verdict stays correct today (no record permits) but it is a
    function of ambient machine state, so a concurrently-finalizing plan holding
    a claim on the same bot would flip tests that have nothing to do with the
    guard.

    Default-on and inherited by construction: a test written later is hermetic
    without its author remembering an incantation. A test that needs the refusing
    side of the predicate injects its own ``window_reader``; the matched pair
    named in the module docstring is what keeps this fixture honest.
    """
    monkeypatch.setattr(github_re_review, 'read_rate_window', _window_reader(_NO_RECORD_WINDOW))


@pytest.fixture(autouse=True)
def _neutralize_in_progress_read(monkeypatch):
    """Hold the completion read at NOT OBSERVED RUNNING for every test here.

    ``await_fresh_review`` consults ``read_bot_in_progress`` whenever a poll would end
    on a comment that names no commit, and that function reads the awaited bot's
    check-run through ``gh``. Left alone, every such case in this module would shell
    out, and its verdict would depend on whether some real PR's check happened to be
    running.

    Default-on and inherited by construction. A test that needs the withholding side
    injects its own ``in_progress_reader``; the matched pair named in the module
    docstring is what keeps this fixture honest.
    """
    monkeypatch.setattr(github_re_review, 'read_bot_in_progress', lambda _pr_number, _bot_kind: False)


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


def _review(commit_sha, submitted_at, *, user='coderabbit[bot]', state='COMMENTED', body=''):
    """Build a review row in the shape fetch_pr_reviews_with_commits returns.

    ``body`` mirrors the widened projection: a review row now carries its body so
    the completion discriminator can tell a genuine review from a refusal notice
    submitted as a review object. It defaults to empty, which no refusal layer
    matches, so a fixture that does not care about the body behaves as before.
    """
    return {
        'user': user,
        'state': state,
        'submitted_at': submitted_at,
        'commit_sha': commit_sha,
        'body': body,
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


_GUARD_SWEEP_POPULATION: list[str] = bot_registry.bot_kinds()
_GUARD_SWEEP_POPULATION_SIZE = len(_GUARD_SWEEP_POPULATION)
_GUARD_PR_NUMBER = 42
_GUARD_PUSH_TIME = '2026-01-01T00:00:00Z'


def _parse(value):
    return github_re_review._parse_iso(value)


def _match_review(reviews, head_sha, trigger_dt, bot_kind, refusals=None):
    """Call ``_match_review`` with a throwaway refusal accumulator.

    Both discriminators take a ``refusals`` list they APPEND every skipped refusal
    to (the record that arms recovery instead of letting the refusal vanish into a
    bare timeout). Tests that do not assert on the accumulator pass a throwaway;
    tests that DO assert on it pass their own list.
    """
    return github_re_review._ReReviewStrategy._match_review(
        reviews, head_sha, trigger_dt, bot_kind, [] if refusals is None else refusals
    )


def _match_bot_comment(comments, head_sha, bot_kind, trigger_dt, refusals=None, acknowledgments=None):
    """Call ``_match_bot_comment`` with a throwaway refusal accumulator.

    ``head_sha`` sits where :meth:`_match_review`'s does, because the comment arm
    now reads it too: among the eligible comments it prefers one whose body names
    that SHA. ``acknowledgments`` is passed through untouched, so ``None`` exercises
    the caller that supplies no accumulator.
    """
    return github_re_review._ReReviewStrategy._match_bot_comment(
        comments, head_sha, bot_kind, trigger_dt, [] if refusals is None else refusals, acknowledgments
    )


_PR_AGENT_LOGIN = 'cuioss-review-bot'
_TRIGGER = '2026-01-01T00:02:00Z'


def _await_with_comments(
    monkeypatch,
    comments,
    *,
    reviews=None,
    bot_kind='cuioss-review-bot',
    head_sha='headsha',
    in_progress_reader=None,
):
    """Run ``await_fresh_review`` over a fixed comment (and review) set.

    ``head_sha`` is parametrized for the reviewed-commit-reference cases below, which
    need a real 40-hex SHA to exercise the URL-embedded shape. It defaults to the
    ``'headsha'`` token every other case uses, so those are unaffected.

    ``in_progress_reader`` is forwarded only when a test supplies one. Left unset the
    call takes the default seam — which the autouse fixture neutralises — so the
    cases that do not care about the completion read exercise the production default.
    """
    _noop_sleep(monkeypatch)
    monkeypatch.setattr(
        github_re_review._github,
        'fetch_pr_reviews_with_commits',
        lambda pr_number: {'status': 'success', 'reviews': list(reviews or [])},
    )
    _patch_comments(monkeypatch, comments)
    strategy = github_re_review.resolve_strategy(bot_kind)
    extra = {} if in_progress_reader is None else {'in_progress_reader': in_progress_reader}
    return strategy.await_fresh_review(42, head_sha, _TRIGGER, bot_kind=bot_kind, timeout=1, interval=0, **extra)


def _recording_reader(answer, calls):
    """Build an ``in_progress_reader`` that records each consult and returns ``answer``."""

    def _read(pr_number, bot_kind):
        calls.append((pr_number, bot_kind))
        return answer

    return _read


def _fake_completion_module(monkeypatch, result, calls=None, *, raises=None):
    """Stand a fake ``github_pr`` in for the completion read ``read_bot_in_progress`` makes.

    ``read_bot_in_progress`` imports ``github_pr`` at call time, so the entry in
    ``sys.modules`` is what it resolves. Replacing that entry reaches the read at its
    own boundary without this module importing ``github_pr`` itself.
    """

    def _read_bot_completion(pr_number, bot_kind, check_name):
        if calls is not None:
            calls.append((pr_number, bot_kind, check_name))
        if raises is not None:
            raise raises
        return result

    fake = types.ModuleType('github_pr')
    setattr(fake, '_read_bot_completion', _read_bot_completion)  # noqa: B010 - ModuleType declares no such attribute
    monkeypatch.setitem(sys.modules, 'github_pr', fake)


def _acknowledgment_comment(body, *, created_at='2026-01-01T00:05:00Z', updated_at=''):
    """An acknowledgment reply from the acknowledging bot, post-dating ``_TRIGGER`` by default."""
    return _comment(ACKNOWLEDGMENT_BOT_LOGIN, created_at=created_at, updated_at=updated_at, body=body)


_HEAD_SHA = 'a1b2c3d4e5f60718293a4b5c6d7e8f9012345678'
_OTHER_SHA = '0f1e2d3c4b5a69788796a5b4c3d2e1f098765432'
_HEAD_SHA_URL = f'https://github.com/cuioss/plan-marshall/commit/{_HEAD_SHA}'
_OTHER_SHA_URL = f'https://github.com/cuioss/plan-marshall/commit/{_OTHER_SHA}'
_OBSERVED_REVIEW_BOT_SHA = '4d6738e2d96150706cda6b682109336c5c0c383b'


def _republished_comment(reference, *, created_at='2026-01-01T00:00:00Z', updated_at='2026-01-01T00:05:00Z'):
    """A CodeRabbit in-place-republished summary naming ``reference`` in its body.

    The timestamps are overridable so the selection cases can build TWO eligible
    comments from this one builder — keeping the only difference between them the
    reference their bodies carry, plus the order they arrive in.
    """
    body = f'Review updated until commit {reference}. No actionable comments were generated.'
    return _comment(_CODERABBIT_LOGIN, created_at=created_at, updated_at=updated_at, body=body)


_VERIFYING_REFERENCE = f'[{_HEAD_SHA[:7]}]({_HEAD_SHA_URL})'
_NON_VERIFYING_REFERENCE = 'the latest push'
_SOURCERY_LOGIN = 'sourcery-ai'
_SOURCERY_REFUSAL = (
    'Sourcery was unable to review this pull request because '
    'your pull request is larger than the review limit of 150000 characters. '
    'Reduce the size of the pull request and request another review.'
)
_UNCAPTURED_SHAPED_REFUSAL = (
    '> [!WARNING] > ## Usage limit reached > '
    'This reviewer has reached its monthly usage limit. '
    'Reviews will resume after the limit resets.'
)
_GENUINE_REVIEW_BODY = (
    'Reviewed the new HEAD. One issue: the retry loop can spin forever when the '
    'backoff cap is zero — guard the cap before entering the loop.'
)
_CODERABBIT_LOGIN = 'coderabbitai'
_CODERABBIT_COMMAND_REPLY_REFUSAL = (
    '<!-- This is an auto-generated reply by CodeRabbit --> '
    '<!-- CodeRabbit review command invocation: v2:abc --> '
    '<details> <summary>(warning) Action not completed</summary> '
    'Review rate limited. '
    '> Note: CodeRabbit is an incremental review system and does not re-review '
    'already reviewed commits. This command is applicable only when automatic '
    'reviews are paused. </details>'
)
_CODERABBIT_GENUINE_COMMENT = (
    'Actionable comments posted: 1. The retry loop can spin forever when the backoff '
    'cap is zero — guard the cap before entering the loop.'
)
_CODERABBIT_REFUSAL_WITH_ETA = (
    '> [!WARNING] > ## Review limit reached > Please wait 12 minutes and 30 seconds before requesting another review.'
)


def _arm_enumerative(monkeypatch, max_chars: int = 200) -> None:
    """Give the enumerative arm a threshold, patched where the predicate READS it.

    ``github_re_review`` binds the predicate by name, so the threshold is resolved
    in the DEFINING module's namespace at call time. Patching the function's own
    ``__globals__`` targets that namespace regardless of which ``_github_pr`` object
    this test module happens to hold.
    """
    monkeypatch.setitem(
        github_re_review._is_unrecognised_refusal.__globals__,
        'UNRECOGNISED_REFUSAL_MAX_CHARS',
        max_chars,
    )


_UNRECOGNISED_REFUSAL = 'Not reviewing this one.'


def test_no_hardcoded_trigger_constants_remain():
    """The per-bot trigger constants were collapsed into registry-loaded data."""
    assert not hasattr(github_re_review, 'CODERABBIT_TRIGGER_COMMENT')
    assert not hasattr(github_re_review, 'SOURCERY_TRIGGER_COMMENT')
    assert not hasattr(github_re_review, 'PR_AGENT_TRIGGER_COMMENT')


def test_strategies_are_distinct_objects():
    """coderabbit and cuioss-review-bot must not collapse onto the same strategy object."""
    coderabbit = github_re_review.resolve_strategy('coderabbit')
    pr_agent = github_re_review.resolve_strategy('cuioss-review-bot')

    assert coderabbit is not pr_agent


def test_match_review_matches_when_sha_and_time_satisfy():
    """A review matching HEAD and post-dating the trigger is returned."""
    reviews = [_review('headsha', '2026-01-01T00:05:00Z')]
    trigger_dt = _parse('2026-01-01T00:00:00Z')

    matched = _match_review(reviews, 'headsha', trigger_dt, 'coderabbit')

    assert matched is not None
    assert matched['commit_sha'] == 'headsha'


def test_match_review_rejects_wrong_commit_sha():
    """A review on a stale commit never matches even if it post-dates trigger."""
    reviews = [_review('oldsha', '2026-01-01T00:05:00Z')]
    trigger_dt = _parse('2026-01-01T00:00:00Z')

    assert _match_review(reviews, 'headsha', trigger_dt, 'coderabbit') is None


def test_match_review_rejects_review_at_or_before_trigger_time():
    """A review submitted before the trigger (a pre-existing review) never matches."""
    reviews = [_review('headsha', '2026-01-01T00:00:00Z')]
    trigger_dt = _parse('2026-01-01T00:05:00Z')

    assert _match_review(reviews, 'headsha', trigger_dt, 'coderabbit') is None


def test_match_review_fail_closed_on_unparseable_submitted_at():
    """A review whose submitted_at cannot be parsed never matches (fail-closed)."""
    reviews = [_review('headsha', 'not-a-timestamp')]
    trigger_dt = _parse('2026-01-01T00:00:00Z')

    assert _match_review(reviews, 'headsha', trigger_dt, 'coderabbit') is None


def test_match_review_returns_first_eligible_among_many():
    """The first SHA-and-time eligible review is returned."""
    reviews = [
        _review('oldsha', '2026-01-01T00:09:00Z'),
        _review('headsha', '2026-01-01T00:06:00Z'),
        _review('headsha', '2026-01-01T00:07:00Z'),
    ]
    trigger_dt = _parse('2026-01-01T00:00:00Z')

    matched = _match_review(reviews, 'headsha', trigger_dt, 'coderabbit')

    assert matched is not None
    assert matched['submitted_at'] == '2026-01-01T00:06:00Z'


def test_await_matches_bot_issue_comment_when_no_review_exists(monkeypatch):
    """A bot-authored comment post-dating the trigger satisfies await with no review.

    This is the case that used to be a guaranteed timeout. The envelope must name
    the weaker signal: ``matched_signal: issue_comment``. ``head_sha_verified`` is
    ``false`` here because THIS comment's body names no commit — not because a
    comment structurally cannot; see the comment-path verification section below,
    where a body that does name the awaited commit verifies.
    """
    result = _await_with_comments(monkeypatch, [_comment(_PR_AGENT_LOGIN, created_at='2026-01-01T00:05:00Z')])

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
    result = _await_with_comments(monkeypatch, [_comment('coderabbitai', created_at='2026-01-01T00:05:00Z')])

    assert result['matched'] is False
    assert result['matched_signal'] == ''
    assert result['timed_out'] is True


def test_await_does_not_match_a_human_comment(monkeypatch):
    """A human comment post-dating the trigger does not satisfy await.

    An unresolvable author yields no ``bot_kind``, so it can never equal the
    awaited one — human PR chatter cannot be mistaken for a completed review.
    """
    result = _await_with_comments(monkeypatch, [_comment('alice', created_at='2026-01-01T00:05:00Z')])

    assert result['matched'] is False
    assert result['matched_signal'] == ''


def test_await_does_not_match_a_comment_predating_the_trigger(monkeypatch):
    """A pre-existing bot comment (older than the trigger) does not satisfy await."""
    result = _await_with_comments(monkeypatch, [_comment(_PR_AGENT_LOGIN, created_at='2026-01-01T00:00:00Z')])

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

    strategy = github_re_review.resolve_strategy('cuioss-review-bot')
    result = strategy.await_fresh_review(42, 'headsha', _TRIGGER, timeout=1, interval=0)

    assert result['matched'] is False
    assert result['matched_signal'] == ''


def test_match_bot_comment_fail_closed_on_unparseable_timestamps():
    """A comment whose only timestamps are unparseable never matches (fail-closed)."""
    trigger_dt = _parse(_TRIGGER)
    comments = [_comment(_PR_AGENT_LOGIN, created_at='not-a-timestamp', updated_at='')]

    assert _match_bot_comment(comments, 'headsha', 'cuioss-review-bot', trigger_dt) is None


def test_match_bot_comment_fail_closed_on_missing_trigger_time():
    """An unparseable trigger time yields no comment match (fail-closed)."""
    comments = [_comment(_PR_AGENT_LOGIN, created_at='2026-01-01T00:05:00Z')]

    assert _match_bot_comment(comments, 'headsha', 'cuioss-review-bot', None) is None


def test_match_review_verifies_a_sha_carried_only_inside_a_commit_url():
    """POSITIVE: the reviewed commit is recognised when its SHA sits inside a URL.

    The live merged-main defect, pinned directly: this review names the awaited HEAD
    and nothing else, and whole-field string equality did not see it.
    """
    reviews = [_review(_HEAD_SHA_URL, '2026-01-01T00:05:00Z')]
    trigger_dt = _parse('2026-01-01T00:00:00Z')

    matched = _match_review(reviews, _HEAD_SHA, trigger_dt, 'coderabbit')

    assert matched is not None
    assert matched['commit_sha'] == _HEAD_SHA_URL


def test_match_review_rejects_a_commit_url_naming_a_different_commit():
    """NEGATIVE control for the case above: a different commit still does not match.

    Same fixture builder, same URL shape, same timestamps — the ONLY difference is
    which commit the permalink names. Without this the positive above would pass just
    as happily against an extractor widened to match everything SHA-shaped, which
    would credit any review of any commit as a review of this HEAD.
    """
    reviews = [_review(_OTHER_SHA_URL, '2026-01-01T00:05:00Z')]
    trigger_dt = _parse('2026-01-01T00:00:00Z')

    assert _match_review(reviews, _HEAD_SHA, trigger_dt, 'coderabbit') is None


def test_match_review_rejects_an_abbreviated_reference_to_the_awaited_commit():
    """Equality, never prefix — the widening moved WHERE the SHA may sit, not WHICH.

    An abbreviation of the awaited SHA is SHA-shaped, extractable, and a leading run
    of the real value, so it is the sharpest available probe of the equality boundary.
    Admitting it would widen which commit counts, and would leave the negative control
    above unable to tell "found the awaited commit" from "matched something
    SHA-shaped".
    """
    abbreviated = f'https://github.com/cuioss/plan-marshall/commit/{_HEAD_SHA[:12]}'
    reviews = [_review(abbreviated, '2026-01-01T00:05:00Z')]
    trigger_dt = _parse('2026-01-01T00:00:00Z')

    assert _match_review(reviews, _HEAD_SHA, trigger_dt, 'coderabbit') is None


def test_await_still_matches_when_no_eligible_comment_names_the_awaited_head(monkeypatch):
    """MATCHED CONTROL — the preference reorders eligible comments, it does not filter them.

    Two eligible comments, neither naming a commit. Without this control the
    selection cases above would pass just as happily against a matcher that only
    ever returned a HEAD-verifying comment — which would convert the ordinary
    "the bot answered without naming a commit" case into a permanent timeout for
    every bot whose summary names no commit at all.
    """
    first = _republished_comment(_NON_VERIFYING_REFERENCE, updated_at='2026-01-01T00:05:00Z')
    second = _republished_comment(f'[{_OTHER_SHA[:7]}]({_OTHER_SHA_URL})', updated_at='2026-01-01T00:06:00Z')

    result = _await_with_comments(monkeypatch, [first, second], bot_kind='coderabbit', head_sha=_HEAD_SHA)

    assert result['matched'] is True
    assert result['matched_signal'] == 'issue_comment'
    assert result['head_sha_verified'] is False
    # The fallback is the FIRST eligible comment — the pre-existing behaviour, kept
    # intact for the case where the preference finds nothing to prefer.
    assert result['matched_comment']['body'] == first['body']


def test_await_still_matches_a_genuine_coderabbit_comment(monkeypatch):
    """⛔ NEGATIVE CONTROL: real CodeRabbit feedback still completes the await.

    Asserting only that the refusal is rejected would pass on a change that rejected
    EVERY CodeRabbit comment — which would convert a false green into a permanent false
    timeout and stall every re-review this bot is asked for.
    """
    result = _await_with_comments(
        monkeypatch,
        [
            _comment(
                _CODERABBIT_LOGIN,
                created_at='2026-01-01T00:05:00Z',
                body=_CODERABBIT_GENUINE_COMMENT,
            )
        ],
        bot_kind='coderabbit',
    )

    assert result['matched'] is True
    assert result['matched_signal'] == 'issue_comment'
    assert result['refusal_detected'] is False


def test_await_does_not_match_a_refusal_delivered_as_a_review(monkeypatch):
    """A refusal submitted as a REVIEW object is not a completed review.

    This is the observed case and the sharpest false-green: the refusal review
    satisfies both the commit_sha and submitted_at gates, so before the fix it
    matched and reported ``head_sha_verified: true`` — asserting HEAD coverage the
    bot had explicitly declined to provide. The correct outcome is a truthful
    timeout.
    """
    result = _await_with_comments(
        monkeypatch,
        [],
        reviews=[
            _review(
                'headsha',
                '2026-01-01T00:05:00Z',
                user='sourcery-ai[bot]',
                body=_SOURCERY_REFUSAL,
            )
        ],
        bot_kind='sourcery',
    )

    assert result['status'] == 'success'
    assert result['matched'] is False
    assert result['matched_signal'] == ''
    assert result['head_sha_verified'] is False
    assert result['timed_out'] is True


def test_await_does_not_match_a_refusal_delivered_as_a_comment(monkeypatch):
    """The same refusal delivered as an issue comment is likewise not a response."""
    result = _await_with_comments(
        monkeypatch,
        [_comment(_SOURCERY_LOGIN, created_at='2026-01-01T00:05:00Z', body=_SOURCERY_REFUSAL)],
        bot_kind='sourcery',
    )

    assert result['matched'] is False
    assert result['matched_signal'] == ''
    assert result['timed_out'] is True


def test_await_still_matches_a_genuine_review(monkeypatch):
    """Precision guard: a real review still completes the await on the strong signal."""
    result = _await_with_comments(
        monkeypatch,
        [],
        reviews=[
            _review(
                'headsha',
                '2026-01-01T00:05:00Z',
                user='sourcery-ai[bot]',
                body=_GENUINE_REVIEW_BODY,
            )
        ],
        bot_kind='sourcery',
    )

    assert result['matched'] is True
    assert result['matched_signal'] == 'review'
    assert result['head_sha_verified'] is True
    assert result['timed_out'] is False


def test_await_still_matches_a_genuine_comment(monkeypatch):
    """Precision guard: a real comment still completes the await on the weaker signal."""
    result = _await_with_comments(
        monkeypatch,
        [
            _comment(
                _SOURCERY_LOGIN,
                created_at='2026-01-01T00:05:00Z',
                body='Overall comments: consider extracting the retry helper.',
            )
        ],
        bot_kind='sourcery',
    )

    assert result['matched'] is True
    assert result['matched_signal'] == 'issue_comment'
    assert result['head_sha_verified'] is False


def test_refusal_surfaces_the_parsed_eta_when_the_registry_patterns_match(monkeypatch):
    """The bot's own stated reset time is surfaced, so the recovery sequence can
    size the window instead of guessing at it."""
    result = _await_with_comments(
        monkeypatch,
        [
            _comment(
                _CODERABBIT_LOGIN,
                created_at='2026-01-01T00:05:00Z',
                body=_CODERABBIT_REFUSAL_WITH_ETA,
            )
        ],
        bot_kind='coderabbit',
    )

    assert result['refusal_detected'] is True
    assert result['refusal_class'] == 'awaitable_window'
    assert result['refusal_eta'] == '12 minutes and 30 seconds'
    assert result['refusals'][0]['eta'] == '12 minutes and 30 seconds'


def test_matched_review_reports_no_refusal(monkeypatch):
    """Precision guard: a genuine review leaves the refusal fields empty."""
    result = _await_with_comments(
        monkeypatch,
        [],
        reviews=[
            _review(
                'headsha',
                '2026-01-01T00:05:00Z',
                user='sourcery-ai[bot]',
                body=_GENUINE_REVIEW_BODY,
            )
        ],
        bot_kind='sourcery',
    )

    assert result['matched'] is True
    assert result['refusal_detected'] is False
    assert result['refusals'] == []


def test_an_unrecognised_refusal_on_the_review_path_is_recorded_and_not_matched(monkeypatch):
    """⛔ The false-green this deliverable closes, pinned directly.

    The refusal satisfies the ``commit_sha`` and ``submitted_at`` gates, so before
    the enumerative arm existed ``_match_review`` admitted it and the envelope
    asserted the new HEAD had been reviewed. ``head_sha_verified`` is asserted
    EXPLICITLY rather than inferred from ``matched``: that field is the actual claim
    a consumer reads, and a regression could restore it while ``matched`` stayed
    false.
    """
    _arm_enumerative(monkeypatch)
    result = _await_with_comments(
        monkeypatch,
        [],
        reviews=[
            _review(
                'headsha',
                '2026-01-01T00:05:00Z',
                user='sourcery-ai[bot]',
                body=_UNRECOGNISED_REFUSAL,
            )
        ],
        bot_kind='sourcery',
    )

    # Not a completed review...
    assert result['matched'] is False
    assert result['matched_signal'] == ''
    # ...and specifically NOT a verified HEAD. This is the assertion that fails
    # against the pre-fix code.
    assert result['head_sha_verified'] is False
    # ...but it IS recorded, under the third arm, so it arms a recovery instead of
    # vanishing into an indistinguishable timeout.
    assert result['refusal_detected'] is True
    assert len(result['refusals']) == 1
    assert result['refusals'][0]['layer'] == _github_pr.REFUSAL_LAYER_ENUMERATIVE
    assert result['refusals'][0]['source'] == 'review'


def test_an_unrecognised_refusal_on_the_comment_path_is_recorded_and_not_matched(monkeypatch):
    """The same body arriving as an issue comment is likewise recorded, not matched."""
    _arm_enumerative(monkeypatch)
    result = _await_with_comments(
        monkeypatch,
        [
            _comment(
                _SOURCERY_LOGIN,
                created_at='2026-01-01T00:05:00Z',
                body=_UNRECOGNISED_REFUSAL,
            )
        ],
        bot_kind='sourcery',
    )

    assert result['matched'] is False
    assert result['head_sha_verified'] is False
    assert result['refusal_detected'] is True
    assert result['refusals'][0]['layer'] == _github_pr.REFUSAL_LAYER_ENUMERATIVE
    assert result['refusals'][0]['source'] == 'issue_comment'


def test_a_genuine_short_review_with_a_code_anchor_still_matches(monkeypatch):
    """Matched negative control: the arm does not swallow a real short review.

    Same bot, same armed threshold, same length class as the positive case — the
    only difference is the code anchor a genuine review carries. Without this
    control the positive cases above would pass just as happily against an arm that
    classified EVERY short body as a refusal, which is the failure direction that
    blocks a merge.
    """
    _arm_enumerative(monkeypatch)
    result = _await_with_comments(
        monkeypatch,
        [],
        reviews=[
            _review(
                'headsha',
                '2026-01-01T00:05:00Z',
                user='sourcery-ai[bot]',
                body='Guard the bound at `src/idx.py:12`.',
            )
        ],
        bot_kind='sourcery',
    )

    assert result['matched'] is True
    assert result['matched_signal'] == 'review'
    assert result['head_sha_verified'] is True
    assert result['refusal_detected'] is False
    assert result['refusals'] == []


def test_match_review_without_bot_kind_applies_only_the_structural_layer():
    """With no ``bot_kind`` only the structural arm can fire — the review still matches.

    Pins the bot-scoping of the registry arm: Sourcery's refusal marker must not
    leak into a review being matched for an unknown/unregistered bot. The
    enumerative arm is likewise unable to fire without a resolved bot, so the
    structural test is the only one that applies here — and it does not recognize
    this phrasing.
    """
    trigger_dt = _parse('2026-01-01T00:00:00Z')

    genuine = [_review('headsha', '2026-01-01T00:05:00Z', body=_GENUINE_REVIEW_BODY)]
    assert _match_review(genuine, 'headsha', trigger_dt, None) is not None

    # The Sourcery marker is bot-scoped data: with bot_kind None it cannot fire,
    # and the structural layer does not match this phrasing, so the review matches.
    marker_bearing = [_review('headsha', '2026-01-01T00:05:00Z', body=_SOURCERY_REFUSAL)]
    assert _match_review(marker_bearing, 'headsha', trigger_dt, None) is not None
    # ...and the SAME body IS rejected once the awaited bot is known.
    assert _match_review(marker_bearing, 'headsha', trigger_dt, 'sourcery') is None


# =============================================================================
# An acknowledgment is not an answer
# =============================================================================


def test_the_acknowledgment_population_is_the_declared_pair():
    """Non-vacuity: the acknowledgment cases below run over both declared wordings."""
    assert CODERABBIT_ACKNOWLEDGMENT_COUNT == len(_ACKNOWLEDGMENT_PARAMS) == 2
    assert bot_registry.acknowledgment_patterns(ACKNOWLEDGMENT_BOT_KIND), (
        'the acknowledging bot declares no acknowledgment_patterns — every case below '
        'would assert over a class nothing can be a member of'
    )


@pytest.mark.parametrize('body', _ACKNOWLEDGMENT_PARAMS)
def test_an_acknowledgment_after_the_trigger_is_neither_a_match_nor_a_refusal(monkeypatch, body):
    """⛔ The false decline this deliverable closes, pinned directly.

    The reply is authored by the awaited bot and post-dates the trigger, so it
    satisfied every eligibility gate while naming no commit: the await ended on it as
    ``matched: true`` / ``head_sha_verified: false``. It must now end as a truthful
    timeout that still says the bot received the request.
    """
    result = _await_with_comments(monkeypatch, [_acknowledgment_comment(body)], bot_kind=ACKNOWLEDGMENT_BOT_KIND)

    assert result['status'] == 'success'
    assert result['matched'] is False
    assert result['matched_signal'] == ''
    assert result['matched_comment'] == {}
    assert result['head_sha_verified'] is False
    assert result['timed_out'] is True
    # Not a refusal either: nothing arms a recovery for a bot that merely confirmed.
    assert result['refusal_detected'] is False
    assert result['refusals'] == []
    # ...but it IS reported, so this timeout is distinguishable from silence.
    assert result['acknowledged'] is True
    assert len(result['acknowledgments']) == 1
    record = result['acknowledgments'][0]
    assert record['source'] == 'issue_comment'
    assert record['bot_kind'] == ACKNOWLEDGMENT_BOT_KIND
    assert 'Review' in record['body']


@pytest.mark.parametrize('body', _ACKNOWLEDGMENT_PARAMS)
def test_an_acknowledgment_is_not_read_as_an_unrecognised_refusal(monkeypatch, body):
    """The class displaces the enumerative arm, which reads a short anchor-less body as a refusal.

    Armed exactly as in the control below, so the only difference between the two is
    whether the body is a declared acknowledgment.
    """
    _arm_enumerative(monkeypatch)

    result = _await_with_comments(monkeypatch, [_acknowledgment_comment(body)], bot_kind=ACKNOWLEDGMENT_BOT_KIND)

    assert result['matched'] is False
    assert result['refusal_detected'] is False
    assert result['refusals'] == []
    assert result['acknowledged'] is True


def test_the_enumerative_arm_still_records_a_short_body_that_is_no_acknowledgment(monkeypatch):
    """MATCHED CONTROL for the case above: the arm is live for the same bot.

    Without it the case above would pass just as happily with the enumerative arm
    disabled for this bot altogether.
    """
    _arm_enumerative(monkeypatch)

    result = _await_with_comments(
        monkeypatch,
        [_acknowledgment_comment(_UNRECOGNISED_REFUSAL)],
        bot_kind=ACKNOWLEDGMENT_BOT_KIND,
    )

    assert result['matched'] is False
    assert result['refusal_detected'] is True
    assert result['refusals'][0]['layer'] == _github_pr.REFUSAL_LAYER_ENUMERATIVE
    assert result['acknowledged'] is False
    assert result['acknowledgments'] == []


def test_a_genuine_short_comment_from_the_acknowledging_bot_is_still_matched(monkeypatch):
    """⛔ NEGATIVE CONTROL: a short review comment from the same bot completes the await.

    Same bot, same timestamps, same length class as an acknowledgment. Asserting only
    that acknowledgments are skipped would pass on a change that skipped every short
    comment from this bot, turning the false decline into a permanent false timeout.
    """
    result = _await_with_comments(
        monkeypatch,
        [_acknowledgment_comment(CODERABBIT_GENUINE_SHORT_REVIEW_COMMENT)],
        bot_kind=ACKNOWLEDGMENT_BOT_KIND,
    )

    assert result['matched'] is True
    assert result['matched_signal'] == 'issue_comment'
    assert result['matched_comment']['body'] == CODERABBIT_GENUINE_SHORT_REVIEW_COMMENT
    assert result['acknowledged'] is False
    assert result['acknowledgments'] == []
    assert result['refusal_detected'] is False


@pytest.mark.parametrize('body', _ACKNOWLEDGMENT_PARAMS)
def test_the_answer_beside_an_acknowledgment_is_the_match(monkeypatch, body):
    """The acknowledgment is skipped, not the poll: the answer posted after it matches.

    The acknowledgment is listed FIRST, so a matcher that returned the first eligible
    comment would return it.
    """
    answer = _acknowledgment_comment(CODERABBIT_GENUINE_SHORT_REVIEW_COMMENT, created_at='2026-01-01T00:06:00Z')

    result = _await_with_comments(
        monkeypatch,
        [_acknowledgment_comment(body), answer],
        bot_kind=ACKNOWLEDGMENT_BOT_KIND,
    )

    assert result['matched'] is True
    assert result['matched_comment']['body'] == CODERABBIT_GENUINE_SHORT_REVIEW_COMMENT
    assert result['acknowledged'] is True


@pytest.mark.parametrize('body', _ACKNOWLEDGMENT_PARAMS)
def test_an_acknowledgment_edited_after_the_trigger_is_recorded(monkeypatch, body):
    """The reply is edited in place, so it is dated by ``updated_at`` like any other comment."""
    edited = _acknowledgment_comment(body, created_at='2026-01-01T00:00:00Z', updated_at='2026-01-01T00:05:00Z')

    result = _await_with_comments(monkeypatch, [edited], bot_kind=ACKNOWLEDGMENT_BOT_KIND)

    assert result['matched'] is False
    assert result['acknowledged'] is True
    assert len(result['acknowledgments']) == 1


@pytest.mark.parametrize('body', _ACKNOWLEDGMENT_PARAMS)
def test_an_acknowledgment_predating_the_trigger_is_skipped_without_a_record(monkeypatch, body):
    """An older acknowledgment confirmed some earlier command, not this one."""
    stale = _acknowledgment_comment(body, created_at='2026-01-01T00:00:00Z')

    result = _await_with_comments(monkeypatch, [stale], bot_kind=ACKNOWLEDGMENT_BOT_KIND)

    assert result['matched'] is False
    assert result['acknowledged'] is False
    assert result['acknowledgments'] == []


def test_a_readable_refusal_outranks_an_acknowledgment_literal(monkeypatch):
    """A refusal the stack can READ stays a refusal even beside an acknowledgment wording."""
    body = f'{_CODERABBIT_COMMAND_REPLY_REFUSAL} Review triggered.'

    result = _await_with_comments(monkeypatch, [_acknowledgment_comment(body)], bot_kind=ACKNOWLEDGMENT_BOT_KIND)

    assert result['matched'] is False
    assert result['refusal_detected'] is True
    assert result['refusals'][0]['layer'] != _github_pr.REFUSAL_LAYER_ENUMERATIVE
    assert result['acknowledged'] is False


@pytest.mark.parametrize(
    ('created_at', 'updated_at', 'recorded'),
    [
        pytest.param('2026-01-01T00:05:00Z', '', True, id='written-after-the-trigger'),
        pytest.param('2026-01-01T00:00:00Z', '2026-01-01T00:05:00Z', True, id='edited-after-the-trigger'),
        pytest.param('2026-01-01T00:00:00Z', '', False, id='written-before-the-trigger'),
        pytest.param(_TRIGGER, '', False, id='written-at-the-trigger-instant'),
        pytest.param('2026-01-01T00:00:00Z', '2026-01-01T00:01:00Z', False, id='edited-before-the-trigger'),
        pytest.param('not-a-timestamp', '', False, id='no-readable-timestamp'),
    ],
)
def test_a_refusal_is_this_awaits_refusal_only_when_written_after_the_trigger(
    monkeypatch, created_at, updated_at, recorded
):
    """A refusal that answered some other request is not reported as this await's refusal.

    One body, one bot, one trigger — only the instant the comment was written
    differs, so the recorded and unrecorded rows are each other's control. An
    unrecorded refusal leaves a bare timeout: the bot said nothing to THIS trigger.
    """
    refusal = _comment(
        _CODERABBIT_LOGIN, created_at=created_at, updated_at=updated_at, body=_CODERABBIT_COMMAND_REPLY_REFUSAL
    )

    result = _await_with_comments(monkeypatch, [refusal], bot_kind='coderabbit')

    assert result['matched'] is False
    assert result['timed_out'] is True
    assert result['refusal_detected'] is recorded
    assert len(result['refusals']) == (1 if recorded else 0)
    assert result['refusal_class'] == (bot_registry.rate_limit_class('coderabbit') if recorded else '')


def test_an_unreadable_refusal_predating_the_trigger_is_skipped_without_a_record(monkeypatch):
    """The enumerative arm is gated on the same instant as the arms that read the body."""
    _arm_enumerative(monkeypatch)
    stale = _comment(_SOURCERY_LOGIN, created_at='2026-01-01T00:00:00Z', body=_UNRECOGNISED_REFUSAL)

    result = _await_with_comments(monkeypatch, [stale], bot_kind='sourcery')

    assert result['matched'] is False
    assert result['refusal_detected'] is False
    assert result['refusals'] == []


def test_an_older_refusal_does_not_hide_the_answer_written_after_the_trigger(monkeypatch):
    """The older refusal is skipped, not the poll: the later answer is the match."""
    stale = _comment(_CODERABBIT_LOGIN, created_at='2026-01-01T00:00:00Z', body=_CODERABBIT_COMMAND_REPLY_REFUSAL)
    answer = _comment(_CODERABBIT_LOGIN, created_at='2026-01-01T00:05:00Z', body=_CODERABBIT_GENUINE_COMMENT)

    result = _await_with_comments(monkeypatch, [stale, answer], bot_kind='coderabbit')

    assert result['matched'] is True
    assert result['matched_comment']['body'] == _CODERABBIT_GENUINE_COMMENT
    assert result['refusal_detected'] is False
    assert result['refusals'] == []


@pytest.mark.parametrize('body', _ACKNOWLEDGMENT_PARAMS)
def test_match_bot_comment_skips_an_acknowledgment_without_an_accumulator(body):
    """A caller passing no ``acknowledgments`` list still never receives the reply as the match."""
    trigger_dt = _parse(_TRIGGER)

    matched = _match_bot_comment([_acknowledgment_comment(body)], 'headsha', ACKNOWLEDGMENT_BOT_KIND, trigger_dt)

    assert matched is None


@pytest.mark.parametrize('body', _ACKNOWLEDGMENT_PARAMS)
def test_the_acknowledgment_class_is_scoped_to_the_bot_that_declared_it(body):
    """Only the declaring bot can acknowledge with its literal."""
    assert github_re_review.is_acknowledgment_comment(body, ACKNOWLEDGMENT_BOT_KIND) is True

    undeclared = [kind for kind in bot_registry.bot_kinds() if not bot_registry.acknowledgment_patterns(kind)]
    assert undeclared, 'every bot declares acknowledgment_patterns — the scoping sweep would be vacuous'
    for kind in undeclared:
        assert github_re_review.is_acknowledgment_comment(body, kind) is False
    assert github_re_review.is_acknowledgment_comment(body, None) is False


def test_a_human_quoting_an_acknowledgment_is_not_an_acknowledgment():
    """NEGATIVE control: an unresolvable author carries no ``bot_kind`` to scope the class to."""
    author_kind = github_re_review.bot_kind_for_author('alice')

    assert not author_kind
    assert github_re_review.is_acknowledgment_comment(HUMAN_COMMENT_QUOTING_AN_ACKNOWLEDGMENT, author_kind) is False


def test_the_acknowledgment_match_ignores_how_the_reply_is_wrapped():
    """Both sides are whitespace-collapsed, so a line break inside the statement still matches."""
    assert github_re_review.is_acknowledgment_comment('Review\n   finished.', ACKNOWLEDGMENT_BOT_KIND) is True
    assert (
        github_re_review.is_acknowledgment_comment('Review of the diff is finished.', ACKNOWLEDGMENT_BOT_KIND) is False
    )


def test_a_blank_registry_entry_never_makes_every_body_an_acknowledgment(monkeypatch):
    """A blank declared literal is dropped — the empty string is contained in every body."""
    monkeypatch.setattr(bot_registry, 'acknowledgment_patterns', lambda _kind: ['', '   '])

    assert github_re_review.is_acknowledgment_comment(CODERABBIT_GENUINE_SHORT_REVIEW_COMMENT, 'coderabbit') is False


def test_a_padded_registry_entry_is_normalised_before_it_is_compared(monkeypatch):
    """MATCHED CONTROL: a padded literal still recognises its own wording."""
    monkeypatch.setattr(bot_registry, 'acknowledgment_patterns', lambda _kind: ['  Review   triggered  ', ''])

    assert github_re_review.is_acknowledgment_comment('Review triggered.', 'coderabbit') is True
    assert github_re_review.is_acknowledgment_comment(CODERABBIT_GENUINE_SHORT_REVIEW_COMMENT, 'coderabbit') is False


# =============================================================================
# A non-verifying answer is withheld while the review is still running
# =============================================================================


def _non_verifying_answer():
    """A genuine CodeRabbit comment that names no commit — a decline once the review has ended."""
    return _comment(_CODERABBIT_LOGIN, created_at='2026-01-01T00:05:00Z', body=_CODERABBIT_GENUINE_COMMENT)


def test_a_non_verifying_answer_is_withheld_while_the_review_is_running(monkeypatch):
    """A running review has not answered, so the comment is not reported as its decline."""
    calls: list = []

    result = _await_with_comments(
        monkeypatch,
        [_non_verifying_answer()],
        bot_kind='coderabbit',
        in_progress_reader=_recording_reader(True, calls),
    )

    assert calls, 'the completion read was never consulted'
    assert all(call == (42, 'coderabbit') for call in calls)
    assert result['matched'] is False
    assert result['matched_signal'] == ''
    assert result['matched_comment'] == {}
    assert result['head_sha_verified'] is False
    assert result['answer_withheld_in_progress'] is True
    assert result['timed_out'] is True
    assert result['refusal_detected'] is False


def test_the_same_answer_is_matched_once_the_review_is_not_running(monkeypatch):
    """MATCHED CONTROL: same comment, same reader seam — only the observation differs."""
    calls: list = []

    result = _await_with_comments(
        monkeypatch,
        [_non_verifying_answer()],
        bot_kind='coderabbit',
        in_progress_reader=_recording_reader(False, calls),
    )

    assert calls, 'the completion read was never consulted'
    assert result['matched'] is True
    assert result['matched_signal'] == 'issue_comment'
    assert result['head_sha_verified'] is False
    assert result['answer_withheld_in_progress'] is False


def test_a_verifying_answer_is_matched_without_consulting_the_completion_read(monkeypatch):
    """A comment that names the awaited HEAD is the answer however the check stands."""
    calls: list = []

    result = _await_with_comments(
        monkeypatch,
        [_republished_comment(_VERIFYING_REFERENCE)],
        bot_kind='coderabbit',
        head_sha=_HEAD_SHA,
        in_progress_reader=_recording_reader(True, calls),
    )

    assert result['matched'] is True
    assert result['head_sha_verified'] is True
    assert result['answer_withheld_in_progress'] is False
    assert calls == []


def test_a_matched_review_never_consults_the_completion_read(monkeypatch):
    """The read is taken only for a comment that does not verify — a review costs none."""
    calls: list = []

    result = _await_with_comments(
        monkeypatch,
        [],
        reviews=[_review('headsha', '2026-01-01T00:05:00Z', body=_GENUINE_REVIEW_BODY)],
        bot_kind='coderabbit',
        in_progress_reader=_recording_reader(True, calls),
    )

    assert result['matched'] is True
    assert result['matched_signal'] == 'review'
    assert result['answer_withheld_in_progress'] is False
    assert calls == []


def test_the_neutralized_in_progress_read_leaves_the_answer_matched(monkeypatch):
    """POSITIVE arm of the fixture's matched pair: the provider reports a running review, unseen.

    The fake completion read below reports ``in_progress: true``. With the autouse
    fixture engaged the default seam never reaches it, so the answer is matched.
    """
    calls: list = []
    monkeypatch.setattr(bot_registry, 'completion_check_name', lambda _kind: 'CodeRabbit')
    _fake_completion_module(monkeypatch, {'in_progress': True}, calls)

    result = _await_with_comments(monkeypatch, [_non_verifying_answer()], bot_kind='coderabbit')

    assert result['matched'] is True
    assert result['answer_withheld_in_progress'] is False
    assert calls == []


def test_the_unneutralized_in_progress_read_withholds_the_same_answer(monkeypatch):
    """NEGATIVE arm: with the live reader restored, the same running review withholds it.

    Identical to the arm above except that the fixture's patch is undone, which is
    what proves the fixture — and not an absent read — is what kept that arm matched.
    """
    calls: list = []
    monkeypatch.setattr(bot_registry, 'completion_check_name', lambda _kind: 'CodeRabbit')
    _fake_completion_module(monkeypatch, {'in_progress': True}, calls)
    monkeypatch.setattr(github_re_review, 'read_bot_in_progress', _LIVE_IN_PROGRESS_READER)

    result = _await_with_comments(monkeypatch, [_non_verifying_answer()], bot_kind='coderabbit')

    assert calls, 'the live reader never reached the completion read'
    assert all(call == (42, 'coderabbit', 'CodeRabbit') for call in calls)
    assert result['matched'] is False
    assert result['answer_withheld_in_progress'] is True


def test_read_bot_in_progress_reports_a_positive_observation(monkeypatch):
    """Only ``in_progress: true`` from the completion read answers True."""
    calls: list = []
    monkeypatch.setattr(bot_registry, 'completion_check_name', lambda _kind: 'CodeRabbit')
    _fake_completion_module(monkeypatch, {'in_progress': True}, calls)

    assert _LIVE_IN_PROGRESS_READER('42', 'coderabbit') is True
    assert calls == [(42, 'coderabbit', 'CodeRabbit')]


@pytest.mark.parametrize(
    'observation',
    [
        pytest.param({'in_progress': False}, id='concluded'),
        pytest.param({}, id='no-field'),
        pytest.param({'in_progress': 'true'}, id='truthy-but-not-true'),
        pytest.param(None, id='no-envelope'),
    ],
)
def test_read_bot_in_progress_answers_false_for_anything_but_a_positive_observation(monkeypatch, observation):
    """A hold is armed by a positive observation only — every other read changes nothing."""
    monkeypatch.setattr(bot_registry, 'completion_check_name', lambda _kind: 'CodeRabbit')
    _fake_completion_module(monkeypatch, observation)

    assert _LIVE_IN_PROGRESS_READER(42, 'coderabbit') is False


def test_read_bot_in_progress_answers_false_when_the_read_fails(monkeypatch):
    """A failed read is no observation — it must not withhold an answer."""
    calls: list = []
    monkeypatch.setattr(bot_registry, 'completion_check_name', lambda _kind: 'CodeRabbit')
    _fake_completion_module(monkeypatch, {'in_progress': True}, calls, raises=RuntimeError('gh unavailable'))

    assert _LIVE_IN_PROGRESS_READER(42, 'coderabbit') is False
    assert calls, 'the failing read was never reached, so the failure path went unexercised'


def test_read_bot_in_progress_makes_no_read_for_a_bot_without_a_completion_check(monkeypatch):
    """A bot that declares no check-run has nothing to observe, and costs no provider read."""
    calls: list = []
    monkeypatch.setattr(bot_registry, 'completion_check_name', lambda _kind: '')
    _fake_completion_module(monkeypatch, {'in_progress': True}, calls)

    assert _LIVE_IN_PROGRESS_READER(42, 'coderabbit') is False
    assert calls == []

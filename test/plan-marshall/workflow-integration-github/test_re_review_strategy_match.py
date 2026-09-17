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

``test_the_neutralized_guard_posts_despite_a_claimed_window_in_the_store`` and
``test_the_unneutralized_guard_refuses_on_the_same_claimed_window`` are a MATCHED
PAIR standing guard over that fixture, and DELETING OR WEAKENING EITHER ARM
SILENTLY VOIDS THE OTHER'S EVIDENTIARY VALUE. Both arms simulate a claimed,
unexpired window in the store BELOW the fixture's seam; they differ only in
whether the fixture is engaged. The positive arm alone cannot tell "the fixture
works" from "this machine's store happens to hold no claim", and the negative
control alone proves only that a claim CAN refuse, not that it is suppressed by
default.
"""
import argparse
import sys
import time

import _github_pr
import bot_registry
import ci_base
import github_re_review
import pytest

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
def _match_bot_comment(comments, head_sha, bot_kind, trigger_dt, refusals=None):
    """Call ``_match_bot_comment`` with a throwaway refusal accumulator.

    ``head_sha`` sits where :meth:`_match_review`'s does, because the comment arm
    now reads it too: among the eligible comments it prefers one whose body names
    that SHA.
    """
    return github_re_review._ReReviewStrategy._match_bot_comment(
        comments, head_sha, bot_kind, trigger_dt, [] if refusals is None else refusals
    )
_PR_AGENT_LOGIN = 'cuioss-review-bot'
_TRIGGER = '2026-01-01T00:02:00Z'
def _await_with_comments(monkeypatch, comments, *, reviews=None, bot_kind='cuioss-review-bot', head_sha='headsha'):
    """Run ``await_fresh_review`` over a fixed comment (and review) set.

    ``head_sha`` is parametrized for the reviewed-commit-reference cases below, which
    need a real 40-hex SHA to exercise the URL-embedded shape. It defaults to the
    ``'headsha'`` token every other case uses, so those are unaffected.
    """
    _noop_sleep(monkeypatch)
    monkeypatch.setattr(
        github_re_review._github,
        'fetch_pr_reviews_with_commits',
        lambda pr_number: {'status': 'success', 'reviews': list(reviews or [])},
    )
    _patch_comments(monkeypatch, comments)
    strategy = github_re_review.resolve_strategy(bot_kind)
    return strategy.await_fresh_review(42, head_sha, _TRIGGER, bot_kind=bot_kind, timeout=1, interval=0)
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

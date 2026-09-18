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


_GUARD_SWEEP_POPULATION: list[str] = bot_registry.bot_kinds()
_GUARD_SWEEP_POPULATION_SIZE = len(_GUARD_SWEEP_POPULATION)
assert _GUARD_SWEEP_POPULATION, 'the registry declares no bots — every chokepoint sweep below would be vacuous'
_GUARD_PR_NUMBER = 42
_GUARD_PUSH_TIME = '2026-01-01T00:00:00Z'


def _record_posts(monkeypatch) -> list[tuple]:
    """Replace ``post_pr_comment`` with a recorder; return the list it appends to.

    The SAME recorder shape backs both the refusing cases (which assert the list
    is empty) and the permitting cases (which assert it holds exactly the trigger
    comment), so an empty list can never be read as "the recorder was never
    wired".
    """
    posted: list[tuple] = []

    def fake_post(pr_number, body):
        posted.append((pr_number, body))
        return {'status': 'success', 'operation': 'post_pr_comment', 'pr_number': pr_number}

    monkeypatch.setattr(github_re_review._github, 'post_pr_comment', fake_post)
    return posted


_PR_AGENT_LOGIN = 'cuioss-review-bot'
_TRIGGER = '2026-01-01T00:02:00Z'
_HEAD_SHA = 'a1b2c3d4e5f60718293a4b5c6d7e8f9012345678'
_OTHER_SHA = '0f1e2d3c4b5a69788796a5b4c3d2e1f098765432'
_HEAD_SHA_URL = f'https://github.com/cuioss/plan-marshall/commit/{_HEAD_SHA}'
_OTHER_SHA_URL = f'https://github.com/cuioss/plan-marshall/commit/{_OTHER_SHA}'
_OBSERVED_REVIEW_BOT_SHA = '4d6738e2d96150706cda6b682109336c5c0c383b'
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
_UNRECOGNISED_REFUSAL = 'Not reviewing this one.'


def test_no_bot_specific_strategy_classes_remain():
    """The refactor removed every per-bot strategy subclass — only the generic one exists."""
    assert not hasattr(github_re_review, '_CodeRabbitStrategy')
    assert not hasattr(github_re_review, '_SourceryStrategy')
    assert not hasattr(github_re_review, '_PrAgentStrategy')


def test_sourcery_is_a_valid_bot_kind():
    """``sourcery`` is a first-class member of the canonical BOT_KINDS enum."""
    from _findings_core import BOT_KINDS

    assert 'sourcery' in BOT_KINDS


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

    strategy = github_re_review.resolve_strategy('cuioss-review-bot')
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

    strategy = github_re_review.resolve_strategy('cuioss-review-bot')
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

    strategy = github_re_review.resolve_strategy('cuioss-review-bot')
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


@pytest.mark.parametrize('bot_kind', _GUARD_SWEEP_POPULATION)
def test_an_unexpired_claimed_window_posts_no_trigger_comment(bot_kind, monkeypatch):
    """⛔ The load-bearing case: a live claim means NO comment reaches the PR.

    Paired with ``test_an_expired_window_posts_the_trigger_comment`` over the same
    population and the same recorder: without that control an empty post list here
    is equally consistent with a guard that never posts for anyone.
    """
    posted = _record_posts(monkeypatch)
    strategy = github_re_review.resolve_strategy(bot_kind)

    result = strategy.request_fresh_review(
        _GUARD_PR_NUMBER, _GUARD_PUSH_TIME, window_reader=_window_reader(_OPEN_WINDOW)
    )

    assert posted == [], (
        f'{bot_kind}: the guard posted a trigger comment while the rate window was '
        f'claimed and unexpired — the refusal envelope is not the contract, NOT '
        f'posting is'
    )
    assert result['status'] == 'refused'
    assert result['reason'] == 'window_open'


@pytest.mark.parametrize('bot_kind', _GUARD_SWEEP_POPULATION)
def test_an_expired_window_posts_the_trigger_comment(bot_kind, monkeypatch):
    """MATCHED CONTROL — a claim whose clock ran out permits the post.

    The record still EXISTS here, so this is not the no-record case: the only
    thing that changed against the refusing arm is ``expired``. That is what
    attributes the refusal above to the predicate rather than to the presence of a
    record, and what shows the guard did not simply disable re-review.
    """
    posted = _record_posts(monkeypatch)
    strategy = github_re_review.resolve_strategy(bot_kind)

    result = strategy.request_fresh_review(
        _GUARD_PR_NUMBER, _GUARD_PUSH_TIME, window_reader=_window_reader(_EXPIRED_WINDOW)
    )

    assert result['status'] == 'success'
    assert posted == [(_GUARD_PR_NUMBER, strategy.trigger_comment)]


@pytest.mark.parametrize('bot_kind', _GUARD_SWEEP_POPULATION)
def test_a_bot_with_no_stored_record_posts_the_trigger_comment(bot_kind, monkeypatch):
    """The ORDINARY post-merge path: a re-review that followed no refusal at all.

    ``rate-window check`` reports ``expired: true`` for a bot with no stored
    record, so this case is authorized through the SAME ``expired is False``
    predicate that refuses a live claim — no carve-out, no second branch. Pinning
    it is what keeps a future tightening of the guard from quietly taking the
    common path down with it.
    """
    posted = _record_posts(monkeypatch)
    strategy = github_re_review.resolve_strategy(bot_kind)

    result = strategy.request_fresh_review(
        _GUARD_PR_NUMBER, _GUARD_PUSH_TIME, window_reader=_window_reader(_NO_RECORD_WINDOW)
    )

    assert result['status'] == 'success'
    assert posted == [(_GUARD_PR_NUMBER, strategy.trigger_comment)]


@pytest.mark.parametrize('bot_kind', _GUARD_SWEEP_POPULATION)
def test_an_unreadable_window_read_posts_the_trigger_comment(bot_kind, monkeypatch):
    """A read that could not be performed carries no ``expired`` key, so it permits.

    The guard refuses only on a POSITIVE observation. Refusing on an unreadable
    read would take the whole re-review path down whenever the lock store is
    unreachable — a far larger failure than the one the guard exists to prevent —
    so the direction here is deliberate rather than incidental.
    """
    posted = _record_posts(monkeypatch)
    strategy = github_re_review.resolve_strategy(bot_kind)

    result = strategy.request_fresh_review(
        _GUARD_PR_NUMBER,
        _GUARD_PUSH_TIME,
        window_reader=_window_reader({'status': 'unreadable', 'error': 'store unreachable'}),
    )

    assert result['status'] == 'success'
    assert posted == [(_GUARD_PR_NUMBER, strategy.trigger_comment)]


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


def test_bot_kind_for_author_sourcery_strips_bot_suffix():
    """A ``[bot]``-suffixed sourcery login is normalized before lookup."""
    assert github_re_review.bot_kind_for_author('sourcery-ai[bot]') == 'sourcery'


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


def test_main_recovery_action_still_rejects_an_omitted_bot_kind(monkeypatch):
    """POSITIVE CONTROL — argparse rejection IS reachable through this entry point.

    The permissiveness above is scoped to the flag's VALUE, not to the parser:
    ``--bot-kind`` is still required, and omitting it exits 2. Without this the
    "no ``SystemExit``" above would be an assertion about a parser that might
    reject nothing at all.
    """
    monkeypatch.setattr(sys, 'argv', ['github_re_review.py', 'recovery-action'])

    with pytest.raises(SystemExit) as excinfo:
        github_re_review.main()

    assert excinfo.value.code == 2

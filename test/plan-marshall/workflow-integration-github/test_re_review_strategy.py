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

# ---------------------------------------------------------------------------
# The rate-window seam the trigger guard reads, and its neutralization
# ---------------------------------------------------------------------------

#: A rate-window observation carrying NO stored record — what ``rate-window
#: check`` reports for a bot that has never refused. ``expired: True`` is what
#: authorizes the ordinary post-merge trigger through the guard's single
#: ``expired is False`` predicate, with no carve-out for the no-refusal case.
_NO_RECORD_WINDOW = {'status': 'free', 'expired': True, 'holder': '', 'seconds_remaining': 0.0}

#: A CLAIMED, UNEXPIRED window — the ONE observation the guard refuses on.
_OPEN_WINDOW = {
    'status': 'claimed',
    'expired': False,
    'holder': 'a-concurrently-finalizing-plan',
    'seconds_remaining': 1800.0,
}

#: A claim whose clock has run out. Structurally an open record, so it is not the
#: no-record case, yet ``expired: True`` means the guard permits — which is what
#: makes it the discriminating positive control for the refusing arm.
_EXPIRED_WINDOW = {
    'status': 'claimed',
    'expired': True,
    'holder': 'a-concurrently-finalizing-plan',
    'seconds_remaining': 0.0,
}

#: The LIVE, store-reading observer, captured at import time — BEFORE the autouse
#: fixture below can replace it. The negative control restores it to show the
#: ambient store is genuinely reachable through this seam, which is what makes the
#: positive arm's outcome attributable to the fixture rather than to an empty
#: store on this particular machine.
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
    """cuioss-review-bot resolves to the same generic strategy class, carrying its own trigger."""
    strategy = github_re_review.resolve_strategy('cuioss-review-bot')

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
    """coderabbit and cuioss-review-bot must not collapse onto the same strategy object."""
    coderabbit = github_re_review.resolve_strategy('coderabbit')
    pr_agent = github_re_review.resolve_strategy('cuioss-review-bot')

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


# =============================================================================
# Concern 5: the refusal re-trigger guard at the trigger chokepoint
# =============================================================================
#
# ⛔ Every case below asserts that ``post_pr_comment`` was NOT CALLED. That is the
# guard's PURPOSE — no trigger comment reaches the PR while the bot is refusing —
# and it is not the same claim as "a refusal status came back": an implementation
# that posted the comment first and computed the status afterwards satisfies the
# envelope assertion and violates the guard completely. The envelope fields are
# asserted too, but they are the weaker half.
#
# The sweep runs over the registry-derived bot population rather than a bot-name
# literal, because the guard sits at the single chokepoint EVERY bot's trigger
# passes through — a per-bot exemption is exactly what it must not have.

#: The bot population the chokepoint sweep runs over, DERIVED from the registry so
#: a bot added in a ``standards/{bot_kind}.md`` doc is swept with no test edit.
_GUARD_SWEEP_POPULATION: list[str] = bot_registry.bot_kinds()

#: PUBLISHED population size. A ``parametrize`` over an empty population yields
#: zero cases and still reports green, so the breadth of the sweep is stated
#: rather than implied — an empty registry fails loudly instead of certifying
#: nothing.
_GUARD_SWEEP_POPULATION_SIZE = len(_GUARD_SWEEP_POPULATION)

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


def _simulate_store(monkeypatch, observation) -> dict:
    """Put ``observation`` in the store the LIVE reader delegates to, and count reads.

    Patched at ``merge_lock.run_rate_window`` — one layer BELOW the seam the
    autouse fixture replaces — which is what lets the matched pair simulate an
    ambient claim while the fixture is engaged. The read count is the direct
    evidence of which route the guard took.

    ``merge_lock`` is imported HERE rather than at module scope, mirroring
    ``read_rate_window``'s own lazy import: only the matched pair needs it, so an
    import problem fails those two tests loudly instead of failing collection for
    every test in this module.
    """
    import merge_lock

    reads = {'count': 0}

    def fake_run_rate_window(_namespace):
        reads['count'] += 1
        return dict(observation)

    monkeypatch.setattr(merge_lock, 'run_rate_window', fake_run_rate_window)
    return reads


def test_the_guard_sweep_population_is_non_empty_and_publishes_its_size():
    """⛔ Vacuity guard for the derived chokepoint sweeps below, size STATED.

    Every guard case is parametrized over ``_GUARD_SWEEP_POPULATION``. A
    parametrize over an empty list produces zero cases and reports green, so the
    sweep would look like whole-population coverage while asserting nothing about
    any bot. The population is therefore asserted non-empty and its size
    published, and every member is asserted to resolve a strategy — a bot with no
    strategy has no chokepoint to guard, so it would silently contribute a
    hollow case.
    """
    assert _GUARD_SWEEP_POPULATION, 'the registry declares no bots — every chokepoint sweep below would be vacuous'
    assert _GUARD_SWEEP_POPULATION_SIZE == len(_GUARD_SWEEP_POPULATION)
    for bot_kind in _GUARD_SWEEP_POPULATION:
        assert github_re_review.resolve_strategy(bot_kind) is not None, bot_kind


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
def test_the_refusal_envelope_names_the_holder_and_the_seconds_remaining(bot_kind, monkeypatch):
    """The refusal is a RETURNED value naming who holds the window and for how long.

    A caller cannot decide between waiting and escalating without both, and the
    guard must never raise — a raise out of the trigger path would take down the
    whole re-review sequence instead of handing back a branchable verdict.
    """
    _record_posts(monkeypatch)
    strategy = github_re_review.resolve_strategy(bot_kind)

    result = strategy.request_fresh_review(
        _GUARD_PR_NUMBER, _GUARD_PUSH_TIME, window_reader=_window_reader(_OPEN_WINDOW)
    )

    assert result['operation'] == 'request_fresh_review'
    assert result['bot_kind'] == bot_kind
    assert result['pr_number'] == _GUARD_PR_NUMBER
    assert result['holder'] == _OPEN_WINDOW['holder']
    assert result['seconds_remaining'] == _OPEN_WINDOW['seconds_remaining']


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


def test_the_neutralized_guard_posts_despite_a_claimed_window_in_the_store(monkeypatch):
    """POSITIVE ARM — the autouse fixture is engaged, so an ambient claim is ignored.

    A claimed, unexpired window is simulated in the store the LIVE reader
    delegates to — one layer below the seam the fixture replaces — and the guard
    must still permit, which is only true if the fixture actually replaced that
    seam. The zero read count is the direct evidence: the live route was never
    taken.

    Pairs with ``test_the_unneutralized_guard_refuses_on_the_same_claimed_window``.
    """
    reads = _simulate_store(monkeypatch, _OPEN_WINDOW)
    posted = _record_posts(monkeypatch)
    strategy = github_re_review.resolve_strategy(_GUARD_SWEEP_POPULATION[0])

    result = strategy.request_fresh_review(_GUARD_PR_NUMBER, _GUARD_PUSH_TIME)

    assert result['status'] == 'success'
    assert posted == [(_GUARD_PR_NUMBER, strategy.trigger_comment)]
    assert reads['count'] == 0, (
        'the autouse _neutralize_rate_window fixture did not engage — a guard read '
        'reached the live store route, so every test in this module that drives '
        'request_fresh_review is silently dependent on machine-global lock state'
    )


def test_the_unneutralized_guard_refuses_on_the_same_claimed_window(monkeypatch):
    """NEGATIVE CONTROL — with the fixture disengaged, the SAME claim refuses.

    This is what makes the positive arm meaningful: it proves the simulated claim
    is genuinely reachable through the live reader, so that arm's permitting
    outcome is attributable to the fixture rather than to a store that happens to
    hold nothing on this machine.

    Pairs with
    ``test_the_neutralized_guard_posts_despite_a_claimed_window_in_the_store``.
    """
    monkeypatch.setattr(github_re_review, 'read_rate_window', _LIVE_WINDOW_READER)
    reads = _simulate_store(monkeypatch, _OPEN_WINDOW)
    posted = _record_posts(monkeypatch)
    strategy = github_re_review.resolve_strategy(_GUARD_SWEEP_POPULATION[0])

    result = strategy.request_fresh_review(_GUARD_PR_NUMBER, _GUARD_PUSH_TIME)

    assert reads['count'] == 1, (
        'restoring the live reader did not reach the simulated store, so the '
        'positive arm proves nothing about the fixture'
    )
    assert result['status'] == 'refused'
    assert posted == []


# =============================================================================
# Concern 3: Fresh-review matching (_match_review / await_fresh_review)
# =============================================================================


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


def _match_bot_comment(comments, bot_kind, trigger_dt, refusals=None):
    """Call ``_match_bot_comment`` with a throwaway refusal accumulator."""
    return github_re_review._ReReviewStrategy._match_bot_comment(
        comments, bot_kind, trigger_dt, [] if refusals is None else refusals
    )


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

    strategy = github_re_review.resolve_strategy('cuioss-review-bot')
    result = strategy.await_fresh_review(42, 'headsha', _TRIGGER, timeout=1, interval=0)

    assert result['matched'] is False
    assert result['matched_signal'] == ''


def test_match_bot_comment_fail_closed_on_unparseable_timestamps():
    """A comment whose only timestamps are unparseable never matches (fail-closed)."""
    trigger_dt = _parse(_TRIGGER)
    comments = [_comment(_PR_AGENT_LOGIN, created_at='not-a-timestamp', updated_at='')]

    assert _match_bot_comment(comments, 'cuioss-review-bot', trigger_dt) is None


def test_match_bot_comment_fail_closed_on_missing_trigger_time():
    """An unparseable trigger time yields no comment match (fail-closed)."""
    comments = [_comment(_PR_AGENT_LOGIN, created_at='2026-01-01T00:05:00Z')]

    assert _match_bot_comment(comments, 'cuioss-review-bot', None) is None


# =============================================================================
# The reviewed-commit REFERENCE is recognised wherever the evidence carries it
# =============================================================================
#
# ⛔ This is the one predicate on this path that fails toward BLOCKING. Comparing the
# whole ``commit_sha`` field for string equality recognised only the bare-token shape;
# the same reviewed-commit evidence also arrives as a ``…/commit/{sha}`` permalink,
# which then matched no review, fell through to the weaker comment discriminator, and
# published ``head_sha_verified: false`` — an incremental-review decline the bot never
# made. Consumed as the blocking ``declined`` taxonomy member whose documented remedy
# is to ACCEPT the decline rather than re-trigger, so the false verdict stops a merge
# AND steers the operator away from the retry that would have exposed it.
#
# The correction is therefore a WIDENING, and a widening asserted only by its positive
# case cannot show it did not simply match everything. Every case below is paired:
# the positive is built from the SAME ``_review()`` fixture builder as its negative,
# differing only in WHICH commit the reference names, so an extractor that matched
# anything SHA-shaped would fail the negative while still passing the positive.
#
# The widening is in LOCATION ONLY — every extracted token is still compared for
# EQUALITY — which is what the abbreviation and longer-hex-run cases pin.

#: A real 40-hex commit SHA and the permalink that carries it. A real SHA is needed
#: here rather than the ``'headsha'`` token the fixtures elsewhere use: that token is
#: not hex at all, so no token scan can extract it — which is precisely why the
#: extractor keeps a whole-field equality arm AHEAD of the scan, and why the bare
#: cases above still pass.
_HEAD_SHA = 'a1b2c3d4e5f60718293a4b5c6d7e8f9012345678'
_OTHER_SHA = '0f1e2d3c4b5a69788796a5b4c3d2e1f098765432'
_HEAD_SHA_URL = f'https://github.com/cuioss/plan-marshall/commit/{_HEAD_SHA}'
_OTHER_SHA_URL = f'https://github.com/cuioss/plan-marshall/commit/{_OTHER_SHA}'


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


def test_the_bare_token_shape_still_verifies_after_the_widening():
    """The widening is a SUPERSET: the shape that already worked still works.

    Asserted at the extractor rather than only through a matcher, and paired with the
    non-hex case, because the whole-field equality arm is what keeps a reviewed-commit
    value that is not hex-shaped — which nothing on this path validates it to be —
    from silently ceasing to match once a token scan was introduced.
    """
    assert github_re_review._references_head_sha(_HEAD_SHA, _HEAD_SHA) is True
    assert github_re_review._references_head_sha(_HEAD_SHA_URL, _HEAD_SHA) is True
    assert github_re_review._references_head_sha('headsha', 'headsha') is True
    assert github_re_review._references_head_sha(_OTHER_SHA, _HEAD_SHA) is False


def test_the_extractor_reads_no_sha_out_of_a_longer_hex_run():
    """A 64-hex digest yields no spurious 40-character prefix match.

    The surrounding-character guards are what keep the scan from reading a SLICE of a
    longer alphanumeric run as a commit reference. Built by extending the awaited SHA
    itself, so the digest genuinely OPENS with the 40 characters a boundary-less
    extractor would match — a fixture that merely differed everywhere would not
    exercise the guard.
    """
    digest = _HEAD_SHA + '9' * 24

    assert len(digest) == 64
    assert digest.startswith(_HEAD_SHA)
    assert github_re_review._references_head_sha(digest, _HEAD_SHA) is False


def test_the_extractor_fails_closed_on_an_absent_head_sha():
    """An empty head SHA verifies nothing — answering True would verify everything."""
    assert github_re_review._references_head_sha(_HEAD_SHA_URL, '') is False
    assert github_re_review._references_head_sha('', _HEAD_SHA) is False


def test_await_records_a_url_embedded_sha_as_a_verified_review(monkeypatch):
    """POSITIVE, at the field a consumer actually reads: ``head_sha_verified: true``.

    The matcher assertions above pin the extraction; this pins the ENVELOPE, because
    ``head_sha_verified`` is the bit both re-review consumers branch on and the one
    that manufactured the false decline. No comment is supplied, so nothing but the
    review can satisfy the await and the weaker signal cannot mask the result.
    """
    result = _await_with_comments(
        monkeypatch,
        [],
        reviews=[_review(_HEAD_SHA_URL, '2026-01-01T00:05:00Z')],
        head_sha=_HEAD_SHA,
    )

    assert result['matched'] is True
    assert result['matched_signal'] == 'review'
    assert result['head_sha_verified'] is True
    assert result['timed_out'] is False


def test_await_does_not_verify_a_review_naming_a_different_commit(monkeypatch):
    """NEGATIVE control at the envelope: a genuinely different commit stays unverified.

    Same helper, same URL shape, same absence of comments — only the named commit
    differs. This is the arm that would flip green under an over-wide extractor, and
    it is asserted on ``head_sha_verified`` explicitly rather than inferred from
    ``matched``, because that field is the actual claim the consumers read.
    """
    result = _await_with_comments(
        monkeypatch,
        [],
        reviews=[_review(_OTHER_SHA_URL, '2026-01-01T00:05:00Z')],
        head_sha=_HEAD_SHA,
    )

    assert result['matched'] is False
    assert result['matched_signal'] == ''
    assert result['head_sha_verified'] is False
    assert result['timed_out'] is True


# =============================================================================
# The COMMENT path verifies the HEAD too — the reference is read off the body
# =============================================================================
#
# ⛔ "An issue comment carries no reviewed-commit SHA" was a PREMISE, never an
# observation, and it is false for a bot whose only declared publish shape is an
# issue comment. ``cuioss-review-bot`` declares ``participation_evidence:
# issue_comment`` with an empty ``completion_check_name`` — it submits no review
# object at all — and it names the commit it reviewed INSIDE that comment, as a
# ``…/commit/{sha}`` permalink: the exact URL-embedded shape the section above
# already taught ``_references_head_sha`` to recognise on the review path.
#
# While the field was hard-coded ``matched_signal == 'review'``, the matcher never
# inspected the body, so every correct re-review that bot performed was published as
# ``matched: true`` / ``head_sha_verified: false`` — which both consumers route as an
# incremental-review DECLINE. That member is blocking and its documented remedy is to
# demote the bot to ``optional_bots`` or take a merge-authorization waiver, so a
# REQUIRED bot in this shape could never verify and the pipeline's own advice was to
# stop requiring it.
#
# Every case below is PAIRED on the observed body: the positive and its negative
# control are built from the same body template and differ only in WHICH commit the
# permalink names, so a matcher that answered ``true`` for any comment fails the
# negative while still passing the positive. The third case is the genuine decline —
# a comment naming no commit at all — and it pins that the correction did not erase
# the state it was distinguishing.

#: The commit ``cuioss-review-bot`` named on the live observation (plan-marshall
#: #1473). A REAL 40-hex SHA rather than the ``'headsha'`` token the fixtures above
#: use: the token is not hex, so no token scan can extract it, and the URL-embedded
#: shape is the whole point here.
_OBSERVED_REVIEW_BOT_SHA = '4d6738e2d96150706cda6b682109336c5c0c383b'


def _guide_body(sha: str) -> str:
    """The Guide body shape observed live, naming ``sha`` as the reviewed commit.

    Pinned as the OBSERVED wording rather than a synthetic "sha: <hex>" string: the
    permalink is how this bot actually reports its reviewed commit, and a fixture
    that invented an easier shape would prove the matcher handles a shape no bot
    emits. The heading is carried too, because the real comment is one persistent
    Guide that the bot EDITS — the body always arrives with it attached.
    """
    return f'## PR Reviewer Guide 🔍 (Review updated until commit https://github.com/cuioss/plan-marshall/commit/{sha})'


def test_await_verifies_a_comment_whose_body_names_the_awaited_commit(monkeypatch):
    """POSITIVE: the live defect, pinned at the field both consumers branch on.

    No review is supplied, so nothing but the comment can satisfy the await and the
    stronger signal cannot mask the result.
    """
    result = _await_with_comments(
        monkeypatch,
        [
            _comment(
                _PR_AGENT_LOGIN,
                created_at='2026-01-01T00:05:00Z',
                body=_guide_body(_OBSERVED_REVIEW_BOT_SHA),
            )
        ],
        head_sha=_OBSERVED_REVIEW_BOT_SHA,
    )

    assert result['matched'] is True
    assert result['matched_signal'] == 'issue_comment'
    assert result['head_sha_verified'] is True
    assert result['timed_out'] is False


def test_await_does_not_verify_a_comment_naming_a_different_commit(monkeypatch):
    """NEGATIVE control: the same body shape naming another commit stays unverified.

    Same builder, same author, same timestamps — the ONLY difference is which commit
    the permalink names. Without it the positive above would pass just as happily
    against a matcher widened to answer ``true`` for every comment, which is the
    false-green that would credit a re-review nobody performed.

    It must still MATCH: the bot answered, and a decline is an observation the
    ``declined`` member is built on. Collapsing it into a timeout would lose it.
    """
    result = _await_with_comments(
        monkeypatch,
        [_comment(_PR_AGENT_LOGIN, created_at='2026-01-01T00:05:00Z', body=_guide_body(_OTHER_SHA))],
        head_sha=_OBSERVED_REVIEW_BOT_SHA,
    )

    assert result['matched'] is True
    assert result['matched_signal'] == 'issue_comment'
    assert result['head_sha_verified'] is False


def test_await_does_not_verify_a_comment_naming_no_commit_at_all(monkeypatch):
    """The genuine DECLINE survives the correction unchanged.

    A bot that answers the trigger without naming any reviewed commit is the case
    ``head_sha_verified: false`` was always supposed to report, and the widening must
    not launder it. The body is the same Guide heading with the permalink clause
    absent — the shape a bot emits when it acknowledges without reviewing.
    """
    result = _await_with_comments(
        monkeypatch,
        [_comment(_PR_AGENT_LOGIN, created_at='2026-01-01T00:05:00Z', body='## PR Reviewer Guide 🔍')],
        head_sha=_OBSERVED_REVIEW_BOT_SHA,
    )

    assert result['matched'] is True
    assert result['matched_signal'] == 'issue_comment'
    assert result['head_sha_verified'] is False


def test_the_comment_and_review_paths_share_ONE_predicate():
    """The verification rule is the same function on both paths, over both fields.

    Asserted at the helper rather than only through the envelope, because the
    property that matters is that neither path can drift into its own rule. An
    unmatched signal fails closed — there is no evidence to verify against.
    """
    review = _review(_HEAD_SHA, '2026-01-01T00:05:00Z')
    comment = _comment(_PR_AGENT_LOGIN, created_at='2026-01-01T00:05:00Z', body=_guide_body(_HEAD_SHA))

    assert github_re_review._verifies_head_sha('review', review, _HEAD_SHA) is True
    assert github_re_review._verifies_head_sha('issue_comment', comment, _HEAD_SHA) is True
    assert github_re_review._verifies_head_sha('issue_comment', comment, _OTHER_SHA) is False
    # Fail-closed: nothing matched, so nothing is verified.
    assert github_re_review._verifies_head_sha('', None, _HEAD_SHA) is False


# =============================================================================
# The same body-derived verdict on the OTHER publish shape — an in-place
# republished summary
# =============================================================================
#
# The structural constant did not only silence the permalink Guide above: it reported
# ``false`` just as flatly for a CodeRabbit summary REPUBLISHED IN PLACE whose body
# names the very commit it reviewed, manufacturing the same blocking ``declined``
# verdict one publish shape over. These cases hold the one predicate against that
# second shape, and they carry the boundary the Guide cases do not reach — an
# ABBREVIATION of the awaited SHA — so the widening is demonstrably in LOCATION only
# and equality still decides WHICH commit counts.
#
# Every case is built by ``_republished_comment`` and differs ONLY in the reference its
# body carries: the awaited HEAD verifies; no commit, a different commit, and an
# abbreviation of the awaited one do not. Each negative still MATCHES — the bot did
# answer — which is exactly the decline a consumer routes on ``head_sha_verified``.


def _republished_comment(reference):
    """A CodeRabbit in-place-republished summary naming ``reference`` in its body."""
    body = f'Review updated until commit {reference}. No actionable comments were generated.'
    return _comment(_CODERABBIT_LOGIN, created_at='2026-01-01T00:00:00Z', updated_at='2026-01-01T00:05:00Z', body=body)


def test_await_verifies_a_republished_comment_naming_the_awaited_head(monkeypatch):
    """POSITIVE: a comment whose body links the awaited HEAD reports ``head_sha_verified: true``.

    The body links the full SHA behind an abbreviated label, so the full SHA sits
    inside a commit URL in the body — the same location widening the review arm
    already applies, while the abbreviated label alone would not verify. No review
    is supplied, so only the comment arm can match and the verdict is attributable
    to the body alone.
    """
    reference = f'[{_HEAD_SHA[:7]}]({_HEAD_SHA_URL})'

    result = _await_with_comments(
        monkeypatch, [_republished_comment(reference)], bot_kind='coderabbit', head_sha=_HEAD_SHA
    )

    assert result['matched'] is True
    assert result['matched_signal'] == 'issue_comment'
    assert result['head_sha_verified'] is True
    assert result['matched_review'] == {}
    assert result['refusal_detected'] is False


@pytest.mark.parametrize(
    'reference',
    [
        pytest.param('the latest push', id='names-no-commit'),
        pytest.param(f'[{_OTHER_SHA[:7]}]({_OTHER_SHA_URL})', id='names-a-different-commit'),
        pytest.param(_HEAD_SHA[:12], id='abbreviates-the-awaited-commit'),
    ],
)
def test_await_does_not_verify_a_republished_comment_not_naming_the_awaited_head(reference, monkeypatch):
    """MATCHED NEGATIVE CONTROL: the same comment, naming anything but the awaited HEAD.

    Same builder, same author, same timestamps — only the body's reference differs
    from the positive above. The comment still completes the await (the bot answered),
    so ``matched`` stays true while ``head_sha_verified`` stays false: the
    incremental-review decline a consumer records as ``declined``. A body-derived
    verdict that returned true here would credit a review of some other commit — or of
    nothing — as a review of this HEAD.
    """
    result = _await_with_comments(
        monkeypatch, [_republished_comment(reference)], bot_kind='coderabbit', head_sha=_HEAD_SHA
    )

    assert result['matched'] is True
    assert result['matched_signal'] == 'issue_comment'
    assert result['head_sha_verified'] is False


# =============================================================================
# Refusal notices are NOT a completed review — on BOTH discriminator paths
# =============================================================================
#
# A bot can answer the re-review trigger by DECLINING to review. That answer
# arrives on either path — as an issue comment, or as a REVIEW object whose body
# is the refusal — and on the review path it would otherwise satisfy the
# commit_sha + submitted_at gates and be reported with
# ``head_sha_verified: true``. That is the false-green this section pins shut:
# the envelope would assert the new HEAD was reviewed when the bot explicitly
# said it was not.
#
# Both paths run the same refusal-recognition STACK the producer applies, arm for
# arm: the awaited bot's registry ``refusal_patterns`` (case-sensitive substring
# containment), the structural ``_is_rate_limit_notice``, and the enumerative
# ``_is_unrecognised_refusal`` for a body no earlier arm could read.
# ``_github_pr.REFUSAL_LAYERS`` is the single place those arms are named, so an arm
# added there is covered here without a count to correct.
# The registry arm reads ``refusal_patterns``, NOT ``ignore_patterns`` — the latter
# names sections of a SUCCESSFUL review, so reading it here would report a bot
# that reviewed fine as having declined.
# Every fixture body uses the FLATTENED single-line shape.

_SOURCERY_LOGIN = 'sourcery-ai'

# Sourcery's OBSERVED size-limit refusal. Recognized ONLY by the registry data layer:
# "larger than the review limit of" is a comparison, not an exceeded/reached/hit
# statement, so the structural recognizer does not see it.
_SOURCERY_REFUSAL = (
    'Sourcery was unable to review this pull request because '
    'your pull request is larger than the review limit of 150000 characters. '
    'Reduce the size of the pull request and request another review.'
)

# A structurally-shaped refusal matched by NO registry refusal_patterns entry —
# only the structural fallback can recognize it.
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

# CodeRabbit's reply to the COMMAND INVOCATION this very strategy posts. As observed:
# the trigger comment is `@coderabbitai review`, and THIS is what came back.
# Recognized only by the registry marker ``Review rate limited`` — the structural arm
# sees no exceeded/reached/hit verb, and the enumerative arm is vetoed by ``<details``.
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


def test_await_does_not_credit_the_coderabbit_command_reply_as_a_review(monkeypatch):
    """⛔ The reply to OUR OWN trigger is a refusal, not a completion.

    The sharpest false-green on the comment path, and the one that actually fired: the
    strategy posts ``@coderabbitai review``, CodeRabbit replies that it is rate limited,
    and — because no arm read that reply — the envelope returned ``matched: true`` with
    ``matched_signal: issue_comment``. A refusal was credited as the completion signal
    for the very trigger it declined, asserting review coverage that never happened.

    The correct outcome is a truthful timeout carrying a RECORDED refusal, so the
    caller can arm the rate-limit recovery instead of believing the review landed.
    """
    result = _await_with_comments(
        monkeypatch,
        [
            _comment(
                _CODERABBIT_LOGIN,
                created_at='2026-01-01T00:05:00Z',
                body=_CODERABBIT_COMMAND_REPLY_REFUSAL,
            )
        ],
        bot_kind='coderabbit',
    )

    assert result['matched'] is False
    assert result['matched_signal'] == ''
    assert result['head_sha_verified'] is False
    assert result['timed_out'] is True
    # Recorded, not swallowed — and the registry arm is named as what recognized it,
    # which is the discriminator: this body reaches no other arm.
    assert result['refusal_detected'] is True
    assert result['refusals'][0]['bot_kind'] == 'coderabbit'
    assert result['refusals'][0]['source'] == 'issue_comment'
    assert result['refusals'][0]['layer'] == _github_pr.REFUSAL_LAYER_REGISTRY


def test_await_does_not_credit_the_command_reply_delivered_as_a_review(monkeypatch):
    """The same reply submitted as a REVIEW object is likewise not a completed review.

    Worth its own case because the review path is strictly worse: the row satisfies the
    commit_sha and submitted_at gates, so it would report ``head_sha_verified: true`` —
    claiming the new HEAD was reviewed by a body that says it was not.
    """
    result = _await_with_comments(
        monkeypatch,
        [],
        reviews=[
            _review(
                'headsha',
                '2026-01-01T00:05:00Z',
                user='coderabbitai[bot]',
                body=_CODERABBIT_COMMAND_REPLY_REFUSAL,
            )
        ],
        bot_kind='coderabbit',
    )

    assert result['matched'] is False
    assert result['matched_signal'] == ''
    assert result['head_sha_verified'] is False
    assert result['refusal_detected'] is True
    assert result['refusals'][0]['layer'] == _github_pr.REFUSAL_LAYER_REGISTRY


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


def test_structural_fallback_rejects_an_uncaptured_refusal_on_the_review_path(monkeypatch):
    """A shaped refusal that no refusal_patterns entry matches is still rejected."""
    result = _await_with_comments(
        monkeypatch,
        [],
        reviews=[
            _review(
                'headsha',
                '2026-01-01T00:05:00Z',
                user='sourcery-ai[bot]',
                body=_UNCAPTURED_SHAPED_REFUSAL,
            )
        ],
        bot_kind='sourcery',
    )

    assert result['matched'] is False
    assert result['matched_signal'] == ''
    assert result['head_sha_verified'] is False


def test_structural_fallback_rejects_an_uncaptured_refusal_on_the_comment_path(monkeypatch):
    """The same uncaptured refusal is rejected when it arrives as a comment."""
    result = _await_with_comments(
        monkeypatch,
        [
            _comment(
                _SOURCERY_LOGIN,
                created_at='2026-01-01T00:05:00Z',
                body=_UNCAPTURED_SHAPED_REFUSAL,
            )
        ],
        bot_kind='sourcery',
    )

    assert result['matched'] is False
    assert result['matched_signal'] == ''


# =============================================================================
# A detected refusal is RECORDED, not swallowed into a bare timeout
# =============================================================================
#
# Rejecting a refusal (the section above) is necessary but not sufficient: before
# this contract the rejection was a bare ``continue``, so a bot that explicitly
# said "I could not review" produced the SAME envelope as a bot that never
# answered — ``matched: false`` / ``timed_out: true``, with nothing to branch on.
# The refusal vanished, and with it any chance of arming a recovery. These tests
# pin the recording: the envelope now carries ``refusal_detected``,
# ``refusal_class`` (from the bot's registry ``rate_limit_class``),
# ``refusal_eta`` (from its ``rate_limit_eta_patterns``), and a ``refusals[]``
# audit record naming the detecting layer.

# CodeRabbit's OBSERVED refusal, carrying a machine-readable ETA its registry
# ``rate_limit_eta_patterns`` extract.
_CODERABBIT_REFUSAL_WITH_ETA = (
    '> [!WARNING] > ## Review limit reached > Please wait 12 minutes and 30 seconds before requesting another review.'
)


def test_refusal_delivered_as_a_review_is_recorded_not_swallowed(monkeypatch):
    """The review-path refusal arms a recovery instead of vanishing."""
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

    # Still not a completed review — the rejection behaviour is preserved.
    assert result['matched'] is False
    assert result['head_sha_verified'] is False
    # ...but it is now distinguishable from a bot that never answered.
    assert result['refusal_detected'] is True
    assert result['refusal_class'] == bot_registry.rate_limit_class('sourcery')
    assert len(result['refusals']) == 1
    assert result['refusals'][0]['source'] == 'review'
    assert result['refusals'][0]['bot_kind'] == 'sourcery'
    assert result['refusals'][0]['layer'] == _github_pr.REFUSAL_LAYER_REGISTRY


def test_refusal_delivered_as_a_comment_is_recorded_not_swallowed(monkeypatch):
    """The comment-path refusal is recorded on the same envelope fields."""
    result = _await_with_comments(
        monkeypatch,
        [_comment(_SOURCERY_LOGIN, created_at='2026-01-01T00:05:00Z', body=_SOURCERY_REFUSAL)],
        bot_kind='sourcery',
    )

    assert result['matched'] is False
    assert result['refusal_detected'] is True
    assert result['refusals'][0]['source'] == 'issue_comment'


def test_structurally_detected_refusal_records_the_fallback_layer(monkeypatch):
    """The record names WHICH arm fired, so a reader can tell how much is KNOWN.

    The arms carry different evidential weight: registry DATA means the bot's own
    text is on file, the structural arm inferred a notice from its shape, and the
    enumerative arm read nothing at all. Conflating them would let the weakest
    recognition borrow the authority of the strongest.
    """
    result = _await_with_comments(
        monkeypatch,
        [
            _comment(
                _SOURCERY_LOGIN,
                created_at='2026-01-01T00:05:00Z',
                body=_UNCAPTURED_SHAPED_REFUSAL,
            )
        ],
        bot_kind='sourcery',
    )

    assert result['refusal_detected'] is True
    assert result['refusals'][0]['layer'] == _github_pr.REFUSAL_LAYER_STRUCTURAL


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


def test_genuine_timeout_is_distinguishable_from_a_refusal(monkeypatch):
    """The discriminator's whole point: a bot that never answered reports NO
    refusal, so the caller does not arm a recovery for a silence it cannot fix."""
    result = _await_with_comments(monkeypatch, [], bot_kind='sourcery')

    assert result['matched'] is False
    assert result['timed_out'] is True
    assert result['refusal_detected'] is False
    assert result['refusal_class'] == ''
    assert result['refusal_eta'] == ''
    assert result['refusals'] == []


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


def test_a_registry_recognised_size_refusal_records_its_cause_and_stated_cap():
    """⛔ The producer's OWN unit-level pin for the two-axis keys.

    Sourcery's observed size refusal is a per-PR SIZE ceiling, and the ceiling it
    states is read off the notice rather than declared anywhere. Asserted directly
    on ``_refusal_record`` — the producer — so that removing either key fails a
    named test in the producer's own unit module, instead of only surfacing in the
    arming fixture that consumes it. A key that is only covered downstream is a key
    whose removal reads as someone else's failure.
    """
    record = github_re_review._ReReviewStrategy._refusal_record(_SOURCERY_REFUSAL, 'sourcery', 'review')

    assert record is not None
    assert record['layer'] == _github_pr.REFUSAL_LAYER_REGISTRY
    assert record['cause'] == _github_pr.REFUSAL_CAUSE_SIZE
    assert record['cap'] == '150000 characters'


def test_a_refusal_stating_no_ceiling_records_an_empty_cap():
    """The paired no-stated-ceiling case: unknown is reported, never fabricated.

    The matched counterpart to the size case above. Same producer, same bot, a
    refusal whose notice states no figure — the cap must come back empty rather
    than defaulted, because a cap nobody observed would make an accepted coverage
    gap look audited against a number that was invented. Without this pairing the
    size assertion above would also pass on an implementation that returned some
    plausible constant.
    """
    no_ceiling = (
        'Sourcery was unable to review this pull request because you have reached your weekly rate limit of reviews.'
    )

    record = github_re_review._ReReviewStrategy._refusal_record(no_ceiling, 'sourcery', 'review')

    assert record is not None
    assert record['layer'] == _github_pr.REFUSAL_LAYER_REGISTRY
    # Recognised as a refusal, but a QUOTA one — so no ceiling is claimed.
    assert record['cause'] == _github_pr.REFUSAL_CAUSE_QUOTA
    assert record['cap'] == ''


def test_recorded_refusal_body_is_a_single_truncated_line():
    """The record rides a TOON envelope, whose scalars are single-line — a
    multi-line body would be silently clipped at the transport layer."""
    multiline = 'Review limit reached\n\nPlease wait 5 minutes ' + ('x' * 500)

    record = github_re_review._ReReviewStrategy._refusal_record(multiline, 'coderabbit', 'review')

    assert record is not None
    assert '\n' not in record['body']
    assert len(record['body']) <= github_re_review._REFUSAL_BODY_EXCERPT_CHARS + len('...')
    # The two-axis keys ride the same record. CodeRabbit declares no size marker,
    # so this quota refusal states no ceiling — empty, never a fabricated figure.
    assert record['cause'] == _github_pr.REFUSAL_CAUSE_QUOTA
    assert record['cap'] == ''


# =============================================================================
# The ENUMERATIVE arm on the re-review path
# =============================================================================
#
# This is the WORSE half of the blind spot the plan closes. On the producer path a
# refusal no arm recognised became a finding a human could at least read; here it
# fell through ``_refusal_record``'s terminal ``else: return None`` into
# ``_match_review``, which admits any body that is "not a refusal notice" — so the
# envelope reported ``head_sha_verified: true`` for a HEAD the bot had declined to
# review. The record now exists, and neither matcher was edited to achieve it:
# both already branch on ``_refusal_record`` returning non-``None``.
#
# The arm ships INERT (D1 derived no threshold), so the firing cases arm it
# explicitly and the shipped behaviour is asserted separately.


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


#: A refusal reworded past both earlier arms: no registry marker, and no
#: limit-exceeded statement paired with a notice shape.
_UNRECOGNISED_REFUSAL = 'Not reviewing this one.'


def test_the_layer_vocabulary_has_one_definition_site_read_by_this_consumer():
    """``github_re_review`` READS the vocabulary; it does not declare its own.

    Identity is asserted against the DEFINING module as the SUT itself resolved it
    — ``_is_unrecognised_refusal.__globals__`` is the namespace ``_github_pr``
    actually executed in for this import graph. That is the harness-independent
    probe: comparing against a ``_github_pr`` this test module imported separately
    tests pytest's module loading, not the code, because the harness can execute the
    same file twice and produce two equal-but-distinct tuples.

    Identity against the right object is still what is wanted over equality: a
    parallel vocabulary declared here would compare equal while being a different
    object that drifts on the next edit — the two-sources-of-truth failure the
    shared constant exists to remove.
    """
    defining_namespace = github_re_review._is_unrecognised_refusal.__globals__

    assert github_re_review.REFUSAL_LAYERS is defining_namespace['REFUSAL_LAYERS']
    # And the values agree with the copy this test module resolved, so the two
    # import paths describe one vocabulary rather than two that merely coexist.
    assert list(github_re_review.REFUSAL_LAYERS) == list(_github_pr.REFUSAL_LAYERS)


def test_the_envelope_publishes_the_declared_layer_population(monkeypatch):
    """The envelope carries the vocabulary, and the population is non-empty.

    Publishing it is what lets a consumer validate a ``layer`` value against the
    producer's own declared set rather than a hand-copied list. The size is asserted
    so an emptied or shrunken vocabulary fails here instead of silently making every
    membership check below vacuous.
    """
    result = _await_with_comments(monkeypatch, [], bot_kind='sourcery')

    published = result['refusal_layers']
    assert published, 'the envelope published an empty layer vocabulary'
    assert len(published) == len(_github_pr.REFUSAL_LAYERS)
    assert published == list(_github_pr.REFUSAL_LAYERS)
    # All three named arms are members of the published population.
    for member in (
        _github_pr.REFUSAL_LAYER_REGISTRY,
        _github_pr.REFUSAL_LAYER_STRUCTURAL,
        _github_pr.REFUSAL_LAYER_ENUMERATIVE,
    ):
        assert member in published


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


def test_with_no_threshold_the_re_review_path_behaves_exactly_as_at_head(monkeypatch):
    """⛔ The fail-safe, asserted at the SHIPPED value: the arm cannot over-tighten.

    D1 derived no threshold, so ``_is_unrecognised_refusal`` returns ``False`` for
    every input and ``_refusal_record`` returns ``None`` for an unrecognised body —
    byte-identical to its behaviour before this deliverable. The unrecognised
    refusal is therefore still ADMITTED as a review here, which is the defect; it is
    asserted rather than hidden, because shipping an armed tightening on a bound
    nobody measured would block merges on no evidence. Arming the threshold is what
    turns the fix on, and that is a separate, evidence-gated decision.
    """
    assert github_re_review._is_unrecognised_refusal.__globals__['UNRECOGNISED_REFUSAL_MAX_CHARS'] is None

    assert github_re_review._ReReviewStrategy._refusal_record(_UNRECOGNISED_REFUSAL, 'sourcery', 'review') is None

    # The two-axis keys do NOT depend on the enumerative arm: at this same shipped
    # (inert) threshold a body an earlier arm recognises still carries both. Pinned
    # here so the keys cannot be mistaken for something the arm introduced.
    recognised = github_re_review._ReReviewStrategy._refusal_record(_SOURCERY_REFUSAL, 'sourcery', 'review')
    assert recognised is not None
    assert recognised['cause'] == _github_pr.REFUSAL_CAUSE_SIZE
    assert recognised['cap'] == '150000 characters'

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

    assert result['matched'] is True
    assert result['refusal_detected'] is False


@pytest.mark.parametrize(
    'body',
    [
        pytest.param(_SOURCERY_REFUSAL, id='registry-recognised'),
        pytest.param(_UNCAPTURED_SHAPED_REFUSAL, id='structurally-recognised'),
    ],
)
def test_a_body_an_earlier_arm_recognised_keeps_its_own_layer(body, monkeypatch):
    """Arming the third arm never re-labels a refusal an earlier arm already read.

    Run with the arm LIVE, so this is not a vacuous comparison against an inert
    predicate. The scope is deliberately bodies the earlier arms recognise: those
    verdicts are the ones the new arm must not disturb, because their layer carries
    real information about WHY the bot declined.
    """
    inert = github_re_review._ReReviewStrategy._refusal_record(body, 'sourcery', 'review')
    assert inert is not None, 'fixture must be recognised by an earlier arm'

    _arm_enumerative(monkeypatch)
    live = github_re_review._ReReviewStrategy._refusal_record(body, 'sourcery', 'review')

    assert live is not None
    assert live['layer'] == inert['layer']
    assert live['layer'] != _github_pr.REFUSAL_LAYER_ENUMERATIVE
    # Arming the third arm must not disturb the CAUSE axis either — the cause and
    # the stated ceiling are properties of the notice, not of which arm read it.
    assert live['cause'] == inert['cause']
    assert live['cap'] == inert['cap']


def test_an_armed_threshold_withholds_a_genuine_anchorless_review(monkeypatch):
    """⛔ The tightening's COST, asserted rather than assumed away.

    ``_GENUINE_REVIEW_BODY`` is a real review: it names a defect and prescribes a
    fix. It carries no code anchor and is shorter than this test's deliberately
    generous 200-character threshold, so the enumerative arm withholds it — a
    genuine review recorded as a refusal, which on the re-review path means the bot
    is treated as having declined.

    This is not a defect in the arm; it is the arm's documented failure direction,
    and it is what the threshold's DERIVATION exists to bound. The bound must be the
    shortest GENUINE review comment actually observed, so that no real review can
    fall below it. D1 measured a corpus containing zero such comments and therefore
    emitted NO threshold — and this test is the concrete reason that was the right
    call rather than a cautious one: a guessed bound of this size would withhold
    real review feedback and block merges on evidence nobody gathered.

    Pinned so the cost stays visible. If a future change derives a real threshold,
    this test should be re-expressed against it — and it will fail loudly if that
    threshold is set above a genuine review's length, which is exactly the guard
    wanted.
    """
    assert '`' not in _GENUINE_REVIEW_BODY
    assert len(_GENUINE_REVIEW_BODY) < 200

    _arm_enumerative(monkeypatch, max_chars=200)
    record = github_re_review._ReReviewStrategy._refusal_record(_GENUINE_REVIEW_BODY, 'sourcery', 'review')

    assert record is not None
    assert record['layer'] == _github_pr.REFUSAL_LAYER_ENUMERATIVE
    # An enumerative record read NOTHING about why the bot declined, so it claims no
    # ceiling: the cap is empty and the cause falls to the ``quota`` default rather
    # than asserting a size ceiling nobody observed.
    assert record['cap'] == ''
    assert record['cause'] == _github_pr.REFUSAL_CAUSE_QUOTA
    # The shipped (absent-threshold) behaviour for this same body is pinned by
    # ``test_with_no_threshold_the_re_review_path_behaves_exactly_as_at_head``; it is
    # deliberately not re-asserted here, where the arm is still armed.


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
    """cuioss-review-bot: posts /review, then awaits a fresh review for HEAD."""
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

    result = github_re_review.cmd_re_review(_re_review_args(bot_kind='cuioss-review-bot'))

    assert result['status'] == 'success'
    assert result['matched'] is True
    assert result['bot_kind'] == 'cuioss-review-bot'
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

    result = github_re_review.cmd_re_review(_re_review_args(bot_kind='cuioss-review-bot'))

    assert result['status'] == 'success'
    assert captured['bot_kind'] == 'cuioss-review-bot'


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
    """A failed cuioss-review-bot trigger post aborts before await is ever called."""
    _noop_sleep(monkeypatch)
    monkeypatch.setattr(
        github_re_review._github,
        'post_pr_comment',
        lambda *_a, **_kw: {'status': 'error', 'error': 'comment failed'},
    )

    def exploding_fetch(*_a, **_kw):  # pragma: no cover - must not run
        raise AssertionError('await must not run when request_fresh_review fails')

    monkeypatch.setattr(github_re_review._github, 'fetch_pr_reviews_with_commits', exploding_fetch)

    result = github_re_review.cmd_re_review(_re_review_args(bot_kind='cuioss-review-bot'))

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
    """The PR-Agent bot account login maps to the cuioss-review-bot bot_kind."""
    assert github_re_review.bot_kind_for_author('cuioss-review-bot') == 'cuioss-review-bot'


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


def _run_recovery_action(monkeypatch, capsys, *extra: str) -> dict:
    """Drive ``main()`` through the ``recovery-action`` verb; return the parsed TOON.

    The envelope is PARSED rather than substring-matched: every verdict publishes
    the whole ``recovery_actions`` vocabulary, so ``'escalate_not_awaitable' in
    out`` is true of every return this verb can make and would assert nothing.
    """
    from toon_parser import parse_toon

    monkeypatch.setattr(sys, 'argv', ['github_re_review.py', 'recovery-action', *extra])

    rc = github_re_review.main()

    assert rc == 0
    parsed = parse_toon(capsys.readouterr().out)
    assert isinstance(parsed, dict)
    return parsed


def test_main_recovery_action_accepts_an_unregistered_bot_kind(monkeypatch, capsys):
    """A STALE ``--bot-kind`` reaches the derivation instead of an argparse rejection.

    ``--bot-kind`` on this verb deliberately declares no ``choices=``. An operator
    holding a config token for a bot that has since been renamed or retired needs
    the fail-closed verdict WITH the live kind set published beside it; an
    argparse rejection would replace that answer with exit 2 and name no remedy.

    Paired with ``test_main_recovery_action_still_rejects_an_unknown_verb`` below,
    which shows a rejection is reachable in this harness at all — without it,
    "no ``SystemExit``" would be an assertion about nothing.
    """
    verdict = _run_recovery_action(monkeypatch, capsys, '--bot-kind', 'some-retired-bot')

    assert verdict['action'] == github_re_review.RECOVERY_ACTION_ESCALATE_NOT_AWAITABLE
    assert verdict['bot_kind_registered'] is False
    # The live kind set travels with the verdict — the remedy a stale token needs.
    assert verdict['known_bot_kind_count'] == len(bot_registry.bot_kinds())


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


def test_main_recovery_action_derives_a_registered_bots_verdict(monkeypatch, capsys):
    """MATCHED CONTROL — a REGISTERED kind travels the same verb to a real verdict.

    Without it the case above is consistent with a verb that answers
    ``escalate_not_awaitable`` for every input. Here the bot is registered and its
    refusal is a diff-SIZE one, which dominates the class and resolves the
    structural escalation instead.
    """
    bot_kind = bot_registry.bot_kinds()[0]

    verdict = _run_recovery_action(monkeypatch, capsys, '--bot-kind', bot_kind, '--cause', 'size')

    assert verdict['action'] == github_re_review.RECOVERY_ACTION_ESCALATE_STRUCTURAL
    assert verdict['bot_kind_registered'] is True


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

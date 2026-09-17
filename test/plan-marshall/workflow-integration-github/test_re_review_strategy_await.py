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


def _guide_body(sha: str) -> str:
    """The Guide body shape observed live, naming ``sha`` as the reviewed commit.

    Pinned as the OBSERVED wording rather than a synthetic "sha: <hex>" string: the
    permalink is how this bot actually reports its reviewed commit, and a fixture
    that invented an easier shape would prove the matcher handles a shape no bot
    emits. The heading is carried too, because the real comment is one persistent
    Guide that the bot EDITS — the body always arrives with it attached.
    """
    return f'## PR Reviewer Guide 🔍 (Review updated until commit https://github.com/cuioss/plan-marshall/commit/{sha})'


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
_UNRECOGNISED_REFUSAL = 'Not reviewing this one.'


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


def test_strategy_triggers_derive_from_bot_registry():
    """Every strategy's trigger equals the registry-declared trigger for its bot."""
    import bot_registry

    for bot_kind in bot_registry.bot_kinds():
        strategy = github_re_review.resolve_strategy(bot_kind)
        assert strategy is not None
        assert strategy.trigger_comment == bot_registry.trigger_comment(bot_kind)


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


def test_await_verifies_a_republished_comment_naming_the_awaited_head(monkeypatch):
    """POSITIVE: a comment whose body links the awaited HEAD reports ``head_sha_verified: true``.

    The body links the full SHA behind an abbreviated label, so the full SHA sits
    inside a commit URL in the body — the same location widening the review arm
    already applies, while the abbreviated label alone would not verify. No review
    is supplied, so only the comment arm can match and the verdict is attributable
    to the body alone.
    """
    result = _await_with_comments(
        monkeypatch, [_republished_comment(_VERIFYING_REFERENCE)], bot_kind='coderabbit', head_sha=_HEAD_SHA
    )

    assert result['matched'] is True
    assert result['matched_signal'] == 'issue_comment'
    assert result['head_sha_verified'] is True
    assert result['matched_review'] == {}
    assert result['refusal_detected'] is False


@pytest.mark.parametrize(
    'reference',
    [
        pytest.param(_NON_VERIFYING_REFERENCE, id='names-no-commit'),
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


@pytest.mark.parametrize(
    'verifying_first',
    [
        pytest.param(True, id='verifying-comment-first'),
        pytest.param(False, id='non-verifying-comment-first'),
    ],
)
def test_await_selects_the_head_verifying_comment_whatever_the_list_order(verifying_first, monkeypatch):
    """⛔ BOTH orders, because a first-match matcher passes one of them by accident.

    Two comments from the awaited bot, both clearing every eligibility gate — same
    author, same builder, both post-dating the trigger, neither a refusal — so the
    ONLY thing that can decide between them is the reference their bodies carry.
    Under a first-match matcher the non-verifying-comment-first order published
    ``head_sha_verified: false`` while a comment naming the current HEAD sat later
    in the same list: a manufactured decline that blocks a merge and steers the
    operator toward accepting it.

    Running only the verifying-comment-first order would certify nothing — the
    first-match implementation returns the verifying comment there too.
    """
    verifying = _republished_comment(_VERIFYING_REFERENCE, updated_at='2026-01-01T00:06:00Z')
    non_verifying = _republished_comment(_NON_VERIFYING_REFERENCE, updated_at='2026-01-01T00:05:00Z')
    comments = [verifying, non_verifying] if verifying_first else [non_verifying, verifying]

    result = _await_with_comments(monkeypatch, comments, bot_kind='coderabbit', head_sha=_HEAD_SHA)

    assert result['matched'] is True
    assert result['matched_signal'] == 'issue_comment'
    assert result['head_sha_verified'] is True
    # The SELECTED record is the verifying one, not merely a true verdict computed
    # off some other comment — the envelope hands this record to the caller.
    assert result['matched_comment']['body'] == verifying['body']


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


def test_a_refusal_naming_the_awaited_head_is_still_never_selected(monkeypatch):
    """⛔ The HEAD-verifying preference reorders ELIGIBLE comments; it re-admits no refusal.

    The sharpest probe of that boundary: this refusal body NAMES the awaited HEAD,
    so a preference applied ahead of the refusal gate would select it and report
    ``head_sha_verified: true`` for a review CodeRabbit explicitly declined — the
    false-green the refusal exclusion exists to prevent, reintroduced through the
    selection rather than through the gate.

    The genuine comment beside it names no commit, so the correct outcome is a
    match on THAT comment with ``head_sha_verified: false``, and the refusal
    recorded rather than swallowed.
    """
    refusal_naming_head = _comment(
        _CODERABBIT_LOGIN,
        created_at='2026-01-01T00:05:00Z',
        body=f'{_CODERABBIT_COMMAND_REPLY_REFUSAL} Review updated until commit {_HEAD_SHA}.',
    )
    genuine = _republished_comment(_NON_VERIFYING_REFERENCE, updated_at='2026-01-01T00:06:00Z')

    result = _await_with_comments(
        monkeypatch, [refusal_naming_head, genuine], bot_kind='coderabbit', head_sha=_HEAD_SHA
    )

    # The fixture is only a probe of the SELECTION if the refusal genuinely names
    # the awaited HEAD — otherwise the preference had nothing to be tempted by.
    assert github_re_review._references_head_sha(refusal_naming_head['body'], _HEAD_SHA) is True

    assert result['matched'] is True
    assert result['matched_signal'] == 'issue_comment'
    assert result['head_sha_verified'] is False
    assert result['matched_comment']['body'] == genuine['body']
    assert result['refusal_detected'] is True
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

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

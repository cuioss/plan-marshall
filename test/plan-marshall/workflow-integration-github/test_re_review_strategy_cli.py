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


def _guide_body(sha: str) -> str:
    """The Guide body shape observed live, naming ``sha`` as the reviewed commit.

    Pinned as the OBSERVED wording rather than a synthetic "sha: <hex>" string: the
    permalink is how this bot actually reports its reviewed commit, and a fixture
    that invented an easier shape would prove the matcher handles a shape no bot
    emits. The heading is carried too, because the real comment is one persistent
    Guide that the bot EDITS — the body always arrives with it attached.
    """
    return f'## PR Reviewer Guide 🔍 (Review updated until commit https://github.com/cuioss/plan-marshall/commit/{sha})'


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


def test_author_login_map_derives_from_bot_registry():
    """The login->bot_kind map is derived from the registry, not inline-copied."""
    import bot_registry

    assert github_re_review._AUTHOR_LOGIN_TO_BOT_KIND == bot_registry.login_to_bot_kind()


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


def test_cmd_re_review_unknown_bot_kind_errors():
    result = github_re_review.cmd_re_review(_re_review_args(bot_kind='copilot'))

    assert result['status'] == 'error'
    assert 'copilot' in result['error']


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


def test_bot_kind_for_author_human_returns_none():
    """A human (non-bot) author login resolves to None."""
    assert github_re_review.bot_kind_for_author('octocat') is None


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

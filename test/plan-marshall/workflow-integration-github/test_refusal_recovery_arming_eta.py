# SPDX-License-Identifier: FSL-1.1-ALv2
"""``bot_registry.trigger_semantics`` declarations and ``_extract_rate_limit_eta`` cases.

Every registered bot must DECLARE its trigger semantics (never merely inherit
them), with the unknown-bot fallback pinned; the ETA extractor covers the
declared phrasing shapes and cannot raise on adversarial bodies. The arming
rule itself (cause dominance, window arms, disclosure) lives in the co-located
arming suites; this module pins declarations and extraction only.

The bot population is DERIVED from ``bot_registry``, never hard-coded, so a bot
added or reclassified in a standards doc is swept here automatically.

The reset time is pinned three ways: the text the extractor reads off the notice
CodeRabbit posts ("Next included review available in 38 minutes."), that time as
the seconds a rate window is claimed with (``2280``), and the record's own
``eta_extracted`` statement when a refusal states no time at all. A sweep over
every refusal fixture body in this directory fails when a body that states a
duration yields no reset time.
"""

from __future__ import annotations

import ast
import importlib
import re
from pathlib import Path

importlib.import_module('github_ops')
import _github_pr  # noqa: E402
import bot_registry  # noqa: E402
import github_re_review  # noqa: E402
import pytest  # noqa: E402
from _github_pr import (  # noqa: E402
    REFUSAL_LAYER_REGISTRY,
    REFUSAL_LAYER_STRUCTURAL,
    REFUSAL_LAYERS,
    _detect_rate_limited_bots,
    _extract_rate_limit_eta,
    _is_refusal_notice,
    rate_limit_eta_seconds,
    refusal_layers,
)
from _github_pr_fixtures import (  # noqa: E402
    CODERABBIT_NEXT_REVIEW_NOTICE_COUNT,
    CODERABBIT_NEXT_REVIEW_NOTICES,
    CODERABBIT_NOTICE_STATING_NO_RESET_TIME,
    QUOTA_NOTICE_BOT_KIND,
)

from conftest import get_script_path  # noqa: E402

_ATTEMPTS_REMAINING = 2
_STRUCTURAL_NOTICE_BODY = (
    '> [!WARNING] > ## Usage limit reached > '
    'This reviewer has reached its usage limit. Reviews will resume after the limit resets.'
)
_DECLARED_WORDING_PAIRS: list[tuple[str, str]] = [
    (bot_kind, pattern) for bot_kind in bot_registry.bot_kinds() for pattern in bot_registry.refusal_patterns(bot_kind)
]
_DECLARED_WORDING_POPULATION_SIZE = len(_DECLARED_WORDING_PAIRS)
_DECLARED_WORDING_POPULATION_BASELINE = 7


def _registered_bots() -> list[str]:
    bots = bot_registry.bot_kinds()
    assert bots, 'registry must declare at least one bot'
    return bots


_PRODUCER_ONLY_FIELDS = {'rate_limited_bots': {'rate_limit_class'}, 'refusals': {'source'}}
_AR_SKILL = (
    get_script_path('plan-marshall', 'workflow-integration-github', '_github_pr.py').parents[4]
    / 'plan-marshall'
    / 'skills'
    / 'automatic-review'
    / 'SKILL.md'
)
_DISCLOSED = {'producer', 'layer', 'eta', 'eta_extracted', 'body'}
_LOGGED = _DISCLOSED - {'body'}


class TestTriggerSemanticsIsDeclaredByEveryBot:
    """Every registered bot declares a value from the CLOSED trigger-semantics set."""

    def test_every_registered_bot_declares_a_value_in_the_closed_set(self):
        """Registry-derived: the population is the bot set, the set is the vocabulary.

        Both sides derived — the bots from ``bot_kinds()`` and the admissible values
        from ``TRIGGER_SEMANTICS_VALUES`` — so neither a new bot nor a new value can
        leave this assertion silently stale.
        """
        assert bot_registry.TRIGGER_SEMANTICS_VALUES, 'the vocabulary is empty'

        for bot in _registered_bots():
            assert bot_registry.trigger_semantics(bot) in bot_registry.TRIGGER_SEMANTICS_VALUES

    def test_the_declared_value_is_read_from_the_doc_not_the_fail_closed_default(self):
        """⛔ Matched control: proves the docs DECLARE it rather than defaulting.

        Every shipped bot declares ``requires_explicit_trigger``, which is also the
        fail-closed default — so the sweep above passes identically on three docs
        that declare nothing at all. Reading the RAW parsed record is what
        discriminates a real declaration from an absent one.
        """
        for bot in _registered_bots():
            raw = bot_registry.REGISTRY._by_kind.get(bot, {}).get('trigger_semantics')
            assert isinstance(raw, str) and raw.strip(), (
                f'{bot} does not DECLARE trigger_semantics — it is only inheriting the '
                f'fail-closed default, which this test exists to distinguish'
            )

    def test_an_unregistered_bot_fails_closed_to_requires_explicit_trigger(self):
        """The safe direction: never assume a bot reviews on push."""
        assert bot_registry.trigger_semantics('no-such-bot') == bot_registry.TRIGGER_SEMANTICS_REQUIRES_EXPLICIT_TRIGGER

    def test_a_value_outside_the_closed_set_fails_closed(self, monkeypatch):
        """A malformed doc edit degrades safely rather than propagating a bad value."""
        bot = _registered_bots()[0]
        record = dict(bot_registry.REGISTRY._by_kind[bot])
        record['trigger_semantics'] = 'sometimes_maybe'
        monkeypatch.setitem(bot_registry.REGISTRY._by_kind, bot, record)

        assert bot_registry.trigger_semantics(bot) == bot_registry.TRIGGER_SEMANTICS_REQUIRES_EXPLICIT_TRIGGER


class TestTheEtaExtractorCannotRaise:
    """A registry pattern that COMPILES but captures nothing must not crash the poll.

    ``match.groups()`` is truthy for a one-tuple holding ``None``, so a pattern whose
    declared group sits in a branch that did not participate matched, reported
    groups, and yielded ``None`` — and ``.strip()`` on that raised an AttributeError
    out of the producer's whole return path. The ``re.error`` guard does not cover
    it: that guard catches a pattern that will not COMPILE, not one that compiles and
    captures nothing.
    """

    _BODY = 'Usage limit reached. Try again in 18 minutes.'

    def test_a_declared_group_that_captured_nothing_yields_no_eta(self, monkeypatch):
        """The crash case: the first branch matches, the group is in the second."""
        monkeypatch.setattr(bot_registry, 'rate_limit_eta_patterns', lambda _kind: [r'limit reached|(ZZZ)'])

        for bot in _registered_bots():
            # The assertion is that this RETURNS at all — pre-fix it raised.
            assert _extract_rate_limit_eta(self._BODY, bot) == ''

    def test_an_empty_group_moves_to_the_next_pattern_never_to_group_zero(self, monkeypatch):
        """No fallback from an empty group to the whole match.

        The group(0) fallback is the wrong kind of graceful: it would return the
        prose ``"limit reached"`` as though the notice had stated that as its ETA.
        The honest behaviour is to yield nothing and let the NEXT pattern answer,
        which is what this pins — the returned figure is the second pattern's.
        """
        monkeypatch.setattr(
            bot_registry,
            'rate_limit_eta_patterns',
            lambda _kind: [r'limit reached|(ZZZ)', r'in ([0-9]+ minutes)'],
        )

        for bot in _registered_bots():
            assert _extract_rate_limit_eta(self._BODY, bot) == '18 minutes'

    def test_the_matched_control_a_capturing_pattern_still_yields_its_figure(self, monkeypatch):
        """Matched positive control: the fix did not simply disable extraction."""
        monkeypatch.setattr(bot_registry, 'rate_limit_eta_patterns', lambda _kind: [r'in ([0-9]+ minutes)'])

        for bot in _registered_bots():
            assert _extract_rate_limit_eta(self._BODY, bot) == '18 minutes'

    def test_a_group_less_pattern_still_returns_the_whole_match(self, monkeypatch):
        """The no-group convention is preserved — group(0) remains the answer there."""
        monkeypatch.setattr(bot_registry, 'rate_limit_eta_patterns', lambda _kind: [r'[0-9]+ minutes'])

        for bot in _registered_bots():
            assert _extract_rate_limit_eta(self._BODY, bot) == '18 minutes'


def _bot_comment(bot_kind: str, body: str) -> dict:
    """A comment by ``bot_kind``, authored through the registry's own login map."""
    logins = [login for login, kind in bot_registry.login_to_bot_kind().items() if kind == bot_kind]
    assert logins, f'{bot_kind} declares no author_login'
    return {'author': f'{logins[0]}[bot]', 'body': body, 'created_at': '2026-01-09T00:00:00Z'}


class TestTheResetTimeCodeRabbitStatesIsRead:
    """The review-summary notice's "Next included review available in ..." is extracted.

    Before the wording was declared the extractor read nothing from this notice, so
    the recovery claimed its default window of an hour for a limit the bot had said
    would lift in 38 minutes.
    """

    def test_the_thirty_eight_minute_notice_yields_thirty_eight_minutes(self):
        """The case as the bot posts it — the bare sentence, nothing around it."""
        body = 'Next included review available in 38 minutes.'

        assert _extract_rate_limit_eta(body, QUOTA_NOTICE_BOT_KIND) == '38 minutes'

    def test_the_window_claimed_for_that_notice_is_2280_seconds_not_an_hour(self):
        """The figure the claim is made with comes off the record, not from arithmetic."""
        body, _eta, _seconds = CODERABBIT_NEXT_REVIEW_NOTICES[0]
        assert 'Next included review available in 38 minutes.' in body

        [record] = _detect_rate_limited_bots([_bot_comment(QUOTA_NOTICE_BOT_KIND, body)])

        assert record['eta'] == '38 minutes'
        assert record['eta_seconds'] == 2280
        assert record['eta_seconds'] != 3600
        assert record['eta_extracted'] is True

    def test_the_notice_population_is_published(self):
        """The parametrized cases below run over a stated, non-empty population."""
        assert CODERABBIT_NEXT_REVIEW_NOTICE_COUNT == len(CODERABBIT_NEXT_REVIEW_NOTICES)
        assert CODERABBIT_NEXT_REVIEW_NOTICE_COUNT >= 3, 'the minute, hour and compound forms must all be present'

    @pytest.mark.parametrize(
        ('body', 'stated', 'seconds'),
        CODERABBIT_NEXT_REVIEW_NOTICES,
        ids=[stated for _body, stated, _seconds in CODERABBIT_NEXT_REVIEW_NOTICES],
    )
    def test_each_stated_form_is_read_as_text_and_as_seconds(self, body, stated, seconds):
        """The minute, hour and compound forms each yield their own figure."""
        assert _extract_rate_limit_eta(body, QUOTA_NOTICE_BOT_KIND) == stated
        assert rate_limit_eta_seconds(stated) == seconds

    @pytest.mark.parametrize(
        ('body', 'stated', 'seconds'),
        CODERABBIT_NEXT_REVIEW_NOTICES,
        ids=[stated for _body, stated, _seconds in CODERABBIT_NEXT_REVIEW_NOTICES],
    )
    def test_both_producers_carry_the_same_reset_time_for_one_notice(self, body, stated, seconds):
        """``rate_limited_bots[]`` and ``refusals[]`` state one time, three ways each."""
        [detected] = _detect_rate_limited_bots([_bot_comment(QUOTA_NOTICE_BOT_KIND, body)])
        refusal = github_re_review._ReReviewStrategy._refusal_record(body, QUOTA_NOTICE_BOT_KIND, 'issue_comment')

        assert refusal is not None
        for record in (detected, refusal):
            assert record['eta'] == stated
            assert record['eta_seconds'] == seconds
            assert record['eta_extracted'] is True


class TestTheStatedResetTimeAsSeconds:
    """``rate_limit_eta_seconds`` converts the extracted text, and never invents a zero."""

    @pytest.mark.parametrize(
        ('eta', 'seconds'),
        [
            ('38 minutes', 2280),
            ('1 minute', 60),
            ('45 seconds', 45),
            ('2 hours', 7200),
            ('12 minutes and 30 seconds', 750),
            ('1 hour and 5 minutes', 3900),
            ('3 days and 17 hours', 320400),
        ],
    )
    def test_a_stated_duration_is_summed_over_every_term(self, eta, seconds):
        assert rate_limit_eta_seconds(eta) == seconds

    @pytest.mark.parametrize('eta', ['', 'soon', 'unknown', 'after the limit resets'])
    def test_text_stating_no_duration_is_none_never_zero(self, eta):
        """``None`` is the unread reading; a zero would be a reset time nobody stated."""
        assert rate_limit_eta_seconds(eta) is None

    def test_a_stated_zero_is_a_real_duration(self):
        """Matched control: zero is returned when the text states it, and only then."""
        assert rate_limit_eta_seconds('0 minutes') == 0


class TestARefusalStatingNoResetTimeSaysSo:
    """``eta_extracted: false`` is the record's own statement that nothing was read."""

    def test_the_fixture_is_a_recognised_refusal_that_states_no_duration(self):
        """Fixture control: the case below is about extraction, not about detection."""
        body = CODERABBIT_NOTICE_STATING_NO_RESET_TIME

        assert _is_refusal_notice(body, QUOTA_NOTICE_BOT_KIND) is True
        assert _STATES_A_DURATION.search(body) is None

    def test_the_detector_record_reports_eta_extracted_false(self):
        [record] = _detect_rate_limited_bots(
            [_bot_comment(QUOTA_NOTICE_BOT_KIND, CODERABBIT_NOTICE_STATING_NO_RESET_TIME)]
        )

        assert record['eta'] == ''
        assert record['eta_seconds'] is None
        assert record['eta_extracted'] is False

    def test_the_re_review_record_reports_eta_extracted_false(self):
        record = github_re_review._ReReviewStrategy._refusal_record(
            CODERABBIT_NOTICE_STATING_NO_RESET_TIME, QUOTA_NOTICE_BOT_KIND, 'issue_comment'
        )

        assert record is not None
        assert record['eta'] == ''
        assert record['eta_seconds'] is None
        assert record['eta_extracted'] is False

    @pytest.mark.parametrize('bot_kind', _registered_bots())
    def test_every_detected_refusal_carries_both_fields_and_they_agree(self, bot_kind):
        """Swept over the registry: the two fields are present and never contradict."""
        [record] = _detect_rate_limited_bots([_bot_comment(bot_kind, _STRUCTURAL_NOTICE_BODY)])

        assert isinstance(record['eta_extracted'], bool)
        assert record['eta_extracted'] is (record['eta_seconds'] is not None)


_FIXTURE_DIR = Path(__file__).resolve().parent

#: "A digit followed by minute, hour or second" — the body states a duration.
_STATES_A_DURATION = re.compile(r'[0-9]\s*(?:minute|hour|second)', re.IGNORECASE)


def _string_constant(node: ast.expr | None) -> str:
    """The value of a string-literal node, or ``''`` for anything else."""
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else ''


def _skipped_constants(tree: ast.AST) -> set[int]:
    """Ids of string constants that are not fixture bodies: docstrings and body fragments.

    A docstring describes fixtures in prose. An f-string part and an operand of a
    ``+`` / ``*`` expression are each only a fragment of the body the expression
    builds, so none of them is a body a bot could have posted.
    """
    skipped: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            if node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant):
                skipped.add(id(node.body[0].value))
        elif isinstance(node, ast.JoinedStr):
            skipped.update(id(part) for part in node.values)
        elif isinstance(node, ast.BinOp):
            skipped.update((id(node.left), id(node.right)))
    return skipped


def _refusal_fixture_bodies() -> list[tuple[str, str]]:
    """Every ``(bot_kind, body)`` refusal fixture in this directory's test modules.

    A body is attributed to a bot in one of two ways, both read off the source:

    - a dict literal carrying a constant ``author`` and a constant ``body`` is that
      author's comment, whichever arm recognises it;
    - any other string literal that a bot's own declared ``refusal_patterns`` match
      is that bot's notice.

    Only pairs some pre-noise-filter arm recognises as a refusal are kept.
    """
    pairs: set[tuple[str, str]] = set()
    bots = bot_registry.bot_kinds()
    for path in sorted(_FIXTURE_DIR.glob('*.py')):
        tree = ast.parse(path.read_text(encoding='utf-8'))
        skipped = _skipped_constants(tree)
        for node in ast.walk(tree):
            if isinstance(node, ast.Dict):
                entries = {
                    key.value: value
                    for key, value in zip(node.keys, node.values, strict=True)
                    if isinstance(key, ast.Constant) and isinstance(key.value, str)
                }
                author = _string_constant(entries.get('author'))
                body = _string_constant(entries.get('body'))
                bot = github_re_review.bot_kind_for_author(author) if author and body else None
                if bot:
                    pairs.add((bot, body))
            elif isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in skipped:
                for bot in bots:
                    if REFUSAL_LAYER_REGISTRY in refusal_layers(node.value, bot):
                        pairs.add((bot, node.value))
    return sorted(pair for pair in pairs if refusal_layers(pair[1], pair[0]))


_REFUSAL_FIXTURE_BODIES = _refusal_fixture_bodies()
_DURATION_STATING_FIXTURE_BODIES = [pair for pair in _REFUSAL_FIXTURE_BODIES if _STATES_A_DURATION.search(pair[1])]


class TestEveryRefusalFixtureStatingADurationYieldsAResetTime:
    """No refusal fixture in this directory states a duration the extractor cannot read.

    The population is every refusal body the directory's test modules declare, so a
    fixture added for a newly observed notice is swept without an edit here. A body
    that states "N minutes" and yields an empty reset time is the defect: the
    recovery then claims its default window for a limit the notice had timed.
    """

    def test_the_swept_populations_are_non_empty_and_published(self):
        """⛔ Vacuity guard: a sweep over nothing would report clean."""
        assert _REFUSAL_FIXTURE_BODIES, 'no refusal fixture body was found in this directory'
        assert _DURATION_STATING_FIXTURE_BODIES, 'no refusal fixture body states a duration'
        assert len(_DURATION_STATING_FIXTURE_BODIES) <= len(_REFUSAL_FIXTURE_BODIES)

    def test_the_new_notice_bodies_are_inside_the_swept_population(self):
        """Derivation control: the scan reaches the fixtures module, not only this one."""
        for body, _stated, _seconds in CODERABBIT_NEXT_REVIEW_NOTICES:
            assert (QUOTA_NOTICE_BOT_KIND, body) in _DURATION_STATING_FIXTURE_BODIES

    def test_a_refusal_fixture_stating_no_duration_is_outside_the_duration_subset(self):
        """Matched control: the duration filter excludes, it does not admit everything."""
        pair = (QUOTA_NOTICE_BOT_KIND, CODERABBIT_NOTICE_STATING_NO_RESET_TIME)

        assert pair in _REFUSAL_FIXTURE_BODIES
        assert pair not in _DURATION_STATING_FIXTURE_BODIES

    @pytest.mark.parametrize(
        ('bot_kind', 'body'),
        _DURATION_STATING_FIXTURE_BODIES,
        ids=[f'{bot}-{index}' for index, (bot, _body) in enumerate(_DURATION_STATING_FIXTURE_BODIES)],
    )
    def test_a_body_stating_a_duration_yields_a_reset_time(self, bot_kind, body):
        """The stated time is read, and it converts to seconds."""
        eta = _extract_rate_limit_eta(body, bot_kind)

        assert eta != '', f'{bot_kind} notice states a duration the extractor did not read: {body!r}'
        assert rate_limit_eta_seconds(eta) is not None, (bot_kind, eta)

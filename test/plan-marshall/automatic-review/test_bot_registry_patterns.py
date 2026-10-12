#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for automatic-review/scripts/bot_registry.py — the data-not-code bot loader.

The registry parses each ``automatic-review/standards/{bot_kind}.md`` fenced-YAML
data block ONCE and exposes stable accessors so the finding store, the re-review
strategy registry, the producer pre-filter, and the rate-limit detector DERIVE
what they need instead of hard-coding the shipped bot set across several code
files. Three bots ship today
(``coderabbit``, ``cuioss-review-bot``, ``sourcery``), and that count is asserted from
:data:`_SHIPPED_BOTS` rather than restated per test.

Coverage:

1. Shipped-standards contract — the real ``standards/*.md`` docs parse into the
   expected bot set, login map, triggers, skip-label flags, ignore patterns,
   acknowledgment patterns, contentless-review / actionable-content markers, per-shape
   participation-evidence content markers, rate-limit classes, rate-limit ETA
   patterns, and severity maps.
2. Derived ``BOT_KINDS`` — ``_findings_core.BOT_KINDS`` equals the registry's
   ``bot_kinds()`` (proving it is derived, not a literal).
3. Constrained-YAML reader units — the scalar/comment/block parsers over
   synthetic blocks, including quoted values carrying ``#`` and ``:``.
4. Robustness — a missing or empty standards directory yields an empty registry
   rather than raising; unknown bot kinds return empty defaults.
5. Load-time record validation — a non-map ``participation_evidence_markers``
   declaration, a key outside the record's own ``participation_evidence``, and a
   blank or non-string marker value all raise ``BotRegistryError``. The one place
   the permissive reader is checked rather than tolerated, because that field is
   the one whose malformation disables a gate SILENTLY.

Module import resolves via the root conftest's marketplace PYTHONPATH setup
(``import bot_registry``).
"""

import re

import bot_registry
import pytest

# The bots shipped as standards docs in this skill.
_SHIPPED_BOTS = ['coderabbit', 'cuioss-review-bot', 'sourcery']


# =============================================================================
# 1. Shipped-standards contract (the real standards/*.md docs)
# =============================================================================


def test_severity_map_per_bot():
    """Each bot's marker->severity map is parsed as a nested mapping."""
    coderabbit = bot_registry.severity_map('coderabbit')
    assert coderabbit['nitpick'] == 'low'
    assert coderabbit['potential_issue_critical'] == 'critical'

    sourcery = bot_registry.severity_map('sourcery')
    assert sourcery['security'] == 'critical'

    # PR-Agent's map is an ASSIGNMENT map keyed on the review-table row a finding
    # came from — the observed review emits no severity vocabulary to parse. All
    # three keys are asserted so a dropped row is caught, not just the first.
    pr_agent = bot_registry.severity_map('cuioss-review-bot')
    assert pr_agent == {'security_concern': 'high', 'focus_area': 'medium', 'missing_tests': 'low'}


def test_rate_limit_class_per_bot():
    """Each bot's rate-limit class is read from its data block, per OBSERVED evidence.

    The class is what a caller branches on before deciding to wait out a refusal:
    an ``awaitable_window`` reopens on its own, a ``hard_quota`` does not reopen on
    a useful timescale, and ``unknown`` records that no refusal has ever been seen
    for that bot. The three shipped bots deliberately span all three values.
    """
    assert bot_registry.rate_limit_class('coderabbit') == 'awaitable_window'
    assert bot_registry.rate_limit_class('sourcery') == 'hard_quota'
    assert bot_registry.rate_limit_class('cuioss-review-bot') == 'unknown'


def test_rate_limit_class_fails_closed_for_absent_field(tmp_path):
    """A record that declares no class reads as ``unknown``, never as awaitable.

    ADR-009 fail-closed: assuming an undeclared refusal is waitable is the
    expensive failure — the caller burns its whole await budget and still times
    out. The default must therefore be the value that suppresses the await.
    """
    (tmp_path / 'demo.md').write_text('```yaml\nbot_kind: demo\nauthor_login: demo-bot\n```\n', encoding='utf-8')
    reg = bot_registry.BotRegistry(standards_dir=tmp_path)

    assert reg.rate_limit_class('demo') == 'unknown'


def test_refusal_size_patterns_mark_the_diff_size_cause():
    """``refusal_size_patterns`` overlays the diff-SIZE cause onto ``refusal_patterns``.

    The orthogonal CAUSE axis to ``rate_limit_class`` (awaitability): which of a bot's
    refusals is caused by the diff being too big (remedy: a smaller diff) rather than a
    rate/budget quota (remedy: backoff). Sourcery declares two size-caused refusals —
    its own per-PR character ceiling, and the GitHub API's per-PR FILE-COUNT ceiling it
    reports as an inability to fetch — and both ALSO appear in ``refusal_patterns``
    (detection stays that field's job). Both of its account-quota wordings are
    deliberately absent here, so both classify ``quota``.

    CodeRabbit declares one, and it is the reason the two axes cannot be collapsed: its
    ``rate_limit_class`` is ``awaitable_window``, yet its file-count skip is not
    awaitable at all. A file count does not fall while you wait.
    """
    sourcery_size = bot_registry.refusal_size_patterns('sourcery')
    assert sourcery_size == [
        'your pull request is larger than the review limit of',
        'does not allow us to fetch diffs exceeding',
    ]
    # Every size marker is a genuine subset overlay — each is also a detection pattern.
    for size_marker in sourcery_size:
        assert size_marker in bot_registry.refusal_patterns('sourcery')
    # Both account-quota wordings are refusals but NOT a size cause. The second is the
    # *used* phrasing, which the structural recogniser cannot see either.
    for quota_marker in ('reached your weekly rate limit of', 'used your own review budget of'):
        assert quota_marker in bot_registry.refusal_patterns('sourcery')
        assert quota_marker not in sourcery_size

    # CodeRabbit's file-count skip is size-caused even though its class is awaitable.
    coderabbit_size = bot_registry.refusal_size_patterns('coderabbit')
    assert coderabbit_size == ['Too many files!']
    assert coderabbit_size[0] in bot_registry.refusal_patterns('coderabbit')
    assert bot_registry.rate_limit_class('coderabbit') == 'awaitable_window'
    for quota_marker in ('Review limit reached', 'Review rate limited'):
        assert quota_marker in bot_registry.refusal_patterns('coderabbit')
        assert quota_marker not in coderabbit_size

    assert bot_registry.refusal_size_patterns('cuioss-review-bot') == []


def test_refusal_size_patterns_absent_is_empty():
    """A record that declares no size patterns reads as ``[]`` — every refusal is quota."""
    reg = bot_registry.BotRegistry(standards_dir=bot_registry.STANDARDS_DIR)
    assert reg.refusal_size_patterns('nonexistent-bot') == []


def test_refusal_size_patterns_is_a_subset_of_refusal_patterns_for_every_bot():
    """Every declared size marker is also a detection marker — the subset invariant.

    ``refusal_size_patterns`` is a CAUSE overlay on ``refusal_patterns``, never a
    second detection list: a marker that names a refusal's cause as size but is absent
    from ``refusal_patterns`` would attribute a cause to a refusal the detection layer
    never recognizes. Derived over the WHOLE live bot population so a future registry
    edit that adds a size marker outside the refusal set fails here rather than
    silently reclassifying a quota refusal as size.

    Non-vacuity: at least one shipped bot must declare a size marker, or the subset
    assertion is vacuously true and the guard proves nothing.
    """
    kinds = bot_registry.bot_kinds()
    assert kinds, 'the registry declares no bots — the sweep would be vacuous'

    total_size_markers = 0
    for kind in kinds:
        size = bot_registry.refusal_size_patterns(kind)
        refusal = bot_registry.refusal_patterns(kind)
        total_size_markers += len(size)
        assert set(size) <= set(refusal), (
            f'{kind}: refusal_size_patterns {size} is not a subset of refusal_patterns '
            f'{refusal} — a size marker must also be a detection marker'
        )

    assert total_size_markers > 0, (
        'no shipped bot declares a size marker — the subset assertion above is '
        'vacuously true; the population-derived guard needs at least one to bite'
    )


def test_acknowledgment_patterns_per_bot():
    """Only CodeRabbit declares acknowledgment replies; the other two read empty.

    The two literals are the wordings of the ONE command reply CodeRabbit posts to
    ``@coderabbitai review`` and then edits in place. The other bots' records were not
    edited, so the field reads as its default for them and nothing they post is
    classified an acknowledgment.
    """
    assert bot_registry.acknowledgment_patterns('coderabbit') == ['Review triggered', 'Review finished']
    assert bot_registry.acknowledgment_patterns('cuioss-review-bot') == []
    assert bot_registry.acknowledgment_patterns('sourcery') == []


def test_acknowledgment_patterns_cover_every_shipped_bot_with_exactly_one_declarer():
    """The per-bot assertions above account for the WHOLE shipped population.

    Derived from the registry rather than from the three names above, so a bot added
    later is not silently outside the claim that only one bot declares the field.
    """
    kinds = bot_registry.bot_kinds()
    assert sorted(kinds) == sorted(_SHIPPED_BOTS)

    declarers = [kind for kind in kinds if bot_registry.acknowledgment_patterns(kind)]

    assert declarers == ['coderabbit']


def test_acknowledgment_patterns_absent_is_empty(tmp_path):
    """A record that declares no acknowledgments, and an unknown bot, both read ``[]``."""
    (tmp_path / 'demo.md').write_text('```yaml\nbot_kind: demo\nauthor_login: demo-bot\n```\n', encoding='utf-8')
    reg = bot_registry.BotRegistry(standards_dir=tmp_path)

    assert reg.acknowledgment_patterns('demo') == []
    assert reg.acknowledgment_patterns('nonexistent-bot') == []
    assert bot_registry.acknowledgment_patterns('nonexistent-bot') == []


def test_acknowledgment_patterns_parse_from_a_declared_block(tmp_path):
    """MATCHED CONTROL for the case above: the same reader returns a declared list."""
    (tmp_path / 'demo.md').write_text(
        '```yaml\nbot_kind: demo\nauthor_login: demo-bot\nacknowledgment_patterns:\n'
        '  - "Command received"   # the reply while the command runs\n'
        '  - "Command finished"\n```\n',
        encoding='utf-8',
    )
    reg = bot_registry.BotRegistry(standards_dir=tmp_path)

    assert reg.acknowledgment_patterns('demo') == ['Command received', 'Command finished']


def test_acknowledgment_patterns_returns_a_copy():
    """Mutating the returned list must not edit the registry's own record."""
    first = bot_registry.acknowledgment_patterns('coderabbit')
    first.append('planted')

    assert 'planted' not in bot_registry.acknowledgment_patterns('coderabbit')


def test_an_acknowledgment_literal_is_neither_a_refusal_nor_an_ignore_marker():
    """The three lists answer different questions, so no literal may sit in two of them.

    An acknowledgment that was also a ``refusal_patterns`` entry would be reported as
    a decline, and one that was also an ``ignore_patterns`` entry would be a section
    of a successful review. Swept over the whole live population; the non-vacuity
    check keeps the sweep from passing over zero literals.
    """
    kinds = bot_registry.bot_kinds()
    assert kinds, 'the registry declares no bots — the sweep would be vacuous'

    total = 0
    for kind in kinds:
        acknowledgments = bot_registry.acknowledgment_patterns(kind)
        total += len(acknowledgments)
        for literal in acknowledgments:
            assert isinstance(literal, str) and literal.strip(), f'{kind}: blank acknowledgment literal'
            assert all(literal not in refusal for refusal in bot_registry.refusal_patterns(kind)), (
                f'{kind}: acknowledgment literal {literal!r} is contained in a refusal pattern'
            )
            assert all(literal not in marker for marker in bot_registry.ignore_patterns(kind)), (
                f'{kind}: acknowledgment literal {literal!r} is contained in an ignore pattern'
            )

    assert total > 0, 'no shipped bot declares an acknowledgment literal — the sweep above is vacuous'


def test_escalated_trigger_comment_per_bot():
    """Only CodeRabbit declares a command that re-reviews the whole changeset.

    The inline comment on the declaring line is stripped by the reader, so the value
    is the command alone — it is posted verbatim.
    """
    assert bot_registry.escalated_trigger_comment('coderabbit') == '@coderabbitai full review'
    assert bot_registry.escalated_trigger_comment('cuioss-review-bot') == ''
    assert bot_registry.escalated_trigger_comment('sourcery') == ''


def test_the_escalated_command_differs_from_the_ordinary_trigger_for_every_declarer():
    """An escalated command equal to the ordinary trigger would repeat the refused request."""
    declarers = [kind for kind in bot_registry.bot_kinds() if bot_registry.escalated_trigger_comment(kind)]
    assert declarers, 'no shipped bot declares an escalated command — the sweep below is vacuous'

    for kind in declarers:
        assert bot_registry.escalated_trigger_comment(kind).strip() != bot_registry.trigger_comment(kind).strip()


def test_no_unreviewed_commit_patterns_per_bot():
    """CodeRabbit's two "nothing new to review" literals parse; the other two read empty."""
    assert bot_registry.no_unreviewed_commit_patterns('coderabbit') == [
        'Already reviewed the last commit',
        'No new commits to review',
    ]
    assert bot_registry.no_unreviewed_commit_patterns('cuioss-review-bot') == []
    assert bot_registry.no_unreviewed_commit_patterns('sourcery') == []


def test_no_unreviewed_commit_patterns_is_a_subset_of_refusal_patterns_for_every_bot():
    """The condition overlay never names a literal the detection list does not carry.

    Swept over the whole live population; the non-vacuity check keeps the subset
    assertion from passing over zero literals.
    """
    kinds = bot_registry.bot_kinds()
    assert sorted(kinds) == sorted(_SHIPPED_BOTS)

    total = 0
    for kind in kinds:
        overlay = bot_registry.no_unreviewed_commit_patterns(kind)
        total += len(overlay)
        assert set(overlay) <= set(bot_registry.refusal_patterns(kind)), kind
        # A reply cannot be both a diff-size refusal and a "nothing new" reply.
        assert not set(overlay) & set(bot_registry.refusal_size_patterns(kind)), kind

    assert total > 0, 'no shipped bot declares a no-unreviewed-commit literal — the sweep above is vacuous'


def test_the_new_fields_absent_read_as_empty(tmp_path):
    """A record declaring neither field, and an unknown bot, read ``''`` and ``[]``."""
    (tmp_path / 'demo.md').write_text('```yaml\nbot_kind: demo\nauthor_login: demo-bot\n```\n', encoding='utf-8')
    reg = bot_registry.BotRegistry(standards_dir=tmp_path)

    assert reg.escalated_trigger_comment('demo') == ''
    assert reg.no_unreviewed_commit_patterns('demo') == []
    assert bot_registry.escalated_trigger_comment('nonexistent-bot') == ''
    assert bot_registry.no_unreviewed_commit_patterns('nonexistent-bot') == []


def test_the_new_fields_parse_from_a_declared_block(tmp_path):
    """MATCHED CONTROL for the case above: the same reader returns the declared values."""
    (tmp_path / 'demo.md').write_text(
        '```yaml\nbot_kind: demo\nauthor_login: demo-bot\n'
        'trigger_comment: "@demo review"\n'
        'escalated_trigger_comment: "@demo full review"   # the whole changeset\n'
        'refusal_patterns:\n'
        '  - "Quota used up"\n'
        '  - "Nothing left to look at"\n'
        'no_unreviewed_commit_patterns:\n'
        '  - "Nothing left to look at"\n```\n',
        encoding='utf-8',
    )
    reg = bot_registry.BotRegistry(standards_dir=tmp_path)

    assert reg.escalated_trigger_comment('demo') == '@demo full review'
    assert reg.no_unreviewed_commit_patterns('demo') == ['Nothing left to look at']


def test_a_no_unreviewed_commit_literal_outside_refusal_patterns_is_dropped(tmp_path):
    """The overlay cannot assert its condition on a reply detection never recognises."""
    (tmp_path / 'demo.md').write_text(
        '```yaml\nbot_kind: demo\nauthor_login: demo-bot\n'
        'refusal_patterns:\n'
        '  - "Nothing left to look at"\n'
        'no_unreviewed_commit_patterns:\n'
        '  - "Nothing left to look at"\n'
        '  - "Declared here and nowhere else"\n```\n',
        encoding='utf-8',
    )
    reg = bot_registry.BotRegistry(standards_dir=tmp_path)

    assert reg.no_unreviewed_commit_patterns('demo') == ['Nothing left to look at']


def test_rate_limit_eta_patterns_per_bot():
    """Only a bot whose notice states a reset time declares extraction patterns.

    CodeRabbit's window notice states when it reopens, so its patterns pull that
    ETA out. Sourcery declares one too: its diff-character budget notice states a
    reset days away — a concrete ETA, even though ``hard_quota`` makes it an
    unawaitable one, so extracting it is reporting rather than an invitation to
    wait. PR-Agent declares none because no refusal has been observed at all, and
    an empty list is the signal to report an absent ETA rather than invent one.
    """
    coderabbit = bot_registry.rate_limit_eta_patterns('coderabbit')
    assert coderabbit
    assert all(isinstance(pattern, str) and pattern for pattern in coderabbit)
    assert 'wait ([0-9]+ minutes? and [0-9]+ seconds?) before requesting another review' in coderabbit

    sourcery = bot_registry.rate_limit_eta_patterns('sourcery')
    assert sourcery
    assert all(isinstance(pattern, str) and pattern for pattern in sourcery)
    # The pattern must read the ETA out of the notice as it is actually worded —
    # a declared-but-non-matching pattern degrades silently to "no ETA stated".
    observed = (
        "Sorry @SomeUser, you've used your own review budget of 250,000 diff characters "
        'for the last 7 days.  You can request another review in 3 days and 17 hours by '
        'commenting `@sourcery-ai review`.'
    )
    assert any(re.search(pattern, observed) for pattern in sourcery)
    assert next(m.group(1) for p in sourcery if (m := re.search(p, observed))) == '3 days and 17 hours'

    assert bot_registry.rate_limit_eta_patterns('cuioss-review-bot') == []


@pytest.mark.parametrize(
    ('notice', 'stated'),
    [
        ('Next included review available in 38 minutes.', '38 minutes'),
        ('Next included review available in 1 minute.', '1 minute'),
        ('Next included review available in 2 hours.', '2 hours'),
        ('Next included review available in 12 minutes and 30 seconds.', '12 minutes and 30 seconds'),
        ('Next included review available in 1 hour and 5 minutes.', '1 hour and 5 minutes'),
    ],
)
def test_coderabbit_declares_the_next_included_review_wording(notice, stated):
    """The review-summary notice's own reset-time wording is declared, in every form.

    Each declared pattern is parsed out of the registry block and compiled here, and
    the first one that matches must capture the WHOLE stated time: the compound
    pattern is declared ahead of the single-unit one, so "12 minutes and 30 seconds"
    is not cut short to "12 minutes".
    """
    patterns = bot_registry.rate_limit_eta_patterns('coderabbit')
    declared = [pattern for pattern in patterns if pattern.startswith('Next included review available in')]
    assert len(declared) >= 2, 'the compound and the single-unit form must both be declared'

    captured = [match.group(1) for pattern in patterns if (match := re.compile(pattern).search(notice))]

    assert captured, f'no declared pattern reads {notice!r}'
    assert captured[0] == stated


def test_the_next_included_review_wording_does_not_read_an_unrelated_sentence():
    """Matched control: the new patterns are anchored on the notice's own wording."""
    patterns = [
        pattern
        for pattern in bot_registry.rate_limit_eta_patterns('coderabbit')
        if pattern.startswith('Next included review available in')
    ]
    assert patterns

    for pattern in patterns:
        assert re.search(pattern, 'The retry loop sleeps for 38 minutes between attempts.') is None


def test_rate_limit_eta_patterns_are_valid_regexes():
    """Every declared ETA pattern compiles — a bad data edit is caught here, not at runtime.

    The consumer skips an uncompilable pattern rather than raising into the poll
    return path, so a malformed pattern would otherwise degrade silently to "no ETA
    stated" instead of surfacing as a defect.
    """
    for bot_kind in bot_registry.bot_kinds():
        for pattern in bot_registry.rate_limit_eta_patterns(bot_kind):
            re.compile(pattern)


def test_module_functions_match_registry_singleton():
    """The module-level functions delegate to the ``REGISTRY`` singleton."""
    assert bot_registry.bot_kinds() == bot_registry.REGISTRY.bot_kinds()
    assert bot_registry.login_to_bot_kind() == bot_registry.REGISTRY.login_to_bot_kind()
    for bot_kind in bot_registry.bot_kinds():
        assert bot_registry.trigger_comment(bot_kind) == bot_registry.REGISTRY.trigger_comment(bot_kind)
        assert bot_registry.escalated_trigger_comment(bot_kind) == (
            bot_registry.REGISTRY.escalated_trigger_comment(bot_kind)
        )
        assert bot_registry.no_unreviewed_commit_patterns(bot_kind) == (
            bot_registry.REGISTRY.no_unreviewed_commit_patterns(bot_kind)
        )
        assert bot_registry.completion_check_name(bot_kind) == bot_registry.REGISTRY.completion_check_name(bot_kind)
        assert bot_registry.ignore_patterns(bot_kind) == bot_registry.REGISTRY.ignore_patterns(bot_kind)
        assert bot_registry.acknowledgment_patterns(bot_kind) == (
            bot_registry.REGISTRY.acknowledgment_patterns(bot_kind)
        )
        assert bot_registry.contentless_review_markers(bot_kind) == (
            bot_registry.REGISTRY.contentless_review_markers(bot_kind)
        )
        assert bot_registry.actionable_content_markers(bot_kind) == (
            bot_registry.REGISTRY.actionable_content_markers(bot_kind)
        )
        for shape in ('review_body', 'inline', 'issue_comment'):
            assert bot_registry.participation_evidence_marker(bot_kind, shape) == (
                bot_registry.REGISTRY.participation_evidence_marker(bot_kind, shape)
            )
        assert bot_registry.rate_limit_class(bot_kind) == bot_registry.REGISTRY.rate_limit_class(bot_kind)
        assert bot_registry.rate_limit_eta_patterns(bot_kind) == bot_registry.REGISTRY.rate_limit_eta_patterns(bot_kind)


def test_findings_core_bot_kinds_is_derived_from_registry():
    """``_findings_core.BOT_KINDS`` equals ``bot_registry.bot_kinds()`` — not a literal."""
    from _findings_core import BOT_KINDS

    assert list(BOT_KINDS) == bot_registry.bot_kinds()


def test_findings_core_bot_kinds_contains_every_shipped_bot():
    """The derived enum contains each shipped bot, and nothing beyond them.

    The negative half is the retirement guard: a bot whose ``standards/{bot_kind}.md``
    doc is deleted must disappear from the enum with no code change, so a stale
    ``bot_kind`` can never be stored as a finding.
    """
    from _findings_core import BOT_KINDS

    for bot_kind in _SHIPPED_BOTS:
        assert bot_kind in BOT_KINDS
    assert set(BOT_KINDS) == set(_SHIPPED_BOTS)

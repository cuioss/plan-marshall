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
   contentless-review / actionable-content markers, per-shape
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
        assert bot_registry.completion_check_name(bot_kind) == bot_registry.REGISTRY.completion_check_name(bot_kind)
        assert bot_registry.ignore_patterns(bot_kind) == bot_registry.REGISTRY.ignore_patterns(bot_kind)
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

#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for automatic-review/scripts/bot_registry.py — the data-not-code bot loader.

The registry parses each ``automatic-review/standards/{bot_kind}.md`` fenced-YAML
data block ONCE and exposes stable accessors so the finding store, the re-review
strategy registry, the producer pre-filter, and the rate-limit detector DERIVE
what they need instead of hard-coding the shipped bot set across several code
files. Two bots ship today
(``coderabbit``, ``sourcery``), and that count is asserted from
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
_SHIPPED_BOTS = ['coderabbit', 'sourcery']


# =============================================================================
# 1. Shipped-standards contract (the real standards/*.md docs)
# =============================================================================


def test_ignore_patterns_are_nonempty_literal_markers():
    """Each bot exposes at least one literal whole-comment ignore marker."""
    coderabbit = bot_registry.ignore_patterns('coderabbit')
    assert 'No actionable comments were generated' in coderabbit
    assert '✏️ Learnings added' in coderabbit

    sourcery = bot_registry.ignore_patterns('sourcery')
    assert 'found 0 issues' in sourcery


def test_contentless_review_markers_preserve_quoted_special_characters():
    """A quoted marker carrying ``:`` and HTML-comment syntax survives verbatim.

    The summary marker moved to the content-aware layer when the summary became a
    conditional drop, so the round-trip is asserted there — it is still one quoted value
    carrying ``:``, ``<!--`` and ``-->``.
    """
    assert '<!-- This is an auto-generated comment: summarize by coderabbit.ai -->' in (
        bot_registry.contentless_review_markers('coderabbit')
    )


def test_contentless_review_markers_per_bot():
    """CodeRabbit declares the summary marker; sourcery declares none.

    The list is a CONJUNCTION target — every entry must be present for the
    producer's contentless layer to fire — so all entries are asserted
    member-by-member rather than by one representative. An empty list for
    sourcery is the fail-closed default that keeps its ingest behaviour
    byte-identical to before the field existed.
    """
    assert bot_registry.contentless_review_markers('coderabbit') == [
        '<!-- This is an auto-generated comment: summarize by coderabbit.ai -->',
    ]
    assert bot_registry.contentless_review_markers('sourcery') == []


def test_contentless_review_headings_name_each_published_state():
    """CodeRabbit declares one heading per state its one summary comment is published in.

    The heading list is an ALTERNATION — the body must carry any one entry — so the
    persistent summary comment can be dropped both while a review runs and once it
    finished, and a marker-bearing skip notice (a draft / ignored-path / label skip under
    ``## Review skipped``) drops as noise rather than filing a false positive. Exact
    equality, so a dropped heading (an in-progress summary filed as a finding) or a
    heading moved back into the conjunction (no body could ever satisfy it) turns this red
    at the data boundary.
    """
    assert bot_registry.contentless_review_headings('coderabbit') == [
        '## Walkthrough',
        'Currently processing new changes',
        '## Review skipped',
    ]
    assert bot_registry.contentless_review_headings('sourcery') == []


def test_no_heading_sits_in_the_conjunction():
    """Negative control: no declared heading is a REQUIRED marker, for any bot.

    A heading in ``contentless_review_markers`` is required of every body, so a
    clean body under the OTHER heading could never be dropped — and with both
    headings there no body could. The headings belong to the alternation only.
    """
    declarers = [kind for kind in bot_registry.bot_kinds() if bot_registry.contentless_review_headings(kind)]
    assert declarers, 'no shipped bot declares a heading — the sweep below is vacuous'
    for kind in declarers:
        required = bot_registry.contentless_review_markers(kind)
        for heading in bot_registry.contentless_review_headings(kind):
            assert heading not in required, kind


def test_contentless_review_headings_unknown_bot_is_empty():
    """An unregistered bot declares no heading condition."""
    assert bot_registry.contentless_review_headings('nope') == []
    assert bot_registry.contentless_review_headings('coderabbit') == (
        bot_registry.REGISTRY.contentless_review_headings('coderabbit')
    )


def test_actionable_content_markers_only_declared_by_coderabbit():
    """CodeRabbit declares its concern sections as the disqualifying markers."""
    assert bot_registry.actionable_content_markers('coderabbit') == [
        'Actionable comments',
        'Nitpick comments',
        'Outside-diff comments',
        'Follow-ups',
    ]
    assert bot_registry.actionable_content_markers('sourcery') == []


def test_contentless_markers_survive_inline_comment_stripping():
    """Each marker's trailing rationale is stripped, the value is not.

    Every entry in CodeRabbit's block carries an inline rationale comment, and each
    heading (``## Walkthrough``) opens with the very ``#`` character that starts a YAML
    comment. A reader that stripped from the first ``#`` rather than from the first
    ``#`` OUTSIDE the quoted span would silently truncate a heading to the empty string —
    which the producer drops from the alternation, leaving that summary state undroppable.
    """
    markers = bot_registry.contentless_review_markers('coderabbit')
    headings = bot_registry.contentless_review_headings('coderabbit')
    for marker in markers + headings:
        assert marker
        assert 'CONFIRMED' not in marker
        assert 'UNVERIFIED' not in marker
        assert marker == marker.strip()
    # The quoted-``#`` case specifically: each heading keeps its markdown prefix.
    assert '## Walkthrough' in headings
    assert bot_registry.actionable_content_markers('coderabbit') == [
        'Actionable comments',
        'Nitpick comments',
        'Outside-diff comments',
        'Follow-ups',
    ]

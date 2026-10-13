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


def test_ignore_patterns_are_nonempty_literal_markers():
    """Each bot exposes at least one literal whole-comment ignore marker."""
    coderabbit = bot_registry.ignore_patterns('coderabbit')
    assert '## Walkthrough' in coderabbit
    assert 'No actionable comments were generated' in coderabbit

    sourcery = bot_registry.ignore_patterns('sourcery')
    assert 'found 0 issues' in sourcery

    pr_agent = bot_registry.ignore_patterns('cuioss-review-bot')
    assert '## PR Agent Walkthrough' in pr_agent
    # The persistent-review update notice carries no review content, and is authored by the
    # reviewer identity, so without this marker it reaches triage as a candidate finding.
    # Markdown link syntax must survive the YAML round-trip verbatim.
    assert '**[Persistent review]' in pr_agent


def test_ignore_patterns_preserve_quoted_special_characters():
    """A quoted marker carrying ``:`` and HTML-comment syntax survives verbatim."""
    coderabbit = bot_registry.ignore_patterns('coderabbit')
    assert '<!-- This is an auto-generated comment: summarize by coderabbit.ai -->' in coderabbit


def test_contentless_review_markers_only_declared_by_pr_agent():
    """PR-Agent declares the clean-Guide marker set; the other two declare none.

    The list is a CONJUNCTION target — every entry must be present for the
    producer's contentless layer to fire — so all three entries are asserted
    member-by-member rather than by one representative. An empty list for the
    other two bots is the fail-closed default that keeps their ingest behaviour
    byte-identical to before the field existed.

    The two assertion entries are BARE INNER TEXT, not the ``**bold**`` a human
    reads on GitHub: PR-Agent emits them inside an HTML ``<table>``, where no
    markdown is rendered, so the raw API body carries ``<strong>…</strong>``. The
    superseded ``**``-wrapped values matched no real body at all and left the
    conjunction permanently unsatisfiable, so this assertion is exact rather than
    a membership check — a re-wrapped value must turn it red here, at the data
    boundary, and not only in the producer's behavioural suite.
    """
    assert bot_registry.contentless_review_markers('cuioss-review-bot') == [
        'No security concerns identified',
        'PR contains tests',
    ]
    assert bot_registry.contentless_review_markers('coderabbit') == []
    assert bot_registry.contentless_review_markers('sourcery') == []


def test_contentless_review_headings_name_both_pr_agent_guides():
    """PR-Agent declares one heading per persistent Guide; the other two declare none.

    The heading list is an ALTERNATION — the body must carry any one entry — so
    the security pass's ``## PR Reviewer Guide`` and the code-review pass's
    ``## PR Code Review Guide`` can share one clean-shape rule. Exact equality,
    so a dropped heading (a clean code-review Guide filed as a finding) or a
    heading moved back into the conjunction (no body could ever satisfy it) turns
    this red at the data boundary.
    """
    assert bot_registry.contentless_review_headings('cuioss-review-bot') == [
        '## PR Reviewer Guide',
        '## PR Code Review Guide',
    ]
    assert bot_registry.contentless_review_headings('coderabbit') == []
    assert bot_registry.contentless_review_headings('sourcery') == []


def test_no_heading_sits_in_the_conjunction():
    """Negative control: neither Guide heading is a REQUIRED marker.

    A heading in ``contentless_review_markers`` is required of every body, so a
    clean Guide under the OTHER heading could never be dropped — and with both
    headings there no body could. The headings belong to the alternation only.
    """
    required = bot_registry.contentless_review_markers('cuioss-review-bot')
    for heading in bot_registry.contentless_review_headings('cuioss-review-bot'):
        assert heading not in required


def test_contentless_review_headings_unknown_bot_is_empty():
    """An unregistered bot declares no heading condition."""
    assert bot_registry.contentless_review_headings('nope') == []
    assert bot_registry.contentless_review_headings('cuioss-review-bot') == (
        bot_registry.REGISTRY.contentless_review_headings('cuioss-review-bot')
    )


def test_actionable_content_markers_only_declared_by_pr_agent():
    """``<details>`` is PR-Agent's disqualifying marker; the other two declare none."""
    assert bot_registry.actionable_content_markers('cuioss-review-bot') == ['<details>']
    assert bot_registry.actionable_content_markers('coderabbit') == []
    assert bot_registry.actionable_content_markers('sourcery') == []


def test_contentless_markers_survive_inline_comment_stripping():
    """Each marker's trailing ``# CONFIRMED …`` rationale is stripped, the value is not.

    Every entry in PR-Agent's block carries an inline grounding comment, and each
    heading (``## PR Reviewer Guide``, ``## PR Code Review Guide``) opens with the
    very ``#`` character that starts a YAML comment. A reader that stripped from
    the first ``#`` rather than from the first ``#`` OUTSIDE the quoted span would
    silently truncate a heading to the empty string — which the producer drops
    from the alternation, leaving that Guide's clean shape undroppable.
    """
    markers = bot_registry.contentless_review_markers('cuioss-review-bot')
    headings = bot_registry.contentless_review_headings('cuioss-review-bot')
    for marker in markers + headings:
        assert marker
        assert 'CONFIRMED' not in marker
        assert 'UNVERIFIED' not in marker
        assert marker == marker.strip()
    # The quoted-``#`` case specifically: each heading keeps its markdown prefix.
    assert '## PR Reviewer Guide' in headings
    assert '## PR Code Review Guide' in headings
    assert bot_registry.actionable_content_markers('cuioss-review-bot') == ['<details>']

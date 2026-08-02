#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The OBSERVED PR-Agent ``## PR Reviewer Guide`` body, plus a renderer for its variants.

Two suites assert against PR-Agent's Guide body and must assert against the SAME
shape, because that shape is evidence rather than convention:

* ``workflow-integration-github/test_github_pr.py`` drives the layer-3 predicate
  (``_is_contentless_boilerplate`` / ``_is_obvious_noise``) directly.
* ``workflow-integration-github/test_pr_agent_contentless_guide_interaction.py``
  drives the producer + aggregator round-trip end to end.

A per-suite fixture literal is what made both suites vacuous once already: they
were written in the body's GitHub *rendering* (``**PR contains tests**``) while
the raw API body PR-Agent actually posts carries
``<strong>PR contains tests</strong>``. The registry markers were derived from
the same rendering, so predicate and fixtures agreed with each other and with
nothing real — the conjunction could never hold on a live body, and every suite
stayed green. Sharing the observed body is therefore not deduplication for its
own sake: it removes the second place a fake shape can hide.

:data:`OBSERVED_CLEAN_GUIDE` is the byte-exact evidence — copied from the
quarantined ``raw_input.body`` of the ``pr-comment`` finding PR-Agent's clean
Guide produced on ``cuioss/plan-marshall`` PR #1078 — and is deliberately a
literal rather than a render, so it cannot drift with :func:`guide_body`. The
derived shapes below ARE rendered, and
``test_pr_agent_contentless_guide_interaction`` pins the renderer against the
literal so a drifted renderer cannot quietly fake all four of them.

This file is intentionally a sibling helper and is NOT a ``conftest.py`` —
a second ``conftest.py`` under ``test/`` would shadow the top-level
``test/conftest.py`` and disable the shared autouse isolation fixtures.
"""

from __future__ import annotations

#: The Guide heading. It sits OUTSIDE the HTML table, so it is markdown in the
#: raw body too — the one marker that needs no rendering-independent form.
GUIDE_HEADING = '## PR Reviewer Guide 🔍'


def assertion(text: str) -> str:
    """Emphasize ``text`` the way PR-Agent does — HTML ``<strong>``, never markdown ``**``.

    GitHub renders no markdown inside an HTML block, and every assertion row
    lives inside the Guide's ``<table>``, so ``<strong>`` is what the raw API
    body carries. Writing ``**text**`` here is exactly the defect this module
    exists to keep out of the fixtures.
    """
    return f'<strong>{text}</strong>'


def guide_row(emoji: str, cell: str) -> str:
    """One ``<tr><td>`` row of the Guide table: an emoji, a ``&nbsp;``, then ``cell``.

    ``cell`` is the row's full content — normally an :func:`assertion`, but the
    ⚡ row also carries its ``<details>`` findings, so it is passed through
    verbatim rather than wrapped here.
    """
    return f'<tr><td>{emoji}&nbsp;{cell}</td></tr>'


def guide_body(*rows: str) -> str:
    """Render a complete Guide body: the heading, then the HTML table of ``rows``.

    The double space after the heading and the trailing space after
    ``</table>`` are part of the observed body, not formatting slack — see
    :data:`OBSERVED_CLEAN_GUIDE`, which this function is pinned against.
    """
    return f'{GUIDE_HEADING}  <table> ' + ' '.join(rows) + ' </table> '


#: The VERBATIM body PR-Agent posted on ``cuioss/plan-marshall`` PR #1078,
#: copied from the stored finding's quarantined ``raw_input.body``. This is the
#: project's only capture of the RAW API body — every other shape here is
#: derived from it. Whitespace is reproduced exactly.
OBSERVED_CLEAN_GUIDE = (
    '## PR Reviewer Guide 🔍  <table> '
    '<tr><td>🧪&nbsp;<strong>PR contains tests</strong></td></tr> '
    '<tr><td>🔒&nbsp;<strong>No security concerns identified</strong></td></tr> '
    '<tr><td>⚡&nbsp;<strong>No major issues detected</strong></td></tr> '
    '</table> '
)

#: The observed clean body's three rows, in the order the bot emitted them.
#: Consumed by the renderer-fidelity guard, and reused to build the variants.
CLEAN_TESTS_ROW = guide_row('🧪', assertion('PR contains tests'))
CLEAN_SECURITY_ROW = guide_row('🔒', assertion('No security concerns identified'))
CLEAN_FOCUS_ROW = guide_row('⚡', assertion('No major issues detected'))

#: The clean assertions PLUS one focus-area finding. ``<details>`` is the
#: structural carrier of every finding PR-Agent emits, so its presence proves
#: the Guide has content whatever the clean rows say.
GUIDE_WITH_FINDING = guide_body(
    CLEAN_TESTS_ROW,
    CLEAN_SECURITY_ROW,
    guide_row(
        '⚡',
        assertion('Recommended focus areas for review')
        + '<details><summary>Unbounded retry</summary>'
        + assertion('The retry loop has no ceiling')
        + ' A persistent upstream failure will spin forever.'
        + '</details>',
    ),
)

#: A CHANGED required marker: the 🔒 row names a concrete concern instead of
#: asserting a clean result. No ``<details>`` anywhere.
GUIDE_DEVIATING_ASSERTION = guide_body(
    CLEAN_TESTS_ROW,
    guide_row('🔒', assertion('Token value reaches the log sink at L42')),
    CLEAN_FOCUS_ROW,
)

#: A MISSING required marker: the docs-only shape — the 🔒 clean assertion is
#: present, the 🧪 one is absent entirely.
GUIDE_DOCS_ONLY = guide_body(CLEAN_SECURITY_ROW, CLEAN_FOCUS_ROW)

#: The same clean Guide as GitHub RENDERS it — a markdown table with ``**`` bold
#: instead of an HTML table with ``<strong>``. PR-Agent has never been observed
#: emitting this shape; it is here because the registry markers are bare inner
#: text precisely so they hold across BOTH renderings, and that property needs a
#: fixture to be assertable. It is NOT a claim that the bot emits it.
RENDERED_MARKDOWN_GUIDE = (
    '## PR Reviewer Guide 🔍\n'
    '\n'
    '| | |\n'
    '|---|---|\n'
    '| 🧪 | **PR contains tests** |\n'
    '| 🔒 | **No security concerns identified** |\n'
    '| ⚡ | **No major issues detected** |\n'
)

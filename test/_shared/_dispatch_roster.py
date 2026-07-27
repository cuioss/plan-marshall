# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared heading-bounded Markdown section walk and roster-row parse.

``standards/dispatch-inline-split.md``'s two roster sections (``##
Dispatched steps`` / ``## Inline steps``) and several other phase-6-finalize
standards documents share the same shape: a heading line, followed by
Markdown list items each naming a backticked step key, terminated by the
next heading (or another stop marker). Two independent regression suites
under ``test/plan-marshall/phase-6-finalize/`` each need that identical
heading-bounded walk and row parse — the closure/disjointness/resolver-lookup
sweep and the termination-contract's population-derived reachability check.
This module is the single implementation of the walk and the row parse, so
the two suites read an identical population rather than each maintaining its
own copy that can silently drift out of step.
"""

from __future__ import annotations

import re

#: A roster row names its step as the first backticked token of a list item.
ROSTER_ROW = re.compile(r'^-\s+`([^`]+)`')


def section_lines(
    text: str, heading: str, stop_prefixes: tuple[str, ...] = ('## ',)
) -> list[str]:
    """Return the lines between ``heading`` and the next stop-prefixed line.

    Args:
        text: The full document text.
        heading: The exact (stripped) heading line marking the section start.
        stop_prefixes: Line prefixes that terminate the section. Defaults to
            the top-level ``## `` heading marker.

    Returns:
        The lines strictly between the heading line and the terminating line
        (or end of document, if no terminating line follows).

    Raises:
        AssertionError: when ``heading`` is not found verbatim in ``text``.
    """
    lines = text.splitlines()
    try:
        start = next(i for i, line in enumerate(lines) if line.strip() == heading)
    except StopIteration:
        raise AssertionError(f'Heading not found: {heading!r} in the document') from None
    collected: list[str] = []
    for line in lines[start + 1 :]:
        if line.startswith(stop_prefixes):
            break
        collected.append(line)
    return collected


def parse_roster_rows(doc_text: str, heading: str) -> list[tuple[str, str]]:
    """Return ``(step_key, full_row_line)`` for one roster section, in order."""
    rows: list[tuple[str, str]] = []
    for line in section_lines(doc_text, heading):
        match = ROSTER_ROW.match(line)
        if match:
            rows.append((match.group(1), line))
    return rows


def parse_roster(doc_text: str, heading: str) -> list[str]:
    """Parse the step keys out of one roster section, preserving order."""
    return [key for key, _ in parse_roster_rows(doc_text, heading)]

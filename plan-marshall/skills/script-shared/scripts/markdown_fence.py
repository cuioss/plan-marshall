#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The ONE CommonMark fence-line reader shared by the review-gate scripts.

Two modules used to carry their own copy of this rule — the GitHub review-comment
parser and the criteria-snapshot parser — so a fix to one could leave the other
reading a different document. This module is the single owner; both import it.

The rule answers only "is this line a fence line, and if so which character, how
long, and what trailing text does it carry?". The CALLER decides whether a line
OPENS a fence (any allowed trailing info string) or CLOSES one (same character, at
least the opener's length, and only whitespace after it).
"""

from __future__ import annotations


def fence_marker(line: str) -> tuple[str, int, str] | None:
    """Return ``(character, length, trailing)`` for a CommonMark fence line, or ``None``.

    A fence is a run of at least three backticks or tildes, indented at most three
    spaces (a four-space or tab-indented run is an indented code block, not a fence).
    A BACKTICK fence's info string may not contain a backtick, exactly as CommonMark
    specifies — such a line is ordinary text, not a fence.
    """
    leading = line[: len(line) - len(line.lstrip(' \t'))]
    if '\t' in leading or len(leading) > 3:
        return None
    stripped = line.strip()
    if not stripped or stripped[0] not in '`~':
        return None
    character = stripped[0]
    length = len(stripped) - len(stripped.lstrip(character))
    if length < 3:
        return None
    trailing = stripped[length:]
    if character == '`' and '`' in trailing:
        return None
    return character, length, trailing


__all__ = ['fence_marker']

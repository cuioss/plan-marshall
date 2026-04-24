#!/usr/bin/env python3
"""Derivation of the ``short_description`` field for manage-status.

This helper encapsulates the algorithm that produces the terminal-title
``short_description`` from a plan title:

* Strip lesson-id style prefixes such as ``2026-04-19-13-004-…`` or
  ``lesson-2026-04-19-13-004-…``.
* Collapse internal whitespace runs and replace the remaining spaces
  with underscores.
* Truncate the result at the last underscore boundary that fits within
  ``max_len`` characters, appending ``…`` (U+2026) as the ellipsis tail
  when truncation occurs.
* Return an empty string for unusable input (empty, whitespace-only, or
  pure lesson-id noise with no trailing slug).

The derivation is intentionally deterministic and side-effect free so it
can be exercised from unit tests without fixtures.
"""

from __future__ import annotations

import re

_LESSON_ID_PREFIX = re.compile(
    r'^(?:lesson-)?\d{4}-\d{2}-\d{2}(?:-\d+)*[-_\s]*',
    re.IGNORECASE,
)
_WHITESPACE = re.compile(r'\s+')
_ELLIPSIS = '…'


def derive_short_description(title: str, max_len: int = 36) -> str:
    """Derive a compact ``short_description`` from a plan title.

    Args:
        title: Raw plan title as supplied by ``manage_status create``.
        max_len: Maximum length (inclusive) of the returned string.
            Defaults to 36 to balance legibility against typical
            terminal-tab budgets. Must be a positive integer.

    Returns:
        The derived short description, or an empty string when the
        input is unusable (empty, whitespace-only, or pure lesson-id
        noise with no trailing slug).
    """
    if not isinstance(title, str) or not title.strip():
        return ''
    if max_len <= 0:
        return ''

    stripped = _LESSON_ID_PREFIX.sub('', title).strip()
    if not stripped:
        return ''

    collapsed = _WHITESPACE.sub(' ', stripped).strip()
    slug = collapsed.replace(' ', '_')
    if not slug:
        return ''

    if len(slug) <= max_len:
        return slug

    # Reserve one slot for the ellipsis character.
    budget = max_len - 1
    if budget <= 0:
        return _ELLIPSIS[:max_len]

    head = slug[:budget]
    boundary = head.rfind('_')
    if boundary > 0:
        head = head[:boundary]
    head = head.rstrip('_')
    if not head:
        # Fallback: hard cut when the slug contains no usable boundary.
        head = slug[:budget].rstrip('_')
        if not head:
            return _ELLIPSIS[:max_len]
    return f'{head}{_ELLIPSIS}'

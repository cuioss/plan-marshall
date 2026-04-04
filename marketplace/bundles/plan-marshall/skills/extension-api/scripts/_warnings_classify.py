#!/usr/bin/env python3
"""Unified warning categorization with pluggable pattern matching.

Provides categorize_warnings() with pluggable matchers (substring, wildcard, regex)
used by build-maven and build-gradle check-warnings subcommands.

Note: This module handles the *check-warnings CLI subcommand* (post-hoc classification
of extracted warnings against acceptable patterns). For *build output filtering*
during cmd_run (actionable/structured/errors modes), see _build_parse.filter_warnings().
The two systems serve different pipeline phases:
  1. cmd_run → _build_parse.filter_warnings() — real-time output filtering
  2. check-warnings CLI → _warnings_classify.categorize_warnings() — detailed triage
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

# Warning types that are always considered fixable
ALWAYS_FIXABLE_TYPES = ['javadoc_warning', 'compilation_error', 'deprecation_warning', 'unchecked_warning']

# Types that route to fixable (beyond ALWAYS_FIXABLE_TYPES)
EXTRA_FIXABLE_TYPES = ['test_failure', 'dependency_error']

# Types that route to acceptable
ACCEPTABLE_TYPES = ['openrewrite_info']

# Types that route to unknown
UNKNOWN_TYPES = ['other', 'other_warnings']


def _match_substring(message: str, pattern: str) -> bool:
    """Substring matching + case-insensitive regex fallback (Maven style)."""
    clean = pattern[9:].strip() if pattern.startswith('[WARNING]') else pattern
    if clean in message:
        return True
    try:
        if re.search(clean, message, re.IGNORECASE):
            return True
    except re.error:
        pass
    return False


def _match_wildcard(message: str, pattern: str) -> bool:
    """Wildcard matching + regex for ^-prefixed patterns (Gradle style).

    Supports three wildcard forms (plain string matching, no regex):
    - 'prefix*' — startswith match
    - '*suffix' — endswith match
    - '*infix*' — substring (contains) match
    And explicit regex via '^'-prefixed patterns.
    """
    if message == pattern:
        return True
    if pattern.endswith('*') and not pattern.startswith('*') and message.startswith(pattern[:-1]):
        return True
    if pattern.startswith('*') and pattern.endswith('*') and len(pattern) > 2 and pattern[1:-1] in message:
        return True
    if pattern.startswith('*') and not pattern.endswith('*') and message.endswith(pattern[1:]):
        return True
    if pattern.startswith('^'):
        try:
            if re.match(pattern, message):
                return True
        except re.error:
            logger.debug('Invalid regex in wildcard pattern: %s', pattern)
    return False


def _match_regex(message: str, pattern: str) -> bool:
    """Pure regex matching."""
    try:
        return bool(re.search(pattern, message))
    except re.error:
        logger.debug('Invalid regex pattern: %s', pattern)
        return False


_MATCHERS = {
    'substring': _match_substring,
    'wildcard': _match_wildcard,
    'regex': _match_regex,
}


def flatten_patterns(acceptable_warnings: dict | list) -> list[str]:
    """Flatten acceptable_warnings dict or list into a flat list of patterns."""
    patterns: list[str] = []
    if isinstance(acceptable_warnings, dict):
        for value in acceptable_warnings.values():
            if isinstance(value, list):
                patterns.extend(str(p) for p in value if p)
    elif isinstance(acceptable_warnings, list):
        patterns.extend(str(p) for p in acceptable_warnings if p)
    return patterns


def _is_acceptable(message: str, patterns: list[str], match_fn) -> bool:
    """Check if a warning message matches any acceptable pattern."""
    return any(match_fn(message, p) for p in patterns)


def _is_acceptable_categorized(message: str, categorized: dict, match_fn) -> tuple[bool, str | None]:
    """Check if message matches any pattern in a categorized dict. Returns (matched, category)."""
    for category, patterns in categorized.items():
        if isinstance(patterns, list):
            for pattern in patterns:
                if match_fn(message, pattern):
                    return True, category
    return False, None


def categorize_warnings(
    warnings: list[dict],
    patterns: dict | list | None = None,
    matcher: str = 'substring',
    filter_severity: str | None = None,
) -> dict:
    """Categorize warnings into acceptable, fixable, and unknown.

    Args:
        warnings: List of warning dicts with 'type', 'message', 'severity' fields.
        patterns: Acceptable patterns - flat list or categorized dict.
        matcher: Matching strategy - 'substring' (Maven), 'wildcard' (Gradle), or 'regex'.
        filter_severity: If set, only process warnings with this severity value.

    Returns:
        Dict with keys: acceptable, fixable, unknown (each a list of warning dicts).
    """
    match_fn = _MATCHERS.get(matcher, _match_substring)
    patterns = patterns or []

    # Determine if patterns are categorized (dict) or flat (list)
    is_categorized = isinstance(patterns, dict)
    flat_patterns = flatten_patterns(patterns) if is_categorized else list(patterns)

    items = warnings
    if filter_severity:
        items = [w for w in warnings if w.get('severity') == filter_severity]

    acceptable, fixable, unknown = [], [], []

    for w in items:
        wtype = w.get('type', 'other')
        message = w.get('message', '')

        if wtype in ALWAYS_FIXABLE_TYPES:
            fixable.append({**w, 'reason': f"Type '{wtype}' is always fixable"})
            continue

        # Check acceptable patterns
        if is_categorized and isinstance(patterns, dict):
            matched, category = _is_acceptable_categorized(message, patterns, match_fn)
            if matched:
                acceptable.append({**w, 'reason': f"Matches acceptable pattern in '{category}'"})
                continue
        elif _is_acceptable(message, flat_patterns, match_fn):
            acceptable.append(w)
            continue

        # Route by type
        if wtype in EXTRA_FIXABLE_TYPES:
            fixable.append(w)
        elif wtype in ACCEPTABLE_TYPES:
            acceptable.append(w)
        elif wtype in UNKNOWN_TYPES:
            unknown.append({**w, 'requires_classification': True})
        else:
            fixable.append(w)

    return {'acceptable': acceptable, 'fixable': fixable, 'unknown': unknown}

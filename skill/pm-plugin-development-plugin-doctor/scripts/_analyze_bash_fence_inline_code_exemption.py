#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Bash-fence inline-code-exemption analyzer for the ``bash-fence-inline-code-exemption`` rule.

This module is a reintroduction guard. It detects analyzer modules that scan
*inside* bash/sh fences (they define a ``_BASH_FENCE_INFO_STRINGS`` token) yet
also carry the markdown-prose inline-code exemption (an ``_INLINE_CODE_RE`` or
``_inline_code_spans`` helper). The two concepts are mutually exclusive in a
single analyzer: inside a bash fence a backtick span denotes command
substitution, not a markdown inline-code span, so exempting "inline-code" inside
a bash-fence scanner silently skips real command-substitution shapes.

Detection
---------
For every ``*.py`` file under ``marketplace_root/bundles/**/scripts/``, the rule
checks the literal-token co-presence of:

1. ``_BASH_FENCE_INFO_STRINGS`` — the marker that the analyzer scopes its scan
   to ``bash``/``sh`` fenced blocks, AND
2. ``_INLINE_CODE_RE`` OR ``_inline_code_spans`` — the markdown-prose
   inline-code exemption helper.

When BOTH are present the file is flagged. Files with only one of the two
markers are compliant: prose scanners define only the inline-code helper
(exemption is correct there), and bash-fence scanners define only the
fence-info-strings marker (no inline-code exemption — correct post-PR-#474).

Self-reference and documentary-host exclusion
----------------------------------------------
This analyzer's own source names both token families in its docstring and
detection constants, so it MUST be excluded from its own scan. The dispatch host
``doctor-marketplace.py`` likewise documents every rule (including this one) in
an explanatory comment naming both marker families — a documentary reference,
not an analyzer defining the markers — and is excluded for the same reason. The
exclusion is a path-component-anchored whitelist of those filenames, mirroring
the self-reference whitelist in ``_analyze_executor_path_in_production.py``.

Findings have the shape::

    {
        'rule_id': 'bash-fence-inline-code-exemption',
        'type': 'bash_fence_inline_code_exemption',
        'rule': 'analyze_bash_fence_inline_code_exemption',
        'file': '<absolute file path>',
        'line': <int, 1-based line of the offending inline-code marker>,
        'severity': 'error',
        'fixable': False,
        'snippet': '<line excerpt>',
        'description': '<remediation guidance>',
    }

Public API
----------
- ``analyze_bash_fence_inline_code_exemption(marketplace_root)``: entry point —
  scans ``marketplace/bundles/**/scripts/**/*.py`` and emits findings for files
  defining both marker families.
- ``is_whitelisted(file_path)``: returns True when ``file_path`` is this
  analyzer's own source (self-reference exclusion).
"""

from __future__ import annotations

from pathlib import Path

from _doctor_shared import Finding
from _rule_registry import RuleDescriptor

RULE_ID = 'bash-fence-inline-code-exemption'
RULE_NAME = 'analyze_bash_fence_inline_code_exemption'

RULE_DESCRIPTOR = RuleDescriptor(
    rule_id=RULE_ID,
    severity='error',
    category='structural',
    scope='file-local',
)

# Marker that an analyzer scopes its scan to ``bash``/``sh`` fenced blocks.
_BASH_FENCE_MARKER = '_BASH_FENCE_INFO_STRINGS'

# Markdown-prose inline-code exemption helpers. Either token signals the
# inline-code exemption that must NOT co-exist with the bash-fence marker.
_INLINE_CODE_MARKERS = ('_INLINE_CODE_RE', '_inline_code_spans')

_DESCRIPTION = (
    'Analyzer scans inside a bash/sh fence (defines _BASH_FENCE_INFO_STRINGS) '
    'yet also carries a markdown inline-code exemption (_INLINE_CODE_RE / '
    '_inline_code_spans). Inside a bash fence a backtick span is command '
    'substitution, not markdown inline-code, so the exemption silently skips '
    'real command-substitution shapes. Remove the inline-code exemption helper '
    'from the bash-fence analyzer.'
)

# ---------------------------------------------------------------------------
# Whitelist — path-component-anchored self-reference exclusion
# ---------------------------------------------------------------------------
_WHITELIST_COMPONENT_SETS: list[frozenset[str]] = [
    # This file itself names both marker families in its docstring/constants.
    frozenset({'_analyze_bash_fence_inline_code_exemption.py'}),
    # The dispatch host documents every rule (including this one) in an
    # explanatory comment naming both marker families — a documentary
    # reference, not an analyzer defining the markers.
    frozenset({'doctor-marketplace.py'}),
]


def is_whitelisted(file_path: Path) -> bool:
    """Return True when ``file_path`` matches the self-reference whitelist.

    Each whitelist entry is a frozenset of path-component strings that must ALL
    appear as exact matches among the components of ``file_path``.
    """
    parts_set = set(file_path.parts)
    for required_components in _WHITELIST_COMPONENT_SETS:
        if required_components.issubset(parts_set):
            return True
    return False


def _first_inline_code_line(text: str) -> tuple[int, str] | None:
    """Return the (1-based line number, stripped excerpt) of the first inline-code marker.

    Returns ``None`` when no inline-code marker appears in ``text`` (the caller
    only reaches this function when at least one marker is known to be present,
    but the guard keeps the helper total).
    """
    for line_idx, line in enumerate(text.splitlines()):
        for marker in _INLINE_CODE_MARKERS:
            if marker in line:
                return line_idx + 1, line.strip()[:120]
    return None


def _scan_file(file_path: Path) -> list[dict]:
    """Scan one Python file for co-present bash-fence and inline-code markers."""
    try:
        text = file_path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        return []

    if _BASH_FENCE_MARKER not in text:
        return []
    if not any(marker in text for marker in _INLINE_CODE_MARKERS):
        return []

    located = _first_inline_code_line(text)
    if located is None:
        return []
    line_no, snippet = located

    return [
        Finding(
            type='bash_fence_inline_code_exemption',
            file=str(file_path),
            line=line_no,
            severity='error',
            fixable=False,
            rule_id=RULE_ID,
            description=_DESCRIPTION,
            extra={'rule': RULE_NAME, 'snippet': snippet},
        ).to_dict()
    ]


def analyze_bash_fence_inline_code_exemption(marketplace_root: Path) -> list[dict]:
    """Scan marketplace bundle scripts for the bash-fence inline-code-exemption mismatch.

    Scans every ``*.py`` under ``<marketplace_root>/bundles/**/scripts/`` and
    emits one finding per file that defines BOTH the ``_BASH_FENCE_INFO_STRINGS``
    marker and an inline-code exemption helper (``_INLINE_CODE_RE`` /
    ``_inline_code_spans``). This analyzer's own source is excluded via the
    self-reference whitelist.

    Parameters
    ----------
    marketplace_root:
        Path to the ``marketplace/`` directory.

    Returns
    -------
    list[dict]
        Findings for files carrying both marker families.
    """
    findings: list[dict] = []

    bundles_root = marketplace_root / 'bundles'
    if not bundles_root.is_dir():
        return []

    for py_file in sorted(bundles_root.rglob('*.py')):
        if not py_file.is_file():
            continue
        if is_whitelisted(py_file):
            continue
        findings.extend(_scan_file(py_file))

    return findings

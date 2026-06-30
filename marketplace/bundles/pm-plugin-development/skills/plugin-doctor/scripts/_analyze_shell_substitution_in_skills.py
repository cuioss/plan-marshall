#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shell-substitution scanner for the ``shell-substitution-in-skills`` rule.

This module implements a deterministic regex-based static analyzer that
detects ``$(`` command-substitution patterns inside markdown files under
``marketplace/bundles/plan-marshall/skills/``. Such patterns violate the
``persona-plan-marshall-agent`` "Bash: no shell constructs" hard rule because the
host platform interprets them as a security-prompting shell construct when
a subagent attempts to execute the documented command literally.

Pattern alignment
-----------------
The analyzer mirrors ``_analyze_shell_active_tokens.py``:

- pure static analysis (no subprocess execution, no imports of target scripts)
- regex-driven extraction from markdown source
- stdlib-only dependencies
- no mutation of any file

Detection
---------
Every occurrence of the literal two-character sequence ``$(`` in a markdown
source file is a candidate finding. Two structurally-defined documentary
contexts are exempt:

1. **Inline-code span** — A ``$(`` inside a markdown inline-code span
   (`` `…` ``). Subagents do not execute inline-code tokens; these are
   token references, not runnable commands. Whether the surrounding prose
   names the rule or merely describes the symbol is irrelevant — the
   structural placement inside `` `…` `` makes the occurrence
   non-executable.

2. **Verbatim-source fenced block** — A ``$(`` inside a fenced block whose
   info-string is ``markdown`` or ``text``. These fences hold verbatim
   source examples (e.g., before/after illustrations) that subagents do not
   interpret as instructions.

Every other occurrence — in narrative prose, in a fenced ``bash``/``sh``
block, in any other code-language fenced block (``python``/``json``/etc.
with a ``$(`` that would be shell-interpreted if copy-pasted), or in any
fenced block with no info-string — is a finding.

Findings have the shape::

    {
        'rule_id': 'shell-substitution-in-skills',
        'type': 'shell_substitution_in_skills',
        'rule': 'analyze_shell_substitution_in_skills',
        'file': '<absolute markdown path>',
        'line': <int, 1-based>,
        'severity': 'error',
        'fixable': False,
        'snippet': '<offending text excerpt, max 80 chars>',
        'description': '<short human-readable explanation>',
    }

Public API
----------
- ``analyze_shell_substitution_in_skills(marketplace_root)``: entry point —
  scans every ``*.md`` under ``marketplace_root/plan-marshall/skills/``.
"""

from __future__ import annotations

import re
from pathlib import Path

from _doctor_shared import Finding  # type: ignore[import-not-found]
from _rule_registry import RuleDescriptor

RULE_ID = 'shell-substitution-in-skills'

RULE_DESCRIPTOR = RuleDescriptor(
    rule_id=RULE_ID,
    severity='error',
    category='safety',
    scope='file-local',
)
RULE_NAME = 'analyze_shell_substitution_in_skills'
FINDING_TYPE = 'shell_substitution_in_skills'

# ---------------------------------------------------------------------------
# Detection patterns
# ---------------------------------------------------------------------------

# The forbidden token: literal "$(".
_DOLLAR_PAREN_RE = re.compile(r'\$\(')

# Inline-code span detection (matches `...`).
_INLINE_CODE_RE = re.compile(r'`([^`]+)`')

# Fenced-block boundaries.
_FENCE_OPEN_RE = re.compile(r'^\s*```\s*([A-Za-z0-9_+-]*)\s*$')
_FENCE_CLOSE_RE = re.compile(r'^\s*```\s*$')

# Documentary fence info-strings — verbatim source examples are exempt.
_DOC_FENCE_INFO_STRINGS = frozenset({'markdown', 'text'})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_fence_map(lines: list[str]) -> dict[int, str]:
    """Map 0-based line indices inside any fenced block to the info-string.

    Lines that are NOT inside a fence are absent from the map. The fence
    delimiter lines (the lines containing the opening / closing ``` ``` ```)
    are also absent — only the body lines between the delimiters appear.
    """
    inside: dict[int, str] = {}
    in_fence = False
    info_string = ''
    for idx, line in enumerate(lines):
        if not in_fence:
            m = _FENCE_OPEN_RE.match(line)
            if m:
                in_fence = True
                info_string = m.group(1).lower()
        else:
            if _FENCE_CLOSE_RE.match(line):
                in_fence = False
                info_string = ''
            else:
                inside[idx] = info_string
    return inside


def _inline_code_spans(line: str) -> list[tuple[int, int]]:
    """Return (start, end) character offsets of inline-code spans on ``line``."""
    return [(m.start(), m.end()) for m in _INLINE_CODE_RE.finditer(line)]


def _offset_in_inline_code(offset: int, spans: list[tuple[int, int]]) -> bool:
    """Return ``True`` if ``offset`` lies within any of the inline-code spans."""
    return any(start <= offset < end for start, end in spans)


# ---------------------------------------------------------------------------
# File-level scanner
# ---------------------------------------------------------------------------


def _scan_file(path: Path) -> list[dict]:
    """Scan a single markdown file and return all findings."""
    try:
        text = path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError) as exc:
        return [
            Finding(
                type='file_read_error',
                file=str(path),
                line=0,
                severity='error',
                fixable=False,
                rule_id=RULE_ID,
                description=f'Could not read file: {exc}',
                extra={'rule': RULE_NAME, 'snippet': ''},
            ).to_dict()
        ]

    lines = text.splitlines()
    fence_map = _build_fence_map(lines)

    findings: list[Finding] = []

    for idx, line in enumerate(lines):
        matches = list(_DOLLAR_PAREN_RE.finditer(line))
        if not matches:
            continue

        in_fence = idx in fence_map
        fence_info = fence_map.get(idx, '')
        spans = _inline_code_spans(line)

        for m in matches:
            offset = m.start()

            # Exemption 1: verbatim-source fenced block (info-string is
            # ``markdown`` or ``text``).
            if in_fence and fence_info in _DOC_FENCE_INFO_STRINGS:
                continue

            # Exemption 2: inline-code span. Inline-code spans only matter
            # outside fenced blocks (inside a fence, the backtick is just a
            # literal character, not a span delimiter).
            if not in_fence and _offset_in_inline_code(offset, spans):
                continue

            start = max(0, offset - 30)
            end = min(len(line), offset + 50)
            snippet = line[start:end]
            findings.append(
                Finding(
                    type=FINDING_TYPE,
                    file=str(path),
                    line=idx + 1,
                    severity='error',
                    fixable=False,
                    rule_id=RULE_ID,
                    description=(
                        'Shell command substitution `$(...)` in plan-marshall skill markdown '
                        "violates the persona-plan-marshall-agent 'no shell constructs' hard rule. "
                        'Replace with the documented two-call + text-substitution pattern.'
                    ),
                    extra={'rule': RULE_NAME, 'snippet': snippet},
                )
            )

    return [f.to_dict() for f in findings]


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def _skill_markdown_targets(marketplace_root: Path) -> list[Path]:
    """Return every ``*.md`` under ``marketplace_root/plan-marshall/skills/``."""
    skills_root = marketplace_root / 'plan-marshall' / 'skills'
    if not skills_root.is_dir():
        return []
    return sorted(p for p in skills_root.rglob('*.md') if p.is_file())


def analyze_shell_substitution_in_skills(marketplace_root: Path) -> list[dict]:
    """Scan plan-marshall skill markdown for forbidden ``$(`` substitutions.

    Walks ``marketplace_root/plan-marshall/skills/**/*.md`` and reports every
    ``$(`` occurrence outside the two permitted documentary contexts
    (inline-code mention on a rule-documenting line, or fenced block with
    ``markdown``/``text`` info-string).

    Parameters
    ----------
    marketplace_root:
        Path to the marketplace root (the directory that contains the
        ``plan-marshall``, ``pm-dev-java``, etc. bundle directories — i.e.
        ``<repo>/marketplace/bundles``).

    Returns
    -------
    list[dict]
        List of finding dicts (empty for a clean tree).
    """
    findings: list[dict] = []
    for md_path in _skill_markdown_targets(marketplace_root):
        findings.extend(_scan_file(md_path))
    return findings

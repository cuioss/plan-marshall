#!/usr/bin/env python3
"""Decision-log resolution-branch marker analyzer.

This module implements the ``resolution-branch-side-effect-undocumented`` rule,
which checks that every named branch inside a ``## Resolution`` section of a
skill's ``standards/*.md`` documents at least one observable side effect
(log write, metadata update, status transition, or artifact emission).

Detection algorithm
-------------------
1. Scan ``standards/*.md`` for ``## Resolution`` section headers
   (case-insensitive).
2. Within each Resolution section, enumerate branch headers matching
   ``### <Branch-Name>`` where ``<Branch-Name>`` is on the configurable
   ``RESOLUTION_BRANCH_ALLOWLIST``.
3. Collect all text in each branch body up to the next ``### `` or
   ``## `` header (or end of file).
4. Check the branch body for at least one occurrence of a side-effect
   keyword from ``SIDE_EFFECT_KEYWORDS``.
5. Branches that lack any keyword emit a finding.

Pattern alignment
-----------------
The analyzer mirrors ``_analyze_shell_active_tokens.py``:

- pure static analysis (regex-based, no subprocess execution)
- stdlib-only dependencies
- no mutation of any file

Configurable allowlists
------------------------
- ``RESOLUTION_BRANCH_ALLOWLIST``: The canonical branch name set.  A ``###``
  heading is treated as a resolution branch only when its normalized text
  (stripped, title-cased) appears in this allowlist.  Non-matching ``###``
  headings inside a Resolution section are ignored.

- ``SIDE_EFFECT_KEYWORDS``: Words that constitute an acceptable side-effect
  declaration.  The check is case-insensitive substring match inside the
  branch body.

Findings have the shape::

    {
        'rule_id': 'resolution-branch-side-effect-undocumented',
        'file': '<absolute markdown path>',
        'line': <int, 1-based line of the ### branch header>,
        'branch_name': '<branch heading text>',
    }

Public API
----------
- ``analyze_resolution_branch_markers(skill_dir)``: entry point — scans
  ``standards/*.md`` in one skill directory.
"""

from __future__ import annotations

import re
from pathlib import Path

RULE_ID = 'resolution-branch-side-effect-undocumented'

# ---------------------------------------------------------------------------
# Configurable allowlists
# ---------------------------------------------------------------------------

# Canonical resolution branch names (case-insensitive comparison via .lower()).
RESOLUTION_BRANCH_ALLOWLIST: frozenset[str] = frozenset(
    {
        'hold',
        'accept',
        'accept-with-rationale',
        'split',
        'defer',
        'reject',
        'approve',
        'escalate',
        'resolve',
        'suppress',
        'fix',
        'retry',
        'skip',
        'block',
        'override',
    }
)

# Keywords that constitute a documented side effect.
SIDE_EFFECT_KEYWORDS: frozenset[str] = frozenset(
    {
        'log',
        'metadata',
        'status',
        'artifact',
        'decision.log',
        'work.log',
        'record',
        'emit',
        'persist',
        'update',
        'write',
    }
)

# ---------------------------------------------------------------------------
# Regex helpers
# ---------------------------------------------------------------------------

# H2 section header — matches "## Resolution" (case-insensitive).
_RESOLUTION_H2_RE = re.compile(r'^##\s+resolution\s*$', re.IGNORECASE)

# H2 or H3 header — used to detect section boundaries.
_H2_RE = re.compile(r'^##\s+', re.MULTILINE)
_H3_RE = re.compile(r'^###\s+')

# H3 branch header inside a resolution section.
_H3_HEADER_RE = re.compile(r'^###\s+(.+)$')


def _is_resolution_branch(heading_text: str) -> bool:
    """Return True when ``heading_text`` is on the branch allowlist."""
    normalized = heading_text.strip().lower()
    return normalized in RESOLUTION_BRANCH_ALLOWLIST


def _has_side_effect_keyword(body: str) -> bool:
    """Return True when ``body`` contains at least one side-effect keyword."""
    body_lower = body.lower()
    return any(kw in body_lower for kw in SIDE_EFFECT_KEYWORDS)


# ---------------------------------------------------------------------------
# File-level scanner
# ---------------------------------------------------------------------------


def _scan_file(md_path: Path) -> list[dict]:
    """Scan one markdown file for resolution branches missing side-effect keywords."""
    try:
        text = md_path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        return []

    lines = text.splitlines()
    findings: list[dict] = []

    in_resolution = False
    current_branch_name: str | None = None
    current_branch_start_line: int = 0
    branch_body_lines: list[str] = []

    def _flush_branch() -> None:
        """Check the accumulated branch body and emit a finding if needed."""
        if current_branch_name is None:
            return
        body = '\n'.join(branch_body_lines)
        if not _has_side_effect_keyword(body):
            findings.append(
                {
                    'rule_id': RULE_ID,
                    'file': str(md_path),
                    'line': current_branch_start_line,
                    'branch_name': current_branch_name,
                }
            )

    for line_idx, line in enumerate(lines):
        line_no = line_idx + 1  # 1-based

        # Detect H2 headers — they either start or end a Resolution section.
        if _H2_RE.match(line):
            if in_resolution:
                # We're leaving the Resolution section.
                _flush_branch()
                current_branch_name = None
                branch_body_lines = []
            in_resolution = bool(_RESOLUTION_H2_RE.match(line))
            continue

        if not in_resolution:
            continue

        # Inside a Resolution section.
        h3_match = _H3_HEADER_RE.match(line)
        if h3_match:
            # New H3 heading — flush the previous branch if any.
            _flush_branch()
            heading_text = h3_match.group(1)
            if _is_resolution_branch(heading_text):
                current_branch_name = heading_text
                current_branch_start_line = line_no
                branch_body_lines = []
            else:
                # Non-branch H3 inside Resolution section — ignore.
                current_branch_name = None
                branch_body_lines = []
            continue

        # Accumulate branch body lines.
        if current_branch_name is not None:
            branch_body_lines.append(line)

    # Flush any open branch at end of file.
    _flush_branch()

    return findings


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def _standards_targets(skill_dir: Path) -> list[Path]:
    """Return markdown files in ``standards/`` subject to this rule."""
    targets: list[Path] = []
    standards_dir = skill_dir / 'standards'
    if standards_dir.is_dir():
        for md in sorted(standards_dir.glob('*.md')):
            if md.is_file():
                targets.append(md)
    return targets


def analyze_resolution_branch_markers(skill_dir: Path) -> list[dict]:
    """Scan ``skill_dir/standards/*.md`` for resolution branches without side-effect docs.

    Parameters
    ----------
    skill_dir:
        Path to the skill directory (contains ``SKILL.md``, ``standards/``, etc.).

    Returns
    -------
    list[dict]
        List of finding dicts.  Empty for a clean skill or one with no
        ``standards/*.md`` files containing ``## Resolution`` sections.
    """
    findings: list[dict] = []
    for md_path in _standards_targets(skill_dir):
        findings.extend(_scan_file(md_path))
    return findings

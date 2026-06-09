#!/usr/bin/env python3
"""Self-declared-rule self-compliance scanner for the ``skill-self-declared-rule-violation`` rule.

This module implements a deterministic regex-based static analyzer that
detects a single self-referential defect class: a ``SKILL.md`` that *declares*
a numbering-discipline rule in its own body (a passage prohibiting
sub-numbering / mandating flat step numbering) yet *violates* that same rule
with sub-numbered step headings (``1a``/``3a``/``5a``-style labels) elsewhere
in the same file.

Why only the numbering-discipline class
---------------------------------------
The numbering-discipline rule is the ONE
self-referential rule class that is regex-checkable. Non-regex-checkable
self-rule classes (e.g. tone, structure, naming) deliberately stay out of
scope — they have no deterministic surfacer and forcing them into a heuristic
would be false-positive-prone. This analyzer is narrow by design.

Self-referential, not a global ban
----------------------------------
The rule is self-referential: it fires ONLY when a file declares the rule AND
violates it. A ``SKILL.md`` that uses sub-numbered headings WITHOUT declaring
any flat-numbering rule is NOT flagged — sub-numbering is permitted in the
general case; this analyzer enforces only the self-consistency contract that a
file authoring a numbering rule must obey it.

Scope
-----
``SKILL.md`` files under:

1. ``marketplace/bundles/*/{skills,agents,commands}/**``.
2. the project-local ``.claude/skills/**`` tree (resolved relative to the
   marketplace bundles root).

Only ``SKILL.md`` is scanned — the numbering-discipline rule is a property of
a skill's workflow document, not of every markdown file.

Pattern alignment
-----------------
The analyzer mirrors ``_analyze_lesson_id_in_skill_prose.py`` and
``_analyze_allowed_tools_drift.py``:

- pure static analysis (no subprocess execution, no imports of target scripts)
- regex-driven extraction from source
- stdlib-only dependencies
- no mutation of any file

Detection
---------
1. **Rule declaration** — the file declares a numbering-discipline rule when
   its body matches any of the declaration phrases (``flat-numbering``,
   ``flat numbering``, ``no sub-numbering``, ``no-sub-numbering``,
   ``prohibit sub-numbering``, ``without sub-numbering``, etc.). The match is
   case-insensitive and ignores the YAML frontmatter.
2. **Rule violation** — when (1) holds, scan the file's own step headings for
   the banned sub-numbered shape: a markdown heading (``##`` .. ``####``) whose
   text is ``Step Nx`` or a bare ``Nx`` label (digit immediately followed by a
   lowercase letter), e.g. ``### Step 1a`` or ``#### 3b``.

Each self-violating heading produces one finding that names both the declared
rule and the offending heading.

Exemptions
----------
- **YAML frontmatter** — heading-shaped lines inside the leading ``---`` fences
  are not body content and are skipped for both declaration and violation
  detection.
- **Fenced code block** — lines inside ``` ``` ``` fences are exempt: a
  heading-shaped line inside an example block is not a live heading, and a
  declaration phrase inside an example block is not an authored rule.
- **Suppression marker** — an inline ``<!-- doctor-ignore: self-declared-rule -->``
  on the same line as a violating heading, or on the immediately preceding
  line, suppresses the finding on the marked line only.

Findings have the shape::

    {
        'rule_id': 'skill-self-declared-rule-violation',
        'type': 'skill_self_declared_rule_violation',
        'rule': 'analyze_self_declared_rule_compliance',
        'file': '<absolute source path>',
        'line': <int, 1-based>,
        'severity': 'warning',
        'fixable': False,
        'snippet': '<the offending heading text>',
        'description': '<human-readable self-violation description>. See rule-catalog.md.',
    }

Public API
----------
- ``analyze_self_declared_rule_compliance(marketplace_root)``: entry point —
  scans every ``SKILL.md`` under ``marketplace_root/*/{skills,agents,commands}/**``
  PLUS every ``SKILL.md`` under the sibling project-local ``.claude/skills/**``
  tree.
"""

from __future__ import annotations

import re
from pathlib import Path

RULE_ID = 'skill-self-declared-rule-violation'
RULE_NAME = 'analyze_self_declared_rule_compliance'
FINDING_TYPE = 'skill_self_declared_rule_violation'

# ---------------------------------------------------------------------------
# Detection patterns
# ---------------------------------------------------------------------------

# Numbering-discipline rule declaration. Any of these phrases in the body
# signals that the file authors a flat-numbering / no-sub-numbering rule.
# Case-insensitive. The hyphen/space variants are unified by treating both
# the literal hyphen and a single space as a separator.
_RULE_DECLARATION_RE = re.compile(
    r'(?:'
    r'flat[- ]numbering'
    r'|no[- ]sub[- ]numbering'
    r'|sub[- ]numbering[- ](?:is[- ])?(?:prohibited|forbidden|banned)'
    r'|(?:prohibit|forbid|ban|avoid|no)[- ]sub[- ]numbered'
    r'|(?:prohibit|forbid|ban|without)[- ]sub[- ]numbering'
    r'|flat[- ](?:step[- ])?number'
    r')',
    re.IGNORECASE,
)

# Banned sub-numbered step heading: a markdown heading (## .. ####) whose
# leading label is ``Step Nx`` or a bare ``Nx`` where N is a digit and x is a
# lowercase letter (e.g. ``### Step 1a``, ``#### 3b``, ``## Step 12a``).
_SUBNUMBERED_HEADING_RE = re.compile(
    r'^#{2,4}\s*(?:Step\s*)?\d+[a-z]\b',
)

# Fenced-block boundaries.
_FENCE_OPEN_RE = re.compile(r'^\s*```\s*([A-Za-z0-9_+-]*)\s*$')
_FENCE_CLOSE_RE = re.compile(r'^\s*```\s*$')

# Inline suppression marker.
_SUPPRESS_MARKER = '<!-- doctor-ignore: self-declared-rule -->'


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_frontmatter_set(lines: list[str]) -> set[int]:
    """Return the 0-based indices of lines inside leading YAML frontmatter."""
    inside: set[int] = set()
    if not lines or lines[0].strip() != '---':
        return inside
    inside.add(0)
    for idx in range(1, len(lines)):
        inside.add(idx)
        if lines[idx].strip() == '---':
            return inside
    # Unterminated frontmatter — treat conservatively as not frontmatter.
    return set()


def _build_fence_set(lines: list[str]) -> set[int]:
    """Return the 0-based indices of lines inside any fenced block.

    The fence delimiter lines themselves are NOT included — only the body
    lines between an opening and closing fence.
    """
    inside: set[int] = set()
    in_fence = False
    for idx, line in enumerate(lines):
        if not in_fence:
            if _FENCE_OPEN_RE.match(line):
                in_fence = True
        else:
            if _FENCE_CLOSE_RE.match(line):
                in_fence = False
            else:
                inside.add(idx)
    return inside


def _line_has_suppress_marker(line: str) -> bool:
    return _SUPPRESS_MARKER in line


def _declares_numbering_rule(
    lines: list[str], frontmatter: set[int], fences: set[int]
) -> bool:
    """Return True if the file declares a numbering-discipline rule in its body.

    Frontmatter and fenced-code-block lines are excluded — a declaration phrase
    inside a code example is not an authored rule.
    """
    for idx, line in enumerate(lines):
        if idx in frontmatter or idx in fences:
            continue
        if _RULE_DECLARATION_RE.search(line):
            return True
    return False


# ---------------------------------------------------------------------------
# File-level scanner
# ---------------------------------------------------------------------------


def _scan_file(path: Path) -> list[dict]:
    """Scan a single ``SKILL.md`` for self-declared-rule violations."""
    try:
        text = path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError) as exc:
        return [
            {
                'rule_id': RULE_ID,
                'type': 'file_read_error',
                'rule': RULE_NAME,
                'file': str(path),
                'line': 0,
                'severity': 'error',
                'fixable': False,
                'snippet': '',
                'description': f'Could not read file: {exc}',
            }
        ]

    lines = text.splitlines()
    frontmatter = _build_frontmatter_set(lines)
    fences = _build_fence_set(lines)

    # The rule is self-referential: only files that DECLARE a numbering rule
    # are checked for violations. A file that uses sub-numbering without
    # declaring such a rule is not flagged.
    if not _declares_numbering_rule(lines, frontmatter, fences):
        return []

    findings: list[dict] = []
    for idx, line in enumerate(lines):
        if idx in frontmatter or idx in fences:
            continue
        if not _SUBNUMBERED_HEADING_RE.match(line):
            continue

        # Suppression: same line, or a standalone marker on the preceding line.
        suppressed = _line_has_suppress_marker(line)
        if not suppressed and idx > 0:
            prev = lines[idx - 1]
            prev_is_heading = bool(_SUBNUMBERED_HEADING_RE.match(prev))
            if _line_has_suppress_marker(prev) and not prev_is_heading:
                suppressed = True
        if suppressed:
            continue

        heading_text = line.strip()
        findings.append(
            {
                'rule_id': RULE_ID,
                'type': FINDING_TYPE,
                'rule': RULE_NAME,
                'file': str(path),
                'line': idx + 1,  # 1-based
                'severity': 'warning',
                'fixable': False,
                'snippet': heading_text,
                'description': (
                    f'Heading `{heading_text}` uses sub-numbering, but this '
                    f'SKILL.md declares a flat-numbering / no-sub-numbering '
                    f'rule in its own body — a file that authors a numbering '
                    f'rule must obey it. Renumber to a flat sequence. '
                    f'See rule-catalog.md.'
                ),
            }
        )

    return findings


# ---------------------------------------------------------------------------
# Target enumeration
# ---------------------------------------------------------------------------


def _skill_source_targets(marketplace_root: Path) -> list[Path]:
    """Return every in-scope ``SKILL.md`` under the bundles tree.

    Scope: ``marketplace_root/*/{skills,agents,commands}/**/SKILL.md``.
    """
    if not marketplace_root.is_dir():
        return []
    results: list[Path] = []
    try:
        bundle_dirs = sorted(marketplace_root.iterdir())
    except OSError:
        bundle_dirs = []
    for bundle_dir in bundle_dirs:
        if not bundle_dir.is_dir():
            continue
        for sub in ('skills', 'agents', 'commands'):
            sub_dir = bundle_dir / sub
            if not sub_dir.is_dir():
                continue
            try:
                for src in sorted(sub_dir.rglob('SKILL.md')):
                    if src.is_file():
                        results.append(src)
            except OSError:
                continue
    return results


def _claude_skills_root(marketplace_root: Path) -> Path:
    """Resolve the project-local ``.claude/skills`` tree from ``marketplace_root``.

    ``marketplace_root`` is ``<repo>/marketplace/bundles``; the project-local
    skills tree is ``<repo>/.claude/skills`` — two levels up, then
    ``.claude/skills``.
    """
    return marketplace_root.parent.parent / '.claude' / 'skills'


def _claude_skill_source_targets(marketplace_root: Path) -> list[Path]:
    """Return every ``SKILL.md`` under the project-local ``.claude/skills/**`` tree."""
    skills_root = _claude_skills_root(marketplace_root)
    if not skills_root.is_dir():
        return []
    try:
        sources = sorted(skills_root.rglob('SKILL.md'))
    except OSError:
        return []
    return [src for src in sources if src.is_file()]


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def analyze_self_declared_rule_compliance(marketplace_root: Path) -> list[dict]:
    """Scan ``SKILL.md`` files for self-declared numbering-rule violations.

    Walks two trees and reports every sub-numbered step heading in a file that
    declares a flat-numbering / no-sub-numbering rule in its own body:

    - ``marketplace_root/*/{skills,agents,commands}/**/SKILL.md``.
    - ``<repo>/.claude/skills/**/SKILL.md``.

    The check is self-referential — a file that uses sub-numbering without
    declaring such a rule produces no findings.

    Parameters
    ----------
    marketplace_root:
        Path to the marketplace bundles root (the directory that contains
        the ``plan-marshall``, ``pm-dev-java``, etc. bundle directories —
        i.e. ``<repo>/marketplace/bundles``).

    Returns
    -------
    list[dict]
        List of finding dicts (empty for a clean tree).
    """
    findings: list[dict] = []
    for path in _skill_source_targets(marketplace_root):
        findings.extend(_scan_file(path))
    for path in _claude_skill_source_targets(marketplace_root):
        findings.extend(_scan_file(path))
    return findings

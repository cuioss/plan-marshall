#!/usr/bin/env python3
"""Lesson-ID scanner for the ``no-lesson-id-in-skill-prose`` rule.

This module implements a deterministic regex-based static analyzer that
detects narrative lesson-ID citations inside markdown files under
``marketplace/bundles/*/{skills,agents,commands}/**/*.md``. Such citations
add no durable value to the rule/decision content and should be stripped
in favour of bare prose that names the rule itself.

Pattern alignment
-----------------
The analyzer mirrors ``_analyze_shell_substitution_in_skills.py``:

- pure static analysis (no subprocess execution, no imports of target scripts)
- regex-driven extraction from markdown source
- stdlib-only dependencies
- no mutation of any file

Detection
---------
Two lesson-ID format families are recognised:

1. ``YYYY-MM-DD-NNN`` (e.g., ``2026-04-17-012``)
2. ``YYYY-MM-DD-HH-NNN`` (e.g., ``2026-04-29-23-002``)

Prose-prefixed forms ``lesson XXX`` and ``lesson-XXX`` are also recognised.

Five structurally-defined documentary contexts are exempt:

1. **Allowlisted skill path** — files under canonical lesson-handling skills
   (manage-lessons/**, phase-6-finalize/workflow/lessons-*.md,
   phase-6-finalize/standards/lessons-*.md) and the rule-provenance catalog
   itself (plugin-doctor/references/rule-provenance.md). These files operate
   ON lessons as domain content.
2. **YAML frontmatter** — between the leading ``---`` fences at the start of
   a markdown file.
3. **Fenced code block** — between ``` ``` ``` fences (any info-string).
4. **Source: line** — lines whose payload is a structured provenance source
   declaration.
5. **Inline-code span** — a lesson-ID inside an inline-code span
   (`` `…` ``). Token references in code spans are not narrative prose.

In addition, an inline suppression marker
``<!-- doctor-ignore: lesson-id-prose -->`` placed on the same line as a
match, or on the immediately preceding line, suppresses the finding on the
marked line only.

Findings have the shape::

    {
        'rule_id': 'no-lesson-id-in-skill-prose',
        'type': 'lesson_id_in_skill_prose',
        'rule': 'analyze_lesson_id_in_skill_prose',
        'file': '<absolute markdown path>',
        'line': <int, 1-based>,
        'severity': 'warning',
        'fixable': False,
        'snippet': '<matched lesson-ID token>',
        'description': 'Narrative lesson-ID citation — strip the ID and trivia, keep the rule content. See rule-catalog.md.',
    }

Public API
----------
- ``analyze_lesson_id_in_skill_prose(marketplace_root)``: entry point —
  scans every ``*.md`` under
  ``marketplace_root/*/{skills,agents,commands}/**``.
"""

from __future__ import annotations

import re
from pathlib import Path

RULE_ID = 'no-lesson-id-in-skill-prose'
RULE_NAME = 'analyze_lesson_id_in_skill_prose'
FINDING_TYPE = 'lesson_id_in_skill_prose'

# ---------------------------------------------------------------------------
# Detection patterns
# ---------------------------------------------------------------------------

# Lesson-ID token: optional `lesson ` or `lesson-` prefix + date-based id.
# Two format families: YYYY-MM-DD-NNN and YYYY-MM-DD-HH-NNN.
_LESSON_ID_RE = re.compile(
    r'\b(?:lesson[- ])?(\d{4}-\d{2}-\d{2}(?:-\d{2})?-\d{3})\b',
    re.IGNORECASE,
)

# Inline-code span detection (matches `...`).
_INLINE_CODE_RE = re.compile(r'`([^`]+)`')

# Fenced-block boundaries.
_FENCE_OPEN_RE = re.compile(r'^\s*```\s*([A-Za-z0-9_+-]*)\s*$')
_FENCE_CLOSE_RE = re.compile(r'^\s*```\s*$')

# Source: line — structured provenance citation marker.
_SOURCE_LINE_RE = re.compile(r'^\s*(?:[-*]\s*)?\*{0,2}Source:\*{0,2}', re.IGNORECASE)

# Inline suppression marker.
_SUPPRESS_MARKER = '<!-- doctor-ignore: lesson-id-prose -->'


# ---------------------------------------------------------------------------
# Allowlist
# ---------------------------------------------------------------------------


def _is_allowlisted(rel_to_bundles: str) -> bool:
    """Return True if the file path is in the lesson-domain allowlist."""
    if rel_to_bundles.startswith('plan-marshall/skills/manage-lessons/'):
        return True
    if rel_to_bundles.startswith('plan-marshall/skills/phase-6-finalize/workflow/lessons-'):
        return True
    if rel_to_bundles.startswith('plan-marshall/skills/phase-6-finalize/standards/lessons-'):
        return True
    if rel_to_bundles == 'pm-plugin-development/skills/plugin-doctor/references/rule-provenance.md':
        return True
    return False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_fence_map(lines: list[str]) -> dict[int, str]:
    """Map 0-based line indices inside any fenced block to the info-string.

    Lines that are NOT inside a fence are absent from the map. The fence
    delimiter lines (the opening / closing ``` ``` ```) are also absent —
    only the body lines between the delimiters appear.
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
    # Unterminated frontmatter — treat conservatively as not frontmatter
    # (the spec requires both fences); reset.
    return set()


def _inline_code_spans(line: str) -> list[tuple[int, int]]:
    """Return (start, end) character offsets of inline-code spans on ``line``."""
    return [(m.start(), m.end()) for m in _INLINE_CODE_RE.finditer(line)]


def _offset_in_inline_code(offset: int, spans: list[tuple[int, int]]) -> bool:
    """Return True if ``offset`` lies within any of the inline-code spans."""
    return any(start <= offset < end for start, end in spans)


def _line_has_suppress_marker(line: str) -> bool:
    return _SUPPRESS_MARKER in line


# ---------------------------------------------------------------------------
# File-level scanner
# ---------------------------------------------------------------------------


def _scan_file(path: Path, rel_to_bundles: str) -> list[dict]:
    """Scan a single markdown file and return all findings.

    ``rel_to_bundles`` is the file path relative to
    ``marketplace/bundles/`` (e.g.,
    ``plan-marshall/skills/phase-4-plan/SKILL.md``) — used for allowlist
    matching.
    """
    if _is_allowlisted(rel_to_bundles):
        return []

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
    fence_map = _build_fence_map(lines)
    frontmatter = _build_frontmatter_set(lines)

    findings: list[dict] = []

    for idx, line in enumerate(lines):
        # Skip lines inside YAML frontmatter or fenced code blocks (any
        # info-string) outright.
        if idx in frontmatter:
            continue
        if idx in fence_map:
            continue
        # Skip Source: provenance lines.
        if _SOURCE_LINE_RE.match(line):
            continue
        # Quick pre-check before regex scan.
        matches = list(_LESSON_ID_RE.finditer(line))
        if not matches:
            continue

        # Suppression marker:
        #   - Same line: suppresses findings on this line.
        #   - Preceding line: suppresses findings on this line ONLY when the
        #     preceding line is a standalone marker (no lesson-ID on it).
        #     Otherwise the marker on the preceding line was consumed by its
        #     own same-line suppression and must not double-suppress here.
        suppressed = _line_has_suppress_marker(line)
        if not suppressed and idx > 0:
            prev = lines[idx - 1]
            if _line_has_suppress_marker(prev) and not _LESSON_ID_RE.search(prev):
                suppressed = True
        if suppressed:
            continue

        spans = _inline_code_spans(line)

        for m in matches:
            offset = m.start()

            # Skip matches inside inline-code spans.
            if _offset_in_inline_code(offset, spans):
                continue

            findings.append(
                {
                    'rule_id': RULE_ID,
                    'type': FINDING_TYPE,
                    'rule': RULE_NAME,
                    'file': str(path),
                    'line': idx + 1,
                    'severity': 'warning',
                    'fixable': False,
                    'snippet': m.group(0),
                    'description': (
                        'Narrative lesson-ID citation — strip the ID and trivia, '
                        'keep the rule content. See rule-catalog.md.'
                    ),
                }
            )

    return findings


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def _skill_markdown_targets(marketplace_root: Path) -> list[tuple[Path, str]]:
    """Return ``(absolute_path, rel_to_bundles)`` for every in-scope ``*.md``.

    Scope: ``marketplace_root/*/{skills,agents,commands}/**/*.md``.
    """
    if not marketplace_root.is_dir():
        return []
    results: list[tuple[Path, str]] = []
    for bundle_dir in sorted(marketplace_root.iterdir()):
        if not bundle_dir.is_dir():
            continue
        for sub in ('skills', 'agents', 'commands'):
            sub_dir = bundle_dir / sub
            if not sub_dir.is_dir():
                continue
            for md in sorted(sub_dir.rglob('*.md')):
                if md.is_file():
                    rel = str(md.relative_to(marketplace_root))
                    results.append((md, rel))
    return results


def analyze_lesson_id_in_skill_prose(marketplace_root: Path) -> list[dict]:
    """Scan skill markdown for narrative lesson-ID citations.

    Walks ``marketplace_root/*/{skills,agents,commands}/**/*.md`` and reports
    every lesson-ID occurrence outside the documented exempt contexts
    (allowlisted skill path, YAML frontmatter, fenced code block,
    ``Source:`` provenance line, inline-code span, or
    ``<!-- doctor-ignore: lesson-id-prose -->`` suppression marker).

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
    for md_path, rel in _skill_markdown_targets(marketplace_root):
        findings.extend(_scan_file(md_path, rel))
    return findings

#!/usr/bin/env python3
"""Historical-prose scanner for the ``no-historical-prose-in-skills`` rule.

This module implements a deterministic regex-based static analyzer that
detects historical and transitional narrative patterns inside markdown files
under ``marketplace/bundles/*/{skills,agents,commands}/**/*.md``. Such
patterns describe past events, rejected alternatives, or implementation
history rather than the current state of the rule or contract.

Marketplace skill documents describe current requirements only. Historical
context — why a rule exists, what was tried before, which plan introduced it
— belongs in commit messages, PR descriptions, and (temporarily) lessons.
Skills that retain historical narrative drift as the underlying system
evolves; readers cannot tell which clauses are still authoritative.

Pattern alignment
-----------------
The analyzer mirrors ``_analyze_lesson_id_in_skill_prose.py``:

- pure static analysis (no subprocess execution, no imports of target scripts)
- regex-driven extraction from markdown source
- stdlib-only dependencies
- no mutation of any file

Detection
---------
Seven pattern families are recognized (all case-insensitive):

1. **Driving-lesson prefix** — ``Driving lesson:`` used as a bullet or
   inline annotation that cites the originating lesson.
   Example: ``- Driving lesson: `2026-04-30-23-001` (description)``

2. **Back-reference prefix** — ``Back-reference:`` used to cite the
   originating plan/lesson/PR that established a rule.
   Example: ``d. **Back-reference**: this rule originates from lesson``

3. **Earlier-proposal pattern** — prose describing an alternative approach
   that was considered and rejected.
   Example: ``An earlier proposal ... suggested ... That approach was rejected``

4. **Historical-activation pattern** — describing when a contract/feature
   was "activated" or "introduced" in terms of a past plan/lesson.
   Example: ``The contract was activated end-to-end by lesson``

5. **Seed-failure/observation pattern** — citing the "seed failure" or
   "seed observation" that motivated a rule.
   Example: ``See lesson ... for the seed observation``
   Example: ``the seed failure (lesson ...) is the canonical instance``

6. **Plan/task-authorship pattern** — describing something as "added in
   TASK-NNN of plan" or "added by deliverable N of this plan", which
   anchors the content to a historical implementation event.
   Example: ``added in TASK-007 of plan``
   Example: ``added by deliverable 9 of this plan``

7. **Guard-introduction pattern** — ``introduced in manage-tasks``,
   ``guard introduced in``, etc. that describe when/where a guard was added
   rather than what it does.
   Example: ``guard introduced in `manage-tasks finalize-step```

Allowlisted contexts (exempt from detection):

1. **Allowlisted skill path** — files under canonical lesson/plan-handling
   skills: manage-lessons/**, phase-6-finalize/workflow/lessons-*.md,
   phase-6-finalize/standards/lessons-*.md, plan-retrospective/**,
   plugin-doctor/references/rule-provenance.md, and plan-doctor/standards/**
   (plan-doctor's check-lesson-id-references.md uses historical context
   legitimately as part of its rule rationale table).
2. **YAML frontmatter** — between the leading ``---`` fences.
3. **Fenced code block** — between ``` ``` ``` fences (any info-string).
4. **Source: line** — structured provenance citation marker.
5. **Inline-code span** — historical token inside backticks is a code
   reference, not narrative prose.

Findings have the shape::

    {
        'rule_id': 'no-historical-prose-in-skills',
        'type': 'historical_prose_in_skills',
        'rule': 'analyze_historical_prose_in_skills',
        'file': '<absolute markdown path>',
        'line': <int, 1-based>,
        'severity': 'warning',
        'fixable': False,
        'snippet': '<matched text excerpt>',
        'description': 'Historical/transitional narrative — rewrite as a present-tense rule. See rule-catalog.md.',
        'pattern_family': '<one of the seven family names>',
    }

Public API
----------
- ``analyze_historical_prose_in_skills(marketplace_root)``: entry point —
  scans every ``*.md`` under
  ``marketplace_root/*/{skills,agents,commands}/**``.
"""

from __future__ import annotations

import re
from pathlib import Path

RULE_ID = 'no-historical-prose-in-skills'
RULE_NAME = 'analyze_historical_prose_in_skills'
FINDING_TYPE = 'historical_prose_in_skills'

# ---------------------------------------------------------------------------
# Detection patterns
# ---------------------------------------------------------------------------

# Family 1: Driving-lesson prefix (bullet or inline).
# Matches "Driving lesson:" or "- Driving lesson:" at the start of a word
# boundary, case-insensitive.
_DRIVING_LESSON_RE = re.compile(
    r'\bdriving lesson\s*:',
    re.IGNORECASE,
)

# Family 2: Back-reference prefix.
# Allow optional markdown bold markers (**) between "reference" and the
# colon/dash so "**Back-reference**:" is detected alongside plain
# "Back-reference:".
_BACK_REFERENCE_RE = re.compile(
    r'\bback[- ]?reference\*{0,2}\s*[:\-—–]',
    re.IGNORECASE,
)

# Family 3: Earlier-proposal / earlier-version / earlier-approach pattern.
_EARLIER_PROPOSAL_RE = re.compile(
    r'\b(?:an\s+earlier|the\s+earlier|earlier\s+(?:proposal|approach|version|alternative|design|form))',
    re.IGNORECASE,
)

# Family 4: Historical-activation pattern.
# "activated end-to-end by lesson", "was activated by", etc.
_ACTIVATION_RE = re.compile(
    r'\b(?:activated|introduced)\s+(?:end-to-end\s+)?by\s+(?:lesson|plan|the\s+lesson)',
    re.IGNORECASE,
)

# Family 5: Seed-failure / seed-observation pattern.
_SEED_RE = re.compile(
    r'\bseed\s+(?:failure|observation|defect|gap)\b',
    re.IGNORECASE,
)

# Family 6: Plan/task-authorship pattern.
# "added in TASK-NNN of plan", "added by deliverable N of this plan".
_PLAN_AUTHORSHIP_RE = re.compile(
    r'\badded\s+(?:in|by)\s+(?:TASK-\w+|deliverable\s+\d+)(?:\s+(?:of|in))?\b',
    re.IGNORECASE,
)

# Family 7: Guard/feature-introduction pattern.
# "guard introduced in", "introduced in manage-tasks".
_GUARD_INTRODUCED_RE = re.compile(
    r'\b(?:guard|check|rule|validator|feature)\s+introduced\s+in\b',
    re.IGNORECASE,
)

# All pattern families as (name, compiled_regex) pairs.
_PATTERNS: list[tuple[str, re.Pattern]] = [
    ('driving_lesson_prefix', _DRIVING_LESSON_RE),
    ('back_reference_prefix', _BACK_REFERENCE_RE),
    ('earlier_proposal', _EARLIER_PROPOSAL_RE),
    ('historical_activation', _ACTIVATION_RE),
    ('seed_failure_observation', _SEED_RE),
    ('plan_task_authorship', _PLAN_AUTHORSHIP_RE),
    ('guard_introduction', _GUARD_INTRODUCED_RE),
]

# Inline-code span detection (matches `...`).
_INLINE_CODE_RE = re.compile(r'`([^`]+)`')

# Fenced-block boundaries.
_FENCE_OPEN_RE = re.compile(r'^\s*```\s*([A-Za-z0-9_+-]*)\s*$')
_FENCE_CLOSE_RE = re.compile(r'^\s*```\s*$')

# Source: line — structured provenance citation marker.
_SOURCE_LINE_RE = re.compile(r'^\s*(?:[-*]\s*)?\*{0,2}Source:\*{0,2}', re.IGNORECASE)

# Inline suppression marker.
_SUPPRESS_MARKER = '<!-- doctor-ignore: historical-prose -->'


# ---------------------------------------------------------------------------
# Allowlist
# ---------------------------------------------------------------------------


def _is_allowlisted(rel_to_bundles: str) -> bool:
    """Return True if the file path is in the historical-context allowlist."""
    # Lesson-handling skills operate ON lessons — historical context is part
    # of their domain content.
    if rel_to_bundles.startswith('plan-marshall/skills/manage-lessons/'):
        return True
    if rel_to_bundles.startswith('plan-marshall/skills/phase-6-finalize/workflow/lessons-'):
        return True
    if rel_to_bundles.startswith('plan-marshall/skills/phase-6-finalize/standards/lessons-'):
        return True
    # Plan-retrospective analyses historical log data — historical context is
    # intrinsic to its purpose.
    if rel_to_bundles.startswith('plan-marshall/skills/plan-retrospective/'):
        return True
    # Rule-provenance catalog is the canonical citation home for plugin-doctor
    # rules — lessons and plan references are the provenance, not prose drift.
    if rel_to_bundles == 'pm-plugin-development/skills/plugin-doctor/references/rule-provenance.md':
        return True
    # Rule-catalog.md describes rules and their rationale; lesson/plan
    # citations in the Rationale fields are structural provenance, not prose.
    if rel_to_bundles == 'pm-plugin-development/skills/plugin-doctor/references/rule-catalog.md':
        return True
    # plan-doctor standards describe check rules that reference lessons as
    # first-class content (checking that lesson IDs are valid references).
    if rel_to_bundles.startswith('plan-marshall/skills/plan-doctor/standards/'):
        return True
    return False


# ---------------------------------------------------------------------------
# Helpers (mirrors _analyze_lesson_id_in_skill_prose.py)
# ---------------------------------------------------------------------------


def _build_fence_map(lines: list[str]) -> dict[int, str]:
    """Map 0-based line indices inside any fenced block to the info-string."""
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
    """Scan a single markdown file and return all findings."""
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
                'pattern_family': 'file_read_error',
            }
        ]

    lines = text.splitlines()
    fence_map = _build_fence_map(lines)
    frontmatter = _build_frontmatter_set(lines)

    findings: list[dict] = []

    for idx, line in enumerate(lines):
        # Skip lines inside YAML frontmatter or fenced code blocks.
        if idx in frontmatter:
            continue
        if idx in fence_map:
            continue
        # Skip Source: provenance lines.
        if _SOURCE_LINE_RE.match(line):
            continue

        # Quick pre-check: does any pattern fire on this line?
        any_pattern_match = any(pat.search(line) for _, pat in _PATTERNS)
        if not any_pattern_match:
            continue

        # Suppression marker check.
        suppressed = _line_has_suppress_marker(line)
        if not suppressed and idx > 0:
            prev = lines[idx - 1]
            prev_has_pattern = any(pat.search(prev) for _, pat in _PATTERNS)
            if _line_has_suppress_marker(prev) and not prev_has_pattern:
                suppressed = True
        if suppressed:
            continue

        spans = _inline_code_spans(line)

        # Emit one finding per matching pattern family on this line.
        # Deduplicate: emit at most one finding per (line, family).
        seen_families: set[str] = set()
        for family_name, pattern in _PATTERNS:
            if family_name in seen_families:
                continue
            m = pattern.search(line)
            if not m:
                continue
            # Skip matches whose start offset is fully inside an inline-code
            # span — those are token references, not prose.
            if _offset_in_inline_code(m.start(), spans):
                continue
            seen_families.add(family_name)
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
                        'Historical/transitional narrative — rewrite as a '
                        'present-tense rule or remove entirely. '
                        'See rule-catalog.md.'
                    ),
                    'pattern_family': family_name,
                }
            )

    return findings


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def _skill_markdown_targets(marketplace_root: Path) -> list[tuple[Path, str]]:
    """Return ``(absolute_path, rel_to_bundles)`` for every in-scope ``*.md``."""
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
                    rel = str(md.relative_to(marketplace_root)).replace('\\', '/')
                    results.append((md, rel))
    return results


def analyze_historical_prose_in_skills(marketplace_root: Path) -> list[dict]:
    """Scan skill markdown for historical/transitional narrative patterns.

    Walks ``marketplace_root/*/{skills,agents,commands}/**/*.md`` and reports
    every historical-prose occurrence outside the documented exempt contexts
    (allowlisted skill path, YAML frontmatter, fenced code block,
    ``Source:`` provenance line, inline-code span, or
    ``<!-- doctor-ignore: historical-prose -->`` suppression marker).

    Parameters
    ----------
    marketplace_root:
        Path to the marketplace bundles root (the directory that contains
        the ``plan-marshall``, ``pm-dev-java``, etc. bundle directories).

    Returns
    -------
    list[dict]
        List of finding dicts (empty for a clean tree).
    """
    findings: list[dict] = []
    for md_path, rel in _skill_markdown_targets(marketplace_root):
        findings.extend(_scan_file(md_path, rel))
    return findings

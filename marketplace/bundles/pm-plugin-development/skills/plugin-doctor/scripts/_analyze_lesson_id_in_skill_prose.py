#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Lesson-ID scanner for the ``no-lesson-id-in-skill-prose`` rule.

This module implements a deterministic regex-based static analyzer that
detects narrative lesson-ID citations across three file classes:

1. Markdown (``*.md``) under
   ``marketplace/bundles/*/{skills,agents,commands}/**``.
2. Python (``*.py``) under
   ``marketplace/bundles/*/{skills,agents,commands}/**`` — citations in
   comments, docstrings, and string literals.
3. Both markdown and Python under the project-local ``.claude/skills/**``
   tree (resolved relative to the marketplace bundles root).

Such citations add no durable value to the rule/decision content and should
be stripped in favour of bare prose that names the codified rule itself.

Pattern alignment
-----------------
The analyzer mirrors ``_analyze_shell_substitution_in_skills.py``:

- pure static analysis (no subprocess execution, no imports of target scripts)
- regex-driven extraction from source
- stdlib-only dependencies
- no mutation of any file

Detection
---------
Two lesson-ID format families are recognised:

1. ``YYYY-MM-DD-NNN`` (a date plus a 3-digit index)
2. ``YYYY-MM-DD-HH-NNN`` (a date plus an hour plus a 3-digit index)

Prose-prefixed forms ``lesson XXX`` and ``lesson-XXX`` are also recognised,
including the backtick-wrapped form ``lesson `YYYY-...``` where "lesson" is
prose context but the ID itself sits inside an inline-code span. That form is
a narrative citation — the reader is pointed at an ephemeral lesson file for
context — and must be stripped exactly like the non-backtick form.

Exempt contexts depend on the file class.

For **markdown** sources, five structurally-defined documentary contexts are
exempt:

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
5. **Bare inline-code span** — a lesson-ID inside an inline-code span WITHOUT
   a prose ``lesson`` prefix immediately before the span. Bare IDs in code spans
   are token references, not narrative prose. The ``lesson `YYYY-...``` form is
   NOT exempt: "lesson" is prose context and signals a narrative citation
   regardless of whether the ID token itself is backtick-wrapped.

For **Python** sources, the markdown-only structural exemptions (frontmatter,
fenced code block, Source: line, inline-code span) do NOT apply — the entire
point of scanning ``.py`` is to catch lesson IDs in comments, docstrings, and
string literals, so those contexts are deliberately in scope. Only the
path-allowlist applies to Python.

In addition, for both file classes a per-file frontmatter disable list
(``plugin-doctor-disable: [no-lesson-id-in-skill-prose]``) suppresses every
finding in that file (file-scoped, via the shared substrate).

The path-allowlist (``_is_allowlisted``) is authoritative for both file
classes inside ``marketplace/bundles/``. The project-local ``.claude/skills/**``
tree has no allowlisted members — it is scanned in full.

Findings have the shape::

    {
        'rule_id': 'no-lesson-id-in-skill-prose',
        'type': 'lesson_id_in_skill_prose',
        'rule': 'analyze_lesson_id_in_skill_prose',
        'file': '<absolute source path>',
        'line': <int, 1-based>,
        'severity': 'warning',
        'fixable': False,
        'snippet': '<matched lesson-ID token>',
        'description': 'Narrative lesson-ID citation — strip the ID and trivia, keep the rule content. See rule-catalog.md.',
    }

Public API
----------
- ``analyze_lesson_id_in_skill_prose(marketplace_root)``: entry point — scans
  every ``*.md`` and ``*.py`` under
  ``marketplace_root/*/{skills,agents,commands}/**`` PLUS every ``*.md`` and
  ``*.py`` under the sibling project-local ``.claude/skills/**`` tree.
"""

from __future__ import annotations

import re
from pathlib import Path

from _analyze_shared import (
    _config_layer_suppresses,
    load_default_suppression_config,
    read_frontmatter_disable_list,
)
from _doctor_shared import Finding  # type: ignore[import-not-found]

RULE_ID = 'no-lesson-id-in-skill-prose'
RULE_NAME = 'analyze_lesson_id_in_skill_prose'
FINDING_TYPE = 'lesson_id_in_skill_prose'

# ---------------------------------------------------------------------------
# Detection patterns
# ---------------------------------------------------------------------------

# Lesson-ID token: optional `lesson ` or `lesson-` prefix + date-based id.
# Two format families: YYYY-MM-DD-NNN and YYYY-MM-DD-HH-NNN.
# This regex matches the non-backtick prose form.
_LESSON_ID_RE = re.compile(
    r'\b(?:lesson[- ])?(\d{4}-\d{2}-\d{2}(?:-\d{2})?-\d{3})\b',
    re.IGNORECASE,
)

# Backtick-prefixed form: ``lesson `YYYY-MM-DD-HH-NNN` `` where "lesson"
# is outside the backtick and the ID is inside. Two format families.
# This is a narrative citation regardless of the backtick — the prose word
# "lesson" establishes the context.
_LESSON_BACKTICK_ID_RE = re.compile(
    r'\blesson[- ]`(\d{4}-\d{2}-\d{2}(?:-\d{2})?-\d{3})`',
    re.IGNORECASE,
)

# Inline-code span detection (matches `...`).
_INLINE_CODE_RE = re.compile(r'`([^`]+)`')

# Fenced-block boundaries.
_FENCE_OPEN_RE = re.compile(r'^\s*```\s*([A-Za-z0-9_+-]*)\s*$')
_FENCE_CLOSE_RE = re.compile(r'^\s*```\s*$')

# Source: line — structured provenance citation marker.
_SOURCE_LINE_RE = re.compile(r'^\s*(?:[-*]\s*)?\*{0,2}Source:\*{0,2}', re.IGNORECASE)


# ---------------------------------------------------------------------------
# Allowlist
# ---------------------------------------------------------------------------


def _is_allowlisted(rel_to_bundles: str, default_cfg: dict[str, list[str]]) -> bool:
    """Return True if the file path is exempt from this rule (Granularity-1).

    The lesson-domain exemption table is no longer hardcoded here: it is
    carried by the shipped default suppression config under the ``RULE_ID``
    key (see ``config/default-suppression.yml``). The check delegates to the
    shared layer-1 predicate, which applies the same path-prefix semantics the
    former hardcoded table used (``rel_to_bundles.startswith(prefix)``;
    exact-file entries match because a path is a prefix of itself).
    """
    return _config_layer_suppresses(RULE_ID, rel_to_bundles, default_cfg)


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


# ---------------------------------------------------------------------------
# File-level scanner
# ---------------------------------------------------------------------------


def _scan_file(
    path: Path,
    rel_to_bundles: str | None,
    default_cfg: dict[str, list[str]],
    kind: str = 'markdown',
) -> list[dict]:
    """Scan a single source file and return all findings.

    ``rel_to_bundles`` is the file path relative to ``marketplace/bundles/``
    (e.g., ``plan-marshall/skills/phase-4-plan/SKILL.md``) — used for
    allowlist matching. For files OUTSIDE the bundles tree (the project-local
    ``.claude/skills/**`` tree) this is ``None`` and no allowlist applies.

    ``kind`` is ``'markdown'`` or ``'python'`` and selects which structural
    exemptions apply. For ``'python'`` the markdown-only exemptions
    (frontmatter, fenced code block, Source: line, inline-code span) are
    deliberately disabled so that citations in comments, docstrings, and
    string literals are caught.
    """
    if rel_to_bundles is not None and _is_allowlisted(rel_to_bundles, default_cfg):
        return []

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

    # Granularity-3 (per-file frontmatter): skip the whole file when its
    # ``plugin-doctor-disable`` list names this rule. Applies to both file
    # classes — a Python source may carry the key in a leading docstring/comment
    # block parsed as frontmatter when present.
    if RULE_ID in read_frontmatter_disable_list(text):
        return []

    is_markdown = kind == 'markdown'
    lines = text.splitlines()
    # Markdown-only structural maps. For Python sources these stay empty so
    # comments / docstrings / string literals remain fully in scope.
    fence_map = _build_fence_map(lines) if is_markdown else {}
    frontmatter = _build_frontmatter_set(lines) if is_markdown else set()

    findings: list[Finding] = []

    for idx, line in enumerate(lines):
        if is_markdown:
            # Skip lines inside YAML frontmatter or fenced code blocks (any
            # info-string) outright.
            if idx in frontmatter:
                continue
            if idx in fence_map:
                continue
            # Skip Source: provenance lines.
            if _SOURCE_LINE_RE.match(line):
                continue
        # Quick pre-check: does this line contain any candidate?
        has_bare = bool(_LESSON_ID_RE.search(line))
        has_backtick_prefix = bool(_LESSON_BACKTICK_ID_RE.search(line))
        if not has_bare and not has_backtick_prefix:
            continue

        # Inline-code spans are a markdown construct only. In Python a
        # backtick has no special meaning, so do not treat backtick-wrapped
        # IDs as exempt code-token references.
        spans = _inline_code_spans(line) if is_markdown else []

        # Pass 1: bare prose form (non-backtick IDs, or bare IDs not inside
        # inline-code spans).
        for m in _LESSON_ID_RE.finditer(line):
            offset = m.start()
            # Skip matches inside inline-code spans ONLY when there is no
            # "lesson" prose prefix on the match (bare code-token reference).
            # For Python sources ``spans`` is empty so this never skips.
            if _offset_in_inline_code(offset, spans):
                # The lesson prefix (if any) starts the match; if the prefix
                # is absent the entire match is a bare date token inside
                # backticks — legitimately exempt.
                # If "lesson" appears immediately before the backtick, the
                # backtick-prefixed branch below will catch it.
                continue

            findings.append(
                Finding(
                    type=FINDING_TYPE,
                    file=str(path),
                    line=idx + 1,
                    severity='warning',
                    fixable=False,
                    rule_id=RULE_ID,
                    description=(
                        'Narrative lesson-ID citation — strip the ID and trivia, '
                        'keep the rule content. See rule-catalog.md.'
                    ),
                    extra={'rule': RULE_NAME, 'snippet': m.group(0)},
                )
            )

        # Pass 2: backtick-prefixed form — ``lesson `YYYY-...` ``.
        # "lesson" is outside the backtick; the ID is inside.
        # This is a narrative citation regardless of the backtick. Markdown
        # only — in Python the bare ID inside the backticks was already
        # flagged by Pass 1 (``spans`` is empty there), so running Pass 2 on
        # Python sources would double-count.
        if not is_markdown:
            continue
        for m in _LESSON_BACKTICK_ID_RE.finditer(line):
            findings.append(
                Finding(
                    type=FINDING_TYPE,
                    file=str(path),
                    line=idx + 1,
                    severity='warning',
                    fixable=False,
                    rule_id=RULE_ID,
                    description=(
                        'Narrative lesson-ID citation (backtick form) — '
                        'strip the ID and "lesson" prefix, keep the rule content. '
                        'See rule-catalog.md.'
                    ),
                    extra={'rule': RULE_NAME, 'snippet': m.group(0)},
                )
            )

    return [f.to_dict() for f in findings]


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


# File-class glob → scan-kind mapping. Both classes are scanned under every
# in-scope tree.
_KIND_BY_GLOB = (('*.md', 'markdown'), ('*.py', 'python'))


def _skill_source_targets(marketplace_root: Path) -> list[tuple[Path, str | None, str]]:
    """Return ``(absolute_path, rel_to_bundles, kind)`` for every in-scope file.

    Scope: ``marketplace_root/*/{skills,agents,commands}/**`` — both ``*.md``
    (kind ``'markdown'``) and ``*.py`` (kind ``'python'``). The
    ``rel_to_bundles`` slot is always a string here (these files live inside
    the bundles tree); the type is widened to ``str | None`` only to unify
    with the project-local enumerator at the shared call site.
    """
    if not marketplace_root.is_dir():
        return []
    results: list[tuple[Path, str | None, str]] = []
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
            for glob, kind in _KIND_BY_GLOB:
                for src in sorted(sub_dir.rglob(glob)):
                    if src.is_file():
                        rel = str(src.relative_to(marketplace_root))
                        results.append((src, rel, kind))
    return results


def _claude_skills_root(marketplace_root: Path) -> Path:
    """Resolve the project-local ``.claude/skills`` tree from ``marketplace_root``.

    ``marketplace_root`` is ``<repo>/marketplace/bundles``; the project-local
    skills tree is ``<repo>/.claude/skills`` — two levels up, then
    ``.claude/skills``.
    """
    return marketplace_root.parent.parent / '.claude' / 'skills'


def _claude_skill_source_targets(marketplace_root: Path) -> list[tuple[Path, str | None, str]]:
    """Return ``(absolute_path, None, kind)`` for every ``.claude/skills/**`` file.

    Scope: ``<repo>/.claude/skills/**`` — both ``*.md`` (kind ``'markdown'``)
    and ``*.py`` (kind ``'python'``). The ``rel_to_bundles`` slot is ``None``
    because these files live outside ``marketplace/bundles/`` and have no
    allowlisted members — the project-local tree is scanned in full.
    """
    skills_root = _claude_skills_root(marketplace_root)
    if not skills_root.is_dir():
        return []
    results: list[tuple[Path, str | None, str]] = []
    for glob, kind in _KIND_BY_GLOB:
        try:
            sources = sorted(skills_root.rglob(glob))
        except OSError:
            continue
        for src in sources:
            if src.is_file():
                results.append((src, None, kind))
    return results


def analyze_lesson_id_in_skill_prose(marketplace_root: Path) -> list[dict]:
    """Scan skill sources for narrative lesson-ID citations.

    Walks three trees and reports every lesson-ID occurrence outside the
    documented exempt contexts:

    - ``marketplace_root/*/{skills,agents,commands}/**/*.md`` (markdown
      exemptions: allowlisted skill path, YAML frontmatter, fenced code block,
      ``Source:`` provenance line, inline-code span, per-file
      ``plugin-doctor-disable`` frontmatter key).
    - ``marketplace_root/*/{skills,agents,commands}/**/*.py`` (Python
      exemptions: allowlisted skill path, per-file ``plugin-doctor-disable``
      frontmatter key — markdown-only structural exemptions do not apply).
    - ``<repo>/.claude/skills/**`` for both ``*.md`` and ``*.py`` (no
      allowlisted members; the project-local tree is scanned in full).

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
    default_cfg = load_default_suppression_config()
    findings: list[dict] = []
    for path, rel, kind in _skill_source_targets(marketplace_root):
        findings.extend(_scan_file(path, rel, default_cfg, kind))
    for path, rel, kind in _claude_skill_source_targets(marketplace_root):
        findings.extend(_scan_file(path, rel, default_cfg, kind))
    return findings

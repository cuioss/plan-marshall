#!/usr/bin/env python3
"""Allowed-tools-vs-body-usage drift scanner for the ``allowed-tools-body-drift`` rule.

This module implements a deterministic regex-based static analyzer that
detects a *drift* between a component's declared ``allowed-tools`` (or
``tools``) frontmatter list and the tools its workflow body actually
invokes. The drift it flags is one-directional: a tool the body invokes
that is absent from a declared, non-empty tool list.

Scope
-----
``*.md`` under:

1. ``marketplace/bundles/*/{skills,agents,commands}/**``.
2. the project-local ``.claude/skills/**`` tree (resolved relative to the
   marketplace bundles root).

What is NOT flagged
-------------------
This rule is a consistency check, not a schema prohibition:

- A component that omits ``allowed-tools`` / ``tools`` entirely is NOT
  flagged. Skills MAY declare ``allowed-tools`` per the Claude Code skills
  schema, but are not required to (the fabricated
  ``unsupported-skill-tools-field`` rule was retired in plan
  ``harden-phase3-outline-plugin-doctor-audit``). A missing declaration is
  the "inherit all tools" default, not a drift.
- A component whose declared list COVERS every body-invoked tool is clean.
- A declared tool that the body never invokes is NOT flagged — unused
  declarations are a separate (risky, handler-only) concern.

The finding fires only where a tool is BOTH invoked in the body AND the
frontmatter declares a non-empty list that omits it.

Pattern alignment
-----------------
The analyzer mirrors ``_analyze_lesson_id_in_skill_prose.py``:

- pure static analysis (no subprocess execution, no imports of target scripts)
- regex-driven extraction from source
- stdlib-only dependencies
- no mutation of any file

It reuses the declared-tool parser proven in ``_analyze_coverage.py``
(``parse_declared_tools``) so the frontmatter extraction stays consistent
across the two analyzers rather than diverging.

Body-invocation detection
--------------------------
A tool is considered "invoked" by the body when a known tool name appears:

- as a tool directive at the start of a line: ``Read:``, ``Write:``,
  ``- Skill:``, ``Tool: Bash`` (the ``{ToolName}:`` directive form used in
  workflow prose and dispatch templates), OR
- as a bare ``{ToolName}`` token at a line start (the bullet/heading form
  ``Use Write to …`` is intentionally NOT matched — only directive-shaped
  invocations count, to keep the false-positive rate low).

The known-tool vocabulary is the Claude Code tool set: ``Read``, ``Write``,
``Edit``, ``Glob``, ``Grep``, ``Bash``, ``AskUserQuestion``, ``Skill``,
``Task``, ``WebFetch``.

Exemptions
----------
- **Fenced code block** — body lines inside ``` ``` ``` fences (any
  info-string) are exempt: a tool name inside an example command block is
  not a live invocation.
- **Per-file frontmatter disable** — a
  ``plugin-doctor-disable: [allowed-tools-body-drift]`` frontmatter key
  suppresses every finding in that file (file-scoped, via the shared substrate).

Findings have the shape::

    {
        'rule_id': 'allowed-tools-body-drift',
        'type': 'allowed_tools_body_drift',
        'rule': 'analyze_allowed_tools_drift',
        'file': '<absolute source path>',
        'line': <int, 1-based>,
        'severity': 'warning',
        'fixable': False,
        'snippet': '<the invoked tool name>',
        'description': '<human-readable drift description>. See rule-catalog.md.',
    }

Public API
----------
- ``analyze_allowed_tools_drift(marketplace_root)``: entry point — scans
  every ``*.md`` under ``marketplace_root/*/{skills,agents,commands}/**``
  PLUS every ``*.md`` under the sibling project-local ``.claude/skills/**``
  tree.
"""

from __future__ import annotations

import re
from pathlib import Path

from _analyze_coverage import parse_declared_tools
from _analyze_shared import extract_frontmatter, read_frontmatter_disable_list

RULE_ID = 'allowed-tools-body-drift'
RULE_NAME = 'analyze_allowed_tools_drift'
FINDING_TYPE = 'allowed_tools_body_drift'

# ---------------------------------------------------------------------------
# Known tool vocabulary
# ---------------------------------------------------------------------------

# The Claude Code tool set. Body-invocation detection only matches these
# names — an arbitrary capitalised word at a line start is not treated as a
# tool invocation.
_KNOWN_TOOLS = (
    'Read',
    'Write',
    'Edit',
    'Glob',
    'Grep',
    'Bash',
    'AskUserQuestion',
    'Skill',
    'Task',
    'WebFetch',
)

# ---------------------------------------------------------------------------
# Detection patterns
# ---------------------------------------------------------------------------

# Tool-directive at a line start: optional list-bullet, then a known tool
# name, then a colon (``Read:``, ``- Skill:``) OR a ``Tool: {ToolName}``
# directive. The alternation captures the tool name in group 'tool'.
_TOOL_NAMES_ALT = '|'.join(_KNOWN_TOOLS)
_TOOL_DIRECTIVE_RE = re.compile(
    r'^\s*(?:[-*]\s*)?(?:Tool:\s*)?(?P<tool>' + _TOOL_NAMES_ALT + r')\b\s*:',
)
# ``Tool: {ToolName}`` form where the colon follows ``Tool`` and the tool
# name is the payload (e.g. ``Tool: Bash``). Captured separately because the
# directive regex above requires a trailing colon after the tool name.
_TOOL_PREFIXED_RE = re.compile(
    r'^\s*(?:[-*]\s*)?Tool:\s*(?P<tool>' + _TOOL_NAMES_ALT + r')\b',
)

# Fenced-block boundaries.
_FENCE_OPEN_RE = re.compile(r'^\s*```\s*([A-Za-z0-9_+-]*)\s*$')
_FENCE_CLOSE_RE = re.compile(r'^\s*```\s*$')


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_body(text: str) -> tuple[int, str]:
    """Return ``(body_start_line, body_text)`` for the markdown content.

    ``body_start_line`` is the 0-based index of the first body line (the line
    immediately after the closing frontmatter fence), so finding line numbers
    can be mapped back to absolute file positions. When no frontmatter is
    present the body is the whole file starting at line 0.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != '---':
        return 0, text
    for idx in range(1, len(lines)):
        if lines[idx].strip() == '---':
            return idx + 1, '\n'.join(lines[idx + 1 :])
    # Unterminated frontmatter — treat the whole file as body.
    return 0, text


def _build_fence_set(lines: list[str]) -> set[int]:
    """Return the 0-based indices of body lines inside any fenced block.

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


def _invoked_tool(line: str) -> str | None:
    """Return the tool name invoked on ``line``, or ``None``.

    Matches the ``Tool: {ToolName}`` prefixed form first (so ``Tool: Bash``
    yields ``Bash`` rather than ``Tool``), then the ``{ToolName}:`` directive
    form.
    """
    m = _TOOL_PREFIXED_RE.match(line)
    if m:
        return m.group('tool')
    m = _TOOL_DIRECTIVE_RE.match(line)
    if m:
        return m.group('tool')
    return None


# ---------------------------------------------------------------------------
# File-level scanner
# ---------------------------------------------------------------------------


def _scan_file(path: Path) -> list[dict]:
    """Scan a single markdown file for allowed-tools drift findings."""
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

    # Granularity-3 (per-file frontmatter): skip the whole file when its
    # ``plugin-doctor-disable`` list names this rule.
    if RULE_ID in read_frontmatter_disable_list(text):
        return []

    frontmatter_present, frontmatter = extract_frontmatter(text)
    if not frontmatter_present:
        # No frontmatter → no declared tool list → nothing to drift against.
        return []

    declared_tools = parse_declared_tools(frontmatter)
    if not declared_tools:
        # Empty / absent declaration is the "inherit all tools" default, not a
        # drift. Do NOT flag — this is the retired unsupported-skill-tools-field
        # behaviour we must not reintroduce.
        return []

    declared_set = set(declared_tools)

    body_start, body_text = _extract_body(text)
    body_lines = body_text.splitlines()
    fence_set = _build_fence_set(body_lines)

    findings: list[dict] = []
    for body_idx, line in enumerate(body_lines):
        if body_idx in fence_set:
            continue
        tool = _invoked_tool(line)
        if tool is None:
            continue
        if tool in declared_set:
            continue

        abs_line = body_start + body_idx  # 0-based absolute index

        findings.append(
            {
                'rule_id': RULE_ID,
                'type': FINDING_TYPE,
                'rule': RULE_NAME,
                'file': str(path),
                'line': abs_line + 1,  # 1-based
                'severity': 'warning',
                'fixable': False,
                'snippet': tool,
                'description': (
                    f'Tool `{tool}` is invoked in the body but absent from the '
                    f'declared `allowed-tools`/`tools` frontmatter list '
                    f'({", ".join(sorted(declared_set))}) — add it to the '
                    f'declaration or remove the invocation. See rule-catalog.md.'
                ),
            }
        )

    return findings


# ---------------------------------------------------------------------------
# Target enumeration
# ---------------------------------------------------------------------------


def _skill_source_targets(marketplace_root: Path) -> list[Path]:
    """Return every in-scope ``*.md`` under the bundles tree.

    Scope: ``marketplace_root/*/{skills,agents,commands}/**/*.md``.
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
                for src in sorted(sub_dir.rglob('*.md')):
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
    """Return every ``*.md`` under the project-local ``.claude/skills/**`` tree."""
    skills_root = _claude_skills_root(marketplace_root)
    if not skills_root.is_dir():
        return []
    try:
        sources = sorted(skills_root.rglob('*.md'))
    except OSError:
        return []
    return [src for src in sources if src.is_file()]


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def analyze_allowed_tools_drift(marketplace_root: Path) -> list[dict]:
    """Scan component markdown for allowed-tools-vs-body drift.

    Walks two trees and reports every body-invoked tool that is absent from a
    declared, non-empty ``allowed-tools``/``tools`` frontmatter list:

    - ``marketplace_root/*/{skills,agents,commands}/**/*.md``.
    - ``<repo>/.claude/skills/**/*.md``.

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

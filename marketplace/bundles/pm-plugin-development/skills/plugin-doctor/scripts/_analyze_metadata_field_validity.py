#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Cross-skill metadata field reference validity analyzer.

This module implements the ``metadata-field-undefined`` rule, which detects
skill prose that references metadata field names not established by any
``set-metadata --key {field}`` invocation in the marketplace.

Two-phase static analysis
--------------------------
**Phase 1 — authoritative-set construction**: scan every markdown file under
``marketplace/bundles/*`` for occurrences of ``set-metadata --key {field}``
and collect the set of declared field names.  This set is the ground truth:
a field is "defined" if and only if it has been written by at least one
``set-metadata --key`` invocation somewhere in the marketplace.

**Phase 2 — prose reference detection**: scan each ``*.md`` file in the
target skill directory for backtick-delimited snake_case tokens that appear
within three lines of a ``metadata`` or ``set-metadata`` mention.  When a
detected field name is not in the authoritative set, a finding is emitted.

Pattern alignment
-----------------
The analyzer mirrors ``_analyze_verb_chains.py`` and
``_analyze_shell_active_tokens.py``:

- pure static analysis (no subprocess execution, no imports of target scripts)
- regex-driven extraction from markdown source
- stdlib-only dependencies
- no mutation of any file

Findings have the shape::

    {
        'rule_id': 'metadata-field-undefined',
        'file': '<absolute markdown path>',
        'line': <int, 1-based>,
        'field_name': '<snake_case_field_name>',
        'narrative_context': '<surrounding line excerpt>',
    }

Public API
----------
- ``analyze_metadata_field_validity(marketplace_root)``: entry point — scans
  the entire marketplace and returns findings for field references that do not
  appear in the authoritative set.
- ``build_authoritative_field_set(marketplace_root)``: Phase 1 helper —
  returns the set of known ``set-metadata --key`` field names.
- ``scan_skill_for_undefined_fields(skill_dir, authoritative_set)``: Phase 2
  helper — scans one skill directory and returns per-file findings.
"""

from __future__ import annotations

import re
from pathlib import Path

RULE_ID = 'metadata-field-undefined'

# ---------------------------------------------------------------------------
# Phase 1: authoritative-set construction
# ---------------------------------------------------------------------------

# Matches: set-metadata --key some_field_name
# Captures the field name (snake_case or kebab-case converted to snake_case).
_SET_METADATA_KEY_RE = re.compile(r'set-metadata\s+--key\s+([A-Za-z_][A-Za-z0-9_]*)')

# Common well-known fields from the marketplace that may not always appear
# in explicit set-metadata calls but are part of the core contract.
_BUILTIN_FIELDS: frozenset[str] = frozenset(
    {
        'change_type',
        'plan_source',
        'worktree_path',
        'use_worktree',
        'confidence',
        'scope_estimate',
        'domain',
        'plan_id',
        'task_number',
        'branch',
        'base_branch',
        'phase',
        'status',
        'title',
        'description',
    }
)


def build_authoritative_field_set(marketplace_root: Path) -> frozenset[str]:
    """Scan all markdown under ``marketplace_root`` for ``set-metadata --key`` writes.

    Returns the union of all declared field names plus the built-in field set.
    The result is deterministic: same marketplace state → same set.
    """
    found: set[str] = set()
    if not marketplace_root.is_dir():
        return frozenset(_BUILTIN_FIELDS)

    for md_file in marketplace_root.rglob('*.md'):
        try:
            text = md_file.read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError):
            continue
        for m in _SET_METADATA_KEY_RE.finditer(text):
            found.add(m.group(1))

    return frozenset(found | _BUILTIN_FIELDS)


# ---------------------------------------------------------------------------
# Phase 2: prose reference detection
# ---------------------------------------------------------------------------

# Detect a "metadata context": a line mentioning metadata or set-metadata.
_METADATA_CONTEXT_RE = re.compile(r'\b(?:set-metadata|metadata)\b', re.IGNORECASE)

# Snake-case token inside a backtick inline-code span: `some_field_name`
# We accept snake_case (underscores, no hyphens) to focus on field names.
_BACKTICK_SNAKE_CASE_RE = re.compile(r'`([a-z][a-z0-9_]+)`')

# Heuristic: only flag tokens of 3+ characters that look like field names
# (avoid short words like `id`, `to`, `in`).
_MIN_FIELD_LEN = 4

# Number of lines around a metadata-context line to consider as "nearby".
_CONTEXT_WINDOW = 3


def _scan_file_for_undefined_fields(
    md_path: Path,
    authoritative_set: frozenset[str],
) -> list[dict]:
    """Scan one markdown file for undefined field references near metadata prose."""
    try:
        text = md_path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        return []

    lines = text.splitlines()
    findings: list[dict] = []

    # Build a set of line indices that are "metadata context" lines.
    context_lines: set[int] = set()
    for idx, line in enumerate(lines):
        if _METADATA_CONTEXT_RE.search(line):
            # Expand context window: ±_CONTEXT_WINDOW lines
            for offset in range(-_CONTEXT_WINDOW, _CONTEXT_WINDOW + 1):
                target = idx + offset
                if 0 <= target < len(lines):
                    context_lines.add(target)

    # Scan each context line for backtick snake_case tokens.
    for idx in sorted(context_lines):
        line = lines[idx]
        for m in _BACKTICK_SNAKE_CASE_RE.finditer(line):
            field = m.group(1)
            if len(field) < _MIN_FIELD_LEN:
                continue
            if field in authoritative_set:
                continue
            findings.append(
                {
                    'rule_id': RULE_ID,
                    'file': str(md_path),
                    'line': idx + 1,
                    'field_name': field,
                    'narrative_context': line.strip()[:120],
                }
            )

    return findings


def scan_skill_for_undefined_fields(
    skill_dir: Path,
    authoritative_set: frozenset[str],
) -> list[dict]:
    """Scan all markdown in ``skill_dir`` for undefined metadata field references.

    Covers ``SKILL.md`` and all markdown in ``standards/``, ``references/``,
    ``workflow/``, and ``templates/`` sub-directories.
    """
    findings: list[dict] = []
    targets: list[Path] = []

    skill_md = skill_dir / 'SKILL.md'
    if skill_md.is_file():
        targets.append(skill_md)

    for subdir_name in ('standards', 'references', 'workflows', 'templates'):
        subdir = skill_dir / subdir_name
        if subdir.is_dir():
            for md in sorted(subdir.glob('*.md')):
                if md.is_file():
                    targets.append(md)

    for md_path in targets:
        findings.extend(_scan_file_for_undefined_fields(md_path, authoritative_set))

    return findings


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def analyze_metadata_field_validity(marketplace_root: Path) -> list[dict]:
    """Scan the marketplace for undefined metadata field references in skill prose.

    Phase 1: build the authoritative set of ``set-metadata --key`` field names.
    Phase 2: for every skill directory in the marketplace, scan markdown prose
    for backtick snake_case tokens within three lines of a ``metadata`` or
    ``set-metadata`` mention and emit a finding when the token is not in the
    authoritative set.

    Parameters
    ----------
    marketplace_root:
        Path to the ``marketplace/`` directory (the parent of ``bundles/``).

    Returns
    -------
    list[dict]
        List of finding dicts (empty when no violations detected).
    """
    authoritative_set = build_authoritative_field_set(marketplace_root)

    findings: list[dict] = []
    bundles_root = marketplace_root / 'bundles'
    if not bundles_root.is_dir():
        return []

    # Enumerate skill directories: marketplace/bundles/*/skills/*/
    for bundle_dir in sorted(bundles_root.iterdir()):
        if not bundle_dir.is_dir():
            continue
        skills_root = bundle_dir / 'skills'
        if not skills_root.is_dir():
            continue
        for skill_dir in sorted(skills_root.iterdir()):
            if not skill_dir.is_dir():
                continue
            findings.extend(scan_skill_for_undefined_fields(skill_dir, authoritative_set))

    return findings

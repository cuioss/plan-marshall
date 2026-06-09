#!/usr/bin/env python3
"""Skill-notation analyzer for the ``skill-notation-unresolved`` rule.

This module scans marketplace markdown for ``Skill: {bundle}:{skill}``
directive tokens and asserts that the referenced skill directory
``marketplace/bundles/{bundle}/skills/{skill}/`` exists on disk. A directive
whose target skill directory is missing produces a finding — a ``Skill:``
directive that does not resolve is a dead reference: the dispatcher cannot
load it, and the workflow that depends on it silently misfires.

Scope
-----
Every ``*.md`` file under ``marketplace/bundles/*/{skills,agents,commands}/``.
The directive shape recognised is the two-segment bundle-prefixed form
``Skill: {bundle}:{skill}`` (optionally fenced, optionally indented). The
bare single-segment form (``Skill: dev-agent-behavior-rules`` with no bundle
prefix) and project-local ``.claude/skills`` references are NOT validated here
— this rule targets the bundle-prefixed notation whose on-disk anchor is
deterministic.

Pattern alignment
-----------------
The analyzer mirrors ``_analyze_notation_staleness.py``:

- pure static analysis (no subprocess execution, no imports of target scripts);
- regex-driven extraction from markdown;
- stdlib-only dependencies;
- no mutation of any file;
- findings carry ``rule_id``/``type``/``rule``/``file``/``line``/``severity``/
  ``fixable``/``description`` with rule-specific fields under ``details``.

Public API
----------
- ``analyze_skill_notation(marketplace_root)``: entry point — scans markdown
  under every bundle and returns findings.
- ``RULE_ID``: the canonical rule key.
"""

from __future__ import annotations

import functools
import re
from pathlib import Path

RULE_ID = 'skill-notation-unresolved'
RULE_NAME = 'analyze_skill_notation'

_SEGMENT = r'[A-Za-z0-9][A-Za-z0-9_-]*'
# Match a `Skill: {bundle}:{skill}` directive. The directive may be indented
# and may be preceded by a code-fence marker; the regex anchors on the literal
# `Skill:` keyword followed by the two-segment notation. A trailing third
# segment (script notation) would make this an executor notation, not a skill
# directive, so the skill segment is bounded by a non-`:` lookahead.
_DIRECTIVE_RE = re.compile(
    rf'\bSkill:\s+(?P<bundle>{_SEGMENT}):(?P<skill>{_SEGMENT})(?![:\w-])'
)

# The bundle subtrees whose markdown is scanned.
_COMPONENT_DIRS = ('skills', 'agents', 'commands')


@functools.cache
def _skill_dir_exists(marketplace_root: Path, bundle: str, skill: str) -> bool:
    """Return True when ``bundles/{bundle}/skills/{skill}/`` exists.

    Cached: the marketplace tree is static for the duration of an analysis
    run, so repeated lookups for the same notation avoid redundant filesystem
    ``is_dir()`` calls across every scanned file.
    """
    return (marketplace_root / bundle / 'skills' / skill).is_dir()


@functools.cache
def _bundle_exists(marketplace_root: Path, bundle: str) -> bool:
    """Return True when ``bundles/{bundle}/`` is a real bundle directory."""
    return (marketplace_root / bundle / '.claude-plugin' / 'plugin.json').is_file()


def _scan_file(path: Path, marketplace_root: Path) -> list[dict]:
    """Scan a single markdown file and return skill-notation findings."""
    try:
        text = path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        return []

    findings: list[dict] = []
    seen: set[tuple[int, str]] = set()
    for idx, line in enumerate(text.splitlines(), start=1):
        for match in _DIRECTIVE_RE.finditer(line):
            bundle = match.group('bundle')
            skill = match.group('skill')

            # Only evaluate directives whose bundle is a real bundle on disk.
            # This filters out incidental two-segment tokens whose first
            # segment is not a marketplace bundle (e.g. illustrative examples
            # or single-segment skill names that happened to be colon-joined).
            if not _bundle_exists(marketplace_root, bundle):
                continue
            if _skill_dir_exists(marketplace_root, bundle, skill):
                continue

            notation = f'{bundle}:{skill}'
            key = (idx, notation)
            if key in seen:
                continue
            seen.add(key)

            findings.append(
                {
                    'rule_id': RULE_ID,
                    'type': RULE_ID,
                    'rule': RULE_NAME,
                    'file': str(path),
                    'line': idx,
                    'severity': 'error',
                    'fixable': False,
                    'description': (
                        f'`Skill: {notation}` directive references a skill '
                        f'directory `bundles/{bundle}/skills/{skill}/` that does '
                        f'not exist — the Skill directive does not resolve '
                        f'(skill-notation-unresolved)'
                    ),
                    'details': {
                        'notation': notation,
                        'bundle': bundle,
                        'skill': skill,
                        'reason': 'skill_dir_missing',
                    },
                }
            )
    return findings


def _scoped_markdown(marketplace_root: Path) -> list[Path]:
    """Enumerate every ``*.md`` under each bundle's component subtrees."""
    targets: list[Path] = []
    for bundle_dir in sorted(marketplace_root.iterdir()):
        if not bundle_dir.is_dir():
            continue
        if not (bundle_dir / '.claude-plugin' / 'plugin.json').is_file():
            continue
        for sub in _COMPONENT_DIRS:
            sub_dir = bundle_dir / sub
            if sub_dir.is_dir():
                targets.extend(sorted(sub_dir.rglob('*.md')))
    return targets


def analyze_skill_notation(marketplace_root: Path) -> list[dict]:
    """Scan marketplace markdown for unresolved ``Skill:`` directives.

    Parameters
    ----------
    marketplace_root:
        The bundles root (the directory that contains ``plan-marshall``,
        ``pm-plugin-development``, etc.).

    Returns
    -------
    list[dict]
        A list of finding dicts (see module docstring for the shape).
    """
    findings: list[dict] = []
    for target in _scoped_markdown(marketplace_root):
        findings.extend(_scan_file(target, marketplace_root))
    return findings

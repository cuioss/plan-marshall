#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Persona-profile-uniqueness analyzer for the ``persona-profile-uniqueness`` rule.

In the persona / ref / profile identity model, every persona skill
(``implements: persona``) that owns a work-activity identity declares a
``profiles:`` frontmatter list whose **first** entry is the persona's *primary
identity profile*. Phase-4-plan reverse-looks-up a task's persona by matching
that primary profile, so the binding must be unambiguous: no two persona skills
may declare the same first ``profiles:`` entry. This analyzer flags any
collision.

Scope
-----
``marketplace/bundles/*/skills/*/SKILL.md`` whose frontmatter declares
``implements: persona``. Meta/evaluator personas that own no work-activity
profile omit the ``profiles:`` field entirely (e.g. ``persona-auditor``); those
carry no primary profile and are not subject to the uniqueness check.

Pattern alignment
-----------------
Mirrors ``_analyze_skill_mode.py`` (the ``skill-missing-mode`` analyzer):

- pure static analysis (no subprocess execution, no imports of target scripts);
- regex / line-based frontmatter parsing supporting both inline-flow
  (``profiles: [a, b]``) and block (``profiles:`` + ``  - a`` lines) forms;
- stdlib-only dependencies;
- no mutation of any file;
- findings carry ``rule_id``/``type``/``rule``/``file``/``line``/``severity``/
  ``fixable``/``description`` with rule-specific fields under ``details``.

Public API
----------
- ``analyze_persona_profile_uniqueness(marketplace_root)``: entry point.
- ``RULE_ID``: the canonical rule key.
"""

from __future__ import annotations

import re
from pathlib import Path

from _doctor_shared import Finding  # type: ignore[import-not-found]

RULE_ID = 'persona-profile-uniqueness'
RULE_NAME = 'analyze_persona_profile_uniqueness'


def _leading_frontmatter(text: str) -> str:
    """Return the leading ``---``...``---`` YAML frontmatter block, or ''.

    Recognised only when the first line is ``---`` and a closing ``---`` follows.
    """
    lines = text.split('\n')
    if not lines or lines[0].strip() != '---':
        return ''
    for i in range(1, len(lines)):
        if lines[i].strip() == '---':
            return '\n'.join(lines[1:i])
    return ''


def _parse_yaml_list(frontmatter: str, field: str) -> list[str]:
    """Parse a frontmatter list field, supporting inline-flow and block forms.

    Mirrors ``manage_personas._parse_yaml_list`` so the analyzer reads
    ``profiles:`` exactly as the resolver does. Returns an empty list when the
    field is absent or empty.
    """
    inline = re.search(rf'^{re.escape(field)}:\s*\[(.*?)\]\s*$', frontmatter, re.MULTILINE)
    if inline is not None:
        body = inline.group(1).strip()
        if not body:
            return []
        return [item.strip().strip('\'"') for item in body.split(',') if item.strip()]

    block = re.search(rf'^{re.escape(field)}:\s*$', frontmatter, re.MULTILINE)
    if block is None:
        return []
    items: list[str] = []
    after = frontmatter[block.end() :].split('\n')
    for line in after:
        if line.startswith((' ', '\t')) and line.lstrip().startswith('-'):
            value = line.lstrip()[1:].strip().strip('\'"')
            if value:
                items.append(value)
        elif line.strip() == '':
            continue
        else:
            break
    return items


def _is_persona(frontmatter: str) -> bool:
    """Return True when the frontmatter declares ``implements: persona``."""
    match = re.search(r'^implements:\s*(.+)$', frontmatter, re.MULTILINE)
    return match is not None and match.group(1).strip().strip('\'"') == 'persona'


def _skill_md_files(marketplace_root: Path) -> list[Path]:
    """Enumerate every skill ``SKILL.md`` under the marketplace bundle tree."""
    files: list[Path] = []
    try:
        bundle_dirs = sorted(marketplace_root.iterdir())
    except OSError:
        return files
    for bundle_dir in bundle_dirs:
        if not bundle_dir.is_dir():
            continue
        skills_dir = bundle_dir / 'skills'
        if not skills_dir.is_dir():
            continue
        try:
            skill_dirs = sorted(skills_dir.iterdir())
        except OSError:
            continue
        for skill_dir in skill_dirs:
            if not skill_dir.is_dir():
                continue
            skill_md = skill_dir / 'SKILL.md'
            if skill_md.is_file():
                files.append(skill_md)
    return files


def analyze_persona_profile_uniqueness(marketplace_root: Path) -> list[dict]:
    """Flag any two persona skills sharing the same primary ``profiles:`` entry.

    Parameters
    ----------
    marketplace_root:
        The bundles root (the directory that contains ``plan-marshall``,
        ``pm-plugin-development``, etc.).

    Returns
    -------
    list[dict]
        One finding per persona skill that collides with a prior persona on its
        primary (first) ``profiles:`` entry. The finding is attached to the
        later-sorted file so the first-declared owner is treated as canonical.
    """
    # Map primary profile -> first persona file that claimed it.
    primary_owner: dict[str, Path] = {}
    findings: list[Finding] = []

    for skill_md in _skill_md_files(marketplace_root):
        try:
            text = skill_md.read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError):
            continue
        frontmatter = _leading_frontmatter(text)
        if not _is_persona(frontmatter):
            continue
        profiles = _parse_yaml_list(frontmatter, 'profiles')
        if not profiles:
            # Meta/evaluator persona — owns no primary work-activity profile.
            continue
        primary = profiles[0]
        owner = primary_owner.get(primary)
        if owner is None:
            primary_owner[primary] = skill_md
            continue
        findings.append(
            Finding(
                type=RULE_ID,
                file=str(skill_md),
                line=1,
                severity='error',
                fixable=False,
                rule_id=RULE_ID,
                description=(
                    f'persona skill declares primary profile `{primary}` already '
                    f'owned by `{owner.parent.name}` — the persona<->primary-profile '
                    'binding must be unique so phase-4-plan can reverse-look-up a '
                    "task's persona unambiguously. Give this persona a distinct "
                    'primary (first) `profiles:` entry, or remove the duplicate '
                    'binding.'
                ),
                details={
                    'skill': skill_md.parent.name,
                    'primary_profile': primary,
                    'conflicting_skill': owner.parent.name,
                },
                extra={'rule': RULE_NAME},
            )
        )
    return [f.to_dict() for f in findings]

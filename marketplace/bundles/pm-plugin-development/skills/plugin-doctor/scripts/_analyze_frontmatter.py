#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Frontmatter analyzer for the ``recipe-missing-implements`` rule.

Recipe skills are extension-point implementors: every ``recipe-*`` skill must
declare the ``implements:`` frontmatter field naming the recipe extension
point, so the ``extension-api`` discovery layer can resolve it as a recipe
provider. A ``recipe-*`` skill whose ``SKILL.md`` omits ``implements:`` (or
declares a divergent value) is invisible to recipe discovery — this analyzer
flags that gap.

Required value
--------------
``implements: plan-marshall:extension-api/standards/ext-point-recipe`` — the
canonical extension-point notation documented in
``plan-marshall/skills/extension-api/standards/ext-point-recipe.md``
§ "Implementor Frontmatter".

Scope
-----
Two tree families, both scanned:

- ``marketplace/bundles/*/skills/recipe-*/SKILL.md``
- ``recipe-*/SKILL.md`` under every project-local-skill root for the active
  target (the Claude ``.claude/skills`` tree, or the OpenCode layout),
  resolved through the platform-runtime layout op.

A skill is in scope when its directory name matches ``recipe-*``. The
project-local-skill trees carry no allowlist — they are scanned in full.

Pattern alignment
-----------------
The analyzer mirrors ``_analyze_role_field.py``:

- pure static analysis (no subprocess execution, no imports of target scripts);
- regex / line-based frontmatter parsing;
- stdlib-only dependencies;
- no mutation of any file;
- findings carry ``rule_id``/``type``/``rule``/``file``/``line``/``severity``/
  ``fixable``/``description`` with rule-specific fields under ``details``.

Public API
----------
- ``analyze_frontmatter(marketplace_root)``: entry point — scans both recipe
  trees and returns findings.
- ``RULE_ID``: the canonical rule key.
"""

from __future__ import annotations

from pathlib import Path

from _doctor_shared import Finding, resolve_project_skill_trees

RULE_ID = 'recipe-missing-implements'
RULE_NAME = 'analyze_frontmatter'

_REQUIRED_IMPLEMENTS = 'plan-marshall:extension-api/standards/ext-point-recipe'

_DESCRIPTION_MISSING = (
    'recipe-* skill SKILL.md missing `implements:` frontmatter field — recipe '
    'extension discovery cannot resolve this skill as a recipe provider. '
    f'Declare `implements: {_REQUIRED_IMPLEMENTS}`. See '
    'plan-marshall:extension-api/standards/ext-point-recipe.md '
    '§ Implementor Frontmatter.'
)

_DESCRIPTION_DIVERGENT = (
    'recipe-* skill SKILL.md declares a divergent `implements:` value — recipe '
    f'extension discovery expects `{_REQUIRED_IMPLEMENTS}`. See '
    'plan-marshall:extension-api/standards/ext-point-recipe.md '
    '§ Implementor Frontmatter.'
)


def _parse_frontmatter_keys(text: str) -> dict[str, str] | None:
    """Parse the leading ``---``-fenced YAML frontmatter into a flat string map.

    Returns ``None`` when the file does not open with a ``---`` fence. Returns
    an empty dict when the block is empty. Only top-level scalar ``key: value``
    pairs are recognised; comments, nested mappings, and list-valued entries
    are skipped. Quoted scalars have their wrapping quotes stripped.
    """
    if not text.startswith('---'):
        return None
    lines = text.splitlines()
    out: dict[str, str] = {}
    in_block = False
    for index, line in enumerate(lines):
        stripped = line.strip()
        if index == 0:
            if stripped != '---':
                return None
            in_block = True
            continue
        if not in_block:
            break
        if stripped == '---':
            return out
        if not stripped or stripped.startswith('#'):
            continue
        if ':' not in stripped:
            continue
        key, _, value = stripped.partition(':')
        out[key.strip()] = value.strip().strip('"').strip("'")
    # End of file reached before the closing ``---``: treat as not-frontmatter.
    return None


def _recipe_skill_dirs(marketplace_root: Path) -> list[Path]:
    """Enumerate every ``recipe-*`` skill directory across both tree families.

    The marketplace tree is ``marketplace_root/{bundle}/skills/recipe-*``; the
    project-local trees are ``recipe-*`` directories under every project-local-
    skill root the active target's layout op reports (the Claude
    ``.claude/skills`` tree or the OpenCode layout), resolved via
    ``resolve_project_skill_trees``.
    """
    dirs: list[Path] = []
    try:
        bundle_dirs = sorted(marketplace_root.iterdir())
    except OSError:
        bundle_dirs = []
    for bundle_dir in bundle_dirs:
        if not bundle_dir.is_dir():
            continue
        skills_dir = bundle_dir / 'skills'
        if not skills_dir.is_dir():
            continue
        try:
            recipe_dirs = sorted(skills_dir.glob('recipe-*'))
        except OSError:
            continue
        for skill_dir in recipe_dirs:
            if skill_dir.is_dir():
                dirs.append(skill_dir)

    # Project-local-skill trees are resolved through the platform-runtime layout
    # op so both the Claude ``.claude/skills`` tree and the OpenCode layout are
    # covered. The literal ``.claude/skills`` anchor is no longer hardcoded here.
    for skill_root in resolve_project_skill_trees(marketplace_root):
        try:
            project_recipe_dirs = sorted(skill_root.glob('recipe-*'))
        except OSError:
            continue
        for skill_dir in project_recipe_dirs:
            if skill_dir.is_dir():
                dirs.append(skill_dir)
    return dirs


def _scan_recipe_skill(skill_dir: Path) -> list[dict]:
    """Return a finding when the recipe skill's SKILL.md lacks/diverges implements:."""
    skill_md = skill_dir / 'SKILL.md'
    if not skill_md.is_file():
        # A recipe-* directory without a SKILL.md is not this rule's concern;
        # the declared-component-vs-disk / structural rules cover that.
        return []
    try:
        text = skill_md.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        return []

    frontmatter = _parse_frontmatter_keys(text)
    declared = (frontmatter or {}).get('implements', '').strip()

    if declared == _REQUIRED_IMPLEMENTS:
        return []

    reason = 'implements_missing' if not declared else 'implements_divergent'
    description = _DESCRIPTION_MISSING if not declared else _DESCRIPTION_DIVERGENT
    details: dict = {
        'skill': skill_dir.name,
        'required_implements': _REQUIRED_IMPLEMENTS,
        'reason': reason,
    }
    if declared:
        details['declared_implements'] = declared

    return [
        Finding(
            type=RULE_ID,
            file=str(skill_md),
            line=1,
            severity='error',
            fixable=False,
            rule_id=RULE_ID,
            description=description,
            details=details,
            extra={'rule': RULE_NAME},
        ).to_dict()
    ]


def analyze_frontmatter(marketplace_root: Path) -> list[dict]:
    """Scan recipe-* skills for a missing / divergent ``implements:`` field.

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
    for skill_dir in _recipe_skill_dirs(marketplace_root):
        findings.extend(_scan_recipe_skill(skill_dir))
    return findings

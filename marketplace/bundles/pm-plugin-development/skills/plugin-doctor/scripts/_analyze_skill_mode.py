#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Skill-mode analyzer for the ``skill-missing-mode`` rule.

Every skill declares its execution archetype via the ``mode:`` frontmatter
field — the single, authoritative signal for how the skill is consumed,
replacing the prose ``**REFERENCE MODE**`` line and the Enforcement-block
``**Execution mode**:`` line skills previously carried. A skill whose
``SKILL.md`` omits ``mode:`` (or declares a value outside the closed enum) is
not classifiable by the archetype-aware consumers — this analyzer flags that
gap.

Closed enum
-----------
The ``mode:`` value MUST be exactly one of
``{knowledge, workflow, script-executor, manifest}``. The enum and its meaning
are owned authoritatively by
``marketplace/bundles/pm-plugin-development/skills/plugin-architecture/references/frontmatter-standards.md``
§ "mode (required)" — this analyzer does NOT restate the per-value semantics;
it consumes the enum membership only.

Scope
-----
Two trees, both scanned:

- ``marketplace/bundles/*/skills/*/SKILL.md``
- ``.claude/skills/*/SKILL.md`` (the project-local skill tree, resolved
  relative to the marketplace bundles root)

Every skill directory carrying a ``SKILL.md`` is in scope; the ``.claude/skills``
tree carries no allowlist — it is scanned in full.

Pattern alignment
-----------------
The analyzer mirrors ``_analyze_frontmatter.py`` (the ``recipe-missing-implements``
analyzer):

- pure static analysis (no subprocess execution, no imports of target scripts);
- regex / line-based frontmatter parsing;
- stdlib-only dependencies;
- no mutation of any file;
- findings carry ``rule_id``/``type``/``rule``/``file``/``line``/``severity``/
  ``fixable``/``description`` with rule-specific fields under ``details``.

Public API
----------
- ``analyze_skill_mode(marketplace_root)``: entry point — scans both skill
  trees and returns findings.
- ``RULE_ID``: the canonical rule key.
"""

from __future__ import annotations

from pathlib import Path

from _doctor_shared import Finding  # type: ignore[import-not-found]

RULE_ID = 'skill-missing-mode'
RULE_NAME = 'analyze_skill_mode'

# Closed enum of valid ``mode:`` values. Owned authoritatively by
# plugin-architecture/references/frontmatter-standards.md § "mode (required)";
# kept here only as the membership set the presence rule checks against.
_VALID_MODES = frozenset({'knowledge', 'workflow', 'script-executor', 'manifest'})

_VALID_MODES_HINT = '{' + ', '.join(sorted(_VALID_MODES)) + '}'

_DESCRIPTION_MISSING = (
    'skill SKILL.md missing `mode:` frontmatter field — the skill declares no '
    'execution archetype, so archetype-aware consumers cannot classify it. '
    f'Declare `mode:` with one of {_VALID_MODES_HINT}. See '
    'pm-plugin-development:plugin-architecture/references/frontmatter-standards.md '
    '§ mode.'
)

_DESCRIPTION_INVALID = (
    'skill SKILL.md declares a `mode:` value outside the closed enum — valid '
    f'values are {_VALID_MODES_HINT}. See '
    'pm-plugin-development:plugin-architecture/references/frontmatter-standards.md '
    '§ mode.'
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


def _skill_md_files(marketplace_root: Path) -> list[Path]:
    """Enumerate every skill ``SKILL.md`` across both trees.

    The marketplace tree is ``marketplace_root/{bundle}/skills/{skill}/SKILL.md``;
    the project-local tree is ``{repo_root}/.claude/skills/{skill}/SKILL.md`` where
    the repo root is the parent of the ``marketplace`` directory
    (``marketplace_root`` is ``marketplace/bundles``, so two parents up is the
    repo root).
    """
    files: list[Path] = []
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
            skill_dirs = sorted(skills_dir.iterdir())
        except OSError:
            continue
        for skill_dir in skill_dirs:
            if not skill_dir.is_dir():
                continue
            skill_md = skill_dir / 'SKILL.md'
            if skill_md.is_file():
                files.append(skill_md)

    # .claude/skills lives at the repo root: marketplace_root is
    # <repo>/marketplace/bundles, so repo_root = marketplace_root.parent.parent.
    claude_skills = marketplace_root.parent.parent / '.claude' / 'skills'
    if claude_skills.is_dir():
        try:
            claude_skill_dirs = sorted(claude_skills.iterdir())
        except OSError:
            claude_skill_dirs = []
        for skill_dir in claude_skill_dirs:
            if not skill_dir.is_dir():
                continue
            skill_md = skill_dir / 'SKILL.md'
            if skill_md.is_file():
                files.append(skill_md)
    return files


def _scan_skill(skill_md: Path) -> list[dict]:
    """Return a finding when the skill's SKILL.md lacks/invalidates ``mode:``."""
    try:
        text = skill_md.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        return []

    frontmatter = _parse_frontmatter_keys(text)
    declared = (frontmatter or {}).get('mode', '').strip()

    if declared in _VALID_MODES:
        return []

    reason = 'mode_missing' if not declared else 'mode_invalid'
    description = _DESCRIPTION_MISSING if not declared else _DESCRIPTION_INVALID
    details: dict = {
        'skill': skill_md.parent.name,
        'valid_modes': sorted(_VALID_MODES),
        'reason': reason,
    }
    if declared:
        details['declared_mode'] = declared

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


def analyze_skill_mode(marketplace_root: Path) -> list[dict]:
    """Scan every skill SKILL.md for a missing / invalid ``mode:`` field.

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
    for skill_md in _skill_md_files(marketplace_root):
        findings.extend(_scan_skill(skill_md))
    return findings

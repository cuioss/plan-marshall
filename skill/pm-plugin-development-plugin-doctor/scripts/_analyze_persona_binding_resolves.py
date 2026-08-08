#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Persona-binding-resolves analyzer for the ``persona-binding-resolves`` rule.

In the persona / ref / profile identity model, ``manage-personas resolve``
flattens a persona's composition DAG into a deduped ``skills[]`` (always
including the base ``persona-plan-marshall-agent``). A persona that declares a
``profiles:`` binding is a dispatch target: phase-4-plan resolves it to augment
a task's skills. This analyzer verifies that every persona declaring
``profiles:`` is actually **resolvable** — its composition DAG walk succeeds
(no cycle, every composed ``persona-*`` exists on disk), so the resolver returns
``status: success`` with a non-empty ``skills[]`` rather than an error
discriminator.

The check is performed **statically**, mirroring the resolver's DAG walk
(``manage_personas._flatten``) without importing the target script or shelling
out — consistent with the stdlib-only, no-subprocess pattern of the sibling
analyzers (``_analyze_skill_mode.py``, ``_analyze_persona_profile_uniqueness.py``).
A successful walk over the same on-disk frontmatter is equivalent to a
successful ``resolve`` call.

Scope
-----
``marketplace/bundles/*/skills/*/SKILL.md`` whose frontmatter declares
``implements: persona`` AND a non-empty ``profiles:`` list. Meta/evaluator
personas that omit ``profiles:`` are not dispatch targets and are out of scope.

Public API
----------
- ``analyze_persona_binding_resolves(marketplace_root)``: entry point.
- ``RULE_ID``: the canonical rule key.
"""

from __future__ import annotations

import re
from pathlib import Path

from _doctor_shared import Finding
from _rule_registry import RuleDescriptor

RULE_ID = 'persona-binding-resolves'
RULE_NAME = 'analyze_persona_binding_resolves'

RULE_DESCRIPTOR = RuleDescriptor(
    rule_id=RULE_ID,
    severity='error',
    category='structural',
    scope='corpus-relational',
)


def _leading_frontmatter(text: str) -> str:
    """Return the leading ``---``...``---`` YAML frontmatter block, or ''."""
    lines = text.split('\n')
    if not lines or lines[0].strip() != '---':
        return ''
    for i in range(1, len(lines)):
        if lines[i].strip() == '---':
            return '\n'.join(lines[1:i])
    return ''


def _parse_yaml_list(frontmatter: str, field: str) -> list[str]:
    """Parse a frontmatter list field, supporting inline-flow and block forms.

    Mirrors ``manage_personas._parse_yaml_list``. Returns an empty list when the
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


def _persona_md_path(marketplace_root: Path, persona_key: str) -> Path | None:
    """Resolve a ``bundle:skill`` persona key to its SKILL.md path, or None."""
    if ':' not in persona_key:
        return None
    bundle, skill = persona_key.split(':', 1)
    path = marketplace_root / bundle / 'skills' / skill / 'SKILL.md'
    return path if path.is_file() else None


def _read_persona(marketplace_root: Path, persona_key: str) -> dict | None:
    """Return a persona's parsed frontmatter, or None when it is absent.

    ``{'profiles': [...], 'composes': [...], 'is_persona': bool}``.
    """
    path = _persona_md_path(marketplace_root, persona_key)
    if path is None:
        return None
    try:
        text = path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        return None
    frontmatter = _leading_frontmatter(text)
    implements = re.search(r'^implements:\s*(.+)$', frontmatter, re.MULTILINE)
    is_persona = implements is not None and implements.group(1).strip().strip('\'"') == 'persona'
    return {
        'profiles': _parse_yaml_list(frontmatter, 'profiles'),
        'composes': _parse_yaml_list(frontmatter, 'composes'),
        'is_persona': is_persona,
    }


def _walk_resolvable(
    marketplace_root: Path,
    persona_key: str,
    visiting: set[str],
) -> str | None:
    """Statically walk a persona's composition DAG, mirroring the resolver.

    Returns an error discriminator (``composition_cycle`` /
    ``composed_persona_not_found``) on failure, or None when the persona
    resolves. Only ``persona-*`` composition edges are followed (ref-* concerns
    are leaf skills, not personas, and are not required to resolve as personas).
    """
    if persona_key in visiting:
        return 'composition_cycle'
    fm = _read_persona(marketplace_root, persona_key)
    if fm is None:
        return 'composed_persona_not_found'

    visiting.add(persona_key)
    for edge in fm['composes']:
        bare_skill = edge.split(':', 1)[1] if ':' in edge else edge
        if bare_skill.startswith('persona-'):
            err = _walk_resolvable(marketplace_root, edge, visiting)
            if err is not None:
                visiting.discard(persona_key)
                return err
    visiting.discard(persona_key)
    return None


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


def analyze_persona_binding_resolves(marketplace_root: Path) -> list[dict]:
    """Flag any profile-declaring persona whose composition DAG does not resolve.

    Parameters
    ----------
    marketplace_root:
        The bundles root (the directory that contains ``plan-marshall``,
        ``pm-plugin-development``, etc.).

    Returns
    -------
    list[dict]
        One finding per persona that declares ``profiles:`` but whose static
        composition-DAG walk fails (cycle or missing composed persona), meaning
        ``manage-personas resolve`` would return an error instead of a non-empty
        ``skills[]``.
    """
    findings: list[Finding] = []
    for skill_md in _skill_md_files(marketplace_root):
        try:
            text = skill_md.read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError):
            continue
        frontmatter = _leading_frontmatter(text)
        implements = re.search(r'^implements:\s*(.+)$', frontmatter, re.MULTILINE)
        is_persona = (
            implements is not None and implements.group(1).strip().strip('\'"') == 'persona'
        )
        if not is_persona:
            continue
        profiles = _parse_yaml_list(frontmatter, 'profiles')
        if not profiles:
            # No profiles binding — not a dispatch target, out of scope.
            continue
        bundle = skill_md.parent.parent.parent.name
        persona_key = f'{bundle}:{skill_md.parent.name}'
        err = _walk_resolvable(marketplace_root, persona_key, visiting=set())
        if err is None:
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
                    f'persona declares `profiles:` {profiles} but its composition '
                    f'DAG does not resolve (`{err}`) — `manage-personas resolve` '
                    'would return an error instead of a non-empty skills[], so the '
                    "profile binding is not backed by a resolvable persona. Fix the "
                    'broken composition edge (a missing composed persona or a '
                    'composition cycle).'
                ),
                details={
                    'skill': skill_md.parent.name,
                    'persona_key': persona_key,
                    'profiles': profiles,
                    'resolve_error': err,
                },
                extra={'rule': RULE_NAME},
            )
        )
    return [f.to_dict() for f in findings]

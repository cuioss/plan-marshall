#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The ONE reader of a staged spec's per-deliverable ``Skills:`` / ``Persona:`` lines.

Two consumers read the declaration, and they must agree about it: the runbook lane
loads what a deliverable declares, and the orchestrator's ``corpus spec-skills``
verb both fills and verifies the same lines. This module owns the grammar, the
declaration resolution and the existence probe; neither consumer carries a copy.

The declaration is a pair of child lines under a numbered deliverable::

    1. **A deliverable.**
       - Skills: pm-dev-python:python-core, plan-marshall:ref-toon-format
       - Persona: implementer

Both lines are OPTIONAL. A spec staged before they existed carries neither, and the
lane then falls back to the persona table's per-kind defaults with no domain skills —
so ``none named`` is a legal state, never an error.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

#: The heading that opens a staged spec's deliverable list.
DELIVERABLES_HEADING = '## Deliverables'

#: A numbered deliverable at column 0. Nested numbering is INDENTED, so the
#: sub-conditions a deliverable states are never mistaken for further
#: deliverables — a rule this parser depends on and a spec's own format supplies.
DELIVERABLE_HEAD_RE = re.compile(r'^(?P<number>\d+)\.\s+(?P<title>.+?)\s*$')

#: The two per-deliverable declarations. Both are OPTIONAL.
SKILLS_DECL_RE = re.compile(r'^(?:\s*[-*]\s*)?Skills:\s*(?P<value>.+?)\s*$')
PERSONA_DECL_RE = re.compile(r'^(?:\s*[-*]\s*)?Persona:\s*(?P<value>.+?)\s*$')


def _this_skill_dir() -> Path:
    """The shared module's own skill directory."""
    return Path(__file__).resolve().parents[1]


def _this_skills_root() -> Path:
    """The ``skills/`` directory this module ships in."""
    return Path(__file__).resolve().parents[2]


def installed_bundle(skill_dir: Path | None = None) -> str | None:
    """The bundle a skill ships in, used to resolve a BARE skill name.

    ``skill_dir`` defaults to this module's own directory. In the source tree and
    the nested plugin cache the bundle is the grandparent directory name. In a flat
    deployment the directory is the dash-joined ``{bundle}-{skill}``, which no
    separator position can split back into the pair, so the bundle is read from the
    identity the flat emitters record in the skill's ``SKILL.md``. ``None`` means a
    flat deployment that records no identity: a bare name then has no bundle to
    resolve in, and the caller reports that rather than probing a bundle that does
    not exist.
    """
    from deployed_layout import is_flat_root, read_flat_skill_identity
    from marketplace_bundles import extract_bundle_name

    directory = _this_skill_dir() if skill_dir is None else skill_dir
    identity = read_flat_skill_identity(directory)
    if identity is not None:
        return identity[0]
    if is_flat_root(directory.parent):
        return None
    return extract_bundle_name(directory.parents[1])


#: The literal value a deliverable writes when the project configures no domain
#: skills for its modules. It is a DECLARATION (the line is present, the author
#: looked) and never a skill name to probe.
NO_SKILLS_VALUE = 'none'


def spec_deliverables(spec: Path) -> list[dict[str, Any]]:
    """Read a staged spec's ``## Deliverables`` section into per-deliverable rows.

    Each row carries its number, title, raw ``Skills:`` value and raw
    ``Persona:`` value. Only lines INSIDE the section and outside a fenced block
    are read, so a spec that quotes the declaration format in prose or in an
    example does not declare anything by it.
    """
    try:
        lines = spec.read_text(encoding='utf-8').splitlines()
    except OSError:
        return []
    start = next((i for i, line in enumerate(lines) if line.strip() == DELIVERABLES_HEADING), None)
    if start is None:
        return []
    rows: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    in_fence = False
    for line in lines[start + 1 :]:
        if line.strip().startswith('```'):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if line.startswith('## '):
            break
        head = DELIVERABLE_HEAD_RE.match(line)
        if head:
            current = {
                'number': head.group('number'),
                'title': head.group('title').strip().strip('*').strip(),
                'skills': '',
                'persona': '',
            }
            rows.append(current)
            continue
        if current is None:
            continue
        skills = SKILLS_DECL_RE.match(line)
        if skills:
            current['skills'] = skills.group('value')
            continue
        persona = PERSONA_DECL_RE.match(line)
        if persona:
            current['persona'] = persona.group('value')
    return rows


def declared_skills(value: str) -> list[str]:
    """Split a ``Skills:`` value into its ``bundle:skill`` notations.

    The literal :data:`NO_SKILLS_VALUE` is dropped: a deliverable that writes
    ``Skills: none`` declares that the project configures none, and probing a skill
    called ``none`` would refuse an emission the author already answered.
    """
    skills: list[str] = []
    for part in value.split(','):
        name = part.strip().strip('`')
        if name and name.casefold() != NO_SKILLS_VALUE:
            skills.append(name)
    return skills


def declared_persona(value: str) -> str:
    """Normalise a ``Persona:`` value to a resolvable persona notation.

    ``implementer`` and ``plan-marshall:persona-implementer`` name the same
    skill. A name KEEPS its bundle when it carries one — a persona in another
    bundle must resolve there, not in the consumer's own — while a bare kind is
    prefixed with the canonical ``persona-`` marker and left bare, to be
    qualified with the consumer's own bundle at probe time.
    """
    persona = value.strip().strip('`')
    if not persona:
        return ''
    bundle, separator, skill = persona.partition(':')
    if not separator:
        skill = persona
    if not skill.startswith('persona-'):
        skill = f'persona-{skill}'
    return f'{bundle}:{skill}' if separator else skill


def skill_probe_paths(
    notation: str,
    bundle: str,
    *,
    skills_root: Path | None = None,
    anchor: Path | None = None,
) -> list[Path]:
    """Return every path probed for *notation*, in probe order.

    A bare name is qualified with ``bundle`` first, so a consumer's own skills
    resolve beside it without the caller spelling a bundle. ONE enumeration feeds
    both the existence answer and the "every probed path" error: the flat
    ``{bundle}-{skill}`` candidates come from the same vocabulary
    :func:`deployed_layout.resolve_skill_path` uses internally
    (:func:`deployed_layout.skill_roots` plus
    :func:`deployed_layout.flat_skill_dir_name`), and the nested bundle tree —
    every version dir in it — through :func:`marketplace_bundles.resolve_bundle_path`.

    ``skills_root`` and ``anchor`` default to this module's own install. A caller
    that lives in another install (the lane's own test harness materializes one)
    passes its own so the probe enumerates the tree the CALLER ships in.
    """
    from deployed_layout import flat_skill_dir_name, skill_roots

    root = _this_skills_root() if skills_root is None else skills_root
    name, separator, skill = notation.partition(':')
    if not separator:
        name, skill = bundle, notation
    subpath = f'skills/{skill}/SKILL.md'

    candidates: list[Path] = [base / flat_skill_dir_name(name, skill) / 'SKILL.md' for base in skill_roots(root)]
    try:
        from marketplace_bundles import resolve_bundle_path, resolve_bundles_root, select_live_version_dir

        bundles_root: Path | None = resolve_bundles_root(Path(__file__) if anchor is None else anchor)
    except Exception:
        bundles_root = None
    if bundles_root is not None:
        # A VERSIONED bundle cache has one live version dir, and that is the
        # path a probe actually reads. Naming the unversioned fallback for such a
        # cache reports a path that cannot exist on that machine.
        bundle_dir = bundles_root / name
        live_version: Path | None = None
        if bundle_dir.is_dir():
            live_version = select_live_version_dir(
                bundle_dir, lambda version_dir: (version_dir / '.claude-plugin' / 'plugin.json').is_file()
            )
        nested = (
            live_version / subpath if live_version is not None else resolve_bundle_path(bundles_root, name, subpath)
        )
        if nested not in candidates:
            candidates.append(nested)
    return candidates


def skill_exists(notation: str, bundle: str, *, skills_root: Path | None = None, anchor: Path | None = None) -> bool:
    """Whether *notation* names a skill installed in any deployed layout."""
    return any(path.is_file() for path in skill_probe_paths(notation, bundle, skills_root=skills_root, anchor=anchor))


def resolve_deliverable_skills(
    spec: Path,
    bundle: str | None = None,
    *,
    skills_root: Path | None = None,
    anchor: Path | None = None,
    skill_dir: Path | None = None,
) -> dict[str, Any]:
    """Resolve every deliverable's named skills and persona, and verify each exists.

    The declaration is authored by the ORCHESTRATOR when the spec is staged; the
    consumer only reads it. A name that does not resolve to an installed skill is
    reported as missing so the caller can stop and ask — or refuse the emission —
    rather than silently working without the standard it was told to apply.

    ``bundle`` defaults to :func:`installed_bundle`; ``None`` for a flat
    deployment records no identity, and then a BARE name has no bundle to resolve
    in and raises ``ValueError('flat_skill_identity_missing')`` — refusing by
    name rather than reporting a silent miss on every bare name. A qualified name
    carries its own bundle and needs this one not at all.
    """
    own_bundle = installed_bundle(skill_dir) if bundle is None else bundle
    rows = spec_deliverables(spec)
    declared: list[str] = []
    personas: list[str] = []
    # A declaration is the LINE, not the skill list: ``Skills: none`` states the
    # author looked and the project configures none, which is a different fact from
    # a deliverable that carries no line at all.
    declaration_seen = any(row['skills'].strip() or row['persona'].strip() for row in rows)
    for row in rows:
        skills = declared_skills(row['skills'])
        declared.extend(skills)
        row['declared_skills'] = skills
        row['skills'] = ', '.join(skills)
        row['persona'] = declared_persona(row['persona'])
        if row['persona']:
            personas.append(row['persona'])
    names = [*declared, *personas]
    if own_bundle is None:
        if any(':' not in name for name in names):
            raise ValueError('flat_skill_identity_missing')
        own_bundle = ''
    missing: list[str] = []
    probed: list[str] = []
    for name in names:
        if skill_exists(name, own_bundle, skills_root=skills_root, anchor=anchor):
            continue
        missing.append(name)
        probed.extend(
            str(candidate) for candidate in skill_probe_paths(name, own_bundle, skills_root=skills_root, anchor=anchor)
        )
    return {
        'deliverables': rows,
        'missing_skills': missing,
        'missing_probed': probed,
        'skills_note': 'declared' if declaration_seen else 'none named',
    }


__all__ = [
    'DELIVERABLES_HEADING',
    'DELIVERABLE_HEAD_RE',
    'NO_SKILLS_VALUE',
    'declared_persona',
    'declared_skills',
    'installed_bundle',
    'resolve_deliverable_skills',
    'skill_exists',
    'skill_probe_paths',
    'spec_deliverables',
]

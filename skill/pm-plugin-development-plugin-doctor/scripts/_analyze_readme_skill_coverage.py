#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""README-vs-plugin.json skill-coverage analyzer for the ``readme-skill-registration-drift`` rule.

This module detects drift between a bundle README's skill enumeration (the
hand-maintained mirror) and the skills its ``.claude-plugin/plugin.json``
registers (the machine-derivable source of truth). It is the same
mirror-versus-derived shape the canonical-enum guard applies one surface over:
a README that states a skill count or lists skills while ``plugin.json``
registers a different set is a stale oracle.

Why an OMITTED skill, not a wrong number, is the defect that matters
-------------------------------------------------------------------
A README undercount is cosmetic right up until the omitted skill is the one a
reader goes looking for — and in this tree three of the known undercounts hide a
*security* skill (``javascript-security``, ``python-security``,
``plugin-security``). So the check is keyed on COVERAGE, not on a parsed
headline number: every skill ``plugin.json`` registers MUST be named somewhere
in the README. A README whose parenthetical count is off by one but whose
enumeration is complete hides nothing and is not flagged; a README that silently
drops a registered skill from its enumeration is, because that omission is the
failure a reader is harmed by.

Source of truth
---------------
``{bundle}/.claude-plugin/plugin.json`` — its ``skills`` array, each entry a
``./skills/{name}`` (or ``skills/{name}``) path whose basename is the registered
skill name. That set is the derived population every finding publishes.

Detection
---------
For each bundle carrying both a ``plugin.json`` and a ``README.md``:

1. Read the registered skill-name set from ``plugin.json``.
2. For each registered name, test whether the README names it — as a
   backtick/bold/bare token bounded so a longer sibling never counts as a match
   (``plan-marshall`` inside ``plan-marshall-plugin`` is NOT a match for
   ``plan-marshall``).
3. Emit one error-severity, non-fixable finding per registered skill the README
   never names, each carrying the derived ``population_size`` so a clean bundle
   is provably a pass over a non-empty registration set rather than a vacant one.

Fail-closed
-----------
A bundle whose ``plugin.json`` is missing/unreadable/registers no skills, or
whose README is absent, is out of scope (no comparison is possible) and emits
nothing — the same short-circuit ``plugin-json-orphan-component`` uses. Only a
readable registration set paired with a readable README is checked.

Pattern alignment
-----------------
Mirrors ``_analyze_plugin_json.py`` / ``_analyze_literal_count.py``: pure static
analysis (``json`` + regex + pathlib), stdlib-only, no subprocess, no import of
any target, no mutation.

Findings have the shape::

    {
        'type': 'readme-skill-registration-drift',
        'rule_id': 'readme-skill-registration-drift',
        'rule': 'analyze_readme_skill_coverage',
        'file': '<absolute README.md path>',
        'line': <int, README Skills-heading line or 1>,
        'severity': 'error',
        'fixable': False,
        'description': '<human-readable drift description>',
        'details': {
            'bundle': '<bundle name>',
            'skill': '<omitted registered skill name>',
            'reason': 'registered_skill_absent_from_readme',
            'population_size': <int registered-skill count>,
        },
    }

Public API
----------
- ``analyze_readme_skill_coverage(marketplace_root)``: entry point.
- ``derive_readme_population(marketplace_root)``: per-bundle registered-skill
  population (the positive-population surface).
- ``RULE_ID``: the canonical rule key.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from _doctor_shared import Finding
from _rule_registry import RuleDescriptor

RULE_ID = 'readme-skill-registration-drift'
RULE_NAME = 'analyze_readme_skill_coverage'

RULE_DESCRIPTOR = RuleDescriptor(
    rule_id=RULE_ID,
    severity='error',
    category='structural',
    scope='corpus-relational',
)

# The README ``Skills`` heading, used only to anchor a finding's line number.
_SKILLS_HEADING_RE = re.compile(r'^#{1,6}\s+Skills\b')


@dataclass(frozen=True)
class BundleCoverage:
    """One bundle's registered-skill population and the subset absent from its README."""

    bundle: str
    readme: Path
    registered: tuple[str, ...]
    undocumented: tuple[str, ...]


def _registered_skill_names(plugin_json: Path) -> list[str]:
    """Return the basenames of the ``skills`` entries in ``plugin.json``.

    Each entry is a ``./skills/{name}`` (or ``skills/{name}``) path; the trailing
    path component is the registered skill name. A missing/unreadable/malformed
    manifest yields an empty list (out of scope, fail-closed).
    """
    try:
        data = json.loads(plugin_json.read_text(encoding='utf-8'))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return []
    if not isinstance(data, dict):
        return []
    entries = data.get('skills')
    if not isinstance(entries, list):
        return []
    names: list[str] = []
    for entry in entries:
        if isinstance(entry, str) and entry.strip():
            names.append(entry.rstrip('/').split('/')[-1])
    return names


def _readme_names_skill(readme_text: str, skill: str) -> bool:
    """Return True when ``skill`` is named as a whole token in ``readme_text``.

    Bounded by ``(?<![\\w-])`` / ``(?![\\w-])`` so a longer sibling never counts:
    ``plan-marshall`` does NOT match inside ``plan-marshall-plugin``, and
    ``python-core`` does not match inside ``python-core-extra``. Backtick or bold
    wrapping is irrelevant — the token match is on the name itself.
    """
    pattern = re.compile(r'(?<![\w-])' + re.escape(skill) + r'(?![\w-])')
    return bool(pattern.search(readme_text))


def _skills_heading_line(readme_text: str) -> int:
    """Return the 1-based line of the README's first ``Skills`` heading, or 1."""
    for idx, line in enumerate(readme_text.splitlines(), start=1):
        if _SKILLS_HEADING_RE.match(line):
            return idx
    return 1


def derive_readme_population(marketplace_root: Path) -> list[BundleCoverage]:
    """Return per-bundle registered-skill coverage over the whole tree.

    Each :class:`BundleCoverage` carries the bundle's full registered-skill
    population and the subset its README fails to name. The population is the
    positive-population surface: a clean bundle is a non-empty ``registered``
    with an empty ``undocumented`` — distinguishable from a bundle that examined
    nothing.
    """
    coverage: list[BundleCoverage] = []
    try:
        bundle_dirs = sorted(marketplace_root.iterdir())
    except OSError:
        return coverage
    for bundle_dir in bundle_dirs:
        if not bundle_dir.is_dir():
            continue
        plugin_json = bundle_dir / '.claude-plugin' / 'plugin.json'
        readme = bundle_dir / 'README.md'
        if not plugin_json.is_file() or not readme.is_file():
            continue
        registered = _registered_skill_names(plugin_json)
        if not registered:
            continue
        try:
            readme_text = readme.read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError):
            continue
        undocumented = tuple(
            name for name in registered if not _readme_names_skill(readme_text, name)
        )
        coverage.append(
            BundleCoverage(
                bundle=bundle_dir.name,
                readme=readme,
                registered=tuple(registered),
                undocumented=undocumented,
            )
        )
    return coverage


def analyze_readme_skill_coverage(marketplace_root: Path) -> list[dict]:
    """Flag every plugin.json-registered skill a bundle README fails to name.

    Parameters
    ----------
    marketplace_root:
        The bundles root (the directory that contains ``plan-marshall``,
        ``pm-plugin-development``, etc.).

    Returns
    -------
    list[dict]
        One finding per registered skill absent from its bundle README. Every
        finding publishes the bundle's registered-skill ``population_size`` so a
        clean result proves coverage over a non-empty registration set.
    """
    findings: list[Finding] = []
    for cov in derive_readme_population(marketplace_root):
        if not cov.undocumented:
            continue
        try:
            line = _skills_heading_line(cov.readme.read_text(encoding='utf-8'))
        except (OSError, UnicodeDecodeError):
            line = 1
        for skill in cov.undocumented:
            findings.append(
                Finding(
                    type=RULE_ID,
                    file=str(cov.readme),
                    line=line,
                    severity='error',
                    fixable=False,
                    rule_id=RULE_ID,
                    description=(
                        f'Bundle `{cov.bundle}` registers skill `{skill}` in plugin.json '
                        f'but its README never names it — the README enumeration is a '
                        f'stale mirror of the registration (readme-skill-registration-drift). '
                        f'An omitted skill is invisible to a reader who goes looking for it.'
                    ),
                    details={
                        'bundle': cov.bundle,
                        'skill': skill,
                        'reason': 'registered_skill_absent_from_readme',
                        'population_size': len(cov.registered),
                    },
                    extra={'rule': RULE_NAME},
                )
            )
    return [f.to_dict() for f in findings]

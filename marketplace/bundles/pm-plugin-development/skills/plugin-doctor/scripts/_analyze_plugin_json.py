#!/usr/bin/env python3
"""plugin.json bidirectional manifest analyzer.

This module houses the reverse-direction half of the plugin.json
manifest-integrity check — the ``plugin-json-orphan-component`` rule — and
re-exports the forward-direction ``declared-component-vs-disk`` analyzer from
``_analyze_declared_vs_disk.py`` so the orchestrator can wire the full
bidirectional audit from one import site.

Two directions, one manifest contract:

- **forward** (``declared-component-vs-disk``, in ``_analyze_declared_vs_disk``):
  every entry declared in ``plugin.json`` must resolve to a file on disk.
- **reverse** (``plugin-json-orphan-component``, here): every on-disk
  component the bundle ships under ``skills/*/SKILL.md`` / ``agents/*.md`` /
  ``commands/*.md`` must be declared in its bundle's ``plugin.json`` — UNLESS
  it is legitimately unregistered per the marketplace registration convention.

Registration convention (the exemption)
---------------------------------------
Not every on-disk skill is registered in ``plugin.json`` (see the registration
convention in ``frontmatter-standards.md``):

1. **user-invocable skills** (``user-invocable: true``) — MUST register. An
   undeclared one is a real orphan.
2. **context-loaded / script-only / extension-implementor skills**
   (``user-invocable: false``) — registration is optional (script-only skills
   invoked solely via 3-part executor notation, and extension implementors
   discovered dynamically via ``implements:``, are deliberately NOT declared).

The orphan rule therefore flags an undeclared SKILL.md only when its
frontmatter declares ``user-invocable: true``. Agents and commands are always
registered, so any undeclared ``agents/*.md`` / ``commands/*.md`` is an orphan
with no frontmatter exemption.

Severity
--------
``plugin-json-orphan-component`` is advisory (``severity: warning``,
``fixable: false``) — a missing user-invocable registration degrades
discoverability rather than breaking a resolving reference. The rule runs under
``cmd_analyze`` only, never the build-failing ``cmd_quality_gate``.

Pattern alignment
-----------------
Pure static analysis: ``json`` + ``pathlib``, regex-free frontmatter scan, no
subprocess execution, no imports of target scripts, no mutation.

Public API
----------
- ``analyze_plugin_json_orphans(marketplace_root)``: the reverse-direction
  orphan analyzer.
- ``analyze_declared_vs_disk``: re-exported forward-direction analyzer.
- ``RULE_ID``: the orphan rule key.
"""

from __future__ import annotations

import json
from pathlib import Path

from _analyze_declared_vs_disk import analyze_declared_vs_disk

__all__ = [
    'RULE_ID',
    'analyze_declared_vs_disk',
    'analyze_plugin_json_orphans',
]

RULE_ID = 'plugin-json-orphan-component'
RULE_NAME = 'analyze_plugin_json_orphans'

_COMPONENT_KEYS = ('agents', 'commands', 'skills')


def _declared_entries(data: dict) -> set[str]:
    """Collect the normalised set of declared component path strings.

    Entries are normalised by stripping a leading ``./`` so disk-side and
    manifest-side spellings compare directly.
    """
    declared: set[str] = set()
    for key in _COMPONENT_KEYS:
        entries = data.get(key)
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if isinstance(entry, str) and entry.strip():
                rel = entry[2:] if entry.startswith('./') else entry
                declared.add(rel.rstrip('/'))
    return declared


def _frontmatter_user_invocable(skill_md: Path) -> bool | None:
    """Return the SKILL.md ``user-invocable`` boolean, or ``None`` when absent.

    Parses only the leading ``---``-fenced frontmatter, scanning for a
    top-level ``user-invocable:`` scalar. ``true`` → ``True``; ``false`` →
    ``False``; missing key / no frontmatter → ``None``.
    """
    try:
        text = skill_md.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        return None
    if not text.startswith('---'):
        return None
    in_block = False
    for index, line in enumerate(text.splitlines()):
        stripped = line.strip()
        if index == 0:
            if stripped != '---':
                return None
            in_block = True
            continue
        if not in_block:
            break
        if stripped == '---':
            break
        if not stripped or stripped.startswith('#') or ':' not in stripped:
            continue
        key, _, value = stripped.partition(':')
        if key.strip() == 'user-invocable':
            normalised = value.strip().strip('"').strip("'").lower()
            if normalised == 'true':
                return True
            if normalised == 'false':
                return False
            return None
    return None


def _orphan_finding(component_path: Path, bundle: str, kind: str, rel: str) -> dict:
    """Construct a single ``plugin-json-orphan-component`` finding."""
    return {
        'rule_id': RULE_ID,
        'type': RULE_ID,
        'rule': RULE_NAME,
        'file': str(component_path),
        'line': 1,
        'severity': 'warning',
        'fixable': False,
        'description': (
            f'On-disk {kind} `{rel}` is not declared in bundle `{bundle}`\'s '
            f'plugin.json — the component ships but is invisible to the plugin '
            f'loader (plugin-json-orphan-component)'
        ),
        'details': {
            'bundle': bundle,
            'component_kind': kind,
            'disk_entry': rel,
            'reason': 'undeclared_on_disk_component',
        },
    }


def _scan_bundle(bundle_dir: Path) -> list[dict]:
    """Scan one bundle for on-disk components missing from its plugin.json."""
    plugin_json = bundle_dir / '.claude-plugin' / 'plugin.json'
    try:
        data = json.loads(plugin_json.read_text(encoding='utf-8'))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return []
    if not isinstance(data, dict):
        return []

    declared = _declared_entries(data)
    bundle = bundle_dir.name
    findings: list[dict] = []

    # Skills: skills/{skill}/SKILL.md → declared as skills/{skill}. Only
    # user-invocable: true skills are required to register.
    skills_dir = bundle_dir / 'skills'
    if skills_dir.is_dir():
        for skill_md in sorted(skills_dir.glob('*/SKILL.md')):
            skill_dir = skill_md.parent
            rel = f'skills/{skill_dir.name}'
            if rel in declared:
                continue
            if _frontmatter_user_invocable(skill_md) is not True:
                # Script-only / context-loaded / extension implementor skills
                # are legitimately unregistered — exempt.
                continue
            findings.append(_orphan_finding(skill_md, bundle, 'skill', rel))

    # Agents and commands always register; any undeclared file is an orphan.
    for kind, sub in (('agent', 'agents'), ('command', 'commands')):
        sub_dir = bundle_dir / sub
        if not sub_dir.is_dir():
            continue
        for md_file in sorted(sub_dir.glob('*.md')):
            rel = f'{sub}/{md_file.name}'
            if rel in declared:
                continue
            findings.append(_orphan_finding(md_file, bundle, kind, rel))

    return findings


def analyze_plugin_json_orphans(marketplace_root: Path) -> list[dict]:
    """Scan every bundle for on-disk components missing from its plugin.json.

    Parameters
    ----------
    marketplace_root:
        The bundles root (the directory that contains ``plan-marshall``,
        ``pm-plugin-development``, etc.).

    Returns
    -------
    list[dict]
        A list of ``plugin-json-orphan-component`` finding dicts.
    """
    findings: list[dict] = []
    for bundle_dir in sorted(marketplace_root.iterdir()):
        if not bundle_dir.is_dir():
            continue
        if not (bundle_dir / '.claude-plugin' / 'plugin.json').is_file():
            continue
        findings.extend(_scan_bundle(bundle_dir))
    return findings

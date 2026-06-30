#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Declared-vs-disk analyzer for the ``declared-component-vs-disk`` rule.

This module implements the forward-direction half of the plugin.json
manifest-integrity check: for every component declared in a bundle's
``.claude-plugin/plugin.json`` (under ``agents`` / ``commands`` / ``skills``),
assert that the corresponding file exists on disk. A declared entry whose
target file is missing produces a finding.

The reverse direction (on-disk components NOT declared in plugin.json — the
``plugin-json-orphan-component`` rule) lives in ``_analyze_plugin_json.py``.
Keeping one module per direction mirrors the analyzer-module convention used
elsewhere in this scripts directory; the orchestrator re-exports both.

Manifest entry shapes
---------------------
``plugin.json`` lists each component as a relative path string anchored at the
bundle root:

- skills: ``./skills/{skill}`` → resolves to ``{bundle}/skills/{skill}/SKILL.md``
- agents: ``./agents/{agent}.md`` → resolves to ``{bundle}/agents/{agent}.md``
- commands: ``./commands/{command}.md`` → resolves to
  ``{bundle}/commands/{command}.md``

A skill entry points at the skill DIRECTORY; the on-disk anchor is its
``SKILL.md``. Agent / command entries point directly at the markdown file.

Pattern alignment
-----------------
The analyzer mirrors ``_analyze_role_field.py`` and
``_analyze_notation_staleness.py``:

- pure static analysis (no subprocess execution, no imports of target scripts);
- stdlib-only dependencies (``json`` + ``pathlib``);
- no mutation of any file;
- findings carry ``rule_id``/``type``/``rule``/``file``/``line``/``severity``/
  ``fixable``/``description`` with rule-specific fields under ``details``.

Public API
----------
- ``analyze_declared_vs_disk(marketplace_root)``: entry point — scans every
  bundle's ``plugin.json`` under ``marketplace_root`` and returns findings.
- ``RULE_ID``: the canonical rule key.
"""

from __future__ import annotations

import json
from pathlib import Path

from _doctor_shared import Finding  # type: ignore[import-not-found]

RULE_ID = 'declared-component-vs-disk'
RULE_NAME = 'analyze_declared_vs_disk'

# The three plugin.json array keys whose entries point at on-disk components.
_COMPONENT_KEYS = ('agents', 'commands', 'skills')


def _resolve_declared_path(bundle_dir: Path, key: str, entry: str) -> Path:
    """Resolve a plugin.json entry string to its on-disk anchor path.

    ``entry`` is a bundle-root-relative path (``./skills/foo`` or
    ``./agents/foo.md``). The leading ``./`` is optional. For skill entries the
    anchor is the directory's ``SKILL.md``; for agents / commands the anchor is
    the markdown file the entry names directly.
    """
    rel = entry[2:] if entry.startswith('./') else entry
    target = bundle_dir / rel
    if key == 'skills':
        return target / 'SKILL.md'
    return target


def _scan_plugin_json(plugin_json: Path) -> list[dict]:
    """Scan a single ``plugin.json`` and return declared-but-missing findings."""
    try:
        data = json.loads(plugin_json.read_text(encoding='utf-8'))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        # Malformed / unreadable manifest is not this rule's failure mode —
        # the invalid-yaml / json structural rules cover that. Skip silently.
        return []
    if not isinstance(data, dict):
        return []

    bundle_dir = plugin_json.parent.parent
    findings: list[Finding] = []
    for key in _COMPONENT_KEYS:
        entries = data.get(key)
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, str) or not entry.strip():
                continue
            anchor = _resolve_declared_path(bundle_dir, key, entry)
            if anchor.is_file():
                continue
            findings.append(
                Finding(
                    type=RULE_ID,
                    file=str(plugin_json),
                    line=1,
                    severity='error',
                    fixable=False,
                    rule_id=RULE_ID,
                    description=(
                        f'plugin.json declares {key[:-1]} `{entry}` but the '
                        f'expected file `{anchor}` does not exist on disk — the '
                        f'declared component does not resolve '
                        f'(declared-component-vs-disk)'
                    ),
                    details={
                        'bundle': bundle_dir.name,
                        'component_kind': key[:-1],
                        'declared_entry': entry,
                        'expected_path': str(anchor),
                        'reason': 'declared_file_missing',
                    },
                    extra={'rule': RULE_NAME},
                )
            )
    return [f.to_dict() for f in findings]


def analyze_declared_vs_disk(marketplace_root: Path) -> list[dict]:
    """Scan every bundle's plugin.json for declared-but-missing components.

    Parameters
    ----------
    marketplace_root:
        The bundles root (the directory that contains ``plan-marshall``,
        ``pm-plugin-development``, etc.). Every ``.claude-plugin/plugin.json``
        beneath it is scanned.

    Returns
    -------
    list[dict]
        A list of finding dicts (see module docstring for the shape). Returns
        an empty list when no plugin.json files exist under the root.
    """
    findings: list[dict] = []
    try:
        plugin_jsons = sorted(marketplace_root.rglob('.claude-plugin/plugin.json'))
    except OSError:
        return findings
    for plugin_json in plugin_jsons:
        if plugin_json.is_file():
            findings.extend(_scan_plugin_json(plugin_json))
    return findings

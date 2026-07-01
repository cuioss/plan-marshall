#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""``error_type`` field scanner for the ``WORKFLOW_DOC_TOON_ERROR_FIELD`` rule.

This module implements a deterministic regex-based static analyzer that
detects fenced ``toon`` blocks using the non-canonical ``error_type`` key
where the canonical error-envelope discriminator field is ``error``.

The canonical contract (established at
``plan-marshall/skills/plan-marshall/workflow/planning.md``) shapes an agent /
workflow error TOON block as::

    status: error
    error: refine_contract_violation
    display_detail: "Human-readable message"

Some workflow and agent docs drifted to ``error_type:`` for the category
discriminator. Because the orchestrator and the execution-context dispatcher
branch on the field name they read out of the TOON block, the drifted key
silently desynchronises the read-side match. This rule flags the drift class
so it does not recur after the normalization sweep that established the
``error:`` pattern.

The rule mirrors ``_analyze_tmp_redirect_in_skills.py``:

- pure static analysis (no subprocess execution, no imports of target scripts)
- regex-driven extraction from fenced ``toon`` blocks only
- stdlib-only dependencies
- no mutation of any file

Detection scope (fenced ``toon`` ONLY)
--------------------------------------
The analyzer builds a fence map of every fenced block whose info-string is
``toon`` in plan-marshall ``{skills,agents,commands}/**/*.md``. Within each
fenced TOON block, it flags any line whose TOON key is ``error_type`` — both
the colon-style (``error_type:``) and the tab-style (``error_type\t``) forms,
since TOON blocks may use either key/value separator.

The analyzer deliberately does NOT flag:

1. Inline ``{status: error, error_type: ...}`` table shorthands — these are not
   fenced agent/workflow error TOON blocks (the key is not at the start of a
   TOON line, it is embedded in an inline brace shorthand).
2. Prose ``error_type:`` references in narrative or log-message text — they live
   outside any ``toon`` fence.
3. ``error_type`` keys appearing inside a non-``toon`` fence (e.g. a ``python``
   or ``json`` fence) — those are not workflow/agent error TOON blocks.

These exclusions are intentional and agree with the normalization sweep's
scope: every fenced TOON site the sweep normalized is exactly the site set this
rule detects.

Findings have the shape::

    {
        'rule_id': 'WORKFLOW_DOC_TOON_ERROR_FIELD',
        'type': 'WORKFLOW_DOC_TOON_ERROR_FIELD',
        'rule': 'analyze_workflow_doc_toon_error_field',
        'file': '<absolute markdown path>',
        'line': <int, 1-based>,
        'severity': 'error',
        'fixable': False,
        'snippet': '<offending text excerpt, max 80 chars>',
        'description': '<short human-readable explanation>',
    }

Public API
----------
- ``analyze_workflow_doc_toon_error_field(marketplace_root)``: entry point —
  scans every ``*.md`` under
  ``marketplace_root/plan-marshall/{skills,agents,commands}/``.
"""

from __future__ import annotations

import re
from pathlib import Path

from _doctor_shared import Finding  # type: ignore[import-not-found]
from _rule_registry import RuleDescriptor

RULE_ID = 'WORKFLOW_DOC_TOON_ERROR_FIELD'
RULE_NAME = 'analyze_workflow_doc_toon_error_field'
FINDING_TYPE = 'WORKFLOW_DOC_TOON_ERROR_FIELD'

RULE_DESCRIPTOR = RuleDescriptor(
    rule_id=RULE_ID,
    severity='error',
    category='safety',
    scope='file-local',
)

# ---------------------------------------------------------------------------
# Detection patterns
# ---------------------------------------------------------------------------

_FENCE_OPEN_RE = re.compile(r'^\s*```\s*([A-Za-z0-9_+-]*)\s*$')
_FENCE_CLOSE_RE = re.compile(r'^\s*```\s*$')

_TOON_FENCE_INFO_STRINGS = frozenset({'toon'})

# Match an ``error_type`` TOON key at the start of a TOON line: optional leading
# whitespace, the literal ``error_type``, then either a colon (``error_type:``)
# or a tab (``error_type\t``) as the key/value separator. Anchoring at the line
# start (after whitespace) is what excludes inline ``{..., error_type: ...}``
# brace shorthands, where the key is not the first token on the line.
_TOON_ERROR_TYPE_KEY_RE = re.compile(r'^(\s*)error_type(?::|\t)')


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_fence_map(lines: list[str]) -> dict[int, str]:
    """Map 0-based line indices inside any fenced block to the info-string."""
    inside: dict[int, str] = {}
    in_fence = False
    info_string = ''
    for idx, line in enumerate(lines):
        if not in_fence:
            m = _FENCE_OPEN_RE.match(line)
            if m:
                in_fence = True
                info_string = m.group(1).lower()
        else:
            if _FENCE_CLOSE_RE.match(line):
                in_fence = False
                info_string = ''
            else:
                inside[idx] = info_string
    return inside


def _make_finding(path: Path, line_no: int, line: str) -> dict:
    snippet = line.strip()[:80]
    return Finding(
        type=FINDING_TYPE,
        file=str(path),
        line=line_no,
        severity='error',
        fixable=False,
        rule_id=RULE_ID,
        description=(
            'Fenced ``toon`` error block uses the non-canonical ``error_type`` key. '
            'The canonical error-envelope discriminator field is ``error`` (see '
            'plan-marshall workflow/planning.md). Rename the key to ``error``; for a '
            'two-key block carrying both a category and a human-readable message, '
            'demote the message to ``display_detail``.'
        ),
        extra={'rule': RULE_NAME, 'snippet': snippet},
    ).to_dict()


# ---------------------------------------------------------------------------
# File-level scanner
# ---------------------------------------------------------------------------


def _scan_file(path: Path) -> list[dict]:
    """Scan a single markdown file and return all findings."""
    try:
        text = path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError) as exc:
        return [
            Finding(
                type='file_read_error',
                file=str(path),
                line=0,
                severity='error',
                fixable=False,
                rule_id=RULE_ID,
                description=f'Could not read file: {exc}',
                extra={'rule': RULE_NAME, 'snippet': ''},
            ).to_dict()
        ]

    lines = text.splitlines()
    fence_map = _build_fence_map(lines)
    findings: list[dict] = []

    for idx, line in enumerate(lines):
        fence_info = fence_map.get(idx)
        if fence_info not in _TOON_FENCE_INFO_STRINGS:
            continue

        if _TOON_ERROR_TYPE_KEY_RE.match(line):
            findings.append(_make_finding(path, idx + 1, line))

    return findings


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def _markdown_targets(marketplace_root: Path) -> list[Path]:
    """Return every ``*.md`` under plan-marshall skills, agents, and commands."""
    targets: list[Path] = []
    bundle = marketplace_root / 'plan-marshall'
    for subdir in ('skills', 'agents', 'commands'):
        root = bundle / subdir
        if root.is_dir():
            targets.extend(sorted(p for p in root.rglob('*.md') if p.is_file()))
    return targets


def analyze_workflow_doc_toon_error_field(marketplace_root: Path) -> list[dict]:
    """Scan plan-marshall workflow/agent markdown for ``error_type`` TOON keys.

    Walks ``marketplace_root/plan-marshall/{skills,agents,commands}/**/*.md``
    and reports every ``error_type`` key (colon- or tab-style) appearing inside
    a fenced ``toon`` block.

    Parameters
    ----------
    marketplace_root:
        Path to the marketplace root (the directory that contains the
        ``plan-marshall``, ``pm-dev-java``, etc. bundle directories — i.e.
        ``<repo>/marketplace/bundles``).

    Returns
    -------
    list[dict]
        List of finding dicts (empty for a clean tree).
    """
    findings: list[dict] = []
    for md_path in _markdown_targets(marketplace_root):
        findings.extend(_scan_file(md_path))
    return findings

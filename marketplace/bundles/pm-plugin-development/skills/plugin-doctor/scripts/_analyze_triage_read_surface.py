#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Triage-reads-top-level-only analyzer (build-failing under ``quality-gate``).

The consolidated find/triage flow files every producer's untrusted free-text to
the ``manage-findings`` ledger under a quarantined ``raw_input.{field}``
sub-namespace, then a single batched ``validate_struct`` ingestion pass promotes
only the cleaned values to the clean TOP-LEVEL field names. The containment
invariant is structural: ``raw_input.*`` = un-ingested untrusted quarantine,
kept solely for audit; top-level = clean-by-construction. **Triage MUST read
top-level fields only, never ``raw_input.*``** — reading the quarantine namespace
re-opens the prompt-injection surface the ingestion boundary closes.

This analyzer is the static backstop for that invariant: it flags any triage
surface (a triage workflow doc or an ``ext-triage-{domain}`` skill doc) that
READS a ``raw_input`` field. The detection is deliberately narrow — it matches
only ACCESS expressions that read a concrete field FROM ``raw_input``, never the
placeholder/wildcard forms (``raw_input.*``, ``raw_input.{field}``) that the
docs legitimately use when DOCUMENTING the invariant. So a doc that states
"triage never reads ``raw_input.*``" is not a false positive, while a doc that
instructs reading ``raw_input.detail`` (or subscripts the ``raw_input``
sub-object) is flagged.

Pattern alignment
-----------------
Mirrors ``_analyze_lane_frontmatter.py`` / ``_analyze_finalize_step_token.py``:
pure static regex analysis, stdlib-only, no target-script imports, no file
mutation. Builds uniform :class:`Finding` objects and exposes a module-level
``RULE_DESCRIPTOR`` collected by the central registry.

Triage surface
--------------
A file is a triage surface when EITHER:

- its basename is ``triage.md`` or ``verification-feedback.md`` (the consolidated
  triage workflow docs), OR
- it lives under a directory whose name starts with ``ext-triage-`` (the
  per-domain ``ext-triage-{domain}`` triage skills).

The ``manage-findings`` store scripts — which legitimately WRITE and INGEST the
``raw_input`` namespace — are NOT triage surfaces and are never scanned.

Public API
----------
- ``analyze_triage_read_surface(marketplace_root)``: entry point — scans every
  triage surface under the bundles root and returns a finding per line that reads
  ``raw_input`` (empty list for a clean tree).
"""

from __future__ import annotations

import re
from pathlib import Path

from _doctor_shared import Finding
from _rule_registry import RuleDescriptor

RULE_ID = 'triage-reads-top-level-only'
RULE_NAME = 'analyze_triage_read_surface'
FINDING_TYPE = 'triage_reads_raw_input'

RULE_DESCRIPTOR = RuleDescriptor(
    rule_id=RULE_ID,
    severity='error',
    category='safety',
    scope='file-local',
)

# The consolidated triage workflow docs, identified by basename.
_TRIAGE_DOC_BASENAMES = ('triage.md', 'verification-feedback.md')

# Prefix identifying an ``ext-triage-{domain}`` skill directory.
_EXT_TRIAGE_DIR_PREFIX = 'ext-triage-'

# ``raw_input`` READ patterns — each matches an ACCESS that reads a concrete
# field from the quarantine namespace. The placeholder/wildcard forms the docs
# use to DOCUMENT the invariant (``raw_input.*``, ``raw_input.{field}``) do NOT
# match: ``.*`` and ``.{`` never satisfy the ``.<lowercase-identifier>`` shape,
# and a bare backtick-quoted ``raw_input`` mention carries no access token.
_RAW_INPUT_READ_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r'raw_input\s*\.\s*[a-z][a-z0-9_]*'),  # raw_input.detail / raw_input.get(
    re.compile(r'raw_input\s*\['),  # raw_input['detail']
    re.compile(r"""\[\s*['"]raw_input['"]\s*\]"""),  # finding['raw_input']
    re.compile(r"""\.get\(\s*['"]raw_input['"]"""),  # finding.get('raw_input')
)


def _is_triage_surface(path: Path) -> bool:
    """Return True when ``path`` is a triage workflow doc or ext-triage skill doc."""
    if path.name in _TRIAGE_DOC_BASENAMES:
        return True
    return any(part.startswith(_EXT_TRIAGE_DIR_PREFIX) for part in path.parts)


def _reads_raw_input(line: str) -> bool:
    """Return True when ``line`` contains a concrete ``raw_input`` field read."""
    return any(pattern.search(line) for pattern in _RAW_INPUT_READ_PATTERNS)


def _scan_file(path: Path) -> list[Finding]:
    """Scan one triage-surface file and emit a finding per ``raw_input``-reading line."""
    try:
        text = path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        return []

    findings: list[Finding] = []
    for index, line in enumerate(text.splitlines(), start=1):
        if not _reads_raw_input(line):
            continue
        findings.append(
            Finding(
                type=FINDING_TYPE,
                file=str(path),
                line=index,
                severity='error',
                fixable=False,
                rule_id=RULE_ID,
                description=(
                    'triage surface reads the `raw_input.*` quarantine namespace — '
                    'triage MUST read the clean top-level fields only (the batched '
                    '`manage-findings ingest` pass already promoted validated values '
                    'to top-level). Reading `raw_input.*` re-opens the prompt-injection '
                    'surface the ingestion boundary closes. See '
                    'plan-marshall:manage-findings/standards/jsonl-format.md and the '
                    'containment invariant in triage.md.'
                ),
                extra={'rule': RULE_NAME, 'snippet': line.strip()[:120]},
            )
        )
    return findings


def analyze_triage_read_surface(marketplace_root: Path) -> list[dict]:
    """Flag every triage surface under ``marketplace_root`` that reads ``raw_input.*``.

    ``marketplace_root`` is the bundles root (the directory that contains
    ``plan-marshall``, ``pm-plugin-development``, etc.). Walks every ``.md`` file,
    keeps the triage surfaces (see module docstring), and returns a finding per
    line that reads a concrete ``raw_input`` field. Returns an empty list when the
    tree is absent; unreadable files are skipped silently.
    """
    marketplace_root = Path(marketplace_root)
    if not marketplace_root.is_dir():
        return []

    findings: list[Finding] = []
    for md_path in sorted(marketplace_root.rglob('*.md')):
        if not _is_triage_surface(md_path):
            continue
        findings.extend(_scan_file(md_path))
    return [f.to_dict() for f in findings]

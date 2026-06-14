#!/usr/bin/env python3
"""TOON prose status-conflation scanner for the ``MANAGE_STATUS_PROSE_CONFLATION`` rule.

This module implements a deterministic regex-based static analyzer that
detects inline-code prose of the form ``status: {specific_code}`` that
conflates the two-tier TOON error envelope.

The canonical two-tier error contract (see
``pm-plugin-development:plugin-script-architecture/standards/output-contract.md``
§ "Operation Failure (exit 0, status: error)") shapes a failure envelope as::

    status: error
    error: plan_not_found

The ``status`` field is ALWAYS the literal ``error`` on failure; the specific
failure code lives in the ``error`` field. Prose that writes ``status:
plan_not_found`` (or any ``status: {code}`` where ``{code}`` is neither
``error`` nor ``success``) misdescribes the contract — it collapses the two
tiers into one, telling the reader that the discriminator-and-code live on a
single ``status`` key. This rule flags that misdescription so it does not recur.

The rule mirrors ``_analyze_workflow_doc_toon_error_field.py``:

- pure static analysis (no subprocess execution, no imports of target scripts)
- regex-driven extraction from source
- stdlib-only dependencies
- no mutation of any file

Detection scope (inline-code spans ONLY)
----------------------------------------
The analyzer is anchored to markdown inline-code spans (backtick-wrapped). For
each line it enumerates the inline-code spans and, within each span, matches the
``status: {token}`` shape where ``{token}`` is a bare identifier. The match is
flagged when ``{token}`` is NEITHER ``error`` NOR ``success`` — both of which
are correct, fully-formed top-level discriminator values.

The analyzer deliberately does NOT flag:

1. ``status: error`` / ``status: success`` inside inline-code spans — these name
   the two correct top-level discriminator values, not a conflated code.
2. ``status: {code}`` in plain prose (outside any inline-code span) — narrative
   text describing a value is not a contract misdescription.
3. ``status: {code}`` inside a fenced code block (any info-string) — a fenced
   TOON / shell / python block is illustrating a literal payload, not prose.

The rule intentionally accepts some residual false positives (an inline-code
``status: {code}`` that legitimately documents a non-error value) in exchange
for catching the structural misdescription.

Findings have the shape::

    {
        'rule_id': 'MANAGE_STATUS_PROSE_CONFLATION',
        'type': 'MANAGE_STATUS_PROSE_CONFLATION',
        'rule': 'analyze_toon_prose_status_conflation',
        'file': '<absolute markdown path>',
        'line': <int, 1-based>,
        'severity': 'error',
        'fixable': False,
        'snippet': '<offending text excerpt, max 80 chars>',
        'description': '<short human-readable explanation>',
    }

Public API
----------
- ``analyze_toon_prose_status_conflation(marketplace_root)``: entry point —
  scans every ``*.md`` under
  ``marketplace_root/plan-marshall/{skills,agents,commands}/`` (plan-marshall
  bundle ONLY — TOON contracts are plan-marshall-owned prose).
"""

from __future__ import annotations

import re
from pathlib import Path

RULE_ID = 'MANAGE_STATUS_PROSE_CONFLATION'
RULE_NAME = 'analyze_toon_prose_status_conflation'
FINDING_TYPE = 'MANAGE_STATUS_PROSE_CONFLATION'

# ---------------------------------------------------------------------------
# Detection patterns
# ---------------------------------------------------------------------------

_FENCE_OPEN_RE = re.compile(r'^\s*```\s*([A-Za-z0-9_+-]*)\s*$')
_FENCE_CLOSE_RE = re.compile(r'^\s*```\s*$')

# Inline-code span detection (matches `...`).
_INLINE_CODE_RE = re.compile(r'`([^`]+)`')

# Match a ``status: {token}`` shape where {token} is a bare identifier. The
# token is captured for the error/success exemption check. ``status`` must sit
# at the start of the span body (after optional leading whitespace) so that
# embedded prose like "the status: field" is not over-matched.
_STATUS_KV_RE = re.compile(r'^\s*status:\s*([A-Za-z_][A-Za-z0-9_]*)\b')

# The two correct top-level discriminator values — exempt.
_EXEMPT_CODES = frozenset({'error', 'success'})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_fence_map(lines: list[str]) -> dict[int, str]:
    """Map 0-based line indices inside any fenced block to the info-string.

    Lines that are NOT inside a fence are absent from the map. The fence
    delimiter lines (the opening / closing ``` ``` ```) are also absent —
    only the body lines between the delimiters appear.
    """
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


def _inline_code_spans(line: str) -> list[str]:
    """Return the inner text of every inline-code span on ``line``."""
    return [m.group(1) for m in _INLINE_CODE_RE.finditer(line)]


def _make_finding(path: Path, line_no: int, snippet_src: str) -> dict:
    snippet = snippet_src.strip()[:80]
    return {
        'rule_id': RULE_ID,
        'type': FINDING_TYPE,
        'rule': RULE_NAME,
        'file': str(path),
        'line': line_no,
        'severity': 'error',
        'fixable': False,
        'snippet': snippet,
        'description': (
            'Inline-code prose ``status: {code}`` conflates the two-tier TOON error '
            'envelope. On failure ``status`` is ALWAYS the literal ``error``; the '
            'specific failure code lives in the ``error`` field (see '
            'plugin-script-architecture output-contract.md). Rewrite the prose to '
            'name both tiers — e.g. ``status: error`` + ``error: {code}``.'
        ),
    }


# ---------------------------------------------------------------------------
# File-level scanner
# ---------------------------------------------------------------------------


def _scan_file(path: Path) -> list[dict]:
    """Scan a single markdown file and return all findings."""
    try:
        text = path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError) as exc:
        return [
            {
                'rule_id': RULE_ID,
                'type': 'file_read_error',
                'rule': RULE_NAME,
                'file': str(path),
                'line': 0,
                'severity': 'error',
                'fixable': False,
                'snippet': '',
                'description': f'Could not read file: {exc}',
            }
        ]

    lines = text.splitlines()
    fence_map = _build_fence_map(lines)
    findings: list[dict] = []

    for idx, line in enumerate(lines):
        # Fenced code blocks (any info-string) are exempt — a literal payload,
        # not prose.
        if idx in fence_map:
            continue

        for span in _inline_code_spans(line):
            m = _STATUS_KV_RE.match(span)
            if m is None:
                continue
            code = m.group(1)
            if code in _EXEMPT_CODES:
                continue
            findings.append(_make_finding(path, idx + 1, span))

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


def analyze_toon_prose_status_conflation(marketplace_root: Path) -> list[dict]:
    """Scan plan-marshall markdown for status-conflation inline-code prose.

    Walks ``marketplace_root/plan-marshall/{skills,agents,commands}/**/*.md``
    and reports every inline-code ``status: {code}`` occurrence where ``{code}``
    is neither ``error`` nor ``success``.

    Parameters
    ----------
    marketplace_root:
        Path to the marketplace bundles root (the directory that contains the
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

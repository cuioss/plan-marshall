#!/usr/bin/env python3
"""``/tmp`` redirect scanner for the ``tmp-redirect-in-skills`` rule.

This module implements a deterministic regex-based static analyzer that
detects ``>`` / ``>>`` redirect targets pointing at ``/tmp/`` or
``/var/tmp/`` inside fenced ``bash``/``sh`` blocks in skill/agent/command
markdown files.

The canonical violation example (from the source lesson) is:

.. code-block:: text

    python3 .plan/execute-script.py … > /tmp/output.json 2>&1; grep …

Writing to ``/tmp/`` from an LLM-authored Bash command in a skill workflow
violates the project policy that all temporary files must live under
``.plan/temp/`` (covered by ``Write(.plan/**)`` permission — avoids
permission prompts and ensures the file tree is self-consistent).  In
addition, using ``>`` / ``>>`` to redirect into a temporary file is
frequently paired with a compound chain (``;``, ``&&``) to subsequently
read the file — a pattern that is separately flagged by
``_analyze_bash_chain_shapes_in_skills.py`` (the chain-shape rule).

The rule mirrors ``_analyze_shell_substitution_in_skills.py``:

- pure static analysis (no subprocess execution, no imports of target scripts)
- regex-driven extraction from fenced ``bash``/``sh`` blocks only
- stdlib-only dependencies
- no mutation of any file

Detection
---------
Inside every fenced block whose info-string is ``bash`` or ``sh``, the
analyzer looks for redirect operators (``>`` or ``>>``) whose target starts
with ``/tmp/`` or ``/var/tmp/``.  Specifically:

1. **``> /tmp/…`` redirect** — the output-redirect form.
2. **``>> /tmp/…`` redirect** — the append-redirect form.
3. **``/var/tmp/…`` equivalents** — same patterns with ``/var/tmp/``.

Structural exemptions (identical to ``shell-substitution-in-skills``):

1. **Lines outside bash/sh fenced blocks** — only lines inside fenced blocks
   whose info-string is ``bash`` or ``sh`` are scanned.

2. **Comment lines** — lines whose first non-whitespace character is ``#`` are
   skipped.

3. **Inline-code spans** — a redirect pattern inside a backtick span is a
   structural reference, not a runnable command.

Findings have the shape::

    {
        'rule_id': 'tmp-redirect-in-skills',
        'type': 'tmp_redirect_in_skills',
        'rule': 'analyze_tmp_redirect_in_skills',
        'file': '<absolute markdown path>',
        'line': <int, 1-based>,
        'severity': 'error',
        'fixable': False,
        'redirect_type': 'append' | 'overwrite',
        'target_prefix': '/tmp/' | '/var/tmp/',
        'snippet': '<offending text excerpt, max 80 chars>',
        'description': '<short human-readable explanation>',
    }

Public API
----------
- ``analyze_tmp_redirect_in_skills(marketplace_root)``: entry point — scans
  every ``*.md`` under ``marketplace_root/plan-marshall/{skills,agents,commands}/``.
"""

from __future__ import annotations

import re
from pathlib import Path

RULE_ID = 'tmp-redirect-in-skills'
RULE_NAME = 'analyze_tmp_redirect_in_skills'
FINDING_TYPE = 'tmp_redirect_in_skills'

# ---------------------------------------------------------------------------
# Detection patterns
# ---------------------------------------------------------------------------

_FENCE_OPEN_RE = re.compile(r'^\s*```\s*([A-Za-z0-9_+-]*)\s*$')
_FENCE_CLOSE_RE = re.compile(r'^\s*```\s*$')

_BASH_FENCE_INFO_STRINGS = frozenset({'bash', 'sh'})

_INLINE_CODE_RE = re.compile(r'`([^`]+)`')

# Match >> or > followed by optional whitespace then /tmp/ or /var/tmp/.
# The group(1) captures the operator (>> or >), group(2) the target prefix.
_TMP_REDIRECT_RE = re.compile(r'(>>?)\s*(/(?:var/)?tmp/)')


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


def _inline_code_spans(line: str) -> list[tuple[int, int]]:
    """Return (start, end) character offsets of inline-code spans on ``line``."""
    return [(m.start(), m.end()) for m in _INLINE_CODE_RE.finditer(line)]


def _offset_in_inline_code(offset: int, spans: list[tuple[int, int]]) -> bool:
    """Return ``True`` if ``offset`` lies within any of the inline-code spans."""
    return any(start <= offset < end for start, end in spans)


def _is_comment_line(line: str) -> bool:
    """Return ``True`` if the line is a shell comment (first non-ws char is ``#``)."""
    return line.lstrip().startswith('#')


def _make_finding(
    path: Path,
    line_no: int,
    redirect_type: str,
    target_prefix: str,
    line: str,
    offset: int,
) -> dict:
    start = max(0, offset - 30)
    end = min(len(line), offset + 50)
    snippet = line[start:end]
    return {
        'rule_id': RULE_ID,
        'type': FINDING_TYPE,
        'rule': RULE_NAME,
        'file': str(path),
        'line': line_no,
        'severity': 'error',
        'fixable': False,
        'redirect_type': redirect_type,
        'target_prefix': target_prefix,
        'snippet': snippet,
        'description': (
            f'Bash redirect to ``{target_prefix}`` in skill markdown violates the project '
            'policy that all temporary files must live under ``.plan/temp/``. '
            'Replace with a ``Write`` tool call targeting ``.plan/temp/{{plan_id}}-<name>`` '
            'or pass the value through a TOON field instead of writing to a temp file.'
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
                'redirect_type': '',
                'target_prefix': '',
                'snippet': '',
                'description': f'Could not read file: {exc}',
            }
        ]

    lines = text.splitlines()
    fence_map = _build_fence_map(lines)
    findings: list[dict] = []

    for idx, line in enumerate(lines):
        fence_info = fence_map.get(idx)
        if fence_info not in _BASH_FENCE_INFO_STRINGS:
            continue

        if _is_comment_line(line):
            continue

        spans = _inline_code_spans(line)

        for m in _TMP_REDIRECT_RE.finditer(line):
            offset = m.start()
            if _offset_in_inline_code(offset, spans):
                continue
            operator = m.group(1)
            target_prefix = m.group(2)
            redirect_type = 'append' if operator == '>>' else 'overwrite'
            findings.append(
                _make_finding(path, idx + 1, redirect_type, target_prefix, line, offset)
            )

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


def analyze_tmp_redirect_in_skills(marketplace_root: Path) -> list[dict]:
    """Scan plan-marshall skill/agent/command markdown for ``/tmp/`` redirects.

    Walks ``marketplace_root/plan-marshall/{skills,agents,commands}/**/*.md``
    and reports every ``>`` or ``>>`` redirect targeting ``/tmp/`` or
    ``/var/tmp/`` inside a fenced ``bash`` or ``sh`` block.

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

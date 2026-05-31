#!/usr/bin/env python3
"""Bash chain-shape scanner for the ``bash-chain-shapes-in-skills`` rule.

This module implements a deterministic regex-based static analyzer that
detects compound Bash command sequences (``&&``, ``;``, trailing ``&``, and
inline pipe-chains with embedded ``&&``/``;``) inside fenced ``bash``/``sh``
blocks in skill/agent/command markdown files.  Such patterns violate the
``dev-agent-behavior-rules`` "Bash: one command per call" hard rule because
the host platform's permission UI flags compound commands, and compound shapes
obscure the env-var / subprocess contract that each individual command owns.

The rule mirrors ``_analyze_shell_substitution_in_skills.py``:

- pure static analysis (no subprocess execution, no imports of target scripts)
- regex-driven extraction from fenced ``bash``/``sh`` blocks only
- stdlib-only dependencies
- no mutation of any file

Detection
---------
Inside every fenced block whose info-string is ``bash`` or ``sh``:

1. **``&&`` chain** — a non-comment source line contains the literal two-char
   sequence ``&&``.  This catches ``cmd1 && cmd2`` and the multi-arg
   env-var-assignment form ``MY_VAR=val cmd && …``.

2. **``;`` chain** — a non-comment source line contains a bare ``;`` operator
   that separates two commands (conservatively: any ``;`` on a non-comment line
   inside a bash/sh fence is a candidate finding).

3. **trailing ``&``** — a non-comment source line ends with a bare ``&``
   (background dispatch).  The sequence ``\\&`` (backslash-escaped) is
   explicitly exempted.

Structural exemptions (identical to ``shell-substitution-in-skills``):

1. **Lines outside bash/sh fenced blocks** — the analyzer only inspects lines
   inside fenced blocks whose info-string is ``bash`` or ``sh``.  Prose,
   Python fences, JSON fences, and so on are not scanned.

2. **Verbatim-source fenced blocks** — fenced blocks whose info-string is
   ``markdown`` or ``text`` hold verbatim source examples that subagents do
   not interpret as instructions.  Since these are not ``bash``/``sh``, they
   are naturally excluded by rule 1.

3. **Comment lines** — lines whose first non-whitespace character is ``#`` are
   treated as comments and skipped (common in shell scripts to illustrate
   intent without running code).

Findings have the shape::

    {
        'rule_id': 'bash-chain-shapes-in-skills',
        'type': 'bash_chain_shapes_in_skills',
        'rule': 'analyze_bash_chain_shapes_in_skills',
        'file': '<absolute markdown path>',
        'line': <int, 1-based>,
        'severity': 'error',
        'fixable': False,
        'chain_type': 'and_and' | 'semicolon' | 'background',
        'snippet': '<offending text excerpt, max 80 chars>',
        'description': '<short human-readable explanation>',
    }

Public API
----------
- ``analyze_bash_chain_shapes_in_skills(marketplace_root)``: entry point —
  scans every ``*.md`` under ``marketplace_root/plan-marshall/skills/``,
  ``marketplace_root/plan-marshall/agents/``, and
  ``marketplace_root/plan-marshall/commands/``.
"""

from __future__ import annotations

import re
from pathlib import Path

RULE_ID = 'bash-chain-shapes-in-skills'
RULE_NAME = 'analyze_bash_chain_shapes_in_skills'
FINDING_TYPE = 'bash_chain_shapes_in_skills'

# ---------------------------------------------------------------------------
# Detection patterns
# ---------------------------------------------------------------------------

# Fenced-block boundaries.
_FENCE_OPEN_RE = re.compile(r'^\s*```\s*([A-Za-z0-9_+-]*)\s*$')
_FENCE_CLOSE_RE = re.compile(r'^\s*```\s*$')

# Info-strings for which detection fires (only inside bash/sh fences).
_BASH_FENCE_INFO_STRINGS = frozenset({'bash', 'sh'})

# Compound-command detection.
_AND_AND_RE = re.compile(r'&&')
_SEMICOLON_RE = re.compile(r';')
# Trailing & but NOT \& (backslash-escaped).  Matches a non-backslash char
# followed by & at end-of-content (ignoring trailing whitespace).
_TRAILING_BG_RE = re.compile(r'(?<!\\)&\s*$')


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_fence_map(lines: list[str]) -> dict[int, str]:
    """Map 0-based line indices inside any fenced block to the info-string.

    Lines that are NOT inside a fence are absent from the map.  The fence
    delimiter lines themselves are also absent — only the body lines between
    the delimiters appear.
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


def _is_comment_line(line: str) -> bool:
    """Return ``True`` if the line is a shell comment (first non-ws char is ``#``)."""
    return line.lstrip().startswith('#')


def _make_finding(path: Path, line_no: int, chain_type: str, line: str, offset: int) -> dict:
    start = max(0, offset - 30)
    end = min(len(line), offset + 50)
    snippet = line[start:end]
    descriptions = {
        'and_and': (
            'Compound ``&&`` chain in bash fence violates the dev-agent-behavior-rules '
            '"Bash: one command per call" hard rule. Split into separate Bash tool calls.'
        ),
        'semicolon': (
            'Compound ``;`` chain in bash fence violates the dev-agent-behavior-rules '
            '"Bash: one command per call" hard rule. Split into separate Bash tool calls.'
        ),
        'background': (
            'Trailing ``&`` background dispatch in bash fence violates the dev-agent-behavior-rules '
            '"Bash: one command per call" hard rule. Use run_in_background parameter instead.'
        ),
    }
    return {
        'rule_id': RULE_ID,
        'type': FINDING_TYPE,
        'rule': RULE_NAME,
        'file': str(path),
        'line': line_no,
        'severity': 'error',
        'fixable': False,
        'chain_type': chain_type,
        'snippet': snippet,
        'description': descriptions.get(chain_type, 'Forbidden bash chain shape detected.'),
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
                'chain_type': '',
                'snippet': '',
                'description': f'Could not read file: {exc}',
            }
        ]

    lines = text.splitlines()
    fence_map = _build_fence_map(lines)
    findings: list[dict] = []

    for idx, line in enumerate(lines):
        # Only scan inside bash/sh fenced blocks.
        fence_info = fence_map.get(idx)
        if fence_info not in _BASH_FENCE_INFO_STRINGS:
            continue

        # Skip comment lines.
        if _is_comment_line(line):
            continue

        # Check for && chains.
        for m in _AND_AND_RE.finditer(line):
            findings.append(_make_finding(path, idx + 1, 'and_and', line, m.start()))

        # Check for ; chains.
        for m in _SEMICOLON_RE.finditer(line):
            findings.append(_make_finding(path, idx + 1, 'semicolon', line, m.start()))

        # Check for trailing & (background dispatch).
        m_bg = _TRAILING_BG_RE.search(line)
        if m_bg:
            findings.append(_make_finding(path, idx + 1, 'background', line, m_bg.start()))

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


def analyze_bash_chain_shapes_in_skills(marketplace_root: Path) -> list[dict]:
    """Scan plan-marshall skill/agent/command markdown for forbidden bash chain shapes.

    Walks ``marketplace_root/plan-marshall/{skills,agents,commands}/**/*.md``
    and reports every ``&&``, ``;``, or trailing ``&`` inside a fenced
    ``bash`` or ``sh`` block on a non-``#``-comment line.

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

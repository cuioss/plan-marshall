#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shell-active token scanner for the ``shell-active-tokens`` rule.

This module implements a deterministic regex-based static analyzer that
detects shell-active constructs embedded in skill markdown prose.  Unlike
executable ``bash`` blocks (where shell tokens are expected), these constructs
appear inside flag values, template strings, or narrative text and would cause
unintended shell expansion if copied into a terminal session.

Four token classes are checked
-------------------------------
1. **backtick-in-flag** — Backtick characters (````` ` `````) found inside
   ``--detail``, ``--message``, or ``--title`` flag values (inline or in a
   bash fenced block).  Backticks inside flag values are shell-interpreted
   by the invoking shell and may break argument passing.

2. **brace-expansion** — Bash brace-expansion syntax (``{a..b}``,
   ``{x,y,z}``) detected inside fenced ``bash``/``sh`` blocks AND in
   inline-code path-pattern regions (i.e. inline-code spans that look like
   filesystem glob patterns).  Outside those contexts brace expansion is
   expected in skill prose and is not flagged.

3. **glob-wildcard** — Unquoted glob wildcards (``*`` or ``?``) found
   *outside* fenced code blocks.  Inside fenced blocks wildcards are part of
   the documented command and are intentional; outside them they represent
   unintended shell glob references.

4. **dollar-token** — Unescaped ``$VAR`` / ``$(...)`` references in template
   strings (inline code spans that contain ``$`` followed by a letter or
   opening parenthesis).

Pattern alignment
-----------------
The analyzer mirrors ``_analyze_verb_chains.py`` and
``_analyze_argument_naming.py``:

- pure static analysis (no subprocess execution, no imports of target scripts)
- regex-driven extraction from markdown source
- stdlib-only dependencies
- no mutation of any file

Findings have the shape::

    {
        'rule_id': 'shell-active-tokens',
        'file': '<absolute markdown path>',
        'line': <int, 1-based>,
        'token_class': 'backtick-in-flag' | 'brace-expansion'
                       | 'glob-wildcard' | 'dollar-token',
        'snippet': '<offending text excerpt>',
    }

Public API
----------
- ``analyze_shell_active_tokens(skill_dir)``: entry point — scans one skill
  directory's ``standards/*.md`` files.
"""

from __future__ import annotations

import re
from pathlib import Path

RULE_ID = 'shell-active-tokens'

# ---------------------------------------------------------------------------
# Fenced-block helpers
# ---------------------------------------------------------------------------

_BASH_FENCE_OPEN = re.compile(r'^\s*```\s*(bash|sh)\s*$')
_FENCE_CLOSE = re.compile(r'^\s*```\s*$')

# ---------------------------------------------------------------------------
# Token-class patterns
# ---------------------------------------------------------------------------

# 1. Backtick inside --detail / --message / --title flag values.
# Matches: --detail "...`..." or --detail '...`...' or --detail `...` (any
# of the three quoting styles that keep the value in one token).  We capture
# a short snippet around the backtick.
_FLAG_BACKTICK_RE = re.compile(
    r'--(?:detail|message|title)\s+'
    r'(?:"[^"]*`[^"]*"|\'[^\']*`[^\']*\'|`[^`]*`)',
    re.IGNORECASE,
)

# 2. Bash brace expansion inside a fenced bash/sh block or inline-code path.
# Sequence like {a..b} or {x,y} or {x,y,z}.
_BRACE_EXPANSION_RE = re.compile(r'\{[^}]*\.\.[^}]*\}|\{[^}]*,[^}]*\}')

# Inline-code span detection (matches `...` that looks like a path pattern).
_INLINE_CODE_RE = re.compile(r'`([^`]+)`')
_PATH_PATTERN_RE = re.compile(r'[/\\*?{}]')  # looks like a path/glob

# 3. Glob wildcard (* or ?) outside fenced blocks, outside inline-code spans.
# We strip inline code spans first before checking.
_GLOB_WILDCARD_RE = re.compile(r'(?<![`\\])[*?]')

# 4. Unescaped $VAR or $(...) in inline-code spans.
_DOLLAR_TOKEN_RE = re.compile(r'\$(?:[A-Za-z_][A-Za-z0-9_]*|\()')


# ---------------------------------------------------------------------------
# Fence-tracking helpers
# ---------------------------------------------------------------------------


def _build_fence_map(lines: list[str]) -> set[int]:
    """Return a set of 0-based line indices that are inside a bash/sh fence."""
    inside: set[int] = set()
    in_fence = False
    for idx, line in enumerate(lines):
        if not in_fence:
            if _BASH_FENCE_OPEN.match(line):
                in_fence = True
        else:
            if _FENCE_CLOSE.match(line):
                in_fence = False
            else:
                inside.add(idx)
    return inside


def _build_any_fence_map(lines: list[str]) -> set[int]:
    """Return a set of 0-based line indices inside ANY fenced block."""
    inside: set[int] = set()
    in_fence = False
    fence_open = re.compile(r'^\s*```')
    fence_close = re.compile(r'^\s*```\s*$')
    for idx, line in enumerate(lines):
        if not in_fence:
            if fence_open.match(line):
                in_fence = True
        else:
            if fence_close.match(line):
                in_fence = False
            else:
                inside.add(idx)
    return inside


# ---------------------------------------------------------------------------
# Per-line checkers
# ---------------------------------------------------------------------------


def _check_backtick_in_flag(line: str) -> list[str]:
    """Return snippets of flag+backtick violations in ``line``."""
    return [m.group(0) for m in _FLAG_BACKTICK_RE.finditer(line)]


def _check_brace_expansion(line: str) -> list[str]:
    """Return brace-expansion snippets found in ``line``.

    Called only for lines that are inside a bash/sh fenced block OR
    contain an inline-code span that looks like a path pattern.
    """
    snippets: list[str] = []
    # Check inline-code spans for brace expansion
    for ic_match in _INLINE_CODE_RE.finditer(line):
        span = ic_match.group(1)
        if _PATH_PATTERN_RE.search(span):
            for be in _BRACE_EXPANSION_RE.finditer(span):
                snippets.append(be.group(0))
    return snippets


def _check_brace_expansion_in_bash(line: str) -> list[str]:
    """Return brace-expansion snippets inside a bash-fenced line."""
    return [m.group(0) for m in _BRACE_EXPANSION_RE.finditer(line)]


def _strip_inline_code(line: str) -> str:
    """Replace inline-code spans with spaces of equal length."""
    result = list(line)
    for m in _INLINE_CODE_RE.finditer(line):
        for i in range(m.start(), m.end()):
            result[i] = ' '
    return ''.join(result)


def _check_glob_wildcard(line: str) -> list[str]:
    """Return wildcard snippets found in ``line`` outside inline code."""
    stripped = _strip_inline_code(line)
    return [stripped[m.start():m.start() + 1] for m in _GLOB_WILDCARD_RE.finditer(stripped)]


def _check_dollar_token(line: str) -> list[str]:
    """Return dollar-token snippets found in inline-code spans of ``line``."""
    snippets: list[str] = []
    for ic_match in _INLINE_CODE_RE.finditer(line):
        span = ic_match.group(1)
        for dt in _DOLLAR_TOKEN_RE.finditer(span):
            snippets.append(dt.group(0) + '...')
    return snippets


# ---------------------------------------------------------------------------
# File-level scanner
# ---------------------------------------------------------------------------


def _scan_file(path: Path) -> list[dict]:
    """Scan a single markdown file and return all findings."""
    try:
        text = path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        return []

    lines = text.splitlines()
    bash_fence_lines = _build_fence_map(lines)
    any_fence_lines = _build_any_fence_map(lines)

    findings: list[dict] = []

    def _add(line_idx: int, token_class: str, snippet: str) -> None:
        findings.append(
            {
                'rule_id': RULE_ID,
                'file': str(path),
                'line': line_idx + 1,  # 1-based
                'token_class': token_class,
                'snippet': snippet,
            }
        )

    for idx, line in enumerate(lines):
        in_bash = idx in bash_fence_lines
        in_any_fence = idx in any_fence_lines

        # --- 1. backtick-in-flag (checked everywhere, fenced or not) ---
        for snippet in _check_backtick_in_flag(line):
            _add(idx, 'backtick-in-flag', snippet[:80])

        # --- 2. brace-expansion ---
        if in_bash:
            # Inside bash/sh fenced block: check the raw line
            for snippet in _check_brace_expansion_in_bash(line):
                _add(idx, 'brace-expansion', snippet)
        else:
            # Outside bash blocks: only check inline-code path patterns
            for snippet in _check_brace_expansion(line):
                _add(idx, 'brace-expansion', snippet)

        # --- 3. glob-wildcard (only outside ALL fenced blocks) ---
        if not in_any_fence:
            for snippet in _check_glob_wildcard(line):
                _add(idx, 'glob-wildcard', snippet)

        # --- 4. dollar-token in inline-code spans ---
        for snippet in _check_dollar_token(line):
            _add(idx, 'dollar-token', snippet)

    return findings


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def _standards_targets(skill_dir: Path) -> list[Path]:
    """Return markdown files in ``standards/`` subject to this rule."""
    targets: list[Path] = []
    standards_dir = skill_dir / 'standards'
    if standards_dir.is_dir():
        for md in sorted(standards_dir.glob('*.md')):
            if md.is_file():
                targets.append(md)
    return targets


def analyze_shell_active_tokens(skill_dir: Path) -> list[dict]:
    """Scan ``skill_dir/standards/*.md`` for shell-active token constructs.

    Returns a list of finding dicts.  The list is empty for a clean skill
    directory or one with no ``standards/*.md`` files.

    Parameters
    ----------
    skill_dir:
        Path to the skill directory (the directory that contains
        ``SKILL.md``, ``standards/``, etc.).
    """
    findings: list[dict] = []
    for md_path in _standards_targets(skill_dir):
        findings.extend(_scan_file(md_path))
    return findings

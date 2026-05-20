#!/usr/bin/env python3
"""Plan-path-in-scripts analyzer for the ``plan-path-in-scripts`` rule.

This module detects occurrences of the literal string ``.plan/plans/`` inside
Python files in the marketplace bundle scripts tree.  The canonical plan
directory is ``.plan/local/plans/`` (resolved via
``tools-file-ops:file_ops.get_plan_dir``); any production script that joins
``plans/{plan_id}`` against ``cwd/.plan`` directly produces a "ghost"
``.plan/plans/`` tree at the repo root on every invocation.

Convention documented here
--------------------------
The canonical plan-directory helper is ``get_plan_dir(plan_id)`` from
``tools-file-ops:file_ops`` which resolves to ``<repo>/.plan/local/plans/{plan_id}``.
Production scripts must use the helper rather than constructing the path by
hand.  Code-literal occurrences of ``.plan/plans/`` in marketplace
``scripts/*.py`` files are runtime hazards.

Docstring-only occurrences (``.plan/plans/`` inside triple-quoted blocks)
are intentionally ignored.  Many legacy docstring examples still cite the
shorter shorthand; sweeping those is out of scope for this rule.  The
analyzer fires only on code-literal hits.

Whitelist categories (path-component-anchored)
-----------------------------------------------
Each whitelist entry is matched by checking whether ALL its required path
components appear among the components of the candidate path.

1. **lint-analyzer**: This file itself contains the marker literal as the
   detection target and must not flag itself.
   - ``_analyze_plan_path_in_scripts.py``

Findings have the shape::

    {
        'rule_id': 'plan-path-in-scripts',
        'file': '<absolute file path>',
        'line': <int, 1-based>,
        'category': 'production_script' | 'test_assertion',
        'snippet': '<line excerpt>',
    }

Public API
----------
- ``analyze_plan_path_in_scripts(marketplace_root)``: entry point — scans
  ``marketplace/bundles/**/scripts/**/*.py`` and emits findings for
  non-whitelisted code-literal occurrences.
- ``is_whitelisted(file_path)``: returns True when ``file_path`` matches a
  whitelist entry.
"""

from __future__ import annotations

from pathlib import Path

RULE_ID = 'plan-path-in-scripts'

# The literal string we scan for.  The canonical path is .plan/local/plans/;
# this marker catches the shorter (drifted) form.
_MARKER = '.plan/plans/'

# ---------------------------------------------------------------------------
# Whitelist — path-component-anchored
# ---------------------------------------------------------------------------
# Each entry is a frozenset of path component names that must ALL be present
# in the file's parts.  Component-presence test, not raw substring of the
# full path string.

_WHITELIST_COMPONENT_SETS: list[frozenset[str]] = [
    # lint-analyzer: this file itself (self-referential — the marker is the
    # detection target).
    frozenset({'_analyze_plan_path_in_scripts.py'}),
]


def is_whitelisted(file_path: Path) -> bool:
    """Return True when ``file_path`` matches any whitelist entry.

    Each whitelist entry is a frozenset of path-component strings that must
    ALL appear as exact matches among the components of ``file_path``.
    """
    parts_set = set(file_path.parts)
    parts_set.add(file_path.name)
    for required_components in _WHITELIST_COMPONENT_SETS:
        if required_components.issubset(parts_set):
            return True
    return False


def _classify(file_path: Path) -> str:
    """Classify a file as ``production_script`` or ``test_assertion``."""
    for part in file_path.parts:
        if part in ('test', 'tests'):
            return 'test_assertion'
    name = file_path.name
    if name.startswith('test_') or name.endswith('_test.py'):
        return 'test_assertion'
    return 'production_script'


def _compute_docstring_lines(text: str) -> set[int]:
    """Return the set of 1-based line numbers that lie inside a docstring block.

    A "docstring block" is any region delimited by triple-quoted string
    literals (``\"\"\"`` or ``'''``).  The analyzer is line-based, not AST-based,
    so this is a structural approximation: any text between matching triple
    quotes is treated as docstring.  Mismatched / unclosed triple quotes are
    handled defensively by stopping at end-of-file.
    """
    inside_lines: set[int] = set()
    in_block = False
    delimiter = ''
    for line_idx, line in enumerate(text.splitlines(), start=1):
        # Walk character-by-character to handle multiple delimiters on the
        # same line (e.g. opening and closing triple quote on one line).
        i = 0
        line_was_in_block = in_block
        line_toggled = False
        while i < len(line):
            if not in_block:
                # Look for an opening triple quote.
                if line.startswith('"""', i):
                    in_block = True
                    delimiter = '"""'
                    i += 3
                    line_toggled = True
                    continue
                if line.startswith("'''", i):
                    in_block = True
                    delimiter = "'''"
                    i += 3
                    line_toggled = True
                    continue
            else:
                # Look for the matching closing triple quote.
                if line.startswith(delimiter, i):
                    in_block = False
                    i += 3
                    line_toggled = True
                    continue
            i += 1
        # A line is "inside a docstring" if either:
        #   - it was inside a block when the line started and the line is
        #     fully consumed inside the block, OR
        #   - any toggle happened on the line (open/close), because the
        #     marker may sit between the delimiters on that same line.
        # Use a conservative rule: mark the line as docstring if the block
        # was active either at line start OR at line end OR a toggle happened
        # on the line.
        if line_was_in_block or in_block or line_toggled:
            inside_lines.add(line_idx)
    return inside_lines


def _scan_file(file_path: Path) -> list[dict]:
    """Scan one Python file for ``_MARKER`` occurrences.

    Lines whose match falls entirely inside a triple-quoted docstring block
    are skipped — only code-literal hits produce findings.
    """
    try:
        text = file_path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        return []

    findings: list[dict] = []
    category = _classify(file_path)
    docstring_lines = _compute_docstring_lines(text)

    for line_idx, line in enumerate(text.splitlines(), start=1):
        if _MARKER not in line:
            continue
        if line_idx in docstring_lines:
            continue
        findings.append(
            {
                'rule_id': RULE_ID,
                'file': str(file_path),
                'line': line_idx,
                'category': category,
                'snippet': line.strip()[:120],
            }
        )
    return findings


def analyze_plan_path_in_scripts(marketplace_root: Path) -> list[dict]:
    """Scan marketplace bundle scripts for non-whitelisted plan-path references.

    Scans:
    - ``<marketplace_root>/bundles/**/skills/*/scripts/**/*.py``

    Test files are scanned but their findings are categorised as
    ``test_assertion`` rather than ``production_script`` so callers can apply
    different triage.

    Docstring-only occurrences are skipped — only code-literal hits produce
    findings.

    Parameters
    ----------
    marketplace_root:
        Path to the ``marketplace/`` directory.

    Returns
    -------
    list[dict]
        Findings for non-whitelisted code-literal occurrences of
        ``.plan/plans/``.
    """
    findings: list[dict] = []

    bundles_root = marketplace_root / 'bundles'
    if not bundles_root.is_dir():
        return []

    for py_file in sorted(bundles_root.rglob('*.py')):
        if not py_file.is_file():
            continue
        if is_whitelisted(py_file):
            continue
        findings.extend(_scan_file(py_file))

    return findings

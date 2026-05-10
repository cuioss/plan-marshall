#!/usr/bin/env python3
"""Executor-path-in-production analyzer for the ``executor-path-in-production`` rule.

This module detects occurrences of the literal string ``.plan/execute-script.py``
inside Python files in the marketplace bundle scripts tree and (optionally) the
test tree.  Legitimate categories are whitelisted by path-component anchoring
(not substring matching).

Convention documented here
--------------------------
Interactive Claude / manage-* invocations use ``python3 .plan/execute-script.py``
notation; production Python scripts, build pipelines, and pre-merge checks use
direct script paths (e.g. ``_analyze_verb_chains.py``, imported as a module).
When a production script embeds the executor path, it creates a runtime coupling
to the ``.plan/`` directory structure, which is a deployment-time assumption that
production code must not carry.

Whitelist categories (path-component-anchored)
-----------------------------------------------
Each whitelist entry is matched by checking whether ALL its required path
components appear among the components of the candidate path (in order).

1. **executor-generator**: The script *generates* the executor; it must reference
   the path to write it.
   - ``tools-script-executor/scripts/generate_executor.py``
   - ``tools-script-executor/templates/execute-script.py.template``

2. **lint-analyzer**: Analyzers that *inspect markdown* for executor notation.
   - ``_analyze_verb_chains.py``
   - ``_analyze_argument_naming.py``
   - ``_analyze_markdown.py``
   - ``_analyze_executor_path_in_production.py`` (this file, self-referential)

3. **permission-tooling**: Tools that construct executor-style permission strings.
   - ``tools-permission-fix/scripts/permission_fix.py``

Findings have the shape::

    {
        'rule_id': 'executor-path-in-production',
        'file': '<absolute file path>',
        'line': <int, 1-based>,
        'category': 'production_script' | 'test_assertion',
        'snippet': '<line excerpt>',
    }

Public API
----------
- ``analyze_executor_path_in_production(marketplace_root)``: entry point —
  scans ``marketplace/bundles/**/scripts/**/*.py`` and emits findings for
  non-whitelisted occurrences.
- ``is_whitelisted(file_path)``: returns True when ``file_path`` matches a
  whitelist entry.
"""

from __future__ import annotations

from pathlib import Path

RULE_ID = 'executor-path-in-production'

# The literal string we scan for.
_EXECUTOR_MARKER = '.plan/execute-script.py'

# ---------------------------------------------------------------------------
# Whitelist — path-component-anchored
# ---------------------------------------------------------------------------
# Each entry is a tuple of path component fragments that must ALL appear as
# substrings of the corresponding path components (in order, from the tail).
# The check uses a component-presence test, not a raw substring of the full
# path string, so false positives from similarly named directories are avoided.
#
# Format: frozenset of frozensets; each inner frozenset contains path
# component names that must ALL be present in the file's parts.

_WHITELIST_COMPONENT_SETS: list[frozenset[str]] = [
    # executor-generator: tools-script-executor generator script
    frozenset({'tools-script-executor', 'generate_executor.py'}),
    # executor-generator: the template that becomes the executor
    frozenset({'tools-script-executor', 'execute-script.py.template'}),
    # lint-analyzer: verb-chain scanner
    frozenset({'_analyze_verb_chains.py'}),
    # lint-analyzer: argument naming scanner
    frozenset({'_analyze_argument_naming.py'}),
    # lint-analyzer: markdown analyzer
    frozenset({'_analyze_markdown.py'}),
    # lint-analyzer: this file itself (self-referential)
    frozenset({'_analyze_executor_path_in_production.py'}),
    # permission-tooling: permission-fix script
    frozenset({'tools-permission-fix', 'permission_fix.py'}),
]


def is_whitelisted(file_path: Path) -> bool:
    """Return True when ``file_path`` matches any whitelist entry.

    Each whitelist entry is a frozenset of path-component strings that must
    ALL appear as exact matches among the components of ``file_path``.
    """
    parts_set = set(file_path.parts)
    # Also include the full filename as one of the searchable components.
    parts_set.add(file_path.name)
    for required_components in _WHITELIST_COMPONENT_SETS:
        if required_components.issubset(parts_set):
            return True
    return False


def _classify(file_path: Path) -> str:
    """Classify a file as ``production_script`` or ``test_assertion``."""
    path_str = str(file_path)
    for part in file_path.parts:
        if part in ('test', 'tests'):
            return 'test_assertion'
    name = file_path.name
    if name.startswith('test_') or name.endswith('_test.py'):
        return 'test_assertion'
    return 'production_script'


def _scan_file(file_path: Path) -> list[dict]:
    """Scan one Python file for ``_EXECUTOR_MARKER`` occurrences."""
    try:
        text = file_path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        return []

    findings: list[dict] = []
    category = _classify(file_path)

    for line_idx, line in enumerate(text.splitlines()):
        if _EXECUTOR_MARKER in line:
            findings.append(
                {
                    'rule_id': RULE_ID,
                    'file': str(file_path),
                    'line': line_idx + 1,
                    'category': category,
                    'snippet': line.strip()[:120],
                }
            )
    return findings


def analyze_executor_path_in_production(marketplace_root: Path) -> list[dict]:
    """Scan marketplace bundle scripts for non-whitelisted executor-path references.

    Scans:
    - ``<marketplace_root>/bundles/**/skills/*/scripts/**/*.py``

    The scan does not cover test files by default (they often legitimately
    assert command-line argument shapes), but when the rule fires inside a test
    file the finding is categorised as ``test_assertion`` rather than
    ``production_script`` so callers can apply different triage.

    Parameters
    ----------
    marketplace_root:
        Path to the ``marketplace/`` directory.

    Returns
    -------
    list[dict]
        Findings for non-whitelisted occurrences of ``.plan/execute-script.py``.
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

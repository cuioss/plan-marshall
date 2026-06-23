#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Phase-2-refine contract analyzer for the ``refine-contract-violation`` rule.

This module implements a deterministic regex-based static analyzer that
detects ``Edit`` / ``Write`` tool references inside ``phase-2-refine``
workflow files whose path argument is not prefixed with ``.plan/local/``.

The analyzer enforces the phase-2-refine § Enforcement → Allowed write paths
contract: refine produces refined-request artifacts only and MUST NOT edit
production files in ``marketplace/``, source trees, build configs, etc.
The runtime complement to this static check is the orchestrator's
post-dispatch ``git -C . status --porcelain`` assertion documented in
``plan-marshall:plan-marshall:planning.md`` § "2-Refine Phase" →
"Post-dispatch contract assertion".

Scope
-----
The analyzer walks files under ``phase-2-refine/`` (the skill's directory)
and scans for tool-invocation references on each line. Only ``Edit`` and
``Write`` tool references are flagged; ``Read`` is allowed everywhere
because refine MUST read broadly to reason about the request, and read
operations are not contract violations.

Allowed path prefixes
---------------------
A referenced path is considered allowed when it begins with one of:

- ``.plan/local/``
- ``{WORKTREE}/.plan/local/``
- ``{worktree_path}/.plan/local/``

The second and third prefixes accommodate workflow prose that substitutes
the worktree absolute path placeholder before the plan-scoped sub-path.
Every other path triggers a ``refine-contract-violation`` finding.

Pattern alignment
-----------------
The analyzer mirrors ``_analyze_shell_active_tokens.py``:

- pure static analysis (no subprocess execution, no imports of target
  scripts)
- regex-driven extraction from markdown source
- stdlib-only dependencies
- no mutation of any file

Findings have the shape::

    {
        'rule_id': 'refine-contract-violation',
        'file': '<absolute markdown path>',
        'line': <int, 1-based>,
        'tool': 'Edit' | 'Write',
        'path': '<offending path argument>',
        'suggested_fix': '<remediation hint>',
    }

Public API
----------
- ``analyze_phase2_refine_contract(paths, rules_filter=None)``: entry point
  — scans ``phase-2-refine/`` workflow files reachable from ``paths``.
"""

from __future__ import annotations

import re
from pathlib import Path

RULE_ID = 'refine-contract-violation'

_ALLOWED_PREFIXES = (
    '.plan/local/',
    '{WORKTREE}/.plan/local/',
    '{worktree_path}/.plan/local/',
)

# Match ``Edit(file_path="…")``, ``Write(file_path="…")``, or bare
# ``Edit "..."`` / ``Write "..."`` invocations. The regex captures the tool
# name and the first quoted path argument; alternative single-quoted forms
# are normalized into the same capture.
_TOOL_CALL_RE = re.compile(
    r'\b(Edit|Write)\s*'
    r'(?:\(\s*(?:file_path\s*=\s*)?["\']([^"\']+)["\']'
    r'|["\']([^"\']+)["\'])',
)

_PHASE_DIR_NAME = 'phase-2-refine'


def _path_is_allowed(path: str) -> bool:
    """Return True when ``path`` starts with one of the allowed prefixes."""
    stripped = path.strip()
    if not stripped:
        # Empty / placeholder-only paths are not contract violations.
        return True
    if '..' in stripped:
        # Reject path traversal sequences (e.g. '.plan/local/../../../etc/passwd')
        # before the prefix check — the literal prefix match would otherwise
        # accept any traversal that started inside an allowed prefix.
        return False
    for prefix in _ALLOWED_PREFIXES:
        if stripped.startswith(prefix):
            return True
    return False


def _suggested_fix(path: str) -> str:
    """Return a remediation hint for a non-allowed path."""
    return (
        f'route the operation through `manage-plan-documents` or restrict '
        f'the path to `.plan/local/plans/{{plan_id}}/**` '
        f'(current: {path!r})'
    )


def _scan_file(path: Path) -> list[dict]:
    """Scan a single markdown file and return all findings."""
    try:
        text = path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        return []

    findings: list[dict] = []
    for idx, line in enumerate(text.splitlines()):
        for match in _TOOL_CALL_RE.finditer(line):
            tool = match.group(1)
            referenced_path = match.group(2) or match.group(3) or ''
            if _path_is_allowed(referenced_path):
                continue
            findings.append(
                {
                    'rule_id': RULE_ID,
                    'file': str(path),
                    'line': idx + 1,
                    'tool': tool,
                    'path': referenced_path,
                    'suggested_fix': _suggested_fix(referenced_path),
                }
            )
    return findings


def _is_refine_workflow_file(path: Path) -> bool:
    """Return True for markdown files under any ``phase-2-refine/`` directory."""
    if path.suffix != '.md':
        return False
    return _PHASE_DIR_NAME in path.parts


def _resolve_targets(paths: list[Path]) -> list[Path]:
    """Expand ``paths`` into the concrete markdown files this rule scans.

    ``paths`` entries may be either individual ``.md`` files (passed through
    when they match the refine-workflow predicate) or directories (recursed
    to find all ``phase-2-refine/**/*.md`` files inside them).
    """
    targets: list[Path] = []
    seen: set[Path] = set()
    for entry in paths:
        if entry.is_file():
            if _is_refine_workflow_file(entry) and entry not in seen:
                targets.append(entry)
                seen.add(entry)
        elif entry.is_dir():
            for md in sorted(entry.rglob('*.md')):
                if _is_refine_workflow_file(md) and md not in seen:
                    targets.append(md)
                    seen.add(md)
    return targets


def analyze_phase2_refine_contract(
    paths: list[Path],
    *,
    rules_filter: set[str] | None = None,
) -> list[dict]:
    """Scan ``paths`` for phase-2-refine contract violations.

    Parameters
    ----------
    paths:
        List of files and / or directories to scan. The analyzer self-filters
        to markdown files whose path contains a ``phase-2-refine`` segment,
        so callers may safely pass broader sets (e.g. an entire bundle's
        skills directory).
    rules_filter:
        Optional opt-in rule allow-list. When supplied and the analyzer's
        ``RULE_ID`` is not in the set, the analyzer returns no findings —
        the caller has deselected this rule. When ``None`` (the default),
        the rule is unconditionally active.

    Returns
    -------
    list[dict]
        A list of finding dicts (see module docstring for the shape). Empty
        when no violations are found OR when the rule is filtered out via
        ``rules_filter``.
    """
    if rules_filter is not None and RULE_ID not in rules_filter:
        return []

    findings: list[dict] = []
    for md_path in _resolve_targets(paths):
        findings.extend(_scan_file(md_path))
    return findings

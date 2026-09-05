#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Planning-phase contract analyzer for the three ``*-contract-violation`` rules.

This module implements a deterministic regex-based static analyzer that
detects ``Edit`` / ``Write`` tool references inside the three *planning-phase*
workflow directories (``phase-2-refine``, ``phase-3-outline``,
``phase-4-plan``) whose path argument is not prefixed with ``.plan/local/``.
One rule id is emitted per matched phase directory:

- ``phase-2-refine``  → ``refine-contract-violation``
- ``phase-3-outline`` → ``outline-contract-violation``
- ``phase-4-plan``    → ``plan-contract-violation``

The analyzer enforces the planning-phase § Enforcement → Allowed write paths
contract: the outline / plan / refine phases produce plan-scoped artifacts
only and MUST NOT edit production files in ``marketplace/``, source trees,
build configs, etc. All three phases run on the main checkout (the worktree
is not materialized until phase-5 Step 2.5), so a stray ``Edit`` / ``Write``
against a non-plan path is a main-checkout mutation. The runtime complement
to this static check is the orchestrator's post-dispatch
``git -C . status --porcelain`` assertion — for phase-2-refine in
``plan-marshall:plan-marshall:planning.md`` § "2-Refine Phase" →
"Post-dispatch contract assertion", and for phase-3-outline / phase-4-plan in
``plan-marshall:plan-marshall:planning-outline.md`` Steps 2c / 4b.

Import-site stability
--------------------
The module file name and the public function name stay
``analyze_phase2_refine_contract`` so the single call site
(``_doctor_analysis.py::analyze_component``) and the
``_rule_registry.py::_DESCRIPTOR_MODULES`` entry are unchanged; the registry
auto-collects the ``RULE_DESCRIPTORS`` list below.

Scope
-----
The analyzer walks files under any of the three planning-phase directories
and scans for tool-invocation references on each line. Only ``Edit`` and
``Write`` tool references are flagged; ``Read`` is allowed everywhere
because the planning phases MUST read broadly to reason about the request,
and read operations are not contract violations.

Allowed path prefixes
---------------------
A referenced path is considered allowed when it begins with one of:

- ``.plan/local/``
- ``{WORKTREE}/.plan/local/``
- ``{worktree_path}/.plan/local/``

The second and third prefixes accommodate workflow prose that substitutes
the worktree absolute path placeholder before the plan-scoped sub-path.
Every other path triggers the matched phase's ``*-contract-violation``
finding.

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
        'rule_id': '<matched phase rule id>',
        'file': '<absolute markdown path>',
        'line': <int, 1-based>,
        'tool': 'Edit' | 'Write',
        'path': '<offending path argument>',
        'suggested_fix': '<remediation hint>',
    }

Public API
----------
- ``analyze_phase2_refine_contract(paths, rules_filter=None)``: entry point
  — scans the three planning-phase workflow directories reachable from
  ``paths``.
"""

from __future__ import annotations

import re
from pathlib import Path

from _doctor_shared import Finding
from _rule_registry import RuleDescriptor

# Map each planning-phase directory segment to its contract-violation rule id.
# A single scanner covers all three planning phases because they all run on the
# main checkout; the emitted finding carries the rule id of whichever phase
# directory the offending file lives under.
_PHASE_RULE_IDS: dict[str, str] = {
    'phase-2-refine': 'refine-contract-violation',
    'phase-3-outline': 'outline-contract-violation',
    'phase-4-plan': 'plan-contract-violation',
}

RULE_DESCRIPTORS = [
    RuleDescriptor(
        rule_id=rule_id,
        severity='error',
        category='safety',
        scope='file-local',
    )
    for rule_id in _PHASE_RULE_IDS.values()
]

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


def _matched_phase(path: Path) -> tuple[str, str] | None:
    """Return ``(phase_dir, rule_id)`` for the first planning-phase directory
    segment present in ``path``, or ``None`` when the path is under none of the
    three planning phases.
    """
    for phase_dir, rule_id in _PHASE_RULE_IDS.items():
        if phase_dir in path.parts:
            return (phase_dir, rule_id)
    return None


def _scan_file(path: Path) -> list[dict]:
    """Scan a single planning-phase markdown file and return all findings.

    The emitted finding carries the rule id of the phase directory the file
    lives under; the phase's short name is interpolated into the description.
    """
    matched = _matched_phase(path)
    if matched is None:
        return []
    phase_dir, rule_id = matched
    # The trailing segment of the phase directory is the phase's short verb
    # ('phase-2-refine' → 'refine', 'phase-3-outline' → 'outline',
    # 'phase-4-plan' → 'plan') used in the finding description.
    phase_short = phase_dir.rsplit('-', 1)[-1]

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
                Finding(
                    type=rule_id,
                    rule_id=rule_id,
                    file=str(path),
                    line=idx + 1,
                    severity='error',
                    fixable=False,
                    description=(
                        f'{phase_dir} workflow file invokes `{tool}` against '
                        f'a non-plan path `{referenced_path}` — {phase_short} MUST write only '
                        f'inside `.plan/local/plans/{{plan_id}}/**` or '
                        f'`.plan/local/worktrees/{{plan_id}}/**` '
                        f'({rule_id})'
                    ),
                    details={
                        'tool': tool,
                        'path': referenced_path,
                        'suggested_fix': _suggested_fix(referenced_path),
                    },
                ).to_dict()
            )
    return findings


def _is_planning_workflow_file(path: Path) -> bool:
    """Return True for markdown files under any of the three planning-phase
    directories (``phase-2-refine`` / ``phase-3-outline`` / ``phase-4-plan``).
    """
    if path.suffix != '.md':
        return False
    return _matched_phase(path) is not None


def _resolve_targets(paths: list[Path]) -> list[Path]:
    """Expand ``paths`` into the concrete markdown files this rule scans.

    ``paths`` entries may be either individual ``.md`` files (passed through
    when they match the planning-workflow predicate) or directories (recursed
    to find all planning-phase ``**/*.md`` files inside them).
    """
    targets: list[Path] = []
    seen: set[Path] = set()
    for entry in paths:
        if entry.is_file():
            if _is_planning_workflow_file(entry) and entry not in seen:
                targets.append(entry)
                seen.add(entry)
        elif entry.is_dir():
            for md in sorted(entry.rglob('*.md')):
                if _is_planning_workflow_file(md) and md not in seen:
                    targets.append(md)
                    seen.add(md)
    return targets


def analyze_phase2_refine_contract(
    paths: list[Path],
    *,
    rules_filter: set[str] | None = None,
) -> list[dict]:
    """Scan ``paths`` for planning-phase contract violations.

    Parameters
    ----------
    paths:
        List of files and / or directories to scan. The analyzer self-filters
        to markdown files whose path contains one of the three planning-phase
        segments (``phase-2-refine`` / ``phase-3-outline`` / ``phase-4-plan``),
        so callers may safely pass broader sets (e.g. an entire bundle's
        skills directory).
    rules_filter:
        Optional opt-in rule allow-list. When supplied, a matched file is
        scanned only when its phase's rule id is in the set — the caller has
        deselected the other rules. When ``None`` (the default), all three
        rules are unconditionally active.

    Returns
    -------
    list[dict]
        A list of finding dicts (see module docstring for the shape). Empty
        when no violations are found OR when every matched file's rule is
        filtered out via ``rules_filter``.
    """
    findings: list[dict] = []
    for md_path in _resolve_targets(paths):
        matched = _matched_phase(md_path)
        if matched is None:
            continue
        _, rule_id = matched
        if rules_filter is not None and rule_id not in rules_filter:
            continue
        findings.extend(_scan_file(md_path))
    return findings

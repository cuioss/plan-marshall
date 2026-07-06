#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""``AskUserQuestion`` reachability scanner for dispatched-leaf workflow docs.

A workflow doc dispatched as an ``execution-context`` leaf CANNOT fire
``AskUserQuestion`` at runtime: operator input is unreachable inside a
dispatched subagent envelope (the tool is absent from the leaf's runtime tool
set even though ``agents/execution-context.md`` frontmatter lists it). The
canonical contract — a dispatched leaf returns an escalation/prompt-required
envelope for the inline orchestrator to own the prompt — lives at
``plan-marshall/skills/ref-workflow-architecture/standards/agents.md`` §
"Leaf cannot fire AskUserQuestion — return a prompt-required envelope".

This analyzer surfaces every remaining ``AskUserQuestion:`` **invocation block**
inside a dispatched-leaf workflow doc as an advisory finding so the unreachable
call sites are visible rather than silently degrading to a default. It is
**analyze-only / NON-gating** — registered in ``doctor-marketplace.py::cmd_analyze``
(via the runner's marketplace-wide pass), NOT in ``cmd_quality_gate`` — so it
surfaces findings without failing the build, mirroring the analyze-surfaced
agentfile-hygiene backstop rules.

Dispatched-leaf identification
------------------------------
A markdown doc is a dispatched-leaf workflow doc when BOTH hold:

1. It is a *declared dispatchable workflow body* — it carries
   ``implements: plan-marshall:extension-api/standards/ext-point-execution-context-workflow``
   in its frontmatter, OR it is a ``phase-*/SKILL.md`` phase skill (dispatched
   under a role key).
2. It is NOT itself a *main-context orchestrator*. The structural discriminator
   is the presence of a ``Task:`` dispatch directive: a dispatched leaf CANNOT
   spawn a further subagent, so a doc that carries one or more ``Task:`` dispatch
   blocks is an orchestrator running in main context (e.g.
   ``plan-marshall/workflow/planning.md``, which carries the ``implements:``
   frontmatter yet drives every phase dispatch and legitimately fires
   ``AskUserQuestion`` in its own list / cleanup / lessons menus). Excluding
   Task-dispatching docs is what keeps the rule from false-positiving the
   orchestrator's own menus.

Invocation-shape matching (NOT prose)
-------------------------------------
Only the structured **invocation block** is flagged: a line that is exactly
``AskUserQuestion:`` (optional leading whitespace, nothing else on the line)
immediately introducing a ``questions:`` / ``question:`` / ``options:`` sub-key.
Prose references — "fire an ``AskUserQuestion``", "surface via
``AskUserQuestion``", "do NOT fire ``AskUserQuestion`` here" — are NOT flagged,
because the many docs that merely mention the tool while delegating the actual
firing to the orchestrator must not trip the rule.

Findings have the shape::

    {
        'rule_id': 'askuserquestion-in-dispatched-workflow',
        'type': 'askuserquestion-in-dispatched-workflow',
        'rule': 'analyze_askuserquestion_reachability',
        'file': '<absolute markdown path>',
        'line': <int, 1-based (the AskUserQuestion: header line)>,
        'severity': 'warning',
        'fixable': False,
        'snippet': '<offending text excerpt, max 80 chars>',
        'description': '<short human-readable explanation>',
    }

Public API
----------
- ``analyze_askuserquestion_reachability(marketplace_root)``: entry point — scans
  every ``*.md`` under ``marketplace_root/*/skills/**/`` across all bundles.
"""

from __future__ import annotations

import re
from pathlib import Path

from _doctor_shared import Finding
from _rule_registry import RuleDescriptor

RULE_ID = 'askuserquestion-in-dispatched-workflow'
RULE_NAME = 'analyze_askuserquestion_reachability'
FINDING_TYPE = 'askuserquestion-in-dispatched-workflow'

RULE_DESCRIPTOR = RuleDescriptor(
    rule_id=RULE_ID,
    severity='warning',
    category='structural',
    scope='file-local',
)

# The execution-context workflow-body extension-point marker. A doc carrying
# this in its ``implements:`` frontmatter is a declared dispatchable workflow
# body.
IMPLEMENTS_MARKER = (
    'plan-marshall:extension-api/standards/ext-point-execution-context-workflow'
)

# ---------------------------------------------------------------------------
# Detection patterns
# ---------------------------------------------------------------------------

# Frontmatter block: leading ``---`` line, content, closing ``---`` line.
_FRONTMATTER_RE = re.compile(r'^---\s*\n(.*?)\n---\s*\n', re.DOTALL)

# The implements marker appearing anywhere in the frontmatter (it may be a
# single-value ``implements:`` or one entry of a YAML list).
_IMPLEMENTS_MARKER_RE = re.compile(re.escape(IMPLEMENTS_MARKER))

# A ``Task:`` dispatch directive at the start of a line — the structural tell of
# a main-context orchestrator (a leaf cannot dispatch a subagent).
_TASK_DISPATCH_RE = re.compile(r'^\s*Task:\s*\S')

# The ``AskUserQuestion:`` invocation-block header: the literal on its own line
# (only whitespace allowed before / after). A prose line such as
# ``If action: exists, use AskUserQuestion:`` does NOT match because the literal
# is not the first non-whitespace token on the line.
_ASKUSER_HEADER_RE = re.compile(r'^\s*AskUserQuestion:\s*$')

# The invocation-block sub-keys that confirm an ``AskUserQuestion:`` header is a
# structured call (not a stray line). Any of ``questions:`` / ``question:`` /
# ``options:`` introduces the block body.
_ASKUSER_SUBKEY_RE = re.compile(r'^\s*(?:questions|question|options)\s*:')


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_frontmatter(text: str) -> str:
    """Return the frontmatter block content, or an empty string when absent."""
    match = _FRONTMATTER_RE.match(text)
    return match.group(1) if match else ''


def _is_phase_skill(path: Path) -> bool:
    """True when the path is a ``phase-*/SKILL.md`` phase-skill body."""
    return path.name == 'SKILL.md' and path.parent.name.startswith('phase-')


def _is_dispatched_leaf_workflow(path: Path, text: str) -> bool:
    """Decide whether a markdown doc is a dispatched-leaf workflow body.

    True when the doc is a declared dispatchable workflow body (carries the
    execution-context ``implements:`` marker OR is a ``phase-*/SKILL.md``) AND is
    NOT itself a main-context orchestrator (carries no ``Task:`` dispatch
    directive). See the module docstring for the full contract.
    """
    frontmatter = _extract_frontmatter(text)
    declares_workflow = bool(_IMPLEMENTS_MARKER_RE.search(frontmatter)) or _is_phase_skill(path)
    if not declares_workflow:
        return False
    # Orchestrator exclusion: any ``Task:`` dispatch directive marks a
    # main-context orchestrator, which reaches the operator legitimately.
    for line in text.splitlines():
        if _TASK_DISPATCH_RE.match(line):
            return False
    return True


def _make_finding(path: Path, line_no: int, line: str) -> dict:
    snippet = line.strip()[:80]
    return Finding(
        type=FINDING_TYPE,
        file=str(path),
        line=line_no,
        severity='warning',
        fixable=False,
        rule_id=RULE_ID,
        description=(
            'AskUserQuestion invocation block inside a dispatched-leaf workflow '
            'doc. A doc dispatched as an execution-context leaf cannot reach the '
            'operator at runtime, so this prompt silently degrades to a default. '
            'Move the prompt to the inline orchestrator: the leaf returns a '
            'prompt-required envelope and the main-context orchestrator owns the '
            'AskUserQuestion (see ref-workflow-architecture/standards/agents.md '
            'Leaf cannot fire AskUserQuestion).'
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

    if not _is_dispatched_leaf_workflow(path, text):
        return []

    lines = text.splitlines()
    findings: list[dict] = []
    for idx, line in enumerate(lines):
        if not _ASKUSER_HEADER_RE.match(line):
            continue
        # Confirm the header introduces a structured invocation block: the next
        # non-blank line must be a ``questions:`` / ``question:`` / ``options:``
        # sub-key. A bare header with no block body is not an invocation.
        for follow in lines[idx + 1:]:
            if not follow.strip():
                continue
            if _ASKUSER_SUBKEY_RE.match(follow):
                findings.append(_make_finding(path, idx + 1, line))
            break

    return findings


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def _markdown_targets(marketplace_root: Path) -> list[Path]:
    """Return every ``*.md`` under any bundle's ``skills/`` tree."""
    targets: list[Path] = []
    for bundle_dir in sorted(p for p in marketplace_root.iterdir() if p.is_dir()):
        skills_root = bundle_dir / 'skills'
        if skills_root.is_dir():
            targets.extend(sorted(p for p in skills_root.rglob('*.md') if p.is_file()))
    return targets


def analyze_askuserquestion_reachability(marketplace_root: Path) -> list[dict]:
    """Scan every bundle's skill markdown for unreachable AskUserQuestion blocks.

    Walks ``marketplace_root/*/skills/**/*.md`` and reports every
    ``AskUserQuestion:`` invocation block inside a dispatched-leaf workflow doc
    (a declared execution-context workflow body / ``phase-*/SKILL.md`` that
    carries no ``Task:`` dispatch directive).

    Parameters
    ----------
    marketplace_root:
        Path to the marketplace bundles directory (the directory that contains
        the ``plan-marshall``, ``pm-dev-java``, etc. bundle directories — i.e.
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

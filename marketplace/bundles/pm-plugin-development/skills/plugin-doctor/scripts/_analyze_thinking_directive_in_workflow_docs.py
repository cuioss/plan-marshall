#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Reasoning-level directive scanner for the ``thinking-directive-in-workflow-doc`` rule.

This module implements a deterministic regex-based static analyzer that detects
in-prose directives instructing the model to adopt a *reasoning level* or to
*narrate a reasoning process* inside dispatched workflow docs — the population of
markdown reachable as an ``execution-context-{level}`` ``workflow:`` target.

Why the directive is inert
--------------------------
``marketplace/bundles/plan-marshall/agents/execution-context.md`` states the
contract outright: **model and effort are NOT prompt-body fields; they are pinned
by the variant filename (``execution-context-{level}.md``) the caller dispatched
against.** A doc reached only through such a dispatch runs at a level already
fixed before its first line is read, so a prose directive such as "use ultrathink
mode" or "use careful step-by-step reasoning" cannot do what it says. It is at
best inert, and at worst in tension with the pin — the *vacuous guard* archetype:
a predicate that can never fire, two files away from the contract that says so.

Population — derived, never hand-listed
---------------------------------------
The candidate file set is **derived** from each doc's own frontmatter: every
``SKILL.md`` and every ``workflow/*.md`` under
``marketplace_root/*/skills/*/`` whose ``implements:`` frontmatter declares the
execution-context-workflow ext-point (scalar or block-sequence form). That is
the structural definition of "reachable as an ``execution-context*``
``workflow:`` target" — the same ext-point the dispatcher resolves against
(see ``ext-point-execution-context-workflow.md`` § Addressing). Nothing is
hardcoded, so a workflow doc added tomorrow is covered the moment it declares
the ext-point.

Anti-vacuity guard
------------------
The analyzer PUBLISHES the population size it examined in every finding's
``details.population_size`` and, when the derived population is empty, emits its
own finding (``reason: empty_population``). A clean (zero-violation) result
therefore proves the population was non-empty rather than reading a vacuous pass
over an unread population — the exact archetype this rule exists to close.

Detection — the false-positive boundary is the hard part
--------------------------------------------------------
Descriptive prose about workflow *sequencing* ("Step-by-step workflow for
creating a solution outline") is **not** a violation. Only a directive asking the
model to adopt a reasoning level, or to narrate a reasoning process, is. Six
high-precision families are recognized (all case-insensitive), each firing on a
cognition directive and deliberately NOT on procedural prose:

1. ``ultrathink`` — Claude reasoning-mode jargon (``ultrathink`` / ``ultra think``
   / ``ultra-think``), REQUIRED to carry a directive cue (use/enable/apply/…) in
   the same clause. A descriptive mention ("the ultrathink feature is documented
   elsewhere") is not a directive and is NOT flagged.
2. ``extended-thinking`` — "extended thinking" reasoning-mode jargon, likewise
   directive-scoped ("use extended thinking" fires; "extended thinking is
   configured by the dispatcher" does not).
3. ``careful-reasoning`` — "careful (step-by-step) reasoning/thinking/thought",
   "reason carefully". Does NOT fire on "careful analysis" (a review activity,
   not a reasoning-level directive).
4. ``step-by-step-reasoning`` — "step-by-step reasoning/thinking/thought" and
   "reason/think step by step". Does NOT fire on "step-by-step
   workflow/guide/process/…" (sequencing prose): the distinguishing token is the
   cognition noun that must sit adjacent to "step by step".
5. ``think-imperative`` — "think carefully/deeply/hard/harder/slowly/thoroughly".
6. ``take-your-time`` — "take your time".

YAML frontmatter, fenced code blocks (backtick OR tilde, three-or-more markers),
and inline-code spans are exempt (a token inside them is an example, not a live
directive).

Findings have the shape::

    {
        'rule_id': 'thinking-directive-in-workflow-doc',
        'type': 'thinking_directive_in_workflow_doc',
        'rule': 'analyze_thinking_directive_in_workflow_docs',
        'file': '<absolute markdown path>',
        'line': <int, 1-based>,
        'severity': 'error',
        'fixable': False,
        'details': {'family': '<family name>', 'population_size': <int>},
        'snippet': '<matched text excerpt>',
        'message': '<human-readable description>',
    }

Public API
----------
- ``enumerate_execution_context_workflow_docs(marketplace_root)``: the derived
  population (list of ``Path``).
- ``analyze_thinking_directive_in_workflow_docs(marketplace_root)``: entry point
  — derives the population, scans each doc, and returns a list of finding dicts
  (empty for a clean, non-empty population).
"""

from __future__ import annotations

import re
from pathlib import Path

from _doctor_shared import Finding
from _rule_registry import RuleDescriptor

RULE_ID = 'thinking-directive-in-workflow-doc'
RULE_NAME = 'analyze_thinking_directive_in_workflow_docs'
FINDING_TYPE = 'thinking_directive_in_workflow_doc'
EMPTY_POPULATION_TYPE = 'thinking_directive_population_empty'

# The ext-point every dispatched workflow doc declares. Membership in the
# population is DECLARED on each doc via this ``implements:`` value and DERIVED by
# the frontmatter scan below — never a hand-maintained path list. The contract
# lives in the central standard: marketplace/bundles/plan-marshall/skills/
# extension-api/standards/ext-point-execution-context-workflow.md.
EXT_POINT = 'plan-marshall:extension-api/standards/ext-point-execution-context-workflow'

# The standard doc that DEFINES the ext-point. Its presence is the anchor for the
# empty-population guard: a tree that defines the ext-point but derives zero
# implementors has a broken derivation (the vacuity archetype), whereas a minimal
# tree that does not define the ext-point legitimately has no population and is
# not flagged.
_EXT_POINT_STANDARD_REL = 'plan-marshall/skills/extension-api/standards/ext-point-execution-context-workflow.md'

RULE_DESCRIPTOR = RuleDescriptor(
    rule_id=RULE_ID,
    severity='error',
    category='content',
    scope='corpus-relational',
)

# ---------------------------------------------------------------------------
# Detection patterns — high precision, favouring a false negative over a false
# positive (per the plan: a detector that fires on procedural prose is a
# regression, not a win). Families are checked in order; the FIRST match on a
# line wins, so a line carries at most one finding and overlapping families
# (e.g. "careful step-by-step reasoning" matches both careful-reasoning and
# step-by-step-reasoning) are recorded under the most specific family.
# ---------------------------------------------------------------------------

# A directive cue: an imperative/modal verb that turns a bare reasoning-mode term
# into an instruction. Required for the two "bare-term" families (ultrathink,
# extended thinking) so a DESCRIPTIVE mention ("Extended thinking is configured by
# the dispatcher") is NOT flagged — only a directive ("use ultrathink") is. The
# cue must sit in a short same-clause window before the term; the window stops at
# a clause boundary (``.`` / ``;`` / ``:``) so a cue in an unrelated clause on the
# same line ("Use the search tool; ultrathink is documented below") does not bind.
_DIRECTIVE_CUES = (
    r'use|uses|using|enabl(?:e|es|ing)|appl(?:y|ies|ying)|invok(?:e|es|ing)'
    r'|engag(?:e|es|ing)|employ(?:s|ing)?|activat(?:e|es|ing)|consider(?:s|ing)?'
    r'|switch(?:es|ing)?\s+to|turn(?:s|ing)?\s+on'
)
_CUE_WINDOW = r'[^.;:\n]{0,40}?'

# Family 1: Claude reasoning-mode jargon (``ultrathink`` / ``ultra think`` /
# ``ultra-think``), directive-scoped. A dispatched doc cannot enable it — the
# level is pinned by the variant filename.
_ULTRATHINK_RE = re.compile(rf'\b(?:{_DIRECTIVE_CUES})\b{_CUE_WINDOW}\bultra[\s-]?think\b', re.IGNORECASE)

# Family 2: "extended thinking" reasoning-mode jargon, directive-scoped.
_EXTENDED_THINKING_RE = re.compile(rf'\b(?:{_DIRECTIVE_CUES})\b{_CUE_WINDOW}\bextended thinking\b', re.IGNORECASE)

# Family 3: "careful (step-by-step) reasoning/thinking/thought", "reason
# carefully". The cognition noun (reasoning/thinking/thought) is required after
# "careful", so "careful analysis" — a review activity, not a reasoning-level
# directive — does NOT match.
_CAREFUL_REASONING_RE = re.compile(
    r'\b(?:careful(?:ly)?\s+(?:step[\s-]by[\s-]step\s+)?(?:reasoning|thinking|thought)'
    r'|reason\s+carefully)\b',
    re.IGNORECASE,
)

# Family 4: "step-by-step reasoning/thinking/thought" and "reason/think step by
# step". The cognition noun adjacent to "step by step" is the whole point: it
# fires on chain-of-thought scaffolds and NOT on "step-by-step
# workflow/guide/process/instructions/approach/outline" (sequencing prose).
_STEP_BY_STEP_REASONING_RE = re.compile(
    r'\b(?:step[\s-]by[\s-]step\s+(?:reasoning|thinking|thought)'
    r'|(?:reason(?:ing)?|think(?:ing)?)\s+step[\s-]by[\s-]step)\b',
    re.IGNORECASE,
)

# Family 5: "think {intensifier}" imperatives. "step by step" is deliberately
# excluded here (family 4 owns it) so a line matches exactly one family.
_THINK_IMPERATIVE_RE = re.compile(
    r'\bthink\s+(?:carefully|deeply|hard(?:er)?|slowly|thoroughly|longer)\b',
    re.IGNORECASE,
)

# Family 6: "take your time" — a reasoning-effort nudge.
_TAKE_YOUR_TIME_RE = re.compile(r'\btake your time\b', re.IGNORECASE)

# Ordered (name, pattern) pairs — first match on a line wins.
_PATTERNS: list[tuple[str, re.Pattern]] = [
    ('ultrathink', _ULTRATHINK_RE),
    ('extended-thinking', _EXTENDED_THINKING_RE),
    ('careful-reasoning', _CAREFUL_REASONING_RE),
    ('step-by-step-reasoning', _STEP_BY_STEP_REASONING_RE),
    ('think-imperative', _THINK_IMPERATIVE_RE),
    ('take-your-time', _TAKE_YOUR_TIME_RE),
]

# Structural-exemption helpers. Inline-code spans mirror
# _analyze_historical_prose_in_skills.py; the fence marker recognizes both
# backtick and tilde fences of three-or-more markers (CommonMark), not only the
# exactly-three-backtick form.
_INLINE_CODE_RE = re.compile(r'`([^`]+)`')
_FENCE_MARKER_RE = re.compile(r'^\s*(`{3,}|~{3,})')


# ---------------------------------------------------------------------------
# Frontmatter ``implements:`` reader (scalar + block-sequence forms)
# ---------------------------------------------------------------------------


def _declared_implements(text: str) -> list[str]:
    """Return the ``implements:`` value(s) from a doc's leading YAML frontmatter.

    Handles both the inline-scalar form (``implements: <value>``) and the
    block-sequence form (``implements:`` followed by ``- <value>`` item lines),
    mirroring ``extension_discovery.read_implements_field``. Returns an empty
    list when the file carries no leading ``---`` frontmatter or declares no
    ``implements:`` key.
    """
    if not text.startswith('---'):
        return []
    end = text.find('\n---', 3)
    if end == -1:
        return []
    fm_lines = text[3:end].split('\n')

    for index, raw_line in enumerate(fm_lines):
        line = raw_line.strip()
        if not line or line.startswith('#') or ':' not in line:
            continue
        key, _, value = line.partition(':')
        if key.strip() != 'implements':
            continue
        inline = value.strip().strip('"').strip("'")
        if inline:
            return [inline]
        values: list[str] = []
        for seq_raw in fm_lines[index + 1 :]:
            seq = seq_raw.strip()
            if not seq or seq.startswith('#'):
                continue
            if not seq.startswith('- '):
                break
            item = seq[2:].strip().strip('"').strip("'")
            if item:
                values.append(item)
        return values
    return []


# ---------------------------------------------------------------------------
# Population derivation
# ---------------------------------------------------------------------------


def enumerate_execution_context_workflow_docs(marketplace_root: Path) -> list[Path]:
    """Return every dispatched-workflow doc declaring the execution-context ext-point.

    Scans ``marketplace_root/*/skills/*/SKILL.md`` and
    ``marketplace_root/*/skills/*/workflow/*.md`` — the two addressing surfaces
    an execution-context ``workflow:`` target may live at — and keeps the docs
    whose frontmatter ``implements:`` list contains :data:`EXT_POINT`. The
    population is derived from each doc's own declaration; nothing is hardcoded.

    Returns the matching paths in sorted order (empty when the tree is absent).
    """
    marketplace_root = Path(marketplace_root)
    if not marketplace_root.is_dir():
        return []
    docs: list[Path] = []
    for bundle_dir in sorted(marketplace_root.iterdir()):
        if not bundle_dir.is_dir() or bundle_dir.name.startswith('.'):
            continue
        skills_dir = bundle_dir / 'skills'
        if not skills_dir.is_dir():
            continue
        for skill_dir in sorted(skills_dir.iterdir()):
            if not skill_dir.is_dir() or skill_dir.name.startswith('.'):
                continue
            candidates = [skill_dir / 'SKILL.md']
            workflow_dir = skill_dir / 'workflow'
            if workflow_dir.is_dir():
                candidates.extend(sorted(workflow_dir.glob('*.md')))
            for candidate in candidates:
                if not candidate.is_file():
                    continue
                try:
                    text = candidate.read_text(encoding='utf-8')
                except (OSError, UnicodeDecodeError):
                    continue
                if EXT_POINT in _declared_implements(text):
                    docs.append(candidate)
    return docs


# ---------------------------------------------------------------------------
# Structural-exemption helpers
# ---------------------------------------------------------------------------


def _build_fence_map(lines: list[str]) -> set[int]:
    """Return the 0-based indices of lines inside any fenced code block.

    Recognizes both backtick and tilde fences of three-or-more markers
    (CommonMark). A fence closes on a bare line of the SAME marker character, at
    least as long as the opener (an info string is allowed only on the opener).
    The opening and closing fence lines themselves are not counted as inside.
    """
    inside: set[int] = set()
    fence: tuple[str, int] | None = None  # (marker char, marker length)
    for idx, line in enumerate(lines):
        if fence is None:
            marker = _FENCE_MARKER_RE.match(line)
            if marker:
                token = marker.group(1)
                fence = (token[0], len(token))
            continue
        char, length = fence
        stripped = line.strip()
        if stripped and stripped == char * len(stripped) and len(stripped) >= length:
            # Bare closing fence: same char, at least as long as the opener.
            fence = None
        else:
            inside.add(idx)
    return inside


def _build_frontmatter_set(lines: list[str]) -> set[int]:
    """Return the 0-based indices of lines inside leading YAML frontmatter."""
    inside: set[int] = set()
    if not lines or lines[0].strip() != '---':
        return inside
    inside.add(0)
    for idx in range(1, len(lines)):
        inside.add(idx)
        if lines[idx].strip() == '---':
            return inside
    return set()


def _inline_code_spans(line: str) -> list[tuple[int, int]]:
    """Return (start, end) character offsets of inline-code spans on ``line``."""
    return [(m.start(), m.end()) for m in _INLINE_CODE_RE.finditer(line)]


def _offset_in_inline_code(offset: int, spans: list[tuple[int, int]]) -> bool:
    """Return True if ``offset`` lies within any of the inline-code spans."""
    return any(start <= offset < end for start, end in spans)


# ---------------------------------------------------------------------------
# File-level scanner
# ---------------------------------------------------------------------------


def _scan_doc(path: Path, population_size: int) -> list[dict]:
    """Scan one workflow doc and emit a finding per line carrying a directive."""
    try:
        text = path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        return []

    lines = text.splitlines()
    fence = _build_fence_map(lines)
    frontmatter = _build_frontmatter_set(lines)

    findings: list[dict] = []
    for idx, line in enumerate(lines):
        if idx in frontmatter or idx in fence:
            continue
        spans = _inline_code_spans(line)
        for family, pattern in _PATTERNS:
            # Take the first match of this family that is NOT inside an
            # inline-code span. ``search`` would return only the first match, so
            # a live directive later on the same line as an in-code mention
            # (e.g. "Mention `ultrathink`, then use ultrathink mode") would be
            # missed; ``finditer`` scans every occurrence.
            match = next(
                (m for m in pattern.finditer(line) if not _offset_in_inline_code(m.start(), spans)),
                None,
            )
            if match is None:
                continue
            findings.append(
                Finding(
                    type=FINDING_TYPE,
                    file=str(path),
                    line=idx + 1,
                    severity='error',
                    fixable=False,
                    rule_id=RULE_ID,
                    details={'family': family, 'population_size': population_size},
                    extra={
                        'rule': RULE_NAME,
                        'snippet': match.group(0),
                        'message': (
                            f'In-prose reasoning-level directive '
                            f'(`{match.group(0)}`) in a dispatched workflow doc. '
                            f'Model and effort are pinned by the '
                            f'execution-context-{{level}} variant the caller '
                            f'dispatched against, so this directive is inert. '
                            f'Remove it; preserve surrounding criteria. See '
                            f'rule-catalog.md.'
                        ),
                    },
                ).to_dict()
            )
            # First-match-per-line: one finding per line, most specific family.
            break
    return findings


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def analyze_thinking_directive_in_workflow_docs(marketplace_root: Path) -> list[dict]:
    """Scan dispatched workflow docs for in-prose reasoning-level directives.

    Derives the population (docs declaring the execution-context ext-point via
    :func:`enumerate_execution_context_workflow_docs`), then scans each for a
    reasoning-level / reasoning-process directive outside frontmatter, fenced
    code blocks, and inline-code spans. Every finding publishes the
    ``population_size`` examined; an EMPTY derived population emits its own
    finding so a clean result can never read as coverage over an unread
    population.

    Parameters
    ----------
    marketplace_root:
        Path to the marketplace bundles root (the directory that contains the
        ``plan-marshall``, ``pm-documents``, etc. bundle directories).

    Returns
    -------
    list[dict]
        List of finding dicts (empty for a clean, non-empty population).
    """
    marketplace_root = Path(marketplace_root)
    population = enumerate_execution_context_workflow_docs(marketplace_root)
    population_size = len(population)

    if population_size == 0:
        # Anti-vacuity guard: an empty population is a finding ONLY when this tree
        # actually DEFINES the ext-point (the standard doc exists). Then zero
        # implementors means the derivation broke — a rule reporting "clean" over
        # an unread population, the archetype this epic is named for. A minimal
        # tree that does not define the ext-point legitimately has no population
        # and is not flagged.
        if (marketplace_root / _EXT_POINT_STANDARD_REL).is_file():
            return [
                Finding(
                    type=EMPTY_POPULATION_TYPE,
                    file=str(marketplace_root),
                    line=0,
                    severity='error',
                    fixable=False,
                    rule_id=RULE_ID,
                    details={'population_size': 0, 'reason': 'empty_population'},
                    extra={
                        'rule': RULE_NAME,
                        'snippet': '',
                        'message': (
                            'The execution-context-workflow ext-point is defined '
                            'but its derived population is EMPTY — the '
                            'reasoning-level-directive sweep would be vacuous. '
                            f'Expected docs declaring `implements: {EXT_POINT}`. '
                            'See rule-catalog.md.'
                        ),
                    },
                ).to_dict()
            ]
        return []

    findings: list[dict] = []
    for doc in population:
        findings.extend(_scan_doc(doc, population_size))
    return findings

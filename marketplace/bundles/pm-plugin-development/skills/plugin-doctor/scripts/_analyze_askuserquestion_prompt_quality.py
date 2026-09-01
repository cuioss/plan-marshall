#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""``AskUserQuestion`` prompt-quality scanner — the mechanical subset.

The authoring contract is
``pm-plugin-development:plugin-architecture`` ``references/askuserquestion-patterns.md``,
which states five numbered obligations every prompt must meet. This analyzer
enforces the three that are mechanically checkable and declines the two that are
not, rather than approximating them:

- **check A — preamble/option vocabulary** (obligations 5 and 2). A ``question:``
  preamble, or an option ``label`` / ``description``, carrying a workflow
  step-number token, a tool-API type name, or an internal-mechanics noun.
- **check B — option missing consequence** (obligation 1). An option entry that
  carries a ``label`` with no ``description`` sub-key, or whose ``description``
  only restates its ``label``.

Declared blind spots
--------------------
Obligation **3** (the recommended option is marked and ordered first) and
obligation **4** (the question names what the system already knows and why it
still needs the user) are **NOT evaluated** by this analyzer, and no attempt is
made to approximate them. Both require judging whether a recommendation is
*correct* and whether context is *sufficient* — neither is a token-level
property. A silent run therefore means "no obligation-1, -2 or -5 violation was
found in the invocation blocks examined"; it is **not** a verdict that a prompt
is conformant. Every finding publishes ``population_size`` — the number of
invocation blocks the run examined — so a finding is never reported without the
population it was drawn against.

Invocation-shape matching (NOT prose)
-------------------------------------
The recognizer is the sibling ``_analyze_askuserquestion_reachability.py``
recognizer, unchanged: only a structured **invocation block** is examined — a
line that is exactly ``AskUserQuestion:`` (optional leading whitespace, nothing
else on the line) immediately introducing a ``questions:`` / ``question:`` /
``options:`` sub-key. Prose references to the tool are never examined, and a
bare ``AskUserQuestion:`` header with no block body is not an invocation.

Findings have the shape::

    {
        'rule_id': 'askuserquestion-prompt-quality',
        'type': 'askuserquestion-prompt-quality',
        'rule': 'analyze_askuserquestion_prompt_quality',
        'file': '<absolute markdown path>',
        'line': <int, 1-based>,
        'severity': 'warning',
        'fixable': False,
        'snippet': '<offending text excerpt, max 80 chars>',
        'description': '<which obligation was violated and why>',
        'population_size': <int, invocation blocks examined across the run>,
    }

Public API
----------
- ``analyze_askuserquestion_prompt_quality(marketplace_root)``: entry point —
  scans every ``*.md`` under ``marketplace_root/*/skills/**/``.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import NamedTuple

from _doctor_shared import Finding
from _rule_registry import RuleDescriptor

RULE_ID = 'askuserquestion-prompt-quality'
RULE_NAME = 'analyze_askuserquestion_prompt_quality'
FINDING_TYPE = 'askuserquestion-prompt-quality'

RULE_DESCRIPTOR = RuleDescriptor(
    rule_id=RULE_ID,
    severity='warning',
    category='content',
    scope='file-local',
)

# ---------------------------------------------------------------------------
# Detection patterns
# ---------------------------------------------------------------------------

# The ``AskUserQuestion:`` invocation-block header and the sub-keys that confirm
# it introduces a structured call. Both mirror the sibling reachability scanner.
_ASKUSER_HEADER_RE = re.compile(r'^\s*AskUserQuestion:\s*$')
_ASKUSER_SUBKEY_RE = re.compile(r'^\s*(?:questions|question|options)\s*:')

# A ``question:`` preamble, with or without the leading list dash.
_QUESTION_RE = re.compile(r'^\s*(?:-\s+)?question\s*:\s*(\S.*)$')

# A YAML list item and a ``key: value`` mapping line.
_ITEM_RE = re.compile(r'^(\s*)-\s+(\S.*)$')
_KEY_RE = re.compile(r'^([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.*)$')

# Two or more quoted ``key: "value"`` pairs written on ONE line — the flow form
# ``- label: "Resume"  description: "Continue with the existing plan"``. Without
# this the trailing pairs are swallowed into the first key's value and a fully
# described option reads as one that declares no description at all.
_QUOTED_PAIR_RE = re.compile(
    r'([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*("[^"]*"|\'[^\']*\')'
)

# A workflow step-number token: ``Step 4``, ``Step 4b``, ``step 12``. Kept as a
# pattern rather than a token set because the ordinal is unbounded.
_STEP_NUMBER_RE = re.compile(r'\bsteps?\s+\d+[a-z]?\b', re.IGNORECASE)

# Tool-API type names. Deliberately tiny and literal: these are names of the
# AskUserQuestion tool schema and its sibling tool directives, which a reader
# answering the prompt has no way to know about.
_TOOL_API_TYPE_NAMES = frozenset(
    {
        'askuserquestion',
        'multiselect',
        'slashcommand',
    }
)

# Internal-mechanics nouns. Deliberately tiny and literal rather than a general
# "internal noun" classifier: each entry names a plan-marshall runtime mechanism
# a reader can only reason about by having read this codebase.
_INTERNAL_MECHANICS_NOUNS = frozenset(
    {
        'dispatch envelope',
        'execution-context',
        'frontmatter',
        'skill loading',
        'standard set',
        'subagent',
        'worktree',
    }
)

# Punctuation stripper for the label-vs-description restatement comparison.
_NON_ALNUM_RE = re.compile(r'[^a-z0-9]+')


class _Violation(NamedTuple):
    """One detected obligation violation, before the population is known."""

    line: int
    snippet: str
    description: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _indent(line: str) -> int:
    """Return the leading-whitespace width of a line."""
    return len(line) - len(line.lstrip())


def _unquote(value: str) -> str:
    """Strip one layer of matching surrounding quotes from a scalar value."""
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
        return value[1:-1]
    return value


def _normalise(value: str) -> str:
    """Lower-case, strip punctuation and collapse whitespace for comparison."""
    return _NON_ALNUM_RE.sub(' ', _unquote(value).lower()).strip()


def _scalar_pairs(text: str) -> dict[str, str]:
    """Return the ``key: value`` mapping entries one line of YAML declares.

    A line carrying two or more quoted pairs is a flow-style mapping and every
    pair is returned; anything else is the ordinary one-key-per-line form, whose
    value runs to end of line.
    """
    quoted = _QUOTED_PAIR_RE.findall(text)
    if len(quoted) >= 2:
        return dict(quoted)
    single = _KEY_RE.match(text)
    return {single.group(1): single.group(2)} if single else {}


def _vocabulary_hits(text: str) -> list[str]:
    """Return the check-A vocabulary violations a piece of prompt text carries."""
    lowered = text.lower()
    hits: list[str] = []
    step_match = _STEP_NUMBER_RE.search(text)
    if step_match:
        hits.append(f'workflow step number "{step_match.group(0)}"')
    hits.extend(
        f'tool-API type name "{name}"'
        for name in sorted(_TOOL_API_TYPE_NAMES)
        if name in lowered
    )
    hits.extend(
        f'internal-mechanics noun "{noun}"'
        for noun in sorted(_INTERNAL_MECHANICS_NOUNS)
        if noun in lowered
    )
    return hits


def _block_body(lines: list[str], header_idx: int) -> list[int]:
    """Return the line indices belonging to the block opened at ``header_idx``.

    The body runs until the first non-blank line indented no further than the
    ``AskUserQuestion:`` header itself.
    """
    header_indent = _indent(lines[header_idx])
    body: list[int] = []
    for idx in range(header_idx + 1, len(lines)):
        line = lines[idx]
        if not line.strip():
            body.append(idx)
            continue
        if _indent(line) <= header_indent:
            break
        body.append(idx)
    return body


def _is_invocation_block(lines: list[str], header_idx: int) -> bool:
    """Confirm the header at ``header_idx`` introduces a structured call."""
    for follow in lines[header_idx + 1:]:
        if not follow.strip():
            continue
        return bool(_ASKUSER_SUBKEY_RE.match(follow))
    return False


def _own_keys(lines: list[str], body: list[int], item_pos: int) -> dict[str, str]:
    """Return the sub-keys a list item declares at its OWN nesting level.

    Keys belonging to a nested structure (a deeper-indented mapping, or a nested
    list item) are excluded, so an outer ``- question:`` item never absorbs the
    ``label`` / ``description`` keys of the options nested beneath it.
    """
    line = lines[body[item_pos]]
    match = _ITEM_RE.match(line)
    if match is None:
        return {}
    dash_indent = len(match.group(1))
    inline = match.group(2)
    own_indent = line.index(inline)

    keys: dict[str, str] = dict(_scalar_pairs(inline))

    for idx in body[item_pos + 1:]:
        follow = lines[idx]
        if not follow.strip():
            continue
        follow_indent = _indent(follow)
        if follow_indent <= dash_indent:
            break
        if follow_indent != own_indent or follow.lstrip().startswith('- '):
            continue
        keys.update(_scalar_pairs(follow.strip()))
    return keys


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------


def _check_vocabulary(line_no: int, kind: str, text: str) -> list[_Violation]:
    """check A — flag internal vocabulary in a preamble or an option field."""
    hits = _vocabulary_hits(text)
    if not hits:
        return []
    obligation = '5' if kind == 'preamble' else '2'
    return [
        _Violation(
            line=line_no,
            snippet=text.strip()[:80],
            description=(
                f'AskUserQuestion {kind} carries {", ".join(hits)}. A reader '
                'answering the prompt cannot evaluate system-internal '
                f'vocabulary — obligation {obligation} of '
                'plugin-architecture/references/askuserquestion-patterns.md. '
                'Rewrite it in terms of the reader\'s own work.'
            ),
        )
    ]


def _check_consequence(line_no: int, keys: dict[str, str]) -> list[_Violation]:
    """check B — flag an option that does not state what choosing it does."""
    label = keys['label']
    if 'description' not in keys:
        return [
            _Violation(
                line=line_no,
                snippet=_unquote(label)[:80],
                description=(
                    'AskUserQuestion option declares a label with no '
                    'description, so it never states what happens when it is '
                    'chosen — obligation 1 of '
                    'plugin-architecture/references/askuserquestion-patterns.md.'
                ),
            )
        ]
    if _normalise(keys['description']) == _normalise(label):
        return [
            _Violation(
                line=line_no,
                snippet=_unquote(label)[:80],
                description=(
                    'AskUserQuestion option description only restates its '
                    'label, so it names the option rather than its consequence '
                    '— obligation 1 of '
                    'plugin-architecture/references/askuserquestion-patterns.md.'
                ),
            )
        ]
    return []


# ---------------------------------------------------------------------------
# File-level scanner
# ---------------------------------------------------------------------------


def _scan_block(lines: list[str], header_idx: int) -> list[_Violation]:
    """Return every violation the invocation block at ``header_idx`` carries."""
    body = _block_body(lines, header_idx)
    violations: list[_Violation] = []

    for idx in body:
        question = _QUESTION_RE.match(lines[idx])
        if question:
            violations.extend(
                _check_vocabulary(idx + 1, 'preamble', _unquote(question.group(1)))
            )

    for item_pos, idx in enumerate(body):
        if not _ITEM_RE.match(lines[idx]):
            continue
        keys = _own_keys(lines, body, item_pos)
        if 'label' not in keys:
            continue
        violations.extend(_check_consequence(idx + 1, keys))
        for field_name in ('label', 'description'):
            if field_name in keys:
                violations.extend(
                    _check_vocabulary(
                        idx + 1, f'option {field_name}', _unquote(keys[field_name])
                    )
                )

    return sorted(violations)


def _scan_file(path: Path) -> tuple[list[_Violation], int, list[dict]]:
    """Scan one markdown file.

    Returns ``(violations, blocks_examined, read_errors)``. The read-error list
    carries a ready-made finding dict for the unreadable-file case, which is a
    file-level diagnostic rather than a rule violation.
    """
    try:
        text = path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError) as exc:
        return (
            [],
            0,
            [
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
            ],
        )

    lines = text.splitlines()
    violations: list[_Violation] = []
    blocks = 0
    for idx, line in enumerate(lines):
        if not _ASKUSER_HEADER_RE.match(line):
            continue
        if not _is_invocation_block(lines, idx):
            continue
        blocks += 1
        violations.extend(_scan_block(lines, idx))
    return violations, blocks, []


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


def _make_finding(path: Path, violation: _Violation, population_size: int) -> dict:
    return Finding(
        type=FINDING_TYPE,
        file=str(path),
        line=violation.line,
        severity='warning',
        fixable=False,
        rule_id=RULE_ID,
        description=violation.description,
        extra={
            'rule': RULE_NAME,
            'snippet': violation.snippet,
            'population_size': population_size,
        },
    ).to_dict()


def analyze_askuserquestion_prompt_quality(marketplace_root: Path) -> list[dict]:
    """Scan every bundle's skill markdown for low-quality AskUserQuestion prompts.

    Walks ``marketplace_root/*/skills/**/*.md`` and reports each violation of
    obligation 1, 2 or 5 inside an ``AskUserQuestion:`` invocation block.
    Obligations 3 and 4 are declared blind spots (see the module docstring): a
    clean result does not certify a conformant prompt.

    Parameters
    ----------
    marketplace_root:
        Path to the marketplace bundles directory (the directory that contains
        the ``plan-marshall``, ``pm-dev-java``, etc. bundle directories — i.e.
        ``<repo>/marketplace/bundles``).

    Returns
    -------
    list[dict]
        List of finding dicts (empty for a clean tree). Every finding carries
        ``population_size``: the number of invocation blocks the run examined.
    """
    per_file: list[tuple[Path, list[_Violation]]] = []
    findings: list[dict] = []
    population_size = 0
    for md_path in _markdown_targets(marketplace_root):
        violations, blocks, read_errors = _scan_file(md_path)
        findings.extend(read_errors)
        population_size += blocks
        if violations:
            per_file.append((md_path, violations))

    for path, violations in per_file:
        findings.extend(
            _make_finding(path, violation, population_size) for violation in violations
        )
    return findings

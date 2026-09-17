#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Cause-selection logic for the exit-code-convention derivation.

This module holds the classification half of the former
``_exit_code_convention_derivation`` helper: which skill documents are
retained and how each retained document classifies. The population and
body-sweep measurements live in ``_exit_code_convention_derivation_messages``,
which imports these predicates.
"""

from __future__ import annotations

import re
from pathlib import Path

from conftest import PROJECT_ROOT

#: The literal every executor invocation carries. A document with no occurrence
#: of it invokes nothing and never enters the population.
EXECUTOR_TOKEN = '.plan/execute-script.py'

#: Classification outcomes. Exhaustive and mutually exclusive over the retained
#: population: every retained document lands in exactly one.
WIDENED = 'widened'
NARROW = 'narrow'
NONE = 'none'

#: A fenced-code-block delimiter. Matched loosely (any info string, both fence
#: characters) because the only thing the walk needs from a fence is where
#: command text starts and stops.
_FENCE_RE = re.compile(r'^\s*(?:```|~~~)')

#: A ``{bundle}:{skill}:{script}`` notation. Placeholder forms such as
#: ``{bundle}:{skill}:{script}`` do not match, because braces are outside the
#: character class — which is the point: a template is not an invocation.
_NOTATION_RE = re.compile(r'\b[A-Za-z0-9][A-Za-z0-9_-]*:[A-Za-z0-9][A-Za-z0-9_-]*:[A-Za-z0-9][A-Za-z0-9_-]*\b')

#: A markdown heading naming an exit-code convention, at any level.
_CONVENTION_HEADING_RE = re.compile(r'^(#{1,6})\s+(.*exit-code convention.*)$', re.IGNORECASE)

#: Any markdown heading — used to find where a convention section ends.
_ANY_HEADING_RE = re.compile(r'^(#{1,6})\s')

#: A convention heading that scopes itself to ``manage-*`` — the superseded form.
#: Matched on the HEADING rather than the body, because the heading is forbidden
#: for a retained document however complete its prose happens to be: a narrow
#: section that spells out all three clauses still satisfies
#: :func:`states_full_contract`, so a body-only test would accept it.
_NARROW_HEADING_RE = re.compile(r'^#{1,6}\s+.*exit-code convention.*manage-', re.IGNORECASE)

#: The one document that states the contract. Every other document reaches the
#: contract by referring to this one.
CANONICAL_STANDARD = 'marketplace/bundles/plan-marshall/skills/tools-script-executor/standards/exit-code-convention.md'

#: The tail of :data:`CANONICAL_STANDARD` that a reference must name. Matching the
#: TAIL rather than the whole path is what makes the per-document relative prefix
#: (``standards/``, ``../``, ``../../../plan-marshall/skills/``) irrelevant: a
#: reference is correct wherever it is written from, and the predicate should not
#: have to know the depth of the document writing it.
_CANONICAL_LINK_TAIL = 'tools-script-executor/standards/exit-code-convention.md'

#: A disposition clause, as it appears in the contract: a list item opening with
#: the ``exit_code`` condition it discriminates on.
#:
#: This is a DERIVED property, not a phrase alternation. The previous classifier
#: matched a hand-kept list of sentences a convention might contain, which made the
#: predicate a guess about wording; this one keys on the contract's own structure —
#: how many exit-code conditions the section actually dispositions — so a
#: re-worded clause still counts and a paragraph that merely discusses exit codes
#: does not.
_CLAUSE_BULLET_RE = re.compile(r'^[ \t]*[-*][ \t]+\*\*`exit_code\s*[!=]=\s*0`', re.MULTILINE)

#: How many disposition clauses a full statement of the contract carries: exit 0
#: with success, exit 0 without it, and a non-zero exit.
FULL_CONTRACT_CLAUSE_COUNT = 3


def references_canonical(section: str) -> bool:
    """True when *section* points at the canonical standard.

    This is the covered state for every document but one. The predicate is a
    single structural fact — does the text name the canonical document? — rather
    than a judgement about how the reference is worded.
    """
    return _CANONICAL_LINK_TAIL in section


def states_full_contract(text: str) -> bool:
    """True when *text* dispositions every exit-code condition itself.

    The canonical standard is the one document for which this is the covered
    state. Anywhere else it is the duplication the single-body guard rejects —
    this predicate is what that guard counts with, so the two read the same
    property rather than each deciding for itself what a copy looks like.
    """
    return len(_CLAUSE_BULLET_RE.findall(text)) >= FULL_CONTRACT_CLAUSE_COUNT


def _fenced_line_flags(lines: list[str]) -> list[bool]:
    """Return, per line, whether it sits inside a fenced code block.

    The delimiter lines themselves are marked as fenced, so a heading can never
    be read out of a fence and an example convention shown inside a code block
    is not mistaken for the document's own.
    """
    flags: list[bool] = []
    inside = False
    for line in lines:
        if _FENCE_RE.match(line):
            flags.append(True)
            inside = not inside
            continue
        flags.append(inside)
    return flags


def _command_lines(text: str) -> list[str]:
    """Yield the logical command lines of every fenced block in *text*.

    A trailing backslash continues a command onto the next line, so the two are
    joined before any notation is read off them — otherwise an invocation whose
    notation sits on the continuation line reads as no invocation at all.
    """
    lines = text.splitlines()
    flags = _fenced_line_flags(lines)
    commands: list[str] = []
    pending = ''

    for line, fenced in zip(lines, flags, strict=True):
        if _FENCE_RE.match(line):
            if pending:
                commands.append(pending)
                pending = ''
            continue
        if not fenced:
            continue
        stripped = line.rstrip()
        if stripped.endswith('\\'):
            pending += stripped[:-1].rstrip() + ' '
            continue
        pending += stripped
        commands.append(pending)
        pending = ''

    if pending:
        commands.append(pending)
    return commands


def invoked_notations(text: str) -> frozenset[str]:
    """Every ``{bundle}:{skill}:{script}`` notation *text* actually invokes.

    A notation counts only as the executor's **first positional** — the token
    immediately following ``.plan/execute-script.py`` on a logical command line
    inside a fenced block. Reading any notation-shaped token on the line instead
    would retain a document on a notation quoted inside a ``--message`` argument
    of some other call, which is a mention and not an invocation. A bare prose
    mention outside a fenced block yields nothing for the same reason.
    """
    found: set[str] = set()
    for command in _command_lines(text):
        cursor = command.find(EXECUTOR_TOKEN)
        while cursor != -1:
            remainder = command[cursor + len(EXECUTOR_TOKEN) :].split()
            if remainder:
                match = _NOTATION_RE.fullmatch(remainder[0])
                if match is not None:
                    found.add(match.group(0))
            cursor = command.find(EXECUTOR_TOKEN, cursor + len(EXECUTOR_TOKEN))
    return frozenset(found)


def retains(notations: frozenset[str]) -> bool:
    """True when at least one notation's skill segment is not a ``manage-*`` skill.

    This is retention rule (c). It bounds the sweep to the gap the plan set out to
    close — documents invoking a non-``manage-*`` notation, which carried no
    convention at all — and drops the ``manage-*``-only documents.
    """
    return any(not notation.split(':')[1].startswith('manage-') for notation in notations)


def _convention_sections(text: str) -> list[str]:
    """The body of EVERY exit-code-convention section in *text*, in document order.

    Each section runs from its heading to the next heading at the same level or
    higher, so a nested subsection stays part of the convention it belongs to.
    """
    lines = text.splitlines()
    flags = _fenced_line_flags(lines)
    sections: list[str] = []

    for index, (line, fenced) in enumerate(zip(lines, flags, strict=True)):
        if fenced:
            continue
        heading = _CONVENTION_HEADING_RE.match(line)
        if heading is None:
            continue
        level = len(heading.group(1))
        body = [line]
        for next_line, next_fenced in zip(lines[index + 1 :], flags[index + 1 :], strict=True):
            if not next_fenced:
                boundary = _ANY_HEADING_RE.match(next_line)
                if boundary is not None and len(boundary.group(1)) <= level:
                    break
            body.append(next_line)
        sections.append('\n'.join(body))
    return sections


def classify(text: str) -> str:
    """Classify *text* as :data:`WIDENED`, :data:`NARROW`, or :data:`NONE`."""
    sections = _convention_sections(text)
    if not sections:
        return NONE
    if any(_NARROW_HEADING_RE.match(section.splitlines()[0]) for section in sections):
        return NARROW
    if any(references_canonical(s) or states_full_contract(s) for s in sections):
        return WIDENED
    return NARROW


def documents(root: Path) -> list[Path]:
    """Every skill document under *root*, in sorted order."""
    return sorted((root / 'marketplace' / 'bundles').glob('*/skills/**/*.md'))


def _read_documents(base: Path) -> list[tuple[Path, str]]:
    """Read every skill document, skipping unreadable files."""
    collected: list[tuple[Path, str]] = []
    for path in documents(base):
        if not path.is_file():
            continue
        try:
            collected.append((path, path.read_text(encoding='utf-8')))
        except (OSError, UnicodeDecodeError):
            continue
    return collected

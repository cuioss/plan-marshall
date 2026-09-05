#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Derive the executor-invoking marketplace documents and classify each one's exit-code convention.

Every ``python3 .plan/execute-script.py`` call a document issues is governed by
that document's own exit-code convention. Where the convention is scoped to
``manage-*`` calls, a document that invokes ``ci``, ``github_pr``, ``sonar``, or
any other non-``manage-*`` script leaves the reader with no rule at all — and
those scripts print ``status: error`` at exit 0 by design, so an exit-code-only
reading accepts a failed call as a usable value.

This module derives that population mechanically rather than from a hand-kept
list, and classifies each member. It is consumed by two test modules: the unit
test beside it drives fixture documents through :func:`derive` to pin each
retention and classification branch, and the population guard re-runs the same
derivation over the live tree.

Why the discrimination is mechanized rather than arithmetic
-----------------------------------------------------------

Two facts make a subtraction of counts wrong, and both are why this walk reads
each document rather than differencing two search totals:

* A document may **name** a notation in prose without invoking it. Only an
  invocation inside a fenced command block counts, so the extractor tracks
  fences and requires the executor token on the same logical command line.
* The convention-carrying set is **not** a subset of the invoking set. A
  document can carry a convention heading and invoke nothing at all, so the
  ``none`` class cannot be computed by subtracting one total from the other.

Coverage
--------

:class:`Coverage` travels with every result, per ADR-019: a class that is empty
because the walk was complete is a measurement, while a class that is empty
because files could not be read is the absence of one. A file that cannot be
decoded is named in ``unreadable`` and excluded from ``files_scanned``, so the
population can never silently shrink behind a clean-looking zero.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

#: The repository root, derived from this file's own location — this module sits
#: at ``test/plan-marshall/tools-integration-ci/``, three directories below it.
#: Derived here rather than imported from ``conftest`` so the module loads
#: standalone, which is how the session-start population header reads it.
PROJECT_ROOT = Path(__file__).resolve().parents[3]

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

#: Phrases by which a convention declares it governs more than ``manage-*``.
#: Matched against normalized text, so ``manage-*`` arrives as ``manage-``.
_WIDENING_MARKERS = (
    'not only manage-',
    'every script call',
    'every notation',
)

#: Phrases by which a convention states that a zero exit alone does not
#: establish success — the clause that makes the rule bite on a ``ci`` call.
_EXIT_ZERO_MARKERS = (
    'does not imply the operation succeeded',
    'zero exit is not evidence',
    'alone does not establish success',
    'exit 0 alone does not',
)


@dataclass(frozen=True)
class Coverage:
    """What the walk actually reached, reported beside what it found."""

    #: Markdown files under ``marketplace/`` that were read successfully.
    files_scanned: int
    #: Repo-relative paths that could not be decoded, named rather than dropped.
    unreadable: tuple[str, ...]

    @property
    def complete(self) -> bool:
        """True only when something was scanned and nothing was unreadable.

        An empty class is evidence of absence only under this conjunction; a
        consumer that reads a zero without it is reading an unmeasured tree as a
        clean one.
        """
        return self.files_scanned > 0 and not self.unreadable


@dataclass(frozen=True)
class Derivation:
    """The three disjoint classes of the retained population, plus coverage."""

    #: Documents whose convention reaches every notation AND states that a zero
    #: exit alone does not establish success.
    widened: tuple[str, ...]
    #: Documents carrying a convention heading that does not reach that far —
    #: in practice, one scoped to ``manage-*`` calls only.
    narrow: tuple[str, ...]
    #: Documents carrying no exit-code convention heading at all.
    none: tuple[str, ...]
    coverage: Coverage

    @property
    def population_size(self) -> int:
        """How many documents were retained and classified."""
        return len(self.widened) + len(self.narrow) + len(self.none)


def _normalize(text: str) -> str:
    """Fold *text* to the form the marker phrases are written against.

    Emphasis markers and backticks are removed rather than matched around,
    because a convention's wording is authored with both and neither carries
    meaning for the classification. Underscores are deliberately preserved:
    stripping them would fuse ``exit_code`` into ``exitcode``.
    """
    return re.sub(r'\s+', ' ', re.sub(r'[`*]', '', text.lower()))


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

    This is retention rule (c): a document invoking only ``manage-*`` skills is
    already covered by the narrow convention and is not part of the gap.
    """
    return any(not notation.split(':')[1].startswith('manage-') for notation in notations)


def _convention_section(text: str) -> str | None:
    """The body of *text*'s exit-code-convention section, or ``None`` if it has none.

    The section runs from its heading to the next heading at the same level or
    higher, so a nested subsection stays part of the convention it belongs to.
    """
    lines = text.splitlines()
    flags = _fenced_line_flags(lines)

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
        return '\n'.join(body)
    return None


def classify(text: str) -> str:
    """Classify *text* as :data:`WIDENED`, :data:`NARROW`, or :data:`NONE`.

    ``widened`` requires both halves: the convention must reach past ``manage-*``
    AND state that a zero exit alone does not establish success. A convention
    carrying the exit-zero clause but scoped to ``manage-*`` is ``narrow`` — it
    is precisely the shape that leaves a ``ci`` caller with no rule.
    """
    section = _convention_section(text)
    if section is None:
        return NONE
    normalized = _normalize(section)
    reaches_every_notation = any(marker in normalized for marker in _WIDENING_MARKERS)
    states_exit_zero_rule = any(marker in normalized for marker in _EXIT_ZERO_MARKERS)
    return WIDENED if reaches_every_notation and states_exit_zero_rule else NARROW


def documents(root: Path) -> list[Path]:
    """Every skill document under *root*, in sorted order.

    The walk is scoped to ``marketplace/bundles/*/skills/`` — a bundle's
    ``SKILL.md`` and its ``standards/``, ``workflow/``, and ``references/``
    bodies. That is the surface a caller reads a step off, and it is exactly the
    scope the convention sweep is authorised over; a bundle's ``agents/`` and
    ``commands/`` documents are a different category and are not part of it.
    """
    return sorted((root / 'marketplace' / 'bundles').glob('*/skills/**/*.md'))


def derive(root: Path | None = None) -> Derivation:
    """Walk the skill documents under *root* and return the classified population.

    *root* defaults to the repository root; a test supplies a ``tmp_path`` whose
    ``marketplace/bundles/`` subtree holds fixture documents. Returned paths are
    repo-relative POSIX strings, sorted, so a failure message names the same
    thing on every platform.
    """
    base = Path(root) if root is not None else PROJECT_ROOT

    buckets: dict[str, list[str]] = {WIDENED: [], NARROW: [], NONE: []}
    unreadable: list[str] = []
    files_scanned = 0

    for path in documents(base):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError):
            unreadable.append(path.relative_to(base).as_posix())
            continue
        files_scanned += 1
        if EXECUTOR_TOKEN not in text:
            continue
        if not retains(invoked_notations(text)):
            continue
        buckets[classify(text)].append(path.relative_to(base).as_posix())

    return Derivation(
        widened=tuple(buckets[WIDENED]),
        narrow=tuple(buckets[NARROW]),
        none=tuple(buckets[NONE]),
        coverage=Coverage(files_scanned=files_scanned, unreadable=tuple(unreadable)),
    )

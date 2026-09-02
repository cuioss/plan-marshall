# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared scan for DOCUMENTED EXAMPLES in a skill document.

A documented example is a promise: a reader copies it and runs it. When the
example cannot survive the validator that governs it, the failure names the
wrong culprit — the reader is sent to fix something already correct. This module
extracts the examples a document actually carries so a test can feed each one
through its governing validator instead of asserting a remembered list.

**Every entry point returns the size of the population it examined alongside its
findings, and a ZERO population is an UNRESOLVED scan, never a clean one.** A
document whose shape drifts past these extractors yields no examples, and a
caller that reads "no failures" from that is reading a scan that looked at
nothing. Callers MUST assert the published population is non-zero before acting
on the findings. This mirrors the contract of the sibling
``_push_prescription_scan``, which is the in-repo archetype for a
population-publishing document scan.

**The population is DERIVED from the document source, never declared.** A
hand-written whitelist of examples locks the defect in: an example the list
forgets is an example no test ever runs, and the list stays green while the
document rots. So the extractors below key on the SHAPE of an example — a
fenced block, a ``title:``/``steps:`` pair, a shell-quoted JSON array — and
whatever the document holds in that shape is the population.

**A commented example counts.** These documents write a TOON payload as a
comment block inside a ``bash`` fence, because the surrounding prose is telling
the reader to write that payload with an editor rather than to pipe it through
a shell. Reading only un-commented fence content would silently drop those,
which are among the most-copied examples in the corpus.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

#: The multi-target generator prescription that cannot succeed as written: ``uv``
#: is installed only into the project-local ``.pyprojectx/`` tree and is not on
#: ``PATH``, so this line exits 127 from a normal shell. Dropping the prefix does
#: not help — a bare ``python3`` form fails on the project's ``PyYAML``
#: dependency instead.
#:
#: ⛔ **Defined here ONCE, and deliberately nowhere else.** A guard cannot forbid
#: a string it must itself spell: a repository-wide sweep for this literal would
#: report every guard that names it as a prescriber of it. Centralising the
#: spelling means exactly one file in the tree contains it, so that sweep needs
#: exactly one path exemption instead of a growing list of guard modules — and
#: the exemption is a definition site, the same kind of exemption the pyprojectx
#: alias table takes.
DEFECTIVE_GENERATOR_CALL = 'uv run python marketplace/targets/generate.py'

#: The wrapper form every prescription uses instead. ``generate`` forwards
#: trailing arguments; ``generate-claude`` and ``generate-opencode`` carry their
#: own ``--target``/``--output`` pair.
WRAPPER_GENERATOR_CALL = './pw generate'

#: Fenced-code-block delimiter. The language tag is captured but never used to
#: decide whether a block holds an example: a TOON task definition appears under
#: ``toon`` fences AND, commented, under ``bash`` ones, so keying on the tag
#: would drop the second kind.
_FENCE = '```'

#: Opens a TOON/YAML-ish task definition. The key must carry a value, so a
#: ``title:`` heading a nested block does not qualify.
_TITLE_LINE = re.compile(r'^(?P<indent>[ \t]*)title:[ \t]*\S')

#: The ``steps`` list header in any of the three shapes the parser accepts:
#: bare (``steps:``), length-declared (``steps[2]:``) and uniform-array
#: (``steps[2]{target,intent}:``).
_STEPS_HEADER = re.compile(r'^[ \t]*steps(\[\d+\])?(\{[^}]*\})?:[ \t]*$')

#: A ``{token}`` placeholder. An example carrying one is a TEMPLATE: it is not
#: meant to be run verbatim, so it cannot be fed to a validator as-is. Templates
#: are reported apart rather than dropped — an unchecked example is a residual to
#: publish, not one to fold into a pass.
_PLACEHOLDER = re.compile(r'\{[A-Za-z_][A-Za-z0-9_]*\}')

#: The trailing parenthesized marker of a step row. See :func:`step_marker` for
#: why this is looser than the validator's own suffix pattern.
_STEP_MARKER = re.compile(r'\(([^()]+)\)[ \t]*$')

#: A shell-quoted JSON array of objects, as a ``batch-add`` payload is written
#: on a command line. The closing ``'`` is load-bearing: without it the
#: non-greedy body would stop at the first nested ``}]`` inside a step array.
_QUOTED_JSON_ARRAY = re.compile(r"'(\[\s*\{.*?\}\s*\])'", re.DOTALL)


@dataclass(frozen=True)
class FencedBlock:
    """One fenced code block: its language tag, body, and 1-based opening line."""

    language: str
    body: str
    line: int


@dataclass(frozen=True)
class TaskDefinitionExample:
    """One documented task-definition example extracted from a document.

    Attributes:
        text: The example as a validator can consume it — de-commented and
            dedented to column zero.
        line: 1-based line of the fence the example was found in.
        commented: Whether the example was written as a comment block inside a
            fence rather than as fence content.
        placeholders: The ``{token}`` placeholders the example carries. Non-empty
            means the example is a TEMPLATE and cannot be run verbatim.
    """

    text: str
    line: int
    commented: bool
    placeholders: tuple[str, ...]

    @property
    def is_template(self) -> bool:
        """Whether this example carries placeholders and so is not runnable as-is."""
        return bool(self.placeholders)


def iter_fenced_blocks(text: str) -> list[FencedBlock]:
    """Return every fenced code block in ``text``, in document order."""
    blocks: list[FencedBlock] = []
    language = ''
    start_line = 0
    buffer: list[str] = []
    in_fence = False
    for number, line in enumerate(text.splitlines(), start=1):
        stripped = line.lstrip()
        if stripped.startswith(_FENCE):
            if in_fence:
                blocks.append(FencedBlock(language, '\n'.join(buffer), start_line))
                buffer = []
                in_fence = False
            else:
                language = stripped[len(_FENCE):].strip()
                start_line = number
                in_fence = True
            continue
        if in_fence:
            buffer.append(line)
    return blocks


def decomment(body: str) -> str:
    """Return only the comment lines of ``body``, with their ``#`` marker removed.

    Non-comment lines become blank rather than disappearing, so a comment block
    that sits between two shell commands does not silently merge with a second,
    unrelated comment block further down the same fence.
    """
    out: list[str] = []
    for line in body.splitlines():
        stripped = line.lstrip()
        if not stripped.startswith('#'):
            out.append('')
            continue
        without_marker = stripped[1:]
        out.append(without_marker[1:] if without_marker.startswith(' ') else without_marker)
    return '\n'.join(out)


def _extract_task_definition(text: str) -> str | None:
    """Return the task definition inside ``text``, dedented, or ``None``.

    A task definition is recognised by the pair its validator requires: a
    ``title:`` carrying a value, and a ``steps`` list header in any accepted
    shape. The definition is taken to run from the ``title:`` line to the end of
    the text and is dedented by that line's indent, which is what lifts a
    definition written as an indented comment block back to column zero.
    """
    lines = text.splitlines()
    for index, line in enumerate(lines):
        match = _TITLE_LINE.match(line)
        if match is None:
            continue
        indent = len(match.group('indent'))
        tail = [row[indent:] if row[:indent].strip() == '' else row.lstrip() for row in lines[index:]]
        candidate = '\n'.join(tail).rstrip()
        if any(_STEPS_HEADER.match(row) for row in tail):
            return candidate + '\n'
        return None
    return None


def scan_task_definition_examples(text: str) -> tuple[list[TaskDefinitionExample], int]:
    """Return ``(task-definition examples, fenced blocks examined)``.

    Each fenced block is read twice — as its own content, and as the payload of
    whatever comment block it carries — because both spellings of a documented
    task definition occur in this corpus. An example found both ways is emitted
    once.

    The second element is the published population. Callers MUST fail a scan
    that examined zero blocks rather than reporting it clean.
    """
    blocks = iter_fenced_blocks(text)
    examples: list[TaskDefinitionExample] = []
    seen: set[str] = set()
    for block in blocks:
        for commented, source in ((False, block.body), (True, decomment(block.body))):
            definition = _extract_task_definition(source)
            if definition is None or definition in seen:
                continue
            seen.add(definition)
            examples.append(
                TaskDefinitionExample(
                    text=definition,
                    line=block.line,
                    commented=commented,
                    placeholders=tuple(sorted(set(_PLACEHOLDER.findall(definition)))),
                )
            )
    return examples, len(blocks)


def step_rows(example_text: str) -> list[str]:
    """Return the ``steps`` list rows of one example, item text only.

    Scoped to the rows beneath the ``steps`` header rather than to every ``- ``
    row in the example: a ``skills`` item carries no intent marker by contract,
    so sweeping every list row would report the contract's own shape as a defect.
    """
    rows: list[str] = []
    collecting = False
    for line in example_text.splitlines():
        if _STEPS_HEADER.match(line):
            collecting = True
            continue
        if not collecting:
            continue
        stripped = line.strip()
        if stripped.startswith('- '):
            rows.append(stripped[2:].strip())
        elif stripped:
            collecting = False
    return rows


def step_marker(row: str) -> str | None:
    """Return the trailing ``(...)`` marker text of a step row, or ``None``.

    Deliberately LOOSER than the validator's own suffix pattern, which requires
    the marker to spell a lowercase intent from the closed vocabulary. A
    documented TEMPLATE writes the intent as a ``{placeholder}``, which no closed
    vocabulary can contain, so the strict pattern would report the template's
    intended shape as a missing marker. Callers apply the strict pattern to any
    marker this one returns that carries no placeholder — the loose read locates
    the marker; it does not decide whether the marker is valid.
    """
    match = _STEP_MARKER.search(row)
    return match.group(1) if match else None


def scan_json_array_examples(text: str) -> tuple[list[str], int]:
    """Return ``(shell-quoted JSON array literals, fenced blocks examined)``.

    Only arrays whose first element is an object are collected — that is the
    ``batch-add`` payload shape. The second element is the published population,
    and a zero means the scan resolved nothing.
    """
    blocks = iter_fenced_blocks(text)
    literals: list[str] = []
    for block in blocks:
        literals.extend(match.group(1) for match in _QUOTED_JSON_ARRAY.finditer(block.body))
    return literals, len(blocks)


def scan_shell_prescriptions(text: str) -> tuple[list[str], int]:
    """Return ``(prescribed shell command lines, fenced lines examined)``.

    A prescription is a command a reader would run, so comment lines and blanks
    are excluded: a comment naming a command in order to say it must NOT be run
    is the opposite of a prescription. The second element is the published
    population.
    """
    lines: list[str] = []
    commands: list[str] = []
    for block in iter_fenced_blocks(text):
        for line in block.body.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            lines.append(stripped)
            if not stripped.startswith('#'):
                commands.append(stripped)
    return commands, len(lines)

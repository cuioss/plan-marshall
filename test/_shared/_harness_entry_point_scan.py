# SPDX-License-Identifier: FSL-1.1-ALv2
"""Readers for a command that exists once per harness-local entry point.

A command every harness must carry is written three times — a Claude skill, an
OpenCode command and an Antigravity skill — and the three drift apart unless a
test holds them together. That test needs the same primitives each time: the
frontmatter of a document, the command lines of its ``bash`` fences, its
post-run blockquote, and the bodies of its numbered steps.

Every reader here is a PURE function over document text, which is what lets a
matched control plant a violation in a temporary tree and read it back through
the same code path the real entry points go through, instead of asserting a
remembered shape. The module carries no knowledge of a particular command: the
command name, the entry-point paths and the expected sequence belong to the test
that uses these readers.
"""

from __future__ import annotations

import re

from _documented_example_scan import iter_fenced_blocks

#: A gate on a target's own ``status`` rather than on its ``cache_status``.
BARE_STATUS_GATE = re.compile(r'(?<!cache_)status: success')

#: A ``./pw`` invocation at any shell command boundary: line start, or after a
#: command separator. A prefix test alone would pass ``cd repo && ./pw …``.
DIRECT_WRAPPER_CALL = re.compile(r'(?:^|[;&|(]\s*)\./pw(?:\s|$)')

#: Opens a numbered step, whichever numbering style the document uses.
_STEP_OPENER = re.compile(r'^### Step (?P<heading>\d+):|^(?P<numbered>\d+)\. ')

#: Where a numbered step ends: the next heading, numbered step or blockquote.
_STEP_END = re.compile(r'^(?:#{2,3} |\d+\. |> )')


def frontmatter(text: str) -> dict[str, str]:
    """The ``key: value`` pairs of the document's leading ``---`` block."""
    lines = text.splitlines()
    closing = lines.index('---', 1)
    pairs = (line.partition(':') for line in lines[1:closing])
    return {key.strip(): value.strip() for key, _, value in pairs}


def prescribed_commands(text: str) -> list[str]:
    """The command lines of every ``bash`` fence, in document order.

    Only ``bash`` fences are read: a ``text`` fence carries a diagram or a usage
    example, which is not a command the entry point runs.
    """
    return [
        line.strip()
        for block in iter_fenced_blocks(text)
        if block.language == 'bash'
        for line in block.body.splitlines()
        if line.strip()
    ]


def post_run_block(text: str) -> str:
    """The document's blockquote — the post-run instruction block — verbatim."""
    return '\n'.join(line for line in text.splitlines() if line.startswith('>'))


def collapsed(text: str) -> str:
    """``text`` with emphasis markers dropped and every whitespace run collapsed."""
    return re.sub(r'\s+', ' ', text.replace('*', ''))


def step_blocks(text: str) -> dict[int, str]:
    """The body of every numbered step, keyed by its number."""
    blocks: dict[int, str] = {}
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        opener = _STEP_OPENER.match(lines[index])
        if opener is None:
            index += 1
            continue
        number = int(opener.group('heading') or opener.group('numbered'))
        end = index + 1
        while end < len(lines) and _STEP_END.match(lines[end]) is None:
            end += 1
        blocks.setdefault(number, '\n'.join(lines[index:end]))
        index = end
    return blocks


def swap_lines(text: str, first: str, second: str) -> str:
    """``text`` with the lines carrying ``first`` and ``second`` exchanged.

    Raises ``AssertionError`` when either line is absent: a control that silently
    planted nothing would assert the clean case twice.
    """
    lines = text.splitlines()
    first_at = next((index for index, line in enumerate(lines) if line.strip() == first), None)
    second_at = next((index for index, line in enumerate(lines) if line.strip() == second), None)
    assert first_at is not None, f'the line to exchange is absent: {first!r}'
    assert second_at is not None, f'the line to exchange is absent: {second!r}'
    lines[first_at], lines[second_at] = lines[second_at], lines[first_at]
    return '\n'.join(lines)


def replace_nth(text: str, needle: str, replacement: str, occurrence: int) -> str:
    """``text`` with the ``occurrence``-th (1-based) ``needle`` replaced.

    Raises ``AssertionError`` when the occurrence is absent, so a control that
    meant to plant a violation in the third site cannot silently plant it in the
    first.
    """
    start = -1
    for _ in range(occurrence):
        start = text.find(needle, start + 1)
        assert start != -1, f'occurrence {occurrence} of {needle!r} is absent'
    return text[:start] + replacement + text[start + len(needle) :]

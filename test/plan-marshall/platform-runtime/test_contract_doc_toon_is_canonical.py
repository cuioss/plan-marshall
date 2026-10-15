#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Pin the platform-runtime standards' TOON examples to the real serializer.

Every documented payload in these standards is a claim about what the runtime
emits, and until now nothing checked it. That gap is not theoretical: the
``project install-hook`` examples were once written by hand and documented an
inline ``key[N]: a,b,c`` list the serializer has never produced for a list of
strings, alongside a render-event label that does not exist. The quality gate,
plugin-doctor and the whole test suite passed over it, because a false sentence
in a document type-checks and lints exactly like a true one.

A round-trip is what closes it. ``serialize_toon`` has one canonical rendering
per value, so a block that does NOT survive ``serialize_toon(parse_toon(block))``
is in a shape the serializer could never emit. That direction is sound and is
what this test enforces, and the expectation comes from the serializer the
production code calls, never from the document.

**The converse does not hold, and the limit is wider than "shape vs content".**
A surviving block is the canonical rendering of SOME dict — not necessarily of
the dict this operation emits. A mutation battery against real block shapes found
it catches every indentation, separator, quoting, count-header, dropped-row,
blank-line and duplicate-key defect, and misses at least three that are shape
rather than content: keys in the wrong ORDER (the serializer emits
dict-insertion order, so a reordered block is unemittable yet passes), a renamed
uniform-array header field, and a type flip such as ``false`` to ``"false"``. It
is blind to wrong field names and wrong values by design.

So this cannot replace reading a payload against its producer — the install-hook
captures in ``contract.md`` were verified by reproduction, and that is what a
content claim costs. What it does buy is that the class of
transcription-invented SYNTAX can no longer land.
"""

import pathlib
import re

import pytest

# conftest.py sets up PYTHONPATH so imports resolve without manual sys.path work.
from toon_parser import parse_toon, serialize_toon

from conftest import get_skill_dir

_STANDARDS = get_skill_dir('plan-marshall', 'platform-runtime') / 'standards'


def _toon_blocks(doc: pathlib.Path) -> list[tuple[int, str]]:
    """Return EVERY fenced ``toon`` block in *doc* as ``(line_number, body)``.

    Nothing is exempted. An earlier version skipped blocks containing
    ``<angle-bracket>`` placeholders on the theory that a template is not a
    payload, and that exemption immediately hid a real defect: an ``io_error``
    example whose ``message`` was unquoted where the serializer quotes it. A
    placeholder sits in a VALUE, and a value with a placeholder still renders
    the way the serializer renders values — so a template can be canonical, and
    every one in these standards is. An exemption that is not needed is only a
    place for defects to hide.
    """
    blocks: list[tuple[int, str]] = []
    body: list[str] | None = None
    start = 0
    for lineno, line in enumerate(doc.read_text(encoding='utf-8').splitlines(), 1):
        if line.strip() == '```toon' and body is None:
            body, start = [], lineno
        elif line.strip() == '```' and body is not None:
            blocks.append((start, '\n'.join(body)))
            body = None
        elif body is not None:
            body.append(line)
    if body is not None:
        raise AssertionError(
            f'{doc}: ```toon fence opened at line {start} is never closed. '
            'The scan would silently DROP this block, and the parametrized test '
            'would still pass on every other block — so a malformed documented '
            'payload would read as verified. Close the fence.'
        )
    return blocks


def _cases() -> list[tuple[str, int, str]]:
    cases = [
        (doc.name, lineno, block) for doc in sorted(_STANDARDS.glob('*.md')) for lineno, block in _toon_blocks(doc)
    ]
    assert cases, f'no TOON blocks found under {_STANDARDS} — the scan is broken'
    return cases


#: Collected once at import. The scan walks every standards document, so calling
#: ``_cases()`` a second time to build the ids would read the whole directory
#: again — and, worse, would let the parameter list and the id list come from two
#: separate scans that could disagree if a file changed between them.
_CASES = _cases()


@pytest.mark.parametrize(
    ('doc_name', 'lineno', 'block'),
    _CASES,
    ids=[f'{doc}-L{line}' for doc, line, _ in _CASES],
)
def test_documented_toon_block_is_what_the_serializer_emits(doc_name: str, lineno: int, block: str) -> None:
    """Each documented payload round-trips through the canonical serializer unchanged."""
    assert serialize_toon(parse_toon(block)) == block, (
        f'{doc_name}:{lineno} is not in the shape serialize_toon emits — '
        f'it documents a payload the runtime cannot produce'
    )


# =============================================================================
# Corrected runtime-info examples (harness-stamp deliverable)
# =============================================================================
#
# The round-trip test above holds every block to the serializer SHAPE, but a
# shape check cannot catch a dropped field or a self-contradictory example:
# both still round-trip. These pins assert the corrected CONTENT — the
# `transcripts` capability flag both success examples must carry, and an
# unknown-target name outside the registered set.

_CONTRACT_DOC = _STANDARDS / 'contract.md'

_REGISTERED_TARGETS = frozenset({'antigravity', 'claude', 'opencode'})


def _section_span(marker: str) -> tuple[int, int]:
    """Return the 1-based (start, end) line span of one `### ` section."""
    lines = _CONTRACT_DOC.read_text(encoding='utf-8').splitlines()
    start = next(i for i, line in enumerate(lines, 1) if line.strip() == marker)
    end = next(
        (i for i, line in enumerate(lines, 1) if i > start and line.startswith('### ')),
        len(lines) + 1,
    )
    return start, end


def _section_blocks(marker: str, *needles: str) -> list[str]:
    """Every toon block in one section whose body contains all of `needles`."""
    start, end = _section_span(marker)
    return [
        body
        for lineno, body in _toon_blocks(_CONTRACT_DOC)
        if start <= lineno < end and all(needle in body for needle in needles)
    ]


def test_runtime_info_success_examples_carry_transcripts() -> None:
    """Both success examples carry the `transcripts` capability flag."""
    blocks = _section_blocks('### `runtime-info`', 'operation: runtime-info', 'status: success')

    assert len(blocks) == 2, (
        f'expected the two runtime-info success examples, found {len(blocks)} — '
        'the section changed shape and this pin no longer covers it'
    )
    for body in blocks:
        assert 'transcripts: full' in body, (
            'a runtime-info success example dropped the transcripts flag — '
            'the client.toon pre-flight artifact cannot tell a measured run from an unmeasured one'
        )


def test_runtime_info_unknown_target_example_names_no_registered_target() -> None:
    """The error example quotes a target outside the registry, never a real one."""
    blocks = _section_blocks('### `runtime-info`', 'operation: runtime-info', 'error: unknown_target')

    assert len(blocks) == 1, f'expected the one runtime-info unknown-target example, found {len(blocks)}'
    match = re.search(r"runtime\.target '([^']+)'", blocks[0])
    assert match is not None, 'the error message names no quoted runtime.target value'
    assert match.group(1) not in _REGISTERED_TARGETS, (
        f'{match.group(1)!r} is a registered target — the example contradicts its own unknown_target error'
    )
    assert 'valid targets are: antigravity, claude, opencode' in blocks[0]


def test_health_check_permissions_detail_names_the_resolved_file() -> None:
    """The permissions detail names the file it resolved, never a hardcoded literal."""
    text = _CONTRACT_DOC.read_text(encoding='utf-8')

    assert '_claude_project_settings_read_path()' in text
    assert 'never a hardcoded literal' in text
    assert 'settings.json present;' in text

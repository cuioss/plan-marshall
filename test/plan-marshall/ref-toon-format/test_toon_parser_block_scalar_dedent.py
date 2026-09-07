#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""A block scalar's body is dedented by what it carries, never past it.

``block_scalar_body_continues`` admits every line indented deeper than the
``key: |`` header — one space past it included. ``_parse_multiline_value`` then
has to remove the emitter's structural prefix, which is two spaces past the
header. Those two are not the same number, and a fixed two-space slice of a
one-space-indented line does not merely mis-indent it: it cuts into the payload
and deletes characters, silently and without any error.

That is the parser's two halves disagreeing about the block's extent, which is
the failure mode the exported predicate exists to prevent. It is unreachable
through this repository's own emitter, whose body is always exactly two spaces
past the header — and reachable through every document the transport did not
write: a hand-authored TOON fixture, a skill body's worked example, an
agent-composed envelope. Those are also where verbatim carriage is the whole
point, since what rides a block scalar is opaque foreign text.

The cases are a matched set. The shallow arms pin that no payload character is
lost; the canonical and deeper arms pin that the ordinary dedent did not move,
without which "never cut into the payload" would be satisfiable by a parser that
had stopped dedenting at all and returned the structural prefix as content.
"""

from __future__ import annotations

import pytest
from toon_parser import BlockScalar, parse_toon, serialize_toon


@pytest.mark.parametrize(
    'body_indent,expected,reason',
    [
        (' ', 'value', 'one space past the header — admitted by the predicate, shallower than the emitter writes'),
        ('  ', 'value', 'the canonical emitter indent, dedented exactly'),
        ('   ', ' value', 'deeper than the emitter writes, so the surplus space is payload'),
        ('      ', '    value', 'four surplus spaces are four spaces of payload'),
    ],
)
def test_a_body_line_keeps_every_payload_character_at_any_admitted_indent(body_indent, expected, reason):
    """No admitted indentation costs the payload a character.

    ``parse_toon('note: |\\n value\\n')`` returned ``'alue'`` before the dedent
    was clamped: the slice ran two columns into a line that carried one, so the
    payload's first character went with the indentation.
    """
    assert parse_toon(f'note: |\n{body_indent}value\n') == {'note': expected}, reason


@pytest.mark.parametrize(
    'payload,reason',
    [
        ('ab', 'two characters — the shortest line the fixed slice could truncate'),
        ('a', 'one character — the length the old length-guard happened to handle'),
        ('status: blocked', 'a line that reads as a TOON key/value pair must stay opaque text'),
    ],
)
def test_a_one_space_body_line_is_carried_whole_whatever_its_length(payload, reason):
    """The old guard branched on line LENGTH, so the defect only bit longer lines.

    A single-character payload took the ``line.strip()`` fallback and came back
    intact, which is why the corruption never showed up in a short example.
    """
    assert parse_toon(f'note: |\n {payload}\n')['note'] == payload, reason


def test_a_nested_block_scalar_body_one_space_past_its_header_is_carried_whole():
    """The clamp is relative to the header's own indent, not to column zero.

    A nested header sits at indent 2, so its shallowest admitted body line sits at
    indent 3 — and a fixed ``header + 2`` slice cut a character off that line just
    as it did at the top level.
    """
    parsed = parse_toon('outer:\n  note: |\n   value\n')

    assert parsed == {'outer': {'note': 'value'}}


def test_a_shallow_body_still_closes_the_block_at_the_header_indent():
    """MATCHED CONTROL — clamping the dedent did not widen the block's extent.

    The shallow line is body because it is deeper than the header; the following
    line at the header's own indent is a sibling key. A fix that had loosened the
    predicate instead of the slice would swallow that key into the prose.
    """
    parsed = parse_toon('note: |\n one\nafter: yes\n')

    assert parsed['note'] == 'one'
    assert parsed['after'] == 'yes'


def test_the_emitter_round_trip_is_unchanged_by_the_clamp():
    """MATCHED CONTROL — documents this transport wrote still round-trip verbatim.

    Every body line the emitter writes sits at exactly ``header + 2``, so the clamp
    is inert for them and the payload's own leading spaces remain payload. Without
    this arm, a dedent that had been weakened to strip only the whitespace each
    line happens to carry would satisfy every case above while flattening the
    body's own indentation.
    """
    body = '  leading-space line\nplain line\n\n    deep\ntail'

    reparsed = parse_toon(serialize_toon({'note': BlockScalar(body)}) + '\n')

    assert reparsed['note'] == body

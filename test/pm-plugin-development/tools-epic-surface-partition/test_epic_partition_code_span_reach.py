#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for how far a markdown code-span delimiter REACHES in a spec.

Drives the underscore-prefixed helpers directly by inserting the scripts dir on
``sys.path`` (the canonical scaffolding pattern).

The reproduction guard discards a sweep marker lying wholly inside a code span,
so every question about a span's REACH is a question about whether a real
declaration survives. Two reaches exist and they are decided by POSITION:

- an INLINE span is bounded by the blank line, so a stray backtick costs at most
  its own paragraph;
- a FENCED block runs to its closing delimiter however many paragraphs later,
  and to the end of the document when it has none.

Each bound carries a control that FAILS when it is removed and a matched partner
that fails when it is applied to the other form, so neither can be deleted nor
over-applied behind a green suite. The phrasing cross-product — every sweep
alternative in every reproduction form — lives in ``test_epic_partition.py``;
this module holds one phrasing and varies the DELIMITER instead.

Every body here is a literal built in the test; no file, corpus or tree is read.
"""

from __future__ import annotations

import sys

from conftest import get_scripts_dir

SCRIPTS_DIR = get_scripts_dir('pm-plugin-development', 'tools-epic-surface-partition')
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import _epic_partition as partition_mod  # noqa: E402


# --- scaffolding -------------------------------------------------------------

#: One settled sweep phrasing. Which one is immaterial here — the guard is
#: applied at the single point every alternative passes through, so this cluster
#: varies the delimiter around a fixed phrasing rather than the phrasing.
DECLARATION = "this plan's surface is the test tree entire"

#: The claim line every body carries, so each body is a spec that resolves a
#: surface rather than a bare paragraph.
CLAIM_LINE = '- OBSERVED: test/beta/ — this plan\'s own mirror\n'


def spec(body: str) -> str:
    """A minimal spec whose Expected Surface section carries ``body``."""
    return f'# PLAN-260\n\n## Expected Surface\n\n{CLAIM_LINE}\n{body}'


def declaring(body: str) -> str:
    """A spec whose ``body`` is followed by an unreproduced declaration."""
    return f'{spec(body)}\n- OBSERVED: test/beta/ — ⛔ **the whole tree.** {DECLARATION}\n'


def test_the_fixture_phrasing_is_a_real_marker() -> None:
    """Guards every body below against decaying into a spec with no marker at all.

    Without this, a phrasing that stopped matching the marker would make every
    ``not is_sweep_declaration`` row below pass for the wrong reason — the guard
    would be measured against a body carrying nothing to guard.
    """
    assert partition_mod.is_sweep_declaration(declaring(''))


# --- the inline bound: a stray backtick costs one paragraph ------------------

#: Two stray SINGLE backticks in different paragraphs, a declaration between
#: them. The mutant this discriminates is the paragraph bound REMOVED: pairing
#: across the whole document reads the two strays as one span and swallows the
#: declaration.
_STRAY_INLINE_MARKS_BODY = (
    '# PLAN-261\n\n## Expected Surface\n\n'
    'The sibling row opens `\n'
    '\n'
    f'- OBSERVED: test/beta/ — ⛔ **the whole tree.** {DECLARATION}\n'
    '\n'
    'and a later row closes `\n'
)

#: The same shape with TRIPLE runs, both sitting MID-LINE. Length is not what
#: makes a fence, so these are inline spans and must be bounded exactly as the
#: single marks above are. The mutant this discriminates is the run-length split:
#: three-or-more treated as a fence wherever it sits, which hands
#: end-of-document reach to a delimiter typed in running prose.
_STRAY_MIDLINE_RUNS_BODY = (
    '# PLAN-262\n\n## Expected Surface\n\n'
    'A fence is written ``` in running prose.\n'
    '\n'
    f'- OBSERVED: test/beta/ — ⛔ **the whole tree.** {DECLARATION}\n'
    '\n'
    'and a later row writes ``` again.\n'
)


def test_stray_backticks_in_two_paragraphs_do_not_pair_across_a_declaration() -> None:
    """Inline pairing is bounded by the blank line, so a stray costs one paragraph.

    KILLS the mutant that removes the paragraph bound from the inline scan. With
    the bound gone the two strays pair into one span covering the declaration,
    and a real sweep is silently demoted to an ordinary slice. The count pins
    that the fixture really carries the second mark such a mutant would pair with.
    """
    assert _STRAY_INLINE_MARKS_BODY.count('`') == 2
    assert partition_mod.is_sweep_declaration(_STRAY_INLINE_MARKS_BODY)


def test_a_mid_line_triple_run_is_inline_and_cannot_reach_past_its_paragraph() -> None:
    """A run's LENGTH does not make it a fence; its POSITION does.

    KILLS the mutant that splits inline from fenced on run length. Both runs here
    sit mid-line, so both are inline spans bounded by their own paragraphs. Under
    a length-based split they are fences that pair across the document and
    swallow the declaration between them — the identical failure the quotation
    form's paragraph bound already stops, reintroduced through the code-span form.
    """
    assert _STRAY_MIDLINE_RUNS_BODY.count('```') == 2
    assert partition_mod.is_sweep_declaration(_STRAY_MIDLINE_RUNS_BODY)


def test_an_inline_span_still_contains_a_reproduction_in_its_own_paragraph() -> None:
    """The bound's matched partner: bounding is not disabling.

    Without this, a mutant that skipped every inline run outright — never
    pairing, never containing — would pass both bound controls above while the
    inline form guarded nothing.
    """
    body = spec(f'One row reads ``{DECLARATION}`` and is a **genuine claim**.\n')

    assert not partition_mod.is_sweep_declaration(body)


# --- the fenced reach: a block spans paragraphs -------------------------------

#: A reproduction inside a fenced block that CONTAINS A BLANK LINE. The mutant
#: this discriminates is the paragraph bound applied to EVERY run: the block is
#: then cut at the blank line, the reproduction falls outside every span, and the
#: analysing plan is read as declaring the sweep it is quoting.
_FENCED_ACROSS_A_BLANK_LINE_BODY = spec(
    'PLAN-240 declares:\n\n'
    '```text\n'
    'the first line of the quoted block\n'
    '\n'
    f'{DECLARATION}\n'
    '```\n'
)


def test_a_fenced_block_contains_a_reproduction_across_a_blank_line() -> None:
    """A fence's reach is its closing delimiter, not the next blank line.

    KILLS the mutant that applies the paragraph bound to every backtick run. A
    fenced block legitimately spans paragraphs, so bounding it at the blank line
    leaves the second half of a quoted block uncontained and reads the quoting
    plan as declaring the sweep. The blank-line assertion pins that the fixture
    really straddles the bound such a mutant would impose.
    """
    assert '\n\n' in _FENCED_ACROSS_A_BLANK_LINE_BODY.split('```text\n')[1].split('\n```')[0]
    assert not partition_mod.is_sweep_declaration(_FENCED_ACROSS_A_BLANK_LINE_BODY)


def test_an_unterminated_fence_reaches_the_end_of_the_document() -> None:
    """The one delimiter whose reach is not bounded by its paragraph.

    Markdown's own reading, shared with ``epic_spec_parser._fenced_mask``: a
    block with no closing delimiter runs to the end of the document. Pinned
    rather than left implicit because it is the single exception to the
    stray-delimiter-costs-one-paragraph rule the rest of this module asserts, and
    the standard states it as such.
    """
    body = f'# PLAN-263\n\n## Expected Surface\n\n{CLAIM_LINE}\n```text\n{DECLARATION}\n'

    assert not partition_mod.is_sweep_declaration(body)


# --- the fence-delimiter clauses ----------------------------------------------

#: An opening delimiter whose run is FOUR backticks, with a bare three-backtick
#: line inside the block. A length-blind close ends the block there, leaving the
#: reproduction that follows uncontained.
_FENCE_CLOSED_ONLY_BY_AN_EQUAL_OR_LONGER_RUN_BODY = spec(
    'PLAN-240 declares:\n\n'
    '````text\n'
    '```\n'
    f'{DECLARATION}\n'
    '````\n'
)

#: An opening delimiter of three backticks whose block contains a delimiter line
#: CARRYING AN INFO STRING. Only the opening fence may carry one, so that line is
#: body text; an info-blind close ends the block there.
_FENCE_NOT_CLOSED_BY_A_DELIMITER_WITH_INFO_BODY = spec(
    'PLAN-240 declares:\n\n'
    '```text\n'
    '```python\n'
    f'{DECLARATION}\n'
    '```\n'
)

#: A block opened by three backticks and closed by FOUR. CommonMark closes on a
#: run AT LEAST AS LONG as the opener, so this block is closed and its contents
#: contained.
_FENCE_CLOSED_BY_A_LONGER_RUN_BODY = spec(
    'PLAN-240 declares:\n\n'
    '```text\n'
    f'{DECLARATION}\n'
    '````\n'
)

#: A PARAGRAPH that opens with the fence marker and then quotes inline code. A
#: backtick fence's info string may not carry a backtick, so this is not an
#: opening delimiter at all — reading it as one masks the rest of the document.
_SENTENCE_OPENING_WITH_THE_FENCE_MARKER_BODY = (
    '# PLAN-264\n\n## Expected Surface\n\n'
    f'{CLAIM_LINE}'
    '\n``` opens a block, as `test/beta/` shows.\n'
    '\n'
    f'- OBSERVED: test/beta/ — ⛔ **the whole tree.** {DECLARATION}\n'
)


def test_a_fenced_block_is_not_closed_by_a_shorter_run() -> None:
    """The opening run's LENGTH survives to the close test.

    A length-blind close ends a four-backtick block at the first three-backtick
    example inside it, after which every reproduction below that example is
    uncontained and the quoting plan reads as a sweep.
    """
    assert not partition_mod.is_sweep_declaration(
        _FENCE_CLOSED_ONLY_BY_AN_EQUAL_OR_LONGER_RUN_BODY
    )


def test_a_fenced_block_is_not_closed_by_a_delimiter_carrying_an_info_string() -> None:
    """Only the OPENING delimiter may carry an info string.

    A delimiter with one is body text, never a close. Dropping the clause ends
    the block at the first ```` ```lang ```` line inside it and leaves what
    follows uncontained.
    """
    assert not partition_mod.is_sweep_declaration(
        _FENCE_NOT_CLOSED_BY_A_DELIMITER_WITH_INFO_BODY
    )


def test_a_fenced_block_is_closed_by_a_longer_run() -> None:
    """The matched partner of the length clause: at-least-as-long, not exactly.

    Requiring an EXACT length match leaves this block unterminated to the end of
    the document. It would still contain the reproduction, so the failure is
    invisible from that body alone — it surfaces as everything AFTER the block
    being masked too, which the second assertion pins by keeping a declaration
    there that must still fire.
    """
    assert not partition_mod.is_sweep_declaration(_FENCE_CLOSED_BY_A_LONGER_RUN_BODY)
    assert partition_mod.is_sweep_declaration(
        f'{_FENCE_CLOSED_BY_A_LONGER_RUN_BODY}\n'
        f'- OBSERVED: test/beta/ — ⛔ **the whole tree.** {DECLARATION}\n'
    )


def test_a_sentence_opening_with_the_fence_marker_opens_no_block() -> None:
    """A backtick fence's info string may not carry a backtick.

    The shape a sentence takes when it begins with the fence marker and then
    quotes inline code. Reading it as an opening delimiter masks every paragraph
    after it, including the declaration this spec makes in its own right.
    """
    assert partition_mod.is_sweep_declaration(_SENTENCE_OPENING_WITH_THE_FENCE_MARKER_BODY)


def test_an_indented_delimiter_past_the_third_column_opens_no_block() -> None:
    """CommonMark bounds a fence's leading indentation to three spaces.

    A fourth column is an indented code block's content rather than a fence, so
    the run is read inline and bounded by its paragraph. Without the bound the
    line opens a block that masks the declaration below it.
    """
    body = (
        '# PLAN-265\n\n## Expected Surface\n\n'
        f'{CLAIM_LINE}'
        '\n    ```\n'
        '\n'
        f'- OBSERVED: test/beta/ — ⛔ **the whole tree.** {DECLARATION}\n'
    )

    assert partition_mod.is_sweep_declaration(body)


# --- the two forms do not leak into each other --------------------------------


def test_an_inline_run_inside_a_fence_does_not_pair_with_one_outside_it() -> None:
    """Fenced blocks are resolved FIRST, and the inline scan runs over the gaps.

    KILLS the mutant that drops the ordering and runs the inline scan over the
    whole document. The block here carries a BLANK LINE, so its own delimiters
    cannot self-pair inline and the whole-document scan walks straight past both;
    the lone mark left inside the block then pairs with the lone mark in the
    running prose after it, and the span between them swallows the declaration.
    Under the shipped ordering the block is taken as a fenced span first and its
    inner mark is never offered to the inline scan at all.

    ⛔ A block WITHOUT that blank line does not discriminate: the whole-document
    scan reaches the opening delimiter run first, pairs it with the closing run,
    and skips the index past the inner mark, so both readings agree and the
    control passes green against the very mutant it names. The two assertions pin
    what makes the fixture diverge — the blank line the fence straddles, and the
    two lone marks left for the mutant to pair across once the delimiters are
    discounted.
    """
    body = (
        '# PLAN-266\n\n## Expected Surface\n\n'
        f'{CLAIM_LINE}'
        '\nPLAN-240 declares:\n\n'
        '```text\n'
        'the first line of the quoted block\n'
        '\n'
        'a lone ` inside the block\n'
        '```\n'
        f'- OBSERVED: test/beta/ — ⛔ **the whole tree.** {DECLARATION}\n'
        'and a later row closes `\n'
    )

    assert '\n\n' in body.split('```text\n')[1].split('\n```')[0]
    assert body.replace('```', '').count('`') == 2
    assert partition_mod.is_sweep_declaration(body)

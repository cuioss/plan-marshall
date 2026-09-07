#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Population-derived contract test: every counted candidate list has a check.

The self-review surfacer sums every ``CANDIDATE_LISTS`` entry whose ``in_total``
flag is set into ``counts.total`` — the number the terminal verdict reports as
``"{N} candidates examined"`` and the Step 1b dispatch gate keys off. A summed
entry that no cognitive check adjudicates inflates that examined-count without
being examined: volume-read-as-coverage, reproduced inside the very contract
built to detect it (the pre-fix ``duplicate_claimable_keys`` /
``discard_without_report`` gap).

This test ties registry membership to check coverage by an invariant. The
population is DERIVED from the registry (``in_total`` entries), never a
hand-copied list, and its size is published so a pass over an empty population —
the vacuous-confident-zero archetype this whole surface is about — is impossible.
For each counted entry it requires a backtick-quoted reference to the entry's key
inside the workflow doc's NUMBERED-CHECK block (not merely somewhere in the
Step-3 region): a key that appears only in the region's explanatory prose — the
preamble, the class-closure obligation, the present-state grounding precondition,
a worked example, or a paragraph interleaved BETWEEN two numbered entries — does
NOT count as a consuming check, because none of those adjudicates the candidate.
A counted entry with no numbered check that references it fails here rather than
silently shipping.
"""

import re

import pytest
from _self_review_patterns import CANDIDATE_LISTS, CandidateList

from conftest import MARKETPLACE_ROOT

_WORKFLOW_DOC = (
    MARKETPLACE_ROOT
    / 'plan-marshall'
    / 'skills'
    / 'phase-6-finalize'
    / 'workflow'
    / 'pre-submission-self-review.md'
)

#: The Step-3 checks region boundaries. Coverage is asserted ONLY inside the
#: region where the numbered cognitive checks live, so a candidate-list key that
#: appears in an Inputs table or an output-schema block elsewhere in the doc is
#: never mistaken for a consuming check.
_CHECKS_REGION_START = '### Step 3: Apply'
_CHECKS_REGION_END = '### Dispatched-envelope output'

#: A numbered cognitive-check entry opener — ``1. `` / ``17. `` at column zero.
#: The numbered checks are the LAST thing in the Step-3 region before the
#: dispatched-envelope output, after the preamble and every ``####`` subsection,
#: so the block from the first such line to the region end is exactly the
#: numbered checks. This is the discriminator that keeps a key mentioned only in
#: explanatory prose (which precedes the first numbered check) from reading as
#: covered.
#:
#: That structural assumption is no longer only a comment: it is asserted against
#: the REAL document by
#: ``test_numbered_check_block_is_one_contiguous_run_with_no_heading_inside``. If
#: the doc grows a ``####`` subsection after the checks, or an ordered list in the
#: preamble whose first item precedes the real checks, the block silently stops
#: being "exactly the numbered checks" and every coverage verdict above is drawn
#: against the wrong text — a failure that would otherwise surface as an
#: inexplicable uncovered-key report, or not at all.
_NUMBERED_CHECK_OPENER = re.compile(r'^\d+\.\s', re.MULTILINE)

#: The same opener, capturing its ordinal so the run can be checked for gaps.
_NUMBERED_CHECK_ORDINAL = re.compile(r'^(\d+)\.\s', re.MULTILINE)

#: Any markdown ATX heading. CommonMark permits UP TO THREE spaces of indentation
#: before the ``#`` run, and the retired column-zero-only form matched none of
#: them — so an indented ``#### `` subsection added after the checks was invisible
#: to the structural guard, and "to the region end" over-reached past the checks
#: with nothing failing.
_ATX_HEADING = re.compile(r'^ {0,3}#{1,6}\s', re.MULTILINE)

#: A LAZY continuation: an indented line sitting DIRECTLY below the line above
#: it, with no blank line between. CommonMark continues the open paragraph there
#: whatever its indentation, so any indentation continues the entry. After a
#: BLANK line this pattern does NOT apply — the stricter rule below governs.
_LAZY_CONTINUATION = re.compile(r'^\s+\S')

#: A numbered opener with its MARKER captured (``1. `` / ``17. ``). The marker's
#: width IS the list item's content column, and CommonMark requires a
#: continuation to REACH that column once a blank line has closed the preceding
#: paragraph. Deriving the requirement from the ACTIVE marker is what keeps a
#: one- or two-space paragraph after a blank line — a NEW paragraph outside the
#: list, i.e. genuinely interleaved prose — from reading as a continuation.
#:
#: The retired ``^\s+\S`` admitted any indentation here, so such a paragraph
#: landed in ``list_lines``, ``interleaved`` stayed EMPTY, the structural guard
#: asserting ``interleaved == []`` stayed green, and every backtick-quoted key in
#: the paragraph read as COVERED by :func:`_uncovered` while no numbered check
#: adjudicated it — volume-read-as-coverage, reproduced inside the module built
#: to detect it.
_NUMBERED_CHECK_MARKER = re.compile(r'^(\d+\.[ \t]+)')


def _indent_width(line: str) -> int:
    """The line's leading-space count — the column at which its content starts."""
    return len(line) - len(line.lstrip(' '))


def _checks_region(text: str) -> str:
    """Return the workflow doc's Step-3 cognitive-checks region."""
    start = text.index(_CHECKS_REGION_START)
    end = text.index(_CHECKS_REGION_END)
    return text[start:end]


def _split_numbered_check_run(region: str) -> tuple[list[str], list[str]]:
    """Split the numbered-check run into its LIST lines and the prose between them.

    Returns ``(list_lines, interleaved)``. ``list_lines`` are the numbered
    openers and their indented continuations — the entries themselves.
    ``interleaved`` are the non-list lines sitting BETWEEN entries: unindented,
    non-blank text that opens no entry.

    Splitting them is what closes the hole the ordinal-continuity check cannot
    see. Ordinals ``[1, 2]`` are contiguous whether or not paragraphs sit between
    ``1.`` and ``2.``, so a run taken wholesale from the first opener to the
    region end silently swallows any such paragraph. A backtick-quoted candidate
    key in one then reads as covered by :func:`_uncovered` while NO numbered
    check adjudicates it — volume-read-as-coverage, reproduced inside the module
    built to detect it.

    A blank line is neither a continuation nor a break on its own: it is resolved
    by the line that follows it, so a paragraph break INSIDE an entry keeps the
    entry together while a blank before under-indented prose does not absorb it.
    Which of the two a following line is depends on the ACTIVE entry's content
    column — the width of its ``N. `` marker, tracked as the openers are walked.
    A line reaching that column continues the entry; one indented less opens a
    NEW paragraph outside the list, which is what interleaved prose IS. A line
    following its predecessor with no blank between is a lazy continuation and
    needs no such indentation.
    """
    match = _NUMBERED_CHECK_OPENER.search(region)
    if match is None:
        return [], []

    list_lines: list[str] = []
    interleaved: list[str] = []
    pending_blanks: list[str] = []
    content_column = 0
    for line in region[match.start() :].splitlines():
        if not line.strip():
            pending_blanks.append(line)
            continue
        opener = _NUMBERED_CHECK_MARKER.match(line)
        if opener is not None:
            content_column = len(opener.group(1))
            continues = True
        elif pending_blanks:
            continues = _indent_width(line) >= content_column
        else:
            continues = _LAZY_CONTINUATION.match(line) is not None
        if continues:
            list_lines.extend(pending_blanks)
            list_lines.append(line)
        else:
            interleaved.append(line)
        pending_blanks = []
    return list_lines, interleaved


def _numbered_check_block(region: str) -> str:
    """Return only the numbered-check ENTRIES of a Step-3 ``region``.

    The run starts at the first ``N.`` numbered-check opener, so the preamble and
    the ``####`` subsections that precede the checks — where a candidate-list key
    may legitimately appear in explanatory prose without any check adjudicating
    it — are excluded. Non-list content interleaved BETWEEN entries is excluded
    too (see :func:`_split_numbered_check_run`); it is not dropped silently — that
    function returns it, and the structural guard asserts it is empty against the
    shipped document. An empty string is returned when the region carries no
    numbered check (which the caller asserts against, so it cannot pass
    vacuously).
    """
    return '\n'.join(_split_numbered_check_run(region)[0])


def _headings_inside(block: str) -> list[str]:
    """The ATX headings occurring inside an extracted ``block``.

    Pure so a negative control can drive it with synthetic input. The guard that
    consumes it reads the shipped document, where an indented heading does not
    occur — so the real-document assertion alone can never demonstrate that an
    indented heading WOULD be caught, which is precisely the hole the
    column-zero-only pattern left open.
    """
    return [line for line in block.splitlines() if _ATX_HEADING.match(line)]


def _counted_lists() -> list[CandidateList]:
    """The population: every registry entry summed into ``counts.total``."""
    return [spec for spec in CANDIDATE_LISTS if spec.in_total]


# Non-emptiness asserted at IMPORT. A registry that stopped marking any entry
# ``in_total`` would leave every sweep below iterating nothing, and a sweep over
# nothing reports clean — the vacuous-confident-zero shape this module exists to
# prevent, reproduced inside it.
assert _counted_lists(), (
    'no CANDIDATE_LISTS entry carries in_total, so the coverage sweep below would '
    'pass having examined nothing'
)

#: Published on EVERY run — passing included — by the root conftest's
#: ``pytest_report_header`` (see ``_ROUTING_GUARD_MODULES`` in
#: ``test/conftest.py``). The import-time assertion above fails an EMPTY
#: population; publishing the size is what makes a SHRUNKEN one visible on the
#: GREEN run, where no failure message is ever rendered.
#:
#: This replaces a bare ``print`` inside the sweep below. That print could not
#: publish anything: this repository's ``addopts`` carry neither ``-s`` nor
#: ``-rA``, so pytest captures a passing test's stdout and discards it, and under
#: the ``-n auto`` xdist run the canonical build performs, even a
#: capture-suspended write is swallowed by the worker boundary. The report header
#: is rendered by the CONTROLLER before collection and is therefore the one
#: channel a passing run actually surfaces.
GUARD_POPULATION_LABEL = 'self-review counted candidate lists'
GUARD_POPULATION_SIZE = len(_counted_lists())


def _uncovered(candidate_lists: tuple[CandidateList, ...], check_block: str) -> list[str]:
    """Return the counted keys with no backtick-quoted reference in ``check_block``.

    ``check_block`` is the numbered-check text (see :func:`_numbered_check_block`),
    not the whole Step-3 region, so a key that appears only in the region's
    explanatory prose is correctly reported as uncovered. The predicate is pure
    so a negative control can drive it with synthetic input, proving the invariant
    actually fails when a counted entry lacks a check rather than passing vacuously.
    """
    return [
        spec.key
        for spec in candidate_lists
        if spec.in_total and f'`{spec.key}`' not in check_block
    ]


class TestCountedListCheckCoverage:
    def test_numbered_check_block_is_one_contiguous_run_with_no_heading_inside(self):
        """Pin the extraction assumption the coverage verdict rests on.

        ``_numbered_check_block`` takes everything from the first ``N.`` opener to
        the region end and calls the result "exactly the numbered checks". That
        holds only while two structural properties hold of the real document, and
        neither was asserted anywhere — the claim lived in a comment, so the doc
        could drift out from under it and the coverage assertions above would
        quietly start reading the wrong span of text.

        Three are checked here against the shipped document:

        * the openers form ONE contiguous ascending run, so the block is a single
          list rather than two lists with prose (or a second, unrelated ordered
          list) between them;
        * NO non-list content sits between entries. Ordinal continuity does not
          imply this — ``[1, 2]`` is contiguous with or without paragraphs
          between ``1.`` and ``2.`` — and the extraction now excludes such
          paragraphs, so this assertion is what keeps the exclusion visible
          instead of silent: a check legitimately rewritten as an unindented
          paragraph would otherwise vanish from the block with no signal;
        * no ATX heading occurs inside the block, so no ``####`` subsection was
          added after the checks — the property that makes "to the region end" the
          right terminator.
        """
        region = _checks_region(_WORKFLOW_DOC.read_text(encoding='utf-8'))
        list_lines, interleaved = _split_numbered_check_run(region)
        block = '\n'.join(list_lines)

        # Anti-vacuity: an empty block would satisfy all three properties trivially.
        assert block, 'Step-3 region carries no numbered check entry'

        ordinals = [int(match.group(1)) for match in _NUMBERED_CHECK_ORDINAL.finditer(block)]
        assert ordinals, 'no numbered opener parsed out of the block'

        expected = list(range(ordinals[0], ordinals[0] + len(ordinals)))
        assert ordinals == expected, (
            'the numbered-check openers are not one contiguous ascending run, so '
            'the block from the first opener to the region end is NOT exactly the '
            f'numbered checks. Parsed ordinals: {ordinals}; expected {expected}. '
            'A gap or a restart means a second ordered list was picked up, and every '
            'coverage verdict in this module is drawn against the wrong text.'
        )

        assert interleaved == [], (
            'non-list content sits between the numbered check entries. It is '
            'excluded from the block (a candidate key quoted in it must not read '
            'as covered), so if any of it is meant to BE a check it has silently '
            f'stopped counting as one: {interleaved}'
        )

        headings = _headings_inside(block)
        assert headings == [], (
            'a markdown heading occurs inside the extracted numbered-check block, '
            'so the checks are no longer the last thing in the Step-3 region and '
            f'"to the region end" over-reaches: {headings}'
        )

    def test_every_counted_candidate_list_has_a_consuming_check(self):
        """Every ``in_total`` registry entry is adjudicated by a numbered check.

        PUBLICATION CHANNEL — the session report header, via this module's
        ``GUARD_POPULATION_LABEL`` / ``GUARD_POPULATION_SIZE`` pair. The channel
        is named here because it is part of the contract: the population size is
        what distinguishes "examined the whole registry and found every entry
        covered" from "examined a registry that quietly shrank", and those two
        are indistinguishable in a green run that publishes nothing.

        This test therefore emits nothing of its own. It requests no ``capsys``
        — the fixture it used to request and never use is gone — and it prints
        nothing, because a print here would be captured and discarded on the
        pass it is supposed to inform.
        """
        population = _counted_lists()
        # Guard against a silently empty population. A set-guarding test that can
        # pass having enumerated nothing is exactly the vacuous-confident-zero
        # archetype under test, so the population size is asserted > 0 here and
        # PUBLISHED through the report header (see GUARD_POPULATION_SIZE above).
        assert len(population) > 0
        region = _checks_region(_WORKFLOW_DOC.read_text(encoding='utf-8'))
        block = _numbered_check_block(region)
        # The region MUST carry numbered checks, or the block is empty and every
        # key would (wrongly) read as uncovered — assert the block is real so the
        # coverage claim is drawn against actual check entries.
        assert block, 'Step-3 region carries no numbered check entry'
        uncovered = _uncovered(tuple(population), block)
        assert uncovered == [], (
            'counted candidate list(s) with no consuming numbered check in the '
            f'workflow doc Step-3 region: {uncovered} (population={len(population)})'
        )

    def test_coverage_predicate_detects_an_entirely_absent_key(self):
        # NEGATIVE CONTROL 1: the invariant MUST fail when a counted entry's key
        # is absent from the check block entirely. A non-counted (in_total=False)
        # orphan is correctly ignored.
        synthetic = (
            CandidateList('covered_key', 'covered', True, 'structural'),
            CandidateList('orphan_key', 'orphan', True, 'structural'),
            CandidateList('anchor_key', 'anchor', False, 'prose_contract'),
        )
        block = '1. **Real check** — for each `covered_key` entry, adjudicate it.'
        assert _uncovered(synthetic, block) == ['orphan_key']

    def test_coverage_predicate_rejects_a_key_present_only_in_non_check_prose(self):
        # NEGATIVE CONTROL 2 (the stronger one): a counted key that appears in the
        # Step-3 region's EXPLANATORY PROSE but in no numbered check must still be
        # reported as uncovered. Without the numbered-check narrowing this would
        # pass vacuously — a key mentioned in a preamble or worked example is not
        # a check that adjudicates the candidate.
        region = (
            '### Step 3: Apply seventeen checks\n'
            'Preamble prose references `prose_only_key` while explaining the mix.\n'
            '#### Present-state grounding precondition\n'
            'A worked example also names `prose_only_key` in passing.\n'
            '1. **Real check** — for each `covered_key` entry, adjudicate it.\n'
            '2. **Another check** — for each `other_covered_key` entry.\n'
            '### Dispatched-envelope output\n'
        )
        block = _numbered_check_block(_checks_region(region))
        synthetic = (
            CandidateList('prose_only_key', 'prose only', True, 'prose_contract'),
            CandidateList('covered_key', 'covered', True, 'structural'),
            CandidateList('other_covered_key', 'other', True, 'structural'),
        )
        assert _uncovered(synthetic, block) == ['prose_only_key']

    def test_coverage_predicate_rejects_a_key_present_only_in_interleaved_prose(self):
        # NEGATIVE CONTROL 3: a counted key that appears in a paragraph sitting
        # BETWEEN two numbered entries must still be reported as uncovered. This
        # is the hole ordinal continuity cannot see: ordinals [1, 2] are
        # contiguous whether or not prose sits between them, so the retired
        # "first opener to region end" extraction swallowed the paragraph and its
        # backtick-quoted key read as covered by a check that never adjudicates it.
        region = (
            '### Step 3: Apply seventeen checks\n'
            '1. **Real check** — for each `covered_key` entry, adjudicate it.\n'
            '\n'
            'Interleaved commentary that quotes `interleaved_key` while adjudicating\n'
            'nothing at all.\n'
            '\n'
            '2. **Another check** — for each `other_covered_key` entry.\n'
            '### Dispatched-envelope output\n'
        )
        list_lines, interleaved = _split_numbered_check_run(_checks_region(region))
        block = '\n'.join(list_lines)
        synthetic = (
            CandidateList('interleaved_key', 'interleaved', True, 'prose_contract'),
            CandidateList('covered_key', 'covered', True, 'structural'),
            CandidateList('other_covered_key', 'other', True, 'structural'),
        )

        assert _uncovered(synthetic, block) == ['interleaved_key']
        # The prose is reported, not silently dropped — the structural guard above
        # asserts this list is empty against the shipped document.
        assert interleaved == [
            'Interleaved commentary that quotes `interleaved_key` while adjudicating',
            'nothing at all.',
        ]

    def test_structural_guard_rejects_an_indented_heading_inside_the_block(self):
        # NEGATIVE CONTROL 4: CommonMark permits up to three leading spaces on an
        # ATX heading, so a `   #### ` subsection added after the checks is a real
        # heading. The retired column-zero-only pattern matched none of the
        # indented forms, leaving "to the region end" free to over-reach past the
        # checks with the structural guard reporting clean.
        smuggled = '   #### Subsection smuggled in behind three spaces'
        region = (
            '### Step 3: Apply seventeen checks\n'
            '1. **Real check** — for each `covered_key` entry, adjudicate it.\n'
            f'{smuggled}\n'
            '2. **Another check** — for each `other_covered_key` entry.\n'
            '### Dispatched-envelope output\n'
        )
        list_lines, interleaved = _split_numbered_check_run(_checks_region(region))

        # An INDENTED heading is an indented continuation, so it lands inside the
        # block rather than in the interleaved bucket. Naming which of the guard's
        # assertions must catch it is the point: the other one demonstrably does
        # not, so a heading assertion that cannot see indentation catches nothing.
        assert interleaved == []
        assert _headings_inside('\n'.join(list_lines)) == [smuggled]

        # Every indentation CommonMark admits is a heading...
        for indent in ('', ' ', '  ', '   '):
            line = f'{indent}#### Subsection after the checks'
            assert _headings_inside(line) == [line], indent
        # ...and four spaces is an indented CODE BLOCK, not a heading, so it is
        # correctly NOT reported. The boundary, not just the positive side.
        assert _headings_inside('    #### not a heading') == []

    # NEGATIVE CONTROL 5 AND ITS MATCHED POSITIVE ARM, driven with SYNTHETIC input
    # because the shipped document contains neither shape — so a real-document
    # assertion alone can never demonstrate that the under-indented one WOULD be
    # caught, exactly as for _headings_inside above.
    #
    # After a blank line CommonMark resolves the following line against the active
    # item's content column: `1. ` is three wide, so two spaces open a NEW paragraph
    # outside the list while three continue the entry. The retired `^\s+\S` admitted
    # both, so the two-space paragraph landed in list_lines, interleaved stayed empty
    # with the structural guard green, and its `smuggled_key` read as covered by a
    # numbered check that never adjudicated it. Both arms are required: a predicate
    # that rejected EVERY blank-line continuation would pass the negative arm alone.
    @pytest.mark.parametrize(
        ('indent', 'continues'),
        [(2, False), (3, True)],
        ids=['two-space-prose-after-blank-is-interleaved', 'marker-width-after-blank-continues'],
    )
    def test_blank_line_continuation_requires_the_active_marker_width(self, indent, continues):
        prose = f'{" " * indent}Prose quoting `smuggled_key` while adjudicating nothing at all.'
        region = (
            '### Step 3: Apply seventeen checks\n'
            '1. **Real check** — for each `covered_key` entry, adjudicate it.\n'
            '\n'
            f'{prose}\n'
            '\n'
            '2. **Another check** — for each `other_covered_key` entry.\n'
            '### Dispatched-envelope output\n'
        )
        synthetic = (CandidateList('smuggled_key', 'smuggled', True, 'prose_contract'),)

        list_lines, interleaved = _split_numbered_check_run(_checks_region(region))

        assert (prose in list_lines) is continues, prose
        assert (prose in interleaved) is not continues, prose
        # The consequence, not just the bucket: an under-indented paragraph's key
        # must be REPORTED uncovered, and a real continuation's key must not be.
        uncovered = _uncovered(synthetic, '\n'.join(list_lines))
        assert uncovered == ([] if continues else ['smuggled_key'])

    def test_both_new_checks_exist(self):
        # The two entries the plan targets each gained a consuming numbered check.
        block = _numbered_check_block(
            _checks_region(_WORKFLOW_DOC.read_text(encoding='utf-8'))
        )
        assert '`duplicate_claimable_keys`' in block
        assert '`discard_without_report`' in block

    def test_new_checks_do_not_change_total_magnitude(self):
        # Own the consequence rather than discovering it: adding the two checks
        # changes NO in_total flag, so counts.total (and the dispatch gate that
        # keys off it) keep their current magnitude by construction — the two
        # targeted entries were already counted and stay counted.
        assert next(s for s in CANDIDATE_LISTS if s.key == 'duplicate_claimable_keys').in_total
        assert next(s for s in CANDIDATE_LISTS if s.key == 'discard_without_report').in_total

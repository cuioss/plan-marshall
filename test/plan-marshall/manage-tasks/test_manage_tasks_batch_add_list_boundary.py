#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests that the raw-item walk and ``parse_toon`` agree on which rows belong to a list.

``parse_stdin_task`` reads each list body twice: the canonical parser reads it for
VALUES, and ``_normalize_list_headers`` walks it for the RAW, still-quoted item texts
the outer-quote guard adjudicates. Two readers, one boundary — and while the walk
carried its own stricter rule ("strictly deeper than the header") the two disagreed
exactly where ``parse_toon`` admits a row at the header's OWN indent: a column-0 row
under a top-level ``steps[1]:``, and an indent-2 row under a nested ``commands[1]:``.
Such a row parsed into the task record while the guard never saw it, so the guard
failed OPEN on it.

The tests are matched sets. The rejection cases vary ONLY the row indent, so a walk
that sees the deeper row and misses the shallower one fails one half of a pair while
passing the other. The acceptance controls pin that the widened boundary discriminates
rather than rejecting everything it now reaches, and the agreement test states the
invariant itself — equal row counts from both readers — rather than sampling shapes.
"""


import pytest
from _manage_tasks_batch_add_fixtures import normalize_list_headers, parse_stdin_task
from toon_parser import parse_toon

#: An item needing no quoting, so an outer quote around it can only be hand-added.
_HAND_QUOTED_STEP = '"src/plain.py (write-replace)"'

#: An item ``serialize_toon`` is OBLIGED to quote — it carries the table separator.
_SERIALIZER_QUOTED_STEP = '"src/a,b.py (write-replace)"'


def _toon_with_step_row(row, indent):
    """Build a task whose single ``steps[1]:`` row sits at ``indent`` spaces."""
    return (
        'title: List boundary control\n'
        'deliverable: 1\n'
        'domain: plan-marshall-plugin-dev\n'
        'description: Row indent decides nothing about the guard\n'
        'steps[1]:\n'
        f'{" " * indent}- {row}\n'
        'depends_on: none\n'
    )


@pytest.mark.parametrize('indent', [0, 2], ids=['header-own-indent', 'one-level-deeper'])
def test_hand_quoted_step_raises_at_every_indent_the_parser_admits(indent):
    """The guard fires on the identical item wherever ``parse_toon`` accepts its row.

    A top-level ``steps[1]:`` admits rows at column 0 as well as indented ones. The
    column-0 half of this pair is the case the stricter walk skipped, so the item
    reached the task record unadjudicated while its indent-2 twin was rejected.
    """
    with pytest.raises(ValueError) as excinfo:
        parse_stdin_task(_toon_with_step_row(_HAND_QUOTED_STEP, indent))

    assert 'outer double-quotes' in str(excinfo.value)


@pytest.mark.parametrize('indent', [0, 2], ids=['header-own-indent', 'one-level-deeper'])
def test_serializer_quoted_step_is_accepted_at_every_indent_the_parser_admits(indent):
    """POSITIVE control — reaching more rows must not mean rejecting them.

    Matched against the pair above by content: the same two indents, a value the
    serializer had to quote. Without this half, a walk that reported every row as an
    offender would pass the rejection pair outright.
    """
    parsed = parse_stdin_task(_toon_with_step_row(_SERIALIZER_QUOTED_STEP, indent))

    assert parsed['steps'] == [{'target': 'src/a,b.py', 'intent': 'write-replace'}]


def _toon_with_command_row(row, indent):
    """Build a task whose single nested ``commands[1]:`` row sits at ``indent`` spaces."""
    return (
        'title: Nested list boundary control\n'
        'deliverable: 1\n'
        'domain: plan-marshall-plugin-dev\n'
        'description: A nested header admits rows at its own indent\n'
        'steps[1]:\n'
        '  - src/plain.py (write-replace)\n'
        'depends_on: none\n'
        'verification:\n'
        '  commands[1]:\n'
        f'{" " * indent}- {row}\n'
    )


@pytest.mark.parametrize('indent', [2, 4], ids=['header-own-indent', 'one-level-deeper'])
def test_hand_quoted_command_raises_at_every_indent_the_parser_admits(indent):
    """The same disagreement one level down: a nested header admits its own indent.

    ``commands[1]:`` sits at indent 2, so ``parse_toon`` reads a row at indent 2, which
    the stricter walk excluded.
    """
    with pytest.raises(ValueError) as excinfo:
        parse_stdin_task(_toon_with_command_row('"make"', indent))

    assert 'verification.commands' in str(excinfo.value)
    assert 'outer double-quotes' in str(excinfo.value)


def test_bare_header_with_column_zero_rows_yields_its_steps():
    """CONTROL — the widened boundary also lets the length rewrite reach column-0 rows.

    A bare ``steps:`` header is rewritten to ``steps[N]:`` only when the walk found
    rows. With rows at column 0 the walk found none, so the header stayed bare, the
    canonical parser read it as a nested object, and a well-formed document failed with
    ``Missing required field: steps``.
    """
    toon = (
        'title: Bare header column-zero rows\n'
        'deliverable: 1\n'
        'domain: plan-marshall-plugin-dev\n'
        'description: Column-zero rows under a bare header\n'
        'steps:\n'
        '- src/one.py (write-replace)\n'
        '- src/two.py (write-replace)\n'
        'depends_on: none\n'
    )

    parsed = parse_stdin_task(toon)

    assert parsed['steps'] == [
        {'target': 'src/one.py', 'intent': 'write-replace'},
        {'target': 'src/two.py', 'intent': 'write-replace'},
    ]


# =============================================================================
# The invariant itself: both readers see the same rows
# =============================================================================
#
# The cases above are a sample of shapes. This one states the property the shapes
# are evidence FOR, so a future third disagreement is caught by the rule rather
# than by someone happening to write its shape as a new case.


def _steps_of(parsed):
    """Extract the parsed ``steps`` list."""
    return parsed.get('steps') or []


def _commands_of(parsed):
    """Extract the parsed ``verification.commands`` list."""
    return (parsed.get('verification') or {}).get('commands') or []


_AGREEMENT_CASES = [
    (_toon_with_step_row('src/plain.py (write-replace)', 0), 'steps', _steps_of, 'top-level-column-0'),
    (_toon_with_step_row('src/plain.py (write-replace)', 2), 'steps', _steps_of, 'top-level-indented'),
    (_toon_with_command_row('make', 2), 'commands', _commands_of, 'nested-own-indent'),
    (_toon_with_command_row('make', 4), 'commands', _commands_of, 'nested-indented'),
    (
        'title: Blank line inside a list body\n'
        'deliverable: 1\n'
        'domain: plan-marshall-plugin-dev\n'
        'description: A blank row does not close the array\n'
        'steps[2]:\n'
        '  - src/one.py (write-replace)\n'
        '\n'
        '  - src/two.py (write-replace)\n'
        'depends_on: none\n',
        'steps',
        _steps_of,
        'blank-line-inside-body',
    ),
    (
        'title: Comment inside a list body\n'
        'deliverable: 1\n'
        'domain: plan-marshall-plugin-dev\n'
        'description: A comment row does not close the array\n'
        'steps[2]:\n'
        '  - src/one.py (write-replace)\n'
        '  # a note about the second row\n'
        '  - src/two.py (write-replace)\n'
        'depends_on: none\n',
        'steps',
        _steps_of,
        'comment-inside-body',
    ),
]


@pytest.mark.parametrize(
    'toon,raw_key,extract',
    [(toon, raw_key, extract) for toon, raw_key, extract, _ in _AGREEMENT_CASES],
    ids=[case_id for *_, case_id in _AGREEMENT_CASES],
)
def test_raw_item_walk_and_parse_toon_collect_the_same_rows(toon, raw_key, extract):
    """Both readers of one list body report the same number of rows.

    This is the property the guard's coverage rests on: an item the canonical parser
    turns into a value but the walk never collected is an item no guard can see. Row
    COUNT is the assertion because the two readers legitimately differ in what they
    return per row — the walk keeps the raw quoted text, the parser returns the
    unquoted value — but never in which rows exist.
    """
    normalized, raw_items = normalize_list_headers(toon)

    assert len(raw_items.get(raw_key, [])) == len(extract(parse_toon(normalized)))

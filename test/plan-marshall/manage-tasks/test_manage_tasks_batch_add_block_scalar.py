#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests that a ``description: |`` block scalar is opaque to list-header normalization.

``parse_stdin_task`` rewrites a bare ``steps:`` / ``skills:`` / ``commands:`` header
into the canonical length-declared form so one parser reads both shapes. That rewrite
walks raw lines, so it must carry block-scalar state: a ``description: |`` body is
free-form prose the canonical parser consumes verbatim, and a task description may
legitimately contain an indented ``steps:`` line with ``- `` rows under it.

The tests below are a matched set. Two pin that prose inside the block is left alone —
not rewritten, and not put before the outer-quote guard. The third pins that the skip
stops at the block's end, so a real bare header following the description is still
normalized. Without that third case the first two are satisfiable by a normalizer that
gave up on the whole document.

The last section pins the RULES rather than the behaviour: which lines open a block
(the canonical parser constrains the key not at all, so ``task.name: |`` opens one) and
that the block's extent is a single shared predicate both readers resolve, rather than
two copies that agree until one is edited.
"""


import pytest
import toon_parser
from _manage_tasks_batch_add_fixtures import copy_block_scalar_body, parse_stdin_task

#: Prose body of the ``description: |`` block, as it must survive parsing. The
#: canonical parser strips the block's two-space indent, so this is the body text
#: after dedent. The bare ``steps:`` line and its ``- `` row are the payload: they
#: are a sentence and an example, not document structure.
_DESCRIPTION_PROSE = 'The runner writes the file, then updates the manifest.\nsteps:\n  - src/not_a_step.py (write-replace)\nBoth lines above are prose.'


def _toon_with_described_step(prose_row):
    """Build a task whose ``description: |`` block embeds a list header and ``prose_row``.

    ``prose_row`` is written at the block body's deeper indent, so a normalizer with no
    block-scalar state harvests it as a ``steps`` item.
    """
    return (
        'title: Block scalar description\n'
        'deliverable: 1\n'
        'domain: plan-marshall-plugin-dev\n'
        'description: |\n'
        '  The runner writes the file, then updates the manifest.\n'
        '  steps:\n'
        f'    - {prose_row}\n'
        '  Both lines above are prose.\n'
        'steps[1]:\n'
        '  - src/real.py (write-replace)\n'
        'depends_on: none\n'
    )


def test_list_header_inside_a_description_block_is_left_as_prose():
    """A ``steps:`` line inside ``description: |`` survives verbatim and yields no step.

    Without block-scalar state the header is rewritten in place, so the user's own
    description text emerges reading ``steps[1]:``, and the indented row beneath it is
    harvested as a phantom step. Both halves are asserted: the text is unaltered, and
    the parsed step list holds only the real document-level step.
    """
    parsed = parse_stdin_task(_toon_with_described_step('src/not_a_step.py (write-replace)'))

    assert parsed['description'] == _DESCRIPTION_PROSE
    assert parsed['steps'] == [{'target': 'src/real.py', 'intent': 'write-replace'}]


def test_outer_quoted_row_inside_a_description_block_is_not_adjudicated():
    """Description prose is never put before the outer-quote guard.

    ``"src/plain.py (write-replace)"`` is the exact item the guard rejects under a bare
    header. Inside a block scalar it is a quoted example in a sentence, so reaching the
    guard at all is the defect — the parse must succeed and keep the quotes as written.
    """
    parsed = parse_stdin_task(_toon_with_described_step('"src/plain.py (write-replace)"'))

    assert '- "src/plain.py (write-replace)"' in parsed['description']
    assert parsed['steps'] == [{'target': 'src/real.py', 'intent': 'write-replace'}]


def test_bare_header_after_a_description_block_is_still_normalized():
    """CONTROL — the skip ends with the block, it does not swallow the rest of the document.

    The two tests above are equally satisfied by a normalizer that stopped working once
    it saw a block scalar. This one varies only what follows the block: a bare ``steps:``
    header, which the canonical parser reads as a nested object and yields no items for
    unless the rewrite still reaches it.
    """
    toon = (
        'title: Bare header after block\n'
        'deliverable: 1\n'
        'domain: plan-marshall-plugin-dev\n'
        'description: |\n'
        '  Prose mentioning steps: and nothing structural.\n'
        'steps:\n'
        '  - src/after_block.py (write-replace)\n'
        'depends_on: none\n'
    )

    parsed = parse_stdin_task(toon)

    assert parsed['steps'] == [{'target': 'src/after_block.py', 'intent': 'write-replace'}]


def test_hand_quoted_item_under_a_bare_header_after_a_block_still_raises():
    """CONTROL — the guard still fires on real items once the block has closed.

    Pairs with the quoted-prose test above: the identical offending item is ignored
    inside the description and rejected outside it. Varying only the position is what
    proves the block skip is scoped rather than disabling the guard.
    """
    toon = (
        'title: Bare header after block\n'
        'deliverable: 1\n'
        'domain: plan-marshall-plugin-dev\n'
        'description: |\n'
        '  Prose mentioning steps: and nothing structural.\n'
        'steps:\n'
        '  - "src/plain.py (write-replace)"\n'
        'depends_on: none\n'
    )

    with pytest.raises(ValueError) as excinfo:
        parse_stdin_task(toon)

    assert 'outer double-quotes' in str(excinfo.value)


# =============================================================================
# The block-scalar rules themselves: one authority, two readers
# =============================================================================
#
# The cases above pin BEHAVIOUR for the ``description: |`` key. The two below pin
# the RULES the behaviour rests on: the key class the canonical parser actually
# applies, and the fact that the extent is one shared predicate rather than two
# copies that happen to agree today.


def test_a_block_scalar_opened_by_a_non_word_key_is_still_opaque():
    """A key outside ``[\\w_-]+`` opens a block scalar, so its prose is left alone.

    ``toon_parser`` splits on the FIRST colon and asks only whether the remainder
    is ``|``, so ``task.name: |`` is a block scalar to it. A narrower key class
    here made this document structure to one reader and prose to the other: the
    indented ``steps:`` line inside the author's own text was rewritten to
    ``steps[N]:`` and its prose row harvested into the outer-quote guard.

    Matched against ``test_bare_header_after_a_description_block_is_still_normalized``
    above by varying only the KEY: the real ``steps:`` header after the block must
    still be normalised, so a normalizer that gave up on the document fails there.
    """
    toon = (
        'title: Non-word block-scalar key\n'
        'deliverable: 1\n'
        'domain: plan-marshall-plugin-dev\n'
        'task.name: |\n'
        '  Prose that mentions a list.\n'
        '  steps:\n'
        '    - "src/plain.py (write-replace)"\n'
        'steps:\n'
        '  - src/real.py (write-replace)\n'
        'depends_on: none\n'
    )

    parsed = parse_stdin_task(toon)

    assert parsed['steps'] == [{'target': 'src/real.py', 'intent': 'write-replace'}]


_EXTENT_PREDICATE = 'block_scalar_body_continues'


def test_both_block_scalar_readers_resolve_the_same_extent_predicate():
    """The two walks consume ONE predicate object, not two agreeing copies.

    Asserting that both still work is satisfied by a re-duplicated copy — which is
    exactly the state that produced the disagreement, since a copy passes until
    one side is edited. So the assertion is on the predicate each call site
    RESOLVES: the name appears in both code objects, and both resolve it to the
    same function.
    """
    assert _EXTENT_PREDICATE in copy_block_scalar_body.__code__.co_names, (
        'the task-side walk no longer references the shared predicate'
    )
    assert _EXTENT_PREDICATE in toon_parser._parse_multiline_value.__code__.co_names, (
        'the canonical parser no longer references the shared predicate'
    )
    assert (
        copy_block_scalar_body.__globals__[_EXTENT_PREDICATE]
        is toon_parser._parse_multiline_value.__globals__[_EXTENT_PREDICATE]
    ), 'the two call sites resolve different objects for the same predicate name'

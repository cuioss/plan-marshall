#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests that a mis-shaped RECOGNIZED field is named rather than silently reduced.

``parse_stdin_task`` already names input the schema does not handle — an unrecognized
top-level key is reported on a validation failure instead of vanishing. Two RECOGNIZED
fields used to take the opposite path and drop a mis-shaped value with no diagnostic,
after which ``cmd_commit_add`` persisted the reduced record:

* a ``steps`` row whose target is empty was SKIPPED, and the survivors renumbered, so a
  uniform-array row written ``,write-replace`` produced a shorter task than the author
  wrote;
* a ``skills`` value the parser did not return as a list was replaced with ``[]``, so a
  single-line ``skills: bundle:skill`` (which parses to a str) and a bare ``skills:``
  block whose rows are not ``- `` items (which parses to a nested dict) each lost the
  declared skill.

Each rejection is pinned as a MATCHED PAIR: a positive case asserting the mis-shaped
input is rejected AND that the message names the offending field, and a negative control
asserting the legal shape of the same field still parses unchanged. A guard with only
its positive half is satisfied by one that always raises.
"""


import pytest
from _manage_tasks_batch_add_fixtures import parse_stdin_task

_PREAMBLE = (
    'title: Field shape control\n'
    'deliverable: 1\n'
    'domain: plan-marshall-plugin-dev\n'
    'description: Mis-shaped recognized fields are named, not reduced\n'
)

_GOOD_STEPS_BLOCK = 'steps[1]:\n  - src/real.py (write-replace)\n'


def _toon(*body: str) -> str:
    """Assemble a task definition from the shared preamble and ``body`` fragments."""
    return _PREAMBLE + ''.join(body) + 'depends_on: none\n'


# =============================================================================
# steps: a row that declares no target
# =============================================================================


def test_uniform_array_step_row_with_an_empty_target_is_rejected_and_names_steps():
    """A ``,write-replace`` row is a declared step with no target — say so.

    The row parses (the intent column is well-formed), so nothing downstream can
    tell it apart from a task that was written with one fewer step. Skipping it
    renumbered the survivors and persisted the shortened record.
    """
    toon = _toon('steps[2]{target,intent}:\n  src/real.py,write-replace\n  ,write-replace\n')

    with pytest.raises(ValueError) as excinfo:
        parse_stdin_task(toon)

    message = str(excinfo.value)
    assert 'steps' in message
    assert 'no target' in message


def test_uniform_array_step_rows_with_targets_still_parse_unchanged():
    """NEGATIVE CONTROL — varying only whether the target column is filled.

    Byte-for-byte the fixture above with ``src/other.py`` in place of the empty
    cell. Without this half, a guard that rejected every uniform-array row would
    pass the positive case outright.
    """
    toon = _toon('steps[2]{target,intent}:\n  src/real.py,write-replace\n  src/other.py,write-replace\n')

    parsed = parse_stdin_task(toon)

    assert parsed['steps'] == [
        {'target': 'src/real.py', 'intent': 'write-replace'},
        {'target': 'src/other.py', 'intent': 'write-replace'},
    ]


def test_simple_list_step_item_that_is_empty_is_rejected_and_names_steps():
    """The simple-list form takes the same verdict as the uniform-array form.

    An explicitly empty item reaches ``_coerce_steps`` as an empty string, the
    same state the empty target column produces. Reporting it as a missing
    ``(intent)`` marker would send the author to fix a marker that is not the
    problem.
    """
    toon = _toon('steps[2]:\n  - src/real.py (write-replace)\n  - ""\n')

    with pytest.raises(ValueError) as excinfo:
        parse_stdin_task(toon)

    message = str(excinfo.value)
    assert 'steps' in message
    assert 'no target' in message


# =============================================================================
# skills: a value the canonical parser did not return as a list
# =============================================================================


def test_single_line_skills_value_is_rejected_and_names_skills():
    """``skills: bundle:skill`` parses to a str, so the declared skill would be lost.

    ``toon_parser`` splits on the FIRST colon, so the key is ``skills`` and the
    value is the rest of the line. Substituting ``[]`` discarded a skill the
    author declared, with no diagnostic.
    """
    toon = _toon('skills: pm-plugin-development:plugin-architecture\n', _GOOD_STEPS_BLOCK)

    with pytest.raises(ValueError) as excinfo:
        parse_stdin_task(toon)

    message = str(excinfo.value)
    assert 'skills' in message
    assert 'must be a list' in message


def test_bare_skills_block_whose_rows_are_not_list_items_is_rejected_and_names_skills():
    """The second reachable non-list shape: a nested dict.

    ``_normalize_list_headers`` rewrites a bare ``skills:`` header only when its
    walk found ``- `` rows. Rows that are not list items leave the header bare, so
    the canonical parser reads a nested object — and the declared skill was
    likewise replaced with ``[]``.
    """
    toon = _toon('skills:\n  pm-plugin-development: plugin-architecture\n', _GOOD_STEPS_BLOCK)

    with pytest.raises(ValueError) as excinfo:
        parse_stdin_task(toon)

    message = str(excinfo.value)
    assert 'skills' in message
    assert 'must be a list' in message


@pytest.mark.parametrize(
    'skills_block,label',
    [
        ('skills:\n  - pm-plugin-development:plugin-architecture\n', 'bare-header'),
        ('skills[1]:\n  - pm-plugin-development:plugin-architecture\n', 'length-declared'),
    ],
)
def test_list_shaped_skills_still_parse_unchanged(skills_block, label):
    """NEGATIVE CONTROL — both legal shapes of the same field still round-trip.

    Matched against the two rejections above by varying only the SHAPE of the
    ``skills`` value while holding its content identical. Without this half, a
    guard that rejected every ``skills`` value would pass both positive cases.
    """
    parsed = parse_stdin_task(_toon(skills_block, _GOOD_STEPS_BLOCK))

    assert parsed['skills'] == ['pm-plugin-development:plugin-architecture'], label


@pytest.mark.parametrize(
    'skills_block,label',
    [('', 'field-absent'), ('skills:\n', 'header-with-no-rows')],
)
def test_a_skills_field_that_declares_nothing_stays_the_empty_list(skills_block, label):
    """NEGATIVE CONTROL — absence is not a mis-shape.

    ``skills`` is optional, and a header with no rows declares no skill, so
    neither loses anything by yielding ``[]``. Without this case the guard could
    tighten into "``skills`` is required", which is a different contract than the
    one it exists to enforce.
    """
    parsed = parse_stdin_task(_toon(skills_block, _GOOD_STEPS_BLOCK))

    assert parsed['skills'] == [], label

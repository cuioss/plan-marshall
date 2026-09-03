#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the `batch-add` subcommand of manage-tasks."""


import pytest
from _manage_tasks_batch_add_fixtures import (
    _BARE_BLOCK_TASK_TOON,
    _BRACKETED_TASK_TOON,
    _TABULAR_TASK_TOON,
    _TABULAR_TASK_TOON_SOURCE,
    parse_stdin_task,
)
from toon_parser import serialize_toon


@pytest.mark.parametrize(
    'toon,label',
    [
        (_BARE_BLOCK_TASK_TOON, 'bare-block'),
        (_BRACKETED_TASK_TOON, 'bracketed'),
        (_TABULAR_TASK_TOON, 'tabular'),
    ],
)
def test_parse_stdin_task_accepts_both_steps_forms(toon, label):
    """Both bare-block and bracketed ``steps`` forms parse to the same step list."""
    parsed = parse_stdin_task(toon)

    assert parsed['steps'] == [
        {'target': 'test/plan-marshall/manage-tasks/test_a.py', 'intent': 'write-replace'},
        {'target': 'test/plan-marshall/manage-tasks/test_b.py', 'intent': 'write-replace'},
    ], f'{label} form did not normalise to canonical step list'


@pytest.mark.parametrize(
    'toon,label',
    [
        (_BARE_BLOCK_TASK_TOON, 'bare-block'),
        (_BRACKETED_TASK_TOON, 'bracketed'),
        (_TABULAR_TASK_TOON, 'tabular'),
    ],
)
def test_parse_stdin_task_accepts_both_skills_forms(toon, label):
    """Both bare-block and bracketed ``skills`` forms parse to the same skill list."""
    parsed = parse_stdin_task(toon)

    assert parsed['skills'] == ['pm-plugin-development:plugin-architecture'], (
        f'{label} form did not normalise to canonical skills list'
    )


@pytest.mark.parametrize(
    'toon,label',
    [
        (_BARE_BLOCK_TASK_TOON, 'bare-block'),
        (_BRACKETED_TASK_TOON, 'bracketed'),
        (_TABULAR_TASK_TOON, 'tabular'),
    ],
)
def test_parse_stdin_task_accepts_both_verification_commands_forms(toon, label):
    """Both bare-block and bracketed ``verification.commands`` parse identically."""
    parsed = parse_stdin_task(toon)

    expected_cmd = 'python3 .plan/execute-script.py x:y:z run --command-args "module-tests"'
    assert parsed['verification']['commands'] == [expected_cmd], (
        f'{label} verification.commands did not normalise to canonical list'
    )


def test_parse_stdin_task_bracketed_and_bare_block_parse_to_identical_output():
    """Round-trip equivalence — identical content in either shape produces identical dicts.

    The two TOON renderings differ only in length declarations; the
    parser's job is to erase that difference. Anything that diverges
    here is a per-shape branch the contract forbids.

    Every field except ``title`` and ``description`` must match — those two
    are intentionally different per-fixture to keep error messages
    unambiguous about which fixture is failing.
    """
    bare = parse_stdin_task(_BARE_BLOCK_TASK_TOON)
    bracketed = parse_stdin_task(_BRACKETED_TASK_TOON)
    tabular = parse_stdin_task(_TABULAR_TASK_TOON)

    for field in ('deliverable', 'domain', 'profile', 'skills', 'origin', 'steps', 'depends_on', 'verification'):
        assert bare[field] == bracketed[field], f'field {field!r} diverged between shapes'
        assert bare[field] == tabular[field], f'field {field!r} diverged in the tabular shape'


def test_parse_stdin_task_bracketed_steps_zero_count_raises_missing_steps():
    """Bracketed form with a zero-count and empty body still triggers the required-field error.

    ``steps[0]:`` with no items is structurally well-formed but semantically
    empty — the parser must surface the canonical ``Missing required field:
    steps`` message rather than silently accepting an empty list.
    """
    toon = (
        'title: Empty steps\n'
        'deliverable: 1\n'
        'domain: plan-marshall-plugin-dev\n'
        'description: Empty steps must fail required-field validation\n'
        'steps[0]:\n'
        'depends_on: none\n'
    )

    with pytest.raises(ValueError) as excinfo:
        parse_stdin_task(toon)
    assert 'steps' in str(excinfo.value)


def test_parse_stdin_task_bracketed_steps_outer_quotes_still_rejected():
    """The outer-quotes anti-pattern is still rejected in the bracketed form.

    Adding bracketed-form support must not weaken the existing quoting
    contract — the same ValueError fires whether the steps header is
    ``steps:`` or ``steps[N]:``.
    """
    offending = '"src/main/java/Foo.java"'
    toon = (
        'title: Outer quotes negative bracketed\n'
        'deliverable: 1\n'
        'domain: plan-marshall-plugin-dev\n'
        'description: Outer-quoted step under bracketed form should fail fast\n'
        'steps[1]:\n'
        f'  - {offending}\n'
        'depends_on: none\n'
    )

    with pytest.raises(ValueError) as excinfo:
        parse_stdin_task(toon)
    message = str(excinfo.value)
    assert 'steps' in message
    assert 'outer double-quotes' in message


def test_parse_stdin_task_bracketed_form_length_declaration_is_advisory():
    """A mismatched ``[N]`` count does NOT raise — TOON treats ``[N]`` as advisory.

    The parser normalises by walking the body until indentation breaks; the
    declared count is informational only. This mirrors the documented TOON
    specification (see ``ref-toon-format``).

    Fixture declares count 5 with only 2 actual rows.
    """
    toon = (
        'title: Count mismatch\n'
        'deliverable: 1\n'
        'domain: plan-marshall-plugin-dev\n'
        'description: Bracketed count is advisory and should not fail\n'
        'steps[5]:\n'
        '  - test/plan-marshall/manage-tasks/test_a.py (write-replace)\n'
        '  - test/plan-marshall/manage-tasks/test_b.py (write-replace)\n'
        'depends_on: none\n'
    )

    parsed = parse_stdin_task(toon)

    assert parsed['steps'] == [
        {'target': 'test/plan-marshall/manage-tasks/test_a.py', 'intent': 'write-replace'},
        {'target': 'test/plan-marshall/manage-tasks/test_b.py', 'intent': 'write-replace'},
    ]


# =============================================================================
# Tests: round-trip against the serializer's own output
# =============================================================================


def test_tabular_fixture_is_exactly_what_the_serializer_emits():
    """The tabular fixture is real serializer output, not a hand-typed approximation.

    Deriving it here is what makes the round-trip test below meaningful: if the
    fixture drifted from what ``serialize_toon`` actually emits, the round-trip
    would be proving a shape nothing produces.
    """
    assert serialize_toon(_TABULAR_TASK_TOON_SOURCE) == _TABULAR_TASK_TOON.rstrip('\n')


def test_parse_stdin_task_round_trips_serialize_toon_output():
    """``parse_stdin_task(serialize_toon(task))`` reproduces the task record.

    This is the contract the hand-rolled reader broke three separate ways: the
    uniform-array ``steps`` header parsed to zero steps, the ``skills`` item kept
    the serializer's quotes, and the ``verification.commands`` item was rejected
    for carrying them.
    """
    parsed = parse_stdin_task(serialize_toon(_TABULAR_TASK_TOON_SOURCE))

    assert parsed['steps'] == _TABULAR_TASK_TOON_SOURCE['steps']
    assert parsed['skills'] == _TABULAR_TASK_TOON_SOURCE['skills']
    assert parsed['verification']['commands'] == _TABULAR_TASK_TOON_SOURCE['verification']['commands']


def test_tabular_steps_do_not_report_missing_steps():
    """The uniform-array form yields its steps instead of the historical failure.

    A header-only widening still produced ``Missing required field: steps``,
    because the row walker required a ``  - `` prefix the CSV rows do not carry.
    Pinning that the steps arrive is what distinguishes a real delegation from
    an alias on the header.
    """
    parsed = parse_stdin_task(_TABULAR_TASK_TOON)

    assert len(parsed['steps']) == 2


def test_skills_value_containing_a_colon_round_trips_without_embedded_quotes():
    """A quoted ``skills`` item is unquoted, not stored with literal quotes."""
    parsed = parse_stdin_task(_TABULAR_TASK_TOON)

    assert parsed['skills'] == ['pm-plugin-development:plugin-architecture']
    assert '"' not in parsed['skills'][0]


# =============================================================================
# Tests: the outer-quote guards, as a matched positive/negative control pair
# =============================================================================
#
# The guards must reject a HAND-added quote while accepting one the serializer
# was obliged to add. Either test alone is satisfiable by a vacuous guard — one
# that always raises, or one that never does — so the PAIR is the proof
# obligation, not either half.


def _toon_with_step(step_item):
    """Build a minimal task definition whose single step is ``step_item``."""
    return (
        'title: Guard control\n'
        'deliverable: 1\n'
        'domain: plan-marshall-plugin-dev\n'
        'description: Outer-quote guard control\n'
        'steps[1]:\n'
        f'  - {step_item}\n'
        'depends_on: none\n'
    )


def test_serializer_added_quote_on_steps_item_is_accepted_and_unquoted():
    """POSITIVE control — a quote ``serialize_toon`` had to add is legitimate.

    ``src/a,b.py`` contains the table separator, so the serializer must quote it.
    Rejecting that quote would make a legitimately-serialized task unreadable.
    """
    parsed = parse_stdin_task(_toon_with_step('"src/a,b.py (write-replace)"'))

    assert parsed['steps'] == [{'target': 'src/a,b.py', 'intent': 'write-replace'}]


def test_hand_added_quote_on_steps_item_still_raises():
    """NEGATIVE control — a quote on a value needing none is still an anti-pattern.

    ``src/plain.py`` needs no quoting, so an outer quote around it can only have
    been written by hand. This is the matched opposite of the test above, and it
    is what proves the guard discriminates rather than accepting everything.
    """
    with pytest.raises(ValueError) as excinfo:
        parse_stdin_task(_toon_with_step('"src/plain.py (write-replace)"'))

    assert 'outer double-quotes' in str(excinfo.value)


def _toon_with_bare_step(step_item):
    """Build the same definition as ``_toon_with_step`` under a BARE ``steps:`` header."""
    return (
        'title: Guard control bare header\n'
        'deliverable: 1\n'
        'domain: plan-marshall-plugin-dev\n'
        'description: Outer-quote guard control under the bare header form\n'
        'steps:\n'
        f'  - {step_item}\n'
        'depends_on: none\n'
    )


def test_same_quoted_item_is_rejected_under_a_bare_header():
    """The HEADER decides where content cannot: identical bytes, opposite verdict.

    ``"src/a,b.py (write-replace)"`` is accepted verbatim by
    ``test_serializer_added_quote_on_steps_item_is_accepted_and_unquoted``, because
    the serializer was obliged to quote a value carrying the table separator. The
    identical item under a bare ``steps:`` header is rejected, because
    ``serialize_toon`` never writes a bare header — so that quote cannot be its.

    Varying ONLY the header is what proves the guard reads provenance. Every other
    control in this pair varies the content too, so each is satisfiable by a
    content-only rule; this one is not, and it is the case a content-only rule
    silently lets through.
    """
    with pytest.raises(ValueError) as excinfo:
        parse_stdin_task(_toon_with_bare_step('"src/a,b.py (write-replace)"'))

    assert 'outer double-quotes' in str(excinfo.value)


def test_serializer_added_quote_on_verification_command_is_accepted():
    """POSITIVE control for the second guard — commands carry serializer quoting."""
    parsed = parse_stdin_task(_TABULAR_TASK_TOON)

    assert parsed['verification']['commands'] == [
        'python3 .plan/execute-script.py x:y:z run --command-args "module-tests"'
    ]


def test_hand_added_quote_on_verification_command_still_raises():
    """NEGATIVE control for the second guard — ``make`` needs no quoting."""
    toon = (
        'title: Guard control commands\n'
        'deliverable: 1\n'
        'domain: plan-marshall-plugin-dev\n'
        'description: Outer-quoted command should fail fast\n'
        'steps[1]:\n'
        '  - src/plain.py (write-replace)\n'
        'depends_on: none\n'
        'verification:\n'
        '  commands[1]:\n'
        '    - "make"\n'
    )

    with pytest.raises(ValueError) as excinfo:
        parse_stdin_task(toon)

    message = str(excinfo.value)
    assert 'verification.commands' in message
    assert 'outer double-quotes' in message


# =============================================================================
# Test: unrecognized input is named rather than silently discarded
# =============================================================================
#
# The diagnostic is FAILURE-ONLY: ``parse_stdin_task`` consults
# ``_KNOWN_TASK_KEYS`` inside its ``except ValueError`` arm alone, so a valid
# task carrying an unrecognized key parses cleanly and the key simply does not
# reach the returned record. The pair below therefore holds the unrecognized key
# CONSTANT and varies ONLY the task's validity — otherwise each case differs in
# two respects at once and neither can fail for the reason it advertises.


#: The mis-serialized key both cases carry. Named once so the pair cannot drift
#: into testing different keys.
_UNRECOGNIZED_KEY = 'stpes'

_VALID_STEP_ROW = 'src/real.py (write-replace)'

#: Fails ``validate_steps_are_file_paths`` — no path separator, no source
#: extension — so it is the ONLY difference between the two cases.
_INVALID_STEP_ROW = 'notafilepath (write-replace)'


def _toon_with_unrecognized_key(step_row):
    """Build a task carrying ``stpes:`` whose validity turns solely on ``step_row``."""
    return (
        'title: Typo key\n'
        'deliverable: 1\n'
        'domain: plan-marshall-plugin-dev\n'
        f'{_UNRECOGNIZED_KEY}: typo-key-here\n'
        'steps[1]:\n'
        f'  - {step_row}\n'
        'depends_on: none\n'
    )


def test_validation_failure_names_unrecognized_fields():
    """A mis-serialized field is reported on failure instead of being dropped.

    The previous reader fell through to ``i += 1`` on any line it did not
    recognize, so a typo'd key vanished and the caller was told only that a
    required field was missing — pointing at the wrong culprit.
    """
    with pytest.raises(ValueError) as excinfo:
        parse_stdin_task(_toon_with_unrecognized_key(_INVALID_STEP_ROW))

    assert _UNRECOGNIZED_KEY in str(excinfo.value)


def test_a_valid_task_carrying_the_same_key_parses_and_does_not_keep_it():
    """MATCHED NEGATIVE CONTROL — the same key, on a task that validates.

    Two claims, both of which a leak would break. The parse SUCCEEDS, so the
    accumulator has not grown into noise emitted on every green parse; and the
    key is ABSENT from the returned record, so nothing unrecognized was carried
    into the task. The declared canonical fields are asserted alongside, so a
    leak that renamed or reshaped a recognized field is caught here too rather
    than only where that field is consumed.
    """
    parsed = parse_stdin_task(_toon_with_unrecognized_key(_VALID_STEP_ROW))

    assert _UNRECOGNIZED_KEY not in parsed
    assert parsed['steps'] == [{'target': 'src/real.py', 'intent': 'write-replace'}]
    assert parsed['title'] == 'Typo key'
    assert parsed['deliverable'] == 1
    assert parsed['domain'] == 'plan-marshall-plugin-dev'

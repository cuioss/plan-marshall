#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the `batch-add` subcommand of manage-tasks."""


import pytest
from _manage_tasks_batch_add_fixtures import _BARE_BLOCK_TASK_TOON, _BRACKETED_TASK_TOON, parse_stdin_task

# =============================================================================
# Tests: parse_stdin_task accepts both bracketed and bare-block list forms
# =============================================================================

@pytest.mark.parametrize(
    'toon,label',
    [
        (_BARE_BLOCK_TASK_TOON, 'bare-block'),
        (_BRACKETED_TASK_TOON, 'bracketed'),
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

    for field in ('deliverable', 'domain', 'profile', 'skills', 'origin', 'steps', 'depends_on', 'verification'):
        assert bare[field] == bracketed[field], f'field {field!r} diverged between shapes'


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

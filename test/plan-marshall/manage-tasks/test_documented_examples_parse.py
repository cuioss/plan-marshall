#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Every documented example in ``manage-tasks/SKILL.md`` survives its own validator.

A documented example is a promise a reader acts on. When one cannot pass the
validator that governs it, the reader is told a required field is missing or an
intent marker is absent — a rejection that names the wrong culprit, because the
example they copied was the thing at fault. These tests close that gap by feeding
the document's OWN examples through the OWN validators: ``parse_stdin_task`` for
TOON task definitions and ``_validate_batch_entry`` for ``batch-add`` JSON
entries.

The population is derived from the document at test time and asserted non-zero
FIRST. That ordering is the point: an extractor that stops matching the
document's shape finds nothing, and "no example failed" over an empty set is
indistinguishable from a clean pass unless the size is checked on its own.
"""

import json
from pathlib import Path

import pytest
from _documented_example_scan import (
    scan_json_array_examples,
    scan_task_definition_examples,
    step_marker,
    step_rows,
)
from _manage_tasks_fixtures import parse_stdin_task
from conftest import MARKETPLACE_ROOT, load_script_module

_SKILL_MD: Path = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'manage-tasks' / 'SKILL.md'

_crud = load_script_module(
    'plan-marshall', 'manage-tasks', '_tasks_crud.py', '_tasks_crud_documented_examples'
)
_core = load_script_module(
    'plan-marshall', 'manage-tasks', '_tasks_core.py', '_tasks_core_documented_examples'
)

_validate_batch_entry = _crud._validate_batch_entry
_STEP_INTENT_SUFFIX_RE = _core._STEP_INTENT_SUFFIX_RE
_VALID_STEP_INTENTS = _core.VALID_STEP_INTENTS


def _skill_text() -> str:
    return _SKILL_MD.read_text(encoding='utf-8')


def test_skill_document_yields_a_non_empty_example_population():
    """The extractors resolve examples from the live document, not from nothing.

    Checked before any per-example assertion, and separately from them, because
    a zero population makes every downstream assertion vacuously true.
    """
    text = _skill_text()
    definitions, fenced_blocks = scan_task_definition_examples(text)
    arrays, _ = scan_json_array_examples(text)

    assert fenced_blocks > 0, f'no fenced code blocks resolved in {_SKILL_MD} — the scan is unresolved'
    assert definitions, (
        f'no TOON task-definition examples resolved from {fenced_blocks} fenced blocks in '
        f'{_SKILL_MD} — the extractor no longer matches the document, so a broken example '
        f'would pass unseen'
    )
    assert arrays, (
        f'no batch-add JSON arrays resolved from {fenced_blocks} fenced blocks in {_SKILL_MD} — '
        f'the extractor no longer matches the document'
    )


def test_every_concrete_task_definition_example_parses():
    """Each runnable TOON example parses through ``parse_stdin_task``.

    "Concrete" means carrying no ``{placeholder}``: those examples are meant to
    be copied and run verbatim, so the validator is the exact bar they must
    clear. Templates are excluded here and checked structurally below rather
    than folded into this pass.
    """
    definitions, fenced_blocks = scan_task_definition_examples(_skill_text())
    concrete = [example for example in definitions if not example.is_template]

    assert concrete, (
        f'no CONCRETE task-definition examples among {len(definitions)} found across '
        f'{fenced_blocks} fenced blocks — nothing was validated'
    )

    failures: list[str] = []
    for example in concrete:
        try:
            parse_stdin_task(example.text)
        except ValueError as exc:
            failures.append(f'line {example.line}: {exc}')

    assert not failures, (
        f'{len(failures)} of {len(concrete)} concrete documented example(s) in {_SKILL_MD} '
        f'do not parse:\n  ' + '\n  '.join(failures)
    )


def test_every_template_task_definition_example_carries_step_intent_markers():
    """Each placeholder-bearing example still satisfies the step contract it teaches.

    A template cannot be parsed verbatim — a ``{deliverable_number}`` is not an
    integer — so the check that CAN be made is the one the reader copies: every
    step row carries the required trailing ``(intent)`` marker, and any intent
    that is not itself a placeholder is in the closed vocabulary. Reporting the
    template as merely unchecked would leave exactly the defect this file exists
    to close sitting in the most-copied example in the document.
    """
    definitions, _ = scan_task_definition_examples(_skill_text())
    templates = [example for example in definitions if example.is_template]

    assert templates, (
        f'no TEMPLATE task-definition examples resolved from {_SKILL_MD}; this assertion '
        f'guards against an extractor that silently stopped classifying them'
    )

    rows_checked = 0
    failures: list[str] = []
    for example in templates:
        for row in step_rows(example.text):
            rows_checked += 1
            marker = step_marker(row)
            if marker is None:
                failures.append(f'line {example.line}: step {row!r} has no (intent) marker')
                continue
            if '{' in marker:
                # The intent is itself a placeholder; the closed vocabulary
                # cannot contain one, so there is nothing further to check.
                continue
            match = _STEP_INTENT_SUFFIX_RE.match(row)
            if match is None or match.group('intent') not in _VALID_STEP_INTENTS:
                failures.append(f'line {example.line}: step {row!r} names unknown intent {marker!r}')

    assert rows_checked > 0, (
        f'{len(templates)} template example(s) yielded no step rows — nothing was checked'
    )
    assert not failures, (
        f'{len(failures)} of {rows_checked} template step row(s) in {_SKILL_MD} break the step '
        f'contract:\n  ' + '\n  '.join(failures)
    )


def test_every_documented_batch_add_entry_validates():
    """Each ``batch-add`` JSON entry passes ``_validate_batch_entry``.

    The batch path has its own validator, so a TOON example passing says nothing
    about the JSON arrays beside it — notably the ``{"target", "intent"}`` step
    object shape, where a bare-string step is rejected.
    """
    arrays, fenced_blocks = scan_json_array_examples(_skill_text())

    assert arrays, f'no batch-add JSON arrays resolved from {fenced_blocks} fenced blocks in {_SKILL_MD}'

    entries_checked = 0
    failures: list[str] = []
    for literal in arrays:
        try:
            parsed = json.loads(literal)
        except json.JSONDecodeError as exc:
            failures.append(f'documented array is not valid JSON: {exc}')
            continue
        assert isinstance(parsed, list), 'the extractor must only yield JSON arrays'
        for index, entry in enumerate(parsed):
            entries_checked += 1
            try:
                _validate_batch_entry(entry, index)
            except ValueError as exc:
                failures.append(str(exc))

    assert entries_checked > 0, (
        f'{len(arrays)} documented array(s) yielded zero entries — nothing was validated'
    )
    assert not failures, (
        f'{len(failures)} of {entries_checked} documented batch-add entr(ies) in {_SKILL_MD} '
        f'do not validate:\n  ' + '\n  '.join(failures)
    )


def test_scan_reports_zero_population_for_a_document_holding_no_examples():
    """The extractors report an empty population rather than inventing one.

    The matched negative control for the non-zero assertions above: without it,
    a scanner that returned a constant non-zero size would satisfy every other
    test in this file.
    """
    definitions, fenced_blocks = scan_task_definition_examples('# Heading\n\nProse only.\n')
    arrays, _ = scan_json_array_examples('# Heading\n\nProse only.\n')

    assert fenced_blocks == 0
    assert definitions == []
    assert arrays == []


@pytest.mark.parametrize(
    'removed,expected_fragment',
    [
        ('deliverable: 1\n', 'deliverable'),
        (' (write-replace)', 'intent'),
    ],
    ids=['required-field-deleted', 'step-intent-marker-deleted'],
)
def test_a_broken_documented_example_is_rejected(removed, expected_fragment):
    """A real documented example with one required token deleted fails to parse.

    The matched negative control for the pass above: without it, a validator
    that accepted everything would satisfy every other assertion in this file.
    The mutation is applied to the live example text rather than to a fixture,
    so it also proves the tests read the tree instead of a frozen copy.
    """
    definitions, _ = scan_task_definition_examples(_skill_text())
    concrete = [example for example in definitions if not example.is_template]
    assert concrete, 'no concrete example to mutate'

    original = concrete[0].text
    assert removed in original, f'{removed!r} is not present in the example being mutated'
    broken = original.replace(removed, '', 1)

    with pytest.raises(ValueError) as excinfo:
        parse_stdin_task(broken)
    assert expected_fragment in str(excinfo.value)

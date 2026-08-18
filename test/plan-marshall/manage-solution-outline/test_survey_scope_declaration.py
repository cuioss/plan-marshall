#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""A survey-scope deliverable's declaration is parsed, validated, and counted.

``phase-3-outline/standards/outline-workflow-detail.md`` § "Survey-scope vs
mutation-scope declaration" mandates that a deliverable whose mutation set is
not knowable at authoring time declares ``**Files to survey:**`` (the
analysis-only candidate pool) and ``**Files expected to mutate:**`` (the
change-bearing subset) INSTEAD of a flat ``**Affected files:**`` list.

A deliverable authored exactly that way used to parse to an empty file list. The
consequences compounded: it failed contract validation with "Missing **Affected
files:** section", its write-set was empty so every write-set-derived
classification saw a deliverable that touched nothing, and its mutation paths
belonged to no declared set at all — the incomplete-derived-set failure in its
purest form, since the missing paths were exactly the ones nobody could see were
missing.

Each fixture here is built so a regression reaches the OPPOSITE verdict, not
merely a different count.
"""

from typing import Any

from conftest import load_script_module

_parsing = load_script_module(
    'plan-marshall',
    'manage-solution-outline',
    '_plan_parsing.py',
    module_name='_plan_parsing_survey_scope',
)
_mod = load_script_module(
    'plan-marshall',
    'manage-solution-outline',
    'manage-solution-outline.py',
    module_name='manage_solution_outline_survey_scope',
)

deliverable_write_set = _parsing.deliverable_write_set
extract_deliverables = _parsing.extract_deliverables
extract_mutation_scope = _parsing.extract_mutation_scope
extract_survey_scope = _parsing.extract_survey_scope
validate_deliverable_contract = _mod.validate_deliverable_contract

#: A deliverable in the exact form the standard mandates — the two disjoint
#: fields, no ``Affected files:`` list, and no ``(intent)`` markers, which is how
#: the standard's own worked example writes it.
_SURVEY_DELIVERABLE = """### 1. Survey the legacy loggers and classify each

**Metadata:**
- change_type: tech_debt

**Profiles:**
- implementation

**Files to survey:**
- `src/surveyed_only.py`
- `src/also_surveyed.py`

**Files expected to mutate:**
- `src/mutated.py`

**Verification:**
- Command: `./pw verify`
- Criteria: passes
"""


def _only_deliverable() -> dict[str, Any]:
    deliverables = extract_deliverables(_SURVEY_DELIVERABLE)
    assert len(deliverables) == 1, 'precondition: the fixture declares one deliverable'
    record: dict[str, Any] = deliverables[0]
    return record


def test_survey_scope_bullets_are_parsed_as_read_intent():
    """The candidate pool is analysis-only, so an unmarked bullet is ``read``.

    Asserted positively as ``read`` rather than as "not a write": a regression to
    any third value — ``None``, ``write-new`` — would satisfy a negative
    assertion while changing what the write-set contains.
    """
    entries = extract_survey_scope(_SURVEY_DELIVERABLE)

    assert entries == [
        {'path': 'src/surveyed_only.py', 'intent': 'read'},
        {'path': 'src/also_surveyed.py', 'intent': 'read'},
    ]


def test_an_explicit_marker_on_a_survey_bullet_wins_over_the_default():
    """The ``read`` default fills a gap; it never overrides a stated intent."""
    content = '**Files to survey:**\n- `src/a.py` (write-new)\n- `src/b.py`\n'

    assert extract_survey_scope(content) == [
        {'path': 'src/a.py', 'intent': 'write-new'},
        {'path': 'src/b.py', 'intent': 'read'},
    ]


def test_mutation_scope_bullets_are_parsed_with_no_defaulted_intent():
    """An unmarked mutation bullet keeps ``intent=None``.

    Distinguishing "declared a write" from "stated no intent" is what lets
    :func:`deliverable_write_set` count it as a write conservatively while the
    parsed record still reports what the author actually wrote.
    """
    assert extract_mutation_scope(_SURVEY_DELIVERABLE) == [
        {'path': 'src/mutated.py', 'intent': None}
    ]


def test_the_mutation_scope_is_the_write_set_and_the_survey_pool_is_not():
    """Both halves matter, and they fail in opposite directions.

    A write-set that omitted the mutation scope would be EMPTY here; one that
    swept in the survey pool would carry three paths. Only the correct
    membership yields exactly the mutation path.
    """
    assert deliverable_write_set(_only_deliverable()) == ['src/mutated.py']


def test_the_survey_pair_satisfies_the_affected_files_section_requirement():
    """Validation accepts the form the authoring standard mandates.

    The validator and the standard used to disagree about what a declaration
    looks like, so a correctly-authored survey deliverable was rejected outright.
    """
    errors, _warnings = validate_deliverable_contract(_only_deliverable())

    assert not any('Missing **Affected files:** section' in e for e in errors), errors


def test_a_lone_survey_field_does_NOT_satisfy_the_section_requirement():
    """Only the disjoint PAIR is a complete declaration.

    The standard requires both fields; a deliverable naming a candidate pool with
    no mutation subset has declared what it will look at and not what it will
    change. Accepting it would let the very ambiguity the two-field convention
    exists to remove back in through the validator.
    """
    lone = extract_deliverables(
        '### 1. Survey the loggers\n\n'
        '**Profiles:**\n- implementation\n\n'
        '**Files to survey:**\n- `src/surveyed_only.py`\n\n'
        '**Verification:**\n- Command: `./pw verify`\n- Criteria: passes\n'
    )[0]

    errors, _warnings = validate_deliverable_contract(lone)

    assert any('Missing **Affected files:** section' in e for e in errors), errors


def test_survey_pair_bullets_are_exempt_from_the_intent_marker_requirement():
    """Check 3b walks ``affected_files`` only, deliberately.

    The survey pair's documented form carries no markers at all, so requiring
    them would fail every correctly-authored survey deliverable — and the
    candidate pool may legitimately name a pattern, which check 3a rejects.
    """
    errors, _warnings = validate_deliverable_contract(_only_deliverable())

    assert not any('missing intent marker' in e for e in errors), errors


def test_a_glob_in_the_survey_pool_is_not_rejected_as_a_wildcard():
    """The candidate pool is where a declared SCOPE legitimately lives.

    Check 3a rejects a wildcard in ``Affected files:`` — correct for the flat
    form, wrong for a survey pool whose whole purpose is to name a scope wider
    than the enumeration. Reconciling that scope against what it matches is the
    phase-4-plan closure check's job, not the validator's.
    """
    with_glob = extract_deliverables(
        '### 1. Survey the loggers\n\n'
        '**Profiles:**\n- implementation\n\n'
        '**Files to survey:**\n- `src/**/*.py`\n\n'
        '**Files expected to mutate:**\n- `src/mutated.py`\n\n'
        '**Verification:**\n- Command: `./pw verify`\n- Criteria: passes\n'
    )[0]

    errors, _warnings = validate_deliverable_contract(with_glob)

    assert not any('Wildcard in affected files' in e for e in errors), errors

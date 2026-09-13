#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Guard: every declaration heading's paths are reachable through ``DECLARATION_FIELDS``.

``_plan_parsing`` names the declaration surface twice, from opposite ends of the
parse: ``_DECLARATION_HEADINGS`` is the heading TEXT the parser reads, and
``DECLARATION_FIELDS`` is the record KEYS both foreign selectors walk — the
per-entry ``foreign`` stamp ``manage-solution-outline list-deliverables`` applies,
and the population walk of the phase-6 pre-archive foreign-PR landing gate.

``DECLARATION_FIELDS``' own docstring rules that the two are deliberately distinct
and must be edited "in step". Nothing enforced that. A fourth heading added to the
standard and wired into the parser, but not into ``DECLARATION_FIELDS``, parses
into the deliverable record and is then skipped by BOTH selectors — its foreign
paths neither stamped nor inside the gate's population, and silently so, because a
selector that never walked a key cannot report that it missed one. That is the
incomplete-derived-set failure the constant exists to prevent, reappearing through
the one seam the constant does not cover.

The fixture here is DERIVED from ``_DECLARATION_HEADINGS`` rather than restating
today's three headings, so a heading added there produces a path this guard demands
be reachable — no edit to this module required for the guard to cover it. The
reachability computation is a pure function over ``(record, fields)`` so the
mutation control can run the SAME function over a truncated field tuple and prove
the guard reports the loss rather than assuming it would.
"""

from typing import Any

from conftest import load_script_module

_parsing = load_script_module(
    'plan-marshall',
    'manage-solution-outline',
    '_plan_parsing.py',
    module_name='_plan_parsing_declaration_fields',
)

DECLARATION_FIELDS: tuple[str, ...] = _parsing.DECLARATION_FIELDS
DECLARATION_HEADINGS: tuple[tuple[str, str | None], ...] = _parsing._DECLARATION_HEADINGS
extract_deliverables = _parsing.extract_deliverables


# --------------------------------------------------------------------------- #
# Fixture derived from the heading population
# --------------------------------------------------------------------------- #


def _sentinel_path(heading: str) -> str:
    """A path unique to one heading, so an unreachable path names its heading."""
    return 'src/{}.py'.format(heading.lower().replace(' ', '_'))


def _deliverable_declaring_every_heading() -> str:
    """One deliverable declaring a unique path under EVERY declaration heading.

    Built by walking ``_DECLARATION_HEADINGS``, so a heading added there is
    declared here without editing this module. That is what makes the assertion
    below a population-derived guard rather than a second restatement of the three
    headings — a restatement could itself go stale, which is the very failure mode
    under test.
    """
    lines = [
        '### 1. Declare a path under every declaration heading',
        '',
        '**Metadata:**',
        '- change_type: tech_debt',
        '',
        '**Profiles:**',
        '- implementation',
        '',
    ]
    for heading, _default_intent in DECLARATION_HEADINGS:
        lines += [f'**{heading}:**', f'- `{_sentinel_path(heading)}`', '']
    lines += ['**Verification:**', '- Command: `./pw verify`', '- Criteria: passes', '']
    return '\n'.join(lines)


def paths_reachable_through(record: dict[str, Any], fields: tuple[str, ...]) -> set[str]:
    """The declared paths a consumer walking ``fields`` can see on ``record``.

    The pure core of this guard, taking the field tuple as an ARGUMENT rather than
    reading the constant, so the mutation control can run it over a truncated tuple
    and observe the loss the drift would cause.
    """
    return {
        entry['path']
        for field in fields
        for entry in record.get(field, []) or []
        if isinstance(entry, dict) and entry.get('path')
    }


def _only_deliverable() -> dict[str, Any]:
    deliverables = extract_deliverables(_deliverable_declaring_every_heading())
    assert len(deliverables) == 1, 'precondition: the fixture declares one deliverable'
    record: dict[str, Any] = deliverables[0]
    return record


# --------------------------------------------------------------------------- #
# The population
# --------------------------------------------------------------------------- #


def test_the_declaration_heading_population_is_published_and_non_empty():
    """Non-empty, so no assertion below can pass over an unparsed fixture."""
    assert len(DECLARATION_HEADINGS) > 0, 'no declaration heading was read, so every assertion is vacuous'
    assert len(DECLARATION_FIELDS) > 0, 'no declaration field was read, so every assertion is vacuous'


def test_every_declared_heading_path_is_parsed_into_the_record():
    """Precondition: the parser reads each heading, so a miss below is the TUPLE's.

    Without this the next assertion could fail for an unrelated reason — a heading
    the parser never wired up — and be misread as a ``DECLARATION_FIELDS`` gap.
    """
    record = _only_deliverable()
    expected = {_sentinel_path(heading) for heading, _ in DECLARATION_HEADINGS}
    parsed = {
        entry['path']
        for value in record.values()
        if isinstance(value, list)
        for entry in value
        if isinstance(entry, dict) and entry.get('path')
    }

    assert expected <= parsed, f'the parser did not read every heading; unparsed: {sorted(expected - parsed)}'


# --------------------------------------------------------------------------- #
# The guarantee DECLARATION_FIELDS exists to provide
# --------------------------------------------------------------------------- #


def test_every_declared_heading_path_is_reachable_through_declaration_fields():
    """Both foreign selectors walk ``DECLARATION_FIELDS``; nothing may fall outside it."""
    record = _only_deliverable()
    expected = {_sentinel_path(heading) for heading, _ in DECLARATION_HEADINGS}
    reachable = paths_reachable_through(record, DECLARATION_FIELDS)

    assert reachable == expected, (
        'DECLARATION_FIELDS does not reach every declaration heading — such paths are '
        'neither foreign-stamped nor inside the pre-archive gate population; '
        f'unreachable: {sorted(expected - reachable)}'
    )


def test_declaration_fields_names_no_key_the_record_does_not_carry():
    """The mirror direction: a field naming a key ``extract_deliverables`` never emits.

    Such a field is not harmless. Both selectors ``.get`` it to an empty list, so it
    reads as a surface that exists and declares nothing — indistinguishable from one
    that was genuinely empty, and it makes the tuple over-claim its own coverage.
    """
    record = _only_deliverable()

    assert [field for field in DECLARATION_FIELDS if field not in record] == []


def test_mutation_pin_a_field_dropped_from_the_tuple_is_reported_unreachable():
    """The drift itself, fabricated: a tuple missing a field must lose that field's path.

    This is what pins the guard to the right channel. Were the reachability set
    computed from something other than the tuple, dropping a field would change
    nothing and the assertion above would pass over exactly the defect it names.
    """
    record = _only_deliverable()
    assert len(DECLARATION_FIELDS) > 1, 'the truncation must remove a field for this pin to prove anything'

    full = paths_reachable_through(record, DECLARATION_FIELDS)
    truncated = paths_reachable_through(record, DECLARATION_FIELDS[:-1])

    assert truncated < full, 'dropping a field lost no path — this pin is aimed at the wrong channel'

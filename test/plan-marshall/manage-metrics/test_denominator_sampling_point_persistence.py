#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests that each denominator is persisted TOGETHER WITH its sampling point.

The pair is what ``generate`` echoes back, and it is what makes two generations
of the same plan tell themselves apart. A fourth test pins that the two
deliverable extractors read one heading pattern rather than two, since a
disagreement there would move the denominator without moving its sampling point.
"""


import re

import _plan_parsing
from _denominator_sampling_point_fixtures import (
    _seed_phases,
    _write_outline,
    _write_references,
    _write_tasks,
    cmd_generate,
    manage_metrics,
)
from _manage_metrics_fixtures import ns_generate

# =============================================================================
# The pair: a count is never persisted without its sampling point
# =============================================================================


def test_each_denominator_is_persisted_with_its_sampling_point(plan_context):
    """All three denominators land as top-level pairs in metrics.toon.

    RED against pre-fix code, where `generate` persisted numerators only and the
    record carried no denominator at all.
    """
    plan_id = 'denom-all-three'
    plan_dir = _seed_phases(plan_id)
    _write_outline(plan_dir, 4)
    _write_references(plan_dir, ['a.py', 'b.py', 'c.md'])
    _write_tasks(plan_dir, ['done', 'done', 'pending'])

    result = cmd_generate(ns_generate(plan_id))
    assert result['status'] == 'success', result

    data = manage_metrics.read_metrics_raw(plan_id)
    # The counts are the real ones, not placeholders: 4 `### N. Title` headings
    # inside the Deliverables section (the interleaved `### Notes` headings and
    # the `### 99.` decoy under `## Approach` do NOT count), 3 affected files,
    # 2 of 3 tasks done.
    #
    # They read back as STRINGS: `read_metrics_raw` numeric-coerces per-phase
    # block values only, so every plan-level key round-trips as text — the same
    # shape `session_message_count` and the end_time-presence keys have. The
    # assertion is on the literal so the record's real format is pinned rather
    # than a coercion the reader does not perform.
    assert data['deliverable_count'] == '4'
    assert data['files_modified'] == '3'
    assert data['tasks_completed'] == '2'

    # Every count carries its sampling point, from the closed vocabulary.
    for name in ('deliverable_count', 'files_modified', 'tasks_completed'):
        point = data[f'{name}_sampling_point']
        assert point == manage_metrics.SAMPLING_POINT_GENERATE_TIME
        assert point in manage_metrics.SAMPLING_POINTS

    # One shared instant names WHEN the call counted them.
    assert data['denominators_sampled_at']


def test_generate_return_echoes_each_pair(plan_context):
    """The return TOON carries the same pairs the record does."""
    plan_id = 'denom-return'
    plan_dir = _seed_phases(plan_id)
    _write_outline(plan_dir, 2)
    _write_references(plan_dir, ['only.py'])
    _write_tasks(plan_dir, ['done'])

    result = cmd_generate(ns_generate(plan_id))

    assert result['deliverable_count'] == 2
    assert result['deliverable_count_sampling_point'] == 'generate_time'
    assert result['files_modified'] == 1
    assert result['files_modified_sampling_point'] == 'generate_time'
    assert result['tasks_completed'] == 1
    assert result['tasks_completed_sampling_point'] == 'generate_time'
    assert result['denominators_sampled_at']


# =============================================================================
# Two generations at different sampling points are distinguishable
# =============================================================================


def test_two_generations_of_the_same_plan_are_distinguishable_by_the_field(plan_context):
    """The moving denominator moves, and the record says which read it holds.

    This is the whole point of the sampling point: `affected_files` grows during
    execute, so the SAME numerator divides differently on a later read. The
    record must present the count that was current at a NAMED moment, and two
    generations must be tellable apart.
    """
    plan_id = 'denom-moving'
    plan_dir = _seed_phases(plan_id)
    _write_outline(plan_dir, 1)
    _write_references(plan_dir, ['a.py'])
    _write_tasks(plan_dir, ['done', 'pending'])

    cmd_generate(ns_generate(plan_id))
    first = manage_metrics.read_metrics_raw(plan_id)
    first_count = first['files_modified']
    first_sampled_at = first['denominators_sampled_at']

    # The plan advances: two more files are declared and the pending task closes.
    _write_references(plan_dir, ['a.py', 'b.py', 'c.py'])
    _write_tasks(plan_dir, ['done', 'done'])
    cmd_generate(ns_generate(plan_id))
    second = manage_metrics.read_metrics_raw(plan_id)

    # The counts genuinely moved — otherwise the distinguishability below would
    # be vacuous. (Plan-level keys round-trip as text; see the note in
    # `test_each_denominator_is_persisted_with_its_sampling_point`.)
    assert first_count == '1'
    assert first['tasks_completed'] == '1'
    assert second['files_modified'] == '3'
    assert second['tasks_completed'] == '2'

    # Both reads name the same moment CLASS, and the record carries the second
    # read's instant — so a consumer can tell which read it is holding.
    assert first['files_modified_sampling_point'] == 'generate_time'
    assert second['files_modified_sampling_point'] == 'generate_time'
    assert second['denominators_sampled_at'] >= first_sampled_at


# =============================================================================
# One deliverable grammar, not two producers of one number
# =============================================================================

def test_the_two_deliverable_extractors_share_one_heading_pattern(monkeypatch):
    """The agreement above is by construction, not by two matching literals.

    `extract_deliverable_headings` (what `generate` counts with) and
    `split_deliverable_blocks` (what `list-deliverables` counts through) used to
    each compile a private copy of the heading regex. Byte-identical copies
    agree until someone edits one, so the "cannot disagree" claim in
    `data-format.md` and in `_count_deliverables`' docstring rested on a
    coincidence. This pins the collapse: exactly one compiled pattern object,
    referenced by both.

    The guard is over the module's compiled OBJECTS, not over its source text. A
    `source.count("re.compile(r'^###")` scan matches one exact spelling, so a
    reintroduced private copy written with double quotes, with the prefix on the
    next line, or with leading whitespace inside the pattern would leave the
    count at 1 and the test would pass while the two extractors again held
    separate objects — a guard that cannot fail against the very thing it
    watches for.

    Counting the module's objects is still only half the claim. `vars()` sees
    module-level bindings, so an extractor that compiles a FUNCTION-LOCAL copy
    is invisible to it: the population stays at one, the count assertion stays
    green, and the two extractors are once more on separate objects. The
    substitution below closes that half — it swaps the shared object for a
    sentinel grammar and calls both extractors, so "each extractor matches
    through THIS object" is asserted by identity rather than inferred from an
    inventory.
    """
    pattern = _plan_parsing.DELIVERABLE_HEADING_PATTERN

    # Population-derived rather than text-derived: every compiled pattern the
    # module holds, not one spelling of one call site.
    heading_patterns = [
        value
        for value in vars(_plan_parsing).values()
        if isinstance(value, re.Pattern) and value.pattern.startswith('^###')
    ]

    assert heading_patterns == [pattern], (
        'the deliverable heading regex is compiled more than once — the two '
        'extractors are back to private copies that agree only by convention'
    )
    assert pattern.pattern == r'^###\s+(\d+)\.\s+(.+)$'

    # The reference, not the inventory. With the module attribute replaced by a
    # grammar that recognises `@@@ N. Title` and NOT `### N. Title`, an
    # extractor that genuinely dereferences `DELIVERABLE_HEADING_PATTERN`
    # follows the substitution and reports only the sentinel heading; one
    # holding any private copy keeps reporting the `###` heading instead. The
    # probe carries one heading of each grammar so both directions are pinned
    # by a single expected list — a stale extractor yields `['Stale grammar']`,
    # never a silently-equal count.
    sentinel = re.compile(r'^@@@\s+(\d+)\.\s+(.+)$', re.MULTILINE)
    monkeypatch.setattr(_plan_parsing, 'DELIVERABLE_HEADING_PATTERN', sentinel)

    probe = '### 1. Stale grammar\n\nbody\n\n@@@ 2. Substituted grammar\n\nbody\n'

    headings = _plan_parsing.extract_deliverable_headings(probe)
    assert [item['title'] for item in headings] == ['Substituted grammar'], (
        'extract_deliverable_headings does not match through '
        'DELIVERABLE_HEADING_PATTERN — it holds a copy of its own'
    )

    blocks = _plan_parsing.split_deliverable_blocks(probe)
    assert [item['title'] for item in blocks] == ['Substituted grammar'], (
        'split_deliverable_blocks does not split on DELIVERABLE_HEADING_PATTERN '
        '— it holds a copy of its own'
    )

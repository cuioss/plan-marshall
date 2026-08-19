#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the persisted denominators and their sampling-point discriminator.

``metrics.toon`` otherwise persists NUMERATORS only, so a script reading it
supports exactly one verdict: "this got more expensive". Every denominator a
ratio needs lived outside the record and was re-derived at render time — a
figure nobody can check.

Each denominator is also a MOVING quantity (``affected_files`` grows during
execute, the task count grows as triage appends fix-tasks, the deliverable count
can change on a Q-Gate re-entry), so the same numerator over the same plan
yields a different ratio depending on WHEN the denominator was read. That is why
these tests pin the PAIR — count plus ``{denominator}_sampling_point`` — and why
the absent case is pinned as hard as the present one: a denominator whose source
cannot be read is absent from the record, never a guessed ``0``.
"""


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
# Absent is not zero, and not a guess
# =============================================================================


def test_denominator_with_no_readable_source_is_absent_not_zero(plan_context):
    """No outline / references / tasks ⇒ no count and no sampling point.

    A `0` would read as "this plan had no deliverables", which is a claim.
    Absence reads as "this record does not carry that count", which is the truth.
    """
    plan_id = 'denom-absent'
    _seed_phases(plan_id)

    result = cmd_generate(ns_generate(plan_id))
    assert result['status'] == 'success', result

    data = manage_metrics.read_metrics_raw(plan_id)
    for name in ('deliverable_count', 'files_modified', 'tasks_completed'):
        assert name not in data, name
        assert f'{name}_sampling_point' not in data, name
        assert name not in result, name
    assert 'denominators_sampled_at' not in data
    assert 'denominators_sampled_at' not in result


def test_partially_determinable_denominators_persist_only_what_was_counted(plan_context):
    """One readable source does not manufacture the other two.

    The pair is atomic PER denominator, not per call — a plan carrying an
    outline but no references.json persists the deliverable count alone.
    """
    plan_id = 'denom-partial'
    plan_dir = _seed_phases(plan_id)
    _write_outline(plan_dir, 3)

    result = cmd_generate(ns_generate(plan_id))

    data = manage_metrics.read_metrics_raw(plan_id)
    assert data['deliverable_count'] == '3'
    assert data['deliverable_count_sampling_point'] == 'generate_time'
    # The shared instant IS written, because at least one denominator landed.
    assert data['denominators_sampled_at']
    for name in ('files_modified', 'tasks_completed'):
        assert name not in data, name
        assert f'{name}_sampling_point' not in data, name
        assert name not in result, name

#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the duplicate-number disposition across the mechanical Q-Gate.

Four call sites index a caller-supplied deliverable or task number into a
keyed collection: the prose map, the keyword-drift index and the acyclic
check's ``in_degree`` graph in ``_cmd_qgate_mechanical``, and the closure index
in ``_qgate_closure``. A bare subscript insert lets the LAST write win, which
removes one record from the indexing caller's own population while the pass
goes on reporting a measured verdict over the survivor — a completeness claim
computed over a set one element short of what it says it examined.

The acyclic check is the site that came last: it was already immune to the
PHANTOM-CYCLE direction (its denominator is the node count, not the record
count) but published nothing about the records it dropped or collapsed, so its
"no cycle" was still a verdict over a shortened set.

Every test here is paired with a control on the same shape and a distinct
number, because the assertions are about a DIFFERENCE (duplicate vs not) and a
fixture that can only produce one of the two verdicts measures nothing.
"""

from __future__ import annotations

import json
from argparse import Namespace

from _qgate_closure_fixtures import (
    _REAL_A,
    _REAL_B,
    _deliverable,
    _task,
    _write_outline,
    _write_task_file,
    check_acyclic,
    check_declared_set_closure,
    cmd_qgate_mechanical,
    index_unique_by_number,
)

# =============================================================================
# The shared indexer
# =============================================================================


def test_index_unique_by_number_reports_a_collision_rather_than_overwriting():
    """The first value survives AND the collision is published."""
    by_number, duplicates = index_unique_by_number([(1, 'first'), (2, 'other'), (1, 'second')])

    assert by_number == {1: 'first', 2: 'other'}
    assert duplicates == [1]


def test_index_unique_by_number_reports_no_collision_on_distinct_numbers():
    """Control: the same shape with distinct numbers publishes an empty list.

    Without it, ``duplicates == [1]`` above could be produced by an indexer that
    reported a collision unconditionally.
    """
    by_number, duplicates = index_unique_by_number([(1, 'first'), (2, 'second')])

    assert by_number == {1: 'first', 2: 'second'}
    assert duplicates == []


def test_index_unique_by_number_drops_an_unusable_number_without_calling_it_a_duplicate():
    """An absent / non-numeric number is dropped, not counted as a collision."""
    by_number, duplicates = index_unique_by_number([(None, 'a'), ('not-a-number', 'b'), (3, 'c')])

    assert by_number == {3: 'c'}
    assert duplicates == []


# =============================================================================
# The closure's published population
# =============================================================================


def test_closure_population_is_incomplete_when_two_deliverables_claim_one_number():
    """A collision removes a deliverable from the closure's own population.

    ``check_declared_set_closure`` PUBLISHES a completeness claim, so the
    dropped deliverable's declared set would never be run through the closure
    while ``population_complete`` still reported True.
    """
    deliverables = [_deliverable(1, affected=[_REAL_A]), _deliverable(1, affected=[_REAL_B])]

    _gaps, population = check_declared_set_closure([_task(1, 1, [_REAL_A])], deliverables)

    assert population['duplicate_deliverable_numbers'] == [1]
    assert population['population_complete'] is False


def test_closure_population_stays_complete_when_the_numbers_are_distinct():
    """Control: the same two deliverables, numbered apart, keep the claim."""
    deliverables = [_deliverable(1, affected=[_REAL_A]), _deliverable(2, affected=[_REAL_B])]

    _gaps, population = check_declared_set_closure([_task(1, 1, [_REAL_A])], deliverables)

    assert population['duplicate_deliverable_numbers'] == []
    assert population['population_complete'] is True


# =============================================================================
# End-to-end through the mechanical Q-Gate
# =============================================================================


def test_a_duplicate_deliverable_number_makes_the_mechanical_pass_ambiguous(plan_context):
    """Two ``### 1.`` blocks withhold the pass's authority over the outline.

    The records that DID parse are still returned, so every check still reports
    what it can; what is withheld is the claim that the mechanical pass was
    authoritative — which is exactly what ``ambiguous`` carries to the caller.
    """
    plan_dir = plan_context.plan_dir_for('dup-number-e2e')
    _write_outline(
        plan_dir,
        f'### 1. Widen the sweep\n\n'
        f'**Affected files:**\n- `{_REAL_A}` (write-replace)\n\n'
        f'### 1. Widen it again\n\n'
        f'**Affected files:**\n- `{_REAL_B}` (write-replace)\n',
    )
    _write_task_file(plan_dir / 'tasks', _task(1, 1, [_REAL_A]))

    result = cmd_qgate_mechanical(Namespace(plan_id='dup-number-e2e', no_emit=True))

    assert result['ambiguous'] is True
    assert result['population']['declared_set_closure']['duplicate_deliverable_numbers'] == [1]


def test_the_same_outline_numbered_apart_is_not_ambiguous(plan_context):
    """Control: the identical shape with distinct numbers reports authoritative.

    This is what makes the ``ambiguous is True`` above a measurement rather than
    a constant — the flag has to be able to read False on a neighbouring input.
    """
    plan_dir = plan_context.plan_dir_for('dup-number-control')
    _write_outline(
        plan_dir,
        f'### 1. Widen the sweep\n\n'
        f'**Affected files:**\n- `{_REAL_A}` (write-replace)\n\n'
        f'### 2. Widen it again\n\n'
        f'**Affected files:**\n- `{_REAL_B}` (write-replace)\n',
    )
    _write_task_file(plan_dir / 'tasks', _task(1, 1, [_REAL_A]))
    _write_task_file(plan_dir / 'tasks', _task(2, 2, [_REAL_B]))

    result = cmd_qgate_mechanical(Namespace(plan_id='dup-number-control', no_emit=True))

    assert result['ambiguous'] is False
    assert result['population']['declared_set_closure']['duplicate_deliverable_numbers'] == []


# =============================================================================
# The acyclic check's denominator
# =============================================================================


def test_duplicate_task_numbers_are_disclosed_rather_than_absorbed():
    """Kahn's denominator is the NODE count — and the collapse is PUBLISHED.

    ``in_degree`` is keyed by task number, so two records sharing a number
    collapse to one node. Comparing ``visited`` against the record LIST would
    make the shortfall true with no cycle present — and the finding it emits
    names no task at all, because ``cycle_members`` is derived from the same
    already-collapsed ``in_degree``. So the check must NOT fire a cycle finding.

    But not firing is only half the disposition, and the half that was missing is
    the one this module exists to enforce: a clean ``(0, 0)`` return said the
    graph was acyclic over a node set one record shorter than the list handed in,
    with nothing in the result saying so. That is the same
    completeness-over-a-shortened-set claim ``index_unique_by_number`` refuses at
    its own call sites — "Every caller treats a non-empty ``duplicate_numbers``
    as a POPULATION defect" — and the DAG check was the one site in the pair not
    following it.
    """
    tasks = [_task(1, 1, [_REAL_A]), _task(1, 1, [_REAL_B])]

    failed, emitted, population = check_acyclic('dup-task-number', tasks, [], emit=False)

    assert failed == 0, 'a collapsed duplicate must not read as an unvisited cycle member'
    assert emitted == 0
    assert population['duplicate_task_numbers'] == [1]
    assert population['tasks_scanned'] == 2
    assert population['nodes_indexed'] == 1
    assert population['population_complete'] is False


def test_distinct_task_numbers_keep_the_population_claim():
    """Control: the same two records, numbered apart, publish a complete population.

    Without it, the disclosure above could be produced by a check that reported
    a collapse unconditionally.
    """
    tasks = [_task(1, 1, [_REAL_A]), _task(2, 1, [_REAL_B])]

    failed, _emitted, population = check_acyclic('distinct-task-numbers', tasks, [], emit=False)

    assert failed == 0
    assert population['duplicate_task_numbers'] == []
    assert population['nodes_indexed'] == 2
    assert population['population_complete'] is True


def test_a_real_cycle_is_still_reported():
    """Control: the check has not been defanged into never firing."""
    tasks = [
        {**_task(1, 1, [_REAL_A]), 'depends_on': ['TASK-002']},
        {**_task(2, 1, [_REAL_B]), 'depends_on': ['TASK-001']},
    ]

    failed, _emitted, _population = check_acyclic('real-cycle', tasks, [], emit=False)

    assert failed == 1


def test_a_duplicate_task_number_makes_the_mechanical_pass_ambiguous(plan_context):
    """End-to-end: the collapse withholds the pass's authority, as the outline case does.

    The deliverable-number sibling above already reaches ``ambiguous`` through
    ``declared_set_closure``. This is the task-number half of the same rule
    arriving at the same place, so a plan whose task records collapse cannot be
    signed off by a mechanical zero.
    """
    plan_dir = plan_context.plan_dir_for('dup-task-number-e2e')
    _write_outline(
        plan_dir,
        f'### 1. Widen the sweep\n\n**Affected files:**\n- `{_REAL_A}` (write-replace)\n',
    )
    # Two task FILES whose records both claim number 1. The second is written
    # directly rather than through ``_write_task_file``, which derives the
    # filename FROM the record's number and would therefore overwrite the first.
    # Nothing in production validates that a record's ``number`` matches its
    # TASK-NNN filename, which is exactly what makes this collapse reachable from
    # a real plan directory rather than only from a hand-built list.
    task_dir = plan_dir / 'tasks'
    _write_task_file(task_dir, _task(1, 1, [_REAL_A]))
    collided = json.loads((task_dir / 'TASK-001.json').read_text(encoding='utf-8'))
    (task_dir / 'TASK-002.json').write_text(json.dumps(collided, indent=2), encoding='utf-8')

    result = cmd_qgate_mechanical(Namespace(plan_id='dup-task-number-e2e', no_emit=True))

    assert result['population']['acyclic']['duplicate_task_numbers'] == [1]
    assert result['population_complete'] is False
    assert result['ambiguous'] is True

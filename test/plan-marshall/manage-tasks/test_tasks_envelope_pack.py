#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the deterministic envelope bin-packer (_tasks_envelope.py).

The pure packer in ``_tasks_envelope.py`` groups already-sized tasks into
budget-bounded execution *envelope groups* using Next-Fit in task order. It is a
pure, deterministic, total function — no LLM judgement, no I/O, no globals — so
these tests pin its behaviour by direct import:

* the private ``_task_cost`` extractor (presence / type / sign validation);
* ``pack_envelopes`` over the full envelope-packing surface: single-task
  envelopes, multi-task packing within budget, overflow into a second envelope,
  the over-budget-task-lands-alone rule, contiguity / order preservation, the
  per-envelope summary shape, and determinism (same input → same grouping);
* the empty-list and single-oversized-task edge cases the task contract calls
  out.

Tier 2 (direct import) tests cover the pure functions; Tier 3 subprocess tests
exercise the ``pack-envelopes`` CLI plumbing in ``manage-tasks`` against
on-disk task files seeded into the plan's ``tasks/`` directory.
"""


import pytest
from _tasks_envelope_fixtures import _task, _task_cost, pack_envelopes

# =============================================================================
# _task_cost — cost extraction & validation
# =============================================================================


def test_task_cost_returns_stamped_value():
    """A stamped integer cost is returned unchanged."""
    assert _task_cost({'predicted_cost_tokens': 25_000}) == 25_000


def test_task_cost_coerces_integer_string():
    """A stamped magnitude written as a numeric string is coerced to int."""
    assert _task_cost({'predicted_cost_tokens': '60000'}) == 60_000


def test_task_cost_accepts_zero():
    """A zero cost is a valid non-negative magnitude."""
    assert _task_cost({'predicted_cost_tokens': 0}) == 0


def test_task_cost_rejects_missing_field():
    """A task missing predicted_cost_tokens raises ValueError."""
    with pytest.raises(ValueError, match='predicted_cost_tokens'):
        _task_cost({'number': 1})


def test_task_cost_rejects_non_integer():
    """A non-integer magnitude raises ValueError."""
    with pytest.raises(ValueError, match='predicted_cost_tokens'):
        _task_cost({'predicted_cost_tokens': 'huge'})


def test_task_cost_rejects_none():
    """A None magnitude raises ValueError."""
    with pytest.raises(ValueError, match='predicted_cost_tokens'):
        _task_cost({'predicted_cost_tokens': None})


def test_task_cost_rejects_negative():
    """A negative magnitude raises ValueError."""
    with pytest.raises(ValueError, match='non-negative'):
        _task_cost({'predicted_cost_tokens': -1})


# =============================================================================
# pack_envelopes — edge cases (empty list, budget validation)
# =============================================================================


def test_pack_empty_task_list_returns_empty():
    """An empty task list returns ([], [])."""
    assignments, envelopes = pack_envelopes([], per_envelope_budget_tokens=100)
    assert assignments == []
    assert envelopes == []


def test_pack_rejects_zero_budget():
    """A zero budget raises ValueError."""
    with pytest.raises(ValueError, match='per_envelope_budget_tokens'):
        pack_envelopes([_task(1, 10)], per_envelope_budget_tokens=0)


def test_pack_rejects_negative_budget():
    """A negative budget raises ValueError."""
    with pytest.raises(ValueError, match='per_envelope_budget_tokens'):
        pack_envelopes([_task(1, 10)], per_envelope_budget_tokens=-100)


def test_pack_propagates_missing_cost_error():
    """A task missing predicted_cost_tokens propagates _task_cost's ValueError."""
    with pytest.raises(ValueError, match='predicted_cost_tokens'):
        pack_envelopes([{'number': 1}], per_envelope_budget_tokens=100)


# =============================================================================
# pack_envelopes — single-task envelopes
# =============================================================================


def test_pack_single_task_under_budget():
    """A single sub-budget task lands alone in envelope 1."""
    tasks = [_task(1, 40)]
    assignments, envelopes = pack_envelopes(tasks, per_envelope_budget_tokens=100)

    assert assignments == [(tasks[0], 1)]
    assert envelopes == [{'envelope_id': 1, 'task_count': 1, 'total_cost_tokens': 40}]


def test_pack_single_task_exactly_at_budget():
    """A single task whose cost equals the budget still fits in one envelope."""
    tasks = [_task(1, 100)]
    assignments, envelopes = pack_envelopes(tasks, per_envelope_budget_tokens=100)

    assert assignments == [(tasks[0], 1)]
    assert envelopes == [{'envelope_id': 1, 'task_count': 1, 'total_cost_tokens': 100}]


def test_pack_single_oversized_task_lands_alone():
    """A single task whose cost exceeds the budget is placed alone in envelope 1."""
    tasks = [_task(1, 500)]
    assignments, envelopes = pack_envelopes(tasks, per_envelope_budget_tokens=100)

    assert assignments == [(tasks[0], 1)]
    assert envelopes == [{'envelope_id': 1, 'task_count': 1, 'total_cost_tokens': 500}]


# =============================================================================
# pack_envelopes — multi-task packing within budget
# =============================================================================


def test_pack_multiple_tasks_fit_one_envelope():
    """Tasks whose summed cost is under budget all share envelope 1."""
    tasks = [_task(1, 30), _task(2, 30), _task(3, 30)]
    assignments, envelopes = pack_envelopes(tasks, per_envelope_budget_tokens=100)

    assert [eid for _t, eid in assignments] == [1, 1, 1]
    assert envelopes == [{'envelope_id': 1, 'task_count': 3, 'total_cost_tokens': 90}]


def test_pack_sum_exactly_at_budget_stays_one_envelope():
    """A run whose summed cost exactly equals the budget stays in one envelope."""
    tasks = [_task(1, 40), _task(2, 60)]
    assignments, envelopes = pack_envelopes(tasks, per_envelope_budget_tokens=100)

    assert [eid for _t, eid in assignments] == [1, 1]
    assert envelopes == [{'envelope_id': 1, 'task_count': 2, 'total_cost_tokens': 100}]

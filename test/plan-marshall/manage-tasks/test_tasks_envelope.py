#!/usr/bin/env python3
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

import json
from itertools import pairwise

import pytest

from conftest import get_script_path, load_script_module, run_script

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-tasks', 'manage-tasks.py')

_envelope = load_script_module(
    'plan-marshall', 'manage-tasks', '_tasks_envelope.py', '_tasks_envelope_under_test'
)

pack_envelopes = _envelope.pack_envelopes
_task_cost = _envelope._task_cost


def _task(number, cost):
    """Build a minimal sized task record carrying ``predicted_cost_tokens``."""
    return {'number': number, 'predicted_cost_tokens': cost}


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


# =============================================================================
# pack_envelopes — overflow into a second envelope
# =============================================================================


def test_pack_overflow_opens_second_envelope():
    """Adding a task that would exceed the budget rolls into a new envelope."""
    tasks = [_task(1, 60), _task(2, 60)]
    assignments, envelopes = pack_envelopes(tasks, per_envelope_budget_tokens=100)

    assert [eid for _t, eid in assignments] == [1, 2]
    assert envelopes == [
        {'envelope_id': 1, 'task_count': 1, 'total_cost_tokens': 60},
        {'envelope_id': 2, 'task_count': 1, 'total_cost_tokens': 60},
    ]


def test_pack_next_fit_does_not_backfill():
    """Next-Fit never backfills an earlier envelope once a new one is opened.

    Task 2 overflows envelope 1; task 3 (cost 10) would fit in envelope 1's
    remaining room, but Next-Fit only ever appends to the current open
    envelope, so task 3 joins envelope 2.
    """
    tasks = [_task(1, 60), _task(2, 60), _task(3, 10)]
    assignments, envelopes = pack_envelopes(tasks, per_envelope_budget_tokens=100)

    assert [eid for _t, eid in assignments] == [1, 2, 2]
    assert envelopes == [
        {'envelope_id': 1, 'task_count': 1, 'total_cost_tokens': 60},
        {'envelope_id': 2, 'task_count': 2, 'total_cost_tokens': 70},
    ]


def test_pack_oversized_task_does_not_block_following_task():
    """An over-budget task lands alone, and the next task opens a fresh envelope.

    The over-budget task (cost 500) sits alone in envelope 2; because it is
    already alone in a fresh envelope it is never rolled again, so task 3 opens
    envelope 3 rather than being forced to share the oversized envelope.
    """
    tasks = [_task(1, 40), _task(2, 500), _task(3, 40)]
    assignments, envelopes = pack_envelopes(tasks, per_envelope_budget_tokens=100)

    assert [eid for _t, eid in assignments] == [1, 2, 3]
    assert envelopes == [
        {'envelope_id': 1, 'task_count': 1, 'total_cost_tokens': 40},
        {'envelope_id': 2, 'task_count': 1, 'total_cost_tokens': 500},
        {'envelope_id': 3, 'task_count': 1, 'total_cost_tokens': 40},
    ]


def test_pack_zero_cost_tasks_pack_together():
    """Zero-cost tasks never trigger an overflow and all share one envelope."""
    tasks = [_task(1, 0), _task(2, 0), _task(3, 0)]
    assignments, envelopes = pack_envelopes(tasks, per_envelope_budget_tokens=100)

    assert [eid for _t, eid in assignments] == [1, 1, 1]
    assert envelopes == [{'envelope_id': 1, 'task_count': 3, 'total_cost_tokens': 0}]


# =============================================================================
# pack_envelopes — contiguity, order preservation, invariants
# =============================================================================


def test_pack_preserves_input_order():
    """Assignments are returned in input order; the packer never reorders."""
    tasks = [_task(3, 30), _task(1, 30), _task(2, 30)]
    assignments, _envelopes = pack_envelopes(tasks, per_envelope_budget_tokens=100)

    assert [task['number'] for task, _eid in assignments] == [3, 1, 2]


def test_pack_envelope_ids_are_contiguous_runs():
    """Envelope ids form non-decreasing contiguous runs over the task order."""
    tasks = [_task(1, 60), _task(2, 60), _task(3, 60), _task(4, 60)]
    assignments, _envelopes = pack_envelopes(tasks, per_envelope_budget_tokens=100)

    ids = [eid for _t, eid in assignments]
    # Non-decreasing.
    assert ids == sorted(ids)
    # Each task that does not start a new run shares its predecessor's id ± at
    # most 1 — i.e. ids step up by exactly 1 at envelope boundaries.
    for prev, cur in pairwise(ids):
        assert cur in (prev, prev + 1)


def test_pack_assignment_count_matches_input():
    """Every input task appears exactly once in the assignments list."""
    tasks = [_task(n, 30) for n in range(1, 11)]
    assignments, _envelopes = pack_envelopes(tasks, per_envelope_budget_tokens=100)

    assert len(assignments) == len(tasks)
    assert {task['number'] for task, _eid in assignments} == set(range(1, 11))


def test_pack_envelope_summary_totals_match_assignments():
    """Each envelope's task_count and total_cost_tokens reconcile to its members."""
    tasks = [_task(1, 60), _task(2, 60), _task(3, 30), _task(4, 30)]
    assignments, envelopes = pack_envelopes(tasks, per_envelope_budget_tokens=100)

    for env in envelopes:
        members = [
            _task_cost(task) for task, eid in assignments if eid == env['envelope_id']
        ]
        assert env['task_count'] == len(members)
        assert env['total_cost_tokens'] == sum(members)


def test_pack_no_envelope_summary_for_empty_run():
    """The number of envelope summaries equals the number of distinct ids used."""
    tasks = [_task(1, 60), _task(2, 60), _task(3, 60)]
    assignments, envelopes = pack_envelopes(tasks, per_envelope_budget_tokens=100)

    distinct_ids = {eid for _t, eid in assignments}
    assert len(envelopes) == len(distinct_ids)
    assert [env['envelope_id'] for env in envelopes] == sorted(distinct_ids)


# =============================================================================
# pack_envelopes — determinism
# =============================================================================


def test_pack_is_deterministic():
    """Identical input always yields identical grouping."""
    tasks = [_task(1, 40), _task(2, 70), _task(3, 30), _task(4, 90), _task(5, 20)]
    first = pack_envelopes(tasks, per_envelope_budget_tokens=100)
    second = pack_envelopes(tasks, per_envelope_budget_tokens=100)
    assert first == second


def test_pack_determinism_independent_of_call_history():
    """A fresh packer call on the same input is unaffected by prior calls."""
    tasks_a = [_task(1, 50), _task(2, 60)]
    tasks_b = [_task(1, 50), _task(2, 60)]
    pack_envelopes([_task(1, 10)], per_envelope_budget_tokens=5)  # noisy interleaved call
    assert pack_envelopes(tasks_a, per_envelope_budget_tokens=100) == pack_envelopes(
        tasks_b, per_envelope_budget_tokens=100
    )


# =============================================================================
# pack-envelopes — CLI plumbing (Tier 3, on-disk task files)
# =============================================================================


def _seed_task_file(plan_dir, number, cost):
    """Write a minimal TASK-NNN.json carrying predicted_cost_tokens."""
    tasks_dir = plan_dir / 'tasks'
    tasks_dir.mkdir(parents=True, exist_ok=True)
    task = {
        'number': number,
        'title': f'task {number}',
        'predicted_cost_tokens': cost,
        'steps': [],
    }
    (tasks_dir / f'TASK-{number:03d}.json').write_text(
        json.dumps(task, indent=2), encoding='utf-8'
    )


def test_cli_pack_envelopes_returns_success(plan_context):
    """The pack-envelopes subcommand returns a success TOON with envelope_count."""
    plan_dir = plan_context.plan_dir_for('env-success')
    _seed_task_file(plan_dir, 1, 60)
    _seed_task_file(plan_dir, 2, 60)

    result = run_script(
        SCRIPT_PATH,
        'pack-envelopes',
        '--plan-id', 'env-success',
        '--per-envelope-budget-tokens', '100',
    )

    assert result.returncode == 0
    assert 'status: success' in result.stdout
    assert 'envelope_count: 2' in result.stdout


def test_cli_pack_envelopes_single_envelope(plan_context):
    """Tasks that fit one envelope report envelope_count 1."""
    plan_dir = plan_context.plan_dir_for('env-single')
    _seed_task_file(plan_dir, 1, 30)
    _seed_task_file(plan_dir, 2, 30)

    result = run_script(
        SCRIPT_PATH,
        'pack-envelopes',
        '--plan-id', 'env-single',
        '--per-envelope-budget-tokens', '100',
    )

    assert result.returncode == 0
    assert 'envelope_count: 1' in result.stdout


def test_cli_pack_envelopes_empty_plan(plan_context):
    """A plan with no tasks packs into zero envelopes."""
    plan_context.plan_dir_for('env-empty')

    result = run_script(
        SCRIPT_PATH,
        'pack-envelopes',
        '--plan-id', 'env-empty',
        '--per-envelope-budget-tokens', '100',
    )

    assert result.returncode == 0
    assert 'status: success' in result.stdout
    assert 'envelope_count: 0' in result.stdout


def test_cli_pack_envelopes_rejects_non_positive_budget(plan_context):
    """A non-positive budget yields a status: error TOON (packer ValueError)."""
    plan_dir = plan_context.plan_dir_for('env-bad-budget')
    _seed_task_file(plan_dir, 1, 30)

    result = run_script(
        SCRIPT_PATH,
        'pack-envelopes',
        '--plan-id', 'env-bad-budget',
        '--per-envelope-budget-tokens', '0',
    )

    assert result.returncode == 0
    assert 'status: error' in result.stdout


def test_cli_pack_envelopes_reports_error_for_unsized_task(plan_context):
    """A task missing predicted_cost_tokens yields a status: error TOON."""
    plan_dir = plan_context.plan_dir_for('env-unsized')
    tasks_dir = plan_dir / 'tasks'
    tasks_dir.mkdir(parents=True, exist_ok=True)
    (tasks_dir / 'TASK-001.json').write_text(
        json.dumps({'number': 1, 'title': 'unsized', 'steps': []}, indent=2),
        encoding='utf-8',
    )

    result = run_script(
        SCRIPT_PATH,
        'pack-envelopes',
        '--plan-id', 'env-unsized',
        '--per-envelope-budget-tokens', '100',
    )

    assert result.returncode == 0
    assert 'status: error' in result.stdout


def test_cli_pack_envelopes_missing_budget_arg_exits_2(plan_context):
    """Omitting the required --per-envelope-budget-tokens flag is an argparse rejection."""
    plan_context.plan_dir_for('env-no-budget')

    result = run_script(
        SCRIPT_PATH,
        'pack-envelopes',
        '--plan-id', 'env-no-budget',
    )

    assert result.returncode == 2

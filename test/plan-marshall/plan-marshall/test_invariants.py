#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for the ``task_graph_valid`` and ``task_state_hash`` invariants.

Drives ``_capture_task_graph_valid`` and ``_capture_task_state_hash``
directly with real task fixtures created via the ``manage-tasks``
command API (no direct TASK-*.json writes). ``_run_script`` is stubbed
to invoke the manage-tasks query commands in-process and serialize
their TOON output — this avoids relying on a live
``.plan/execute-script.py`` being present in the test worktree while
still exercising the real cycle/dangling/hash pipeline inside the
invariants.

``task_graph_valid`` cases:
    a. Healthy linear graph  → deterministic 16-char hex hash.
    b. Healthy branching graph → different deterministic hash.
    c. Self-cycle → TaskGraphInvalid with non-empty cycle.
    d. Longer cycle (3 nodes) → TaskGraphInvalid with full cycle path.
    e. Dangling reference → TaskGraphInvalid with non-empty dangling.
    f. Empty task list → stable zero-edge hash, no raise.
    g. capture_all surfaces TaskGraphInvalid on broken graph.

``task_state_hash`` cases:
    h. Non-empty plan → non-empty 16-char hex hash (regression guard
       against the ``parsed.get('tasks')`` bug where the invariant
       silently hashed an empty list regardless of task count).
    i. Changing task ``status`` changes the hash.
    j. Changing task ``depends_on`` changes the hash.
    k. Changing a step's status via ``finalize-step`` changes the hash.
    l. No-op recapture yields the same hash (determinism).
    m. Empty-task-list plan yields the stable zero-task hash.
"""

from __future__ import annotations

import json
import sys
from argparse import Namespace
from pathlib import Path

import pytest
from conftest import get_script_path, load_script_module  # type: ignore[import-not-found]

# =============================================================================
# Import the invariants module under test.
# =============================================================================

SCRIPT_PATH = get_script_path('plan-marshall', 'plan-marshall', 'phase_handshake.py')
SCRIPTS_DIR = SCRIPT_PATH.parent

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import _invariants as inv  # noqa: E402


# =============================================================================
# Load manage-tasks command handlers via the shared conftest loader — gives us
# in-process fixture creation without needing a subprocess wrapper.
# =============================================================================

_crud = load_script_module('plan-marshall', 'manage-tasks', '_tasks_crud.py', '_invariants_test_tasks_crud')
_query = load_script_module('plan-marshall', 'manage-tasks', '_tasks_query.py', '_invariants_test_tasks_query')
_step = load_script_module('plan-marshall', 'manage-tasks', '_cmd_step.py', '_invariants_test_tasks_step')

cmd_prepare_add = _crud.cmd_prepare_add
cmd_commit_add = _crud.cmd_commit_add
cmd_update = _crud.cmd_update
cmd_list = _query.cmd_list
cmd_read = _query.cmd_read
cmd_finalize_step = _step.cmd_finalize_step


# =============================================================================
# Helpers: create tasks via the manage-tasks path-allocate flow.
# =============================================================================


def _build_task_toon(
    title: str,
    deliverable: int,
    steps: list[str],
    depends_on: str = 'none',
    domain: str = 'python',
    description: str = 'Invariant fixture task',
) -> str:
    """Build a minimal valid TOON task definition.

    Mirrors ``test_manage_tasks.build_task_toon`` but kept local so this
    test file stays import-light (no cross-file helper dependency).
    """
    lines = [
        f'title: {title}',
        f'deliverable: {deliverable}',
        f'domain: {domain}',
        f'description: {description}',
        'steps:',
    ]
    for step in steps:
        # The required per-step intent marker is appended unless the caller
        # already supplied one (so a test may pin a specific intent).
        if step.rstrip().endswith(')'):
            lines.append(f'  - {step}')
        else:
            lines.append(f'  - {step} (write-replace)')
    lines.append(f'depends_on: {depends_on}')
    return '\n'.join(lines)


def _add_task(plan_id: str, title: str, number_hint: int, depends_on: str = 'none') -> dict:
    """Drive prepare-add → write scratch → commit-add."""
    prep = cmd_prepare_add(Namespace(plan_id=plan_id, slot=None))
    assert prep.get('status') == 'success', f'prepare-add failed: {prep}'
    toon = _build_task_toon(
        title=title,
        deliverable=1,
        steps=[f'src/file{number_hint}.py'],
        depends_on=depends_on,
    )
    Path(prep['path']).write_text(toon, encoding='utf-8')
    result = cmd_commit_add(Namespace(plan_id=plan_id, slot=None))
    assert result.get('status') == 'success', f'commit-add failed: {result}'
    return result


def _set_depends_on(plan_id: str, number: int, depends_on: list[str]) -> None:
    """Retroactively set ``depends_on`` so cycles can be constructed."""
    result = cmd_update(
        Namespace(
            plan_id=plan_id,
            task_number=number,
            title=None,
            description=None,
            depends_on=depends_on,
            status=None,
            domain=None,
            profile=None,
            skills=None,
            deliverable=None,
        )
    )
    assert result.get('status') == 'success', f'update failed: {result}'


def _set_status(plan_id: str, number: int, status: str) -> None:
    """Retroactively set a task's ``status`` field."""
    result = cmd_update(
        Namespace(
            plan_id=plan_id,
            task_number=number,
            title=None,
            description=None,
            depends_on=None,
            status=status,
            domain=None,
            profile=None,
            skills=None,
            deliverable=None,
        )
    )
    assert result.get('status') == 'success', f'update failed: {result}'


def _finalize_step(plan_id: str, task: int, step: int, outcome: str) -> None:
    """Mark a step with outcome (done/skipped/failed)."""
    result = cmd_finalize_step(Namespace(plan_id=plan_id, task_number=task, step=step, outcome=outcome))
    assert result.get('status') == 'success', f'finalize-step failed: {result}'


# =============================================================================
# Stub: make _run_script dispatch to the in-process manage-tasks handlers.
# This bypasses the subprocess hop (no .plan/execute-script.py needed in
# the worktree) while still exercising the real invariant code path and
# the real manage-tasks TOON serialization.
# =============================================================================


def _make_stub_run_script():
    """Return a function that mimics ``_run_script`` for manage-tasks calls."""
    from file_ops import serialize_toon  # type: ignore[import-not-found]

    def _stub(args: list[str]) -> str | None:
        # args shape per _invariants._capture_task_graph_valid:
        #   [notation, subcommand, '--plan-id', plan_id, ...]
        # Or per _capture_unfinished_tasks_count:
        #   [notation, 'list', '--status', 'pending', '--plan-id', plan_id]
        if len(args) < 4:
            return None
        notation = args[0]
        if notation != 'plan-marshall:manage-tasks:manage-tasks':
            return None
        subcommand = args[1]
        # Locate the --plan-id flag instead of assuming a fixed position so
        # both the 4-arg list/get shape and the 6-arg list-with-status shape
        # are handled uniformly.
        try:
            pid_idx = args.index('--plan-id')
        except ValueError:
            return None
        if pid_idx + 1 >= len(args):
            return None
        plan_id = args[pid_idx + 1]
        if subcommand == 'list':
            # Optional --status <value>
            status_filter = 'all'
            if '--status' in args:
                s_idx = args.index('--status')
                if s_idx + 1 < len(args):
                    status_filter = args[s_idx + 1]
            ns = Namespace(
                plan_id=plan_id,
                status=status_filter,
                deliverable=None,
                ready=False,
            )
            return serialize_toon(cmd_list(ns))
        if subcommand == 'read':
            # args[...] contains '--task-number', followed by the number
            t_idx = args.index('--task-number')
            number = int(args[t_idx + 1])
            ns = Namespace(plan_id=plan_id, task_number=number)
            return serialize_toon(cmd_read(ns))
        return None

    return _stub


@pytest.fixture
def stub_run_script(monkeypatch: pytest.MonkeyPatch) -> None:
    """Redirect ``inv._run_script`` to the in-process stub."""
    monkeypatch.setattr(inv, '_run_script', _make_stub_run_script())


# =============================================================================
# (a) Healthy linear graph
# =============================================================================


def test_linear_graph_returns_16char_hex_hash(plan_context, stub_run_script) -> None:
    """TASK-1 ← TASK-2 ← TASK-3 produces a 16-char hex hash."""
    _add_task('inv-linear', 'T1', 1)
    _add_task('inv-linear', 'T2', 2, depends_on='TASK-1')
    _add_task('inv-linear', 'T3', 3, depends_on='TASK-2')

    result = inv._capture_task_graph_valid('inv-linear', {}, '5-execute')

    assert isinstance(result, str), f'expected hash string, got {result!r}'
    assert len(result) == 16, f'expected 16-char hash, got {len(result)} chars: {result}'
    assert all(c in '0123456789abcdef' for c in result), f'expected lowercase hex, got {result!r}'


def test_linear_graph_hash_changes_when_edges_change(plan_context, stub_run_script) -> None:
    """Adding an edge yields a different hash (determinism check part 1)."""
    _add_task('inv-linear-a', 'T1', 1)
    _add_task('inv-linear-a', 'T2', 2, depends_on='TASK-1')
    hash_two_nodes = inv._capture_task_graph_valid('inv-linear-a', {}, '5-execute')

    _add_task('inv-linear-b', 'T1', 1)
    _add_task('inv-linear-b', 'T2', 2, depends_on='TASK-1')
    _add_task('inv-linear-b', 'T3', 3, depends_on='TASK-2')
    hash_three_nodes = inv._capture_task_graph_valid('inv-linear-b', {}, '5-execute')

    assert hash_two_nodes != hash_three_nodes, 'hash must change when an edge is added'


def test_linear_graph_hash_is_deterministic_across_runs(plan_context, stub_run_script) -> None:
    """Same edge set must produce the same hash (determinism check part 2)."""
    _add_task('inv-det-1', 'T1', 1)
    _add_task('inv-det-1', 'T2', 2, depends_on='TASK-1')
    _add_task('inv-det-1', 'T3', 3, depends_on='TASK-2')
    first = inv._capture_task_graph_valid('inv-det-1', {}, '5-execute')

    _add_task('inv-det-2', 'T1', 1)
    _add_task('inv-det-2', 'T2', 2, depends_on='TASK-1')
    _add_task('inv-det-2', 'T3', 3, depends_on='TASK-2')
    second = inv._capture_task_graph_valid('inv-det-2', {}, '5-execute')

    assert first == second, 'same edge set must produce the same hash'


# =============================================================================
# (b) Healthy branching graph
# =============================================================================


def test_branching_graph_returns_different_deterministic_hash(plan_context, stub_run_script) -> None:
    """TASK-1 ← {TASK-2, TASK-3}, TASK-2 ← TASK-4 — different shape, different hash."""
    # Branching run #1.
    _add_task('inv-branch-1', 'T1', 1)
    _add_task('inv-branch-1', 'T2', 2, depends_on='TASK-1')
    _add_task('inv-branch-1', 'T3', 3, depends_on='TASK-1')
    _add_task('inv-branch-1', 'T4', 4, depends_on='TASK-2')
    branching_a = inv._capture_task_graph_valid('inv-branch-1', {}, '5-execute')

    # Branching run #2 (same topology) — must match for determinism.
    _add_task('inv-branch-2', 'T1', 1)
    _add_task('inv-branch-2', 'T2', 2, depends_on='TASK-1')
    _add_task('inv-branch-2', 'T3', 3, depends_on='TASK-1')
    _add_task('inv-branch-2', 'T4', 4, depends_on='TASK-2')
    branching_b = inv._capture_task_graph_valid('inv-branch-2', {}, '5-execute')

    # Linear run of same node count — must differ because edges differ.
    _add_task('inv-branch-linear', 'T1', 1)
    _add_task('inv-branch-linear', 'T2', 2, depends_on='TASK-1')
    _add_task('inv-branch-linear', 'T3', 3, depends_on='TASK-2')
    _add_task('inv-branch-linear', 'T4', 4, depends_on='TASK-3')
    linear_same_size = inv._capture_task_graph_valid('inv-branch-linear', {}, '5-execute')

    assert isinstance(branching_a, str) and len(branching_a) == 16
    assert branching_a == branching_b, 'branching graph hash must be deterministic across runs'
    assert branching_a != linear_same_size, 'branching graph must hash differently than linear graph of same size'


# =============================================================================
# (c) Self-cycle
# =============================================================================


def test_self_cycle_raises_with_non_empty_cycle(plan_context, stub_run_script) -> None:
    """TASK-1 depends on TASK-1 → TaskGraphInvalid, cycle contains TASK-1."""
    _add_task('inv-self-cycle', 'T1', 1)
    _set_depends_on('inv-self-cycle', 1, ['TASK-1'])

    with pytest.raises(inv.TaskGraphInvalid) as excinfo:
        inv._capture_task_graph_valid('inv-self-cycle', {}, '5-execute')

    err = excinfo.value
    assert err.cycle, 'cycle must be non-empty on self-loop'
    assert 'TASK-1' in err.cycle, f'cycle must include TASK-1, got {err.cycle}'
    assert err.dangling == [], f'dangling must be empty, got {err.dangling}'


# =============================================================================
# (d) Longer cycle (3 nodes)
# =============================================================================


def test_three_node_cycle_raises_with_full_cycle_path(plan_context, stub_run_script) -> None:
    """TASK-1 → TASK-2 → TASK-3 → TASK-1 yields a cycle covering all three nodes."""
    _add_task('inv-3cycle', 'T1', 1)
    _add_task('inv-3cycle', 'T2', 2, depends_on='TASK-1')
    _add_task('inv-3cycle', 'T3', 3, depends_on='TASK-2')
    # Close the cycle: TASK-1 now depends on TASK-3.
    _set_depends_on('inv-3cycle', 1, ['TASK-3'])

    with pytest.raises(inv.TaskGraphInvalid) as excinfo:
        inv._capture_task_graph_valid('inv-3cycle', {}, '5-execute')

    err = excinfo.value
    assert err.cycle, 'cycle must be non-empty'
    # All three task identifiers must appear somewhere in the cycle path.
    for expected in ('TASK-1', 'TASK-2', 'TASK-3'):
        assert expected in err.cycle, f'cycle must contain {expected}, got {err.cycle}'
    assert err.dangling == [], f'dangling must be empty, got {err.dangling}'


# =============================================================================
# (e) Dangling reference
# =============================================================================


def test_dangling_reference_raises_with_non_empty_dangling(plan_context, stub_run_script) -> None:
    """TASK-1 depends on TASK-99 (non-existent) → TaskGraphInvalid, dangling non-empty."""
    _add_task('inv-dangling', 'T1', 1, depends_on='TASK-99')

    with pytest.raises(inv.TaskGraphInvalid) as excinfo:
        inv._capture_task_graph_valid('inv-dangling', {}, '5-execute')

    err = excinfo.value
    assert err.dangling, 'dangling must be non-empty when a ref misses'
    # Each dangling entry is a dict with task + missing fields.
    entry = err.dangling[0]
    assert isinstance(entry, dict), f'expected dict entry, got {entry!r}'
    assert entry.get('task') == 'TASK-1'
    assert 'TASK-99' in str(entry.get('missing', '')), f'expected TASK-99 in missing, got {entry}'
    assert err.cycle == [], f'cycle must be empty for pure dangling, got {err.cycle}'


# =============================================================================
# (f) Empty task list
# =============================================================================


def test_empty_task_list_returns_stable_zero_edge_hash(plan_context, stub_run_script) -> None:
    """No tasks → stable hash, no raise, same across runs."""
    result_a = inv._capture_task_graph_valid('inv-empty-a', {}, '5-execute')
    result_b = inv._capture_task_graph_valid('inv-empty-b', {}, '5-execute')

    assert isinstance(result_a, str), f'expected hash, got {result_a!r}'
    assert len(result_a) == 16
    assert result_a == result_b, 'zero-edge hash must be stable across plans'

    # And it must differ from any graph with at least one edge.
    _add_task('inv-empty-vs-edge', 'T1', 1)
    _add_task('inv-empty-vs-edge', 'T2', 2, depends_on='TASK-1')
    one_edge_hash = inv._capture_task_graph_valid('inv-empty-vs-edge', {}, '5-execute')
    assert result_a != one_edge_hash, 'zero-edge hash must differ from a graph with edges'


# =============================================================================
# (g) capture_all surfaces TaskGraphInvalid
# =============================================================================


def test_capture_all_surfaces_task_graph_invalid(plan_context, stub_run_script, monkeypatch: pytest.MonkeyPatch) -> None:
    """capture_all must propagate TaskGraphInvalid from the broken-graph fixture.

    We narrow ``INVARIANTS`` to the real ``task_graph_valid`` entry so the
    other invariants (which would try to shell out to git, manage-config,
    etc.) don't interfere with the assertion.
    """
    narrowed = [
        (
            'task_graph_valid',
            inv._always,
            inv._capture_task_graph_valid,
        ),
    ]
    monkeypatch.setattr(inv, 'INVARIANTS', narrowed)

    _add_task('inv-capture-all', 'T1', 1, depends_on='TASK-99')

    with pytest.raises(inv.TaskGraphInvalid) as excinfo:
        inv.capture_all('inv-capture-all', {}, '5-execute')

    assert excinfo.value.dangling, 'dangling must propagate through capture_all'


# =============================================================================
# task_state_hash — (h) Non-empty plan → non-empty hex hash
# =============================================================================
#
# Regression guard: the previous implementation read ``parsed.get('tasks')``
# from ``manage-tasks list``, but ``list`` actually emits ``tasks_table``.
# The result was a silent no-op hash (empty list) regardless of task count.
# This test would fail against that broken implementation because the hash
# of a 1-task plan would equal the hash of a 0-task plan.
# =============================================================================


def test_state_hash_non_empty_plan_differs_from_empty(plan_context, stub_run_script) -> None:
    """A plan with ≥1 task must not hash to the same value as an empty plan."""
    empty_hash = inv._capture_task_state_hash('inv-state-empty', {}, '5-execute')

    _add_task('inv-state-one-task', 'T1', 1)
    one_task_hash = inv._capture_task_state_hash('inv-state-one-task', {}, '5-execute')

    assert isinstance(empty_hash, str) and len(empty_hash) == 16
    assert isinstance(one_task_hash, str) and len(one_task_hash) == 16
    assert all(c in '0123456789abcdef' for c in one_task_hash)
    assert one_task_hash != empty_hash, (
        'hash for a 1-task plan must differ from the zero-task hash — '
        'if this fails, _capture_task_state_hash is reading the wrong '
        'key from manage-tasks list (should be tasks_table, not tasks)'
    )


# =============================================================================
# task_state_hash — (i) Changing task status changes hash
# =============================================================================


def test_state_hash_changes_when_task_status_changes(plan_context, stub_run_script) -> None:
    """Updating a task's status field must change the captured hash."""
    _add_task('inv-state-status', 'T1', 1)
    before = inv._capture_task_state_hash('inv-state-status', {}, '5-execute')
    _set_status('inv-state-status', 1, 'in_progress')
    after = inv._capture_task_state_hash('inv-state-status', {}, '5-execute')

    assert before != after, 'hash must change when a task status transitions pending -> in_progress'


# =============================================================================
# task_state_hash — (j) Changing depends_on changes hash
# =============================================================================


def test_state_hash_changes_when_depends_on_changes(plan_context, stub_run_script) -> None:
    """Adding a dependency edge must change the captured hash."""
    _add_task('inv-state-deps', 'T1', 1)
    _add_task('inv-state-deps', 'T2', 2)
    before = inv._capture_task_state_hash('inv-state-deps', {}, '5-execute')
    _set_depends_on('inv-state-deps', 2, ['TASK-1'])
    after = inv._capture_task_state_hash('inv-state-deps', {}, '5-execute')

    assert before != after, 'hash must change when a task acquires a new depends_on entry'


# =============================================================================
# task_state_hash — (k) Changing a step's status via finalize-step
# =============================================================================


def test_state_hash_changes_when_step_status_changes(plan_context, stub_run_script) -> None:
    """Marking a step done via finalize-step must change the captured hash."""
    _add_task('inv-state-step', 'T1', 1)
    before = inv._capture_task_state_hash('inv-state-step', {}, '5-execute')
    _finalize_step('inv-state-step', task=1, step=1, outcome='done')
    after = inv._capture_task_state_hash('inv-state-step', {}, '5-execute')

    assert before != after, 'hash must change when a step transitions pending -> done'


# =============================================================================
# task_state_hash — step intent sensitivity (status held constant)
# =============================================================================


def _flip_step_intent(plan_context, plan_id: str, task_number: int, step_index: int, new_intent: str) -> None:
    """Mutate a single step's intent on disk, leaving its status unchanged."""
    tasks_dir = plan_context.plan_dir_for(plan_id) / 'tasks'
    path = tasks_dir / f'TASK-{task_number:03d}.json'
    task = json.loads(path.read_text(encoding='utf-8'))
    task['steps'][step_index]['intent'] = new_intent
    path.write_text(json.dumps(task, indent=2), encoding='utf-8')


def test_state_hash_changes_when_step_intent_changes(plan_context, stub_run_script) -> None:
    """Mutating a step's intent (status held constant) must change the hash.

    intent authoritatively drives the files_exist Q-Gate, so a silent intent
    flip between phase boundaries must surface as task_state_hash drift.
    """
    _add_task('inv-state-intent', 'T1', 1)
    before = inv._capture_task_state_hash('inv-state-intent', {}, '5-execute')
    _flip_step_intent(plan_context, 'inv-state-intent', task_number=1, step_index=0, new_intent='write-new')
    after = inv._capture_task_state_hash('inv-state-intent', {}, '5-execute')

    assert before != after, 'hash must change when a step intent flips write-replace -> write-new'


# =============================================================================
# task_state_hash — (l) No-op recapture yields the same hash
# =============================================================================


def test_state_hash_is_stable_for_no_op_recapture(plan_context, stub_run_script) -> None:
    """Two captures without any intervening change must produce the same hash."""
    _add_task('inv-state-noop', 'T1', 1)
    _add_task('inv-state-noop', 'T2', 2, depends_on='TASK-1')
    first = inv._capture_task_state_hash('inv-state-noop', {}, '5-execute')
    second = inv._capture_task_state_hash('inv-state-noop', {}, '5-execute')

    assert first == second, 'recapture without intervening state changes must yield the same hash'


# =============================================================================
# task_state_hash — (m) Empty task list → stable hash, no raise
# =============================================================================


def test_state_hash_empty_plan_returns_stable_hash(plan_context, stub_run_script) -> None:
    """Two empty plans must produce the same zero-task hash without raising."""
    hash_a = inv._capture_task_state_hash('inv-state-empty-a', {}, '5-execute')
    hash_b = inv._capture_task_state_hash('inv-state-empty-b', {}, '5-execute')

    assert isinstance(hash_a, str) and len(hash_a) == 16
    assert hash_a == hash_b, 'zero-task hash must be stable across plans (deterministic empty state)'


# =============================================================================
# unfinished_tasks_count — registry tuple drives the phase-5-execute guard
# =============================================================================
#
# The capture function counts tasks currently in ``status: pending`` for the
# plan. It must:
#   - Return ``N`` (int) when N pending rows exist.
#   - Return ``0`` (int) when the queue is empty (every task done).
#   - Be reachable through ``capture_all`` so the registry tuple is wired in.
# =============================================================================


@pytest.mark.parametrize('pending_count', [0, 1, 2, 3])
def test_unfinished_tasks_count_returns_pending_row_count(plan_context, stub_run_script, pending_count: int) -> None:
    """``_capture_unfinished_tasks_count`` must return the count of pending tasks.

    Seeds N tasks via the manage-tasks fixture flow, optionally marks some
    done (so they leave ``pending``), then drives the capture function
    directly and asserts the returned int matches the remaining pending
    count.
    """
    plan_id = f'inv-pending-{pending_count}'
    # Seed three tasks first, then mark (3 - pending_count) of them done
    # so exactly ``pending_count`` remain in the pending state.
    _add_task(plan_id, 'T1', 1)
    _add_task(plan_id, 'T2', 2)
    _add_task(plan_id, 'T3', 3)
    to_mark_done = 3 - pending_count
    for n in range(1, to_mark_done + 1):
        _set_status(plan_id, n, 'done')

    result = inv._capture_unfinished_tasks_count(plan_id, {}, '5-execute')

    assert isinstance(result, int), f'expected int count, got {type(result).__name__}: {result!r}'
    assert result == pending_count, f'expected {pending_count} pending, got {result}'


def test_unfinished_tasks_count_drift_across_phases(plan_context, stub_run_script) -> None:
    """Drift case: count changes between phases as tasks complete.

    Captured during 5-execute with 2 pending; after marking some done (e.g.
    finalizing), a re-capture for 6-finalize must yield 0.
    """
    plan_id = 'inv-pending-drift'
    _add_task(plan_id, 'T1', 1)
    _add_task(plan_id, 'T2', 2)
    during_execute = inv._capture_unfinished_tasks_count(plan_id, {}, '5-execute')

    # Complete every task — pending queue drains to zero.
    _set_status(plan_id, 1, 'done')
    _set_status(plan_id, 2, 'done')
    after_execute = inv._capture_unfinished_tasks_count(plan_id, {}, '6-finalize')

    assert during_execute == 2, f'expected 2 pending mid-execute, got {during_execute}'
    assert after_execute == 0, f'expected 0 pending after completion, got {after_execute}'
    assert during_execute != after_execute, (
        'unfinished_tasks_count must reflect drift between phases — '
        'a non-changing value would mean the capture is reading stale data'
    )


def test_unfinished_tasks_count_reachable_via_capture_all(plan_context, stub_run_script, monkeypatch: pytest.MonkeyPatch) -> None:
    """``capture_all`` must surface ``unfinished_tasks_count`` from the registry.

    Narrows ``INVARIANTS`` to just the pending entry so the other invariants
    don't try to shell out, then exercises the registry-driven capture path
    end-to-end.
    """
    narrowed = [
        (
            'unfinished_tasks_count',
            inv._always,
            inv._capture_unfinished_tasks_count,
        ),
    ]
    monkeypatch.setattr(inv, 'INVARIANTS', narrowed)

    _add_task('inv-pending-capture-all', 'T1', 1)
    _add_task('inv-pending-capture-all', 'T2', 2)
    captured = inv.capture_all('inv-pending-capture-all', {}, '5-execute')

    assert 'unfinished_tasks_count' in captured, (
        f'capture_all must include unfinished_tasks_count, got keys: {list(captured)}'
    )
    assert captured['unfinished_tasks_count'] == 2


def test_unfinished_tasks_count_registry_tuple_present() -> None:
    """The registry must wire ``unfinished_tasks_count`` to the capture function.

    Guards against accidental removal of the tuple from ``INVARIANTS`` —
    without this entry the phase-5-execute transition guard cannot fire.
    """
    names = [name for name, _, _ in inv.INVARIANTS]
    assert 'unfinished_tasks_count' in names, f'unfinished_tasks_count must be registered, got {names}'
    entry = next(t for t in inv.INVARIANTS if t[0] == 'unfinished_tasks_count')
    name, applies_fn, capture_fn = entry
    assert capture_fn is inv._capture_unfinished_tasks_count
    # Always-applicable: every phase should record the queue size.
    assert applies_fn('any-plan', {}) is True


def test_unfinished_tasks_count_sums_pending_and_in_progress(plan_context, stub_run_script) -> None:
    """Broadened predicate: invariant counts ``pending`` PLUS ``in_progress``.

    Seeds two tasks, marks one ``in_progress`` and leaves one ``pending``, then
    asserts the capture returns 2 (not 1). Mirrors the broadened
    ``loop-exit-guard`` predicate that treats both buckets as blocking.
    """
    plan_id = 'inv-unfinished-sum'
    _add_task(plan_id, 'T1', 1)
    _add_task(plan_id, 'T2', 2)
    _set_status(plan_id, 1, 'in_progress')

    result = inv._capture_unfinished_tasks_count(plan_id, {}, '5-execute')

    assert isinstance(result, int), f'expected int count, got {type(result).__name__}: {result!r}'
    assert result == 2, (
        f'unfinished_tasks_count must count pending + in_progress, expected 2, got {result}'
    )


def test_unfinished_tasks_count_zero_when_all_done(plan_context, stub_run_script) -> None:
    """Both buckets empty → invariant returns 0."""
    plan_id = 'inv-unfinished-zero'
    _add_task(plan_id, 'T1', 1)
    _set_status(plan_id, 1, 'done')

    result = inv._capture_unfinished_tasks_count(plan_id, {}, '6-finalize')

    assert result == 0, f'expected 0 unfinished when all done, got {result}'


def test_unfinished_tasks_count_partition_blocking_at_every_boundary() -> None:
    """The renamed key keeps the ``blocking_at_every_boundary`` classification."""
    assert inv.INVARIANT_BLOCKING_SCOPE['unfinished_tasks_count'] == 'blocking_at_every_boundary'


# =============================================================================
# _capture_qgate_open_count: phase 1-init short-circuit
# =============================================================================


def test_capture_qgate_open_count_short_circuits_for_1_init(monkeypatch: pytest.MonkeyPatch) -> None:
    """At phase '1-init' the helper returns 0 without invoking _run_script.

    Q-Gate findings are scoped to phases 2-refine onward; manage-findings
    rejects --phase 1-init via argparse. The short-circuit eliminates the
    spurious subprocess call and the resulting [ERROR] log entries.
    """
    calls: list[list[str]] = []

    def _spy_run_script(args: list[str]) -> None:
        calls.append(args)
        return None

    monkeypatch.setattr(inv, '_run_script', _spy_run_script)

    result = inv._capture_qgate_open_count('any-plan', {}, '1-init')

    assert result == 0, f'Expected 0 for 1-init, got {result!r}'
    assert calls == [], f'_run_script must not be called for 1-init, got {calls!r}'


@pytest.mark.parametrize(
    'phase',
    ['2-refine', '3-outline', '4-plan', '5-execute', '6-finalize'],
)
def test_capture_qgate_open_count_invokes_script_for_other_phases(
    monkeypatch: pytest.MonkeyPatch, phase: str
) -> None:
    """For phases 2-refine through 6-finalize the helper invokes _run_script."""
    calls: list[list[str]] = []

    def _spy_run_script(args: list[str]) -> str:
        calls.append(args)
        return 'status: success\nfiltered_count: 0\n'

    monkeypatch.setattr(inv, '_run_script', _spy_run_script)

    result = inv._capture_qgate_open_count('any-plan', {}, phase)

    assert len(calls) == 1, f'Expected exactly one _run_script call for {phase}, got {calls!r}'
    assert '--phase' in calls[0]
    assert phase in calls[0]
    assert result == 0


# =============================================================================
# _worktree_materialized / _worktree_in_use: the unified materialization
# predicate gates the worktree-state invariants
# =============================================================================
#
# TASK-1 unified the worktree-applicability gate onto a single predicate,
# ``_worktree_materialized(metadata, phase)``: True when ``worktree_path`` is
# present and non-empty OR when ``phase`` is one of the materialization phases
# (``5-execute`` / ``6-finalize``), which covers the transient phase-5 window
# between phase entry and Step 2.5's path backfill.
#
# ``_worktree_in_use`` (the registry gate for ``worktree_sha`` /
# ``worktree_dirty``) now delegates to ``_worktree_materialized(metadata,
# None)`` — keyed on the persisted ``worktree_path`` alone (with ``phase=None``
# the materialization-phase branch can never match). The old ``use_worktree``
# truthiness gate is gone: the capture functions themselves return ``None``
# when ``worktree_path`` is unpopulated, so a pre-materialization capture
# simply records an empty column. The inverse-direction orphan invariant
# (``worktree_orphan`` / ``WorktreeMetadataDrift``) and the old private
# ``_worktree_applicable`` predicate were both removed.
# =============================================================================


def test_worktree_materialized_empty_path_planning_phase_is_false() -> None:
    """Empty ``worktree_path`` at a planning phase → not yet materialized.

    Phases 1-4 run on the main checkout and persist only the ``use_worktree``
    intent; the path is materialized at phase-5 Step 2.5. An empty path while a
    planning phase is active is the legitimate pre-materialization state.
    """
    for phase in ('1-init', '2-refine', '3-outline', '4-plan'):
        assert inv._worktree_materialized({'worktree_path': ''}, phase) is False, (
            f'empty path at planning phase {phase} must be not-materialized'
        )
    # A missing key behaves the same as an empty path.
    assert inv._worktree_materialized({}, '3-outline') is False


@pytest.mark.parametrize('phase', ['5-execute', '6-finalize'])
def test_worktree_materialized_empty_path_materialization_phase_is_true(phase: str) -> None:
    """Empty ``worktree_path`` at a materialization phase → True (transient window).

    The phase-5 entry-to-Step-2.5 window has ``use_worktree`` intent but no path
    yet; the materialization-phase membership covers it so the predicate reports
    the worktree as in play.
    """
    assert inv._worktree_materialized({'worktree_path': ''}, phase) is True
    assert inv._worktree_materialized({}, phase) is True


@pytest.mark.parametrize('phase', ['1-init', '4-plan', '5-execute', '6-finalize', None])
def test_worktree_materialized_non_empty_path_is_true_at_any_phase(phase) -> None:
    """A populated ``worktree_path`` → True regardless of phase (even ``None``)."""
    assert inv._worktree_materialized({'worktree_path': '/tmp/wt'}, phase) is True


def test_worktree_materialized_empty_path_phase_none_is_false() -> None:
    """``phase=None`` with an empty path → False (the registry-gate keying).

    ``_worktree_in_use`` calls ``_worktree_materialized(metadata, None)``, so the
    materialization-phase branch can never match; the result is keyed on the
    persisted ``worktree_path`` alone.
    """
    assert inv._worktree_materialized({'worktree_path': ''}, None) is False
    assert inv._worktree_materialized({}, None) is False


@pytest.mark.parametrize('worktree_path', ['/tmp/wt', 'relative/wt', '  /tmp/wt  '])
def test_worktree_in_use_applies_when_path_populated(worktree_path: str) -> None:
    """The gate applies when ``worktree_path`` is present and non-empty.

    ``_worktree_in_use`` is keyed on the materialization predicate with
    ``phase=None``, so a populated path makes it applicable. Whitespace-only
    padding around a real path is still a real path.
    """
    assert inv._worktree_in_use('p', {'worktree_path': worktree_path}) is True


@pytest.mark.parametrize('empty_value', ['', '   ', None])
def test_worktree_in_use_does_not_apply_when_path_empty(empty_value) -> None:
    """An empty / whitespace-only / missing ``worktree_path`` → inapplicable."""
    metadata = {'worktree_path': empty_value} if empty_value is not None else {}
    assert inv._worktree_in_use('p', metadata) is False


def test_worktree_in_use_missing_key_does_not_apply() -> None:
    """A missing ``worktree_path`` key is treated as not-materialized."""
    assert inv._worktree_in_use('p', {}) is False


def test_worktree_in_use_ignores_use_worktree_without_path() -> None:
    """``use_worktree`` truthiness alone no longer makes the gate apply.

    Regression guard for the TASK-1 unification: the gate is keyed on the
    persisted ``worktree_path``, not on ``use_worktree``. A planning-phase
    metadata that declares the intent but has no path yet must NOT apply.
    """
    assert inv._worktree_in_use('p', {'use_worktree': True}) is False
    assert inv._worktree_in_use('p', {'use_worktree': True, 'worktree_path': ''}) is False
    # With the path populated it applies regardless of use_worktree's value.
    assert inv._worktree_in_use('p', {'use_worktree': False, 'worktree_path': '/tmp/wt'}) is True


def test_worktree_state_invariants_gate_on_materialization_predicate() -> None:
    """``worktree_sha`` / ``worktree_dirty`` use the unified ``_worktree_in_use`` gate.

    The gate now keys on the unified materialization predicate
    (``worktree_path`` presence) rather than the removed ``use_worktree``
    truthiness gate or the removed ``_worktree_applicable`` predicate.
    """
    by_name = {name: (applies, capture) for name, applies, capture in inv.INVARIANTS}
    assert by_name['worktree_sha'][0] is inv._worktree_in_use
    assert by_name['worktree_dirty'][0] is inv._worktree_in_use


def test_worktree_orphan_invariant_removed() -> None:
    """The orphan invariant and the removed predicate surfaces are gone.

    ``_worktree_applicable`` (the inert ``worktree_path``-presence predicate
    TASK-1 unified away) and the orphan invariant surface must not exist on the
    module — this guard pins their absence so a regression that re-introduces
    the split predicate fails loudly.
    """
    names = [name for name, _, _ in inv.INVARIANTS]
    assert 'worktree_orphan' not in names
    assert not hasattr(inv, '_capture_worktree_orphan')
    assert not hasattr(inv, '_worktree_orphan_dir')
    assert not hasattr(inv, 'WorktreeMetadataDrift')
    assert not hasattr(inv, '_worktree_applicable')


# =============================================================================
# Layer-D helpers: _filter_main_dirty_paths / _main_dirty_drift_diff /
# _capture_main_dirty_files
# =============================================================================
#
# Unit-level coverage for the layer-D primitives that drive the
# ``main_checkout_dirtied_during_plan`` enforcement. Companion to the
# integration-level scenarios in test_phase_handshake_worktree_assertion.py
# which exercise the full cmd_capture / cmd_verify path.
# Origin: deliverable D2 of plan ``lesson-2026-05-08-08-001``.
# =============================================================================


# --- _filter_main_dirty_paths ---------------------------------------------


def test_filter_main_dirty_paths_drops_dot_plan_paths() -> None:
    """``.plan/`` prefixes are stripped — they live legitimately in main."""
    paths = [
        '.plan/local/plans/foo/work.log',
        '.plan/temp/scratch.toon',
        'src/main.py',
        'README.md',
    ]
    filtered = inv._filter_main_dirty_paths(paths)
    assert filtered == ['src/main.py', 'README.md'], (
        f'expected ``.plan/`` paths to be dropped, got {filtered}'
    )


def test_filter_main_dirty_paths_keeps_non_plan_paths() -> None:
    """Non-``.plan/`` paths pass through unchanged in declaration order."""
    paths = ['a.txt', 'src/b.py', 'docs/c.md']
    assert inv._filter_main_dirty_paths(paths) == ['a.txt', 'src/b.py', 'docs/c.md']


def test_filter_main_dirty_paths_handles_empty_list() -> None:
    """Empty input → empty output (no error)."""
    assert inv._filter_main_dirty_paths([]) == []


def test_filter_main_dirty_paths_only_plan_paths_returns_empty() -> None:
    """Input where every path is under ``.plan/`` → empty result."""
    paths = ['.plan/foo', '.plan/bar', '.plan/baz/qux']
    assert inv._filter_main_dirty_paths(paths) == []


def test_filter_main_dirty_paths_does_not_match_plan_substring() -> None:
    """Filter is prefix-based — ``my.plan/foo`` MUST NOT be dropped.

    Guards against an over-eager substring match that would erroneously
    strip paths that merely contain ``.plan/`` somewhere in their string
    representation. Only paths starting with ``.plan/`` (the project's
    plan-data directory) qualify for the filter.
    """
    paths = ['my.plan/foo.py', 'src/.plan/bar.py']
    # The first path doesn't start with ``.plan/`` — only ``my.plan/`` —
    # so it stays. The second starts with ``src/`` (also not ``.plan/``)
    # so it likewise stays.
    assert inv._filter_main_dirty_paths(paths) == ['my.plan/foo.py', 'src/.plan/bar.py']


# --- _main_dirty_drift_diff -----------------------------------------------


def test_main_dirty_drift_diff_returns_only_new_paths() -> None:
    """Live set has paths not in baseline → those paths are returned, sorted."""
    baseline = ['existing.txt']
    observed = ['existing.txt', 'new-b.md', 'new-a.py']
    # Result is sorted regardless of input order.
    assert inv._main_dirty_drift_diff(baseline, observed) == ['new-a.py', 'new-b.md']


def test_main_dirty_drift_diff_identical_sets_returns_empty() -> None:
    """Baseline-equal observed set → empty diff (proper-superset rule)."""
    baseline = ['a.txt', 'b.py']
    observed = ['a.txt', 'b.py']
    assert inv._main_dirty_drift_diff(baseline, observed) == []


def test_main_dirty_drift_diff_observed_subset_of_baseline_returns_empty() -> None:
    """Live set is a strict subset of baseline → empty diff (cleaned files OK).

    A pre-existing dirty file that got cleaned by the next boundary is
    benign. Only newly-dirty paths count as drift; baseline-only paths
    do NOT contribute to the result.
    """
    baseline = ['a.txt', 'b.py', 'c.md']
    observed = ['a.txt']  # b.py and c.md were cleaned
    assert inv._main_dirty_drift_diff(baseline, observed) == []


def test_main_dirty_drift_diff_empty_baseline_returns_all_observed_sorted() -> None:
    """Empty baseline → every observed path is "newly dirty"."""
    baseline: list[str] = []
    observed = ['z.py', 'a.md', 'm.txt']
    assert inv._main_dirty_drift_diff(baseline, observed) == ['a.md', 'm.txt', 'z.py']


def test_main_dirty_drift_diff_empty_observed_returns_empty() -> None:
    """Empty observed set → no newly-dirty paths regardless of baseline."""
    baseline = ['a.txt', 'b.py']
    observed: list[str] = []
    assert inv._main_dirty_drift_diff(baseline, observed) == []


def test_main_dirty_drift_diff_disjoint_sets_returns_full_observed_sorted() -> None:
    """Disjoint baseline and observed → entire observed set is "newly dirty"."""
    baseline = ['old1.txt', 'old2.py']
    observed = ['new-z.md', 'new-a.py']
    assert inv._main_dirty_drift_diff(baseline, observed) == ['new-a.py', 'new-z.md']


def test_main_dirty_drift_diff_mixed_overlap_returns_only_new() -> None:
    """Mixed overlap — baseline ∩ observed retained, only fresh paths reported."""
    baseline = ['shared.txt', 'cleaned.py']
    observed = ['shared.txt', 'leaked-1.md', 'leaked-2.py']
    assert inv._main_dirty_drift_diff(baseline, observed) == ['leaked-1.md', 'leaked-2.py']


def test_main_dirty_drift_diff_result_is_deterministic() -> None:
    """Same inputs across two calls produce identical output (sorted)."""
    baseline = ['a.txt']
    observed = ['c.py', 'a.txt', 'b.md']
    first = inv._main_dirty_drift_diff(baseline, observed)
    second = inv._main_dirty_drift_diff(baseline, observed)
    assert first == second
    assert first == ['b.md', 'c.py']


# --- _capture_main_dirty_files (integration with filter + git_dirty_files) -


def test_capture_main_dirty_files_returns_filtered_sorted_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Capture wraps ``git_dirty_files`` with ``_filter_main_dirty_paths``.

    Drives the function directly so the capture-time chain (git probe →
    filter → return) is exercised end-to-end as a unit.
    """
    monkeypatch.setattr(
        inv,
        'git_dirty_files',
        lambda _cwd: [
            '.plan/local/plans/foo/work.log',  # filtered
            'src/main.py',
            'README.md',
            '.plan/temp/scratch',  # filtered
        ],
    )
    result = inv._capture_main_dirty_files('any-plan', {}, '5-execute')
    # The filter preserves git-output order; sorting is the responsibility
    # of git_dirty_files (which sorts its return). Here we assert the
    # filter preserved order while dropping ``.plan/`` paths.
    assert result == ['src/main.py', 'README.md']


def test_capture_main_dirty_files_returns_none_when_git_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``git_dirty_files`` returning ``None`` propagates as ``None``.

    Matches the documented "not applicable" contract from the capture's
    docstring: stored row leaves the column empty when the probe fails.
    """
    monkeypatch.setattr(inv, 'git_dirty_files', lambda _cwd: None)
    assert inv._capture_main_dirty_files('any-plan', {}, '5-execute') is None


def test_capture_main_dirty_files_empty_input_returns_empty_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Clean main checkout (no dirty paths) → empty list (NOT None)."""
    monkeypatch.setattr(inv, 'git_dirty_files', lambda _cwd: [])
    assert inv._capture_main_dirty_files('any-plan', {}, '5-execute') == []


def test_capture_main_dirty_files_only_dot_plan_paths_returns_empty_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Only ``.plan/`` paths dirty → empty list after filter."""
    monkeypatch.setattr(
        inv,
        'git_dirty_files',
        lambda _cwd: ['.plan/local/foo', '.plan/temp/bar'],
    )
    assert inv._capture_main_dirty_files('any-plan', {}, '5-execute') == []


def test_main_dirty_files_registered_in_invariants() -> None:
    """The registry must wire ``main_dirty_files`` to the capture function.

    Guards against accidental removal of the tuple from ``INVARIANTS`` —
    without this entry the layer-D drift contract has no captured
    baseline to compare against.
    """
    names = [name for name, _, _ in inv.INVARIANTS]
    assert 'main_dirty_files' in names, f'main_dirty_files must be registered, got {names}'
    entry = next(t for t in inv.INVARIANTS if t[0] == 'main_dirty_files')
    name, applies_fn, capture_fn = entry
    assert capture_fn is inv._capture_main_dirty_files
    # Always-applicable: every phase boundary captures the baseline so the
    # next verify has a known previous-state to compare against.
    assert applies_fn('any-plan', {}) is True


def test_main_checkout_dirtied_during_plan_exception_carries_payload() -> None:
    """The exception class carries baseline / observed / newly_dirty as attrs.

    cmd_verify reads these attributes verbatim into the structured TOON
    error payload — this guards against accidental rename / deletion of
    the public attribute surface.
    """
    err = inv.MainCheckoutDirtiedDuringPlan(
        plan_id='p1',
        phase='5-execute',
        baseline=['old.txt'],
        observed=['old.txt', 'new.md'],
        newly_dirty=['new.md'],
    )
    assert err.plan_id == 'p1'
    assert err.phase == '5-execute'
    assert err.baseline == ['old.txt']
    assert err.observed == ['old.txt', 'new.md']
    assert err.newly_dirty == ['new.md']
    # The formatted message must mention the leaked paths so unstructured
    # log readers (raw stderr) can still see what leaked.
    assert 'new.md' in str(err)


# =============================================================================
# FIXED actionable-vs-knowledge blocking rule (replaces the per-phase config
# partition + determine_mode dispatch)
# =============================================================================


def test_actionable_finding_types_is_the_fixed_set() -> None:
    """The hardcoded actionable set is exactly the six user-approved types."""
    assert set(inv._ACTIONABLE_FINDING_TYPES) == {
        'build-error',
        'test-failure',
        'lint-issue',
        'sonar-issue',
        'qgate',
        'pr-comment',
    }


def test_actionable_set_excludes_every_knowledge_type() -> None:
    """KNOWLEDGE types are NEVER in the actionable set (the fixed exclusion)."""
    for knowledge in ('insight', 'tip', 'best-practice', 'improvement'):
        assert knowledge not in inv._ACTIONABLE_FINDING_TYPES


def test_config_partition_readers_removed_from_module() -> None:
    """The marshal.json read and the determine_mode import are gone.

    ``_read_blocking_finding_types`` (per-phase config read) and
    ``_resolve_blocking_callable_registry`` (cross-module determine_mode
    import) were dropped when the fixed rule replaced the config partition.
    This guard pins their absence so a regression re-introducing the config
    partition fails loudly.
    """
    assert not hasattr(inv, '_read_blocking_finding_types')
    assert not hasattr(inv, '_resolve_blocking_callable_registry')


def test_blocking_count_queries_only_actionable_types(monkeypatch) -> None:
    """The capture queries every actionable type with the uniform signature —
    qgate via the aggregator, the rest via the generic per-type query — and
    queries NO knowledge type.
    """
    generic_calls = []
    qgate_calls = []

    def fake_generic(plan_id, finding_type):
        generic_calls.append((plan_id, finding_type))
        return 0

    def fake_qgate(plan_id):
        qgate_calls.append(plan_id)
        return 0

    monkeypatch.setattr(inv, '_query_pending_count_for_type', fake_generic)
    monkeypatch.setattr(inv, '_query_pending_qgate_count_aggregated', fake_qgate)

    result = inv._capture_pending_findings_blocking_count('plan-x', {}, '5-execute')

    # qgate is summed via the aggregator (exactly once).
    assert qgate_calls == ['plan-x']
    # Every non-qgate actionable type is queried via the generic helper.
    queried_types = {ft for _pid, ft in generic_calls}
    assert queried_types == {
        'build-error',
        'test-failure',
        'lint-issue',
        'sonar-issue',
        'pr-comment',
    }
    # No knowledge type was ever queried.
    for knowledge in ('insight', 'tip', 'best-practice', 'improvement'):
        assert knowledge not in queried_types
    # All zero → total zero.
    assert result == 0


def test_blocking_count_sums_pending_actionable_findings(monkeypatch) -> None:
    """The total is the sum of pending counts across the actionable set."""
    per_type_counts = {
        'build-error': 2,
        'lint-issue': 1,
        'sonar-issue': 0,
        'test-failure': 0,
        'pr-comment': 0,
    }

    monkeypatch.setattr(
        inv,
        '_query_pending_count_for_type',
        lambda _pid, ft: per_type_counts.get(ft, 0),
    )
    monkeypatch.setattr(inv, '_query_pending_qgate_count_aggregated', lambda _pid: 3)

    result = inv._capture_pending_findings_blocking_count('plan-sum', {}, '5-execute')

    # 2 + 1 + 0 + 0 + 0 (per-type) + 3 (qgate) = 6.
    assert result == 6


def test_blocking_count_raises_at_guarded_boundary_when_actionable_pending(monkeypatch) -> None:
    """A pending actionable finding at 6-finalize raises BlockingFindingsPresent
    carrying the hardcoded actionable set as ``blocking_types``."""
    monkeypatch.setattr(
        inv,
        '_query_pending_count_for_type',
        lambda _pid, ft: 1 if ft == 'build-error' else 0,
    )
    monkeypatch.setattr(inv, '_query_pending_qgate_count_aggregated', lambda _pid: 0)

    with pytest.raises(inv.BlockingFindingsPresent) as excinfo:
        inv._capture_pending_findings_blocking_count('plan-block', {}, '6-finalize')

    err = excinfo.value
    assert err.blocking_count == 1
    assert err.blocking_types == list(inv._ACTIONABLE_FINDING_TYPES)
    assert err.per_type['build-error'] == 1


def test_blocking_count_passive_at_non_guarded_boundary(monkeypatch) -> None:
    """A pending actionable finding at a non-guarded phase returns the count
    without raising (passive capture for retrospective analysis)."""
    monkeypatch.setattr(
        inv,
        '_query_pending_count_for_type',
        lambda _pid, ft: 4 if ft == 'sonar-issue' else 0,
    )
    monkeypatch.setattr(inv, '_query_pending_qgate_count_aggregated', lambda _pid: 0)

    result = inv._capture_pending_findings_blocking_count('plan-passive', {}, '5-execute')

    assert result == 4


def test_blocking_count_returns_none_on_partial_query_failure(monkeypatch) -> None:
    """A per-type query returning ``None`` poisons the total to ``None`` (the
    "not applicable" contract) rather than under-counting."""
    monkeypatch.setattr(inv, '_query_pending_count_for_type', lambda _pid, _ft: None)
    monkeypatch.setattr(inv, '_query_pending_qgate_count_aggregated', lambda _pid: 0)

    result = inv._capture_pending_findings_blocking_count('plan-fail', {}, '5-execute')

    assert result is None


def test_blocking_count_returns_none_on_qgate_query_failure(monkeypatch) -> None:
    """A ``None`` from the qgate aggregator likewise poisons the total."""
    monkeypatch.setattr(inv, '_query_pending_count_for_type', lambda _pid, _ft: 0)
    monkeypatch.setattr(inv, '_query_pending_qgate_count_aggregated', lambda _pid: None)

    result = inv._capture_pending_findings_blocking_count('plan-qgate-fail', {}, '5-execute')

    assert result is None


# =============================================================================
# _capture_pr_title_present: refine-authored PR title presence invariant
# =============================================================================


def test_capture_pr_title_present_short_circuits_for_1_init() -> None:
    """At phase '1-init' the capture returns None — the title does not yet exist.

    phase-2-refine Step 13 authors the title; pre-refine the column stays empty
    and is skipped during verify. A present pr_title at 1-init is irrelevant.
    """
    result = inv._capture_pr_title_present('plan-x', {'pr_title': 'fix(x): y'}, '1-init')

    assert result is None, f'expected None at 1-init, got {result!r}'


@pytest.mark.parametrize('phase', ['2-refine', '3-outline', '4-plan', '5-execute', '6-finalize'])
def test_capture_pr_title_present_returns_hash_when_present(phase: str) -> None:
    """A non-empty pr_title at 2-refine+ returns a stable 16-char hex hash."""
    result = inv._capture_pr_title_present('plan-x', {'pr_title': 'fix(create-pr): bind title'}, phase)

    assert isinstance(result, str), f'expected hash string, got {result!r}'
    assert len(result) == 16, f'expected 16-char hash, got {len(result)} chars: {result}'
    assert all(c in '0123456789abcdef' for c in result), f'expected lowercase hex, got {result!r}'


def test_capture_pr_title_present_hash_is_presence_sentinel_not_content() -> None:
    """Two DIFFERENT non-empty titles produce the SAME hash.

    The sentinel encodes only the PRESENCE of a title, so a legitimate title
    edit between boundaries must NOT trip drift detection.
    """
    first = inv._capture_pr_title_present('plan-x', {'pr_title': 'fix(a): one'}, '2-refine')
    second = inv._capture_pr_title_present('plan-x', {'pr_title': 'feat(b): two different title'}, '5-execute')

    assert first == second, (
        'pr_title_present must be a presence-only sentinel — distinct titles '
        f'must hash identically, got {first!r} != {second!r}'
    )


@pytest.mark.parametrize('phase', ['2-refine', '3-outline', '4-plan', '5-execute', '6-finalize'])
@pytest.mark.parametrize('metadata', [{}, {'pr_title': ''}, {'pr_title': '   '}, {'pr_title': None}])
def test_capture_pr_title_present_raises_when_missing_or_empty(phase: str, metadata: dict) -> None:
    """Absent / empty / whitespace-only pr_title at 2-refine+ raises PrTitleMissing."""
    with pytest.raises(inv.PrTitleMissing) as excinfo:
        inv._capture_pr_title_present('plan-x', metadata, phase)

    assert excinfo.value.phase == phase, f'exception must carry the phase, got {excinfo.value.phase!r}'


def test_pr_title_present_registry_tuple_present() -> None:
    """The registry must wire ``pr_title_present`` to the capture function.

    Guards against accidental removal of the tuple from ``INVARIANTS`` —
    without this entry the boundary never enforces the deterministic title.
    """
    names = [name for name, _, _ in inv.INVARIANTS]
    assert 'pr_title_present' in names, f'pr_title_present must be registered, got {names}'
    entry = next(t for t in inv.INVARIANTS if t[0] == 'pr_title_present')
    _name, applies_fn, capture_fn = entry
    assert capture_fn is inv._capture_pr_title_present
    # Always-applicable: the phase gate lives inside the capture function.
    assert applies_fn('any-plan', {}) is True


def test_pr_title_present_reachable_via_capture_all(monkeypatch: pytest.MonkeyPatch) -> None:
    """``capture_all`` must surface ``pr_title_present`` from the registry.

    Narrows ``INVARIANTS`` to just the pr_title entry so the other invariants
    don't try to shell out, then exercises the registry-driven capture path.
    """
    narrowed = [
        ('pr_title_present', inv._always, inv._capture_pr_title_present),
    ]
    monkeypatch.setattr(inv, 'INVARIANTS', narrowed)

    captured = inv.capture_all('plan-x', {'pr_title': 'fix(x): y'}, '2-refine')

    assert 'pr_title_present' in captured, (
        f'capture_all must include pr_title_present, got keys: {list(captured)}'
    )
    assert isinstance(captured['pr_title_present'], str)


def test_pr_title_present_capture_all_omits_at_1_init(monkeypatch: pytest.MonkeyPatch) -> None:
    """At 1-init the capture returns None, so capture_all omits the column."""
    narrowed = [
        ('pr_title_present', inv._always, inv._capture_pr_title_present),
    ]
    monkeypatch.setattr(inv, 'INVARIANTS', narrowed)

    captured = inv.capture_all('plan-x', {'pr_title': 'fix(x): y'}, '1-init')

    assert 'pr_title_present' not in captured, (
        f'capture_all must omit pr_title_present at 1-init, got: {list(captured)}'
    )


@pytest.mark.parametrize('phase', ['1-init', '2-refine', '3-outline', '4-plan', '5-execute', '6-finalize'])
def test_pr_title_present_partition_blocking_at_every_boundary(phase: str) -> None:
    """pr_title_present carries the ``blocking_at_every_boundary`` classification."""
    assert inv.INVARIANT_BLOCKING_SCOPE['pr_title_present'] == 'blocking_at_every_boundary'
    assert inv.is_invariant_blocking_at_phase('pr_title_present', phase) is True

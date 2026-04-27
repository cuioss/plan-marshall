#!/usr/bin/env python3
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

import importlib.util
import sys
from argparse import Namespace
from pathlib import Path

import pytest
from conftest import PlanContext, get_script_path  # type: ignore[import-not-found]

# =============================================================================
# Import the invariants module under test.
# =============================================================================

SCRIPT_PATH = get_script_path('plan-marshall', 'plan-marshall', 'phase_handshake.py')
SCRIPTS_DIR = SCRIPT_PATH.parent

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import _invariants as inv  # noqa: E402


# =============================================================================
# Load manage-tasks command handlers via importlib (same pattern as
# test_manage_tasks.py) — gives us in-process fixture creation without
# needing a subprocess wrapper.
# =============================================================================

_MT_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-tasks'
    / 'scripts'
)


def _load_mt_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, _MT_SCRIPTS_DIR / filename)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_crud = _load_mt_module('_invariants_test_tasks_crud', '_tasks_crud.py')
_query = _load_mt_module('_invariants_test_tasks_query', '_tasks_query.py')
_step = _load_mt_module('_invariants_test_tasks_step', '_cmd_step.py')

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
        lines.append(f'  - {step}')
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
            task=number,
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
            task=number,
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
    result = cmd_finalize_step(
        Namespace(plan_id=plan_id, task=task, step=step, outcome=outcome)
    )
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
        # Or per _capture_pending_tasks_count:
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
            # args[...] contains '--task', followed by the number
            t_idx = args.index('--task')
            number = int(args[t_idx + 1])
            ns = Namespace(plan_id=plan_id, task=number)
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


def test_linear_graph_returns_16char_hex_hash(stub_run_script) -> None:
    """TASK-1 ← TASK-2 ← TASK-3 produces a 16-char hex hash."""
    with PlanContext(plan_id='inv-linear'):
        _add_task('inv-linear', 'T1', 1)
        _add_task('inv-linear', 'T2', 2, depends_on='TASK-1')
        _add_task('inv-linear', 'T3', 3, depends_on='TASK-2')

        result = inv._capture_task_graph_valid('inv-linear', {}, '5-execute')

    assert isinstance(result, str), f'expected hash string, got {result!r}'
    assert len(result) == 16, f'expected 16-char hash, got {len(result)} chars: {result}'
    assert all(c in '0123456789abcdef' for c in result), (
        f'expected lowercase hex, got {result!r}'
    )


def test_linear_graph_hash_changes_when_edges_change(stub_run_script) -> None:
    """Adding an edge yields a different hash (determinism check part 1)."""
    with PlanContext(plan_id='inv-linear-a'):
        _add_task('inv-linear-a', 'T1', 1)
        _add_task('inv-linear-a', 'T2', 2, depends_on='TASK-1')
        hash_two_nodes = inv._capture_task_graph_valid(
            'inv-linear-a', {}, '5-execute'
        )

    with PlanContext(plan_id='inv-linear-b'):
        _add_task('inv-linear-b', 'T1', 1)
        _add_task('inv-linear-b', 'T2', 2, depends_on='TASK-1')
        _add_task('inv-linear-b', 'T3', 3, depends_on='TASK-2')
        hash_three_nodes = inv._capture_task_graph_valid(
            'inv-linear-b', {}, '5-execute'
        )

    assert hash_two_nodes != hash_three_nodes, (
        'hash must change when an edge is added'
    )


def test_linear_graph_hash_is_deterministic_across_runs(stub_run_script) -> None:
    """Same edge set must produce the same hash (determinism check part 2)."""
    with PlanContext(plan_id='inv-det-1'):
        _add_task('inv-det-1', 'T1', 1)
        _add_task('inv-det-1', 'T2', 2, depends_on='TASK-1')
        _add_task('inv-det-1', 'T3', 3, depends_on='TASK-2')
        first = inv._capture_task_graph_valid('inv-det-1', {}, '5-execute')

    with PlanContext(plan_id='inv-det-2'):
        _add_task('inv-det-2', 'T1', 1)
        _add_task('inv-det-2', 'T2', 2, depends_on='TASK-1')
        _add_task('inv-det-2', 'T3', 3, depends_on='TASK-2')
        second = inv._capture_task_graph_valid('inv-det-2', {}, '5-execute')

    assert first == second, 'same edge set must produce the same hash'


# =============================================================================
# (b) Healthy branching graph
# =============================================================================


def test_branching_graph_returns_different_deterministic_hash(stub_run_script) -> None:
    """TASK-1 ← {TASK-2, TASK-3}, TASK-2 ← TASK-4 — different shape, different hash."""
    # Branching run #1.
    with PlanContext(plan_id='inv-branch-1'):
        _add_task('inv-branch-1', 'T1', 1)
        _add_task('inv-branch-1', 'T2', 2, depends_on='TASK-1')
        _add_task('inv-branch-1', 'T3', 3, depends_on='TASK-1')
        _add_task('inv-branch-1', 'T4', 4, depends_on='TASK-2')
        branching_a = inv._capture_task_graph_valid(
            'inv-branch-1', {}, '5-execute'
        )

    # Branching run #2 (same topology) — must match for determinism.
    with PlanContext(plan_id='inv-branch-2'):
        _add_task('inv-branch-2', 'T1', 1)
        _add_task('inv-branch-2', 'T2', 2, depends_on='TASK-1')
        _add_task('inv-branch-2', 'T3', 3, depends_on='TASK-1')
        _add_task('inv-branch-2', 'T4', 4, depends_on='TASK-2')
        branching_b = inv._capture_task_graph_valid(
            'inv-branch-2', {}, '5-execute'
        )

    # Linear run of same node count — must differ because edges differ.
    with PlanContext(plan_id='inv-branch-linear'):
        _add_task('inv-branch-linear', 'T1', 1)
        _add_task('inv-branch-linear', 'T2', 2, depends_on='TASK-1')
        _add_task('inv-branch-linear', 'T3', 3, depends_on='TASK-2')
        _add_task('inv-branch-linear', 'T4', 4, depends_on='TASK-3')
        linear_same_size = inv._capture_task_graph_valid(
            'inv-branch-linear', {}, '5-execute'
        )

    assert isinstance(branching_a, str) and len(branching_a) == 16
    assert branching_a == branching_b, (
        'branching graph hash must be deterministic across runs'
    )
    assert branching_a != linear_same_size, (
        'branching graph must hash differently than linear graph of same size'
    )


# =============================================================================
# (c) Self-cycle
# =============================================================================


def test_self_cycle_raises_with_non_empty_cycle(stub_run_script) -> None:
    """TASK-1 depends on TASK-1 → TaskGraphInvalid, cycle contains TASK-1."""
    with PlanContext(plan_id='inv-self-cycle'):
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


def test_three_node_cycle_raises_with_full_cycle_path(stub_run_script) -> None:
    """TASK-1 → TASK-2 → TASK-3 → TASK-1 yields a cycle covering all three nodes."""
    with PlanContext(plan_id='inv-3cycle'):
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
        assert expected in err.cycle, (
            f'cycle must contain {expected}, got {err.cycle}'
        )
    assert err.dangling == [], f'dangling must be empty, got {err.dangling}'


# =============================================================================
# (e) Dangling reference
# =============================================================================


def test_dangling_reference_raises_with_non_empty_dangling(stub_run_script) -> None:
    """TASK-1 depends on TASK-99 (non-existent) → TaskGraphInvalid, dangling non-empty."""
    with PlanContext(plan_id='inv-dangling'):
        _add_task('inv-dangling', 'T1', 1, depends_on='TASK-99')

        with pytest.raises(inv.TaskGraphInvalid) as excinfo:
            inv._capture_task_graph_valid('inv-dangling', {}, '5-execute')

    err = excinfo.value
    assert err.dangling, 'dangling must be non-empty when a ref misses'
    # Each dangling entry is a dict with task + missing fields.
    entry = err.dangling[0]
    assert isinstance(entry, dict), f'expected dict entry, got {entry!r}'
    assert entry.get('task') == 'TASK-1'
    assert 'TASK-99' in str(entry.get('missing', '')), (
        f'expected TASK-99 in missing, got {entry}'
    )
    assert err.cycle == [], f'cycle must be empty for pure dangling, got {err.cycle}'


# =============================================================================
# (f) Empty task list
# =============================================================================


def test_empty_task_list_returns_stable_zero_edge_hash(stub_run_script) -> None:
    """No tasks → stable hash, no raise, same across runs."""
    with PlanContext(plan_id='inv-empty-a'):
        result_a = inv._capture_task_graph_valid('inv-empty-a', {}, '5-execute')

    with PlanContext(plan_id='inv-empty-b'):
        result_b = inv._capture_task_graph_valid('inv-empty-b', {}, '5-execute')

    assert isinstance(result_a, str), f'expected hash, got {result_a!r}'
    assert len(result_a) == 16
    assert result_a == result_b, 'zero-edge hash must be stable across plans'

    # And it must differ from any graph with at least one edge.
    with PlanContext(plan_id='inv-empty-vs-edge'):
        _add_task('inv-empty-vs-edge', 'T1', 1)
        _add_task('inv-empty-vs-edge', 'T2', 2, depends_on='TASK-1')
        one_edge_hash = inv._capture_task_graph_valid(
            'inv-empty-vs-edge', {}, '5-execute'
        )
    assert result_a != one_edge_hash, (
        'zero-edge hash must differ from a graph with edges'
    )


# =============================================================================
# (g) capture_all surfaces TaskGraphInvalid
# =============================================================================


def test_capture_all_surfaces_task_graph_invalid(
    stub_run_script, monkeypatch: pytest.MonkeyPatch
) -> None:
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

    with PlanContext(plan_id='inv-capture-all'):
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


def test_state_hash_non_empty_plan_differs_from_empty(stub_run_script) -> None:
    """A plan with ≥1 task must not hash to the same value as an empty plan."""
    with PlanContext(plan_id='inv-state-empty'):
        empty_hash = inv._capture_task_state_hash(
            'inv-state-empty', {}, '5-execute'
        )

    with PlanContext(plan_id='inv-state-one-task'):
        _add_task('inv-state-one-task', 'T1', 1)
        one_task_hash = inv._capture_task_state_hash(
            'inv-state-one-task', {}, '5-execute'
        )

    assert isinstance(empty_hash, str) and len(empty_hash) == 16
    assert isinstance(one_task_hash, str) and len(one_task_hash) == 16
    assert all(c in '0123456789abcdef' for c in one_task_hash)
    assert one_task_hash != empty_hash, (
        'hash for a 1-task plan must differ from the zero-task hash — '
        "if this fails, _capture_task_state_hash is reading the wrong "
        'key from manage-tasks list (should be tasks_table, not tasks)'
    )


# =============================================================================
# task_state_hash — (i) Changing task status changes hash
# =============================================================================


def test_state_hash_changes_when_task_status_changes(stub_run_script) -> None:
    """Updating a task's status field must change the captured hash."""
    with PlanContext(plan_id='inv-state-status'):
        _add_task('inv-state-status', 'T1', 1)
        before = inv._capture_task_state_hash(
            'inv-state-status', {}, '5-execute'
        )
        _set_status('inv-state-status', 1, 'in_progress')
        after = inv._capture_task_state_hash(
            'inv-state-status', {}, '5-execute'
        )

    assert before != after, (
        'hash must change when a task status transitions '
        'pending -> in_progress'
    )


# =============================================================================
# task_state_hash — (j) Changing depends_on changes hash
# =============================================================================


def test_state_hash_changes_when_depends_on_changes(stub_run_script) -> None:
    """Adding a dependency edge must change the captured hash."""
    with PlanContext(plan_id='inv-state-deps'):
        _add_task('inv-state-deps', 'T1', 1)
        _add_task('inv-state-deps', 'T2', 2)
        before = inv._capture_task_state_hash(
            'inv-state-deps', {}, '5-execute'
        )
        _set_depends_on('inv-state-deps', 2, ['TASK-1'])
        after = inv._capture_task_state_hash(
            'inv-state-deps', {}, '5-execute'
        )

    assert before != after, (
        'hash must change when a task acquires a new depends_on entry'
    )


# =============================================================================
# task_state_hash — (k) Changing a step's status via finalize-step
# =============================================================================


def test_state_hash_changes_when_step_status_changes(stub_run_script) -> None:
    """Marking a step done via finalize-step must change the captured hash."""
    with PlanContext(plan_id='inv-state-step'):
        _add_task('inv-state-step', 'T1', 1)
        before = inv._capture_task_state_hash(
            'inv-state-step', {}, '5-execute'
        )
        _finalize_step('inv-state-step', task=1, step=1, outcome='done')
        after = inv._capture_task_state_hash(
            'inv-state-step', {}, '5-execute'
        )

    assert before != after, (
        'hash must change when a step transitions pending -> done'
    )


# =============================================================================
# task_state_hash — (l) No-op recapture yields the same hash
# =============================================================================


def test_state_hash_is_stable_for_no_op_recapture(stub_run_script) -> None:
    """Two captures without any intervening change must produce the same hash."""
    with PlanContext(plan_id='inv-state-noop'):
        _add_task('inv-state-noop', 'T1', 1)
        _add_task('inv-state-noop', 'T2', 2, depends_on='TASK-1')
        first = inv._capture_task_state_hash(
            'inv-state-noop', {}, '5-execute'
        )
        second = inv._capture_task_state_hash(
            'inv-state-noop', {}, '5-execute'
        )

    assert first == second, (
        'recapture without intervening state changes must yield the same hash'
    )


# =============================================================================
# task_state_hash — (m) Empty task list → stable hash, no raise
# =============================================================================


def test_state_hash_empty_plan_returns_stable_hash(stub_run_script) -> None:
    """Two empty plans must produce the same zero-task hash without raising."""
    with PlanContext(plan_id='inv-state-empty-a'):
        hash_a = inv._capture_task_state_hash(
            'inv-state-empty-a', {}, '5-execute'
        )

    with PlanContext(plan_id='inv-state-empty-b'):
        hash_b = inv._capture_task_state_hash(
            'inv-state-empty-b', {}, '5-execute'
        )

    assert isinstance(hash_a, str) and len(hash_a) == 16
    assert hash_a == hash_b, (
        'zero-task hash must be stable across plans (deterministic empty state)'
    )


# =============================================================================
# pending_tasks_count — registry tuple drives the phase-5-execute guard
# =============================================================================
#
# The capture function counts tasks currently in ``status: pending`` for the
# plan. It must:
#   - Return ``N`` (int) when N pending rows exist.
#   - Return ``0`` (int) when the queue is empty (every task done).
#   - Be reachable through ``capture_all`` so the registry tuple is wired in.
# =============================================================================


@pytest.mark.parametrize('pending_count', [0, 1, 2, 3])
def test_pending_tasks_count_returns_pending_row_count(
    stub_run_script, pending_count: int
) -> None:
    """``_capture_pending_tasks_count`` must return the count of pending tasks.

    Seeds N tasks via the manage-tasks fixture flow, optionally marks some
    done (so they leave ``pending``), then drives the capture function
    directly and asserts the returned int matches the remaining pending
    count.
    """
    plan_id = f'inv-pending-{pending_count}'
    with PlanContext(plan_id=plan_id):
        # Seed three tasks first, then mark (3 - pending_count) of them done
        # so exactly ``pending_count`` remain in the pending state.
        _add_task(plan_id, 'T1', 1)
        _add_task(plan_id, 'T2', 2)
        _add_task(plan_id, 'T3', 3)
        to_mark_done = 3 - pending_count
        for n in range(1, to_mark_done + 1):
            _set_status(plan_id, n, 'done')

        result = inv._capture_pending_tasks_count(plan_id, {}, '5-execute')

    assert isinstance(result, int), (
        f'expected int count, got {type(result).__name__}: {result!r}'
    )
    assert result == pending_count, (
        f'expected {pending_count} pending, got {result}'
    )


def test_pending_tasks_count_drift_across_phases(stub_run_script) -> None:
    """Drift case: count changes between phases as tasks complete.

    Captured during 5-execute with 2 pending; after marking some done (e.g.
    finalizing), a re-capture for 6-finalize must yield 0.
    """
    plan_id = 'inv-pending-drift'
    with PlanContext(plan_id=plan_id):
        _add_task(plan_id, 'T1', 1)
        _add_task(plan_id, 'T2', 2)
        during_execute = inv._capture_pending_tasks_count(
            plan_id, {}, '5-execute'
        )

        # Complete every task — pending queue drains to zero.
        _set_status(plan_id, 1, 'done')
        _set_status(plan_id, 2, 'done')
        after_execute = inv._capture_pending_tasks_count(
            plan_id, {}, '6-finalize'
        )

    assert during_execute == 2, f'expected 2 pending mid-execute, got {during_execute}'
    assert after_execute == 0, (
        f'expected 0 pending after completion, got {after_execute}'
    )
    assert during_execute != after_execute, (
        'pending_tasks_count must reflect drift between phases — '
        'a non-changing value would mean the capture is reading stale data'
    )


def test_pending_tasks_count_reachable_via_capture_all(
    stub_run_script, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``capture_all`` must surface ``pending_tasks_count`` from the registry.

    Narrows ``INVARIANTS`` to just the pending entry so the other invariants
    don't try to shell out, then exercises the registry-driven capture path
    end-to-end.
    """
    narrowed = [
        (
            'pending_tasks_count',
            inv._always,
            inv._capture_pending_tasks_count,
        ),
    ]
    monkeypatch.setattr(inv, 'INVARIANTS', narrowed)

    with PlanContext(plan_id='inv-pending-capture-all'):
        _add_task('inv-pending-capture-all', 'T1', 1)
        _add_task('inv-pending-capture-all', 'T2', 2)
        captured = inv.capture_all('inv-pending-capture-all', {}, '5-execute')

    assert 'pending_tasks_count' in captured, (
        f'capture_all must include pending_tasks_count, got keys: {list(captured)}'
    )
    assert captured['pending_tasks_count'] == 2


def test_pending_tasks_count_registry_tuple_present() -> None:
    """The registry must wire ``pending_tasks_count`` to the capture function.

    Guards against accidental removal of the tuple from ``INVARIANTS`` —
    without this entry the phase-5-execute transition guard cannot fire.
    """
    names = [name for name, _, _ in inv.INVARIANTS]
    assert 'pending_tasks_count' in names, (
        f'pending_tasks_count must be registered, got {names}'
    )
    entry = next(t for t in inv.INVARIANTS if t[0] == 'pending_tasks_count')
    name, applies_fn, capture_fn = entry
    assert capture_fn is inv._capture_pending_tasks_count
    # Always-applicable: every phase should record the queue size.
    assert applies_fn('any-plan', {}) is True

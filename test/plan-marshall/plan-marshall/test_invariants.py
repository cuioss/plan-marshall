#!/usr/bin/env python3
# ruff: noqa: I001, E402
"""Tests for the ``task_graph_valid`` invariant in ``_invariants.py``.

Drives ``_capture_task_graph_valid`` directly with real task fixtures
created via the ``manage-tasks`` command API (no direct TASK-*.json
writes). ``_run_script`` is stubbed to invoke the manage-tasks query
commands in-process and serialize their TOON output — this avoids
relying on a live ``.plan/execute-script.py`` being present in the
test worktree while still exercising the real cycle/dangling/hash
pipeline inside the invariant.

Cases covered:
    a. Healthy linear graph  → deterministic 16-char hex hash.
    b. Healthy branching graph → different deterministic hash.
    c. Self-cycle → TaskGraphInvalid with non-empty cycle.
    d. Longer cycle (3 nodes) → TaskGraphInvalid with full cycle path.
    e. Dangling reference → TaskGraphInvalid with non-empty dangling.
    f. Empty task list → stable zero-edge hash, no raise.
    g. capture_all surfaces TaskGraphInvalid on broken graph.
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

cmd_prepare_add = _crud.cmd_prepare_add
cmd_commit_add = _crud.cmd_commit_add
cmd_update = _crud.cmd_update
cmd_list = _query.cmd_list
cmd_get = _query.cmd_get


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
        if len(args) < 4:
            return None
        notation = args[0]
        if notation != 'plan-marshall:manage-tasks:manage-tasks':
            return None
        subcommand = args[1]
        plan_id = args[3]
        if subcommand == 'list':
            ns = Namespace(
                plan_id=plan_id,
                status='all',
                deliverable=None,
                ready=False,
            )
            return serialize_toon(cmd_list(ns))
        if subcommand == 'get':
            # args[4] == '--task', args[5] == str(n)
            number = int(args[5])
            ns = Namespace(plan_id=plan_id, task=number)
            return serialize_toon(cmd_get(ns))
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

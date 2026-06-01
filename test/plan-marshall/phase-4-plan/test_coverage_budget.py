#!/usr/bin/env python3
"""Tests for ``coverage_budget.py`` (D6 per-task token-budget reserve).

Drives the pure-function surface directly via ``load_script_module`` (the
``coverage_budget`` module imports cleanly — no hyphen in its filename). The
``resolve_and_reserve`` subprocess hop to ``manage-config coverage resolve`` is
stubbed by monkeypatching the module-private ``_run_coverage_resolve`` helper.

Cases (mirroring solution_outline.md § 6):
    a. Monotonicity on the scope axis (fixed thoroughness).
    b. Monotonicity on the thoroughness axis (fixed scope).
    c. Inherit / unconfigured cell maps to the baseline reserve.
    d. resolve_and_reserve returns the baseline when the cell is unconfigured.
    e. resolve_and_reserve returns the scaled reserve for a declared cell.
    f. Import-time monotonicity self-check is wired (the module loaded at all).
"""

from __future__ import annotations

import pytest

from conftest import load_script_module  # type: ignore[import-not-found]

budget = load_script_module('plan-marshall', 'phase-4-plan', 'coverage_budget.py', '_test_coverage_budget')

_SCOPES = ['change-set', 'artifact', 'component', 'module', 'overall']
_THOROUGHNESSES = ['T1', 'T2', 'T3', 'T4', 'T5']


# =============================================================================
# (a) Monotonicity on the scope axis
# =============================================================================


@pytest.mark.parametrize('thoroughness', _THOROUGHNESSES)
def test_reserve_monotonic_on_scope(thoroughness: str) -> None:
    """Raising scope (fixed thoroughness) never lowers the reserve."""
    reserves = [budget.reserve_for_cell(scope, thoroughness) for scope in _SCOPES]
    for prev, curr in zip(reserves, reserves[1:], strict=False):
        assert curr >= prev, f'reserve must be non-decreasing along scope: {reserves}'
    # And strictly increasing somewhere (the scaling is real, not flat).
    assert reserves[-1] > reserves[0], 'widest scope must reserve more than narrowest'


# =============================================================================
# (b) Monotonicity on the thoroughness axis
# =============================================================================


@pytest.mark.parametrize('scope', _SCOPES)
def test_reserve_monotonic_on_thoroughness(scope: str) -> None:
    """Raising thoroughness (fixed scope) never lowers the reserve."""
    reserves = [budget.reserve_for_cell(scope, t) for t in _THOROUGHNESSES]
    for prev, curr in zip(reserves, reserves[1:], strict=False):
        assert curr >= prev, f'reserve must be non-decreasing along thoroughness: {reserves}'
    assert reserves[-1] > reserves[0], 'highest thoroughness must reserve more than lowest'


# =============================================================================
# (c) Inherit / unconfigured baseline
# =============================================================================


def test_inherit_cell_maps_to_baseline() -> None:
    """A fully-inherit cell returns exactly the baseline reserve."""
    assert budget.reserve_for_cell('inherit', 'inherit') == budget._BASELINE_RESERVE


def test_lowest_concrete_cell_equals_baseline() -> None:
    """The lowest concrete rung on both axes equals the baseline (rank-1 anchor)."""
    assert budget.reserve_for_cell('change-set', 'T1') == budget._BASELINE_RESERVE


def test_single_inherit_axis_scales_only_other_axis() -> None:
    """An inherit on one axis leaves that axis at the baseline rank.

    ``(component, inherit)`` must equal ``(component, T1)`` — the inherit
    thoroughness contributes the rank-1 (baseline) anchor, so only scope scales.
    """
    assert budget.reserve_for_cell('component', 'inherit') == budget.reserve_for_cell('component', 'T1')


# =============================================================================
# (d) resolve_and_reserve — unconfigured → baseline
# =============================================================================


def test_resolve_and_reserve_baseline_when_unreachable(monkeypatch) -> None:
    """Executor unreachable (helper returns None) → baseline reserve."""
    monkeypatch.setattr(budget, '_run_coverage_resolve', lambda _phase: None)
    assert budget.resolve_and_reserve('any-plan', '5-execute') == budget._BASELINE_RESERVE


def test_resolve_and_reserve_baseline_when_inherit(monkeypatch) -> None:
    """coverage resolve returns an inherit cell → baseline reserve."""
    monkeypatch.setattr(
        budget,
        '_run_coverage_resolve',
        lambda _phase: {'status': 'success', 'thoroughness': 'inherit', 'scope': 'inherit'},
    )
    assert budget.resolve_and_reserve('any-plan', '5-execute') == budget._BASELINE_RESERVE


def test_resolve_and_reserve_baseline_when_resolve_errors(monkeypatch) -> None:
    """coverage resolve emits status:error → baseline reserve."""
    monkeypatch.setattr(
        budget,
        '_run_coverage_resolve',
        lambda _phase: {'status': 'error', 'error': 'boom'},
    )
    assert budget.resolve_and_reserve('any-plan', '5-execute') == budget._BASELINE_RESERVE


# =============================================================================
# (e) resolve_and_reserve — declared cell → scaled reserve
# =============================================================================


def test_resolve_and_reserve_scaled_for_declared_cell(monkeypatch) -> None:
    """A declared cell returns the scaled reserve from reserve_for_cell."""
    monkeypatch.setattr(
        budget,
        '_run_coverage_resolve',
        lambda _phase: {'status': 'success', 'thoroughness': 'T4', 'scope': 'component'},
    )
    result = budget.resolve_and_reserve('any-plan', '5-execute')
    assert result == budget.reserve_for_cell('component', 'T4')
    assert result > budget._BASELINE_RESERVE, 'a T4/component cell must reserve above baseline'


# =============================================================================
# (g) Command-construction contract — _run_coverage_resolve builds a valid argv
# =============================================================================
#
# Regression guard for the contract-drift bug where ``_run_coverage_resolve``
# passed ``--audit-plan-id`` to ``coverage resolve``. That flag is NOT declared
# on the ``coverage resolve`` argparse subparser (allow_abbrev=False, only
# --role / --phase / --default), so argparse exited 2, the subprocess returned
# non-zero, and the helper silently collapsed every declared cell to the
# baseline reserve. These tests exercise the REAL argv construction (subprocess
# is the only stub) so the contract drift is caught below the parse layer.


def test_run_coverage_resolve_argv_omits_audit_plan_id(monkeypatch) -> None:
    """The constructed argv must NOT carry the undeclared --audit-plan-id flag."""
    import subprocess

    captured: dict[str, list[str]] = {}

    class _FakeCompleted:
        returncode = 0
        stdout = 'status: success\nthoroughness: T4\nscope: component\n'

    def _fake_run(cmd, **_kwargs):
        captured['cmd'] = list(cmd)
        return _FakeCompleted()

    # Ensure the executor existence guard passes so the cmd is actually built.
    monkeypatch.setattr(budget, 'get_executor_path', lambda: budget.Path('/tmp/exec.py'))
    monkeypatch.setattr(budget.Path, 'exists', lambda _self: True)
    monkeypatch.setattr(subprocess, 'run', _fake_run)

    parsed = budget._run_coverage_resolve('5-execute')

    assert parsed == {'status': 'success', 'thoroughness': 'T4', 'scope': 'component'}
    argv = captured['cmd']
    # The bug: an undeclared --audit-plan-id (and any plan-id positional) must
    # never appear — its presence makes argparse exit 2 at runtime.
    assert '--audit-plan-id' not in argv, f'argv must omit --audit-plan-id, got {argv}'
    # The only declared flag the helper passes is --phase.
    assert '--phase' in argv
    assert 'phase-5-execute' in argv
    assert argv[2:5] == ['plan-marshall:manage-config:manage-config', 'coverage', 'resolve']


def test_resolve_and_reserve_honors_declared_cell_end_to_end(monkeypatch) -> None:
    """A configured cell is honored (not silently baseline) through the real argv.

    Stubs only the subprocess boundary, so the full ``resolve_and_reserve`` →
    ``_run_coverage_resolve`` → argv-construction path runs. Before the fix this
    returned the baseline because the argv tripped argparse exit 2.
    """
    import subprocess

    class _FakeCompleted:
        returncode = 0
        stdout = 'status: success\nthoroughness: T4\nscope: component\n'

    monkeypatch.setattr(budget, 'get_executor_path', lambda: budget.Path('/tmp/exec.py'))
    monkeypatch.setattr(budget.Path, 'exists', lambda _self: True)
    monkeypatch.setattr(subprocess, 'run', lambda _cmd, **_kw: _FakeCompleted())

    result = budget.resolve_and_reserve('any-plan', '5-execute')

    assert result == budget.reserve_for_cell('component', 'T4')
    assert result > budget._BASELINE_RESERVE, 'configured cell must scale above baseline, not collapse'


# =============================================================================
# (f) Import-time self-check wired
# =============================================================================


def test_full_matrix_is_monotonic_grid() -> None:
    """Every (scope, thoroughness) cell is >= every cell it dominates."""
    for si, scope in enumerate(_SCOPES):
        for ti, thoroughness in enumerate(_THOROUGHNESSES):
            value = budget.reserve_for_cell(scope, thoroughness)
            # Compare against the cell one rung lower on each axis (if any).
            if si > 0:
                assert value >= budget.reserve_for_cell(_SCOPES[si - 1], thoroughness)
            if ti > 0:
                assert value >= budget.reserve_for_cell(scope, _THOROUGHNESSES[ti - 1])

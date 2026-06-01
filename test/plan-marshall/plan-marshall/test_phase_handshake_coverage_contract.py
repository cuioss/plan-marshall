#!/usr/bin/env python3
# ruff: noqa: I001, E402
"""Tests for the ``coverage_contract`` phase-handshake invariant (D4).

Drives ``_capture_coverage_contract`` directly and through ``capture_all`` /
``cmd_capture`` / ``cmd_verify``. The declared cell is resolved via D3
(``manage-config coverage resolve``); ``inv._run_script`` is stubbed to return
a controllable TOON payload so no live executor is needed. The achieved cell is
read from the D5 measurement artifact, written into the plan directory's
``work/`` subdir resolved through the ``plan_context`` fixture's
``PLAN_BASE_DIR`` redirect.

Cases (mirroring solution_outline.md § 4):
    a. not-applicable when no cell declared (executor returns inherit) → None.
    b. not-applicable when declared but no measurement artifact → None.
    c. pass when achieved >= declared → returns the satisfied-cell string.
    d. BLOCK when achieved < declared at the guarded boundary → raises
       CoverageContractUnmet (one case per field + both).
    e. informational-only at a planning boundary: the capture is passive
       (returns None) when no measurement exists there, AND the
       INVARIANT_BLOCKING_SCOPE classification marks it blocking only at
       5-execute.
    f. registry wiring + exception payload surface guards.
    g. cmd_capture / cmd_verify surface ``error: coverage_contract_unmet``.
"""

from __future__ import annotations

import sys
import types

import pytest
from conftest import get_script_path  # type: ignore[import-not-found]

SCRIPT_PATH = get_script_path('plan-marshall', 'plan-marshall', 'phase_handshake.py')
SCRIPTS_DIR = SCRIPT_PATH.parent

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import _handshake_commands as cmds  # noqa: E402
import _invariants as inv  # noqa: E402
from file_ops import serialize_toon  # type: ignore[import-not-found]  # noqa: E402


# =============================================================================
# Helpers
# =============================================================================


def _resolve_toon(thoroughness: str, scope: str) -> str:
    """Build the TOON a successful ``coverage resolve`` call emits."""
    return serialize_toon(
        {
            'status': 'success',
            'role': 'phase-5-execute',
            'thoroughness': thoroughness,
            'scope': scope,
            'thoroughness_source': 'plan.phase-5-execute.coverage.thoroughness',
            'scope_source': 'plan.phase-5-execute.coverage.scope',
            'coupling': 'ok',
        }
    )


def _stub_resolve(monkeypatch: pytest.MonkeyPatch, stdout: str | None) -> list[list[str]]:
    """Stub ``inv._run_script`` to return ``stdout`` for the coverage resolve call.

    Returns the mutable list the stub appends every ``coverage resolve`` argv to,
    so a test can assert the REAL command-construction contract (e.g. that the
    undeclared ``--audit-plan-id`` flag never appears — the contract-drift bug
    that silently collapsed declared cells to "no contract").
    """
    seen_argvs: list[list[str]] = []

    def _stub(args: list[str]) -> str | None:
        # Only the coverage-resolve call should reach _run_script here.
        if args[:3] == [
            'plan-marshall:manage-config:manage-config',
            'coverage',
            'resolve',
        ]:
            seen_argvs.append(list(args))
            return stdout
        return None

    monkeypatch.setattr(inv, '_run_script', _stub)
    return seen_argvs


def _write_measurement(
    plan_context, plan_id: str, phase: str, thoroughness: str, scope: str
) -> None:
    """Write the D5 achieved-cell measurement artifact for ``plan_id``/``phase``."""
    work_dir = plan_context.plan_dir_for(plan_id) / 'work'
    work_dir.mkdir(parents=True, exist_ok=True)
    artifact = work_dir / f'coverage-measurement-{phase}.toon'
    artifact.write_text(
        serialize_toon(
            {
                'deterministic_item_coverage': 1.0,
                'item_coverage_rung': thoroughness,
                'relation_depth_verdict': thoroughness,
                'achieved_thoroughness': thoroughness,
                'achieved_scope': scope,
            }
        ),
        encoding='utf-8',
    )


def _ns(**kwargs) -> types.SimpleNamespace:
    kwargs.setdefault('override', False)
    kwargs.setdefault('reason', None)
    kwargs.setdefault('strict', False)
    return types.SimpleNamespace(**kwargs)


# =============================================================================
# (a) Not-applicable: no concrete cell declared
# =============================================================================


def test_capture_passive_when_cell_inherits(plan_context, monkeypatch) -> None:
    """Declared cell resolves to inherit → capture returns None (no block)."""
    _stub_resolve(monkeypatch, _resolve_toon('inherit', 'inherit'))
    # Even with a measurement artifact present, an inherit declaration is no
    # contract — the capture must short-circuit before reading the artifact.
    _write_measurement(plan_context, 'cov-inherit', '5-execute', 'T1', 'change-set')

    result = inv._capture_coverage_contract('cov-inherit', {}, '5-execute')

    assert result is None, f'expected None for inherit declaration, got {result!r}'


def test_capture_passive_when_resolve_unreachable(plan_context, monkeypatch) -> None:
    """Executor unreachable (run_script returns None) → capture returns None."""
    _stub_resolve(monkeypatch, None)
    _write_measurement(plan_context, 'cov-no-exec', '5-execute', 'T4', 'component')

    assert inv._capture_coverage_contract('cov-no-exec', {}, '5-execute') is None


def test_capture_passive_when_resolve_errors(plan_context, monkeypatch) -> None:
    """coverage resolve emits status:error → capture returns None (no block)."""
    _stub_resolve(monkeypatch, serialize_toon({'status': 'error', 'error': 'boom'}))
    _write_measurement(plan_context, 'cov-resolve-err', '5-execute', 'T4', 'component')

    assert inv._capture_coverage_contract('cov-resolve-err', {}, '5-execute') is None


# =============================================================================
# (a2) Command-construction contract — resolve argv omits --audit-plan-id
# =============================================================================
#
# Regression guard for the contract-drift bug where ``_resolve_declared_cell``
# passed ``--audit-plan-id {plan_id}`` to ``coverage resolve``. That flag is NOT
# declared on the ``coverage resolve`` argparse subparser (only --role / --phase
# / --default), so the live call exited 2, returned non-zero, and the declared
# cell silently collapsed to "no contract" (no block ever fired). The stub
# captures the actual argv ``_resolve_declared_cell`` builds so the drift is
# caught at the command-construction layer.


def test_resolve_argv_omits_audit_plan_id(plan_context, monkeypatch) -> None:
    """The coverage-resolve argv must NOT carry the undeclared --audit-plan-id."""
    seen = _stub_resolve(monkeypatch, _resolve_toon('T4', 'component'))
    _write_measurement(plan_context, 'cov-argv', '5-execute', 'T4', 'component')

    # Drive the full capture so _resolve_declared_cell constructs the real argv.
    inv._capture_coverage_contract('cov-argv', {}, '5-execute')

    assert seen, 'the coverage resolve call must have reached _run_script'
    argv = seen[0]
    assert '--audit-plan-id' not in argv, f'argv must omit --audit-plan-id, got {argv}'
    # Only the declared --phase flag is passed; the plan_id never appears.
    assert '--phase' in argv
    assert 'phase-5-execute' in argv
    assert 'cov-argv' not in argv, f'plan_id must not leak into the argv, got {argv}'


# =============================================================================
# (b) Not-applicable: declared but no measurement artifact
# =============================================================================


def test_capture_passive_when_no_measurement(plan_context, monkeypatch) -> None:
    """Declared cell exists but no measurement artifact → capture returns None."""
    _stub_resolve(monkeypatch, _resolve_toon('T4', 'component'))
    # Deliberately do NOT write the measurement artifact.

    result = inv._capture_coverage_contract('cov-no-measure', {}, '5-execute')

    assert result is None, f'expected None when no measurement exists, got {result!r}'


def test_capture_passive_when_measurement_malformed(plan_context, monkeypatch) -> None:
    """Measurement artifact missing achieved fields → capture returns None."""
    _stub_resolve(monkeypatch, _resolve_toon('T4', 'component'))
    work_dir = plan_context.plan_dir_for('cov-bad-measure') / 'work'
    work_dir.mkdir(parents=True, exist_ok=True)
    (work_dir / 'coverage-measurement-5-execute.toon').write_text(
        serialize_toon({'deterministic_item_coverage': 0.5}), encoding='utf-8'
    )

    assert inv._capture_coverage_contract('cov-bad-measure', {}, '5-execute') is None


# =============================================================================
# (c) Pass: achieved >= declared
# =============================================================================


def test_capture_passes_when_achieved_meets_declared(plan_context, monkeypatch) -> None:
    """achieved == declared → returns the satisfied-cell string, no raise."""
    _stub_resolve(monkeypatch, _resolve_toon('T3', 'component'))
    _write_measurement(plan_context, 'cov-meets', '5-execute', 'T3', 'component')

    result = inv._capture_coverage_contract('cov-meets', {}, '5-execute')

    assert isinstance(result, str)
    assert 'declared=T3/component' in result
    assert 'achieved=T3/component' in result


def test_capture_passes_when_achieved_exceeds_declared(plan_context, monkeypatch) -> None:
    """achieved rungs strictly above declared on both axes → pass."""
    _stub_resolve(monkeypatch, _resolve_toon('T2', 'artifact'))
    _write_measurement(plan_context, 'cov-exceeds', '5-execute', 'T4', 'module')

    result = inv._capture_coverage_contract('cov-exceeds', {}, '5-execute')

    assert isinstance(result, str)
    assert 'declared=T2/artifact' in result


# =============================================================================
# (d) Block: achieved < declared at the guarded boundary
# =============================================================================


def test_capture_blocks_on_thoroughness_shortfall(plan_context, monkeypatch) -> None:
    """achieved thoroughness below declared → CoverageContractUnmet."""
    _stub_resolve(monkeypatch, _resolve_toon('T4', 'component'))
    _write_measurement(plan_context, 'cov-short-t', '5-execute', 'T2', 'component')

    with pytest.raises(inv.CoverageContractUnmet) as excinfo:
        inv._capture_coverage_contract('cov-short-t', {}, '5-execute')

    err = excinfo.value
    assert err.phase == '5-execute'
    assert err.declared_thoroughness == 'T4'
    assert err.achieved_thoroughness == 'T2'
    assert err.shortfall == ['thoroughness']


def test_capture_blocks_on_scope_shortfall(plan_context, monkeypatch) -> None:
    """achieved scope below declared → CoverageContractUnmet."""
    _stub_resolve(monkeypatch, _resolve_toon('T3', 'module'))
    _write_measurement(plan_context, 'cov-short-s', '5-execute', 'T3', 'artifact')

    with pytest.raises(inv.CoverageContractUnmet) as excinfo:
        inv._capture_coverage_contract('cov-short-s', {}, '5-execute')

    err = excinfo.value
    assert err.declared_scope == 'module'
    assert err.achieved_scope == 'artifact'
    assert err.shortfall == ['scope']


def test_capture_blocks_on_both_axes_shortfall(plan_context, monkeypatch) -> None:
    """Both axes below declared → shortfall lists both fields."""
    _stub_resolve(monkeypatch, _resolve_toon('T4', 'module'))
    _write_measurement(plan_context, 'cov-short-both', '5-execute', 'T2', 'artifact')

    with pytest.raises(inv.CoverageContractUnmet) as excinfo:
        inv._capture_coverage_contract('cov-short-both', {}, '5-execute')

    assert excinfo.value.shortfall == ['thoroughness', 'scope']


# =============================================================================
# (e) Informational at planning boundaries
# =============================================================================


def test_blocking_scope_classified_only_for_5_execute() -> None:
    """The invariant blocks only at the 5-execute boundary."""
    scope = inv.INVARIANT_BLOCKING_SCOPE['coverage_contract']
    assert isinstance(scope, frozenset)
    assert scope == frozenset({'5-execute'})
    assert inv.is_invariant_blocking_at_phase('coverage_contract', '5-execute') is True
    for planning in ('1-init', '2-refine', '3-outline', '4-plan'):
        assert inv.is_invariant_blocking_at_phase('coverage_contract', planning) is False


def test_capture_passive_at_planning_boundary_without_measurement(
    plan_context, monkeypatch
) -> None:
    """At a planning boundary, no measurement artifact exists yet → passive.

    The declared cell is resolvable, but D5 only writes the measurement at
    the execute boundary, so a planning-phase capture short-circuits to None.
    """
    _stub_resolve(monkeypatch, _resolve_toon('T4', 'component'))
    # No measurement artifact for the 3-outline phase.

    assert inv._capture_coverage_contract('cov-planning', {}, '3-outline') is None


# =============================================================================
# (f) Registry wiring + exception payload guards
# =============================================================================


def test_coverage_contract_registered_in_invariants() -> None:
    """The registry must wire ``coverage_contract`` to the capture function."""
    names = [name for name, _, _ in inv.INVARIANTS]
    assert 'coverage_contract' in names, f'coverage_contract must be registered, got {names}'
    entry = next(t for t in inv.INVARIANTS if t[0] == 'coverage_contract')
    _name, applies_fn, capture_fn = entry
    assert capture_fn is inv._capture_coverage_contract
    assert applies_fn('any-plan', {}) is True


def test_coverage_contract_exception_carries_payload() -> None:
    """The exception class carries declared/achieved/shortfall as attributes."""
    err = inv.CoverageContractUnmet(
        phase='5-execute',
        declared_thoroughness='T4',
        declared_scope='component',
        achieved_thoroughness='T2',
        achieved_scope='component',
        shortfall=['thoroughness'],
    )
    assert err.phase == '5-execute'
    assert err.declared_thoroughness == 'T4'
    assert err.declared_scope == 'component'
    assert err.achieved_thoroughness == 'T2'
    assert err.achieved_scope == 'component'
    assert err.shortfall == ['thoroughness']
    # The message must mention the shortfall so raw-stderr readers see it.
    assert 'thoroughness' in str(err)


def test_capture_all_surfaces_coverage_contract_unmet(plan_context, monkeypatch) -> None:
    """capture_all must propagate CoverageContractUnmet from the broken cell."""
    narrowed = [('coverage_contract', inv._coverage_applicable, inv._capture_coverage_contract)]
    monkeypatch.setattr(inv, 'INVARIANTS', narrowed)
    _stub_resolve(monkeypatch, _resolve_toon('T4', 'component'))
    _write_measurement(plan_context, 'cov-cap-all', '5-execute', 'T1', 'component')

    with pytest.raises(inv.CoverageContractUnmet):
        inv.capture_all('cov-cap-all', {}, '5-execute')


# =============================================================================
# (g) cmd_capture / cmd_verify surface error: coverage_contract_unmet
# =============================================================================


@pytest.fixture
def only_coverage_invariant(monkeypatch: pytest.MonkeyPatch) -> None:
    """Narrow INVARIANTS to the real coverage_contract entry for both modules."""
    narrowed = [
        ('coverage_contract', inv._coverage_applicable, inv._capture_coverage_contract),
    ]
    monkeypatch.setattr(inv, 'INVARIANTS', narrowed)
    monkeypatch.setattr(cmds, 'INVARIANTS', narrowed)


def test_cmd_capture_returns_structured_error_on_shortfall(
    plan_context, monkeypatch, only_coverage_invariant
) -> None:
    """cmd_capture surfaces error: coverage_contract_unmet with the payload."""
    monkeypatch.setattr(cmds, '_load_status_metadata', lambda _pid: {})
    _stub_resolve(monkeypatch, _resolve_toon('T4', 'component'))
    _write_measurement(plan_context, 'cov-cmd-cap', '5-execute', 'T1', 'component')

    result = cmds.cmd_capture(_ns(plan_id='cov-cmd-cap', phase='5-execute'))

    assert result['status'] == 'error'
    assert result['error'] == 'coverage_contract_unmet'
    assert result['declared_thoroughness'] == 'T4'
    assert result['achieved_thoroughness'] == 'T1'
    assert result['shortfall'] == ['thoroughness']


def test_cmd_verify_returns_structured_error_on_shortfall(
    plan_context, monkeypatch, only_coverage_invariant
) -> None:
    """cmd_verify surfaces error: coverage_contract_unmet when achieved < declared.

    Captures a satisfied row first (achieved meets declared), then degrades the
    measurement so re-verification trips the gate.
    """
    monkeypatch.setattr(cmds, '_load_status_metadata', lambda _pid: {})
    _stub_resolve(monkeypatch, _resolve_toon('T3', 'component'))
    _write_measurement(plan_context, 'cov-cmd-ver', '5-execute', 'T3', 'component')

    captured = cmds.cmd_capture(_ns(plan_id='cov-cmd-ver', phase='5-execute'))
    assert captured['status'] == 'success', f'capture should succeed: {captured}'

    # Degrade the achieved measurement below declared.
    _write_measurement(plan_context, 'cov-cmd-ver', '5-execute', 'T1', 'component')

    result = cmds.cmd_verify(_ns(plan_id='cov-cmd-ver', phase='5-execute'))

    assert result['status'] == 'error'
    assert result['error'] == 'coverage_contract_unmet'
    assert result['shortfall'] == ['thoroughness']

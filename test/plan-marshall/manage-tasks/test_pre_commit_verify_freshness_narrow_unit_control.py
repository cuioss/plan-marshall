#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""A build row scoped to a narrow unit is not evidence that a change was covered.

A narrow unit is one test directory or one test file of a module. A step may run
it for a faster first signal, and the row that run leaves in the ledger is green
and carries the current sha. The freshness gate still refuses it: what a build
must have covered is the change's module set, and a part of a module does not
contain it.

The footprint here lies under ``marketplace/targets/``, whose module is the
``marketplace`` test tree. The required coverage is derived by the gate itself,
through the shared registered-target helper, so the cases also show the gate
reading that helper: ``marketplace`` is no bundle, and only a target set that
names it resolves the footprint to a module at all.
"""

from __future__ import annotations

from pathlib import Path

import _freshness_crosscheck as crosscheck
import file_ops
import pytest
from _pre_commit_verify_freshness_fixtures import (
    _TARGETS_FOOTPRINT,
    _TARGETS_MODULE,
    _TARGETS_NARROW_UNIT,
    _build_is_necessary,
    _expected_notations_resolve,
    _run_gate_over_footprint,
    _same_sha_row,
)
from _resolve_project_dir_fixtures import worktree_query_result

_TESTS_RUN = 412


@pytest.fixture(autouse=True)
def _stub_resolver_seam(monkeypatch):
    """Keep worktree-root resolution hermetic (no ``manage-status`` subprocess)."""
    monkeypatch.setattr(
        file_ops,
        '_query_worktree_path',
        lambda _plan_id: worktree_query_result(True, str(Path.cwd())),
    )


@pytest.fixture
def gate(plan_context, monkeypatch, tmp_path):
    """Run the gate over ``rows`` for the ``marketplace/targets/`` footprint."""

    def _gate(rows: list[dict], *, registered: frozenset[str] = frozenset({_TARGETS_MODULE, 'plan-marshall'})) -> dict:
        return _run_gate_over_footprint(
            plan_context,
            monkeypatch,
            tmp_path,
            rows,
            footprint=_TARGETS_FOOTPRINT,
            registered=registered,
            plan_id='freshness-narrow-unit-control',
        )

    return _gate


def _narrow_unit_row() -> dict:
    """A green test row scoped to one test directory of the module."""
    return _same_sha_row(f'module-tests {_TARGETS_NARROW_UNIT}', tests_run=_TESTS_RUN)


def _module_row() -> dict:
    """A green test row scoped to the module itself."""
    return _same_sha_row(f'module-tests {_TARGETS_MODULE}', tests_run=_TESTS_RUN)


def test_a_lone_narrow_unit_row_is_refused_stale(gate) -> None:
    """One green narrow-unit row, and no other row, certifies nothing."""
    result = gate([_narrow_unit_row()])

    assert result['status'] == 'stale', result
    assert result['reason'] == crosscheck.REASON_SCOPE_NARROW
    assert result['scope_cross_check'] == crosscheck.NARROW
    assert 'test' in result['missing_analyses']


def test_a_module_row_plus_a_whole_tree_quality_gate_row_is_fresh(gate) -> None:
    """The module's own test run, beside a whole-tree quality gate, covers the change."""
    result = gate([_same_sha_row('quality-gate'), _module_row()])

    assert result['status'] == 'fresh', result
    assert result['scope_cross_check'] == crosscheck.COVERED
    assert [cited['canonical'] for cited in result['contributing_rows']] == ['quality-gate', 'module-tests']


def test_a_narrow_unit_row_lends_no_test_coverage_beside_a_whole_tree_quality_gate(gate) -> None:
    """Matched control: the fresh rows with only the test row's scope narrowed are stale.

    The two row sets differ in one token - the test row's scope - so the refusal
    follows from the narrow scope alone, and the missing analysis is the one that
    row performed.
    """
    result = gate([_same_sha_row('quality-gate'), _narrow_unit_row()])

    assert result['status'] == 'stale', result
    assert result['reason'] == crosscheck.REASON_SCOPE_NARROW
    assert result['missing_analyses'] == ['test']


def test_the_module_is_resolved_through_the_registered_targets_the_helper_returns(gate) -> None:
    """Without the test tree among the registered targets, the footprint owns no module.

    The same covering rows are then refused: an unresolved path requires a
    whole-tree run, which the module-scoped test row is not.
    """
    result = gate([_same_sha_row('quality-gate'), _module_row()], registered=frozenset({'plan-marshall'}))

    assert result['status'] == 'stale', result
    assert result['missing_analyses'] == ['test']

#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""A build row narrower than a change's required coverage is not evidence for it.

A narrow unit is one test directory or one test file of a module. A step may run
it for a faster first signal, and the row that run leaves in the ledger is green
and carries the current sha. The freshness gate still refuses it: what a build
must have covered is the change's module set, and a part of a module does not
contain it.

The footprint here lies under ``marketplace/targets/``. Its module is the
``marketplace`` test tree, found through the declared source-to-test mapping -
a tree that is no bundle, reached by a mapping that names one tree holding tests
for that source and not the only one. The resolver therefore names the module
and requires the whole tree, so neither a narrow-unit row nor a row scoped to
that module covers the change; a whole-tree test row does.

The required coverage is derived by the gate itself, through the shared target
helpers, so the cases also show the gate reading them: a bundle footprint is
covered by its module's own row only while the helper names that bundle.
"""

from __future__ import annotations

from pathlib import Path

import _freshness_crosscheck as crosscheck
import file_ops
import pytest
from _pre_commit_verify_freshness_fixtures import (
    _PY_FOOTPRINT,
    _PY_FOOTPRINT_MODULE,
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

_BUNDLES = frozenset({_PY_FOOTPRINT_MODULE})
_REGISTERED = _BUNDLES | {_TARGETS_MODULE}


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
    """Run the gate over ``rows``, by default for the ``marketplace/targets/`` footprint."""

    def _gate(
        rows: list[dict],
        *,
        footprint: list[str] = _TARGETS_FOOTPRINT,
        registered: frozenset[str] = _REGISTERED,
        bundles: frozenset[str] = _BUNDLES,
    ) -> dict:
        return _run_gate_over_footprint(
            plan_context,
            monkeypatch,
            tmp_path,
            rows,
            footprint=footprint,
            registered=registered,
            bundles=bundles,
            plan_id='freshness-narrow-unit-control',
        )

    return _gate


def _test_row(scope: str = '') -> dict:
    """A green test row at ``scope``; no scope is the whole tree."""
    return _same_sha_row(f'module-tests {scope}'.strip(), tests_run=_TESTS_RUN)


def test_a_lone_narrow_unit_row_is_refused_stale(gate) -> None:
    """One green narrow-unit row, and no other row, certifies nothing."""
    result = gate([_test_row(_TARGETS_NARROW_UNIT)])

    assert result['status'] == 'stale', result
    assert result['reason'] == crosscheck.REASON_SCOPE_NARROW
    assert result['scope_cross_check'] == crosscheck.NARROW
    assert 'test' in result['missing_analyses']


def test_a_whole_tree_test_row_plus_a_whole_tree_quality_gate_row_is_fresh(gate) -> None:
    """The whole-tree test run, beside a whole-tree quality gate, covers the change."""
    result = gate([_same_sha_row('quality-gate'), _test_row()])

    assert result['status'] == 'fresh', result
    assert result['scope_cross_check'] == crosscheck.COVERED
    assert [cited['canonical'] for cited in result['contributing_rows']] == ['quality-gate', 'module-tests']


@pytest.mark.parametrize(
    'scope',
    [
        pytest.param(_TARGETS_MODULE, id='named_only_module_row'),
        pytest.param(_TARGETS_NARROW_UNIT, id='narrow_unit_row'),
    ],
)
def test_a_scoped_test_row_lends_no_test_coverage_to_a_named_only_footprint(gate, scope) -> None:
    """Matched control: the fresh rows with only the test row's scope narrowed are stale.

    The row sets differ from the fresh one in one token - the test row's scope -
    so the refusal follows from the scope alone, and the missing analysis is the
    one that row performed. A row scoped to the named-only module is refused
    exactly as a narrow unit of it is: the change requires the whole tree.
    """
    result = gate([_same_sha_row('quality-gate'), _test_row(scope)])

    assert result['status'] == 'stale', result
    assert result['reason'] == crosscheck.REASON_SCOPE_NARROW
    assert result['missing_analyses'] == ['test']


def test_a_bundle_footprint_is_covered_by_its_modules_own_test_row(gate) -> None:
    """POSITIVE CONTROL: a module row still covers a footprint its bundle owns.

    Without it, a gate that required the whole tree of every footprint would
    pass every refusal above.
    """
    result = gate([_same_sha_row('quality-gate'), _test_row(_PY_FOOTPRINT_MODULE)], footprint=_PY_FOOTPRINT)

    assert result['status'] == 'fresh', result
    assert result['scope_cross_check'] == crosscheck.COVERED


@pytest.mark.parametrize(
    ('registered', 'bundles'),
    [
        pytest.param(frozenset({_TARGETS_MODULE}), _BUNDLES, id='bundle_not_a_registered_target'),
        pytest.param(_REGISTERED, frozenset(), id='no_bundle_module_enumerated'),
    ],
)
def test_the_module_row_covers_only_while_the_shared_helpers_name_the_bundle(gate, registered, bundles) -> None:
    """The gate reads both target sets from the shared helper.

    The rows and the footprint are the positive control's. With the bundle
    missing from either set the helper returns, the same rows are refused: the
    change then requires a whole-tree run, which the module-scoped test row is
    not.
    """
    result = gate(
        [_same_sha_row('quality-gate'), _test_row(_PY_FOOTPRINT_MODULE)],
        footprint=_PY_FOOTPRINT,
        registered=registered,
        bundles=bundles,
    )

    assert result['status'] == 'stale', result
    assert result['missing_analyses'] == ['test']

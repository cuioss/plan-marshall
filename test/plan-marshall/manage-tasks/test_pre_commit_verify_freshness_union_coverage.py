#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Several build rows at one worktree sha together certify a change.

A gate that runs ``quality-gate`` and ``module-tests`` as separate builds leaves
one ledger row per build, each against the same working tree. No single row
performs every analysis a ``.py`` footprint requires, so the freshness gate
combines them: the change is covered when every required analysis is performed
by at least one row at a scope adequate for the change.

Scope is judged per analysis and never pooled, and that bound is pinned here
beside the pass it bounds, together with the deterministic naming of the rows a
verdict rests on. The guards on WHICH rows may lend coverage at all have their
own module, ``test_pre_commit_verify_freshness_union_controls.py``.
"""

from __future__ import annotations

from pathlib import Path

import _freshness_crosscheck as crosscheck
import file_ops
import pytest
from _pre_commit_verify_freshness_fixtures import (
    _build_is_necessary,
    _expected_notations_resolve,
    _py_footprint_requirement,
    _run_gate_over_rows,
    _same_sha_row,
)
from _resolve_project_dir_fixtures import worktree_query_result

_TESTS_RUN = 19007


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
    """Run the gate over ``rows`` for a ``.py`` footprint; whole-tree unless told otherwise."""

    def _gate(rows: list[dict], *, whole_tree: bool = True) -> dict:
        return _run_gate_over_rows(
            plan_context,
            monkeypatch,
            tmp_path,
            rows,
            required=_py_footprint_requirement(whole_tree=whole_tree),
            plan_id='freshness-union',
        )

    return _gate


def _cited(result: dict) -> list[tuple[int, str, str, str]]:
    """The rows a ``fresh`` verdict names, as ``(ledger_index, canonical, scope, analyses)``."""
    return [
        (row['ledger_index'], row['canonical'], row['scope'], row['analyses']) for row in result['contributing_rows']
    ]


def test_separate_whole_tree_gate_rows_together_certify_a_python_change(gate) -> None:
    """Three green whole-tree rows at one sha cover what no one of them covers alone."""
    result = gate(
        [
            _same_sha_row('quality-gate'),
            _same_sha_row('test-compile'),
            _same_sha_row('module-tests', tests_run=_TESTS_RUN),
        ]
    )

    assert result['status'] == 'fresh', result
    assert result['scope_cross_check'] == crosscheck.COVERED
    assert result['notation_cross_check'] == crosscheck.CORROBORATED
    assert _cited(result) == [
        (0, 'quality-gate', 'whole-tree', 'compile, lint'),
        (2, 'module-tests', 'whole-tree', 'test'),
    ]
    # The scalar evidence fields name the first row the verdict rests on.
    assert result['matched_entry_index'] == 0
    assert 'scope_cross_check_reason' not in result


@pytest.mark.parametrize(
    'rows',
    [
        [_same_sha_row('quality-gate plan-marshall'), _same_sha_row('module-tests', tests_run=_TESTS_RUN)],
        [_same_sha_row('quality-gate'), _same_sha_row('module-tests plan-marshall', tests_run=_TESTS_RUN)],
    ],
    ids=['module-scoped-lint-beside-whole-tree-tests', 'whole-tree-lint-beside-module-scoped-tests'],
)
def test_a_narrow_row_never_borrows_scope_from_a_wide_one(gate, rows) -> None:
    """Each analysis needs its own row at an adequate scope for a whole-tree change."""
    result = gate(rows)

    assert result['status'] == 'stale', result
    assert result['reason'] == crosscheck.REASON_SCOPE_NARROW
    assert result['scope_cross_check'] == crosscheck.NARROW
    assert 'contributing_rows' not in result


def test_module_scoped_rows_certify_a_change_confined_to_that_module(gate) -> None:
    """The control for the refusal above: the same narrow rows cover a narrow change."""
    result = gate(
        [
            _same_sha_row('quality-gate plan-marshall'),
            _same_sha_row('module-tests plan-marshall', tests_run=_TESTS_RUN),
        ],
        whole_tree=False,
    )

    assert result['status'] == 'fresh', result
    assert _cited(result) == [
        (0, 'quality-gate', 'plan-marshall', 'compile, lint'),
        (1, 'module-tests', 'plan-marshall', 'test'),
    ]


def test_a_module_scoped_lint_row_lends_nothing_to_a_change_needing_whole_tree_lint() -> None:
    """One row, two requirements: adequate scope decides what the row may lend."""
    vocabulary, reason = crosscheck.load_analysis_vocabulary()
    assert vocabulary is not None, reason
    row = _same_sha_row('quality-gate plan-marshall')

    tree_wide = crosscheck.row_contribution(row, _py_footprint_requirement(whole_tree=True), vocabulary)
    confined = crosscheck.row_contribution(row, _py_footprint_requirement(whole_tree=False), vocabulary)

    assert tree_wide == frozenset()
    assert confined == frozenset({vocabulary.compile, vocabulary.lint})


def test_the_cited_rows_are_the_first_adequate_row_per_analysis_in_ledger_order(gate) -> None:
    """Later rows that repeat an already-credited analysis are not cited."""
    result = gate(
        [
            _same_sha_row('compile'),
            _same_sha_row('quality-gate'),
            _same_sha_row('module-tests', tests_run=_TESTS_RUN),
            _same_sha_row('module-tests', tests_run=_TESTS_RUN),
            _same_sha_row('quality-gate'),
        ]
    )

    assert result['status'] == 'fresh', result
    assert _cited(result) == [
        (0, 'compile', 'whole-tree', 'compile'),
        (1, 'quality-gate', 'whole-tree', 'lint'),
        (2, 'module-tests', 'whole-tree', 'test'),
    ]


def test_a_row_covering_the_change_alone_is_cited_alone(gate) -> None:
    """A single covering row is the whole evidence, even behind a partial row."""
    result = gate([_same_sha_row('quality-gate'), _same_sha_row('verify', tests_run=_TESTS_RUN)])

    assert result['status'] == 'fresh', result
    assert _cited(result) == [(1, 'verify', 'whole-tree', 'compile, lint, test')]
    assert result['matched_entry_index'] == 1

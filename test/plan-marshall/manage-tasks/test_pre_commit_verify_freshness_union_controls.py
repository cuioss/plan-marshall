#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The controls that keep the freshness gate closed while it credits a union of rows.

Crediting several build rows together widens what the gate accepts. Each case
here pins one guard that bounds the widening, and is built so that the gate
would answer ``fresh`` if that guard were removed: the rows are an otherwise
complete covering set, and only the pinned guard stands between them and a pass.

* The union is taken at the working tree's own sha, never across shas.
* A build that did not finish is never a candidate, so it lends nothing.
* A test row that measured zero tests lends no test coverage.
* A row the attribution check refuses lends nothing.

The fifth case is the control in the other direction: a single covering row
still passes, and names itself exactly as it did before rows could be combined.
"""

from __future__ import annotations

from pathlib import Path

import _freshness_crosscheck as crosscheck
import file_ops
import pytest
from _pre_commit_verify_freshness_fixtures import (
    _OTHER_SHA,
    _build_is_necessary,
    _expected_notations_resolve,
    _py_footprint_requirement,
    _run_gate_over_rows,
    _same_sha_row,
)
from _resolve_project_dir_fixtures import worktree_query_result

_TESTS_RUN = 19007

#: A notation the pinned architecture resolution does not contain.
_UNRESOLVED_NOTATION = 'plan-marshall:build-gradle:gradle'


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
    """Run the gate over ``rows`` for a ``.py`` footprint that requires whole-tree coverage."""

    def _gate(rows: list[dict]) -> dict:
        return _run_gate_over_rows(
            plan_context,
            monkeypatch,
            tmp_path,
            rows,
            required=_py_footprint_requirement(whole_tree=True),
            plan_id='freshness-union-controls',
        )

    return _gate


def _covering_rows() -> list[dict]:
    """Three green whole-tree rows that together cover a ``.py`` footprint."""
    return [
        _same_sha_row('quality-gate'),
        _same_sha_row('test-compile'),
        _same_sha_row('module-tests', tests_run=_TESTS_RUN),
    ]


def test_a_covering_set_stamped_at_another_sha_does_not_certify_this_tree(gate) -> None:
    """Rows describe the tree whose sha they carry, so a moved tree has no evidence."""
    rows = [{**row, 'worktree_sha': _OTHER_SHA} for row in _covering_rows()]

    result = gate(rows)

    assert result['status'] == 'stale', result
    assert result['reason'] == 'worktree_mutated'


@pytest.mark.parametrize('unfinished', ['killed', 'timeout'])
def test_a_test_build_that_did_not_finish_lends_no_test_coverage(gate, unfinished) -> None:
    """A row that is not a success is never a candidate, whatever it would have covered."""
    lint, compile_only, tests = _covering_rows()

    result = gate([lint, compile_only, {**tests, 'status': unfinished}])

    assert result['status'] == 'stale', result
    assert result['missing_analyses'] == ['test']


def test_a_test_row_that_measured_zero_tests_lends_no_test_coverage(gate) -> None:
    """A measured zero is not test coverage, alone or inside a union."""
    result = gate(
        [
            _same_sha_row('quality-gate'),
            _same_sha_row('test-compile'),
            _same_sha_row('module-tests', tests_run=0),
        ]
    )

    assert result['status'] == 'stale', result
    assert result['reason'] == crosscheck.REASON_SCOPE_NARROW
    assert result['missing_analyses'] == ['test']


def test_a_single_covering_row_names_itself_as_the_whole_evidence(gate) -> None:
    """One row covering the change alone is cited alone, by its own identity."""
    row = _same_sha_row('verify', tests_run=_TESTS_RUN)

    result = gate([row])

    assert result['status'] == 'fresh', result
    assert result['matched_entry_index'] == 0
    assert result['matched_notation'] == row['notation']
    assert result['matched_plan_id'] == row['plan_id']
    assert result['timestamp_iso'] == row['timestamp_iso']
    assert [(cited['ledger_index'], cited['canonical']) for cited in result['contributing_rows']] == [(0, 'verify')]


def test_a_row_the_architecture_cannot_attribute_lends_nothing(gate) -> None:
    """An analysis only an unattributable row performed is still missing."""
    result = gate(
        [
            _same_sha_row('quality-gate'),
            _same_sha_row('module-tests', tests_run=_TESTS_RUN, notation=_UNRESOLVED_NOTATION),
        ]
    )

    assert result['status'] == 'stale', result
    assert result['reason'] == crosscheck.REASON_NO_ADMISSIBLE_ROW
    assert result['missing_analyses'] == ['test']

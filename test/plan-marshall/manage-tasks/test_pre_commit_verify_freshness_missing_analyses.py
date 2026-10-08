#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""A coverage refusal names the analyses no build row covered.

When several build rows at one worktree sha each perform part of what a change
requires, the per-row tokens say why each row falls short alone. They do not
say which required analysis is still missing, and that is the fact a reader
needs to choose the remedy. The stale record therefore carries
``missing_analyses`` beside ``row_scopes``, and its message names them.

The reason token stays ``build_scope_narrow``, so a consumer that branches on it
is unaffected.
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
    """Run the gate over ``rows`` for a ``.py`` footprint that requires whole-tree coverage."""

    def _gate(rows: list[dict]) -> dict:
        return _run_gate_over_rows(
            plan_context,
            monkeypatch,
            tmp_path,
            rows,
            required=_py_footprint_requirement(whole_tree=True),
            plan_id='freshness-missing',
        )

    return _gate


def test_a_ledger_with_no_test_row_names_test_as_the_missing_analysis(gate) -> None:
    """Green compile and lint rows leave exactly the test analysis uncovered."""
    result = gate([_same_sha_row('quality-gate'), _same_sha_row('test-compile')])

    assert result['status'] == 'stale', result
    assert result['reason'] == crosscheck.REASON_SCOPE_NARROW
    assert result['missing_analyses'] == ['test']
    assert 'Run the missing analysis (test)' in result['message']


def test_module_scoped_lint_rows_leave_lint_missing_for_a_whole_tree_change(gate) -> None:
    """A lint row too narrow for the change does not count as lint coverage."""
    result = gate(
        [
            _same_sha_row('quality-gate plan-marshall'),
            _same_sha_row('test-compile'),
            _same_sha_row('module-tests', tests_run=_TESTS_RUN),
        ]
    )

    assert result['status'] == 'stale', result
    assert result['reason'] == crosscheck.REASON_SCOPE_NARROW
    assert result['missing_analyses'] == ['lint']


def test_a_fresh_verdict_carries_no_missing_analyses(gate) -> None:
    """The control: once every analysis is covered the record names nothing missing."""
    result = gate([_same_sha_row('quality-gate'), _same_sha_row('module-tests', tests_run=_TESTS_RUN)])

    assert result['status'] == 'fresh', result
    assert 'missing_analyses' not in result

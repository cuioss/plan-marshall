#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Every manage-status walker of the worktree root skips the reserved ledger tree.

The worktree root holds the plan worktrees AND one reserved non-plan entry, the
shared orchestrator ledger worktree. ``manage-status list``, ``census`` and the
sibling-collision enumeration each walk that root's children, so each must skip
the reserved entry by its name — never report it as a plan, count it into a
cohort, or offer its contents as a sibling.

The reserved tree in these fixtures is given a DECOY plan store — a
``.plan/local/plans/{id}/status.json`` carrying an open phase — so its absence
from every result cannot come from the tree merely lacking a plan layout. The
matched control places the identical decoy tree under a non-reserved name, and
there it IS reported: the skip is keyed on the reserved name, not on the layout.

The store is the ``PLAN_BASE_DIR`` override, which every one of the three walkers
resolves its worktree root against; both override spellings are pinned so no
stale in-process override relocates it.
"""

from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path
from typing import Any

import pytest
from marketplace_paths import ORCHESTRATOR_WORKTREE_KEY, WORKTREES_DIRNAME

from conftest import load_script_module

status_query = load_script_module('plan-marshall', 'manage-status', '_status_query.py', register=False)
sibling_collision = load_script_module('plan-marshall', 'manage-status', '_cmd_sibling_collision.py', register=False)

_REAL_PLAN = 'real-worktree-plan'
_DECOY_PLAN = 'decoy-ledger-plan'
_NON_RESERVED_TREE = 'ledger-lookalike'

#: ``{case id: (name of the tree holding the decoy store, whether the decoy is reported)}``.
_TREE_CASES = {
    'reserved-tree-is-skipped': (ORCHESTRATOR_WORKTREE_KEY, False),
    'non-reserved-control-is-reported': (_NON_RESERVED_TREE, True),
}


def _write_open_plan(plan_dir: Path) -> None:
    """Seed one plan directory whose ``status.json`` holds an open phase."""
    plan_dir.mkdir(parents=True)
    document: dict[str, Any] = {
        'title': plan_dir.name,
        'current_phase': '5-execute',
        'phases': [{'name': '1-init', 'status': 'done'}, {'name': '5-execute', 'status': 'in_progress'}],
    }
    (plan_dir / 'status.json').write_text(json.dumps(document), encoding='utf-8')


@pytest.fixture
def store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """The override store, holding one real plan worktree and nothing else yet."""
    base = (tmp_path / 'plan-store').resolve()
    base.mkdir()
    monkeypatch.setenv('PLAN_BASE_DIR', str(base))
    import file_ops

    # A stale in-process ``set_base_dir()`` override would outrank the env var.
    monkeypatch.setattr(file_ops, '_BASE_DIR_OVERRIDE', None)
    _write_open_plan(base / WORKTREES_DIRNAME / _REAL_PLAN / '.plan' / 'local' / 'plans' / _REAL_PLAN)
    return base


def _stage_decoy(store: Path, tree_name: str) -> None:
    """Give the tree ``tree_name`` under the worktree root a decoy plan store."""
    _write_open_plan(store / WORKTREES_DIRNAME / tree_name / '.plan' / 'local' / 'plans' / _DECOY_PLAN)


def _expected_ids(decoy_reported: bool) -> set[str]:
    return {_REAL_PLAN, _DECOY_PLAN} if decoy_reported else {_REAL_PLAN}


@pytest.mark.parametrize(('tree_name', 'decoy_reported'), list(_TREE_CASES.values()), ids=list(_TREE_CASES))
def test_list_reports_only_plans_outside_the_reserved_tree(store, tree_name, decoy_reported):
    _stage_decoy(store, tree_name)

    result = status_query.cmd_list(Namespace(filter=None))

    assert {plan['id'] for plan in result['plans']} == _expected_ids(decoy_reported)
    assert {plan['location'] for plan in result['plans']} == {'worktree'}


@pytest.mark.parametrize(('tree_name', 'decoy_reported'), list(_TREE_CASES.values()), ids=list(_TREE_CASES))
def test_census_worktree_cohort_excludes_the_reserved_tree(store, tree_name, decoy_reported):
    _stage_decoy(store, tree_name)

    result = status_query.cmd_census(Namespace())

    worktree_rows = [row for row in result['cohorts'] if row['cohort'] == 'worktree']
    assert len(worktree_rows) == 1
    row = worktree_rows[0]
    expected = _expected_ids(decoy_reported)
    assert row['coverage'] == 'complete'
    assert row['population'] == len(expected)
    assert row['unreadable_count'] == 0
    recorded = {record['id'] for record in result['open_phase_records'] if record['cohort'] == 'worktree'}
    assert recorded == expected


@pytest.mark.parametrize(('tree_name', 'decoy_reported'), list(_TREE_CASES.values()), ids=list(_TREE_CASES))
def test_census_never_credits_the_reserved_tree_as_unreadable(store, tree_name, decoy_reported):
    """A broken store inside the reserved tree is skipped, not counted as a shortfall.

    The plan store is a regular FILE, so listing it fails. Under a non-reserved
    name that failure degrades the cohort to ``partial``; under the reserved name
    the tree is never probed, so the cohort stays ``complete``.
    """
    broken_store = store / WORKTREES_DIRNAME / tree_name / '.plan' / 'local' / 'plans'
    broken_store.parent.mkdir(parents=True)
    broken_store.write_text('not a directory\n', encoding='utf-8')

    result = status_query.cmd_census(Namespace())

    row = next(row for row in result['cohorts'] if row['cohort'] == 'worktree')
    if decoy_reported:
        assert (row['coverage'], row['unreadable_count']) == ('partial', 1)
        assert tree_name in row['reason']
    else:
        assert (row['coverage'], row['unreadable_count']) == ('complete', 0)
    assert row['population'] == 1


@pytest.mark.parametrize(('tree_name', 'decoy_reported'), list(_TREE_CASES.values()), ids=list(_TREE_CASES))
def test_sibling_collision_enumeration_excludes_the_reserved_tree(store, tree_name, decoy_reported):
    _stage_decoy(store, tree_name)

    active = sibling_collision._iter_active_plan_dirs()

    assert set(active) == _expected_ids(decoy_reported)

#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Regression tests for worktree discipline (PLAN-02).

Covers the move-in seam owning the flag
(``prepare_execute`` persists ``worktree_materialized``), the dispatch guard
reader (``inject_project_dir.guarded_inject`` refuses Bucket-B invocation
while unset), and the documentation surfaces naming each boundary plus the
residual (no script gate binds a free agent's Edit tool).
"""

import json
from pathlib import Path

import pytest
from inject_project_dir import (
    WORKTREE_NOT_MATERIALIZED,
    guarded_inject,
    is_bucket_b_notation,
    refusal_needed,
)

from conftest import get_scripts_dir, run_script

REPO_ROOT = Path(__file__).resolve().parents[3]

PREPARE_SCRIPT = get_scripts_dir('plan-marshall', 'workflow-integration-git') / 'prepare_execute.py'
INJECT_SCRIPT = get_scripts_dir('plan-marshall', 'execute-task') / 'inject_project_dir.py'

BUCKET_B = 'plan-marshall:build-pyproject:pyproject_build'
BUCKET_A = 'plan-marshall:manage-tasks:manage-tasks'


def _bucket_b_command() -> str:
    return f'python3 .plan/execute-script.py {BUCKET_B} run --command-args "module-tests"'


def _bucket_a_command() -> str:
    return f'python3 .plan/execute-script.py {BUCKET_A} list --plan-id demo'


# =============================================================================
# Guard matrix: refusal_needed is pure and exhaustive over the four states
# =============================================================================


def test_bucket_b_use_worktree_unset_refuses():
    assert refusal_needed(BUCKET_B, use_worktree=True, worktree_materialized=False) is True


def test_bucket_b_materialized_passes():
    assert refusal_needed(BUCKET_B, use_worktree=True, worktree_materialized=True) is False


def test_bucket_b_unknown_flag_stays_fail_open():
    assert refusal_needed(BUCKET_B, use_worktree=True, worktree_materialized=None) is False


def test_bucket_b_direct_flow_passes_while_unset():
    assert refusal_needed(BUCKET_B, use_worktree=False, worktree_materialized=False) is False


def test_bucket_a_never_refuses_while_unset():
    assert refusal_needed(BUCKET_A, use_worktree=True, worktree_materialized=False) is False
    assert is_bucket_b_notation(BUCKET_A) is False
    assert is_bucket_b_notation(BUCKET_B) is True


# =============================================================================
# guarded_inject: refusal payload vs injection passthrough
# =============================================================================


def test_guarded_inject_refuses_bucket_b_while_unset():
    result = guarded_inject(_bucket_b_command(), 'demo', use_worktree=True, worktree_materialized=False)
    assert result['status'] == 'error'
    assert result['error'] == WORKTREE_NOT_MATERIALIZED
    assert result['plan_id'] == 'demo'


def test_guarded_inject_passes_once_materialized():
    result = guarded_inject(_bucket_b_command(), 'demo', use_worktree=True, worktree_materialized=True)
    assert result['status'] == 'success'
    assert result['injected'] is True
    assert '--plan-id demo' in result['rewritten_command']


def test_guarded_inject_leaves_bucket_a_alone_while_unset():
    command = _bucket_a_command()
    result = guarded_inject(command, 'demo', use_worktree=True, worktree_materialized=False)
    assert result['status'] == 'success'
    assert result['injected'] is False
    assert result['rewritten_command'] == command


# =============================================================================
# CLI: refusal surfaces through the executor-facing TOON contract
# =============================================================================


def _parse_cli_output(stdout: str) -> dict:
    from toon_parser import parse_toon  # lazy: keeps stdlib-only module top

    return parse_toon(stdout)


def test_cli_refuses_bucket_b_while_unset(tmp_path):
    result = run_script(
        INJECT_SCRIPT,
        'run',
        '--command',
        _bucket_b_command(),
        '--plan-id',
        'demo',
        '--worktree-materialized',
        'false',
        cwd=tmp_path,
    )
    assert result.success, f'CLI failed: {result.stderr}'
    parsed = _parse_cli_output(result.stdout)
    assert parsed['status'] == 'error'
    assert parsed['error'] == WORKTREE_NOT_MATERIALIZED


def test_cli_passes_once_materialized(tmp_path):
    result = run_script(
        INJECT_SCRIPT,
        'run',
        '--command',
        _bucket_b_command(),
        '--plan-id',
        'demo',
        '--worktree-materialized',
        'true',
        cwd=tmp_path,
    )
    assert result.success, f'CLI failed: {result.stderr}'
    parsed = _parse_cli_output(result.stdout)
    assert parsed['status'] == 'success'
    assert parsed['injected'] is True


def test_cli_without_flag_preserves_legacy_behaviour(tmp_path):
    result = run_script(
        INJECT_SCRIPT,
        'run',
        '--command',
        _bucket_b_command(),
        '--plan-id',
        'demo',
        cwd=tmp_path,
    )
    assert result.success, f'CLI failed: {result.stderr}'
    parsed = _parse_cli_output(result.stdout)
    assert parsed['status'] == 'success'
    assert parsed['injected'] is True


# =============================================================================
# prepare_execute: flag persist/is roundtrip against an isolated worktree
# =============================================================================


def test_prepare_execute_flag_roundtrip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import importlib.util

    spec = importlib.util.spec_from_file_location('prepare_execute_isolated', PREPARE_SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    monkeypatch.syspath_prepend(str(PREPARE_SCRIPT.parent))
    spec.loader.exec_module(module)

    plan_id = 'flag-roundtrip-demo'
    worktree_path = tmp_path / 'wt'
    wt_status = worktree_path / '.plan' / 'local' / 'plans' / plan_id / 'status.json'
    wt_status.parent.mkdir(parents=True)
    wt_status.write_text(json.dumps({'plan_id': plan_id, 'metadata': {}}) + '\n', encoding='utf-8')

    assert module.is_worktree_materialized(plan_id, worktree_path) is False
    persisted, _detail = module._persist_worktree_materialized(plan_id, worktree_path)
    assert persisted is True
    assert module.is_worktree_materialized(plan_id, worktree_path) is True


def test_prepare_execute_flag_fail_closed_on_unreadable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import importlib.util

    spec = importlib.util.spec_from_file_location('prepare_execute_closed', PREPARE_SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    monkeypatch.syspath_prepend(str(PREPARE_SCRIPT.parent))
    spec.loader.exec_module(module)

    assert module.is_worktree_materialized('no-such-plan', tmp_path / 'missing-wt') is False


# =============================================================================
# Docs: every boundary plus the residual is named in the tree
# =============================================================================


def test_docs_name_boundaries_and_residual():
    repo = REPO_ROOT
    planning = (
        repo / 'marketplace' / 'bundles' / 'plan-marshall' / 'skills' / 'plan-marshall' / 'workflow' / 'planning.md'
    ).read_text(encoding='utf-8')
    outline = (
        repo
        / 'marketplace'
        / 'bundles'
        / 'plan-marshall'
        / 'skills'
        / 'plan-marshall'
        / 'workflow'
        / 'planning-outline.md'
    ).read_text(encoding='utf-8')
    operations = (
        repo
        / 'marketplace'
        / 'bundles'
        / 'plan-marshall'
        / 'skills'
        / 'phase-5-execute'
        / 'standards'
        / 'operations.md'
    ).read_text(encoding='utf-8')

    assert 'Post-dispatch contract assertion (1→2 boundary)' in planning
    assert 'Hand-off admission gate' in planning
    assert '1→2 boundary assertion' in outline
    assert 'Session-Start Tree Check' in operations
    assert "no script gate binds a free agent's Edit tool" in operations

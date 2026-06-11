#!/usr/bin/env python3
"""Tests for the ``pre-commit-verify-freshness`` subcommand of manage-tasks.

The subcommand answers a single deterministic question — "does the unified
change-ledger contain a ``kind=build`` entry with ``exit_code == 0`` whose
``worktree_sha`` equals the CURRENT working-tree currency hash?" — and returns
one of three statuses (``fresh``, ``stale``, ``undecidable``) for the
orchestrator to consume as a fail-closed gate. See
``marketplace/bundles/plan-marshall/skills/manage-tasks/SKILL.md`` §
"Pre-Commit Verify Freshness" for the contract.

The freshness primitive is the change-ledger lookup, NOT a file-mtime heuristic.
Tests stub the two module-level boundary functions the command imports:

- ``compute_worktree_sha`` — the working-tree currency hash. Stubbed to a
  deterministic literal so the lookup match is exercised without standing up a
  real git worktree. Returning ``None`` exercises the ``head_unresolvable``
  fail-closed path.
- ``resolve_ledger_path`` — the tracked-config-dir ledger location. Stubbed to a
  temp JSONL file so the test controls the ledger entries directly.

Together they make the gate's three-way decision (``fresh`` / ``stale`` /
``undecidable``) deterministic and isolated from both git and the real ledger.
"""

from __future__ import annotations

import importlib.util
import json
from argparse import Namespace
from pathlib import Path

from conftest import PROJECT_ROOT

# Load the cmd module via importlib (mirrors the qgate-mechanical test bootstrap).
_SCRIPTS_DIR = (
    PROJECT_ROOT
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-tasks'
    / 'scripts'
)


def _load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    assert spec is not None
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


_freshness_mod = _load_module(
    '_cmd_pre_commit_verify_freshness_under_test',
    '_cmd_pre_commit_verify_freshness.py',
)
cmd_pre_commit_verify_freshness = _freshness_mod.cmd_pre_commit_verify_freshness

# The current-sha literal the stubbed ``compute_worktree_sha`` returns. A
# ``kind=build`` entry whose ``worktree_sha`` matches this is a fresh build.
_CURRENT_SHA = 'a' * 64
_OTHER_SHA = 'b' * 64


# =============================================================================
# Fixture builders
# =============================================================================


def _write_status(plan_dir: Path, *, worktree_path: str = '') -> Path:
    """Write a minimal ``status.json`` whose metadata.worktree_path is set.

    Empty ``worktree_path`` (the default) leaves the worktree resolution to fall
    back to the current working directory. ``compute_worktree_sha`` is stubbed,
    so the resolved root never reaches real git — the status file exists only so
    ``_resolve_worktree_root`` has a deterministic input.
    """
    status = {
        'plan_id': plan_dir.name,
        'metadata': {'worktree_path': worktree_path},
    }
    status_path = plan_dir / 'status.json'
    status_path.write_text(json.dumps(status), encoding='utf-8')
    return status_path


def _build_entry(
    *,
    worktree_sha: str | None = _CURRENT_SHA,
    exit_code: int = 0,
    notation: str = 'plan-marshall:build-pyproject:pyproject_build',
    plan_id: str | None = 'freshness-test',
    timestamp_iso: str = '2026-06-11T12:00:00Z',
) -> dict:
    """Construct a ``kind=build`` ledger record dict.

    Mirrors the shape produced by ``_ledger_core.build_record``. The gate filters
    on ``kind``, ``exit_code`` and ``worktree_sha`` only — never ``notation`` or
    ``plan_id`` — so those fields are parameterised to prove tier/tool agnosticism.
    """
    return {
        'kind': 'build',
        'notation': notation,
        'plan_id': plan_id,
        'args': 'run',
        'exit_code': exit_code,
        'worktree_sha': worktree_sha,
        'log_file': None,
        'timestamp_iso': timestamp_iso,
    }


def _change_entry(*, worktree_sha: str = _CURRENT_SHA) -> dict:
    """Construct a ``kind=change`` ledger record dict (must NOT satisfy the gate)."""
    return {
        'kind': 'change',
        'deliverable_id': 'D1',
        'commit_sha': 'c' * 40,
        'changed_paths': ['src.py'],
        'worktree_sha': worktree_sha,
        'timestamp_iso': '2026-06-11T11:00:00Z',
    }


def _write_ledger(tmp_path: Path, entries: list[dict]) -> Path:
    """Write a JSONL change-ledger file with the given entries and return its path."""
    ledger_path = tmp_path / 'change-ledger.jsonl'
    lines = [json.dumps(entry, sort_keys=True) for entry in entries]
    ledger_path.write_text('\n'.join(lines) + ('\n' if lines else ''), encoding='utf-8')
    return ledger_path


def _stub_worktree_sha(monkeypatch, sha: str | None) -> None:
    """Patch ``compute_worktree_sha`` so no real git worktree is required."""
    monkeypatch.setattr(_freshness_mod, 'compute_worktree_sha', lambda root: sha)


def _stub_ledger_path(monkeypatch, ledger_path: Path) -> None:
    """Patch ``resolve_ledger_path`` so the gate reads the test's temp ledger."""
    monkeypatch.setattr(_freshness_mod, 'resolve_ledger_path', lambda: ledger_path)


# =============================================================================
# Tests
# =============================================================================


def test_fresh_when_matching_build_entry_present(plan_context, monkeypatch, tmp_path) -> None:
    """status: fresh — ledger has a successful build for the current sha."""
    plan_dir = plan_context.plan_dir_for('freshness-fresh')
    _write_status(plan_dir)
    _stub_worktree_sha(monkeypatch, _CURRENT_SHA)
    ledger_path = _write_ledger(tmp_path, [_build_entry(worktree_sha=_CURRENT_SHA)])
    _stub_ledger_path(monkeypatch, ledger_path)

    result = cmd_pre_commit_verify_freshness(Namespace(plan_id='freshness-fresh'))

    assert result['status'] == 'fresh', result
    assert result['plan_id'] == 'freshness-fresh'
    assert result['worktree_sha'] == _CURRENT_SHA
    assert result['matched_notation'] == 'plan-marshall:build-pyproject:pyproject_build'


def test_stale_when_ledger_empty(plan_context, monkeypatch, tmp_path) -> None:
    """ledger empty -> fail closed (undecidable / no_registry)."""
    plan_dir = plan_context.plan_dir_for('freshness-empty')
    _write_status(plan_dir)
    _stub_worktree_sha(monkeypatch, _CURRENT_SHA)
    ledger_path = _write_ledger(tmp_path, [])
    _stub_ledger_path(monkeypatch, ledger_path)

    result = cmd_pre_commit_verify_freshness(Namespace(plan_id='freshness-empty'))

    assert result['status'] == 'undecidable', result
    assert result['reason'] == 'no_registry'
    assert result['worktree_sha'] == _CURRENT_SHA
    assert 'ledger_path' in result


def test_stale_when_ledger_absent(plan_context, monkeypatch, tmp_path) -> None:
    """ledger file missing entirely -> fail closed (undecidable / no_registry)."""
    plan_dir = plan_context.plan_dir_for('freshness-no-file')
    _write_status(plan_dir)
    _stub_worktree_sha(monkeypatch, _CURRENT_SHA)
    # Point at a path that was never written.
    _stub_ledger_path(monkeypatch, tmp_path / 'never-written.jsonl')

    result = cmd_pre_commit_verify_freshness(Namespace(plan_id='freshness-no-file'))

    assert result['status'] == 'undecidable', result
    assert result['reason'] == 'no_registry'


def test_stale_when_build_entry_for_different_sha(plan_context, monkeypatch, tmp_path) -> None:
    """ledger has a successful build but for a DIFFERENT sha -> stale (fail)."""
    plan_dir = plan_context.plan_dir_for('freshness-diff-sha')
    _write_status(plan_dir)
    _stub_worktree_sha(monkeypatch, _CURRENT_SHA)
    # Successful build, wrong worktree_sha — the worktree mutated since the build.
    ledger_path = _write_ledger(tmp_path, [_build_entry(worktree_sha=_OTHER_SHA)])
    _stub_ledger_path(monkeypatch, ledger_path)

    result = cmd_pre_commit_verify_freshness(Namespace(plan_id='freshness-diff-sha'))

    assert result['status'] == 'stale', result
    assert result['worktree_sha'] == _CURRENT_SHA


def test_stale_when_only_failed_build_for_current_sha(plan_context, monkeypatch, tmp_path) -> None:
    """A build entry matches the sha but ``exit_code != 0`` -> stale (fail closed)."""
    plan_dir = plan_context.plan_dir_for('freshness-failed-build')
    _write_status(plan_dir)
    _stub_worktree_sha(monkeypatch, _CURRENT_SHA)
    ledger_path = _write_ledger(
        tmp_path, [_build_entry(worktree_sha=_CURRENT_SHA, exit_code=1)]
    )
    _stub_ledger_path(monkeypatch, ledger_path)

    result = cmd_pre_commit_verify_freshness(Namespace(plan_id='freshness-failed-build'))

    assert result['status'] == 'stale', result


def test_stale_when_only_change_entry_matches_sha(plan_context, monkeypatch, tmp_path) -> None:
    """A ``kind=change`` entry for the current sha must NOT satisfy the gate."""
    plan_dir = plan_context.plan_dir_for('freshness-change-only')
    _write_status(plan_dir)
    _stub_worktree_sha(monkeypatch, _CURRENT_SHA)
    ledger_path = _write_ledger(tmp_path, [_change_entry(worktree_sha=_CURRENT_SHA)])
    _stub_ledger_path(monkeypatch, ledger_path)

    result = cmd_pre_commit_verify_freshness(Namespace(plan_id='freshness-change-only'))

    assert result['status'] == 'stale', result


def test_undecidable_when_worktree_sha_unresolvable(plan_context, monkeypatch, tmp_path) -> None:
    """ledger query cannot run because the sha is undefined -> conservative fail.

    ``compute_worktree_sha`` returns ``None`` (non-git directory / repo with no
    commit), so no positive freshness proof can be established and the gate fails
    closed BEFORE the ledger is even consulted.
    """
    plan_dir = plan_context.plan_dir_for('freshness-no-sha')
    _write_status(plan_dir)
    _stub_worktree_sha(monkeypatch, None)
    # A fresh-looking ledger exists but must be irrelevant — the sha is undefined.
    ledger_path = _write_ledger(tmp_path, [_build_entry(worktree_sha=_CURRENT_SHA)])
    _stub_ledger_path(monkeypatch, ledger_path)

    result = cmd_pre_commit_verify_freshness(Namespace(plan_id='freshness-no-sha'))

    assert result['status'] == 'undecidable', result
    assert result['reason'] == 'head_unresolvable'


def test_fresh_match_is_notation_and_tier_agnostic(plan_context, monkeypatch, tmp_path) -> None:
    """A non-pyproject, plan-less (``plan_id=None``) build still satisfies the gate.

    The query filters on ``kind``, ``exit_code`` and ``worktree_sha`` only — so a
    Maven build from an orchestrator-driven global-tier run with ``plan_id=None``
    proves freshness exactly as a plan-scoped pyproject build does.
    """
    plan_dir = plan_context.plan_dir_for('freshness-agnostic')
    _write_status(plan_dir)
    _stub_worktree_sha(monkeypatch, _CURRENT_SHA)
    ledger_path = _write_ledger(
        tmp_path,
        [
            _build_entry(
                worktree_sha=_CURRENT_SHA,
                notation='plan-marshall:build-maven:maven',
                plan_id=None,
            )
        ],
    )
    _stub_ledger_path(monkeypatch, ledger_path)

    result = cmd_pre_commit_verify_freshness(Namespace(plan_id='freshness-agnostic'))

    assert result['status'] == 'fresh', result
    assert result['matched_notation'] == 'plan-marshall:build-maven:maven'


def test_fresh_among_mixed_entries(plan_context, monkeypatch, tmp_path) -> None:
    """The matching successful build is found among non-matching noise entries."""
    plan_dir = plan_context.plan_dir_for('freshness-mixed')
    _write_status(plan_dir)
    _stub_worktree_sha(monkeypatch, _CURRENT_SHA)
    ledger_path = _write_ledger(
        tmp_path,
        [
            _change_entry(worktree_sha=_OTHER_SHA),
            _build_entry(worktree_sha=_OTHER_SHA),
            _build_entry(worktree_sha=_CURRENT_SHA, exit_code=1),
            _build_entry(worktree_sha=_CURRENT_SHA, notation='plan-marshall:build-npm:npm'),
        ],
    )
    _stub_ledger_path(monkeypatch, ledger_path)

    result = cmd_pre_commit_verify_freshness(Namespace(plan_id='freshness-mixed'))

    assert result['status'] == 'fresh', result
    assert result['matched_notation'] == 'plan-marshall:build-npm:npm'


def test_malformed_ledger_lines_are_skipped(plan_context, monkeypatch, tmp_path) -> None:
    """A ledger with garbage lines around a valid entry still resolves fresh.

    ``read_entries`` tolerates and skips malformed JSONL lines, so a corrupt line
    must not turn a genuine fresh build into a query error.
    """
    plan_dir = plan_context.plan_dir_for('freshness-malformed')
    _write_status(plan_dir)
    _stub_worktree_sha(monkeypatch, _CURRENT_SHA)
    ledger_path = tmp_path / 'change-ledger.jsonl'
    valid = json.dumps(_build_entry(worktree_sha=_CURRENT_SHA), sort_keys=True)
    ledger_path.write_text(
        'not-json-at-all\n' + valid + '\n{ broken json\n', encoding='utf-8'
    )
    _stub_ledger_path(monkeypatch, ledger_path)

    result = cmd_pre_commit_verify_freshness(Namespace(plan_id='freshness-malformed'))

    assert result['status'] == 'fresh', result

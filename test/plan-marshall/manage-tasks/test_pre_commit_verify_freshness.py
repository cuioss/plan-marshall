#!/usr/bin/env python3
"""Tests for the ``pre-commit-verify-freshness`` subcommand of manage-tasks.

The subcommand answers a single deterministic question — "is the most recent
``plan-marshall:build-pyproject:pyproject_build run`` INFO line in
``script-execution.log`` newer than the most recent file-content mtime in the
worktree?" — and returns one of three statuses (``fresh``, ``stale``,
``undecidable``) for the orchestrator to consume as a fail-closed gate. See
``marketplace/bundles/plan-marshall/skills/manage-tasks/SKILL.md`` §
"Pre-Commit Verify Freshness" for the contract.

The mtime-candidate scope is now the live plan footprint, derived on demand via
``compute_plan_branch_diff`` rather than a seeded ``references.modified_files``
ledger. Tests stub ``_resolve_footprint`` to inject the footprint without
standing up a real git worktree; an empty footprint falls back to the
worktree-root walk exactly as the empty ledger did before.
"""

from __future__ import annotations

import importlib.util
import json
import os
from argparse import Namespace
from datetime import UTC, datetime
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


# =============================================================================
# Fixture builders
# =============================================================================


def _iso(dt: datetime) -> str:
    """Format a UTC datetime as the ISO-8601 string the log scanner expects."""
    return dt.strftime('%Y-%m-%dT%H:%M:%SZ')


def _write_build_log(
    plan_dir: Path,
    *,
    entries: list[tuple[datetime, str]] | None = None,
) -> Path:
    """Write a ``logs/script-execution.log`` file with the given entries.

    Each entry is a ``(timestamp, message)`` tuple. Timestamps are rendered in
    the canonical log format the freshness scanner expects:
    ``[<iso>] [INFO] [<6-char hex>] <message>``. A few non-matching lines are
    sprinkled in to prove the regex skips them.
    """
    logs_dir = plan_dir / 'logs'
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / 'script-execution.log'
    lines: list[str] = []
    if entries:
        for idx, (ts, msg) in enumerate(entries):
            stamp = _iso(ts)
            # 6-char hex hash placeholder (matches the production hash length).
            hash_id = f'{idx:06x}'
            lines.append(f'[{stamp}] [INFO] [{hash_id}] {msg}')
    # Sprinkle some non-matching entries to ensure the regex is strict.
    lines.append('[2026-01-01T00:00:00Z] [INFO] [abcdef] some-other-script run (1.00s)')
    lines.append('[2026-01-01T00:00:01Z] [ERROR] [bbbbbb] plan-marshall:build-pyproject:pyproject_build run (2.00s)')
    log_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return log_path


def _write_status(plan_dir: Path, *, worktree_path: str = '') -> Path:
    """Write a minimal ``status.json`` whose metadata.worktree_path is set.

    Empty ``worktree_path`` (the default) leaves the metadata absent so the
    command falls back to the current working directory.
    """
    status = {
        'plan_id': plan_dir.name,
        'metadata': {'worktree_path': worktree_path},
    }
    status_path = plan_dir / 'status.json'
    status_path.write_text(json.dumps(status), encoding='utf-8')
    return status_path


def _stub_footprint(monkeypatch, footprint: list[str]) -> None:
    """Patch the footprint resolver so no real git worktree is required."""
    monkeypatch.setattr(
        _freshness_mod, '_resolve_footprint', lambda plan_id, worktree_root: list(footprint)
    )


def _touch(path: Path, *, mtime: datetime) -> None:
    """Create a file (or update its mtime) at the given UTC timestamp."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('content', encoding='utf-8')
    epoch = mtime.replace(tzinfo=UTC).timestamp() if mtime.tzinfo is None else mtime.timestamp()
    os.utime(path, (epoch, epoch))


# =============================================================================
# Tests
# =============================================================================


def test_fresh_when_log_entry_post_dates_worktree(plan_context, monkeypatch) -> None:
    """status: fresh — most recent build entry newer than worktree mtime."""
    plan_dir = plan_context.plan_dir_for('freshness-fresh')

    worktree_root = plan_dir / 'worktree'
    worktree_root.mkdir()
    # Worktree file mtime: 2026-05-01
    _touch(worktree_root / 'src.py', mtime=datetime(2026, 5, 1, 12, 0, 0, tzinfo=UTC))

    _write_status(plan_dir, worktree_path=str(worktree_root))
    _stub_footprint(monkeypatch, ['src.py'])
    # Build log entry: 2026-05-02 (after worktree mtime).
    _write_build_log(
        plan_dir,
        entries=[
            (datetime(2026, 5, 2, 12, 0, 0, tzinfo=UTC), 'plan-marshall:build-pyproject:pyproject_build run (5.00s)'),
        ],
    )

    result = cmd_pre_commit_verify_freshness(Namespace(plan_id='freshness-fresh'))

    assert result['status'] == 'fresh', result
    assert result['plan_id'] == 'freshness-fresh'
    assert result['t_build_iso'] == '2026-05-02T12:00:00Z'
    assert result['t_worktree_iso'] == '2026-05-01T12:00:00Z'
    assert result['newest_mtime_path'].endswith('src.py')


def test_stale_when_footprint_file_post_dates_build_log(plan_context, monkeypatch) -> None:
    """status: stale — a footprint entry is newer than the most recent build."""
    plan_dir = plan_context.plan_dir_for('freshness-stale-footprint')

    worktree_root = plan_dir / 'worktree'
    worktree_root.mkdir()
    # File touched AFTER the build entry.
    _touch(worktree_root / 'changed.py', mtime=datetime(2026, 5, 5, 9, 0, 0, tzinfo=UTC))

    _write_status(plan_dir, worktree_path=str(worktree_root))
    _stub_footprint(monkeypatch, ['changed.py'])
    _write_build_log(
        plan_dir,
        entries=[
            (datetime(2026, 5, 4, 23, 0, 0, tzinfo=UTC), 'plan-marshall:build-pyproject:pyproject_build run (5.00s)'),
        ],
    )

    result = cmd_pre_commit_verify_freshness(Namespace(plan_id='freshness-stale-footprint'))

    assert result['status'] == 'stale', result
    assert result['t_build_iso'] == '2026-05-04T23:00:00Z'
    assert result['t_worktree_iso'] == '2026-05-05T09:00:00Z'
    assert result['newest_mtime_path'].endswith('changed.py')


def test_stale_via_worktree_root_fallback_when_footprint_empty(plan_context, monkeypatch) -> None:
    """status: stale — footprint empty; root walk finds a newer file."""
    plan_dir = plan_context.plan_dir_for('freshness-stale-fallback')

    worktree_root = plan_dir / 'worktree'
    worktree_root.mkdir()
    # Drop a recent file outside the footprint; the rglob fallback finds it.
    _touch(worktree_root / 'unlisted.txt', mtime=datetime(2026, 6, 1, 12, 0, 0, tzinfo=UTC))

    _write_status(plan_dir, worktree_path=str(worktree_root))
    # Empty footprint → triggers the worktree-root walk.
    _stub_footprint(monkeypatch, [])
    _write_build_log(
        plan_dir,
        entries=[
            (datetime(2026, 5, 1, 0, 0, 0, tzinfo=UTC), 'plan-marshall:build-pyproject:pyproject_build run (5.00s)'),
        ],
    )

    result = cmd_pre_commit_verify_freshness(Namespace(plan_id='freshness-stale-fallback'))

    assert result['status'] == 'stale', result
    assert result['t_build_iso'] == '2026-05-01T00:00:00Z'
    assert result['newest_mtime_path'].endswith('unlisted.txt')


def test_undecidable_when_no_build_log_entry(plan_context, monkeypatch) -> None:
    """status: undecidable / reason: no_build_log_entry — log has no match."""
    plan_dir = plan_context.plan_dir_for('freshness-undecidable-no-log')

    worktree_root = plan_dir / 'worktree'
    worktree_root.mkdir()
    _touch(worktree_root / 'src.py', mtime=datetime(2026, 5, 1, 12, 0, 0, tzinfo=UTC))

    _write_status(plan_dir, worktree_path=str(worktree_root))
    _stub_footprint(monkeypatch, ['src.py'])
    # No build entries — only the noise lines from _write_build_log.
    _write_build_log(plan_dir, entries=None)

    result = cmd_pre_commit_verify_freshness(Namespace(plan_id='freshness-undecidable-no-log'))

    assert result['status'] == 'undecidable', result
    assert result['reason'] == 'no_build_log_entry'
    assert 'log_path' in result


def test_undecidable_when_worktree_mtime_unresolvable(plan_context, monkeypatch) -> None:
    """status: undecidable / reason: worktree_mtime_unresolvable — empty tree."""
    plan_dir = plan_context.plan_dir_for('freshness-undecidable-empty-tree')

    # Worktree root exists but is empty (and the footprint is empty too).
    worktree_root = plan_dir / 'worktree'
    worktree_root.mkdir()

    _write_status(plan_dir, worktree_path=str(worktree_root))
    _stub_footprint(monkeypatch, [])
    _write_build_log(
        plan_dir,
        entries=[
            (datetime(2026, 5, 2, 12, 0, 0, tzinfo=UTC), 'plan-marshall:build-pyproject:pyproject_build run (5.00s)'),
        ],
    )

    result = cmd_pre_commit_verify_freshness(
        Namespace(plan_id='freshness-undecidable-empty-tree')
    )

    assert result['status'] == 'undecidable', result
    assert result['reason'] == 'worktree_mtime_unresolvable'
    assert result['t_build_iso'] == '2026-05-02T12:00:00Z'


def test_picks_newest_when_multiple_build_entries_present(plan_context, monkeypatch) -> None:
    """Ensures the scanner picks the latest matching INFO entry, not the first."""
    plan_dir = plan_context.plan_dir_for('freshness-newest-wins')

    worktree_root = plan_dir / 'worktree'
    worktree_root.mkdir()
    _touch(worktree_root / 'src.py', mtime=datetime(2026, 5, 1, 0, 0, 0, tzinfo=UTC))

    _write_status(plan_dir, worktree_path=str(worktree_root))
    _stub_footprint(monkeypatch, ['src.py'])
    _write_build_log(
        plan_dir,
        entries=[
            (datetime(2026, 5, 3, 12, 0, 0, tzinfo=UTC), 'plan-marshall:build-pyproject:pyproject_build run (5.00s)'),
            (datetime(2026, 5, 9, 12, 0, 0, tzinfo=UTC), 'plan-marshall:build-pyproject:pyproject_build run (5.00s)'),
            (datetime(2026, 5, 5, 12, 0, 0, tzinfo=UTC), 'plan-marshall:build-pyproject:pyproject_build run (5.00s)'),
        ],
    )

    result = cmd_pre_commit_verify_freshness(Namespace(plan_id='freshness-newest-wins'))

    assert result['status'] == 'fresh', result
    assert result['t_build_iso'] == '2026-05-09T12:00:00Z'


def test_no_exception_when_log_file_missing(plan_context, monkeypatch) -> None:
    """Degenerate case: no log file at all → undecidable, no exception."""
    plan_dir = plan_context.plan_dir_for('freshness-no-log-file')

    worktree_root = plan_dir / 'worktree'
    worktree_root.mkdir()
    _touch(worktree_root / 'src.py', mtime=datetime(2026, 5, 1, 0, 0, 0, tzinfo=UTC))

    _write_status(plan_dir, worktree_path=str(worktree_root))
    _stub_footprint(monkeypatch, ['src.py'])
    # No script-execution.log file written.

    result = cmd_pre_commit_verify_freshness(Namespace(plan_id='freshness-no-log-file'))

    assert result['status'] == 'undecidable', result
    assert result['reason'] == 'no_build_log_entry'

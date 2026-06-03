#!/usr/bin/env python3
"""Tests for integrate_into_main.py — the atomic finalize move-back script.

Contract under test (solution_outline.md §5):

* **Happy path** — ACQUIRES the merge lock, FOLDS the plan's own global logs into
  the plan dir, MOVES the plan dir back from the worktree to main, and RELEASES the
  lock. The executor is NOT regenerated — on-main executor regeneration is the
  project-level finalize-step-sync-plugin-cache step's responsibility (Deliverable 5).
* **Idempotent re-run** — an already-integrated plan (plan dir on main, none in the
  worktree) is a no-op success that never acquires the lock.
* **Rollback-on-partial-failure** — a move-back step that raises rolls the plan dir
  BACK into the worktree (authoritative copy never split) and releases the lock.
* **Lock released on every exit path** — including the rollback path.
* **cwd invariant** — the script never mutates the process cwd.
* **Worktree NOT removed** — the worktree directory survives the call.
* **Executor never touched** — integrate neither moves nor regenerates any
  ``.plan/execute-script.py``; the success payload carries no regen fields.

Isolation (test-isolation lessons 2026-06-02-12-001/002/003): every test runs
against an isolated tree staged under ``tmp_path`` with cwd pinned to a stable
location; the ``merge_lock`` delegation is stubbed so no real lock file is
contended — the suite never contends for the real ``.plan/`` under ``-n auto``.
"""

from __future__ import annotations

import importlib.util
import json
import os
from argparse import Namespace
from pathlib import Path

import pytest

from conftest import get_script_path

SCRIPT_PATH = get_script_path('plan-marshall', 'workflow-integration-git', 'integrate_into_main.py')

_spec = importlib.util.spec_from_file_location('integrate_into_main', SCRIPT_PATH)
assert _spec is not None and _spec.loader is not None
integrate_into_main = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(integrate_into_main)


# =============================================================================
# Fixtures
# =============================================================================


class _FakeMergeLock:
    """Stub merge_lock module recording acquire/release calls."""

    def __init__(self, acquire_status: str = 'success') -> None:
        self.acquire_status = acquire_status
        self.acquired = 0
        self.released = 0

    def run_acquire(self, args: Namespace) -> dict:
        self.acquired += 1
        if self.acquire_status != 'success':
            return {'status': 'error', 'error_code': 'TIMEOUT', 'plan_id': args.plan_id}
        return {'status': 'success', 'plan_id': args.plan_id, 'action': 'acquired'}

    def run_release(self, args: Namespace) -> dict:
        self.released += 1
        return {'status': 'success', 'plan_id': args.plan_id, 'action': 'released'}


@pytest.fixture
def isolated_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    """Stage an isolated main + worktree layout with the plan dir resident in the
    worktree (the move-in already ran).

    Layout::

        tmp_path/
          main/.plan/local/                       (main destination root)
          worktrees/{plan_id}/.plan/local/plans/{plan_id}/   (worktree-resident plan)
          worktrees/{plan_id}/.plan/local/logs/work.log      (plan's global logs)

    Pins cwd to ``main`` (the finalize move-back path) and monkeypatches the two
    resolvers (``get_plan_dir`` → main destination, ``get_worktree_root`` → the
    worktrees root) plus the ``merge_lock`` delegation. integrate no longer
    regenerates the executor, so there is no regen delegation to stub.
    """
    plan_id = 'sample-plan'

    main = tmp_path / 'main'
    main_plan_dir = main / '.plan' / 'local' / 'plans' / plan_id
    # main destination does NOT yet hold the plan dir (it is resident in the worktree)
    (main / '.plan' / 'local' / 'plans').mkdir(parents=True)

    worktrees_root = tmp_path / 'worktrees'
    worktree_path = worktrees_root / plan_id
    wt_plan_dir = worktree_path / '.plan' / 'local' / 'plans' / plan_id
    wt_plan_dir.mkdir(parents=True)
    (wt_plan_dir / 'status.json').write_text('{}\n')
    # references.json with NO marketplace script change by default.
    (wt_plan_dir / 'references.json').write_text(json.dumps({'modified_files': ['doc/foo.md']}))
    wt_global_logs = worktree_path / '.plan' / 'local' / 'logs'
    wt_global_logs.mkdir(parents=True)
    (wt_global_logs / 'work.log').write_text('[STATUS] hello\n')

    monkeypatch.chdir(main)

    monkeypatch.setattr(integrate_into_main, 'get_plan_dir', lambda pid: main / '.plan' / 'local' / 'plans' / pid)
    monkeypatch.setattr(integrate_into_main, 'get_worktree_root', lambda: worktrees_root)

    fake_lock = _FakeMergeLock()
    monkeypatch.setattr(integrate_into_main, '_load_merge_lock', lambda: fake_lock)

    return {
        'plan_id': plan_id,
        'main': main,
        'main_plan_dir': main_plan_dir,
        'worktree_path': worktree_path,
        'wt_plan_dir': wt_plan_dir,
        'wt_global_logs': wt_global_logs,
        'fake_lock': fake_lock,
    }


# =============================================================================
# Happy path
# =============================================================================


class TestIntegrateHappyPath:
    def test_moves_plan_dir_back_folds_logs_and_releases_lock(self, isolated_env: dict) -> None:
        env = isolated_env
        result = integrate_into_main.run_integrate_into_main(Namespace(plan_id=env['plan_id']))

        assert result['status'] == 'success', result
        assert result['action'] == 'integrated'

        # Plan dir is now resident on main as a real directory...
        assert env['main_plan_dir'].is_dir()
        assert not env['main_plan_dir'].is_symlink()
        assert (env['main_plan_dir'] / 'status.json').is_file()
        # ...and GONE from the worktree (moved, not copied).
        assert not env['wt_plan_dir'].exists()

        # The plan's global logs were folded into the plan dir's logs/.
        folded = env['main_plan_dir'] / 'logs' / 'work.log'
        assert folded.is_file()
        assert 'work.log' in result['folded_logs']

        # The lock was acquired AND released.
        assert env['fake_lock'].acquired == 1
        assert env['fake_lock'].released == 1

        # Deliverable 5: the success payload carries NO regen fields — integrate
        # no longer regenerates the executor.
        assert 'regenerated' not in result
        assert 'regen_detail' not in result

    def test_does_not_change_cwd(self, isolated_env: dict) -> None:
        env = isolated_env
        cwd_before = os.getcwd()
        integrate_into_main.run_integrate_into_main(Namespace(plan_id=env['plan_id']))
        assert os.getcwd() == cwd_before

    def test_does_not_remove_worktree(self, isolated_env: dict) -> None:
        env = isolated_env
        integrate_into_main.run_integrate_into_main(Namespace(plan_id=env['plan_id']))
        # The worktree directory itself survives — branch-cleanup owns removal.
        assert env['worktree_path'].is_dir()

    def test_executor_never_touched_by_integrate(self, isolated_env: dict) -> None:
        """Deliverable 5: integrate neither moves nor regenerates any executor.
        Stage both a main-resident executor and a worktree-bound one, and assert
        both are left byte-for-byte untouched across the move-back — integrate has
        no executor responsibility at all.
        """
        env = isolated_env
        # Stage a main-resident executor (it must stay present and unchanged)...
        main_executor = env['main'] / '.plan' / 'execute-script.py'
        main_executor.write_text('# main executor — must stay untouched\n')
        # ...and a worktree-bound one (it must NOT travel to main).
        wt_executor = env['worktree_path'] / '.plan' / 'execute-script.py'
        wt_executor.write_text('# worktree-bound executor — MUST NOT reach main\n')

        integrate_into_main.run_integrate_into_main(Namespace(plan_id=env['plan_id']))

        # Main's executor is present and byte-for-byte unchanged (never regenerated).
        assert main_executor.read_text() == '# main executor — must stay untouched\n'
        # The worktree-bound executor is left where it was (worktree removal handles it),
        # never file-moved onto a fresh main slot.
        assert wt_executor.is_file()


# =============================================================================
# Idempotent re-run
# =============================================================================


class TestIntegrateIdempotent:
    def test_rerun_is_noop_success_without_acquiring_lock(self, isolated_env: dict) -> None:
        env = isolated_env
        first = integrate_into_main.run_integrate_into_main(Namespace(plan_id=env['plan_id']))
        assert first['status'] == 'success'
        assert first['action'] == 'integrated'

        # A re-run observes the plan dir already on main (and gone from the worktree)
        # and short-circuits WITHOUT acquiring the lock.
        acquired_before = env['fake_lock'].acquired
        second = integrate_into_main.run_integrate_into_main(Namespace(plan_id=env['plan_id']))
        assert second['status'] == 'success'
        assert second['action'] == 'noop'
        assert env['fake_lock'].acquired == acquired_before  # no new acquire


# =============================================================================
# Rollback-on-partial-failure
# =============================================================================


class TestIntegrateRollback:
    def test_move_back_failure_rolls_back_to_worktree_and_releases_lock(
        self, isolated_env: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        env = isolated_env

        def boom(src: Path, dst: Path) -> None:
            raise OSError('simulated move-back failure')

        monkeypatch.setattr(integrate_into_main, '_move_back_dir', boom)

        result = integrate_into_main.run_integrate_into_main(Namespace(plan_id=env['plan_id']))

        assert result['status'] == 'error', result
        assert 'rolled back' in result['error']

        # Plan dir is still WHOLLY in the worktree (rolled back / never moved).
        assert env['wt_plan_dir'].is_dir()
        assert (env['wt_plan_dir'] / 'status.json').is_file()
        assert not env['main_plan_dir'].exists()

        # The lock was released even on the rollback path.
        assert env['fake_lock'].released == 1


# =============================================================================
# Lock acquisition failure
# =============================================================================


class TestIntegrateLockFailure:
    def test_acquire_failure_surfaces_and_never_moves_or_releases(
        self, isolated_env: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        env = isolated_env
        failing_lock = _FakeMergeLock(acquire_status='error')
        monkeypatch.setattr(integrate_into_main, '_load_merge_lock', lambda: failing_lock)

        result = integrate_into_main.run_integrate_into_main(Namespace(plan_id=env['plan_id']))

        assert result['status'] == 'error'
        # No move happened (plan dir still in worktree); no release (nothing held).
        assert env['wt_plan_dir'].is_dir()
        assert not env['main_plan_dir'].exists()
        assert failing_lock.acquired == 1
        assert failing_lock.released == 0


# =============================================================================
# Not-found / missing worktree-resident plan dir
# =============================================================================


class TestIntegrateNotFound:
    def test_missing_worktree_plan_dir_errors_without_acquiring_lock(
        self, isolated_env: dict
    ) -> None:
        env = isolated_env
        import shutil

        shutil.rmtree(env['wt_plan_dir'])

        result = integrate_into_main.run_integrate_into_main(Namespace(plan_id=env['plan_id']))
        assert result['status'] == 'error'
        assert result.get('error_code') == integrate_into_main.ErrorCode.NOT_FOUND
        # The lock was never acquired (idempotence/not-found guards run first).
        assert env['fake_lock'].acquired == 0


# =============================================================================
# CLI argparse plumbing
# =============================================================================


class TestIntegrateCli:
    def test_integrate_requires_plan_id(self) -> None:
        from conftest import run_script

        result = run_script(SCRIPT_PATH, 'integrate')
        assert result.returncode != 0
        assert '--plan-id' in result.stderr or '--plan-id' in result.stdout

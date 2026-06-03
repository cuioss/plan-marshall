#!/usr/bin/env python3
"""Tests for prepare_execute.py — the atomic phase-5 move-in script.

Contract under test (solution_outline.md §4):

* **Happy path** — materializes the worktree (delegated to ``cmd_worktree_create``),
  MOVES the plan dir (``.plan/local/plans/{plan_id}``) into the worktree-resident
  ``.plan/``, GENERATES a worktree-bound executor into the worktree, and returns
  the canonical ``worktree_path``. The executor is per-tree DERIVED state: main's
  ``.plan/execute-script.py`` is NOT moved — it stays present and untouched.
* **Idempotent re-run** — an already-moved-in plan is a no-op success returning the
  same path.
* **Rollback-on-partial-failure** — a move-in step that raises leaves the plan
  state WHOLLY on main (never half-moved) and returns ``status: error``.
* **cwd invariant** — the script never mutates the process cwd.

Isolation (test-isolation lessons 2026-06-02-12-001/002/003): every test runs
against an isolated ``PLAN_BASE_DIR`` staged under ``tmp_path`` with cwd pinned
to a stable location; ``cmd_worktree_create`` is stubbed so no real
``git worktree add`` runs and the suite never contends for the real ``.plan/``
under ``-n auto``.
"""

from __future__ import annotations

import importlib.util
import os
from argparse import Namespace
from pathlib import Path

import pytest

from conftest import get_script_path

SCRIPT_PATH = get_script_path('plan-marshall', 'workflow-integration-git', 'prepare_execute.py')

_spec = importlib.util.spec_from_file_location('prepare_execute', SCRIPT_PATH)
assert _spec is not None and _spec.loader is not None
prepare_execute = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(prepare_execute)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def isolated_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    """Stage an isolated main checkout + worktree-root layout under tmp_path.

    Layout::

        tmp_path/
          main/.plan/local/plans/{plan_id}/   (plan dir to move in)
          main/.plan/execute-script.py         (executor to move in)
          worktrees/                            (get_worktree_root() target)

    Pins cwd to ``main`` and monkeypatches the two resolvers
    (``get_plan_dir`` / ``get_worktree_root``) directly on the ``prepare_execute``
    module so they resolve against the isolated tree with the production path
    shapes. The main executor at ``.plan/execute-script.py`` is staged (it must
    STAY present — it is no longer moved). Stubs ``cmd_worktree_create`` to
    materialize the worktree ``.plan`` tree without a real ``git worktree add``,
    and stubs ``_generate_worktree_executor`` to simulate the worktree-bound
    executor generation without shelling out to the real generator.
    """
    plan_id = 'sample-plan'

    main = tmp_path / 'main'
    plan_dir = main / '.plan' / 'local' / 'plans' / plan_id
    plan_dir.mkdir(parents=True)
    (plan_dir / 'status.json').write_text('{}\n')
    executor = main / '.plan' / 'execute-script.py'
    executor.write_text('#!/usr/bin/env python3\n')

    worktrees_root = tmp_path / 'worktrees'
    worktrees_root.mkdir()

    # Pin cwd to main for the duration of the test.
    monkeypatch.chdir(main)

    # Resolve the main-checkout sources and the worktree root against the
    # isolated tree with production path shapes — no PLAN_BASE_DIR coupling
    # (which would place the executor under .plan/local).
    monkeypatch.setattr(prepare_execute, 'get_plan_dir', lambda pid: main / '.plan' / 'local' / 'plans' / pid)
    monkeypatch.setattr(prepare_execute, 'get_worktree_root', lambda: worktrees_root)

    # Stub the worktree-bound executor generation. The real helper shells out to
    # generate_executor.py (marketplace discovery + write to the cwd-resolved
    # tracked-config dir). Simulate a clean generation by writing the worktree
    # executor file directly, so the test asserts prepare_execute's contract
    # (main executor untouched, worktree executor produced) without invoking the
    # real subprocess or coupling to PLAN_BASE_DIR resolution.
    def fake_generate(worktree_path: Path) -> tuple[bool, str]:
        wt_exec = worktree_path / '.plan' / 'execute-script.py'
        wt_exec.parent.mkdir(parents=True, exist_ok=True)
        wt_exec.write_text('#!/usr/bin/env python3\n# worktree-bound\n')
        return True, f'worktree executor generated at {wt_exec}'

    monkeypatch.setattr(prepare_execute, '_generate_worktree_executor', fake_generate)

    def fake_worktree_create(args: Namespace) -> dict:
        # Mimic the post-fix worktree-create contract: materialize a REAL
        # .plan/local directory and create NO symlinks and NO plans/ subdir —
        # the move-in step lands the real plans/{plan_id} directory.
        target = worktrees_root / args.plan_id
        (target / '.plan' / 'local').mkdir(parents=True, exist_ok=True)
        return {
            'status': 'success',
            'plan_id': args.plan_id,
            'worktree_path': str(target),
            'branch': args.branch,
        }

    fake_module = type('M', (), {'cmd_worktree_create': staticmethod(fake_worktree_create)})()
    monkeypatch.setattr(prepare_execute, '_load_git_workflow', lambda: fake_module)

    return {
        'plan_id': plan_id,
        'main': main,
        'plan_dir': plan_dir,
        'executor': executor,
        'worktrees_root': worktrees_root,
        'worktree_path': worktrees_root / plan_id,
    }


# =============================================================================
# Happy path
# =============================================================================


class TestPrepareExecuteHappyPath:
    def test_moves_plan_dir_keeps_main_executor_generates_worktree_executor(
        self, isolated_env: dict
    ) -> None:
        env = isolated_env
        result = prepare_execute.run_prepare_execute(
            Namespace(plan_id=env['plan_id'], branch='feature/sample-plan', base=None)
        )

        assert result['status'] == 'success', result
        assert result['action'] == 'moved'
        assert result['worktree_path'] == str(env['worktree_path'])

        # The plan dir is now resident in the worktree as a real directory...
        wt_plan_dir = env['worktree_path'] / '.plan' / 'local' / 'plans' / env['plan_id']
        assert wt_plan_dir.is_dir()
        assert not wt_plan_dir.is_symlink()
        assert (wt_plan_dir / 'status.json').is_file()

        # ...and the plan dir is GONE from main (moved, not copied).
        assert not env['plan_dir'].exists()

        # FIX 1: main's executor is NOT moved — it stays present and untouched.
        assert env['executor'].is_file()
        assert not env['executor'].is_symlink()

        # The worktree got its OWN generated executor (per-tree derived state).
        assert result['worktree_executor_generated'] is True
        assert 'executor_detail' in result
        wt_exec = env['worktree_path'] / '.plan' / 'execute-script.py'
        assert wt_exec.is_file()
        assert not wt_exec.is_symlink()

        # The payload reports ONLY the plan dir as moved — the executor is no
        # longer part of the move-in slot set.
        assert result['moved_in[1]'] == [str(wt_plan_dir)]
        assert 'moved_in[2]' not in result

        # No-symlink contract: NOTHING under the worktree .plan/local is a
        # symlink — the move-based model owns a fully real .plan/local.
        wt_plan_local = env['worktree_path'] / '.plan' / 'local'
        assert wt_plan_local.is_dir() and not wt_plan_local.is_symlink()
        for entry in wt_plan_local.rglob('*'):
            assert not entry.is_symlink(), f'unexpected symlink under worktree .plan/local: {entry}'

    def test_rejects_symlinked_plan_local(
        self, isolated_env: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # A symlinked worktree .plan/local is rejected before any move-in: the
        # move-based model requires a real directory. Pre-materialize the
        # worktree with .plan/local as a symlink back to main.
        env = isolated_env

        def symlink_worktree_create(args: Namespace) -> dict:
            target = env['worktrees_root'] / args.plan_id
            (target / '.plan').mkdir(parents=True, exist_ok=True)
            (target / '.plan' / 'local').symlink_to(
                env['main'] / '.plan' / 'local', target_is_directory=True
            )
            return {'status': 'success', 'plan_id': args.plan_id, 'worktree_path': str(target)}

        fake_module = type('M', (), {'cmd_worktree_create': staticmethod(symlink_worktree_create)})()
        monkeypatch.setattr(prepare_execute, '_load_git_workflow', lambda: fake_module)

        result = prepare_execute.run_prepare_execute(
            Namespace(plan_id=env['plan_id'], branch='feature/sample-plan', base=None)
        )

        assert result['status'] == 'error'
        assert result.get('error_code') == prepare_execute.ErrorCode.INVALID_INPUT
        # The plan dir stays WHOLLY on main — no move happened.
        assert env['plan_dir'].exists()

    def test_does_not_change_cwd(self, isolated_env: dict) -> None:
        env = isolated_env
        cwd_before = os.getcwd()
        prepare_execute.run_prepare_execute(
            Namespace(plan_id=env['plan_id'], branch='feature/sample-plan', base=None)
        )
        assert os.getcwd() == cwd_before

    def test_cwd_invariant_self_check_restores_and_errors(
        self, isolated_env: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """If an inner step mutates the process cwd, the ``_assert_cwd_unchanged``
        self-check restores it and surfaces an INVALID_INPUT error rather than
        returning a success that silently leaked a cwd change."""
        env = isolated_env
        cwd_before = os.getcwd()

        # Make the worktree-create delegation mutate cwd as a side effect, the
        # exact bug the defensive self-check exists to catch.
        elsewhere = env['worktrees_root']

        def cwd_mutating_create(args: Namespace) -> dict:
            target = elsewhere / args.plan_id
            (target / '.plan' / 'local' / 'plans').mkdir(parents=True, exist_ok=True)
            os.chdir(elsewhere)  # invariant violation injected here
            return {'status': 'success', 'plan_id': args.plan_id, 'worktree_path': str(target)}

        fake_module = type('M', (), {'cmd_worktree_create': staticmethod(cwd_mutating_create)})()
        monkeypatch.setattr(prepare_execute, '_load_git_workflow', lambda: fake_module)

        result = prepare_execute.run_prepare_execute(
            Namespace(plan_id=env['plan_id'], branch='feature/sample-plan', base=None)
        )

        # The self-check restored cwd before returning...
        assert os.getcwd() == cwd_before
        # ...and reported the invariant violation as an error.
        assert result['status'] == 'error'
        assert result.get('error_code') == prepare_execute.ErrorCode.INVALID_INPUT


# =============================================================================
# Idempotent re-run
# =============================================================================


class TestPrepareExecuteIdempotent:
    def test_rerun_is_noop_success_returning_same_path(self, isolated_env: dict) -> None:
        env = isolated_env
        first = prepare_execute.run_prepare_execute(
            Namespace(plan_id=env['plan_id'], branch='feature/sample-plan', base=None)
        )
        assert first['status'] == 'success'
        assert first['action'] == 'moved'

        # A re-run observes the already-resident plan dir and short-circuits.
        second = prepare_execute.run_prepare_execute(
            Namespace(plan_id=env['plan_id'], branch='feature/sample-plan', base=None)
        )
        assert second['status'] == 'success'
        assert second['action'] == 'noop'
        assert second['worktree_path'] == first['worktree_path']


# =============================================================================
# Rollback-on-partial-failure
# =============================================================================


class TestPrepareExecuteRollback:
    def test_move_failure_leaves_plan_state_wholly_on_main(
        self, isolated_env: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When the (sole) plan-dir move raises, the script returns ``status:
        error`` and the plan state ends up WHOLLY on main — never half-moved.
        With the executor removed from the slot set the plan dir is the only
        move-in slot, so a failure leaves it untouched on main."""
        env = isolated_env

        def failing_move(src: Path, dst: Path) -> None:
            raise OSError('simulated move failure on plan-dir slot')

        monkeypatch.setattr(prepare_execute, '_move_in_slot', failing_move)

        result = prepare_execute.run_prepare_execute(
            Namespace(plan_id=env['plan_id'], branch='feature/sample-plan', base=None)
        )

        assert result['status'] == 'error', result
        assert 'rolled back' in result['error']

        # Plan dir stays WHOLLY on main, not stranded in the worktree.
        assert env['plan_dir'].is_dir()
        assert (env['plan_dir'] / 'status.json').is_file()
        wt_plan_dir = env['worktree_path'] / '.plan' / 'local' / 'plans' / env['plan_id']
        assert not (wt_plan_dir.exists() and not wt_plan_dir.is_symlink())

        # Main's executor is never touched on the failure path either.
        assert env['executor'].is_file()

    def test_missing_plan_dir_on_main_errors_without_moving(
        self, isolated_env: dict
    ) -> None:
        """When the plan dir is absent on main, the script fails loud (NOT_FOUND)
        rather than materializing an empty slot."""
        env = isolated_env
        # Remove the plan dir so the pre-flight guard fires.
        import shutil

        shutil.rmtree(env['plan_dir'])

        result = prepare_execute.run_prepare_execute(
            Namespace(plan_id=env['plan_id'], branch='feature/sample-plan', base=None)
        )
        assert result['status'] == 'error'
        assert result.get('error_code') == prepare_execute.ErrorCode.NOT_FOUND


# =============================================================================
# Input validation
# =============================================================================


class TestPrepareExecuteInputValidation:
    def test_first_run_without_branch_is_rejected(self, isolated_env: dict) -> None:
        """The worktree is not yet materialized and no --branch is supplied →
        INVALID_INPUT (cannot create the feature branch)."""
        env = isolated_env
        result = prepare_execute.run_prepare_execute(
            Namespace(plan_id=env['plan_id'], branch=None, base=None)
        )
        assert result['status'] == 'error'
        assert result.get('error_code') == prepare_execute.ErrorCode.INVALID_INPUT
        # No move happened: plan dir still on main.
        assert env['plan_dir'].is_dir()


# =============================================================================
# CLI argparse plumbing
# =============================================================================


class TestPrepareExecuteCli:
    def test_prepare_requires_plan_id(self) -> None:
        from conftest import run_script

        result = run_script(SCRIPT_PATH, 'prepare')
        assert result.returncode != 0
        assert '--plan-id' in result.stderr or '--plan-id' in result.stdout

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

# Capture the REAL _generate_worktree_executor before any fixture monkeypatches
# it away. The function-level post-assertion / copy-from-main tests exercise THIS
# real implementation (the behavior under test IS the post-assert/fallback logic),
# not the isolated_env fixture's fake_generate stub that the run_prepare_execute
# integration tests rely on.
_REAL_GENERATE_WORKTREE_EXECUTOR = prepare_execute._generate_worktree_executor


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
    def fake_generate(worktree_path: Path, plan_id: str) -> tuple[bool, str]:
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
# Worktree-executor production: on-disk post-assertion + copy-from-main fallback
# =============================================================================
#
# These tests exercise the REAL _generate_worktree_executor / _copy_main_executor
# logic (NOT the fixture's fake_generate stub) — the behavior under test IS the
# post-assertion and fallback itself. The generator subprocess is neutralized by
# pointing _GENERATE_EXECUTOR_PATH at an absent file (generation unavailable) or
# by stubbing subprocess.run to simulate the "exited 0, wrote nothing" condition.


class TestExecutorLanded:
    """Direct unit coverage of the on-disk landing predicate (FIX 1 primitive).

    ``_executor_landed`` is the single source of the "did the file actually
    arrive on disk?" verdict that the post-assertion (behavior 1) and the
    false-positive prevention (behavior 3) both depend on. Exercising it in
    isolation pins each branch — absent, present-but-empty, present-non-empty,
    a directory in the leaf position, and the OSError swallow path.
    """

    def test_absent_file_is_not_landed(self, tmp_path: Path) -> None:
        assert prepare_execute._executor_landed(tmp_path / 'nope.py') is False

    def test_empty_file_is_not_landed(self, tmp_path: Path) -> None:
        empty = tmp_path / 'execute-script.py'
        empty.write_text('')
        assert prepare_execute._executor_landed(empty) is False

    def test_non_empty_file_is_landed(self, tmp_path: Path) -> None:
        real = tmp_path / 'execute-script.py'
        real.write_text('#!/usr/bin/env python3\n')
        assert prepare_execute._executor_landed(real) is True

    def test_directory_in_leaf_position_is_not_landed(self, tmp_path: Path) -> None:
        # A directory where the executor file is expected must not be claimed as
        # landed — is_file() is False for a directory.
        as_dir = tmp_path / 'execute-script.py'
        as_dir.mkdir()
        assert prepare_execute._executor_landed(as_dir) is False

    def test_oserror_during_stat_is_swallowed_as_not_landed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # If stat() raises (e.g. a permission / race error), the predicate must
        # return False rather than propagating — it is a best-effort on-disk read.
        target = tmp_path / 'execute-script.py'
        target.write_text('#!/usr/bin/env python3\n')

        def boom(self: Path) -> bool:
            raise OSError('simulated stat failure')

        monkeypatch.setattr(Path, 'is_file', boom)
        assert prepare_execute._executor_landed(target) is False


class TestMainExecutorPathResolution:
    """Coverage of the copy-from-main source resolver (behavior 2 primitive)."""

    def test_returns_none_when_plan_dir_resolution_raises(
        self, isolated_env: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # get_plan_dir raising RuntimeError → no main executor locatable.
        env = isolated_env

        def raising_plan_dir(pid: str) -> Path:
            raise RuntimeError('cannot resolve plan dir')

        monkeypatch.setattr(prepare_execute, 'get_plan_dir', raising_plan_dir)
        assert prepare_execute._main_executor_path(env['plan_id']) is None

    def test_resolves_plan_ancestor_dot_plan_execute_script(
        self, isolated_env: dict
    ) -> None:
        # The resolver walks up from the main plan dir to the .plan ancestor and
        # appends execute-script.py — pointing at main's real executor.
        env = isolated_env
        resolved = prepare_execute._main_executor_path(env['plan_id'])
        assert resolved is not None
        assert resolved == env['main'] / '.plan' / 'execute-script.py'


class TestCopyMainExecutor:
    """Direct coverage of the copy-from-main fallback helper (behavior 2)."""

    def test_returns_false_when_no_main_executor_available(
        self, isolated_env: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Main executor absent → the helper reports the absence, copies nothing.
        env = isolated_env
        worktree_path = env['worktree_path']
        (worktree_path / '.plan').mkdir(parents=True, exist_ok=True)

        empty_main = env['main'] / 'empty'
        (empty_main / '.plan' / 'local' / 'plans' / env['plan_id']).mkdir(parents=True)
        monkeypatch.setattr(
            prepare_execute,
            'get_plan_dir',
            lambda pid: empty_main / '.plan' / 'local' / 'plans' / pid,
        )

        copied, detail = prepare_execute._copy_main_executor(worktree_path, env['plan_id'])
        assert copied is False
        assert 'no main executor available' in detail
        assert not (worktree_path / '.plan' / 'execute-script.py').exists()

    def test_returns_false_when_main_executor_is_empty(
        self, isolated_env: dict
    ) -> None:
        # An empty main executor is treated as "not available" — _executor_landed
        # rejects zero-byte sources, so the copy never claims an empty source.
        env = isolated_env
        worktree_path = env['worktree_path']
        (worktree_path / '.plan').mkdir(parents=True, exist_ok=True)
        env['executor'].write_text('')  # zero-byte main executor

        copied, detail = prepare_execute._copy_main_executor(worktree_path, env['plan_id'])
        assert copied is False
        assert 'no main executor available' in detail

    def test_returns_false_when_copyfile_raises_oserror(
        self, isolated_env: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # A copyfile OSError is reported as a non-fatal failure, never raised.
        env = isolated_env
        worktree_path = env['worktree_path']
        (worktree_path / '.plan').mkdir(parents=True, exist_ok=True)
        env['executor'].write_text('#!/usr/bin/env python3\n# MAIN\n')

        def failing_copy(src: str, dst: str) -> None:
            raise OSError('simulated copyfile failure')

        monkeypatch.setattr(prepare_execute.shutil, 'copyfile', failing_copy)

        copied, detail = prepare_execute._copy_main_executor(worktree_path, env['plan_id'])
        assert copied is False
        assert 'copy-from-main failed' in detail

    def test_successful_copy_is_byte_equivalent_and_reports_mechanism(
        self, isolated_env: dict
    ) -> None:
        env = isolated_env
        worktree_path = env['worktree_path']
        (worktree_path / '.plan').mkdir(parents=True, exist_ok=True)
        main_content = '#!/usr/bin/env python3\n# distinctive MAIN bytes\n'
        env['executor'].write_text(main_content)

        copied, detail = prepare_execute._copy_main_executor(worktree_path, env['plan_id'])
        assert copied is True
        assert 'copied from main' in detail
        wt_exec = worktree_path / '.plan' / 'execute-script.py'
        assert wt_exec.read_text() == main_content


class TestGenerateWorktreeExecutorSuccessAndFailurePaths:
    """The real generation-mechanism branches not covered by the post-assertion
    class: success-via-generation, launch-OSError → copy, and both-fail.
    """

    def test_generation_landing_real_file_reports_generated_mechanism(
        self, isolated_env: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """FIX 1 happy branch: generation exits 0 AND lands a non-empty file →
        ``(True, 'worktree executor generated ...')`` from the generation path,
        NOT the copy fallback."""
        env = isolated_env
        worktree_path = env['worktree_path']
        wt_exec = worktree_path / '.plan' / 'execute-script.py'
        wt_exec.parent.mkdir(parents=True, exist_ok=True)

        monkeypatch.setattr(prepare_execute, '_GENERATE_EXECUTOR_PATH', env['main'] / 'fake_gen.py')
        (env['main'] / 'fake_gen.py').write_text('# stub generator\n')

        class _Result:
            returncode = 0
            stdout = ''
            stderr = ''

        def gen_that_writes(*a: object, **k: object) -> object:
            # Simulate a generator that actually lands a non-empty executor.
            wt_exec.write_text('#!/usr/bin/env python3\n# generated\n')
            return _Result()

        monkeypatch.setattr(prepare_execute.subprocess, 'run', gen_that_writes)

        produced, detail = _REAL_GENERATE_WORKTREE_EXECUTOR(worktree_path, env['plan_id'])
        assert produced is True, detail
        assert 'generated at' in detail
        assert 'copied from main' not in detail

    def test_generation_launch_oserror_falls_back_to_copy(
        self, isolated_env: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """subprocess.run raising OSError (generator cannot launch) routes to the
        copy-from-main fallback rather than propagating."""
        env = isolated_env
        worktree_path = env['worktree_path']
        (worktree_path / '.plan').mkdir(parents=True, exist_ok=True)
        env['executor'].write_text('#!/usr/bin/env python3\n# MAIN\n')

        monkeypatch.setattr(prepare_execute, '_GENERATE_EXECUTOR_PATH', env['main'] / 'fake_gen.py')
        (env['main'] / 'fake_gen.py').write_text('# stub generator\n')

        def launch_failure(*a: object, **k: object) -> object:
            raise OSError('cannot exec generator')

        monkeypatch.setattr(prepare_execute.subprocess, 'run', launch_failure)

        produced, detail = _REAL_GENERATE_WORKTREE_EXECUTOR(worktree_path, env['plan_id'])
        assert produced is True, detail
        assert 'copied from main' in detail
        assert (worktree_path / '.plan' / 'execute-script.py').is_file()

    def test_both_generation_and_copy_fail_reports_combined_detail(
        self, isolated_env: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When generation exits 0 wrote-nothing AND no main executor exists, the
        combined ``(False, '{launch_detail}; {copy_detail}')`` is returned — both
        failure reasons surfaced for the operator."""
        env = isolated_env
        worktree_path = env['worktree_path']
        (worktree_path / '.plan').mkdir(parents=True, exist_ok=True)

        monkeypatch.setattr(prepare_execute, '_GENERATE_EXECUTOR_PATH', env['main'] / 'fake_gen.py')
        (env['main'] / 'fake_gen.py').write_text('# stub generator\n')

        class _Result:
            returncode = 0
            stdout = ''
            stderr = ''

        monkeypatch.setattr(prepare_execute.subprocess, 'run', lambda *a, **k: _Result())

        empty_main = env['main'] / 'empty'
        (empty_main / '.plan' / 'local' / 'plans' / env['plan_id']).mkdir(parents=True)
        monkeypatch.setattr(
            prepare_execute,
            'get_plan_dir',
            lambda pid: empty_main / '.plan' / 'local' / 'plans' / pid,
        )

        produced, detail = _REAL_GENERATE_WORKTREE_EXECUTOR(worktree_path, env['plan_id'])
        assert produced is False
        # Both halves of the combined detail are present.
        assert 'no file landed' in detail
        assert 'no main executor available' in detail

    def test_generator_absent_with_no_main_executor_reports_both(
        self, isolated_env: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Generator missing AND no main executor → ``(False, 'generator not
        found ...; {copy_detail}')`` — the generator-absent branch combined with
        an unavailable copy source."""
        env = isolated_env
        worktree_path = env['worktree_path']
        (worktree_path / '.plan').mkdir(parents=True, exist_ok=True)

        monkeypatch.setattr(
            prepare_execute, '_GENERATE_EXECUTOR_PATH', env['main'] / 'nonexistent_gen.py'
        )

        empty_main = env['main'] / 'empty'
        (empty_main / '.plan' / 'local' / 'plans' / env['plan_id']).mkdir(parents=True)
        monkeypatch.setattr(
            prepare_execute,
            'get_plan_dir',
            lambda pid: empty_main / '.plan' / 'local' / 'plans' / pid,
        )

        produced, detail = _REAL_GENERATE_WORKTREE_EXECUTOR(worktree_path, env['plan_id'])
        assert produced is False
        assert 'generator not found' in detail
        assert 'no main executor available' in detail


class TestGenerateWorktreeExecutorPostAssertion:
    def test_returns_false_when_gen_exits_zero_no_file_and_no_main_executor(
        self, isolated_env: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """FIX 1 + false-positive prevention: a returncode==0 generation that
        wrote nothing AND no main executor to copy yields ``(False, ...)`` — the
        absent file is never reported as generated."""
        env = isolated_env
        worktree_path = env['worktree_path']
        (worktree_path / '.plan').mkdir(parents=True, exist_ok=True)

        # Generator exists and exits 0 but writes no executor file.
        monkeypatch.setattr(prepare_execute, '_GENERATE_EXECUTOR_PATH', env['main'] / 'fake_gen.py')
        (env['main'] / 'fake_gen.py').write_text('# stub generator\n')

        class _Result:
            returncode = 0
            stdout = ''
            stderr = ''

        monkeypatch.setattr(prepare_execute.subprocess, 'run', lambda *a, **k: _Result())

        # No main executor available to copy from: point get_plan_dir at a tree
        # whose .plan has no execute-script.py.
        empty_main = env['main'] / 'empty'
        (empty_main / '.plan' / 'local' / 'plans' / env['plan_id']).mkdir(parents=True)
        monkeypatch.setattr(
            prepare_execute,
            'get_plan_dir',
            lambda pid: empty_main / '.plan' / 'local' / 'plans' / pid,
        )

        produced, detail = _REAL_GENERATE_WORKTREE_EXECUTOR(
            worktree_path, env['plan_id']
        )

        assert produced is False, detail
        # The worktree executor genuinely does not exist on disk.
        assert not (worktree_path / '.plan' / 'execute-script.py').exists()

    def test_returns_false_when_gen_exits_zero_but_writes_empty_file(
        self, isolated_env: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An empty (zero-byte) executor is treated as not-landed — exists() is
        not sufficient, the file must be non-empty."""
        env = isolated_env
        worktree_path = env['worktree_path']
        wt_exec = worktree_path / '.plan' / 'execute-script.py'
        wt_exec.parent.mkdir(parents=True, exist_ok=True)
        wt_exec.write_text('')  # zero-byte: landed-but-empty

        monkeypatch.setattr(prepare_execute, '_GENERATE_EXECUTOR_PATH', env['main'] / 'fake_gen.py')
        (env['main'] / 'fake_gen.py').write_text('# stub generator\n')

        class _Result:
            returncode = 0
            stdout = ''
            stderr = ''

        monkeypatch.setattr(prepare_execute.subprocess, 'run', lambda *a, **k: _Result())

        # No main executor to copy → the empty worktree file must not be claimed.
        empty_main = env['main'] / 'empty'
        (empty_main / '.plan' / 'local' / 'plans' / env['plan_id']).mkdir(parents=True)
        monkeypatch.setattr(
            prepare_execute,
            'get_plan_dir',
            lambda pid: empty_main / '.plan' / 'local' / 'plans' / pid,
        )

        produced, detail = _REAL_GENERATE_WORKTREE_EXECUTOR(
            worktree_path, env['plan_id']
        )

        assert produced is False, detail

    def test_copy_from_main_fallback_produces_byte_equivalent_executor(
        self, isolated_env: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """FIX 2: when generation cannot land but main's executor exists, the
        fallback copies it verbatim and returns ``(True, ...)`` with a detail
        naming the copy mechanism. The copy is byte-equivalent to main."""
        env = isolated_env
        worktree_path = env['worktree_path']
        (worktree_path / '.plan').mkdir(parents=True, exist_ok=True)

        # Give main's executor distinctive content so byte-equivalence is checkable.
        main_content = '#!/usr/bin/env python3\n# MAIN executor mappings\n'
        env['executor'].write_text(main_content)

        # Generation unavailable: point _GENERATE_EXECUTOR_PATH at an absent file.
        monkeypatch.setattr(
            prepare_execute, '_GENERATE_EXECUTOR_PATH', env['main'] / 'nonexistent_gen.py'
        )

        produced, detail = _REAL_GENERATE_WORKTREE_EXECUTOR(
            worktree_path, env['plan_id']
        )

        assert produced is True, detail
        assert 'copied from main' in detail
        wt_exec = worktree_path / '.plan' / 'execute-script.py'
        assert wt_exec.is_file()
        assert wt_exec.read_text() == main_content

    def test_falls_back_to_copy_when_gen_exits_nonzero(
        self, isolated_env: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A non-zero generation exit also routes to the copy-from-main fallback
        (recoverable when main's executor exists)."""
        env = isolated_env
        worktree_path = env['worktree_path']
        (worktree_path / '.plan').mkdir(parents=True, exist_ok=True)
        env['executor'].write_text('#!/usr/bin/env python3\n# MAIN\n')

        monkeypatch.setattr(prepare_execute, '_GENERATE_EXECUTOR_PATH', env['main'] / 'fake_gen.py')
        (env['main'] / 'fake_gen.py').write_text('# stub generator\n')

        class _Result:
            returncode = 1
            stdout = ''
            stderr = 'boom: marketplace anchor unavailable\n'

        monkeypatch.setattr(prepare_execute.subprocess, 'run', lambda *a, **k: _Result())

        produced, detail = _REAL_GENERATE_WORKTREE_EXECUTOR(
            worktree_path, env['plan_id']
        )

        assert produced is True, detail
        assert 'copied from main' in detail
        assert (worktree_path / '.plan' / 'execute-script.py').is_file()


# =============================================================================
# Self-heal on re-run (FIX 3)
# =============================================================================


class TestPrepareExecuteSelfHeal:
    def test_rerun_with_missing_executor_heals_returning_same_path(
        self, isolated_env: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A partial materialization (plan dir already moved in, worktree
        executor absent) self-heals on re-run: the executor is regenerated/copied
        and the call returns success carrying the same worktree_path with
        action=healed — never a bare noop, never a re-attempted worktree add."""
        env = isolated_env
        # First run: full move-in with the stubbed generation.
        first = prepare_execute.run_prepare_execute(
            Namespace(plan_id=env['plan_id'], branch='feature/sample-plan', base=None)
        )
        assert first['status'] == 'success'
        assert first['action'] == 'moved'

        # Simulate the original-defect partial state: delete the worktree executor.
        wt_exec = env['worktree_path'] / '.plan' / 'execute-script.py'
        wt_exec.unlink()
        assert not wt_exec.exists()

        # Restore the REAL generation path so the heal exercises real logic with
        # the copy-from-main fallback (generation unavailable → copy main's).
        monkeypatch.setattr(
            prepare_execute, '_GENERATE_EXECUTOR_PATH', env['main'] / 'nonexistent_gen.py'
        )

        # Re-run in the partial state.
        second = prepare_execute.run_prepare_execute(
            Namespace(plan_id=env['plan_id'], branch='feature/sample-plan', base=None)
        )

        assert second['status'] == 'success', second
        assert second['action'] == 'healed'
        assert second['worktree_path'] == first['worktree_path']
        assert second['worktree_executor_generated'] is True
        # The executor is back on disk (copied from main).
        assert wt_exec.is_file()
        assert wt_exec.stat().st_size > 0

    def test_rerun_with_present_executor_is_plain_noop(self, isolated_env: dict) -> None:
        """When the executor is already present on re-run, the short-circuit is a
        plain noop (no heal, no regeneration) — false-positive prevention in the
        opposite direction: the heal must NOT fire when nothing is missing."""
        env = isolated_env
        first = prepare_execute.run_prepare_execute(
            Namespace(plan_id=env['plan_id'], branch='feature/sample-plan', base=None)
        )
        assert first['action'] == 'moved'

        second = prepare_execute.run_prepare_execute(
            Namespace(plan_id=env['plan_id'], branch='feature/sample-plan', base=None)
        )
        assert second['status'] == 'success'
        assert second['action'] == 'noop'
        assert 'worktree_executor_generated' not in second

    def test_heal_reports_failure_honestly_when_gen_and_copy_both_fail(
        self, isolated_env: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Self-heal that cannot produce the executor (generation unavailable AND
        no main executor to copy) still returns ``action: healed`` and
        ``status: success`` — the move is preserved — but reports the heal
        attempt honestly via ``worktree_executor_generated: False`` rather than a
        false-positive ``True``."""
        env = isolated_env
        first = prepare_execute.run_prepare_execute(
            Namespace(plan_id=env['plan_id'], branch='feature/sample-plan', base=None)
        )
        assert first['action'] == 'moved'

        # Partial-state: delete the worktree executor.
        wt_exec = env['worktree_path'] / '.plan' / 'execute-script.py'
        wt_exec.unlink()

        # Restore the REAL generation path so the heal exercises real logic. The
        # isolated_env fixture stubs _generate_worktree_executor with
        # fake_generate (which always reports success and writes a file); without
        # restoring the real function the generator-absent + no-main-executor
        # failure this test asserts can never occur. Mirrors the restore in
        # test_rerun_with_missing_executor_heals_returning_same_path.
        monkeypatch.setattr(
            prepare_execute, '_generate_worktree_executor', _REAL_GENERATE_WORKTREE_EXECUTOR
        )
        # Make BOTH heal mechanisms fail: generator absent + main executor gone.
        monkeypatch.setattr(
            prepare_execute, '_GENERATE_EXECUTOR_PATH', env['main'] / 'nonexistent_gen.py'
        )
        env['executor'].unlink()  # remove main's executor → no copy source

        second = prepare_execute.run_prepare_execute(
            Namespace(plan_id=env['plan_id'], branch='feature/sample-plan', base=None)
        )

        # The move is preserved and the call still succeeds (non-fatal contract)...
        assert second['status'] == 'success', second
        assert second['action'] == 'healed'
        assert second['worktree_path'] == first['worktree_path']
        # ...but the heal honestly reports it could not produce the executor.
        assert second['worktree_executor_generated'] is False
        assert not wt_exec.exists()


# =============================================================================
# Non-fatal generation contract at the run_prepare_execute integration level
# =============================================================================
#
# Behavior 3 (false-positive prevention) at the integration boundary: a failed
# worktree-executor production on the FRESH move-in path must NOT roll back the
# completed plan-dir move. The move-in succeeds; the failed generation is
# reported faithfully in the payload, never masked and never fatal.


class TestPrepareExecuteNonFatalGeneration:
    def test_fresh_move_reports_failed_generation_without_rollback(
        self, isolated_env: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        env = isolated_env

        # Restore the REAL generation path, then make BOTH mechanisms fail:
        # generator absent and no main executor to copy from.
        monkeypatch.setattr(
            prepare_execute, '_generate_worktree_executor', _REAL_GENERATE_WORKTREE_EXECUTOR
        )
        monkeypatch.setattr(
            prepare_execute, '_GENERATE_EXECUTOR_PATH', env['main'] / 'nonexistent_gen.py'
        )
        # Point get_plan_dir at a main tree whose .plan has no execute-script.py
        # so the copy-from-main fallback also fails — but the plan dir to MOVE
        # still exists at the original location (the real move source).
        # Remove main's executor instead, keeping the real plan dir intact.
        env['executor'].unlink()

        result = prepare_execute.run_prepare_execute(
            Namespace(plan_id=env['plan_id'], branch='feature/sample-plan', base=None)
        )

        # The plan-dir move succeeded and was NOT rolled back...
        assert result['status'] == 'success', result
        assert result['action'] == 'moved'
        wt_plan_dir = env['worktree_path'] / '.plan' / 'local' / 'plans' / env['plan_id']
        assert wt_plan_dir.is_dir()
        assert not env['plan_dir'].exists()  # moved, not copied/restored

        # ...but the failed generation is reported faithfully (not a false True).
        assert result['worktree_executor_generated'] is False
        assert 'executor_detail' in result
        assert not (env['worktree_path'] / '.plan' / 'execute-script.py').exists()


# =============================================================================
# End-to-end regression: absent worktree executor never reported as generated
# =============================================================================
#
# These tests drive the FULL run_prepare_execute move-in → return-TOON path with
# the REAL _generate_worktree_executor wired in (the isolated_env fixture stubs
# it away with fake_generate, so each test restores the real implementation
# first). They reproduce the original user-visible defect signature end-to-end:
# a returncode==0 generation against a worktree with no reachable
# marketplace/bundles reported ``worktree_executor_generated: true`` while no
# ``execute-script.py`` existed on disk, so every subsequent relative executor
# call from the cwd-pinned worktree failed ``No such file or directory``.
#
# Pre-fix behaviour: _generate_worktree_executor returned ``(True, ...)`` on
# ``returncode == 0`` WITHOUT asserting the file landed, so the unrecoverable
# variant below would report ``worktree_executor_generated: True`` for an absent
# file — the exact false positive these tests guard against. Post-fix (D1), the
# on-disk post-assertion makes the same path report ``False`` truthfully. The
# unrecoverable variant therefore FAILS against the pre-fix function and PASSES
# after D1, acting as the regression guard.


class TestPrepareExecuteEndToEndExecutorReporting:
    """Full move-in path with the real executor-generation logic wired in."""

    def _wire_real_generation_no_marketplace(
        self, env: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Restore the real _generate_worktree_executor and simulate a
        plugin-cache layout: a generator that exits 0 having written nothing
        (no reachable marketplace/bundles to anchor against)."""
        monkeypatch.setattr(
            prepare_execute, '_generate_worktree_executor', _REAL_GENERATE_WORKTREE_EXECUTOR
        )
        # Generator present but a no-op: exits 0 and writes no executor file —
        # the exact "exited 0, wrote nothing" plugin-cache condition.
        monkeypatch.setattr(prepare_execute, '_GENERATE_EXECUTOR_PATH', env['main'] / 'fake_gen.py')
        (env['main'] / 'fake_gen.py').write_text('# stub generator\n')

        class _Result:
            returncode = 0
            stdout = ''
            stderr = ''

        monkeypatch.setattr(prepare_execute.subprocess, 'run', lambda *a, **k: _Result())

    def test_unrecoverable_absent_executor_is_never_reported_as_generated(
        self, isolated_env: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """REGRESSION: generation exits 0 / writes nothing AND no main executor to
        copy → the returned TOON reports ``worktree_executor_generated: False``
        with a truthful detail and NO ``execute-script.py`` on disk.

        This reproduces the original ``worktree_executor_generated: true`` /
        absent-file signature from the user-visible move-in path. Against the
        pre-fix function (which returned True on returncode==0 without checking
        the file) this assertion would observe ``True`` and FAIL; after D1 it
        observes the truthful ``False`` and PASSES."""
        env = isolated_env
        self._wire_real_generation_no_marketplace(env, monkeypatch)

        # Redirect get_plan_dir to a main tree whose .plan has NO
        # execute-script.py. This is both the move-in source (a real plan dir
        # with content to move) and the copy-from-main lookup root (its .plan
        # ancestor has no executor), so the copy-from-main fallback finds no
        # source and the executor stays unrecoverable.
        no_exec_main = env['main'] / 'no-executor'
        no_exec_plan_dir = no_exec_main / '.plan' / 'local' / 'plans' / env['plan_id']
        no_exec_plan_dir.mkdir(parents=True)
        (no_exec_plan_dir / 'status.json').write_text('{}\n')
        monkeypatch.setattr(
            prepare_execute, 'get_plan_dir', lambda pid: no_exec_main / '.plan' / 'local' / 'plans' / pid
        )

        result = prepare_execute.run_prepare_execute(
            Namespace(plan_id=env['plan_id'], branch='feature/sample-plan', base=None)
        )

        # The plan-dir move-in still succeeds (non-fatal generation contract)...
        assert result['status'] == 'success', result
        assert result['action'] == 'moved'
        wt_plan_dir = env['worktree_path'] / '.plan' / 'local' / 'plans' / env['plan_id']
        assert wt_plan_dir.is_dir()

        # ...but the absent executor is NOT claimed as generated (the regression).
        assert result['worktree_executor_generated'] is False
        assert 'executor_detail' in result
        wt_exec = env['worktree_path'] / '.plan' / 'execute-script.py'
        assert not wt_exec.exists()

    def test_recoverable_variant_lands_real_executor_via_copy_from_main(
        self, isolated_env: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When generation cannot land but main's executor exists, the full path
        recovers via copy-from-main: a real, non-empty ``execute-script.py``
        lands in the worktree and the TOON reports success."""
        env = isolated_env
        self._wire_real_generation_no_marketplace(env, monkeypatch)

        # Main's executor is present with distinctive content (the copy source).
        main_content = '#!/usr/bin/env python3\n# distinctive MAIN bytes for e2e\n'
        env['executor'].write_text(main_content)

        result = prepare_execute.run_prepare_execute(
            Namespace(plan_id=env['plan_id'], branch='feature/sample-plan', base=None)
        )

        assert result['status'] == 'success', result
        assert result['action'] == 'moved'
        # The executor is genuinely on disk and byte-equivalent to main's.
        assert result['worktree_executor_generated'] is True
        assert 'copied from main' in result['executor_detail']
        wt_exec = env['worktree_path'] / '.plan' / 'execute-script.py'
        assert wt_exec.is_file()
        assert wt_exec.stat().st_size > 0
        assert wt_exec.read_text() == main_content

        # Main's executor is untouched by the copy.
        assert env['executor'].read_text() == main_content

    def test_plan_dir_move_unaffected_by_executor_outcome(
        self, isolated_env: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Non-fatal generation contract end-to-end: whether the executor lands or
        not, the plan-dir move-in completes and is never rolled back."""
        env = isolated_env
        self._wire_real_generation_no_marketplace(env, monkeypatch)
        # Remove main's executor so neither generation nor copy can produce one.
        env['executor'].unlink()

        result = prepare_execute.run_prepare_execute(
            Namespace(plan_id=env['plan_id'], branch='feature/sample-plan', base=None)
        )

        # Move-in succeeded and was NOT rolled back despite the failed executor.
        assert result['status'] == 'success', result
        assert result['action'] == 'moved'
        wt_plan_dir = env['worktree_path'] / '.plan' / 'local' / 'plans' / env['plan_id']
        assert wt_plan_dir.is_dir()
        assert (wt_plan_dir / 'status.json').is_file()
        assert not env['plan_dir'].exists()  # moved, not copied/restored
        # The failed executor is reported honestly, never a false positive.
        assert result['worktree_executor_generated'] is False


# =============================================================================
# CLI argparse plumbing
# =============================================================================


class TestPrepareExecuteCli:
    def test_prepare_requires_plan_id(self) -> None:
        from conftest import run_script

        result = run_script(SCRIPT_PATH, 'prepare')
        assert result.returncode != 0
        assert '--plan-id' in result.stderr or '--plan-id' in result.stdout

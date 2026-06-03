#!/usr/bin/env python3
"""Real-git end-to-end regression test for the worktree move-in lifecycle.

This is the test whose absence let the move-in defect ship (PR #556). It uses a
REAL ``git init`` + ``git worktree add`` and the REAL resolvers — NO mocked
``get_worktree_root`` / ``get_plan_dir`` / ``cmd_worktree_create`` /
``resolve_main_anchored_path`` — so it exercises the post-redesign no-symlink
contract end-to-end. The worktree-bound executor generation (which shells out to
generate_executor.py + marketplace discovery, absent from the tmp fixture) is
stubbed to write the worktree executor file; the move-in contract under test is
that main's executor is NOT moved, not the generator internals (covered by
generate_executor's own tests).

Contract under test (solution_outline.md §5, deliverable 5):

* ``worktree/.plan/local/plans/{plan_id}`` is a REAL non-symlink directory
  carrying the moved-in sentinel.
* ``worktree/.plan/local`` itself is a real directory (not a symlink).
* NO symlink exists anywhere under ``worktree/.plan/local`` (the core
  post-redesign invariant).
* main no longer holds ``.plan/local/plans/{plan_id}`` after move-in.
* FIX 1: main's ``.plan/execute-script.py`` is NOT moved — it stays present
  after move-in — and a worktree-bound executor is generated into the worktree.
* A symlinked ``worktree/.plan/local`` is rejected by ``prepare_execute``.
* From a worktree cwd, run-config + lessons writes land on MAIN via
  ``resolve_main_anchored_path`` (the b8912f main-anchored-via-utility
  assertion) — NOT mocked — and the worktree gains NO ``run-configuration.json``
  / ``lessons-learned`` of its own.

Isolation (test-isolation lessons 2026-06-02-12-001/002/003): every test stages
a unique ``tmp_path`` real-git repo, anchors runtime state via ``PLAN_BASE_DIR``
pointed at the staged main checkout's ``.plan/local``, and pins cwd
deterministically — the suite never contends for the real ``.plan/`` under
``-n auto``.
"""

from __future__ import annotations

import importlib.util
import subprocess
from argparse import Namespace
from pathlib import Path

import pytest

from conftest import get_script_path

_GW_PATH = get_script_path('plan-marshall', 'workflow-integration-git', 'git-workflow.py')
_gw_spec = importlib.util.spec_from_file_location('git_workflow', _GW_PATH)
assert _gw_spec is not None and _gw_spec.loader is not None
git_workflow = importlib.util.module_from_spec(_gw_spec)
_gw_spec.loader.exec_module(git_workflow)

_PE_PATH = get_script_path('plan-marshall', 'workflow-integration-git', 'prepare_execute.py')
_pe_spec = importlib.util.spec_from_file_location('prepare_execute', _PE_PATH)
assert _pe_spec is not None and _pe_spec.loader is not None
prepare_execute = importlib.util.module_from_spec(_pe_spec)
_pe_spec.loader.exec_module(prepare_execute)

_II_PATH = get_script_path('plan-marshall', 'workflow-integration-git', 'integrate_into_main.py')
_ii_spec = importlib.util.spec_from_file_location('integrate_into_main', _II_PATH)
assert _ii_spec is not None and _ii_spec.loader is not None
integrate_into_main = importlib.util.module_from_spec(_ii_spec)
_ii_spec.loader.exec_module(integrate_into_main)

_RC_PATH = get_script_path('plan-marshall', 'manage-run-config', 'run_config.py')
_rc_spec = importlib.util.spec_from_file_location('run_config', _RC_PATH)
assert _rc_spec is not None and _rc_spec.loader is not None
run_config = importlib.util.module_from_spec(_rc_spec)
_rc_spec.loader.exec_module(run_config)

import marketplace_paths  # type: ignore[import-not-found]  # noqa: E402

_PLAN_ID = 'lifecycle-plan'


def _init_main_repo(repo: Path) -> None:
    """Seed a real main checkout with the canonical .plan layout and content."""
    subprocess.run(['git', 'init', '-q', '-b', 'main', str(repo)], check=True)
    subprocess.run(['git', '-C', str(repo), 'config', 'user.email', 't@t.test'], check=True)
    subprocess.run(['git', '-C', str(repo), 'config', 'user.name', 'Test'], check=True)
    (repo / 'README.md').write_text('x\n')
    plan_dir = repo / '.plan'
    plan_dir.mkdir()
    (plan_dir / 'marshal.json').write_text('{"system": {}, "plan": {}}\n')
    (repo / '.gitignore').write_text('.plan/local\n.plan/execute-script.py\n.plan/local/worktrees/\n')
    subprocess.run(['git', '-C', str(repo), 'add', '.'], check=True)
    subprocess.run(['git', '-C', str(repo), 'commit', '-q', '-m', 'init'], check=True)

    # Gitignored runtime state on main: a plan dir with a sentinel, the real
    # executor, and the shared cross-session corpora.
    local = plan_dir / 'local'
    (local / 'plans' / _PLAN_ID).mkdir(parents=True)
    (local / 'plans' / _PLAN_ID / 'status.json').write_text('{"sentinel": true}\n')
    (plan_dir / 'execute-script.py').write_text('#!/usr/bin/env python3\n')
    (local / 'lessons-learned').mkdir(parents=True)
    (local / 'run-configuration.json').write_text('{"version": 1, "commands": {}}\n')


@pytest.fixture
def real_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    """Stage a real-git main checkout and anchor the real resolvers at it.

    PLAN_BASE_DIR is pointed at ``main/.plan/local`` so the cwd-relative
    resolvers (``get_worktree_root`` / ``get_plan_dir`` / ``get_executor_path``)
    and ``resolve_main_anchored_path`` all anchor at the staged main checkout —
    the override stands in for the main-checkout ``.plan/local`` exactly as in
    production test isolation.
    """
    main = tmp_path / 'main'
    main.mkdir()
    _init_main_repo(main)
    main_local = main / '.plan' / 'local'

    monkeypatch.setenv('PLAN_BASE_DIR', str(main_local))
    import file_ops  # type: ignore[import-not-found]

    monkeypatch.setattr(file_ops, '_BASE_DIR_OVERRIDE', None)
    monkeypatch.chdir(main)

    # Stub the worktree-bound executor generation: the real helper shells out to
    # generate_executor.py with marketplace discovery, which the tmp fixture has
    # no marketplace tree for. Simulate a clean generation by writing the worktree
    # executor file, so the move-in contract (main executor NOT moved, worktree
    # executor produced) is asserted without the real subprocess.
    def fake_generate(worktree_path: Path) -> tuple[bool, str]:
        wt_exec = worktree_path / '.plan' / 'execute-script.py'
        wt_exec.parent.mkdir(parents=True, exist_ok=True)
        wt_exec.write_text('#!/usr/bin/env python3\n# worktree-bound\n')
        return True, f'worktree executor generated at {wt_exec}'

    monkeypatch.setattr(prepare_execute, '_generate_worktree_executor', fake_generate)

    return {'main': main, 'main_local': main_local, 'plan_id': _PLAN_ID}


class TestWorktreeMoveLifecycle:
    def test_move_in_lands_real_plan_dir_no_symlinks(self, real_repo: dict) -> None:
        main_local = real_repo['main_local']
        plan_id = real_repo['plan_id']

        create = git_workflow.cmd_worktree_create(
            Namespace(plan_id=plan_id, branch=f'feature/{plan_id}', base=None)
        )
        assert create['status'] == 'success', create
        worktree = Path(create['worktree_path'])

        result = prepare_execute.run_prepare_execute(
            Namespace(plan_id=plan_id, branch=f'feature/{plan_id}', base=None)
        )
        assert result['status'] == 'success', result
        assert result['action'] == 'moved'

        wt_local = worktree / '.plan' / 'local'
        wt_plan_dir = wt_local / 'plans' / plan_id

        # (1) plans/{id} is a REAL non-symlink dir carrying the sentinel.
        assert wt_plan_dir.is_dir()
        assert not wt_plan_dir.is_symlink()
        assert (wt_plan_dir / 'status.json').read_text() == '{"sentinel": true}\n'

        # (2) .plan/local itself is a real directory.
        assert wt_local.is_dir() and not wt_local.is_symlink()

        # (3) NO symlink anywhere under the worktree .plan/local.
        for entry in wt_local.rglob('*'):
            assert not entry.is_symlink(), f'unexpected symlink under worktree .plan/local: {entry}'

        # (4) main no longer holds the plan dir (moved, not copied).
        assert not (main_local / 'plans' / plan_id).exists()

        # (5) FIX 1: main's executor is NOT moved — it stays present after
        # move-in. This is the regression the whole plan exists to fix: a
        # main-anchored hook shelling out to .plan/execute-script.py must never
        # find it missing while a worktree-backed plan sits mid-phase-5.
        main_executor = real_repo['main'] / '.plan' / 'execute-script.py'
        assert main_executor.is_file()
        assert not main_executor.is_symlink()

        # (6) FIX 1: the worktree gained its OWN generated executor, and the
        # payload reports the executor as no longer part of the moved slot set.
        assert result['worktree_executor_generated'] is True
        assert (worktree / '.plan' / 'execute-script.py').is_file()
        assert result['moved_in[1]'] == [str(wt_plan_dir)]
        assert 'moved_in[2]' not in result

    def test_integrate_round_trip_leaves_main_executor_untouched(self, real_repo: dict) -> None:
        """FIX 1 + Deliverable 5: across the full move-in → move-back round-trip,
        main's executor is present and byte-for-byte UNCHANGED, and
        ``integrate_into_main`` does NOT touch (move or regenerate) any
        ``.plan/execute-script.py``. On-main executor regeneration is relocated to
        the project-level ``finalize-step-sync-plugin-cache`` step — it is no
        longer ``integrate_into_main``'s responsibility, so the integrate payload
        carries no regen fields."""
        main = real_repo['main']
        main_local = real_repo['main_local']
        plan_id = real_repo['plan_id']
        main_executor = main / '.plan' / 'execute-script.py'

        # Snapshot main's executor content before the round-trip.
        before = main_executor.read_text()

        create = git_workflow.cmd_worktree_create(
            Namespace(plan_id=plan_id, branch=f'feature/{plan_id}', base=None)
        )
        assert create['status'] == 'success', create

        move_in = prepare_execute.run_prepare_execute(
            Namespace(plan_id=plan_id, branch=f'feature/{plan_id}', base=None)
        )
        assert move_in['status'] == 'success', move_in
        # Main executor present + unchanged right after move-in (never moved).
        assert main_executor.is_file()
        assert main_executor.read_text() == before

        # Move the plan dir back into main.
        move_back = integrate_into_main.run_integrate_into_main(Namespace(plan_id=plan_id))
        assert move_back['status'] == 'success', move_back
        assert move_back['action'] == 'integrated'

        # Deliverable 5: integrate carries NO regen fields and never touched the executor.
        assert 'regenerated' not in move_back
        assert 'regen_detail' not in move_back

        # Main's executor is present and byte-for-byte unchanged across the round-trip.
        assert main_executor.is_file()
        assert main_executor.read_text() == before

        # The plan dir is back on main.
        assert (main_local / 'plans' / plan_id).is_dir()

    def test_main_anchored_writes_from_worktree_cwd_land_on_main(
        self, real_repo: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """b8912f assertion: run-config + lessons resolve to MAIN from a worktree
        cwd via the real ``resolve_main_anchored_path`` — no symlink present."""
        main_local = real_repo['main_local']
        plan_id = real_repo['plan_id']

        git_workflow.cmd_worktree_create(
            Namespace(plan_id=plan_id, branch=f'feature/{plan_id}', base=None)
        )
        result = prepare_execute.run_prepare_execute(
            Namespace(plan_id=plan_id, branch=f'feature/{plan_id}', base=None)
        )
        worktree = Path(result['worktree_path'])

        # Pin cwd into the worktree — the phase-5 execution posture.
        monkeypatch.chdir(worktree)

        # run-config write from the worktree cwd lands on MAIN.
        run_config.timeout_set('build:verify', 300)
        assert (main_local / 'run-configuration.json').is_file()
        assert not (worktree / '.plan' / 'local' / 'run-configuration.json').exists()

        # lessons corpus resolves to MAIN's lessons-learned, not the worktree's.
        resolved_lessons = marketplace_paths.resolve_main_anchored_path('lessons-learned')
        assert resolved_lessons == main_local / 'lessons-learned'
        # Write a lesson-shaped file via the resolved path and confirm it lands
        # on main, leaving the worktree corpus empty.
        (resolved_lessons / '2025-01-01-01-001.md').write_text('id=2025-01-01-01-001\n\n# x\n')
        assert (main_local / 'lessons-learned' / '2025-01-01-01-001.md').is_file()
        wt_lessons = worktree / '.plan' / 'local' / 'lessons-learned'
        assert not wt_lessons.exists() or not list(wt_lessons.glob('*.md'))

    def test_move_in_rejects_symlinked_plan_local(self, real_repo: dict) -> None:
        """A symlinked worktree .plan/local is rejected before any move-in."""
        main_local = real_repo['main_local']
        plan_id = real_repo['plan_id']

        # Materialize the worktree, then replace its real .plan/local with a
        # symlink back to main — the retired-symlink-residue scenario.
        create = git_workflow.cmd_worktree_create(
            Namespace(plan_id=plan_id, branch=f'feature/{plan_id}', base=None)
        )
        worktree = Path(create['worktree_path'])
        wt_local = worktree / '.plan' / 'local'
        for entry in sorted(wt_local.rglob('*'), reverse=True):
            if entry.is_dir():
                entry.rmdir()
            else:
                entry.unlink()
        wt_local.rmdir()
        wt_local.symlink_to(main_local, target_is_directory=True)

        result = prepare_execute.run_prepare_execute(
            Namespace(plan_id=plan_id, branch=f'feature/{plan_id}', base=None)
        )

        assert result['status'] == 'error'
        assert result.get('error_code') == prepare_execute.ErrorCode.INVALID_INPUT
        # The plan dir stays WHOLLY on main — no move through the symlink.
        assert (main_local / 'plans' / plan_id).exists()

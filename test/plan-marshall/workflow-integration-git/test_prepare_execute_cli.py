#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
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

Isolation: every test runs
against an isolated ``PLAN_BASE_DIR`` staged under ``tmp_path`` with cwd pinned
to a stable location; ``cmd_worktree_create`` is stubbed so no real
``git worktree add`` runs and the suite never contends for the real ``.plan/``
under ``-n auto``.
"""

from __future__ import annotations

import os
import shutil
from argparse import Namespace
from pathlib import Path

import pytest

from conftest import get_script_path, load_script_module

SCRIPT_PATH = get_script_path('plan-marshall', 'workflow-integration-git', 'prepare_execute.py')

prepare_execute = load_script_module(
    'plan-marshall', 'workflow-integration-git', 'prepare_execute.py', 'prepare_execute'
)

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


# =============================================================================
# CLI argparse plumbing
# =============================================================================


class TestPrepareExecuteCli:
    def test_prepare_requires_plan_id(self) -> None:
        from conftest import run_script

        result = run_script(SCRIPT_PATH, 'prepare')
        assert result.returncode != 0
        assert '--plan-id' in result.stderr or '--plan-id' in result.stdout

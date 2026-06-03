#!/usr/bin/env python3
"""Atomic phase-5 move-in: materialize the worktree and move plan state in.

Notation: ``plan-marshall:workflow-integration-git:prepare_execute``

This is a single-action standalone script that, in ONE call, performs the
phase-5 materialization step of the move-based, cwd-pinned hermetic worktree
model (ADR-002, solution_outline.md §4):

  1. **Materialize** the worktree + feature branch (delegating to the existing
     ``git-workflow.py worktree-create`` machinery so a single code path owns
     ``git worktree add`` + ``.plan`` bookkeeping).
  2. **Move** (not copy) the plan-scoped non-git runtime state from the main
     checkout into the worktree-resident location: the plan directory
     (``.plan/local/plans/{plan_id}``) and the executor
     (``.plan/execute-script.py``).
  3. **Return** a status TOON carrying the canonical ``worktree_path`` and a
     ``status`` field.

Concurrency / crash correctness (solution_outline.md §4 "Concurrency-correctness
note"): the move-in is a check-then-act sequence with TOCTOU windows (a
concurrent session, an aborted prior attempt, or a crash mid-move). The script
is therefore:

  * **Idempotent** — an already-moved-in plan (real plan dir already resident
    in the worktree) is a no-op success that returns the same ``worktree_path``.
  * **Atomic-with-rollback** — a partial move failure rolls back so the plan
    state is left WHOLLY on main, never half-moved, and returns ``status:
    error``. The D3 resolver's "nearest ancestor ``.plan/local``" walk-up is the
    structural backstop, but this script never deliberately leaves a half-moved
    location for the resolver to stumble onto.

CWD design (solution_outline.md §4 "CWD design"): a subprocess cannot mutate its
parent's cwd, so this script does NOT change the caller's cwd. It RETURNS the
canonical worktree path; the phase-5 orchestrator pins ITS OWN cwd to that path
(D8 wires the pin). The script reads :func:`os.getcwd` once at entry and asserts
it is unchanged at every exit path as a defensive self-check.

See the TOCTOU / check-then-act mitigation menu in
``dev-general-code-quality/standards/code-organization.md#toctou--check-then-act-hazards``.
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import sys
from argparse import Namespace
from pathlib import Path
from typing import Any

from file_ops import (  # type: ignore[import-not-found]
    get_executor_path,
    get_plan_dir,
    get_worktree_root,
)
from marketplace_paths import PLAN_DIR_NAME  # type: ignore[import-not-found]
from triage_helpers import (  # type: ignore[import-not-found]
    ErrorCode,
    create_workflow_cli,
    make_error,
    print_toon,
    safe_main,
)

# ---------------------------------------------------------------------------
# worktree-create delegation
# ---------------------------------------------------------------------------
# git-workflow.py is kebab-case (not a valid module identifier), so load it via
# importlib to reuse cmd_worktree_create rather than re-implementing
# ``git worktree add`` + bookkeeping. Sharing the single materialization code
# path is the explicit design intent (solution_outline.md §4).

_THIS_DIR = Path(__file__).resolve().parent
_GIT_WORKFLOW_PATH = _THIS_DIR / 'git-workflow.py'


def _load_git_workflow() -> Any:
    """Import ``git-workflow.py`` by file path (kebab-case filename)."""
    spec = importlib.util.spec_from_file_location('git_workflow', _GIT_WORKFLOW_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'cannot load git-workflow.py from {_GIT_WORKFLOW_PATH}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# move-in primitives
# ---------------------------------------------------------------------------
#
# A "move-in slot" pairs a source path on the main checkout with its
# worktree-resident destination. ``worktree-create`` symlinks .plan/local and
# .plan/execute-script.py into main; the move-in replaces those symlinks with
# the real moved content so the worktree owns an authoritative copy.


def _is_real_moved_in(dst: Path) -> bool:
    """Return True when ``dst`` is a real (non-symlink) materialized path."""
    return dst.exists() and not dst.is_symlink()


def _move_in_slot(src: Path, dst: Path) -> None:
    """Move ``src`` to ``dst``, replacing any symlink/stale dst first.

    The destination's parent must already exist (the worktree's ``.plan`` /
    ``.plan/local`` tree is materialized by ``git worktree add`` +
    ``worktree-create``). When ``dst`` is a symlink (the placeholder
    ``worktree-create`` created pointing back at main) it is unlinked before the
    move so the real content takes its place.
    """
    if dst.is_symlink():
        dst.unlink()
    elif dst.exists():
        # A real path already occupies the destination — refuse rather than
        # silently clobber. The idempotence guard in run_prepare_execute()
        # short-circuits the already-moved-in case before reaching here, so a
        # real dst at this point is an unexpected collision.
        raise FileExistsError(f'destination already occupied by real path: {dst}')
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst))


def _restore_slot(src: Path, dst: Path) -> None:
    """Best-effort inverse of :func:`_move_in_slot` for rollback.

    Moves a successfully-moved ``dst`` back to ``src`` so a partial failure
    leaves the plan state WHOLLY on main. Swallows errors — rollback runs on the
    error path and must not mask the original failure.
    """
    try:
        if _is_real_moved_in(dst) and not src.exists():
            src.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(dst), str(src))
    except OSError:
        pass


# ---------------------------------------------------------------------------
# main action
# ---------------------------------------------------------------------------


def run_prepare_execute(args: Namespace) -> dict[str, Any]:
    """Materialize the worktree and move plan-scoped state in (single action).

    Returns a TOON-shaped payload carrying ``status`` and (on success) the
    canonical ``worktree_path``. Never changes the caller's cwd.
    """
    plan_id: str = args.plan_id
    branch: str | None = getattr(args, 'branch', None)
    base: str | None = getattr(args, 'base', None)

    cwd_at_entry = os.getcwd()

    def _assert_cwd_unchanged(payload: dict[str, Any]) -> dict[str, Any]:
        """Defensive self-check: this script must never mutate the caller cwd."""
        if os.getcwd() != cwd_at_entry:
            # Restore and surface as an internal error — a cwd change is a bug.
            os.chdir(cwd_at_entry)
            return make_error(
                'prepare_execute changed the process cwd (invariant violation); restored',
                code=ErrorCode.INVALID_INPUT,
                plan_id=plan_id,
            )
        return payload

    # Resolve the canonical worktree path for this plan (independent of whether
    # it has been materialized yet). This is the path the caller pins cwd to.
    try:
        worktree_path = get_worktree_root() / plan_id
    except RuntimeError as exc:
        return _assert_cwd_unchanged(
            make_error(
                f'cannot resolve worktree root: {exc}',
                code=ErrorCode.NOT_FOUND,
                plan_id=plan_id,
            )
        )

    # The main checkout's plan-scoped state (read via the uniform cwd rule:
    # the caller runs phase-5 with cwd still on main at this point).
    main_plan_dir = get_plan_dir(plan_id)
    try:
        main_executor = get_executor_path()
    except RuntimeError as exc:
        return _assert_cwd_unchanged(
            make_error(
                f'cannot resolve executor path: {exc}',
                code=ErrorCode.NOT_FOUND,
                plan_id=plan_id,
            )
        )

    # Worktree-resident destinations for the moved-in state.
    wt_plan_dir = worktree_path / PLAN_DIR_NAME / 'local' / 'plans' / plan_id
    wt_executor = worktree_path / PLAN_DIR_NAME / 'execute-script.py'

    # --- Idempotence guard -------------------------------------------------
    # If the plan dir is already a real (non-symlink) path resident in the
    # worktree, the move-in already ran (this is a phase-5 re-entry). Return a
    # no-op success carrying the same path.
    if _is_real_moved_in(wt_plan_dir):
        return _assert_cwd_unchanged(
            {
                'status': 'success',
                'plan_id': plan_id,
                'worktree_path': str(worktree_path),
                'action': 'noop',
                'message': 'plan state already moved into worktree',
            }
        )

    # --- Step 1: materialize the worktree (idempotent re-use) --------------
    # worktree-create returns error 'worktree_exists' when the path is already
    # on disk — that is fine for a re-entry where the worktree exists but the
    # plan dir has not yet been moved in. Treat worktree_exists as a benign
    # already-materialized signal; any other error aborts.
    if not worktree_path.exists():
        if not branch:
            return _assert_cwd_unchanged(
                make_error(
                    '--branch is required when the worktree has not been materialized yet',
                    code=ErrorCode.INVALID_INPUT,
                    plan_id=plan_id,
                )
            )
        git_workflow = _load_git_workflow()
        create_result = git_workflow.cmd_worktree_create(
            Namespace(plan_id=plan_id, branch=branch, base=base)
        )
        if create_result.get('status') != 'success' and create_result.get('error') != 'worktree_exists':
            return _assert_cwd_unchanged(
                {
                    **create_result,
                    'plan_id': plan_id,
                }
            )

    # --- Step 2: move plan-scoped state into the worktree (atomic) ---------
    # Track completed moves so a later failure can roll them back, leaving the
    # plan state WHOLLY on main.
    completed: list[tuple[Path, Path]] = []
    slots: list[tuple[Path, Path]] = [
        (main_plan_dir, wt_plan_dir),
        (main_executor, wt_executor),
    ]

    # Pre-flight: the plan dir MUST exist on main to move it in. Its absence
    # means the plan was never initialized on main (or already moved by a
    # concurrent session) — fail loud rather than materialize an empty slot.
    if not main_plan_dir.exists():
        return _assert_cwd_unchanged(
            make_error(
                f'plan directory not found on main checkout: {main_plan_dir}',
                code=ErrorCode.NOT_FOUND,
                plan_id=plan_id,
            )
        )

    for src, dst in slots:
        if not src.exists() and not src.is_symlink():
            # The executor may legitimately be absent in a fresh repo before
            # /marshall-steward regeneration; skip a missing executor slot but
            # never skip the plan dir (guarded above).
            if dst == wt_executor:
                continue
            # Roll back what we already moved and abort.
            for done_src, done_dst in reversed(completed):
                _restore_slot(done_src, done_dst)
            return _assert_cwd_unchanged(
                make_error(
                    f'move-in source missing: {src}',
                    code=ErrorCode.NOT_FOUND,
                    plan_id=plan_id,
                )
            )
        try:
            _move_in_slot(src, dst)
            completed.append((src, dst))
        except (OSError, FileExistsError) as exc:
            # Partial-failure rollback: restore every completed move so the
            # plan state ends up WHOLLY on main, never half-moved.
            for done_src, done_dst in reversed(completed):
                _restore_slot(done_src, done_dst)
            return _assert_cwd_unchanged(
                make_error(
                    f'move-in failed at {src} -> {dst}: {exc}; rolled back to main',
                    code=ErrorCode.INVALID_INPUT,
                    plan_id=plan_id,
                )
            )

    return _assert_cwd_unchanged(
        {
            'status': 'success',
            'plan_id': plan_id,
            'worktree_path': str(worktree_path),
            'action': 'moved',
            'moved_in[2]': [str(wt_plan_dir), str(wt_executor)],
        }
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    """Entry point — single ``prepare`` action."""
    parser = create_workflow_cli(
        description='Atomic phase-5 move-in: materialize the worktree and move plan state in',
        epilog="""
Examples:
  prepare_execute.py prepare --plan-id EXAMPLE-PLAN --branch feature/EXAMPLE-PLAN [--base origin/main]
""",
        subcommands=[
            {
                'name': 'prepare',
                'help': 'Materialize the worktree and atomically move plan state in',
                'handler': run_prepare_execute,
                'args': [
                    {
                        'flags': ['--plan-id'],
                        'dest': 'plan_id',
                        'required': True,
                        'help': 'Plan identifier (mandatory)',
                    },
                    {
                        'flags': ['--branch'],
                        'help': (
                            'Feature branch to create when the worktree has not been '
                            'materialized yet (required on first run; ignored on re-entry)'
                        ),
                    },
                    {
                        'flags': ['--base'],
                        'help': 'Base ref for the new branch (default: current HEAD)',
                    },
                ],
            },
        ],
    )
    args = parser.parse_args()
    return print_toon(args.func(args))


if __name__ == '__main__':
    sys.exit(safe_main(main))

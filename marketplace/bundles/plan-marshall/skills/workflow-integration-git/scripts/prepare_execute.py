#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Atomic phase-5 move-in: materialize the worktree and move plan state in.

Notation: ``plan-marshall:workflow-integration-git:prepare_execute``

This is a single-action standalone script that, in ONE call, performs the
phase-5 materialization step of the move-based, cwd-pinned hermetic worktree
model (ADR-002, solution_outline.md §4):

  1. **Materialize** the worktree + feature branch (delegating to the existing
     ``git-workflow.py worktree-create`` machinery so a single code path owns
     ``git worktree add`` + ``.plan`` bookkeeping).
  2. **Move** (not copy) the plan directory (``.plan/local/plans/{plan_id}``)
     from the main checkout into the worktree-resident location. The executor
     (``.plan/execute-script.py``) is NOT moved — it is per-tree DERIVED state:
     main's copy stays present and untouched, and a worktree-bound copy is
     GENERATED into the worktree (via ``generate_executor --marketplace-root``).
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
``ref-code-quality/standards/code-organization.md#toctou--check-then-act-hazards``.
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
from argparse import Namespace
from pathlib import Path
from typing import Any

from file_ops import (
    get_plan_dir,
    get_worktree_root,
)
from marketplace_paths import PLAN_DIR_NAME
from triage_helpers import (
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
# worktree-resident destination. Under the move-based model (ADR-002) the
# worktree owns a fully REAL ``.plan/local`` with NO symlinks: ``worktree-create``
# materializes ``.plan/local`` as a real directory, and the move-in lands the
# real plan dir + executor inside it. There is no symlink for the move-in to
# replace; the genuinely-shared cross-session corpora are reached by the
# main-anchored resolver, not by filesystem symlinks.


def _is_real_moved_in(dst: Path) -> bool:
    """Return True when ``dst`` is a real (non-symlink) materialized path AND no
    ancestor up to the ``.plan`` directory is a symlink.

    Applies to the plan-dir move-in slot (``.plan/local/plans/{id}``). Walking
    up to the ``.plan`` directory and rejecting any symlinked ancestor keeps the
    "already moved in" verdict robust to residual symlink traversal: under the
    no-symlink model every ancestor is a real directory, so a ``dst`` reachable
    only through a symlinked ancestor is rejected as not-yet-moved (correct
    first-run behaviour).
    """
    if not (dst.exists() and not dst.is_symlink()):
        return False
    curr = dst.parent
    while curr != curr.parent:
        if curr.is_symlink():
            return False
        if curr.name == PLAN_DIR_NAME:
            break
        curr = curr.parent
    return True


def _move_in_slot(src: Path, dst: Path) -> None:
    """Move ``src`` to ``dst``, replacing any stale dst first.

    The destination's parent must already exist (the worktree's ``.plan`` /
    ``.plan/local`` tree is materialized as a REAL directory by ``git worktree
    add`` + ``worktree-create``). The ``dst.is_symlink()`` unlink branch is a
    defensive no-op under the no-symlink model (the leaf is absent on a fresh
    move-in and the parent is real) but is retained as harmless robustness.
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
# worktree-bound executor generation
# ---------------------------------------------------------------------------
#
# The executor is per-tree DERIVED state, NOT a moved slot: main's copy stays
# present and untouched, and the worktree gets its own copy with worktree-bound
# mappings, generated here. This mirrors the worktree-fresh-executor pattern in
# finalize-step-plugin-doctor. Generation is universal (every new worktree needs
# a working executor) — distinct from the meta-project-only finalize REgeneration
# of main's executor after a script-set change.

_GENERATE_EXECUTOR_PATH = (
    _THIS_DIR.parent.parent / 'tools-script-executor' / 'scripts' / 'generate_executor.py'
)


def _worktree_executor_path(worktree_path: Path) -> Path:
    return worktree_path / PLAN_DIR_NAME / 'execute-script.py'


def _executor_landed(executor_path: Path) -> bool:
    """Return True when ``executor_path`` exists on disk AND is non-empty.

    The on-disk post-assertion (FIX 1): a generation that exits 0 but writes
    nothing (the plugin-cache-install case, where the worktree has no vendored
    ``marketplace/bundles`` and anchoring lands nowhere) leaves the executor
    absent or empty. ``returncode == 0`` alone is NOT proof the file landed, so
    the success verdict must be derived from on-disk reality, never from
    generation intent.
    """
    try:
        return executor_path.is_file() and not executor_path.is_symlink() and executor_path.stat().st_size > 0
    except OSError:
        return False


def _main_executor_path(plan_id: str) -> Path | None:
    """Resolve the MAIN checkout's executor (``.plan/execute-script.py``).

    The main executor is per-tree DERIVED state that ADR-002 keeps present and
    untouched at move-in; at this point the caller's cwd is still MAIN, so it is
    the byte-source for the copy-from-main fallback. Derived from the
    main-checkout plan dir the script already resolves via ``get_plan_dir`` (the
    one monkeypatch seam tests exercise): ``main_plan_dir`` is
    ``<main>/.plan/local/plans/{id}``, so walking up to the ``.plan`` directory
    yields ``<main>/.plan`` whose child ``execute-script.py`` is the source. This
    mirrors the main-anchored exception (``resolve_main_anchored_path``) without
    coupling the copy to real git-common-dir resolution, keeping the fallback
    testable under the isolated tmp_path layout.

    Returns the resolved path, or ``None`` when the ``.plan`` ancestor cannot be
    located (a malformed main layout) — the caller treats ``None`` as "no main
    executor available to copy".
    """
    try:
        main_plan_dir = get_plan_dir(plan_id)
    except RuntimeError:
        return None
    curr = main_plan_dir
    while curr != curr.parent:
        if curr.name == PLAN_DIR_NAME:
            return curr / 'execute-script.py'
        curr = curr.parent
    return None


def _copy_main_executor(worktree_path: Path, plan_id: str) -> tuple[bool, str]:
    """Copy main's executor verbatim into the worktree (the FIX 2 fallback).

    Used when generation is not viable or did not land on disk. The executor is a
    pure notation→absolute-path proxy whose mappings are project-wide
    plugin-cache absolutes (cwd-independent) and which resolves ``.plan/local`` by
    walking up from cwd — so a verbatim copy of main's executor satisfies the
    EXACT same contract as a fresh generation (solution_outline.md §Overview).
    Re-asserts the copied file landed and is non-empty before reporting success.

    Returns ``(copied, detail)`` — never raises (non-fatal contract).
    """
    main_executor = _main_executor_path(plan_id)
    if main_executor is None or not _executor_landed(main_executor):
        return False, 'no main executor available to copy from'
    wt_executor = _worktree_executor_path(worktree_path)
    try:
        wt_executor.parent.mkdir(parents=True, exist_ok=True)
        wt_executor.unlink(missing_ok=True)
        shutil.copy(str(main_executor), str(wt_executor))
    except OSError as exc:
        return False, f'copy-from-main failed: {exc}'
    if not _executor_landed(wt_executor):
        return False, f'copy-from-main produced no file on disk at {wt_executor}'
    return True, f'worktree executor copied from main ({main_executor} -> {wt_executor})'


def _generate_worktree_executor(worktree_path: Path, plan_id: str) -> tuple[bool, str]:
    """Produce ``worktree_path/.plan/execute-script.py`` and confirm it on disk.

    Two production mechanisms, tried in order, with the verdict ALWAYS derived
    from on-disk reality (never generation intent):

      1. **Generation** — invoke ``generate_executor.py generate
         --marketplace-root {worktree_path}`` as a subprocess. Then assert
         (FIX 1) the target executor exists AND is non-empty via
         :func:`_executor_landed`. A ``returncode == 0`` that wrote nothing (the
         plugin-cache install where the worktree has no vendored
         ``marketplace/bundles``) does NOT count as success and falls through.
      2. **Copy-from-main fallback** (FIX 2) — when generation is unavailable
         (missing generator), failed to launch, exited non-zero, or exited 0 but
         left no file, copy main's executor verbatim via
         :func:`_copy_main_executor`. The copy is byte-equivalent to a correct
         generation (solution_outline.md §Overview) and only changes the
         PRODUCTION MECHANISM when marketplace anchoring is structurally
         unavailable.

    NON-FATAL and idempotent: every failure mode is reported in the return value
    and NEVER raised, so the already-completed plan-dir move is preserved — the
    worktree can recover later via ``/marshall-steward``.

    The subprocess runs with ``cwd`` pinned to ``worktree_path``: the generator
    writes its output to ``get_tracked_config_dir()/execute-script.py``, which is
    resolved by walking up from the cwd to the nearest ``.plan/local`` ancestor.
    At move-in the orchestrator's cwd is still MAIN (the pin to the worktree
    happens AFTER this returns), so without the explicit ``cwd`` the generator
    would clobber main's executor — the exact regression this fix prevents.
    ``--marketplace-root`` only pins bundle DISCOVERY, not the output location.

    Returns ``(produced, detail)``: ``produced`` is True only after the worktree
    executor is confirmed present and non-empty on disk (by either mechanism);
    ``detail`` names which mechanism produced it (or why neither could).
    """
    wt_executor = _worktree_executor_path(worktree_path)

    if not _GENERATE_EXECUTOR_PATH.exists():
        # Generation is unavailable — go straight to the copy-from-main fallback.
        copied, copy_detail = _copy_main_executor(worktree_path, plan_id)
        if copied:
            return True, copy_detail
        return False, f'generator not found at {_GENERATE_EXECUTOR_PATH}; {copy_detail}'

    launch_detail: str | None = None
    try:
        result = subprocess.run(
            [
                sys.executable,
                str(_GENERATE_EXECUTOR_PATH),
                'generate',
                '--marketplace-root',
                str(worktree_path),
            ],
            cwd=str(worktree_path),
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        launch_detail = f'generation failed to launch: {exc}'
    else:
        if result.returncode != 0:
            lines = (result.stderr or result.stdout or '').strip().splitlines()
            tail = lines[-1] if lines else f'exit {result.returncode}'
            launch_detail = f'generation exited {result.returncode}: {tail}'
        elif _executor_landed(wt_executor):
            # FIX 1: only report success after the file is confirmed on disk.
            return True, f'worktree executor generated at {wt_executor}'
        else:
            # returncode 0 but no file landed (plugin-cache "exited 0, wrote
            # nothing" condition) — do NOT report a generation that did not land.
            launch_detail = f'generation exited 0 but no file landed at {wt_executor}'

    # FIX 2: generation did not produce a usable executor — copy from main.
    copied, copy_detail = _copy_main_executor(worktree_path, plan_id)
    if copied:
        return True, copy_detail
    return False, f'{launch_detail}; {copy_detail}'


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

    # The main checkout's plan directory (read via the uniform cwd rule: the
    # caller runs phase-5 with cwd still on main at this point).
    main_plan_dir = get_plan_dir(plan_id)

    # Worktree-resident destination for the moved-in plan directory. The
    # executor is NOT moved — its worktree copy is generated post-move below.
    wt_plan_dir = worktree_path / PLAN_DIR_NAME / 'local' / 'plans' / plan_id
    wt_plan_local = worktree_path / PLAN_DIR_NAME / 'local'

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

    # --- Symlinked .plan/local rejection -----------------------------------
    # Under the no-symlink model (ADR-002) the worktree's .plan/local is a fully
    # real directory. A symlinked .plan/local is a residue of the retired
    # symlink machinery (or a hand-rolled link) that would make the move-in land
    # plan state on main through the symlink. Reject it loudly rather than move
    # through it.
    if wt_plan_local.is_symlink():
        return _assert_cwd_unchanged(
            make_error(
                f'worktree .plan/local is a symlink ({wt_plan_local}); the move-based model '
                'requires a real .plan/local directory. Remove the symlink and re-create the '
                'worktree (worktree-create now materializes a real .plan/local).',
                code=ErrorCode.INVALID_INPUT,
                plan_id=plan_id,
            )
        )

    # --- Idempotence guard (materialize-then-guard) ------------------------
    # Runs AFTER worktree materialization so .plan/local is guaranteed present.
    # If the plan dir is already a real (non-symlink) path resident in the
    # worktree AND its parent .plan/local is a real directory, the move-in
    # already ran (phase-5 re-entry).
    if _is_real_moved_in(wt_plan_dir):
        # FIX 3: self-heal a partial materialization. A prior run may have moved
        # the plan dir in but left the executor absent (the original defect:
        # generation reported success for a file that never landed). Before
        # returning a bare noop, check the worktree executor on disk; when it is
        # missing, regenerate/copy it and report the heal. This makes the move-in
        # genuinely self-healing without re-attempting ``git worktree add``.
        wt_executor = _worktree_executor_path(worktree_path)
        if _executor_landed(wt_executor):
            return _assert_cwd_unchanged(
                {
                    'status': 'success',
                    'plan_id': plan_id,
                    'worktree_path': str(worktree_path),
                    'action': 'noop',
                    'message': 'plan state already moved into worktree',
                }
            )
        generated, executor_detail = _generate_worktree_executor(worktree_path, plan_id)
        return _assert_cwd_unchanged(
            {
                'status': 'success',
                'plan_id': plan_id,
                'worktree_path': str(worktree_path),
                'action': 'healed',
                'message': 'plan state already moved in; regenerated missing worktree executor',
                'worktree_executor_generated': generated,
                'executor_detail': executor_detail,
            }
        )

    # --- Step 2: move plan-scoped state into the worktree (atomic) ---------
    # Track completed moves so a later failure can roll them back, leaving the
    # plan state WHOLLY on main.
    completed: list[tuple[Path, Path]] = []
    slots: list[tuple[Path, Path]] = [
        (main_plan_dir, wt_plan_dir),
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
            # Only the plan dir is moved now, and the pre-flight check above
            # guarantees its presence — a missing source here is unexpected.
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

    # --- Step 3: generate a worktree-bound executor ------------------------
    # The executor is per-tree DERIVED state — main's copy is never moved, so
    # the worktree needs its own. Generation is non-fatal: a failure is reported
    # in the payload but never rolls back the completed plan-dir move.
    generated, executor_detail = _generate_worktree_executor(worktree_path, plan_id)

    return _assert_cwd_unchanged(
        {
            'status': 'success',
            'plan_id': plan_id,
            'worktree_path': str(worktree_path),
            'action': 'moved',
            'moved_in[1]': [str(wt_plan_dir)],
            'worktree_executor_generated': generated,
            'executor_detail': executor_detail,
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

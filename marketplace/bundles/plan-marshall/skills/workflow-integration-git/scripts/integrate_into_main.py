#!/usr/bin/env python3
"""Atomic finalize move-back: integrate the worktree-resident plan into main.

Notation: ``plan-marshall:workflow-integration-git:integrate_into_main``

This is a single-action standalone script that, in ONE atomic call, performs the
finalize integration step of the move-based, cwd-pinned hermetic worktree model
(ADR-002, solution_outline.md §5). It is the inverse of the D4 move-in script
(``prepare_execute.py``) and runs while the worktree is STILL PRESENT — branch
cleanup removes the worktree AFTER this script returns. In one call it:

  1. **ACQUIRES** the cooperative merge lock (delegating to the D15 ``merge_lock``
     script — atomic ``O_EXCL`` create, holder = this ``plan_id``, simple-backoff
     retry, minimal stale reclamation). The merge lock is the SINGLE deliberate
     main-anchored exception to cwd-relative resolution (ADR-002).
  2. **FOLDS** the plan's OWN global logs (only logs generated for this plan,
     currently resident in the worktree's ``.plan/local/logs/``) into the plan
     directory (``.plan/local/plans/{plan_id}/logs/``) BEFORE move-back so the
     retrospective can read them after the plan dir lands on main.
  3. **MOVES** the plan directory back from the worktree to the main checkout.
  4. **REGENERATES** the executor against main — NOT a file-move. A
     worktree-bound executor file-moved onto main re-introduces the original
     boundary defect; the regenerate runs with the working directory on main so
     the uniform cwd rule (ADR-002) resolves it to main's ``.plan/``.
     ``integrate_into_main.py`` is the SINGLE owner of finalize executor
     regeneration. The regen is gated by the
     modified-files filter — it runs only when the plan touched a ``.py`` file
     under ``marketplace/bundles/*/skills/*/scripts/`` — and is idempotent and
     NON-FATAL (a regen failure never blocks finalize).
  5. **RELEASES** the merge lock — on EVERY exit path, including the rollback
     path, so a crashed-and-retried finalize never wedges the lock.

It RETURNS a status TOON; it does NOT change the caller's cwd (a subprocess
cannot mutate its parent's cwd) and it does NOT remove the worktree (branch
cleanup owns that, after this returns). The finalize orchestrator returns ITS OWN
cwd to main after the call (so the uniform cwd rule resumes main resolution for
retrospective + archive).

Atomic-with-rollback (solution_outline.md §5): a partial move-back failure rolls
the plan dir BACK into the worktree so the authoritative copy is never split, and
the merge lock is released on the rollback path too. Idempotent: an
already-moved-back plan (real plan dir already resident on main, none in the
worktree) is a no-op success.

See the TOCTOU / check-then-act mitigation menu in
``dev-general-code-quality/standards/code-organization.md#toctou--check-then-act-hazards``
and the lock-correctness notes in ``merge_lock.py``.
"""

from __future__ import annotations

import importlib.util
import os
import re
import shutil
import subprocess
import sys
from argparse import Namespace
from pathlib import Path
from typing import Any

from file_ops import (  # type: ignore[import-not-found]
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
# Folded-in modified-files filter (from the deleted finalize-step-regenerate-
# executor wrapper). Only ``.py`` files DIRECTLY under skills/*/scripts/ declare
# new user-facing notations; nested subdirectories (importable modules) are
# already covered by the executor's PYTHONPATH _ALL_SCRIPT_DIRS, so they do NOT
# trigger a regeneration.
# ---------------------------------------------------------------------------
_SCRIPT_PATH_RE = re.compile(r'^marketplace/bundles/[^/]+/skills/[^/]+/scripts/[^/]+\.py$')


# ---------------------------------------------------------------------------
# Sibling-script delegation (kebab-case filenames → importlib by file path)
# ---------------------------------------------------------------------------
# merge_lock.py and generate_executor.py are loaded by file path so this script
# reuses the SINGLE owner of lock logic (merge_lock) and the SINGLE executor
# generator (generate_executor) rather than re-implementing either.

_THIS_DIR = Path(__file__).resolve().parent
_MERGE_LOCK_PATH = _THIS_DIR / 'merge_lock.py'


def _load_module_by_path(name: str, path: Path) -> Any:
    """Import a module by file path (used for sibling scripts)."""
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'cannot load {name} from {path}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_merge_lock() -> Any:
    """Import ``merge_lock.py`` by file path."""
    return _load_module_by_path('merge_lock', _MERGE_LOCK_PATH)


# ---------------------------------------------------------------------------
# move-back primitives (inverse of prepare_execute._move_in_slot)
# ---------------------------------------------------------------------------


def _is_real_resident(path: Path) -> bool:
    """Return True when ``path`` is a real (non-symlink) materialized path."""
    return path.exists() and not path.is_symlink()


def _move_back_dir(src: Path, dst: Path) -> None:
    """Move the plan dir ``src`` (worktree-resident) to ``dst`` (main).

    Replaces any symlink/stale placeholder at ``dst`` first (the worktree-create
    step left a symlink at main's slot pointing into the worktree; under the
    move model that is reversed at finalize). The destination's parent is created
    on demand.
    """
    if dst.is_symlink():
        dst.unlink()
    elif dst.exists():
        # A real path already occupies main's slot — refuse rather than clobber.
        # The idempotence guard short-circuits the already-moved-back case before
        # reaching here, so a real dst here is an unexpected collision.
        raise FileExistsError(f'main plan-dir slot already occupied by real path: {dst}')
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst))


def _restore_to_worktree(src: Path, dst: Path) -> None:
    """Best-effort inverse of :func:`_move_back_dir` for rollback.

    Moves a successfully-moved ``dst`` (main) back to ``src`` (worktree) so a
    partial failure leaves the authoritative plan copy WHOLLY in the worktree.
    Swallows errors — rollback runs on the error path and must not mask the
    original failure.
    """
    try:
        if _is_real_resident(dst) and not src.exists():
            src.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(dst), str(src))
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Fold the plan's own global logs into the plan dir
# ---------------------------------------------------------------------------


def _fold_global_logs(wt_global_logs: Path, plan_logs_dst: Path) -> list[str]:
    """Fold the worktree-resident global logs into the plan dir's ``logs/``.

    The plan's OWN global logs accumulate in the worktree's
    ``.plan/local/logs/`` during phase-5+ execution. Folding them into the plan
    dir BEFORE move-back makes them resident on main alongside the plan after
    integration, so the retrospective LOG step reads them from the plan dir.

    Best-effort and non-fatal: a missing/empty global-logs dir is a no-op. Each
    log file is COPIED (not moved) into ``<plan_dir>/logs/`` so the worktree's
    own copy is left intact for the worktree-removal step. Returns the list of
    folded-in log filenames (for the status payload).
    """
    folded: list[str] = []
    if not wt_global_logs.is_dir():
        return folded
    plan_logs_dst.mkdir(parents=True, exist_ok=True)
    for entry in sorted(wt_global_logs.iterdir()):
        if not entry.is_file():
            continue
        try:
            shutil.copy2(str(entry), str(plan_logs_dst / entry.name))
            folded.append(entry.name)
        except OSError:
            # A single un-copyable log never blocks finalize integration.
            continue
    return folded


# ---------------------------------------------------------------------------
# Executor regeneration (the single finalize executor-regeneration site)
# ---------------------------------------------------------------------------


def _read_modified_files(plan_id: str) -> list[str]:
    """Read ``references.modified_files`` for the plan from the on-main plan dir.

    Reads the moved-back plan dir's ``references.json`` (this runs AFTER move-back
    so the plan dir is resident on main). Best-effort: returns an empty list when
    references.json is absent or malformed.
    """
    references = get_plan_dir(plan_id) / 'references.json'
    if not references.is_file():
        return []
    try:
        import json

        data = json.loads(references.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return []
    modified = data.get('modified_files', [])
    return [str(p) for p in modified] if isinstance(modified, list) else []


def _has_marketplace_script_change(modified_files: list[str]) -> bool:
    """Return True when any modified file is a new/changed marketplace script.

    Mirrors the deleted wrapper's filter: only ``.py`` files DIRECTLY under
    ``marketplace/bundles/*/skills/*/scripts/`` qualify (new user-facing
    notations). Nested module subdirectories are intentionally excluded.
    """
    return any(_SCRIPT_PATH_RE.match(p) for p in modified_files)


def _regenerate_executor() -> dict[str, Any]:
    """Regenerate ``.plan/execute-script.py`` against main (cwd = main).

    Invokes the canonical generator (``generate_executor.py generate``) as a
    subprocess so the uniform cwd rule resolves the executor to main's ``.plan/``
    (this runs with the working directory on main). Idempotent and NON-FATAL: a
    non-zero exit or a raised exception is reported as a skipped/failed regen but
    NEVER propagates an error — finalize must not block on a mapping refresh
    (matching the deleted wrapper's contract).

    Returns a small dict describing the regen outcome for the status payload.
    """
    generator = _THIS_DIR.parent.parent / 'tools-script-executor' / 'scripts' / 'generate_executor.py'
    if not generator.is_file():
        return {'regenerated': False, 'regen_detail': f'generator not found: {generator}'}
    try:
        result = subprocess.run(
            [sys.executable, str(generator), 'generate'],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {'regenerated': False, 'regen_detail': f'regen invocation failed (non-fatal): {exc}'}
    if result.returncode != 0:
        return {
            'regenerated': False,
            'regen_detail': 'generator returned non-zero (non-fatal); run /marshall-steward to recover',
        }
    return {'regenerated': True, 'regen_detail': 'executor regenerated against main'}


# ---------------------------------------------------------------------------
# main action
# ---------------------------------------------------------------------------


def run_integrate_into_main(args: Namespace) -> dict[str, Any]:
    """Acquire lock → fold logs → move-back → regenerate → release (one action).

    Returns a TOON-shaped payload carrying ``status``. Never changes the caller's
    cwd; never removes the worktree. The merge lock is released on EVERY exit
    path, including rollback.
    """
    plan_id: str = args.plan_id

    cwd_at_entry = os.getcwd()

    def _assert_cwd_unchanged(payload: dict[str, Any]) -> dict[str, Any]:
        """Defensive self-check: this script must never mutate the caller cwd."""
        if os.getcwd() != cwd_at_entry:
            os.chdir(cwd_at_entry)
            return make_error(
                'integrate_into_main changed the process cwd (invariant violation); restored',
                code=ErrorCode.INVALID_INPUT,
                plan_id=plan_id,
            )
        return payload

    # Resolve the worktree-resident source and the main destination. This runs
    # with cwd = main (finalize regenerate-on-main path), so get_worktree_root()
    # and get_plan_dir() resolve against main's .plan/local via the uniform cwd
    # rule.
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

    main_plan_dir = get_plan_dir(plan_id)
    wt_plan_dir = worktree_path / PLAN_DIR_NAME / 'local' / 'plans' / plan_id
    wt_global_logs = worktree_path / PLAN_DIR_NAME / 'local' / 'logs'

    # --- Idempotence guard -------------------------------------------------
    # If the plan dir is already a real (non-symlink) path resident on main AND
    # no real plan dir remains in the worktree, the move-back already ran (a
    # finalize re-entry). Return a no-op success WITHOUT acquiring the lock —
    # there is nothing to coordinate.
    if _is_real_resident(main_plan_dir) and not _is_real_resident(wt_plan_dir):
        return _assert_cwd_unchanged(
            {
                'status': 'success',
                'plan_id': plan_id,
                'action': 'noop',
                'message': 'plan state already integrated into main',
            }
        )

    # The worktree-resident plan dir MUST exist to move it back. Its absence
    # (and the main dir also absent) means the plan was never moved in or the
    # state is in an unexpected shape — fail loud rather than fabricate.
    if not _is_real_resident(wt_plan_dir):
        return _assert_cwd_unchanged(
            make_error(
                f'worktree-resident plan directory not found: {wt_plan_dir}',
                code=ErrorCode.NOT_FOUND,
                plan_id=plan_id,
            )
        )

    # --- Step 1: acquire the cooperative merge lock ------------------------
    merge_lock = _load_merge_lock()
    acquire_result = merge_lock.run_acquire(Namespace(plan_id=plan_id, timeout=None))
    if acquire_result.get('status') != 'success':
        # Could not acquire (timeout / resolution failure) — surface verbatim.
        # No lock was acquired, so there is nothing to release.
        return _assert_cwd_unchanged({**acquire_result, 'plan_id': plan_id})

    def _release_and(payload: dict[str, Any]) -> dict[str, Any]:
        """Release the lock (idempotent) and return ``payload`` unchanged."""
        try:
            merge_lock.run_release(Namespace(plan_id=plan_id))
        except Exception:  # noqa: BLE001 - release must never mask the real result
            # Release failure is logged via the lock's own contract on the next
            # acquire's stale-reclamation path; never let it overwrite the
            # operation's real status.
            pass
        return _assert_cwd_unchanged(payload)

    # --- Step 2: fold the plan's own global logs into the plan dir ---------
    # Folded BEFORE move-back so they travel with the plan dir to main. Folds
    # into the WORKTREE-resident plan dir's logs/ (the dir we are about to move).
    folded_logs = _fold_global_logs(wt_global_logs, wt_plan_dir / 'logs')

    # --- Step 3: move the plan directory back to main (atomic w/ rollback) --
    try:
        _move_back_dir(wt_plan_dir, main_plan_dir)
    except (OSError, FileExistsError) as exc:
        # Roll the plan dir back into the worktree so the authoritative copy is
        # never split, then release the lock.
        _restore_to_worktree(wt_plan_dir, main_plan_dir)
        return _release_and(
            make_error(
                f'move-back failed for {wt_plan_dir} -> {main_plan_dir}: {exc}; '
                f'rolled back to worktree',
                code=ErrorCode.INVALID_INPUT,
                plan_id=plan_id,
            )
        )

    # --- Step 4: regenerate the executor against main (gated, non-fatal) ----
    # The plan dir is now on main, so references.json reads from main. Regenerate
    # only when the plan touched a marketplace script; the regen is non-fatal.
    modified_files = _read_modified_files(plan_id)
    if _has_marketplace_script_change(modified_files):
        regen = _regenerate_executor()
    else:
        regen = {'regenerated': False, 'regen_detail': 'no marketplace script changes; regen skipped'}

    # --- Step 5: release the lock and return success ------------------------
    return _release_and(
        {
            'status': 'success',
            'plan_id': plan_id,
            'action': 'integrated',
            'plan_dir': str(main_plan_dir),
            'folded_logs': folded_logs,
            'regenerated': regen['regenerated'],
            'regen_detail': regen['regen_detail'],
        }
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    """Entry point — single ``integrate`` action."""
    parser = create_workflow_cli(
        description=(
            'Atomic finalize move-back: acquire lock, fold logs, move plan dir to '
            'main, regenerate executor on main, release lock'
        ),
        epilog="""
Examples:
  integrate_into_main.py integrate --plan-id EXAMPLE-PLAN
""",
        subcommands=[
            {
                'name': 'integrate',
                'help': (
                    'Atomically integrate the worktree-resident plan into main '
                    '(lock → fold-logs → move-back → regenerate → release)'
                ),
                'handler': run_integrate_into_main,
                'args': [
                    {
                        'flags': ['--plan-id'],
                        'dest': 'plan_id',
                        'required': True,
                        'help': 'Plan identifier (mandatory)',
                    },
                ],
            },
        ],
    )
    args = parser.parse_args()
    return print_toon(args.func(args))


if __name__ == '__main__':
    sys.exit(safe_main(main))

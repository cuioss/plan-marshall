#!/usr/bin/env python3
"""
Lifecycle command handlers for manage-status: create, transition, archive, delete-plan.
"""

import argparse
import shutil
import subprocess
from typing import Any

from _handshake_commands import cmd_verify  # type: ignore[import-not-found]
from _invariants import _BLOCKING_BOUNDARIES  # type: ignore[import-not-found]
from _references_core import read_references, write_references  # type: ignore[import-not-found]
from _short_description import derive_short_description  # type: ignore[import-not-found]
from _status_core import (
    get_archive_dir,
    get_status_path,
    log_entry,
    now_utc_iso,
    require_status,
    require_valid_plan_id,
    write_status,
)
from constants import (  # type: ignore[import-not-found]
    PHASE_STATUS_DONE,
    PHASE_STATUS_IN_PROGRESS,
    PHASE_STATUS_PENDING,
)
from file_ops import get_plan_dir  # type: ignore[import-not-found]

# Result-status values that indicate the strict-verify gate refuses to advance.
# Mirrors the ``--strict`` exit-1 conditions in ``phase_handshake.py`` main()
# so the inline guard in ``cmd_transition`` and the CLI exit-code wrapper in
# ``manage_status.py`` main() treat the same situations as boundary refusals.
# Single source of truth — both consumers import this name; do not duplicate
# the literal set.
VERIFY_REFUSAL_ERRORS = frozenset({
    'worktree_unresolved',
    'worktree_metadata_drift',
    'main_checkout_dirtied_during_plan',
})


def verify_blocks_transition(verify_result: dict) -> bool:
    """Return True when a cmd_verify result MUST block the transition.

    Consumed by both ``cmd_transition`` (refuse to mutate state) and
    ``manage_status.py`` main() (exit 1) so the in-process refusal and the
    CLI exit-code contract stay in lockstep.
    """
    if verify_result.get('status') == 'drift':
        return True
    return verify_result.get('error') in VERIFY_REFUSAL_ERRORS


def cmd_create(args: argparse.Namespace) -> dict:
    """Create status.json for a new plan.

    When the plan runs in an isolated worktree, the caller MUST pass
    ``--use-worktree``, ``--worktree-path``, and ``--worktree-branch``
    so the trio is seeded into ``status.metadata`` at creation time.
    Downstream consumers (build wrappers, phase-entry assertions,
    ``get-worktree-path``) read these fields without re-deriving the
    path from filesystem layout.

    When ``--use-worktree`` is omitted (or set to ``false``), no
    worktree metadata is written and the plan is treated as running
    against the main checkout.
    """
    require_valid_plan_id(args)

    path = get_status_path(args.plan_id)
    if path.exists() and not args.force:
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'file_exists',
            'message': 'status.json already exists. Use --force to overwrite.',
        }

    # Parse phases from comma-separated argument
    phases = [p.strip() for p in args.phases.split(',') if p.strip()]
    if not phases:
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'invalid_phases',
            'message': 'At least one phase is required',
        }

    # Worktree metadata seeding — when use-worktree is true, both
    # worktree-path and worktree-branch must be supplied. Refusing
    # partial input prevents silently-incoherent metadata.
    use_worktree = bool(getattr(args, 'use_worktree', False))
    worktree_path_arg = getattr(args, 'worktree_path', None)
    worktree_branch_arg = getattr(args, 'worktree_branch', None)
    if use_worktree and (not worktree_path_arg or not worktree_branch_arg):
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'invalid_worktree_args',
            'message': '--use-worktree requires both --worktree-path and --worktree-branch',
        }

    now = now_utc_iso()

    status: dict[str, Any] = {
        'title': args.title,
        'short_description': derive_short_description(args.title),
        'current_phase': phases[0],
        'phases': [{'name': p, 'status': PHASE_STATUS_PENDING} for p in phases],
        'created': now,
        'updated': now,
    }
    # Mark first phase as in_progress
    status['phases'][0]['status'] = PHASE_STATUS_IN_PROGRESS

    if use_worktree:
        status['metadata'] = {
            'use_worktree': True,
            'worktree_path': worktree_path_arg,
            'worktree_branch': worktree_branch_arg,
        }
    else:
        # Explicit false-state seeding: even when no worktree is
        # allocated, downstream consumers benefit from a definite
        # ``use_worktree: false`` marker rather than having to treat
        # absence-of-metadata as "main-checkout". Keeps the contract
        # symmetric.
        status['metadata'] = {'use_worktree': False}

    write_status(args.plan_id, status)

    result: dict[str, Any] = {
        'status': 'success',
        'plan_id': args.plan_id,
        'file': 'status.json',
        'created': True,
        'plan': {'title': args.title, 'current_phase': phases[0]},
        'use_worktree': use_worktree,
    }
    if use_worktree:
        result['worktree_path'] = worktree_path_arg
        result['worktree_branch'] = worktree_branch_arg
    return result


def _collect_modified_files(plan_id: str, status: dict, base_branch: str) -> list[str] | None:
    """Collect modified files via git when completing 5-execute.

    Phase-5-execute completes before ``commit-push`` runs, so feature commits
    do not yet exist on HEAD.  Two git probes capture the pending work:

    * ``git diff --name-only {base_branch}`` — modifications to tracked files
      relative to the base branch (includes staged and unstaged edits).
    * ``git ls-files --others --exclude-standard`` — newly created files that
      are not yet tracked (new source files, new tests, etc.).

    The union of both probes is the complete set of files modified during
    the execute phase.  When the plan runs inside a worktree
    (``metadata.worktree_path`` is set), ``git -C {worktree_path}`` is used so
    both probes are resolved against the correct working tree.

    Returns:
        Sorted list of relative file paths, or ``None`` on any error.
    """
    metadata = status.get('metadata', {})
    worktree_path = metadata.get('worktree_path')

    base_cmd: list[str] = ['git']
    if worktree_path:
        base_cmd.extend(['-C', worktree_path])

    diff_cmd = [*base_cmd, 'diff', '--name-only', base_branch]
    untracked_cmd = [*base_cmd, 'ls-files', '--others', '--exclude-standard']

    try:
        diff_result = subprocess.run(diff_cmd, capture_output=True, text=True, check=True, timeout=30)  # noqa: S603
        untracked_result = subprocess.run(
            untracked_cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=30,  # noqa: S603
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return None

    collected: set[str] = set()
    for line in diff_result.stdout.splitlines():
        entry = line.strip()
        if entry:
            collected.add(entry)
    for line in untracked_result.stdout.splitlines():
        entry = line.strip()
        if entry:
            collected.add(entry)
    return sorted(collected)


def cmd_transition(args: argparse.Namespace) -> dict | None:
    """Transition to next phase."""
    status = require_status(args)
    if status is None:
        return None

    phases = status.get('phases', [])
    phase_names = [p['name'] for p in phases]

    if args.completed not in phase_names:
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'invalid_phase',
            'message': f'Invalid phase: {args.completed}',
        }

    completed_idx = phase_names.index(args.completed)

    # Determine next phase early so the guard below can inspect it before any
    # state mutation. The standalone ``cmd_transition`` later computes the same
    # value after marking the completed phase done, but the inline guard MUST
    # see ``next_phase`` first to decide whether the strict-verify gate fires.
    if completed_idx + 1 < len(phase_names):
        next_phase: str | None = phase_names[completed_idx + 1]
    else:
        next_phase = None

    # Inline strict-verify guard for guarded boundaries — folds the
    # ``phase_handshake verify --phase {completed} --strict`` step that
    # workflow docs used to issue separately into the transition itself.
    # When ``next_phase`` is in ``_BLOCKING_BOUNDARIES`` (currently
    # ``{'6-finalize'}``), re-run the verify code path against the captured
    # baseline for the completed phase. On drift (or any of the three
    # worktree-/main-checkout boundary refusals listed in
    # ``VERIFY_REFUSAL_ERRORS``) return the verify result unchanged and
    # SKIP ``write_status`` so ``current_phase`` stays on the completed
    # phase. Non-guarded transitions are unaffected — they keep today's
    # behaviour with no verify invoked.
    if next_phase in _BLOCKING_BOUNDARIES:
        verify_args = argparse.Namespace(
            plan_id=args.plan_id,
            phase=args.completed,
            strict=True,
        )
        verify_result = cmd_verify(verify_args)
        if verify_blocks_transition(verify_result):
            return verify_result

    # Mark completed phase as done
    phases[completed_idx]['status'] = PHASE_STATUS_DONE

    # Collect modified files when completing 5-execute
    if args.completed == '5-execute':
        refs = read_references(args.plan_id)
        if refs and (base_branch := refs.get('base_branch')):
            modified = _collect_modified_files(args.plan_id, status, base_branch)
            if modified is not None:
                # WHY: An empty git diff at phase-completion can mean the
                # branch already merged its commits upstream (e.g. squash
                # merge resets the diff to empty). Overwriting a
                # previously-populated ``modified_files`` with [] would
                # destroy the audit trail downstream consumers
                # (plan-retrospective, finalize) rely on. Preserve the
                # existing list whenever the new diff is empty AND we have
                # a prior non-empty value; only replace when the diff has
                # entries or the prior value is absent/empty.
                existing = refs.get('modified_files') or []
                if modified or not existing:
                    refs['modified_files'] = modified
                    write_references(args.plan_id, refs)

    # Apply the next-phase mutation. ``next_phase`` was resolved earlier so
    # the inline strict-verify guard could decide whether to fire — here we
    # only need to perform the state changes that follow from it.
    if next_phase is not None:
        phases[completed_idx + 1]['status'] = PHASE_STATUS_IN_PROGRESS
        status['current_phase'] = next_phase
    else:
        # Last phase completed — set the post-finalize sentinel so dormant
        # consumers (phase-6-finalize SKILL.md "current_phase: complete"
        # check, planning.md cleanup --filter complete) start matching.
        # Mirrors cmd_archive's atomic-archive behavior so the two verbs
        # produce the same end-state.
        status['current_phase'] = 'complete'

    write_status(args.plan_id, status)

    result: dict[str, Any] = {'status': 'success', 'plan_id': args.plan_id, 'completed_phase': args.completed}
    if next_phase:
        result['next_phase'] = next_phase
    else:
        result['message'] = 'All phases completed'

    return result


def cmd_archive(args: argparse.Namespace) -> dict | None:
    """Archive a completed plan.

    Atomically closes the active phase before moving the plan directory:
    marks the active phase ``done``, and when every phase is done sets
    ``current_phase = 'complete'``. Mirrors cmd_transition so an archived
    status.json reflects a fully-closed plan instead of being frozen at the
    last phase's in_progress state.
    """
    require_valid_plan_id(args)

    plan_dir = get_plan_dir(args.plan_id)
    if not plan_dir.exists():
        return {'status': 'error', 'plan_id': args.plan_id, 'error': 'not_found', 'message': 'Plan directory not found'}

    date_prefix = now_utc_iso()[:10]  # YYYY-MM-DD
    archive_name = f'{date_prefix}-{args.plan_id}'
    archive_dir = get_archive_dir()
    archive_path = archive_dir / archive_name

    if args.dry_run:
        return {'status': 'success', 'plan_id': args.plan_id, 'dry_run': True, 'would_archive_to': str(archive_path)}

    # Atomic phase close: load status, mark the active phase done, set the
    # post-finalize sentinel when all phases are complete, then write back
    # to the live plan directory BEFORE the shutil.move. This guarantees the
    # archived status.json reflects the closed state — historically this
    # was attempted via a follow-up `transition --completed 6-finalize`
    # call, but that always failed because shutil.move had already
    # invalidated the live path.
    status = require_status(args)
    if status is None:
        # Plan dir exists but status.json is missing/unreadable. Fail
        # loudly via require_status's error contract instead of moving the
        # broken plan into the archive — silent archives mask data loss.
        return None
    phases = status.get('phases', [])
    active_idx = next(
        (i for i, p in enumerate(phases) if p.get('status') != PHASE_STATUS_DONE),
        None,
    )
    if active_idx is not None:
        phases[active_idx]['status'] = PHASE_STATUS_DONE
    if all(p.get('status') == PHASE_STATUS_DONE for p in phases):
        status['current_phase'] = 'complete'
    write_status(args.plan_id, status)

    archive_dir.mkdir(parents=True, exist_ok=True)
    shutil.move(str(plan_dir), str(archive_path))

    return {'status': 'success', 'plan_id': args.plan_id, 'archived_to': str(archive_path)}


def _restore_lesson_from_plan_dir(plan_id: str, plan_dir: Any) -> tuple[bool, list[str]]:
    """Scan ``plan_dir`` for lesson-{id}.md files and move each one back to the
    global lessons-learned directory.

    Returns ``(restored_any, lesson_ids)`` — ``restored_any=False, lesson_ids=[]``
    when nothing was restored (no lesson files, plan dir missing). When the plan
    directory contains multiple ``lesson-*.md`` files (e.g., a plan derived from
    consolidating several lessons), every file is restored; per-file skips
    (destination collision, path-traversal id) are silently dropped from the
    returned list so the caller sees only the ids that successfully landed back
    in ``lessons-learned/``. ``restored_any`` is ``True`` iff at least one file
    was restored.
    """
    from file_ops import base_path  # type: ignore[import-not-found]

    if not plan_dir.exists():
        return False, []

    matches = sorted(plan_dir.glob('lesson-*.md'))
    if not matches:
        return False, []

    lessons_dir = base_path('lessons-learned').resolve()
    lessons_dir.mkdir(parents=True, exist_ok=True)

    restored_ids: list[str] = []
    for match in matches:
        source = match.resolve()
        lesson_id = source.stem[len('lesson-'):]
        if any(sep in lesson_id for sep in ('/', '\\', '..')):
            continue

        destination = (lessons_dir / f'{lesson_id}.md').resolve()
        if destination.parent != lessons_dir or destination.exists():
            continue

        shutil.move(str(source), str(destination))
        log_entry(
            'work',
            plan_id,
            'INFO',
            f'[RESTORE] (plan-marshall:manage-status:delete-plan) Restored lesson file '
            f'lesson-{lesson_id}.md to .plan/local/lessons-learned/{lesson_id}.md before '
            'plan-dir deletion',
        )
        restored_ids.append(lesson_id)

    return bool(restored_ids), restored_ids


def cmd_delete_plan(args: argparse.Namespace) -> dict:
    """Delete an entire plan directory."""
    require_valid_plan_id(args)

    plan_dir = get_plan_dir(args.plan_id)

    if not plan_dir.exists():
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'plan_not_found',
            'message': f'Plan directory does not exist: {plan_dir}',
        }

    # Auto-restore moved lesson files (default behaviour; opt-out via
    # ``--no-restore-lessons``). Plans derived from multiple lessons can
    # carry more than one ``lesson-*.md`` file; restore them all.
    lesson_restored = False
    restored_lesson_ids: list[str] = []
    if not getattr(args, 'no_restore_lessons', False):
        lesson_restored, restored_lesson_ids = _restore_lesson_from_plan_dir(args.plan_id, plan_dir)

    # Count files before deletion for audit trail
    files_removed = sum(1 for _ in plan_dir.rglob('*') if _.is_file())

    try:
        shutil.rmtree(plan_dir)
        log_entry('work', args.plan_id, 'INFO', f'[MANAGE-STATUS] Deleted plan ({files_removed} files)')
        result: dict[str, Any] = {
            'status': 'success',
            'plan_id': args.plan_id,
            'action': 'deleted',
            'path': str(plan_dir),
            'files_removed': files_removed,
            'lesson_restored': lesson_restored,
        }
        if restored_lesson_ids:
            result['restored_lesson_ids'] = restored_lesson_ids
        return result
    except PermissionError as e:
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'permission_denied',
            'message': f'Permission denied: {e}',
        }
    except Exception as e:
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'delete_failed',
            'message': f'Failed to delete plan directory: {e}',
        }

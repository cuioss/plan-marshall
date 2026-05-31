#!/usr/bin/env python3
"""Write-back reconcile-files verb for manage-references.

Recomputes ``references.modified_files`` from the plan-branch-only diff and
PERSISTS the reconciled set. This is the write-back counterpart of the
read-only ``diff-files`` verb: both share the three-dot + porcelain-union
primitive (``compute_plan_branch_diff`` in ``_references_core``), but
``reconcile-files`` writes the intersected set back to references.json whereas
``diff-files`` never mutates state.

The reconciliation drops ledger entries that are absent from the live
plan-branch-only set — these are the absorbed-upstream files that polluted the
ledger after an absorb merge (phase-5-execute self-absorb or baseline-reconcile
focused auto-merge). After this verb runs, downstream finalize consumers read a
clean footprint that contains only files the plan actually touched.
"""

from pathlib import Path

from _references_core import (
    _run_git,
    read_references,
    reconcile_modified_files,
    resolve_base_ref,
)
from input_validation import require_valid_plan_id  # type: ignore[import-not-found]


def cmd_reconcile_files(args) -> dict:
    """Recompute and persist modified_files from the plan-branch-only diff.

    Write-back counterpart of ``diff-files``. Error contract is identical to
    ``diff-files`` (``worktree_not_found``, ``references_not_found``,
    ``not_a_git_worktree``).
    """
    require_valid_plan_id(args)

    worktree = Path(args.worktree_path)
    if not worktree.exists() or not worktree.is_dir():
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'worktree_not_found',
            'message': f'Worktree path does not exist or is not a directory: {args.worktree_path}',
        }

    refs = read_references(args.plan_id)
    if not refs:
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'references_not_found',
            'message': 'references.json not found',
        }

    rev_parse = _run_git(worktree, ['rev-parse', '--git-dir'])
    if rev_parse.returncode != 0:
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'not_a_git_worktree',
            'message': f'Path is not inside a git worktree: {args.worktree_path}',
        }

    base_ref = resolve_base_ref(getattr(args, 'base_ref', None), refs)
    return reconcile_modified_files(args.plan_id, worktree, base_ref)

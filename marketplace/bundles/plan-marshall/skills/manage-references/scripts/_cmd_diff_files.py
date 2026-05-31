#!/usr/bin/env python3
"""Read-only diff-files query for manage-references.

Intersects the append-only intent ledger (``references.json:modified_files``)
with the live git working-tree state so consumers operate on
"actually-modified-now" paths instead of trusting a potentially stale ledger.

This handler is read-only: it never mutates ``references.json``. The write-back
counterpart is the ``reconcile-files`` verb (``_cmd_reconcile_files.py``); both
verbs share the three-dot + porcelain-union primitive
(``compute_plan_branch_diff`` in ``_references_core``).

Resolution rule:
    files     = ledger ∩ live, in ledger order
    dropped[] = ledger entries no longer present in live
    phantom[] = live entries that were never recorded in the ledger

Where ``live`` is the union of:
    - ``git -C {worktree_path} diff --name-only {base_ref}...HEAD``
    - parsed paths from ``git -C {worktree_path} status --porcelain``
"""

from pathlib import Path

from _references_core import (
    _run_git,
    compute_plan_branch_diff,
    read_references,
    resolve_base_ref,
)
from input_validation import require_valid_plan_id  # type: ignore[import-not-found]


def cmd_diff_files(args) -> dict:
    """Return ledger ∩ live working-tree set, with drift accounting.

    Read-only — never writes references.json.
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
    ledger: list[str] = list(refs.get('modified_files', []))

    live_set = compute_plan_branch_diff(worktree, base_ref)
    ledger_set = set(ledger)

    files: list[str] = [path for path in ledger if path in live_set]
    dropped = [{'path': path, 'reason': 'not_in_working_tree'} for path in ledger if path not in live_set]
    phantom = sorted(live_set - ledger_set)

    return {
        'status': 'success',
        'plan_id': args.plan_id,
        'base_ref': base_ref,
        'files': files,
        'references_count': len(ledger),
        'live_count': len(live_set),
        'dropped': dropped,
        'phantom': phantom,
    }

#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Read-only compute-footprint query for manage-references.

Derives the plan's actual footprint live from the worktree git state — the
union of the three-dot ``{base_ref}...HEAD`` diff and the porcelain working-tree
state — without consulting any persisted ledger. The footprint is computed
on-demand from the worktree, which is the single source of truth.

This handler is read-only: it never mutates ``references.json``. It reads
``references.json`` only to resolve ``base_branch`` for the diff range.

Resolution rule:
    files = sorted live footprint set

Where ``live`` is the union of:
    - ``git -C {worktree_path} diff --name-only {base_ref}...HEAD``
    - parsed paths from ``git -C {worktree_path} status --porcelain``
"""

import argparse
import subprocess
from pathlib import Path

from _references_core import (
    _run_git,
    compute_plan_branch_diff,
    read_references,
    resolve_base_ref,
)
from input_validation import require_valid_plan_id  # type: ignore[import-not-found]


def cmd_compute_footprint(args: argparse.Namespace) -> dict:
    """Return the live plan-branch-only footprint set.

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
    try:
        live_set = compute_plan_branch_diff(worktree, base_ref)
    except subprocess.CalledProcessError as exc:
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'git_error',
            'message': f'Failed to compute plan branch diff: {exc}',
        }
    files = sorted(live_set)

    return {
        'status': 'success',
        'plan_id': args.plan_id,
        'base_ref': base_ref,
        'files': files,
        'live_count': len(files),
    }

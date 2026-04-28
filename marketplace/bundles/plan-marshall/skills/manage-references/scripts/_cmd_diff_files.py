#!/usr/bin/env python3
"""Read-only diff-files query for manage-references.

Intersects the append-only intent ledger (``references.json:modified_files``)
with the live git working-tree state so consumers operate on
"actually-modified-now" paths instead of trusting a potentially stale ledger.

This handler is read-only: it never mutates ``references.json``.

Resolution rule:
    files     = ledger ∩ live, in ledger order
    dropped[] = ledger entries no longer present in live
    phantom[] = live entries that were never recorded in the ledger

Where ``live`` is the union of:
    - ``git -C {worktree_path} diff --name-only {base_ref}...HEAD``
    - parsed paths from ``git -C {worktree_path} status --porcelain``
"""

import subprocess
from pathlib import Path

from _references_core import read_references
from input_validation import require_valid_plan_id  # type: ignore[import-not-found]


def _run_git(worktree: Path, args: list[str]) -> subprocess.CompletedProcess:
    """Run a git command anchored to ``worktree`` and return the completed process."""
    return subprocess.run(
        ['git', '-C', str(worktree), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def _parse_porcelain(stdout: str) -> list[str]:
    """Parse ``git status --porcelain`` output into a list of paths.

    Porcelain format: two-character status code, a space, then the path.
    Renames have the form ``R  old -> new``; both old and new are surfaced.
    """
    paths: list[str] = []
    for raw in stdout.splitlines():
        if not raw:
            continue
        # Porcelain v1: bytes 0..1 = status, byte 2 = space, byte 3.. = path(s).
        if len(raw) < 4:
            continue
        payload = raw[3:]
        if ' -> ' in payload:
            old, new = payload.split(' -> ', 1)
            paths.append(old.strip().strip('"'))
            paths.append(new.strip().strip('"'))
        else:
            paths.append(payload.strip().strip('"'))
    return paths


def _resolve_base_ref(args, refs: dict) -> str:
    """Resolve --base-ref, falling back to references.base_branch then 'main'."""
    explicit = getattr(args, 'base_ref', None)
    if explicit:
        return str(explicit)
    base_branch = refs.get('base_branch')
    if base_branch:
        return str(base_branch)
    return 'main'


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

    base_ref = _resolve_base_ref(args, refs)
    ledger: list[str] = list(refs.get('modified_files', []))

    diff_proc = _run_git(worktree, ['diff', '--name-only', f'{base_ref}...HEAD'])
    diff_paths = [line for line in diff_proc.stdout.splitlines() if line]

    # ``--untracked-files=all`` is critical: with the default mode
    # (``--untracked-files=normal``) git collapses untracked directories into
    # a single ``?? src/`` entry, hiding individual file paths. The ledger
    # records files, so we need files-level visibility to intersect correctly.
    status_proc = _run_git(worktree, ['status', '--porcelain', '--untracked-files=all'])
    status_paths = _parse_porcelain(status_proc.stdout)

    live_set = set(diff_paths) | set(status_paths)
    ledger_set = set(ledger)

    files: list[str] = [path for path in ledger if path in live_set]
    dropped = [
        {'path': path, 'reason': 'not_in_working_tree'}
        for path in ledger
        if path not in live_set
    ]
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

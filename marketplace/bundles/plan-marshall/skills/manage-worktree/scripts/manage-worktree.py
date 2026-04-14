#!/usr/bin/env python3
"""
Manage per-plan git worktrees.

Worktrees are rooted at ``<project_root>/.claude/worktrees/{plan-id}/`` —
the canonical Claude Code worktree location. Anchoring worktrees inside
the main git checkout means project-level permission allow-lists, IDE
indexing, and ``.worktreeinclude`` copying all work without per-host
customization. All plan-marshall runtime state lives under
``<root>/.plan/local/`` in the main checkout, reached via
``file_ops.get_base_dir()``.

After ``git worktree add``, the create path links the worktree's ``.plan``
directly at the main checkout's ``.plan`` via a symlink, so the tracked
config, the executor, and runtime state are shared across every worktree.
Running ``python3 .plan/execute-script.py ...`` from inside a worktree
invokes the exact same executor as the main checkout.

Subcommands:
  path    - Return the computed worktree path for a plan
  create  - Create a worktree + feature branch + .plan symlink
  remove  - Remove a worktree (non-force by default)
  list    - Enumerate worktrees known to git under the worktree root

Output: TOON format.
"""

import argparse
import os
import subprocess
from pathlib import Path

from file_ops import (  # type: ignore[import-not-found]
    get_worktree_root,
    output_toon,
    output_toon_error,
    safe_main,
)
from input_validation import add_plan_id_arg  # type: ignore[import-not-found]
from marketplace_paths import git_main_checkout_root  # type: ignore[import-not-found]

PLAN_DIR_NAME = os.environ.get('PLAN_DIR_NAME', '.plan')


def _worktrees_root() -> Path:
    return get_worktree_root()


def _worktree_path(plan_id: str) -> Path:
    return _worktrees_root() / plan_id


def _run_git(args: list[str]) -> tuple[int, str, str]:
    result = subprocess.run(
        ['git', *args],
        capture_output=True,
        text=True,
        timeout=60,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def _ensure_worktree_plan_symlink(worktree: Path) -> tuple[bool, str]:
    """Link ``{worktree}/.plan`` to the main checkout's ``.plan`` directory.

    Idempotent:
    - If the link already points at the expected target, returns success.
    - If ``.plan`` exists as a stale symlink, replaces it.
    - If ``.plan`` exists as an empty directory (e.g. created incidentally
      by tooling), removes it and creates the symlink.
    - If ``.plan`` exists as a non-empty directory, refuses — this would
      clobber real user data.

    Returns ``(success, error_message)``.
    """
    main_root = git_main_checkout_root()
    if main_root is None:
        return False, 'cannot resolve main git checkout root for .plan symlink'
    target_plan = (main_root / PLAN_DIR_NAME).resolve()
    link_path = worktree / PLAN_DIR_NAME

    if link_path.is_symlink():
        try:
            if link_path.resolve() == target_plan:
                return True, ''
        except OSError:
            pass
        link_path.unlink()
    elif link_path.exists():
        # Plain directory (or file). git worktree add never creates .plan,
        # so this is almost certainly empty — but guard against data loss.
        if link_path.is_dir():
            contents = list(link_path.iterdir())
            if contents:
                return False, (
                    f'{link_path} exists as a non-empty directory; refusing to '
                    'replace with symlink'
                )
            link_path.rmdir()
        else:
            return False, f'{link_path} exists and is not a directory; refusing to replace'

    try:
        os.symlink(target_plan, link_path, target_is_directory=True)
    except OSError as exc:
        return False, f'failed to create .plan symlink: {exc}'
    return True, ''


def cmd_path(args: argparse.Namespace) -> None:
    path = _worktree_path(args.plan_id)
    output_toon(
        {
            'status': 'success',
            'plan_id': args.plan_id,
            'worktree_path': str(path),
            'exists': path.is_dir(),
        }
    )


def cmd_create(args: argparse.Namespace) -> None:
    target = _worktree_path(args.plan_id)
    if target.exists():
        output_toon_error(
            'worktree_exists',
            f'Worktree already exists: {target}',
            plan_id=args.plan_id,
            worktree_path=str(target),
        )
        return
    target.parent.mkdir(parents=True, exist_ok=True)

    git_args = ['worktree', 'add']
    if args.base:
        git_args += ['-b', args.branch, str(target), args.base]
    else:
        git_args += ['-b', args.branch, str(target)]
    rc, _out, err = _run_git(git_args)
    if rc != 0:
        output_toon_error(
            'worktree_add_failed',
            f'git worktree add failed: {err}',
            plan_id=args.plan_id,
            branch=args.branch,
        )
        return

    ok, link_err = _ensure_worktree_plan_symlink(target)
    if not ok:
        output_toon_error(
            'plan_symlink_failed',
            f'Worktree created but .plan symlink failed: {link_err}',
            plan_id=args.plan_id,
            worktree_path=str(target),
        )
        return

    output_toon(
        {
            'status': 'success',
            'plan_id': args.plan_id,
            'worktree_path': str(target),
            'branch': args.branch,
            'plan_symlink': str(target / PLAN_DIR_NAME),
        }
    )


def cmd_remove(args: argparse.Namespace) -> None:
    target = _worktree_path(args.plan_id)
    if not target.exists():
        output_toon(
            {
                'status': 'success',
                'plan_id': args.plan_id,
                'worktree_path': str(target),
                'action': 'noop',
                'message': 'Worktree does not exist',
            }
        )
        return

    git_args = ['worktree', 'remove', str(target)]
    if args.force:
        git_args.append('--force')
    rc, _out, err = _run_git(git_args)
    if rc != 0:
        output_toon_error(
            'worktree_remove_failed',
            f'git worktree remove failed: {err}',
            plan_id=args.plan_id,
            worktree_path=str(target),
            hint='Pass --force only after verifying the worktree is clean.',
        )
        return
    output_toon(
        {
            'status': 'success',
            'plan_id': args.plan_id,
            'worktree_path': str(target),
            'action': 'removed',
        }
    )


def cmd_list(_args: argparse.Namespace) -> None:
    rc, out, err = _run_git(['worktree', 'list', '--porcelain'])
    if rc != 0:
        output_toon_error('git_list_failed', err)
        return
    root = _worktrees_root().resolve()
    entries: list[dict] = []
    current: dict = {}
    for line in out.splitlines():
        if line.startswith('worktree '):
            if current.get('path'):
                entries.append(current)
            current = {'path': line[len('worktree ') :].strip()}
        elif line.startswith('branch '):
            current['branch'] = line[len('branch ') :].strip().removeprefix('refs/heads/')
        elif line == '':
            if current.get('path'):
                entries.append(current)
                current = {}
    if current.get('path'):
        entries.append(current)

    managed = []
    for entry in entries:
        p = Path(entry['path']).resolve()
        try:
            rel = p.relative_to(root)
        except ValueError:
            continue
        parts = rel.parts
        if len(parts) != 1:
            continue
        managed.append(
            {
                'plan_id': parts[0],
                'path': str(p),
                'branch': entry.get('branch', ''),
            }
        )
    output_toon({'status': 'success', 'worktrees_root': str(root), 'count': len(managed), 'worktrees': managed})


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Manage per-plan git worktrees')
    sub = parser.add_subparsers(dest='command', required=True)

    p_path = sub.add_parser('path', help='Return computed worktree path for a plan')
    add_plan_id_arg(p_path)
    p_path.set_defaults(func=cmd_path)

    p_create = sub.add_parser('create', help='Create worktree + feature branch + shim drop')
    add_plan_id_arg(p_create)
    p_create.add_argument('--branch', required=True, help='Feature branch name to create')
    p_create.add_argument('--base', help='Base ref for the new branch (default: current HEAD)')
    p_create.set_defaults(func=cmd_create)

    p_remove = sub.add_parser('remove', help='Remove a worktree')
    add_plan_id_arg(p_remove)
    p_remove.add_argument('--force', action='store_true', help='Force removal (use only if worktree is clean)')
    p_remove.set_defaults(func=cmd_remove)

    p_list = sub.add_parser('list', help='List managed worktrees')
    p_list.set_defaults(func=cmd_list)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)
    return 0


if __name__ == '__main__':
    safe_main(main)()

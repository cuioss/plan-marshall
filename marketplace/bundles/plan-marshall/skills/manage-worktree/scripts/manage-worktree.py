#!/usr/bin/env python3
"""
Manage per-plan git worktrees.

Worktrees are rooted at ``{base_dir}/worktrees/{plan-id}/`` where
``base_dir`` is the per-project global directory (``~/.plan-marshall/
{project}/``). The shim dropped into each worktree's ``.plan/`` resolves
back to the same main-checkout executor via ``git rev-parse
--git-common-dir``, so running ``python3 .plan/execute-script.py ...``
inside a worktree is functionally identical to running it in the main
checkout.

Subcommands:
  path    - Return the computed worktree path for a plan
  create  - Create a worktree + feature branch + shim drop
  remove  - Remove a worktree (non-force by default)
  list    - Enumerate worktrees known to git under the global dir

Output: TOON format.
"""

import argparse
import os
import subprocess
from pathlib import Path

from file_ops import get_base_dir, output_toon, output_toon_error, safe_main  # type: ignore[import-not-found]
from input_validation import add_plan_id_arg  # type: ignore[import-not-found]

WORKTREES_SUBDIR = 'worktrees'
PLAN_DIR_NAME = os.environ.get('PLAN_DIR_NAME', '.plan')


def _worktrees_root() -> Path:
    return get_base_dir() / WORKTREES_SUBDIR


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


def _run_generate_executor_write_shim(target: Path) -> tuple[bool, str]:
    """Invoke generate_executor write-shim via the executor to drop a shim into target/.plan/.

    Uses the currently-active executor (via the shim in the CURRENT checkout)
    rather than re-implementing shim writing here. This guarantees every
    worktree gets the canonical shim template.
    """
    # Locate generate_executor.py alongside this script's sibling skill.
    script_dir = Path(__file__).resolve().parent.parent.parent
    gen = script_dir / 'tools-script-executor' / 'scripts' / 'generate_executor.py'
    if not gen.is_file():
        return False, f'generate_executor.py not found at {gen}'
    result = subprocess.run(
        ['python3', str(gen), 'write-shim', '--target', str(target)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        return False, result.stderr.strip() or result.stdout.strip()
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

    ok, shim_err = _run_generate_executor_write_shim(target)
    if not ok:
        output_toon_error(
            'shim_write_failed',
            f'Worktree created but shim drop failed: {shim_err}',
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
            'shim_path': str(target / PLAN_DIR_NAME / 'execute-script.py'),
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
            if current:
                entries.append(current)
            current = {'path': line[len('worktree ') :]}
        elif line.startswith('branch '):
            current['branch'] = line[len('branch ') :].removeprefix('refs/heads/')
        elif line == '':
            if current:
                entries.append(current)
                current = {}
    if current:
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

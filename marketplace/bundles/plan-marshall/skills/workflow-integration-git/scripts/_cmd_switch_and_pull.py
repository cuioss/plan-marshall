"""switch-and-pull verb for git-workflow.py.

Checks out ``--base`` on the supplied project directory and then pulls
from ``origin`` using the explicit form ``git pull origin {base_branch}``
(never the implicit plain ``git pull`` — Drift 1 resolution in design.md §4).

Design contract: §3.2 and §5.2 of design.md.

Primary path  (``--plan-id``): resolves the project directory (main checkout)
              from ``manage-status get-worktree-path``.
Escape hatch  (``--project-dir``): uses the supplied path directly. Useful
              in post-cleanup scenarios or non-plan contexts where the
              caller already knows the main checkout path.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from git_provider import run_git  # type: ignore[import-not-found]

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _find_executor() -> Path | None:
    """Locate ``.plan/execute-script.py`` relative to the main checkout."""
    try:
        from marketplace_paths import git_main_checkout_root  # type: ignore[import-not-found]
        root = git_main_checkout_root()
        if root is None:
            return None
        candidate = root / '.plan' / 'execute-script.py'
        return candidate if candidate.exists() else None
    except ImportError:
        return None


def _resolve_project_dir(args) -> tuple[Path | None, dict | None]:
    """Resolve the project directory from --plan-id or --project-dir.

    Returns ``(path, None)`` on success or ``(None, error_dict)`` on failure.
    The resolved path is used as the ``git -C`` target for all operations.
    """
    plan_id: str | None = getattr(args, 'plan_id', None)
    project_dir_arg: str | None = getattr(args, 'project_dir', None)

    envelope = {'operation': 'switch-and-pull'}
    if plan_id:
        envelope['plan_id'] = plan_id
    if project_dir_arg:
        envelope['project_dir'] = project_dir_arg

    if plan_id:
        executor = _find_executor()
        if executor is None:
            return None, {
                **envelope,
                'status': 'error',
                'error_type': 'plan_not_found',
                'message': 'plan-marshall executor not available (.plan/execute-script.py missing)',
            }

        try:
            result = subprocess.run(
                ['python3', str(executor), 'plan-marshall:manage-status:manage-status',
                 'get-worktree-path', '--plan-id', plan_id],
                capture_output=True,
                text=True,
                timeout=30,
            )
        except FileNotFoundError:
            return None, {
                **envelope,
                'status': 'error',
                'error_type': 'plan_not_found',
                'message': 'python3 not found on PATH',
            }
        except subprocess.TimeoutExpired:
            return None, {
                **envelope,
                'status': 'error',
                'error_type': 'plan_not_found',
                'message': 'manage-status get-worktree-path timed out',
            }

        if result.returncode != 0:
            return None, {
                **envelope,
                'status': 'error',
                'error_type': 'plan_not_found',
                'message': (result.stderr or result.stdout).strip() or 'manage-status failed',
            }

        try:
            from toon_parser import parse_toon  # type: ignore[import-not-found]
            parsed = parse_toon(result.stdout)
        except Exception as exc:  # noqa: BLE001
            return None, {
                **envelope,
                'status': 'error',
                'error_type': 'plan_not_found',
                'message': f'failed to parse manage-status output: {exc}',
            }

        if parsed.get('status') == 'error' or parsed.get('error'):
            return None, {
                **envelope,
                'status': 'error',
                'error_type': 'plan_not_found',
                'message': parsed.get('message') or 'plan resolution failed',
            }

        # For switch-and-pull, we operate on the main checkout (not the
        # worktree). The main checkout path is the parent of the worktree
        # root or the ``project_dir`` field returned by manage-status.
        # ``manage-status get-worktree-path`` returns the worktree path when
        # use_worktree is true; for main-checkout flow it returns the project
        # root. We use whatever path is returned as the working directory since
        # the caller of this verb (branch-cleanup.md §7.1) always supplies
        # ``--project-dir {main_checkout}`` explicitly when they know the path.
        # When invoked via ``--plan-id``, the caller does not know the path —
        # we derive the main checkout root from ``marketplace_paths``.
        try:
            from marketplace_paths import git_main_checkout_root  # type: ignore[import-not-found]
            main_root = git_main_checkout_root()
            if main_root is None:
                return None, {
                    **envelope,
                    'status': 'error',
                    'error_type': 'plan_not_found',
                    'message': 'cannot resolve main git checkout root',
                }
            return main_root, None
        except ImportError:
            return None, {
                **envelope,
                'status': 'error',
                'error_type': 'plan_not_found',
                'message': 'marketplace_paths module unavailable',
            }

    elif project_dir_arg:
        return Path(project_dir_arg), None

    else:
        return None, {
            **envelope,
            'status': 'error',
            'error_type': 'missing_required_arg',
            'message': 'one of --plan-id or --project-dir is required',
        }


def _verify_git_repo(path: Path) -> str | None:
    """Return an error message if ``path`` is not a git working tree root."""
    rc, _out, err = run_git(['-C', str(path), 'rev-parse', '--show-toplevel'])
    if rc != 0:
        return f'path is not a git working tree: {err or "rev-parse failed"}'
    return None


# ---------------------------------------------------------------------------
# Public command handler
# ---------------------------------------------------------------------------


def cmd_switch_and_pull(args) -> dict:
    """Handle switch-and-pull subcommand.

    1. Verify the base branch exists on the remote (ls-remote guard).
    2. Capture ``pre_sha`` (HEAD before checkout).
    3. ``git checkout {base_branch}``.
    4. ``git pull origin {base_branch}`` (explicit form — Drift 1 resolution).
    5. Capture ``post_sha`` and compute ``commits_pulled``.
    """
    plan_id: str | None = getattr(args, 'plan_id', None)
    project_dir_arg: str | None = getattr(args, 'project_dir', None)
    base_branch: str = args.base

    project_path, error = _resolve_project_dir(args)
    if error is not None:
        return error

    assert project_path is not None  # narrowing

    envelope: dict = {'operation': 'switch-and-pull'}
    if plan_id:
        envelope['plan_id'] = plan_id
    if project_dir_arg:
        envelope['project_dir'] = project_dir_arg
    envelope['base_branch'] = base_branch

    # Verify path is a git working tree when --project-dir.
    if project_dir_arg:
        err_msg = _verify_git_repo(project_path)
        if err_msg:
            return {
                **envelope,
                'status': 'error',
                'error_type': 'project_dir_not_a_git_repo',
                'message': err_msg,
            }

    # Invariant §5.2.1 — verify base branch exists on remote.
    rc, ls_out, _ls_err = run_git(
        ['-C', str(project_path), 'ls-remote', '--heads', 'origin', base_branch]
    )
    if rc != 0 or not ls_out.strip():
        return {
            **envelope,
            'status': 'error',
            'error_type': 'branch_not_found',
            'message': f'base branch not found on remote: origin/{base_branch}',
        }

    # Invariant §5.2.2 — capture pre_sha.
    rc, pre_sha_out, _err = run_git(['-C', str(project_path), 'rev-parse', 'HEAD'])
    if rc != 0:
        return {
            **envelope,
            'status': 'error',
            'error_type': 'pull_failed',
            'message': f'git rev-parse HEAD failed: {_err.strip()}',
        }
    pre_sha = pre_sha_out.strip()

    # Checkout the base branch.
    rc, _out, err = run_git(['-C', str(project_path), 'checkout', base_branch])
    if rc != 0:
        err_lower = err.lower()
        if 'conflict' in err_lower or 'overwrite' in err_lower or 'uncommitted' in err_lower:
            return {
                **envelope,
                'status': 'error',
                'error_type': 'merge_conflict',
                'pre_sha': pre_sha,
                'message': f'checkout failed due to uncommitted changes: {err.strip()}',
            }
        return {
            **envelope,
            'status': 'error',
            'error_type': 'pull_failed',
            'pre_sha': pre_sha,
            'message': f'git checkout {base_branch} failed: {err.strip()}',
        }

    # Invariant §5.2.3 — explicit pull origin {base_branch}.
    rc, _pull_out, pull_err = run_git(
        ['-C', str(project_path), 'pull', 'origin', base_branch]
    )
    if rc != 0:
        return {
            **envelope,
            'status': 'error',
            'error_type': 'pull_failed',
            'pre_sha': pre_sha,
            'message': f'git pull origin {base_branch} failed: {pull_err.strip() or "non-zero exit"}',
        }

    # Capture post_sha.
    rc, post_sha_out, _err = run_git(['-C', str(project_path), 'rev-parse', 'HEAD'])
    post_sha = post_sha_out.strip() if rc == 0 else ''

    # Invariant §5.2.4 — compute commits_pulled.
    commits_pulled = 0
    if pre_sha and post_sha:
        rc_count, count_out, _err = run_git(
            ['-C', str(project_path), 'rev-list', '--count', f'{pre_sha}..HEAD']
        )
        if rc_count == 0 and count_out.strip().isdigit():
            commits_pulled = int(count_out.strip())

    payload = {
        **envelope,
        'status': 'success',
        'pre_sha': pre_sha,
        'post_sha': post_sha,
        'commits_pulled': commits_pulled,
    }
    return payload

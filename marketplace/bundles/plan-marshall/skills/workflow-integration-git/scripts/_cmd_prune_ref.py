"""prune-local-and-remote-ref verb for git-workflow.py.

Deletes the local feature branch and optionally the remote-tracking ref
``refs/remotes/origin/{head_branch}`` after a PR merge. Consolidates
the three inline git calls (BC-04, BC-05, BC-06) from branch-cleanup.md.

Design contract: §3.2 and §5.3 of design.md.

Two modes:
  ``local_and_remote``  (default) — delete local branch AND remote-tracking ref.
  ``local_only``        — delete only the local branch; skip remote-tracking ref.

Primary path  (``--plan-id``): resolves the project directory and head branch
              from ``manage-status get-worktree-path``.
Escape hatch  (``--project-dir`` + ``--head``): uses the supplied path and
              branch name directly.

Safety invariants (§5.3 of design.md):
1. Never delete the currently checked-out branch.
2. Force-delete (``-D``) — post-merge squash merges make safe-delete refuse.
3. Internal show-ref guard before update-ref -d (Drift 3 resolution).
4. Targeted ref deletion only — no ``git fetch --prune``.
5. ``local_only`` mode skips all remote-tracking ref operations.
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


def _resolve_project_dir_and_head(args) -> tuple[Path | None, str | None, dict | None]:
    """Resolve (project_path, head_branch) from --plan-id or --project-dir + --head.

    Returns ``(path, head, None)`` on success or ``(None, None, error_dict)``
    on failure.
    """
    plan_id: str | None = getattr(args, 'plan_id', None)
    project_dir_arg: str | None = getattr(args, 'project_dir', None)
    head_arg: str | None = getattr(args, 'head', None)

    envelope = {'operation': 'prune-local-and-remote-ref'}
    if plan_id:
        envelope['plan_id'] = plan_id
    if project_dir_arg:
        envelope['project_dir'] = project_dir_arg

    if plan_id:
        executor = _find_executor()
        if executor is None:
            return None, None, {
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
            return None, None, {
                **envelope,
                'status': 'error',
                'error_type': 'plan_not_found',
                'message': 'python3 not found on PATH',
            }
        except subprocess.TimeoutExpired:
            return None, None, {
                **envelope,
                'status': 'error',
                'error_type': 'plan_not_found',
                'message': 'manage-status get-worktree-path timed out',
            }

        if result.returncode != 0:
            return None, None, {
                **envelope,
                'status': 'error',
                'error_type': 'plan_not_found',
                'message': (result.stderr or result.stdout).strip() or 'manage-status failed',
            }

        try:
            from toon_parser import parse_toon  # type: ignore[import-not-found]
            parsed = parse_toon(result.stdout)
        except Exception as exc:  # noqa: BLE001
            return None, None, {
                **envelope,
                'status': 'error',
                'error_type': 'plan_not_found',
                'message': f'failed to parse manage-status output: {exc}',
            }

        if parsed.get('status') == 'error' or parsed.get('error'):
            return None, None, {
                **envelope,
                'status': 'error',
                'error_type': 'plan_not_found',
                'message': parsed.get('message') or 'plan resolution failed',
            }

        head_branch = parsed.get('worktree_branch') or ''
        if not head_branch:
            return None, None, {
                **envelope,
                'status': 'error',
                'error_type': 'worktree_not_materialized',
                'message': 'worktree_branch absent from manage-status response',
            }

        # For prune-local-and-remote-ref, we operate on the main checkout.
        try:
            from marketplace_paths import git_main_checkout_root  # type: ignore[import-not-found]
            main_root = git_main_checkout_root()
            if main_root is None:
                return None, None, {
                    **envelope,
                    'status': 'error',
                    'error_type': 'plan_not_found',
                    'message': 'cannot resolve main git checkout root',
                }
            return main_root, head_branch, None
        except ImportError:
            return None, None, {
                **envelope,
                'status': 'error',
                'error_type': 'plan_not_found',
                'message': 'marketplace_paths module unavailable',
            }

    elif project_dir_arg:
        if not head_arg:
            return None, None, {
                **envelope,
                'status': 'error',
                'error_type': 'missing_required_arg',
                'message': '--head is required when --project-dir is supplied',
            }
        return Path(project_dir_arg), head_arg, None

    else:
        return None, None, {
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


def cmd_prune_ref(args) -> dict:
    """Handle prune-local-and-remote-ref subcommand.

    1. Guard: head_branch is not the currently checked-out branch.
    2. Force-delete the local branch (``git branch -D``).
    3. For ``local_and_remote`` mode:
       a. show-ref guard (Drift 3 resolution) — skip if ref absent.
       b. ``git update-ref -d refs/remotes/origin/{head_branch}``.
    """
    plan_id: str | None = getattr(args, 'plan_id', None)
    project_dir_arg: str | None = getattr(args, 'project_dir', None)
    mode: str = getattr(args, 'mode', 'local_and_remote')

    project_path, head_branch, error = _resolve_project_dir_and_head(args)
    if error is not None:
        return error

    assert project_path is not None and head_branch is not None  # narrowing

    envelope: dict = {'operation': 'prune-local-and-remote-ref'}
    if plan_id:
        envelope['plan_id'] = plan_id
    if project_dir_arg:
        envelope['project_dir'] = project_dir_arg
    envelope['head_branch'] = head_branch
    envelope['mode'] = mode

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

    # Invariant §5.3.1 — guard: never delete the currently checked-out branch.
    rc, current_branch_out, _err = run_git(
        ['-C', str(project_path), 'rev-parse', '--abbrev-ref', 'HEAD']
    )
    current_branch = current_branch_out.strip() if rc == 0 else ''
    if current_branch == head_branch:
        return {
            **envelope,
            'status': 'error',
            'error_type': 'branch_delete_failed',
            'local_deleted': False,
            'message': f'refusing to delete the currently checked-out branch: {head_branch}',
        }

    # Invariant §5.3.2 — force-delete the local branch.
    rc, _out, err = run_git(['-C', str(project_path), 'branch', '-D', head_branch])
    if rc != 0:
        return {
            **envelope,
            'status': 'error',
            'error_type': 'branch_delete_failed',
            'local_deleted': False,
            'message': f'git branch -D {head_branch} failed: {err.strip() or "non-zero exit"}',
        }

    # Invariant §5.3.5 — local_only mode: skip remote-tracking ref operations.
    if mode == 'local_only':
        return {
            **envelope,
            'status': 'success',
            'local_deleted': True,
            'remote_ref_deleted': False,
        }

    # Invariant §5.3.3 — show-ref guard before update-ref -d.
    ref_path = f'refs/remotes/origin/{head_branch}'
    rc_sr, _sr_out, _sr_err = run_git(
        ['-C', str(project_path), 'show-ref', '--quiet', ref_path]
    )

    if rc_sr != 0:
        # Remote-tracking ref is already absent — graceful no-op.
        return {
            **envelope,
            'status': 'partial',
            'local_deleted': True,
            'remote_ref_deleted': False,
            'remote_ref_warning': (
                f'remote-tracking ref {ref_path} was already absent — no-op'
            ),
        }

    # Invariant §5.3.4 — targeted ref deletion only.
    rc_ud, _ud_out, ud_err = run_git(
        ['-C', str(project_path), 'update-ref', '-d', ref_path]
    )
    if rc_ud != 0:
        return {
            **envelope,
            'status': 'error',
            'error_type': 'unexpected_ref_error',
            'local_deleted': True,
            'remote_ref_deleted': False,
            'message': f'update-ref -d failed after show-ref confirmed ref exists: {ud_err.strip()}',
        }

    return {
        **envelope,
        'status': 'success',
        'local_deleted': True,
        'remote_ref_deleted': True,
    }

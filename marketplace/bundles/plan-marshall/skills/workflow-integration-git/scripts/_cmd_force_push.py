"""force-push-with-lease verb for git-workflow.py.

Pushes the plan's feature branch to ``origin`` using ``--force-with-lease``
so concurrent pushes from other sources are detected and rejected cleanly
rather than silently overwriting remote state.

Design contract: §3.2 and §5.1 of design.md.

Primary path  (``--plan-id``): resolves the worktree path and branch name
              from ``manage-status get-worktree-path``.
Escape hatch  (``--project-dir`` + ``--branch``): uses the supplied path as
              the ``git -C`` target and the supplied branch name directly.
              Useful after worktree removal or in non-plan contexts.
"""

from __future__ import annotations

from pathlib import Path

from git_provider import run_git  # type: ignore[import-not-found]

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _verify_git_repo(path: Path) -> str | None:
    """Return an error message if ``path`` is not a git working tree root."""
    rc, _out, err = run_git(['-C', str(path), 'rev-parse', '--show-toplevel'])
    if rc != 0:
        return f'path is not a git working tree: {err or "rev-parse failed"}'
    return None


def _resolve_branch_and_path(args) -> tuple[str | None, Path | None, dict | None]:
    """Resolve (branch, worktree_path) from --plan-id or --project-dir + --branch.

    Returns ``(branch, path, None)`` on success or ``(None, None, error_dict)``
    on failure.
    """
    if getattr(args, 'plan_id', None):
        plan_id: str = args.plan_id
        # Import here to keep the module testable without a live executor.
        try:
            import subprocess

            from git_provider import run_git as _rg  # noqa: F401 — already imported above

            executor = _find_executor()
            if executor is None:
                return None, None, {
                    'status': 'error',
                    'operation': 'force-push-with-lease',
                    'plan_id': plan_id,
                    'error_type': 'plan_not_found',
                    'message': 'plan-marshall executor not available (.plan/execute-script.py missing)',
                }

            result = subprocess.run(
                ['python3', str(executor), 'plan-marshall:manage-status:manage-status',
                 'get-worktree-path', '--plan-id', plan_id],
                capture_output=True,
                text=True,
                timeout=30,
            )
        except FileNotFoundError:
            return None, None, {
                'status': 'error',
                'operation': 'force-push-with-lease',
                'plan_id': plan_id,
                'error_type': 'plan_not_found',
                'message': 'python3 not found on PATH',
            }
        except subprocess.TimeoutExpired:
            return None, None, {
                'status': 'error',
                'operation': 'force-push-with-lease',
                'plan_id': plan_id,
                'error_type': 'plan_not_found',
                'message': 'manage-status get-worktree-path timed out',
            }

        if result.returncode != 0:
            return None, None, {
                'status': 'error',
                'operation': 'force-push-with-lease',
                'plan_id': plan_id,
                'error_type': 'plan_not_found',
                'message': (result.stderr or result.stdout).strip() or 'manage-status failed',
            }

        # Parse TOON output for worktree_path and worktree_branch.
        try:
            from toon_parser import parse_toon  # type: ignore[import-not-found]
            parsed = parse_toon(result.stdout)
        except Exception as exc:  # noqa: BLE001
            return None, None, {
                'status': 'error',
                'operation': 'force-push-with-lease',
                'plan_id': plan_id,
                'error_type': 'plan_not_found',
                'message': f'failed to parse manage-status output: {exc}',
            }

        if parsed.get('status') == 'error' or parsed.get('error'):
            return None, None, {
                'status': 'error',
                'operation': 'force-push-with-lease',
                'plan_id': plan_id,
                'error_type': 'plan_not_found',
                'message': parsed.get('message') or 'plan resolution failed',
            }

        worktree_path_str = parsed.get('worktree_path') or ''
        branch = parsed.get('worktree_branch') or ''
        if not worktree_path_str or not branch:
            return None, None, {
                'status': 'error',
                'operation': 'force-push-with-lease',
                'plan_id': plan_id,
                'error_type': 'worktree_not_materialized',
                'message': 'worktree_path or worktree_branch absent from manage-status response',
            }

        return branch, Path(worktree_path_str), None

    else:
        # --project-dir + --branch path
        project_dir = getattr(args, 'project_dir', None)
        branch = getattr(args, 'branch', None)
        if not project_dir or not branch:
            return None, None, {
                'status': 'error',
                'operation': 'force-push-with-lease',
                'error_type': 'missing_required_arg',
                'message': 'one of --plan-id or --project-dir is required; '
                           '--project-dir also requires --branch',
            }
        return branch, Path(project_dir), None


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


# ---------------------------------------------------------------------------
# Public command handler
# ---------------------------------------------------------------------------


def cmd_force_push(args) -> dict:
    """Handle force-push-with-lease subcommand.

    Uses ``git push origin {branch} --force-with-lease`` after verifying
    the branch exists locally and is not the base branch. Captures the
    remote SHA after a successful push and returns it as ``remote_sha``
    for caller verification.
    """
    plan_id: str | None = getattr(args, 'plan_id', None)
    project_dir_arg: str | None = getattr(args, 'project_dir', None)

    branch, worktree_path, error = _resolve_branch_and_path(args)
    if error is not None:
        return error

    assert branch is not None and worktree_path is not None  # narrowing

    # Shared envelope echo fields.
    envelope: dict = {'operation': 'force-push-with-lease'}
    if plan_id:
        envelope['plan_id'] = plan_id
    if project_dir_arg:
        envelope['project_dir'] = project_dir_arg

    # Invariant §5.1.2 — verify path is a git working tree when project-dir.
    if project_dir_arg:
        err_msg = _verify_git_repo(worktree_path)
        if err_msg:
            return {
                **envelope,
                'status': 'error',
                'error_type': 'project_dir_not_a_git_repo',
                'message': err_msg,
            }

    # Invariant §5.1.2 — verify branch exists locally.
    rc, _out, _err = run_git(['-C', str(worktree_path), 'rev-parse', '--verify', branch])
    if rc != 0:
        return {
            **envelope,
            'status': 'error',
            'error_type': 'branch_not_found',
            'branch': branch,
            'message': f'branch does not exist locally: {branch}',
        }

    # Invariant §5.1.3 — reject push to base branch.
    # Detect the current checkout's default/base branch heuristically:
    # any branch named "main" or "master" is treated as off-limits.
    if branch in ('main', 'master'):
        return {
            **envelope,
            'status': 'error',
            'error_type': 'branch_not_found',
            'branch': branch,
            'message': 'refusing to force-push to base branch',
        }

    # Perform the push with --force-with-lease.
    rc, _stdout, stderr = run_git(
        ['-C', str(worktree_path), 'push', 'origin', branch, '--force-with-lease']
    )

    if rc == 0:
        # Invariant §5.1.4 — capture remote SHA after successful push.
        rc_ls, ls_out, _ls_err = run_git(
            ['-C', str(worktree_path), 'ls-remote', 'origin', branch]
        )
        remote_sha: str | None = None
        if rc_ls == 0 and ls_out:
            parts = ls_out.split()
            remote_sha = parts[0] if parts else None

        payload = {
            **envelope,
            'status': 'success',
            'branch': branch,
            'remote': 'origin',
        }
        if remote_sha:
            payload['remote_sha'] = remote_sha
        return payload

    # Distinguish lease violation from other push failures.
    stderr_lower = stderr.lower()
    if 'stale info' in stderr_lower or 'rejected' in stderr_lower or 'force-with-lease' in stderr_lower:
        if 'non-fast-forward' in stderr_lower or 'updates were rejected' in stderr_lower:
            return {
                **envelope,
                'status': 'rejected',
                'branch': branch,
                'remote': 'origin',
                'error_type': 'push_rejected_non_fast_forward',
                'message': f'lease violation: remote moved since last fetch — {stderr.strip()}',
            }
        return {
            **envelope,
            'status': 'error',
            'branch': branch,
            'remote': 'origin',
            'error_type': 'lease_check_failed',
            'message': f'force-with-lease check could not be evaluated: {stderr.strip()}',
        }

    return {
        **envelope,
        'status': 'error',
        'branch': branch,
        'remote': 'origin',
        'error_type': 'push_failed',
        'message': f'push failed: {stderr.strip() or "non-zero exit"}',
    }

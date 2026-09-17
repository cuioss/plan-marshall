# SPDX-License-Identifier: FSL-1.1-ALv2
"""prune-local-and-remote-ref verb for git-workflow.py.

Deletes the local feature branch and optionally the remote-tracking ref
``refs/remotes/origin/{head_branch}`` after a PR merge. Consolidates
the three inline git calls (BC-04, BC-05, BC-06) from branch-cleanup.md.

Design contract: §3.2 and §5.3 of design.md.

Two modes:
  ``local_and_remote``  (default) — delete local branch AND remote-tracking ref.
  ``local_only``        — delete only the local branch; skip remote-tracking ref.

Primary path  (``--plan-id``): resolves the head branch through
              ``file_ops.resolve_plan_context`` — the single plan-context
              resolver — and the project directory from the cwd-relative
              checkout root (this verb prunes refs in the checkout the working
              directory is in, not in the plan's worktree).
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

from pathlib import Path

from git_provider import run_git

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


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
        try:
            from file_ops import (
                WorktreeResolutionError,
                cwd_checkout_root,
                resolve_plan_context,
            )
        except ImportError as exc:
            return (
                None,
                None,
                {
                    **envelope,
                    'status': 'error',
                    'error_type': 'plan_not_found',
                    'message': f'file_ops module unavailable: {exc}',
                },
            )

        try:
            head_branch = resolve_plan_context(plan_id, ensure=False).worktree_branch
        except WorktreeResolutionError as exc:
            return (
                None,
                None,
                {
                    **envelope,
                    'status': 'error',
                    'error_type': 'plan_not_found',
                    'message': str(exc),
                },
            )

        if not head_branch:
            return (
                None,
                None,
                {
                    **envelope,
                    'status': 'error',
                    'error_type': 'worktree_not_materialized',
                    'message': 'plan has no recorded feature branch to prune',
                },
            )

        # For prune-local-and-remote-ref, we operate on the checkout the working
        # directory is in — NOT on the plan's worktree, which this verb is
        # typically called to clean up AFTER. The checkout root comes from the
        # uniform cwd rule (ADR-002): the nearest ancestor of cwd containing
        # ``.plan/local``.
        return Path(cwd_checkout_root()), head_branch, None

    elif project_dir_arg:
        if not head_arg:
            return (
                None,
                None,
                {
                    **envelope,
                    'status': 'error',
                    'error_type': 'missing_required_arg',
                    'message': '--head is required when --project-dir is supplied',
                },
            )
        return Path(project_dir_arg), head_arg, None

    else:
        return (
            None,
            None,
            {
                **envelope,
                'status': 'error',
                'error_type': 'missing_required_arg',
                'message': 'one of --plan-id or --project-dir is required',
            },
        )


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
    rc, current_branch_out, _err = run_git(['-C', str(project_path), 'rev-parse', '--abbrev-ref', 'HEAD'])
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
    # Tolerated-delete path: when the local branch is already absent (verified
    # via show-ref), record local_deleted True with a warning and continue to
    # the show-ref-guarded remote-tracking ref deletion instead of aborting
    # with branch_delete_failed. Branch-cleanup removes the worktree before
    # deleting the branch, so a re-entry or an externally deleted branch must
    # still prune refs/remotes/origin/{head_branch}.
    local_delete_warning: str | None = None
    rc, _out, err = run_git(['-C', str(project_path), 'branch', '-D', head_branch])
    if rc != 0:
        rc_v, _v_out, _v_err = run_git(
            ['-C', str(project_path), 'show-ref', '--verify', '--quiet', f'refs/heads/{head_branch}']
        )
        if rc_v == 1:
            local_delete_warning = (
                f'local branch {head_branch} was already deleted — continuing to remote-tracking ref cleanup'
            )
        elif rc_v == 0:
            return {
                **envelope,
                'status': 'error',
                'error_type': 'branch_delete_failed',
                'local_deleted': False,
                'message': f'git branch -D {head_branch} failed: {err.strip() or "non-zero exit"}',
            }
        else:
            return {
                **envelope,
                'status': 'error',
                'error_type': 'branch_delete_failed',
                'local_deleted': False,
                'message': (
                    f'git branch -D {head_branch} failed: {err.strip() or "non-zero exit"}; '
                    f'show-ref verification inconclusive (exit {rc_v}): '
                    f'{_v_err.strip() or "no verdict"}'
                ),
            }

    # Invariant §5.3.5 — local_only mode: skip remote-tracking ref operations.
    if mode == 'local_only':
        payload: dict = {
            **envelope,
            'status': 'success',
            'local_deleted': True,
            'remote_ref_deleted': False,
        }
        if local_delete_warning is not None:
            payload['local_delete_warning'] = local_delete_warning
        return payload

    # Invariant §5.3.3 — show-ref guard before update-ref -d.
    ref_path = f'refs/remotes/origin/{head_branch}'
    rc_sr, _sr_out, _sr_err = run_git(['-C', str(project_path), 'show-ref', '--quiet', ref_path])

    if rc_sr != 0:
        # Remote-tracking ref is already absent — graceful no-op.
        payload_noop: dict = {
            **envelope,
            'status': 'partial',
            'local_deleted': True,
            'remote_ref_deleted': False,
            'remote_ref_warning': (f'remote-tracking ref {ref_path} was already absent — no-op'),
        }
        if local_delete_warning is not None:
            payload_noop['local_delete_warning'] = local_delete_warning
        return payload_noop

    # Invariant §5.3.4 — targeted ref deletion only.
    rc_ud, _ud_out, ud_err = run_git(['-C', str(project_path), 'update-ref', '-d', ref_path])
    if rc_ud != 0:
        payload_ref_error: dict = {
            **envelope,
            'status': 'error',
            'error_type': 'unexpected_ref_error',
            'local_deleted': True,
            'remote_ref_deleted': False,
            'message': f'update-ref -d failed after show-ref confirmed ref exists: {ud_err.strip()}',
        }
        if local_delete_warning is not None:
            payload_ref_error['local_delete_warning'] = local_delete_warning
        return payload_ref_error

    payload_done: dict = {
        **envelope,
        'status': 'success',
        'local_deleted': True,
        'remote_ref_deleted': True,
    }
    if local_delete_warning is not None:
        payload_done['local_delete_warning'] = local_delete_warning
    return payload_done

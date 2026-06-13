#!/usr/bin/env python3
"""Shared utilities for manage-references scripts.

Provides path resolution, read/write operations, and TOON output formatting.
"""

import subprocess
from pathlib import Path
from typing import Any, TypedDict, cast

from constants import FILE_REFERENCES  # type: ignore[import-not-found]
from file_ops import get_plan_dir, read_json, write_json  # type: ignore[import-not-found]

# =============================================================================
# Type Definitions
# =============================================================================


class ReferencesData(TypedDict, total=False):
    """Type definition for references data structure."""

    branch: str
    base_branch: str
    issue_url: str
    build_system: str
    domains: list[str]
    affected_files: list[str]
    external_docs: dict[str, Any]


# =============================================================================
# File Operations
# =============================================================================


def get_references_path(plan_id: str) -> Path:
    """Get the references.json file path."""
    return get_plan_dir(plan_id) / FILE_REFERENCES


def read_references(plan_id: str) -> dict[Any, Any]:
    """Read references.json for a plan."""
    return cast(dict[Any, Any], read_json(get_references_path(plan_id)))


def write_references(plan_id: str, refs: dict) -> None:
    """Write references.json for a plan."""
    write_json(get_references_path(plan_id), refs)


def require_references(plan_id: str) -> dict[Any, Any]:
    """Read references, returning an error dict if not found.

    Args:
        plan_id: Plan identifier (must already be validated).

    Returns:
        References dict on success, or an error dict
        ``{'status': 'error', 'plan_id': ..., 'error': 'file_not_found',
        'message': 'references.json not found'}`` on failure. The caller MUST
        check ``result.get('status') == 'error'`` and propagate the dict so
        the main dispatcher can emit the TOON. Operation failures exit 0 —
        the script ran successfully, only the operation failed; callers
        branch on the TOON ``status`` field, not on the process exit code.

    Raises:
        ValueError: If references.json exists but its top-level JSON value
            is not a JSON object (e.g., list, string, number, boolean, null).
            This indicates file corruption rather than the expected
            file-not-found state, so it surfaces as a clear error at the
            boundary instead of triggering ``AttributeError`` downstream when
            callers invoke ``.get()`` on the parsed value.
    """
    refs = read_references(plan_id)
    if not refs:
        return {
            'status': 'error',
            'plan_id': plan_id,
            'error': 'file_not_found',
            'message': 'references.json not found',
        }
    if not isinstance(refs, dict):
        raise ValueError(
            f"references.json for plan {plan_id!r} has invalid format: "
            f"expected a JSON object, got {type(refs).__name__}"
        )
    return refs


# =============================================================================
# Shared Plan-Branch-Only Diff Primitive
# =============================================================================
#
# The "live" plan-branch-only file set is the union of:
#     - ``git -C {worktree} diff --name-only {base_ref}...HEAD`` (three-dot:
#       the symmetric difference relative to the merge-base, i.e. files changed
#       on the plan branch only — NOT files that arrived from base via an
#       absorb merge)
#     - parsed paths from ``git -C {worktree} status --porcelain
#       --untracked-files=all`` (uncommitted working-tree state)
#
# This primitive is the single source of truth for the read-only
# ``compute-footprint`` verb and every in-process footprint call site.
# Do NOT re-implement it elsewhere.


def _run_git(worktree: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
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


def resolve_base_ref(explicit: str | None, refs: dict) -> str:
    """Resolve the base ref, falling back to references.base_branch then 'main'.

    Args:
        explicit: An explicit base ref (e.g. from ``--base-ref``), or None.
        refs: The references dict (read from references.json).

    Returns:
        The resolved base ref string.
    """
    if explicit is not None:
        val = str(explicit).strip()
        if val:
            return val
    base_branch = refs.get('base_branch')
    if base_branch is not None:
        val = str(base_branch).strip()
        if val:
            return val
    return 'main'


def compute_plan_branch_diff(worktree: Path, base_ref: str) -> set[str]:
    """Compute the live plan-branch-only file set.

    Returns the union of the three-dot ``{base_ref}...HEAD`` diff name set and
    the porcelain working-tree state. This is the canonical "live" footprint set
    that the read-only ``compute-footprint`` verb returns. The three-dot form
    excludes files that arrived on the branch from ``base_ref`` via an absorb
    merge, so the footprint reflects only files the plan branch actually touched.

    Args:
        worktree: Absolute path to the active git worktree.
        base_ref: Base ref for the three-dot diff.

    Returns:
        The set of plan-branch-only paths (diff range ∪ working-tree state).

    Raises:
        subprocess.CalledProcessError: If either ``git diff`` or ``git status``
            exits non-zero (e.g., invalid ``base_ref``, missing ref in the
            worktree, or transient git error).  A silent failure here would
            cause the footprint to be computed against an empty set, so we
            surface the error loudly to make it immediately actionable.
    """
    diff_proc = _run_git(worktree, ['diff', '--name-only', f'{base_ref}...HEAD'])
    if diff_proc.returncode != 0:
        raise subprocess.CalledProcessError(
            diff_proc.returncode,
            diff_proc.args,
            output=diff_proc.stdout,
            stderr=diff_proc.stderr,
        )
    diff_paths = [line for line in diff_proc.stdout.splitlines() if line]

    # ``--untracked-files=all`` is critical: with the default mode
    # (``--untracked-files=normal``) git collapses untracked directories into
    # a single ``?? src/`` entry, hiding individual file paths. The ledger
    # records files, so we need files-level visibility to intersect correctly.
    status_proc = _run_git(worktree, ['status', '--porcelain', '--untracked-files=all'])
    if status_proc.returncode != 0:
        raise subprocess.CalledProcessError(
            status_proc.returncode,
            status_proc.args,
            output=status_proc.stdout,
            stderr=status_proc.stderr,
        )
    status_paths = _parse_porcelain(status_proc.stdout)

    return set(diff_paths) | set(status_paths)

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
    modified_files: list[str]
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
# This primitive is the single source of truth shared by the read-only
# ``diff-files`` verb and the write-back ``reconcile-files`` verb, and by the
# in-process baseline-reconcile call site. Do NOT re-implement it elsewhere.


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


def resolve_base_ref(explicit: str | None, refs: dict) -> str:
    """Resolve the base ref, falling back to references.base_branch then 'main'.

    Args:
        explicit: An explicit base ref (e.g. from ``--base-ref``), or None.
        refs: The references dict (read from references.json).

    Returns:
        The resolved base ref string.
    """
    if explicit:
        return str(explicit)
    base_branch = refs.get('base_branch')
    if base_branch:
        return str(base_branch)
    return 'main'


def compute_plan_branch_diff(worktree: Path, base_ref: str) -> set[str]:
    """Compute the live plan-branch-only file set.

    Returns the union of the three-dot ``{base_ref}...HEAD`` diff name set and
    the porcelain working-tree state. This is the canonical "live" set that both
    ``diff-files`` (read-only) and ``reconcile-files`` (write-back) intersect the
    ledger against. The three-dot form excludes files that arrived on the branch
    from ``base_ref`` via an absorb merge, which is precisely why the reconcile
    write-back removes absorbed-upstream pollution from the ledger.

    Args:
        worktree: Absolute path to the active git worktree.
        base_ref: Base ref for the three-dot diff.

    Returns:
        The set of plan-branch-only paths (diff range ∪ working-tree state).
    """
    diff_proc = _run_git(worktree, ['diff', '--name-only', f'{base_ref}...HEAD'])
    diff_paths = [line for line in diff_proc.stdout.splitlines() if line]

    # ``--untracked-files=all`` is critical: with the default mode
    # (``--untracked-files=normal``) git collapses untracked directories into
    # a single ``?? src/`` entry, hiding individual file paths. The ledger
    # records files, so we need files-level visibility to intersect correctly.
    status_proc = _run_git(worktree, ['status', '--porcelain', '--untracked-files=all'])
    status_paths = _parse_porcelain(status_proc.stdout)

    return set(diff_paths) | set(status_paths)


def reconcile_modified_files(plan_id: str, worktree: Path, base_ref: str) -> dict:
    """Recompute and persist ``references.modified_files`` from the plan-branch-only diff.

    Write-back counterpart of the read-only ``diff-files`` query. Computes the
    live plan-branch-only set via :func:`compute_plan_branch_diff`, reconciles
    the existing ledger against it (ledger ∩ live, in ledger order, plus any live
    plan-branch files the diff range proves belong to the plan), replaces
    ``references.modified_files`` with the reconciled set, and persists it.

    The reconciliation drops ledger entries that are NOT in the live
    plan-branch-only set — these are the absorbed-upstream files that polluted
    the ledger after an absorb merge.

    Args:
        plan_id: Plan identifier (must already be validated).
        worktree: Absolute path to the active git worktree.
        base_ref: Base ref for the three-dot diff.

    Returns:
        A structured result dict. On success::

            {'status': 'success', 'plan_id', 'base_ref', 'before_count',
             'after_count', 'removed': [paths], 'modified_files': [paths]}

        On failure (references.json missing)::

            {'status': 'error', 'plan_id', 'error': 'references_not_found',
             'message': ...}
    """
    refs = read_references(plan_id)
    if not refs:
        return {
            'status': 'error',
            'plan_id': plan_id,
            'error': 'references_not_found',
            'message': 'references.json not found',
        }

    ledger: list[str] = list(refs.get('modified_files', []))
    live_set = compute_plan_branch_diff(worktree, base_ref)
    ledger_set = set(ledger)

    # ledger ∩ live, preserving ledger order.
    reconciled: list[str] = [path for path in ledger if path in live_set]
    # Plan-branch live files the ledger never recorded (the diff range proves
    # they belong to the plan), appended in sorted order for determinism.
    for path in sorted(live_set - ledger_set):
        reconciled.append(path)

    removed = [path for path in ledger if path not in live_set]

    refs['modified_files'] = reconciled
    write_references(plan_id, refs)

    return {
        'status': 'success',
        'plan_id': plan_id,
        'base_ref': base_ref,
        'before_count': len(ledger),
        'after_count': len(reconciled),
        'removed': removed,
        'modified_files': reconciled,
    }

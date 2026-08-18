#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared plan-footprint resolution for the retrospective / audit consumers.

One resolution chain, so the recall check (``check-artifact-consistency``) and the
mis-prune check (``check-routing-decisions``) grade against the **same** footprint —
the D4 "one footprint resolution, two consumers" contract. Both call the whole-chain
:func:`resolve_footprint`. ``analyze-logs`` reuses the per-tier helpers here for its
own scope-deviation resolver, which keeps a **different** diff-failure policy (fall
through to the legacy key rather than reporting unresolvable) and therefore composes
the helpers itself rather than calling the whole-chain function.

Resolution tiers, in order:

1. **Live diff** — a live plan whose worktree the ONE resolver
   (:func:`_references_core.resolve_live_worktree`) resolves to a directory on disk.
   A ``CalledProcessError`` here reports UNRESOLVABLE rather than falling through: the
   worktree resolved but the diff failed, so a lower tier would answer a different
   question while presenting as the same measurement.
2. **Realized-footprint capture** — ``references.realized_footprint``, persisted by
   ``default:branch-cleanup`` (via ``manage-references capture-footprint``) while the
   worktree still existed and the diff was still accurate. This is the primary tier
   for an ARCHIVED plan and the set the resolver **prefers** over any re-derivation:
   it is captured-while-true, not re-derived from a substrate that has since changed.
3. **Merge-commit** — ``references.merge_commit_sha`` resolved as
   ``git -C {plan_dir} diff --name-only {sha}^1 {sha}``. The first-parent range names
   the changes the landing commit introduced, which is exact for BOTH a squash landing
   (its single parent is the base) and a true merge commit (its first parent is the
   base branch). It is **not** a ``base..HEAD`` range and carries no sibling
   contamination — a landing commit names its own first parent. It resolves only
   *post*-merge, so it sits BELOW the deterministic capture as a fallback: it cannot
   serve a consumer running before the merge.
4. **Legacy key** — ``references.modified_files`` (a SHIM for archived plans created
   before the change-ledger was removed).
5. **Unresolvable** — :data:`FOOTPRINT_UNRESOLVED`. Key absent and key present-but-empty
   are different answers and are reported differently: an empty list is a resolved,
   genuinely-empty footprint, never the unresolvable sentinel.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, TypeGuard

from _references_core import (
    compute_plan_branch_diff,
    resolve_base_ref,
    resolve_live_worktree,
)

#: Stated sentinel for a footprint that could NOT be resolved at all. Deliberately
#: distinct from ``set()`` (the footprint resolved and the plan touched no files).
#: Collapsing the two is what let an exact footprint score a confident "Recall 0%"
#: after branch-cleanup deleted the worktree the resolver measures.
FOOTPRINT_UNRESOLVED = None


def resolve_diff_file_path(diff_file: str, plan_dir: Path) -> Path:
    """Resolve an explicit ``--diff-file`` argument to an existing file, or raise.

    An absolute path is used verbatim. A RELATIVE path is resolved against the
    plan directory first and the process cwd second, and the first candidate that
    exists wins. Plan-relative comes first because that is the form the capture
    pattern documents (``--diff-file work/footprint.txt``, where ``work/`` is a
    plan-directory subdirectory) and the form the sibling ``collect-fragments add
    --fragment-file`` flag has always accepted in the same workflow.

    **A supplied-but-unresolvable path raises.** It is never reported as an absent
    one. The two were previously indistinguishable: an unresolvable ``--diff-file``
    returned the same empty list as no ``--diff-file`` at all, so the documented
    plan-relative invocation degraded to a ``skip`` reading *"no realized
    footprint"* while the identical file passed as an absolute path found a real
    violation. A could-not-look must not carry the same token as a
    nothing-to-look-at, least of all when that token reads benign in every
    downstream summary.

    Args:
        diff_file: The ``--diff-file`` argument as supplied.
        plan_dir: The resolved plan directory a relative argument is resolved against.

    Returns:
        The existing file the argument names.

    Raises:
        ValueError: When no candidate exists, naming every candidate tried.
    """
    raw = Path(diff_file)
    if raw.is_absolute():
        if raw.exists():
            return raw
        raise ValueError(f'Diff file does not exist: {diff_file}')
    candidates = [plan_dir / raw, Path.cwd() / raw]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    tried = ', '.join(str(c) for c in candidates)
    raise ValueError(
        f'Diff file does not exist: {diff_file} — a relative --diff-file is resolved '
        f'against the plan directory first and the cwd second; tried: {tried}'
    )


def footprint_resolved(footprint: set[str] | None) -> TypeGuard[set[str]]:
    """The ONE named predicate callers use to read a footprint's resolution state.

    ``not footprint`` is NOT equivalent: it is also true for a resolved-but-empty
    footprint, which is a measured result and must still yield a measured verdict.
    """
    return footprint is not FOOTPRINT_UNRESOLVED


def load_references_dict(plan_dir: Path) -> dict[str, Any]:
    """Read ``references.json`` from ``plan_dir``; return ``{}`` on any error."""
    refs_path = plan_dir / 'references.json'
    if not refs_path.exists():
        return {}
    try:
        data = json.loads(refs_path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _coerce_path_set(value: Any) -> set[str] | None:
    """Coerce a references path-list value to a set, or None when the key is unusable.

    A missing key (``None``) is ``None``; a bare string is a one-element list; a list
    is the set of its non-empty stringified entries (possibly empty — a resolved,
    genuinely-empty footprint); anything else is ``None`` (unusable → next tier).
    """
    if value is None:
        return None
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return None
    return {str(p).strip() for p in value if p}


def read_captured_footprint(refs: dict[str, Any]) -> set[str] | None:
    """Tier 2: ``references.realized_footprint`` (the capture-while-true side effect)."""
    return _coerce_path_set(refs.get('realized_footprint'))


def read_legacy_footprint(refs: dict[str, Any]) -> set[str] | None:
    """Tier 4: the legacy ``references.modified_files`` key."""
    # SHIM(B): archived plans' references.modified_files key, written before the change-ledger was removed.
    # shim-owner: plan-retrospective
    # shim-floor: the change-ledger removal that stopped persisting references.modified_files; the current writer no longer emits the key (predates this shallow clone's history root dcd3c00 / #1105, so not PR-pinnable here).
    # shim-remove-when: no archived plan predating the ledger removal is retained (i.e. such archives are purged/aged out).
    return _coerce_path_set(refs.get('modified_files'))


def resolve_merge_commit_footprint(plan_dir: Path, refs: dict[str, Any]) -> set[str] | None:
    """Tier 3: the realized path set of the recorded landing commit, or ``None``.

    Uses ``git -C {plan_dir} diff --name-only {sha}^1 {sha}``. ``plan_dir`` is inside
    the repository (``.plan/archived-plans/…`` sits under the repo root even though
    it is git-ignored), so ``git -C`` resolves the enclosing repo and the landed
    commit in its history.

    ⚠ The ignored thing is that sub-path, not ``.plan/`` as a whole: a number of
    files under ``.plan/`` ARE tracked (``marshal.json``, every
    ``project-architecture/**/enriched.json``), which is why ``script-shared``'s
    ``_plan_state_exemption`` exists. The conclusion here is unaffected — an
    ignored path still resolves its enclosing repo — but the blanket form of the
    claim is false and must not be restated.

    Any git failure — the SHA is absent (a shallow clone that never fetched it),
    ``plan_dir`` is not inside a repository, or a non-zero exit — returns ``None`` so
    the caller falls through to the legacy tier rather than fabricating a set. The SHA
    itself is recorded by ``default:branch-cleanup`` only on the synchronous merge
    path; on the async merge-queue path it is absent and tier 2 is the resolution.
    """
    sha = refs.get('merge_commit_sha')
    if not isinstance(sha, str) or not sha.strip():
        return None
    sha = sha.strip()
    try:
        proc = subprocess.run(
            ['git', '-C', str(plan_dir), 'diff', '--name-only', f'{sha}^1', sha],
            capture_output=True,
            text=True,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    return {line.strip() for line in proc.stdout.splitlines() if line.strip()}


def resolve_footprint(plan_dir: Path, plan_id: str | None = None) -> set[str] | None:
    """The whole-chain resolver shared by the recall and mis-prune consumers.

    Archived mode passes ``plan_id=None`` and therefore skips tier 1 (an archived
    plan's recorded worktree names a directory finalize already removed). Returns a
    set when the footprint resolved (possibly empty), or :data:`FOOTPRINT_UNRESOLVED`
    when no tier answered. Read the distinction through :func:`footprint_resolved`,
    never by testing emptiness.
    """
    refs = load_references_dict(plan_dir)

    worktree = resolve_live_worktree(plan_id)
    if worktree is not None:
        base_ref = resolve_base_ref(None, refs)
        try:
            return compute_plan_branch_diff(worktree, base_ref)
        except subprocess.CalledProcessError:
            return FOOTPRINT_UNRESOLVED

    captured = read_captured_footprint(refs)
    if captured is not None:
        return captured

    merge_set = resolve_merge_commit_footprint(plan_dir, refs)
    if merge_set is not None:
        return merge_set

    legacy = read_legacy_footprint(refs)
    if legacy is not None:
        return legacy

    return FOOTPRINT_UNRESOLVED

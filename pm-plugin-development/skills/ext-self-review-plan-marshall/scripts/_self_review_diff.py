#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Git/diff plumbing helpers for self-review candidate surfacing.

Runs the worktree diff against the base branch, derives the plan footprint, and
parses the unified diff into the added-line and changed-line-pair shapes the
detectors consume. Importers pull these by flat name (e.g.
``from _self_review_diff import _iter_added_lines``).
"""

import subprocess
from pathlib import Path

from _references_core import (
    compute_plan_branch_diff,
)
from _self_review_patterns import (
    _FILE_HEADER,
    _HUNK_HEADER,
)

# =============================================================================
# Helpers
# =============================================================================


def _truncate(text: str, limit: int) -> str:
    """Truncate text to limit characters, adding ellipsis when shortened."""
    if len(text) <= limit:
        return text
    return text[: limit - 3] + '...'


def _run_git(project_dir: Path, *args: str) -> tuple[int, str, str]:
    """Run a git command via ``git -C {project_dir} ...`` and return (returncode, stdout, stderr)."""
    cmd = ['git', '-C', str(project_dir), *args]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)  # noqa: S603
    return proc.returncode, proc.stdout, proc.stderr


def _resolve_footprint(project_dir: Path, base_branch: str) -> list[str]:
    """Derive the plan footprint live from the worktree.

    Computes the on-demand footprint via ``compute_plan_branch_diff``
    (``{base}...HEAD`` ∪ porcelain) read straight from ``project_dir``. Returns
    repo-relative paths, or an empty list on a git error — an empty footprint
    means "do not filter the surfaced diff", preserving the prior behaviour when
    no scope was resolvable.
    """
    try:
        footprint = compute_plan_branch_diff(project_dir, base_branch)
    except subprocess.CalledProcessError:
        return []
    return sorted(footprint)


def _verify_base_branch(project_dir: Path, base_branch: str) -> bool:
    """Return True if the base branch ref resolves inside the project dir."""
    rc, _, _ = _run_git(project_dir, 'rev-parse', '--verify', base_branch)
    return rc == 0


def _diff_hunks(project_dir: Path, base_branch: str) -> str:
    """Return the post-image diff of the working tree against the merge-base.

    The diff TARGET is the **working tree** (not ``HEAD``) precisely BECAUSE
    ``pre-submission-self-review`` runs BEFORE ``push`` — the changes
    under review are typically uncommitted (staged AND unstaged), so they must
    still be surfaced. This preserves the documented pre-commit timing contract.

    The diff ANCHOR is the **merge-base** of ``base_branch`` and ``HEAD``
    (``git merge-base {base_branch} HEAD``), NOT the base-branch tip. Diffing
    against the merge-base excludes commits that arrived on the branch FROM
    ``base_branch`` via an absorb merge — those commits sit at or below the
    merge-base and so fall outside the diff range, removing absorbed-merge
    pollution from the surfaced review surface.

    This is deliberately NEITHER of the two rejected alternatives:

    * NOT a naive ``{base_branch}...HEAD`` three-dot diff — that diffs HEAD (not
      the working tree) against the merge-base, dropping the uncommitted
      pre-submission changes the review exists to surface.
    * NOT the old naive two-dot ``git diff {base_branch}`` against an advanced
      base tip — when the base tip has been absorbed into the branch, that diff
      re-includes the absorbed-upstream content.

    On a merge-base resolution failure (non-zero rc or empty output), falls back
    to the prior two-dot ``git diff {base_branch}`` so the function never returns
    an empty surface on a transient git failure. The existing fail-safe
    ``return ''`` is preserved only for the case where the diff itself fails.
    """
    mb_rc, mb_out, _ = _run_git(project_dir, 'merge-base', base_branch, 'HEAD')
    merge_base = mb_out.strip() if mb_rc == 0 else ''
    anchor = merge_base or base_branch
    rc, out, _ = _run_git(project_dir, 'diff', '--unified=3', anchor)
    if rc != 0:
        return ''
    return out


def _read_post_image(project_dir: Path, repo_relative_path: str) -> list[str]:
    """Return the worktree's current contents of repo_relative_path as a list of lines."""
    full = project_dir / repo_relative_path
    if not full.is_file():
        return []
    try:
        return full.read_text(encoding='utf-8').splitlines()
    except (OSError, UnicodeDecodeError):
        return []


# =============================================================================
# Diff parsing
# =============================================================================


def _iter_added_lines(diff_text: str) -> list[tuple[str, int, str]]:
    """Yield ``(file_path, post_image_line_no, content)`` for each added line in the diff."""
    out: list[tuple[str, int, str]] = []
    current_file: str | None = None
    post_line = 0
    for raw in diff_text.splitlines():
        m_file = _FILE_HEADER.match(raw)
        if m_file is not None:
            current_file = m_file.group(1)
            post_line = 0
            continue
        m_hunk = _HUNK_HEADER.match(raw)
        if m_hunk is not None:
            post_line = int(m_hunk.group(1))
            continue
        if current_file is None:
            continue
        if raw.startswith('+++') or raw.startswith('---'):
            continue
        if raw.startswith('+'):
            content = raw[1:]
            out.append((current_file, post_line, content))
            post_line += 1
            continue
        if raw.startswith('-'):
            continue
        if raw.startswith(' '):
            post_line += 1
            continue
        if raw.startswith('\\'):
            continue
    return out


def _iter_changed_line_pairs(diff_text: str) -> list[tuple[str, int, str, str]]:
    """Yield ``(file_path, post_image_line_no, removed, added)`` for adjacent
    ``-``/``+`` pairs within a hunk.

    A pair is a removed line immediately followed by an added line in the same
    hunk. The ``post_image_line_no`` is the added line's post-image line number.
    Unpaired ``+`` lines (an addition not preceded by a removal) and unpaired
    ``-`` lines (a removal not followed by an addition) are ignored — only the
    one-for-one swap shape Facet 3 cares about is yielded. ``_iter_added_lines``
    is intentionally left untouched (other detectors depend on its added-only
    shape); this helper is the removed-line-aware companion.
    """
    out: list[tuple[str, int, str, str]] = []
    current_file: str | None = None
    post_line = 0
    pending_removed: str | None = None
    for raw in diff_text.splitlines():
        m_file = _FILE_HEADER.match(raw)
        if m_file is not None:
            current_file = m_file.group(1)
            post_line = 0
            pending_removed = None
            continue
        m_hunk = _HUNK_HEADER.match(raw)
        if m_hunk is not None:
            post_line = int(m_hunk.group(1))
            pending_removed = None
            continue
        if current_file is None:
            continue
        if raw.startswith('+++') or raw.startswith('---'):
            continue
        if raw.startswith('-'):
            pending_removed = raw[1:]
            continue
        if raw.startswith('+'):
            content = raw[1:]
            if pending_removed is not None:
                out.append((current_file, post_line, pending_removed, content))
            pending_removed = None
            post_line += 1
            continue
        if raw.startswith(' '):
            pending_removed = None
            post_line += 1
            continue
        if raw.startswith('\\'):
            continue
        pending_removed = None
    return out

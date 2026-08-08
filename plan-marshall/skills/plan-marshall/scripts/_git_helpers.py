# SPDX-License-Identifier: FSL-1.1-ALv2
"""Git subprocess helpers for phase_handshake invariants.

Uses plain subprocess matching the codebase convention (workflow-integration-git).
No external git library dependency.
"""

from __future__ import annotations

import subprocess
from pathlib import Path


def git_head(cwd: str | Path) -> str | None:
    """Return the full HEAD SHA at ``cwd``, or None if not a git repository."""
    try:
        result = subprocess.run(
            ['git', 'rev-parse', 'HEAD'],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return None
    return result.stdout.strip() or None


def git_dirty_count(cwd: str | Path) -> int | None:
    """Return the number of porcelain status lines at ``cwd``.

    Zero means the working tree is clean. None means the directory is not a
    git repository (or the command could not run).
    """
    try:
        result = subprocess.run(
            ['git', 'status', '--porcelain'],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return None
    output = result.stdout
    if not output.strip():
        return 0
    return len([line for line in output.splitlines() if line.strip()])


def git_dirty_files(cwd: str | Path) -> list[str] | None:
    """Return a sorted list of dirty paths at ``cwd`` per ``git status --porcelain``.

    Each output line of ``git status --porcelain`` has the shape ``XY path``
    (or ``XY orig -> path`` for renames). The leading two-character status
    code is stripped and rename arrows resolve to the destination path so
    the returned list is a flat set of repository-relative paths.

    An empty working tree returns ``[]``. ``None`` is returned when the
    directory is not a git repository or the command could not run, matching
    :func:`git_dirty_count`'s "not applicable" semantics so callers can
    cleanly skip the invariant in that case.

    The result is sorted (stable across captures) and deduplicated. Filter
    rules (e.g., excluding ``.plan/`` entries) are the caller's
    responsibility; this helper returns the raw porcelain set.
    """
    try:
        result = subprocess.run(
            ['git', 'status', '--porcelain'],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return None
    paths: set[str] = set()
    for raw in result.stdout.splitlines():
        if not raw.strip():
            continue
        # Porcelain format: ``XY path`` (length >= 4 when path is present).
        if len(raw) < 4:
            continue
        rest = raw[3:]
        # Renames render as ``orig -> dest``; use the destination so the
        # captured path matches the on-disk reality after the rename.
        if ' -> ' in rest:
            rest = rest.rsplit(' -> ', 1)[1]
        # Quoted paths (with embedded special characters) come wrapped in
        # double quotes; strip them so set membership treats quoted and
        # unquoted forms identically across captures.
        if rest.startswith('"') and rest.endswith('"') and len(rest) >= 2:
            rest = rest[1:-1]
        if rest:
            paths.add(rest)
    return sorted(paths)

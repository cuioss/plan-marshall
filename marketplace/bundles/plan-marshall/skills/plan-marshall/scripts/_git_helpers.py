"""Git subprocess helpers for phase_handshake invariants.

Uses plain subprocess matching the codebase convention (manage-worktree,
workflow-integration-git). No external git library dependency.
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

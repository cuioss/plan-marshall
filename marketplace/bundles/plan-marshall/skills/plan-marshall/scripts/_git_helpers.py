# SPDX-License-Identifier: FSL-1.1-ALv2
"""Git subprocess helpers for phase_handshake invariants.

Uses plain subprocess matching the codebase convention (workflow-integration-git).
No external git library dependency.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from _porcelain import parse_porcelain_z


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
    """Return a sorted list of dirty paths at ``cwd`` per ``git status --porcelain -z``.

    The observation is NUL-delimited and decoded through the SHARED
    :func:`_porcelain.parse_porcelain_z`, which the post-run source guard also
    uses — so the two working-tree observations in the finalize band speak ONE
    path encoding rather than two.

    The encoding matters because the caller
    (:func:`_invariants._filter_main_dirty_paths`) compares these paths against
    the NUL-delimited tracked set from
    :func:`_plan_state_exemption.tracked_plan_paths`. The default porcelain line
    form quotes and C-escapes a path containing a special character; stripping the
    quotes without unescaping — the previous behaviour here — produced a spelling
    that could never match the tracked set, so a tracked ``.plan/`` file git chose
    to quote escaped the comparison. In ``-z`` mode git emits every path verbatim,
    so the two sides agree by construction.

    Renames and copies contribute BOTH sides (git emits the original as its own
    NUL-terminated field). This is deliberate: a rename dirties both paths, and the
    ``orig -> dest`` infix the previous line-form parse split on is itself ambiguous
    for a path containing the literal ``" -> "``.

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
            ['git', 'status', '--porcelain', '-z'],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return None
    return sorted(set(parse_porcelain_z(result.stdout)))

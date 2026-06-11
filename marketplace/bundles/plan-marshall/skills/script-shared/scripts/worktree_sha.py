#!/usr/bin/env python3
"""Working-tree currency hash — the single shared freshness primitive.

Notation: imported as a module (PYTHONPATH) — ``from worktree_sha import
compute_worktree_sha``. NOT an executor entry point.

This module is the ONE implementation of the working-tree currency hash used by
every freshness writer and reader: the ``manage-change-ledger worktree-sha``
verb, the executor dispatch-boundary ``kind=build`` ledger writer, the phase-5
``kind=change`` ledger writer, and the ``pre-commit-verify-freshness`` gate. The
writer/gate symmetry is correctness-critical — a divergent hash silently breaks
every freshness match — so the helper lives here once and is imported, never
re-implemented.

**Why working-tree currency, not HEAD currency.** The freshness gate is a
*pre-commit* gate: at gate time the plan's edits are still uncommitted (the
plan-level squash lands later, at merge). A ``git rev-parse HEAD`` primitive
would return the same pre-plan commit sha both when a build runs during phase-5
AND when the gate queries pre-commit, matching trivially regardless of any
working-tree changes between build and gate — a false-positive ``fresh``. The
primitive therefore captures the *working-tree* state, including the still
uncommitted staged + unstaged + untracked changes.

**The composition (non-mutating).** ``compute_worktree_sha`` hashes:

  1. the committed base (``git rev-parse HEAD``),
  2. the full tracked diff against that base (``git diff HEAD`` — staged AND
     unstaged modifications), and
  3. the sorted ``(path, content)`` stream of untracked-not-ignored files
     (``git ls-files --others --exclude-standard``),

with ``hashlib.sha256``, returning the hex digest. On a clean tree (empty diff,
no untracked files) the digest reduces to a stable function of the HEAD sha
alone — the clean-tree HEAD-tree fallback, still deterministic and matchable.

The function NEVER mutates the working tree, index, or refs: no ``git stash``,
no ``git write-tree``, no ``git add``. ``git stash create`` (without ``-u``)
would exclude untracked files and return empty on a clean tracked tree, so a
plan's brand-new files would not change the sha — a false match; ``git
write-tree`` captures only the staged index, missing unstaged edits and
untracked files. The ``git diff HEAD`` + ``git ls-files --others`` composition
is the only fully non-mutating, untracked-inclusive option, so it is the chosen
primitive.
"""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

_NULL = b'\0'


def _run_git(args: list[str], cwd: str | Path) -> tuple[int, bytes]:
    """Run a git command, returning ``(returncode, stdout_bytes)``.

    Error-tolerant: a missing git binary or any subprocess failure surfaces as a
    non-zero return code with empty stdout, so callers can map an unresolvable
    HEAD to a ``None`` digest rather than raising. NEVER mutates anything — the
    only commands passed are read-only plumbing.
    """
    try:
        completed = subprocess.run(
            ['git', *args],
            cwd=str(cwd),
            capture_output=True,
            check=False,
        )
    except (OSError, ValueError):
        return 1, b''
    return completed.returncode, completed.stdout


def compute_worktree_sha(worktree_root: str | Path) -> str | None:
    """Compute the working-tree currency hash for ``worktree_root``.

    Returns the hex sha256 digest of (HEAD sha) + (tracked diff vs HEAD) +
    (sorted untracked-not-ignored content), or ``None`` when HEAD is
    unresolvable (a non-git directory or a repo with no commit). The digest is
    identical for identical working-tree state and differs whenever any tracked
    edit (staged or unstaged) or any untracked-not-ignored file changes. Never
    mutates the working tree, index, or refs.
    """
    head_rc, head_out = _run_git(['rev-parse', 'HEAD'], worktree_root)
    if head_rc != 0:
        return None
    head = head_out.strip()

    _diff_rc, diff_out = _run_git(['diff', 'HEAD'], worktree_root)

    _others_rc, others_out = _run_git(
        ['ls-files', '--others', '--exclude-standard'], worktree_root
    )

    hasher = hashlib.sha256()
    hasher.update(head)
    hasher.update(_NULL)
    hasher.update(diff_out)
    hasher.update(_NULL)

    others = sorted(
        line for line in others_out.decode('utf-8', 'surrogateescape').splitlines() if line
    )
    for rel_path in others:
        hasher.update(rel_path.encode('utf-8', 'surrogateescape'))
        hasher.update(_NULL)
        try:
            content = (Path(worktree_root) / rel_path).read_bytes()
        except OSError:
            # A file git listed but that we cannot read (symlink to nowhere,
            # race with a concurrent delete): fold a stable marker so the
            # absence still contributes deterministically.
            content = b''
        hasher.update(content)
        hasher.update(_NULL)

    return hasher.hexdigest()

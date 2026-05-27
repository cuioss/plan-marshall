"""Shared worktree-content fingerprint for the Claude target staleness guard.

The fingerprint is the SHA-1 of the sorted concatenation of
``{path}:{blob_sha}\\n`` lines, where each ``blob_sha`` is git's own
content hash for the worktree bytes of the named path. The pipeline
relies exclusively on git's native primitives:

* ``git -C {repo_root} ls-files {prefix}`` enumerates tracked paths under
  the configured prefix (default ``marketplace/bundles``). Untracked
  files, build artefacts, and gitignored paths are excluded by git itself
  — no custom filter logic.
* ``git -C {repo_root} hash-object --stdin-paths`` returns blob SHAs over
  the WORKTREE bytes of all tracked paths in a single subprocess invocation
  (not HEAD, not INDEX). Uncommitted edits therefore change the digest,
  which is the property the staleness guard depends on.
* ``hashlib.sha1`` folds the sorted ``{path}:{blob_sha}\\n`` lines into a
  single hex digest. SHA-1 mirrors git's own blob primitive; the choice
  is anchored to the rest of the system instead of inventing a new hash.

The helper is imported by ``marketplace/targets/claude/target.py`` (to
write the sentinel at the end of every successful emit) and by
``.claude/skills/sync-plugin-cache/scripts/sync.py`` (to recompute the
fingerprint inside ``_staleness_guard``). A single source of truth keeps
the two sides byte-symmetric so the guard never trips on a hashing
discrepancy.
"""

from __future__ import annotations

import hashlib
import shutil
import subprocess
from pathlib import Path

DEFAULT_PREFIX = 'marketplace/bundles'


class FingerprintError(RuntimeError):
    """Raised when the fingerprint cannot be computed deterministically.

    The two failure modes are (a) git is unavailable on PATH and
    (b) the requested ``repo_root`` is not inside a git work tree. Both
    are fatal — the staleness guard depends on git's primitives, so we
    refuse to fall back to a non-git hashing path that could silently
    diverge between the emitter and the sync engine.
    """


def _require_git() -> str:
    git = shutil.which('git')
    if git is None:
        raise FingerprintError('git binary not found on PATH')
    return git


def _run_git(repo_root: Path, *args: str) -> str:
    git = _require_git()
    result = subprocess.run(
        [git, '-C', str(repo_root), *args],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip()
        raise FingerprintError(
            f'git {" ".join(args)} (cwd={repo_root}) exited {result.returncode}: {stderr}'
        )
    return result.stdout


def list_tracked_files(repo_root: Path, prefix: str = DEFAULT_PREFIX) -> list[str]:
    """Return the sorted list of tracked paths under ``prefix`` (repo-relative).

    Wraps ``git ls-files {prefix}``. ``ls-files`` already filters to
    tracked paths matching ``.gitignore`` / ``core.excludesfile``, so the
    caller does not need to apply a separate ignore filter.
    """
    raw = _run_git(repo_root, 'ls-files', prefix)
    paths = [line for line in raw.splitlines() if line.strip()]
    paths.sort()
    return paths


def hash_objects(repo_root: Path, paths: list[str]) -> list[str]:
    """Return the git blob SHAs over the WORKTREE bytes of multiple paths.

    Uses ``git hash-object --stdin-paths`` to hash all paths in a single
    subprocess invocation, avoiding the overhead of spawning a process per
    file. This is especially significant on Windows or in repositories with
    many tracked files.

    Returns a list of 40-character hex SHA-1 strings in the same order as
    ``paths``. Raises :class:`FingerprintError` when git is unavailable,
    any subprocess fails, or the output line count does not match the input.
    """
    if not paths:
        return []
    git = _require_git()
    result = subprocess.run(
        [git, '-C', str(repo_root), 'hash-object', '--stdin-paths'],
        input='\n'.join(paths),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip()
        raise FingerprintError(
            f'git hash-object --stdin-paths (cwd={repo_root}) exited {result.returncode}: {stderr}'
        )
    shas = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if len(shas) != len(paths):
        raise FingerprintError(
            f'git hash-object returned {len(shas)} hashes for {len(paths)} paths'
        )
    return shas


def compute_source_tree_fingerprint(
    repo_root: Path, prefix: str = DEFAULT_PREFIX
) -> str:
    """Compute the worktree-content fingerprint over ``{repo_root}/{prefix}``.

    Procedure:

    1. ``git ls-files {prefix}`` -> tracked path list (sorted).
    2. ``git hash-object --stdin-paths`` -> blob SHAs over the worktree bytes
       for all paths in a single subprocess invocation.
    3. ``hashlib.sha1`` of the sorted ``{path}:{blob_sha}\\n`` lines.

    Returns the SHA-1 hex digest. Raises :class:`FingerprintError` when
    git is unavailable or any subprocess fails — the staleness guard
    must refuse rather than compare against a non-deterministic value.
    """
    paths = list_tracked_files(repo_root, prefix)
    shas = hash_objects(repo_root, paths)
    digest = hashlib.sha1()
    for path, blob_sha in zip(paths, shas, strict=True):
        digest.update(f'{path}:{blob_sha}\n'.encode())
    return digest.hexdigest()

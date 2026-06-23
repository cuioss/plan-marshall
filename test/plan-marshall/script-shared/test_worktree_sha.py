#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Unit tests for ``worktree_sha.compute_worktree_sha`` — the single shared
working-tree currency primitive.

The module under test is imported directly (PYTHONPATH-resolved, not an executor
entry point) and exercised against REAL ``git init`` repositories staged under a
unique ``tmp_path``. No git plumbing is mocked: the helper's whole correctness
claim is "the digest reflects the actual working-tree state", so a mocked
subprocess would test nothing real. Coverage:

* happy path — a clean committed repo yields a stable 64-hex sha256 digest;
* clean-tree determinism — two calls on the same clean tree return the same hash;
* tracked-edit detection — an unstaged edit changes the digest (the false-positive
  ``fresh`` the primitive exists to prevent);
* staged-edit detection — a staged-but-uncommitted edit changes the digest;
* untracked-file detection — a brand-new untracked-not-ignored file changes the
  digest (the ``git stash create`` blind-spot the composition deliberately
  avoids);
* gitignored-file invariance — an ignored file does NOT change the digest;
* detached HEAD — a detached-HEAD checkout still resolves a digest (HEAD is a
  real commit sha);
* non-git directory — a directory outside any repo yields ``None``
  (``git rev-parse HEAD`` fails);
* subprocess error — a missing ``git`` binary (OSError from the shell-out)
  surfaces as ``None`` rather than raising.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from worktree_sha import compute_worktree_sha  # type: ignore[import-not-found]

_HEX64 = 64


def _git(repo: Path, *args: str) -> None:
    """Run a git command in ``repo``, raising on failure."""
    subprocess.run(['git', '-C', str(repo), *args], check=True, capture_output=True)


def _init_repo(repo: Path) -> None:
    """Initialise a real git repo with one committed file."""
    subprocess.run(['git', 'init', '-q', '-b', 'main', str(repo)], check=True)
    _git(repo, 'config', 'user.email', 't@t.test')
    _git(repo, 'config', 'user.name', 'Test')
    (repo / 'tracked.txt').write_text('original\n')
    _git(repo, 'add', '.')
    _git(repo, 'commit', '-q', '-m', 'init')


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A real single-commit git repo under a unique tmp_path."""
    root = tmp_path / 'repo'
    root.mkdir()
    _init_repo(root)
    return root


def test_clean_repo_returns_hex_digest(repo: Path) -> None:
    digest = compute_worktree_sha(repo)

    assert digest is not None
    assert len(digest) == _HEX64
    assert all(c in '0123456789abcdef' for c in digest)


def test_clean_tree_is_deterministic(repo: Path) -> None:
    first = compute_worktree_sha(repo)
    second = compute_worktree_sha(repo)

    # A clean tree hashes to a stable function of HEAD alone.
    assert first == second


def test_accepts_str_path(repo: Path) -> None:
    # The signature is ``str | Path``; a str arg must work.
    digest = compute_worktree_sha(str(repo))

    assert digest is not None
    assert len(digest) == _HEX64


def test_unstaged_edit_changes_digest(repo: Path) -> None:
    before = compute_worktree_sha(repo)

    (repo / 'tracked.txt').write_text('modified\n')
    after = compute_worktree_sha(repo)

    # The unstaged diff must move the digest (no false-positive fresh).
    assert before != after


def test_staged_edit_changes_digest(repo: Path) -> None:
    before = compute_worktree_sha(repo)

    (repo / 'tracked.txt').write_text('staged change\n')
    _git(repo, 'add', 'tracked.txt')
    after = compute_worktree_sha(repo)

    # ``git diff HEAD`` covers staged modifications too.
    assert before != after


def test_untracked_file_changes_digest(repo: Path) -> None:
    before = compute_worktree_sha(repo)

    # A brand-new untracked, not-ignored file (a plan's new file).
    (repo / 'brand_new.txt').write_text('new content\n')
    after = compute_worktree_sha(repo)

    # The untracked stream is folded in (the stash-create blind spot).
    assert before != after


def test_untracked_file_content_matters(repo: Path) -> None:
    (repo / 'brand_new.txt').write_text('content A\n')
    first = compute_worktree_sha(repo)

    # Same path, different content.
    (repo / 'brand_new.txt').write_text('content B\n')
    second = compute_worktree_sha(repo)

    # Content (not just presence) contributes to the digest.
    assert first != second


def test_gitignored_file_does_not_change_digest(repo: Path) -> None:
    (repo / '.gitignore').write_text('ignored/\n')
    _git(repo, 'add', '.gitignore')
    _git(repo, 'commit', '-q', '-m', 'add gitignore')
    before = compute_worktree_sha(repo)

    # A file in the ignored dir is excluded by --exclude-standard.
    ignored_dir = repo / 'ignored'
    ignored_dir.mkdir()
    (ignored_dir / 'build.log').write_text('noise\n')
    after = compute_worktree_sha(repo)

    # Ignored content must NOT move the digest.
    assert before == after


def test_detached_head_resolves_digest(repo: Path) -> None:
    # A second commit so there is a prior sha to detach onto.
    (repo / 'tracked.txt').write_text('second\n')
    _git(repo, 'commit', '-aqm', 'second')
    head = subprocess.run(
        ['git', '-C', str(repo), 'rev-parse', 'HEAD'],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    _git(repo, 'checkout', '-q', head)
    digest = compute_worktree_sha(repo)

    # A detached HEAD still resolves a working-tree digest.
    assert digest is not None
    assert len(digest) == _HEX64


def test_non_git_directory_returns_none(tmp_path: Path) -> None:
    plain = tmp_path / 'plain'
    plain.mkdir()

    digest = compute_worktree_sha(plain)

    # ``git rev-parse HEAD`` fails → None, never an exception.
    assert digest is None


def test_repo_with_no_commit_returns_none(tmp_path: Path) -> None:
    # An initialised repo that has no commit yet (HEAD unresolvable).
    empty = tmp_path / 'empty'
    empty.mkdir()
    subprocess.run(['git', 'init', '-q', '-b', 'main', str(empty)], check=True)

    digest = compute_worktree_sha(empty)

    # No commit means no HEAD sha → None.
    assert digest is None


def test_missing_git_binary_returns_none(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Simulate the git binary being absent: the internal shell-out raises OSError,
    # which ``_run_git`` maps to (1, b'').
    import worktree_sha  # type: ignore[import-not-found]

    def _boom(*_args: object, **_kwargs: object) -> None:
        raise OSError('git not found')

    monkeypatch.setattr(worktree_sha.subprocess, 'run', _boom)

    digest = compute_worktree_sha(repo)

    # A subprocess failure surfaces as None, not a raised exception.
    assert digest is None

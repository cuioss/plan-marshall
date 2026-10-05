# SPDX-License-Identifier: FSL-1.1-ALv2
"""Real-git sandbox for the ``orchestrator land`` verb tests.

Builds on :mod:`_orchestrator_worktree_fixtures` — a bare ``origin``, a main
checkout, and a peer clone that moves ``origin`` behind the main checkout's back
— and adds what a land needs on top: the ledger ignore rules the real repository
carries, the ``orchestrator.use_worktree`` knob switched on, a repository-local
git identity (the land module runs ``git commit`` and ``git rebase`` itself, so
the per-call identity the shared ``git`` helper injects never reaches it), and
the shared ledger worktree created through the real seam.

No git call is mocked: every handler under test runs its real git sequence
against these repositories.
"""

from __future__ import annotations

import argparse
import subprocess
from dataclasses import dataclass
from pathlib import Path

import _orchestrator_land
from _orchestrator_worktree_fixtures import (
    LedgerRepo,
    build_ledger_repo,
    commit_file,
    git,
    use_real_resolver,
    write_marshal,
)
from marketplace_paths import resolve_main_anchored_path
from orchestrator_worktree import ORCHESTRATOR_WORKTREE_BRANCH, ensure_orchestrator_worktree

#: The remote head ref a land pushes to, as the bare origin stores it.
REMOTE_HEAD_REF = f'refs/heads/{ORCHESTRATOR_WORKTREE_BRANCH}'

#: The ledger ignore rules of the real repository: the two store roots are
#: tracked, and the per-epic ``logs/`` directory inside them is machine-local.
_GITIGNORE = (
    '.plan/*\n'
    '!.plan/orchestrator/\n'
    '!.plan/archived-orchestrators/\n'
    '.plan/orchestrator/*/logs/\n'
    '.plan/archived-orchestrators/*/logs/\n'
)


@dataclass(frozen=True)
class LandSandbox:
    """One sandbox: the repository topology, the shared ledger tree and its guard file."""

    repo: LedgerRepo
    tree: Path
    guard: Path

    def write(self, relpath: str, content: str) -> Path:
        """Write ``relpath`` inside the shared ledger worktree (uncommitted)."""
        target = self.tree / relpath
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding='utf-8')
        return target

    def ref(self, name: str, *, cwd: Path | None = None) -> str | None:
        """Resolve ``name`` to a SHA in ``cwd`` (default: the ledger tree); ``None`` when absent."""
        result = subprocess.run(
            ['git', 'rev-parse', '--verify', '--quiet', name],
            cwd=cwd or self.tree,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.stdout.strip() if result.returncode == 0 else None

    def marker(self) -> str | None:
        return self.ref(_orchestrator_land.PUSHED_MARKER_REF)

    def bindings(self) -> dict[str, str]:
        """Every PR binding ref in the ledger tree as ``{refname: sha}``."""
        listing = git(
            self.tree, 'for-each-ref', '--format=%(refname) %(objectname)', _orchestrator_land.BINDING_REF_PREFIX
        )
        return dict(line.split(' ', 1) for line in listing.splitlines() if line)

    def remote_head(self) -> str | None:
        """The SHA the bare origin holds for the ledger head branch; ``None`` when absent."""
        return self.ref(REMOTE_HEAD_REF, cwd=self.repo.origin)

    def delete_remote_head(self) -> None:
        git(self.repo.origin, 'update-ref', '-d', REMOTE_HEAD_REF)

    def tree_state(self) -> tuple[str | None, str, str, str | None, dict[str, str]]:
        """Everything a refusal must leave unchanged: HEAD, index, working tree and both refs."""
        return (
            self.ref('HEAD'),
            git(self.tree, 'diff', '--cached', '--name-status'),
            git(self.tree, 'status', '--porcelain=v1', '--untracked-files=all'),
            self.marker(),
            self.bindings(),
        )

    def push_foreign_commit_to_remote_head(self) -> str:
        """Move the remote ledger head branch to a commit the ledger tree does not have."""
        peer = self.repo.peer
        git(peer, 'fetch', 'origin')
        start = f'origin/{ORCHESTRATOR_WORKTREE_BRANCH}' if self.remote_head() else 'origin/main'
        git(peer, 'checkout', '--detach', start)
        sha = commit_file(peer, 'foreign.txt', 'a commit the ledger tree never saw\n')
        git(peer, 'push', 'origin', f'HEAD:{REMOTE_HEAD_REF}')
        git(peer, 'checkout', 'main')
        return sha

    def squash_land(self, *, tamper: str | None = None) -> str:
        """Squash-merge the pushed ledger branch onto ``origin/main``; return the landed SHA.

        ``tamper`` names a path whose content is changed before the squash is
        committed, so the landed content differs from what was pushed.
        """
        peer = self.repo.peer
        git(peer, 'fetch', 'origin')
        git(peer, 'checkout', 'main')
        git(peer, 'pull', 'origin', 'main')
        git(peer, 'merge', '--squash', f'origin/{ORCHESTRATOR_WORKTREE_BRANCH}')
        if tamper is not None:
            (peer / tamper).write_text('content the land never pushed\n', encoding='utf-8')
            git(peer, 'add', tamper)
        git(peer, 'commit', '-m', 'land the orchestrator ledger (squash)')
        git(peer, 'push', 'origin', 'main')
        return git(peer, 'rev-parse', 'HEAD')


def build_land_sandbox(root: Path, monkeypatch) -> LandSandbox:
    """Create the sandbox under ``root`` and stand the caller on its main checkout."""
    repo = build_ledger_repo(root)
    for key, value in (
        ('user.name', 'orchestrator-land-test'),
        ('user.email', 'test@example.com'),
        ('commit.gpgsign', 'false'),
    ):
        git(repo.main, 'config', key, value)
    commit_file(repo.main, '.gitignore', _GITIGNORE)
    git(repo.main, 'push', 'origin', 'main')
    git(repo.peer, 'pull', 'origin', 'main')
    write_marshal(repo.main, {'orchestrator': {'use_worktree': True}})

    use_real_resolver(monkeypatch)
    monkeypatch.chdir(repo.main)
    tree = ensure_orchestrator_worktree()
    guard = resolve_main_anchored_path(_orchestrator_land.LAND_GUARD_FILE)
    return LandSandbox(repo=repo, tree=tree, guard=guard)


def status() -> dict:
    return _orchestrator_land.cmd_land_status(argparse.Namespace())


def snapshot(*, extend: bool = False) -> dict:
    return _orchestrator_land.cmd_land_snapshot(argparse.Namespace(extend=extend))


def bind(pr_number: int) -> dict:
    return _orchestrator_land.cmd_land_bind(argparse.Namespace(pr_number=pr_number))


def resync(pr_number: int, merge_commit_sha: str) -> dict:
    return _orchestrator_land.cmd_land_resync(
        argparse.Namespace(pr_number=pr_number, merge_commit_sha=merge_commit_sha)
    )

# SPDX-License-Identifier: FSL-1.1-ALv2
"""Real-git sandbox helpers for the orchestrator ledger worktree tests.

Every sandbox is a real repository topology with no mocked resolution: a bare
``origin`` remote, a main checkout cloned from it, a linked plan worktree under
the main checkout's ``.plan/local/worktrees/``, and a peer clone that advances
``origin`` behind the main checkout's back. The substrate resolves the main
checkout through ``git rev-parse --git-common-dir`` from the process cwd, so a
test selects "where the caller stands" by ``monkeypatch.chdir`` alone.
"""

import json
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path

import file_ops

# Identity and signing are pinned per call so a developer's global git config
# (a missing identity, mandatory commit signing) cannot decide the outcome.
_GIT_CONFIG = (
    '-c',
    'user.name=orchestrator-worktree-test',
    '-c',
    'user.email=test@example.com',
    '-c',
    'commit.gpgsign=false',
)


def git(cwd: Path, *args: str) -> str:
    """Run a test-controlled git command in ``cwd`` and return its stripped stdout."""
    # argv-list call, never a shell string; 'git' is resolved via PATH on purpose
    # so the fixture works on any CI runner without hardcoding an absolute path.
    result = subprocess.run(
        ['git', *_GIT_CONFIG, *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result.stdout.strip()


def commit_file(checkout: Path, relpath: str, content: str) -> str:
    """Write ``relpath`` in ``checkout``, commit it, and return the new HEAD sha."""
    target = checkout / relpath
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding='utf-8')
    git(checkout, 'add', relpath)
    git(checkout, 'commit', '-m', f'add {relpath}')
    return git(checkout, 'rev-parse', 'HEAD')


def write_marshal(checkout: Path, payload: object) -> Path:
    """Write ``payload`` as the checkout's ``.plan/marshal.json`` and return its path."""
    path = checkout / '.plan' / 'marshal.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding='utf-8')
    return path


def random_plan_id() -> str:
    """Return a fresh plan id in the kebab-case shape real plan ids take."""
    return f'plan-{uuid.uuid4().hex[:12]}'


@dataclass(frozen=True)
class LedgerRepo:
    """The four trees of one sandbox."""

    origin: Path
    main: Path
    plan_worktree: Path
    peer: Path

    @property
    def expected_worktree(self) -> Path:
        """The main-anchored location the shared ledger worktree must occupy."""
        return (self.main / '.plan' / 'local' / 'worktrees' / '_orchestrator').resolve()

    def advance_origin(self, relpath: str) -> str:
        """Push a new commit to ``origin/main`` from the peer clone; return its sha."""
        sha = commit_file(self.peer, relpath, uuid.uuid4().hex)
        git(self.peer, 'push', 'origin', 'main')
        return sha


def build_ledger_repo(root: Path) -> LedgerRepo:
    """Create the origin / main / plan-worktree / peer topology under ``root``."""
    origin = root / 'origin.git'
    git(root, 'init', '--bare', '--initial-branch=main', str(origin))
    main = root / 'main'
    main.mkdir()
    git(main, 'init', '--initial-branch=main')
    git(main, 'remote', 'add', 'origin', str(origin))
    commit_file(main, 'README.md', 'sandbox\n')
    git(main, 'push', '--set-upstream', 'origin', 'main')
    plan_worktree = main / '.plan' / 'local' / 'worktrees' / random_plan_id()
    git(main, 'worktree', 'add', '-b', f'feature/{plan_worktree.name}', str(plan_worktree))
    peer = root / 'peer'
    git(root, 'clone', str(origin), str(peer))
    return LedgerRepo(origin=origin, main=main, plan_worktree=plan_worktree, peer=peer)


def use_real_resolver(monkeypatch) -> None:
    """Clear both base-dir override spellings so resolution runs through git.

    Under ``PLAN_BASE_DIR`` or a ``set_base_dir()`` override the main-anchored
    resolver short-circuits to the override directory, which would make every
    main-anchoring assertion describe the override instead of the repository.
    The clears are setup-time ``monkeypatch`` calls, so monkeypatch's own
    unconditional restore puts the prior values back.
    """
    monkeypatch.delenv('PLAN_BASE_DIR', raising=False)
    monkeypatch.setattr(file_ops, '_BASE_DIR_OVERRIDE', None)

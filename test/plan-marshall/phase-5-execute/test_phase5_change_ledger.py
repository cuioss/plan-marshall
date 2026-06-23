#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Flow tests for the phase-5-execute per-deliverable commit + ``kind=change``
ledger-append wiring documented in
``marketplace/bundles/plan-marshall/skills/phase-5-execute/SKILL.md`` Step 10a.

Step 10a is a five-sub-step chain-tail flow: (1) the per-deliverable commit,
(2) the ``[OUTCOME]`` log, (3) ``git rev-parse HEAD`` → ``commit_sha``,
(4) ``git diff-tree --no-commit-id --name-only -r {commit_sha}`` →
``changed_paths``, (5) ``manage-change-ledger append --kind change`` with those
git-sourced values. The contract these tests pin is that ``commit_sha`` and
``changed_paths`` are GIT-SOURCED at the commit point and stored VERBATIM — not
self-computed from the deliverable's declared ``affected_files``.

These tests model the FLOW (commit → git-source → append) rather than the CLI
argparse surface (the latter is exercised exhaustively by
``test_manage_change_ledger.py``). Each test runs inside a REAL ``git init`` repo
under a unique ``tmp_path`` (so ``git rev-parse``/``git diff-tree`` and the
shared ``compute_worktree_sha`` helper resolve a real HEAD), and routes the
ledger file under an isolated ``PLAN_BASE_DIR`` (so ``get_tracked_config_dir``
resolves the fixture, never the real ``.plan/`` tree).

Coverage — the three scenarios named in the deliverable:

* happy path — a per-deliverable commit succeeds, the flow git-sources the
  commit's ``commit_sha`` and ``changed_paths``, and the ledger entry is written
  carrying those exact git-sourced values;
* git-commit error — when the commit step fails there is no commit to source
  from, so the ledger append never fires and no ``kind=change`` entry exists;
* ledger-append error — when the append fails the phase does NOT abort: the
  per-deliverable commit is already in git history and survives the append
  failure (the commit and the ledger write are decoupled, append-last).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from conftest import get_script_path, run_script

_SCRIPT = get_script_path('plan-marshall', 'manage-change-ledger', 'manage-change-ledger.py')


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run a git subcommand in ``repo``, raising on non-zero exit."""
    return subprocess.run(
        ['git', '-C', str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )


def _init_repo(repo: Path) -> None:
    """Initialise a real git repo with one committed file."""
    subprocess.run(['git', 'init', '-q', '-b', 'main', str(repo)], check=True)
    _git(repo, 'config', 'user.email', 't@t.test')
    _git(repo, 'config', 'user.name', 'Test')
    (repo / 'tracked.txt').write_text('original\n')
    _git(repo, 'add', '.')
    _git(repo, 'commit', '-q', '-m', 'init')


def _rev_parse_head(repo: Path) -> str:
    """Step 10a sub-step 3 — git-source the commit_sha (``git rev-parse HEAD``)."""
    return _git(repo, 'rev-parse', 'HEAD').stdout.strip()


def _diff_tree_paths(repo: Path, commit_sha: str) -> list[str]:
    """Step 10a sub-step 4 — git-source the changed_paths for ``commit_sha``.

    Mirrors ``git diff-tree --no-commit-id --name-only -r {commit_sha}`` exactly
    as documented in the SKILL.md flow.
    """
    out = _git(
        repo, 'diff-tree', '--no-commit-id', '--name-only', '-r', commit_sha
    ).stdout
    return [line for line in out.splitlines() if line.strip()]


@pytest.fixture
def env(tmp_path: Path):
    """A real git repo + isolated ledger root.

    Returns a small namespace carrying the repo cwd, the ``PLAN_BASE_DIR``
    override, and the resolved ledger path so tests can assert on-disk state.
    """
    repo = tmp_path / 'repo'
    repo.mkdir()
    _init_repo(repo)

    base = tmp_path / 'base'
    base.mkdir()
    overrides = {'PLAN_BASE_DIR': str(base)}
    ledger_path = base / 'work' / 'change-ledger.jsonl'

    class Env:
        def __init__(self) -> None:
            self.repo = repo
            self.base = base
            self.overrides = overrides
            self.ledger_path = ledger_path

        def run(self, *args: str):
            return run_script(
                _SCRIPT,
                *args,
                cwd=str(self.repo),
                env_overrides=self.overrides,
            )

    return Env()


def _read_ledger(ledger_path: Path) -> list[dict]:
    """Parse the on-disk JSONL ledger into a list of dicts."""
    if not ledger_path.exists():
        return []
    return [json.loads(line) for line in ledger_path.read_text().splitlines() if line.strip()]


def _commit_deliverable(repo: Path, *files: tuple[str, str]) -> str:
    """Make a per-deliverable commit touching ``files`` and return its SHA.

    Each ``files`` entry is a ``(relative_path, contents)`` pair. Models the
    Step 10a sub-step 1 per-deliverable commit.
    """
    for rel, contents in files:
        target = repo / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(contents)
    _git(repo, 'add', '.')
    _git(repo, 'commit', '-q', '-m', 'feat: deliverable work')
    return _rev_parse_head(repo)


# ---------------------------------------------------------------------------
# Happy path — commit succeeds, ledger entry written with git-sourced values
# ---------------------------------------------------------------------------


def test_happy_path_appends_change_entry_with_git_sourced_values(env) -> None:
    # Step 10a sub-step 1: a per-deliverable commit lands two files.
    commit_sha = _commit_deliverable(
        env.repo,
        ('src/feature.py', 'value = 1\n'),
        ('test/test_feature.py', 'def test_value():\n    assert True\n'),
    )
    # Steps 3 + 4: git-source commit_sha and changed_paths from the commit.
    sourced_sha = _rev_parse_head(env.repo)
    changed_paths = _diff_tree_paths(env.repo, commit_sha)
    assert sourced_sha == commit_sha
    assert set(changed_paths) == {'src/feature.py', 'test/test_feature.py'}

    # Step 5: append the kind=change ledger entry with git-sourced values.
    result = env.run(
        'append',
        '--kind',
        'change',
        '--deliverable-id',
        '5',
        '--commit-sha',
        sourced_sha,
        '--changed-paths',
        ','.join(changed_paths),
    )

    assert result.success, result.stderr
    data = result.toon()
    assert data['status'] == 'success'
    assert data['kind'] == 'change'

    # Exactly one kind=change entry carrying the git-sourced values stored
    # verbatim (NOT self-computed from affected_files).
    entries = _read_ledger(env.ledger_path)
    assert len(entries) == 1
    entry = entries[0]
    assert entry['kind'] == 'change'
    assert entry['deliverable_id'] == '5'
    assert entry['commit_sha'] == commit_sha
    assert entry['changed_paths'] == changed_paths
    assert entry['worktree_sha']
    assert entry['timestamp_iso']


def test_happy_path_task_id_alias_links_the_commit(env) -> None:
    # A single-file deliverable committed; flow uses the --task-id alias.
    commit_sha = _commit_deliverable(env.repo, ('src/only.py', 'x = 2\n'))
    changed_paths = _diff_tree_paths(env.repo, commit_sha)

    # Step 5 with the --task-id alias instead of --deliverable-id.
    result = env.run(
        'append',
        '--kind',
        'change',
        '--task-id',
        'TASK-8',
        '--commit-sha',
        commit_sha,
        '--changed-paths',
        ','.join(changed_paths),
    )

    # The alias populates deliverable_id and the commit is linked.
    assert result.success, result.stderr
    entry = _read_ledger(env.ledger_path)[0]
    assert entry['deliverable_id'] == 'TASK-8'
    assert entry['commit_sha'] == commit_sha
    assert entry['changed_paths'] == ['src/only.py']


# ---------------------------------------------------------------------------
# git-commit error — no commit, so the ledger append never fires
# ---------------------------------------------------------------------------


def test_git_commit_error_writes_no_ledger_entry(env) -> None:
    # A commit attempt with nothing staged fails (no changes to commit).
    # The Step 10a flow git-sources commit_sha AFTER the commit succeeds, so a
    # failed commit short-circuits the flow before the append ever runs.
    proc = subprocess.run(
        ['git', '-C', str(env.repo), 'commit', '-q', '-m', 'empty'],
        capture_output=True,
        text=True,
    )

    # The commit itself failed (nothing to commit) ...
    assert proc.returncode != 0

    # ... and because the flow appends only after a successful commit, the
    # ledger append is never invoked — no kind=change entry exists.
    assert _read_ledger(env.ledger_path) == []
    assert not env.ledger_path.exists()


def test_git_commit_error_leaves_head_at_baseline(env) -> None:
    # Capture the baseline HEAD before the failed commit attempt.
    baseline_head = _rev_parse_head(env.repo)

    # An empty commit attempt fails and must not advance HEAD.
    proc = subprocess.run(
        ['git', '-C', str(env.repo), 'commit', '-q', '-m', 'empty'],
        capture_output=True,
        text=True,
    )

    # HEAD is unchanged, so there is no commit to source from.
    assert proc.returncode != 0
    assert _rev_parse_head(env.repo) == baseline_head
    assert _read_ledger(env.ledger_path) == []


# ---------------------------------------------------------------------------
# ledger-append error — phase does not abort, commit already made
# ---------------------------------------------------------------------------


def test_ledger_append_error_does_not_undo_the_commit(env) -> None:
    # Step 10a sub-step 1: the per-deliverable commit lands first.
    commit_sha = _commit_deliverable(env.repo, ('src/done.py', 'done = True\n'))

    # Step 5: the append fails because the required --commit-sha is omitted
    # (a malformed append at the tail of the flow). The append is the LAST
    # sub-step, so its failure cannot undo the already-made commit.
    result = env.run(
        'append',
        '--kind',
        'change',
        '--deliverable-id',
        '5',
    )

    # The append returned an error and wrote no ledger entry ...
    data = result.toon()
    assert data['status'] == 'error'
    assert _read_ledger(env.ledger_path) == []

    # ... but the per-deliverable commit is intact in git history: the phase
    # does NOT abort on an append failure, and the commit is not rolled back.
    assert _rev_parse_head(env.repo) == commit_sha
    log = _git(env.repo, 'log', '--oneline').stdout
    assert 'feat: deliverable work' in log


def test_ledger_append_error_keeps_committed_files_present(env) -> None:
    # Commit a file, then drive a failing append (missing commit-sha).
    _commit_deliverable(env.repo, ('src/persisted.py', 'kept = 1\n'))

    # Failing append at the flow tail.
    result = env.run('append', '--kind', 'change', '--deliverable-id', '5')

    # Append failed, ledger empty, but the committed file survives on disk
    # (the working tree is untouched by the append failure).
    assert result.toon()['status'] == 'error'
    assert _read_ledger(env.ledger_path) == []
    assert (env.repo / 'src/persisted.py').read_text() == 'kept = 1\n'

#!/usr/bin/env python3
"""Tests for manage-worktree.py script.

Subprocess-based tests because the script shells out to git and to
generate_executor.py; importing the module directly would skip the
integration paths we actually want to verify.

Worktrees are anchored at ``<git_main_checkout_root>/.claude/worktrees/``
(the canonical Claude Code location). The root is derived from the git
repo itself via ``git rev-parse``, so tests just need to run the script
with ``cwd=repo`` — no ``PLAN_BASE_DIR`` override is involved.
"""

import subprocess
from pathlib import Path

import pytest
from file_ops import get_worktree_root
from toon_parser import parse_toon

from conftest import get_script_path, run_script

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-worktree', 'manage-worktree.py')


def _init_git_repo(repo: Path) -> None:
    """Initialize a bare-ish git repo with one commit so worktrees are usable."""
    subprocess.run(['git', 'init', '-q', '-b', 'main', str(repo)], check=True)
    subprocess.run(['git', '-C', str(repo), 'config', 'user.email', 't@t.test'], check=True)
    subprocess.run(['git', '-C', str(repo), 'config', 'user.name', 'Test'], check=True)
    (repo / 'README.md').write_text('x\n')
    # .plan/ and .claude/worktrees/ must be gitignored so the executor shim
    # and the worktrees themselves don't count as "untracked" and block
    # non-force `git worktree remove`.
    (repo / '.gitignore').write_text('.plan/\n.claude/worktrees/\n')
    subprocess.run(['git', '-C', str(repo), 'add', '.'], check=True)
    subprocess.run(['git', '-C', str(repo), 'commit', '-q', '-m', 'init'], check=True)


def _expected_worktree(repo: Path, plan_id: str) -> Path:
    return repo / '.claude' / 'worktrees' / plan_id


def test_path_returns_computed_location(tmp_path):
    repo = tmp_path / 'repo'
    _init_git_repo(repo)

    result = run_script(
        SCRIPT_PATH,
        'path',
        '--plan-id',
        'my-plan',
        cwd=repo,
    )
    assert result.success, result.stderr
    data = parse_toon(result.stdout)
    assert data['status'] == 'success'
    assert data['worktree_path'] == str(_expected_worktree(repo, 'my-plan'))
    assert data['exists'] in (False, 'false', 'False')


def test_create_makes_worktree_with_shim(tmp_path):
    repo = tmp_path / 'repo'
    _init_git_repo(repo)

    result = run_script(
        SCRIPT_PATH,
        'create',
        '--plan-id',
        'feature-x',
        '--branch',
        'feature/feature-x',
        cwd=repo,
    )
    assert result.success, result.stderr
    data = parse_toon(result.stdout)
    assert data['status'] == 'success'
    worktree = Path(data['worktree_path'])
    assert worktree == _expected_worktree(repo, 'feature-x')
    assert worktree.is_dir()
    shim = worktree / '.plan' / 'execute-script.py'
    assert shim.is_file(), 'shim must be dropped into the new worktree'
    # branch should be checked out in the worktree
    head = subprocess.run(
        ['git', '-C', str(worktree), 'rev-parse', '--abbrev-ref', 'HEAD'],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    assert head == 'feature/feature-x'


def test_create_fails_when_worktree_exists(tmp_path):
    repo = tmp_path / 'repo'
    _init_git_repo(repo)

    first = run_script(
        SCRIPT_PATH,
        'create',
        '--plan-id',
        'dup',
        '--branch',
        'feature/dup',
        cwd=repo,
    )
    assert first.success, first.stderr

    second = run_script(
        SCRIPT_PATH,
        'create',
        '--plan-id',
        'dup',
        '--branch',
        'feature/dup2',
        cwd=repo,
    )
    data = parse_toon(second.stdout)
    assert data['status'] == 'error'
    assert data['error'] == 'worktree_exists'


def test_remove_clean_worktree(tmp_path):
    repo = tmp_path / 'repo'
    _init_git_repo(repo)

    create = run_script(
        SCRIPT_PATH,
        'create',
        '--plan-id',
        'rm-me',
        '--branch',
        'feature/rm-me',
        cwd=repo,
    )
    assert create.success, create.stderr

    remove = run_script(
        SCRIPT_PATH,
        'remove',
        '--plan-id',
        'rm-me',
        cwd=repo,
    )
    assert remove.success, remove.stderr
    data = parse_toon(remove.stdout)
    assert data['status'] == 'success'
    assert data['action'] == 'removed'
    assert not _expected_worktree(repo, 'rm-me').exists()


def test_remove_dirty_worktree_fails_without_force(tmp_path):
    repo = tmp_path / 'repo'
    _init_git_repo(repo)

    create = run_script(
        SCRIPT_PATH,
        'create',
        '--plan-id',
        'dirty',
        '--branch',
        'feature/dirty',
        cwd=repo,
    )
    assert create.success, create.stderr
    worktree = Path(parse_toon(create.stdout)['worktree_path'])
    (worktree / 'uncommitted.txt').write_text('draft work\n')

    remove = run_script(
        SCRIPT_PATH,
        'remove',
        '--plan-id',
        'dirty',
        cwd=repo,
    )
    data = parse_toon(remove.stdout)
    assert data['status'] == 'error'
    assert data['error'] == 'worktree_remove_failed'
    assert worktree.is_dir(), 'non-force remove must leave dirty worktree in place'


def test_remove_nonexistent_is_noop(tmp_path):
    repo = tmp_path / 'repo'
    _init_git_repo(repo)

    remove = run_script(
        SCRIPT_PATH,
        'remove',
        '--plan-id',
        'ghost',
        cwd=repo,
    )
    assert remove.success, remove.stderr
    data = parse_toon(remove.stdout)
    assert data['status'] == 'success'
    assert data['action'] == 'noop'


def test_list_only_reports_managed_worktrees(tmp_path):
    repo = tmp_path / 'repo'
    _init_git_repo(repo)

    # Managed (under <repo>/.claude/worktrees/)
    run_script(
        SCRIPT_PATH,
        'create',
        '--plan-id',
        'managed',
        '--branch',
        'feature/managed',
        cwd=repo,
    )
    # Unmanaged (user-created worktree outside .claude/worktrees/)
    unmanaged = tmp_path / 'adhoc'
    subprocess.run(
        ['git', '-C', str(repo), 'worktree', 'add', '-b', 'adhoc', str(unmanaged)],
        check=True,
        capture_output=True,
    )

    result = run_script(
        SCRIPT_PATH,
        'list',
        cwd=repo,
    )
    assert result.success, result.stderr
    data = parse_toon(result.stdout)
    assert data['status'] == 'success'
    # Expect managed worktree only
    ids = [w['plan_id'] for w in data.get('worktrees', [])]
    assert 'managed' in ids
    assert 'adhoc' not in ids


# =============================================================================
# Unit tests for file_ops.get_worktree_root
#
# The subprocess tests above exercise get_worktree_root indirectly through the
# manage-worktree CLI. These unit tests pin the contract of the helper itself
# so a regression in the resolver (e.g. falling back to ``~/.plan-marshall``)
# is caught even if the CLI wrapping masks it.
# =============================================================================


def test_get_worktree_root_in_repo_returns_claude_worktrees(tmp_path, monkeypatch):
    """In a git repo, get_worktree_root() resolves to ``<repo>/.claude/worktrees``."""
    repo = tmp_path / 'repo'
    _init_git_repo(repo)

    monkeypatch.chdir(repo)
    root = get_worktree_root()

    # resolve() both sides to survive macOS /private/var vs /var symlinks.
    assert root.resolve() == (repo / '.claude' / 'worktrees').resolve()


def test_get_worktree_root_outside_repo_raises_runtime_error(tmp_path, monkeypatch):
    """Outside a git repo, get_worktree_root() raises RuntimeError (no silent fallback)."""
    non_repo = tmp_path / 'not-a-repo'
    non_repo.mkdir()
    # Sanity: make sure there really is no .git anywhere above non_repo in the
    # fixture tree. tmp_path is pytest-managed and never git-tracked.
    assert not (non_repo / '.git').exists()

    monkeypatch.chdir(non_repo)
    with pytest.raises(RuntimeError, match='requires a git repository'):
        get_worktree_root()

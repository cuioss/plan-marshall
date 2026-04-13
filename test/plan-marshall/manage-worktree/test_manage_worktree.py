#!/usr/bin/env python3
"""Tests for manage-worktree.py script.

Subprocess-based tests because the script shells out to git and to
generate_executor.py; importing the module directly would skip the
integration paths we actually want to verify.
"""

import subprocess
from pathlib import Path

from toon_parser import parse_toon

from conftest import get_script_path, run_script

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-worktree', 'manage-worktree.py')


def _init_git_repo(repo: Path) -> None:
    """Initialize a bare-ish git repo with one commit so worktrees are usable."""
    subprocess.run(['git', 'init', '-q', '-b', 'main', str(repo)], check=True)
    subprocess.run(['git', '-C', str(repo), 'config', 'user.email', 't@t.test'], check=True)
    subprocess.run(['git', '-C', str(repo), 'config', 'user.name', 'Test'], check=True)
    (repo / 'README.md').write_text('x\n')
    # .plan/ must be gitignored so the executor shim dropped into each
    # worktree's .plan/ does not count as "untracked" and block
    # non-force `git worktree remove`.
    (repo / '.gitignore').write_text('.plan/\n')
    subprocess.run(['git', '-C', str(repo), 'add', '.'], check=True)
    subprocess.run(['git', '-C', str(repo), 'commit', '-q', '-m', 'init'], check=True)


def test_path_returns_computed_location(tmp_path):
    repo = tmp_path / 'repo'
    _init_git_repo(repo)
    base_dir = tmp_path / 'global'
    base_dir.mkdir()

    result = run_script(
        SCRIPT_PATH,
        'path',
        '--plan-id',
        'my-plan',
        cwd=repo,
        env_overrides={'PLAN_BASE_DIR': str(base_dir)},
    )
    assert result.success, result.stderr
    data = parse_toon(result.stdout)
    assert data['status'] == 'success'
    assert data['worktree_path'] == str(base_dir / 'worktrees' / 'my-plan')
    assert data['exists'] in (False, 'false', 'False')


def test_create_makes_worktree_with_shim(tmp_path):
    repo = tmp_path / 'repo'
    _init_git_repo(repo)
    base_dir = tmp_path / 'global'
    base_dir.mkdir()

    result = run_script(
        SCRIPT_PATH,
        'create',
        '--plan-id',
        'feature-x',
        '--branch',
        'feature/feature-x',
        cwd=repo,
        env_overrides={'PLAN_BASE_DIR': str(base_dir)},
    )
    assert result.success, result.stderr
    data = parse_toon(result.stdout)
    assert data['status'] == 'success'
    worktree = Path(data['worktree_path'])
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
    base_dir = tmp_path / 'global'
    base_dir.mkdir()

    first = run_script(
        SCRIPT_PATH,
        'create',
        '--plan-id',
        'dup',
        '--branch',
        'feature/dup',
        cwd=repo,
        env_overrides={'PLAN_BASE_DIR': str(base_dir)},
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
        env_overrides={'PLAN_BASE_DIR': str(base_dir)},
    )
    data = parse_toon(second.stdout)
    assert data['status'] == 'error'
    assert data['error'] == 'worktree_exists'


def test_remove_clean_worktree(tmp_path):
    repo = tmp_path / 'repo'
    _init_git_repo(repo)
    base_dir = tmp_path / 'global'
    base_dir.mkdir()

    create = run_script(
        SCRIPT_PATH,
        'create',
        '--plan-id',
        'rm-me',
        '--branch',
        'feature/rm-me',
        cwd=repo,
        env_overrides={'PLAN_BASE_DIR': str(base_dir)},
    )
    assert create.success, create.stderr

    remove = run_script(
        SCRIPT_PATH,
        'remove',
        '--plan-id',
        'rm-me',
        cwd=repo,
        env_overrides={'PLAN_BASE_DIR': str(base_dir)},
    )
    assert remove.success, remove.stderr
    data = parse_toon(remove.stdout)
    assert data['status'] == 'success'
    assert data['action'] == 'removed'
    assert not (base_dir / 'worktrees' / 'rm-me').exists()


def test_remove_dirty_worktree_fails_without_force(tmp_path):
    repo = tmp_path / 'repo'
    _init_git_repo(repo)
    base_dir = tmp_path / 'global'
    base_dir.mkdir()

    create = run_script(
        SCRIPT_PATH,
        'create',
        '--plan-id',
        'dirty',
        '--branch',
        'feature/dirty',
        cwd=repo,
        env_overrides={'PLAN_BASE_DIR': str(base_dir)},
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
        env_overrides={'PLAN_BASE_DIR': str(base_dir)},
    )
    data = parse_toon(remove.stdout)
    assert data['status'] == 'error'
    assert data['error'] == 'worktree_remove_failed'
    assert worktree.is_dir(), 'non-force remove must leave dirty worktree in place'


def test_remove_nonexistent_is_noop(tmp_path):
    repo = tmp_path / 'repo'
    _init_git_repo(repo)
    base_dir = tmp_path / 'global'
    base_dir.mkdir()

    remove = run_script(
        SCRIPT_PATH,
        'remove',
        '--plan-id',
        'ghost',
        cwd=repo,
        env_overrides={'PLAN_BASE_DIR': str(base_dir)},
    )
    assert remove.success, remove.stderr
    data = parse_toon(remove.stdout)
    assert data['status'] == 'success'
    assert data['action'] == 'noop'


def test_list_only_reports_managed_worktrees(tmp_path):
    repo = tmp_path / 'repo'
    _init_git_repo(repo)
    base_dir = tmp_path / 'global'
    base_dir.mkdir()

    # Managed (under base_dir/worktrees/)
    run_script(
        SCRIPT_PATH,
        'create',
        '--plan-id',
        'managed',
        '--branch',
        'feature/managed',
        cwd=repo,
        env_overrides={'PLAN_BASE_DIR': str(base_dir)},
    )
    # Unmanaged (user-created worktree outside the plan-marshall tree)
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
        env_overrides={'PLAN_BASE_DIR': str(base_dir)},
    )
    assert result.success, result.stderr
    data = parse_toon(result.stdout)
    assert data['status'] == 'success'
    # Expect managed worktree only
    ids = [w['plan_id'] for w in data.get('worktrees', [])]
    assert 'managed' in ids
    assert 'adhoc' not in ids

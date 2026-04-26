#!/usr/bin/env python3
"""Tests for manage-worktree.py script.

Worktrees are anchored at ``<git_main_checkout_root>/.claude/worktrees/``
(the canonical Claude Code location). Most tests shell out to the CLI
because the script calls ``git worktree add``; importing the module
directly would skip that integration path.

Narrowed-scope symlink contract (post-lesson 2026-04-14-006):

After ``git worktree add``, the script leaves ``{worktree}/.plan`` as a
real directory materialized by git (so tracked files like
``marshal.json`` and ``project-architecture/`` are per-worktree and
version-controlled). Only two gitignored paths are symlinked back into
the main checkout so runtime state and the executor stay shared:

* ``{worktree}/.plan/local`` → ``{main}/.plan/local`` (per-plan state)
* ``{worktree}/.plan/execute-script.py`` → ``{main}/.plan/execute-script.py``

Tests 3 and 4 exercise ``_ensure_worktree_plan_symlinks`` directly via
``importlib`` because the ``cmd_create`` entry point refuses to run
against an existing worktree — the symlink helper's error and
replacement paths are easier to probe in isolation.

The worktree root is derived from the git repo itself via
``git rev-parse``, so tests just run the script with ``cwd=repo`` — no
``PLAN_BASE_DIR`` override is involved.
"""

import importlib.util
import os
import subprocess
from pathlib import Path

import pytest
from file_ops import get_worktree_root
from toon_parser import parse_toon

from conftest import get_script_path, run_script

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-worktree', 'manage-worktree.py')


def _load_manage_worktree_module():
    """Import manage-worktree.py as a module for direct function access.

    The filename is hyphenated (``manage-worktree.py``), so a standard
    ``import`` statement is not usable. ``importlib.util`` loads the
    file under the sanitized name ``manage_worktree_under_test``.
    """
    spec = importlib.util.spec_from_file_location(
        'manage_worktree_under_test', str(SCRIPT_PATH)
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _init_git_repo(repo: Path) -> None:
    """Initialize a git repo with tracked ``.plan/`` content plus a narrow gitignore.

    The fixture mirrors the real plan-marshall repo layout: tracked
    files under ``.plan/`` (e.g. ``marshal.json``, ``project-architecture/``)
    are committed, while only the runtime subpaths that the worktree
    script symlinks (``.plan/local`` and ``.plan/execute-script.py``) and
    the worktree root (``.claude/worktrees/``) are gitignored. This
    ensures ``git worktree add`` materializes the tracked ``.plan``
    content inside each new worktree.
    """
    subprocess.run(['git', 'init', '-q', '-b', 'main', str(repo)], check=True)
    subprocess.run(['git', '-C', str(repo), 'config', 'user.email', 't@t.test'], check=True)
    subprocess.run(['git', '-C', str(repo), 'config', 'user.name', 'Test'], check=True)
    (repo / 'README.md').write_text('x\n')

    # Tracked content under .plan/ — committed so git worktree add
    # materializes these files inside every new worktree as regular
    # per-worktree files. Keeps parity with the real plan-marshall repo.
    plan_dir = repo / '.plan'
    plan_dir.mkdir(exist_ok=True)
    (plan_dir / 'marshal.json').write_text('{"system": {}, "plan": {}}\n')
    arch_dir = plan_dir / 'project-architecture'
    arch_dir.mkdir(exist_ok=True)
    (arch_dir / 'README.md').write_text('architecture placeholder\n')

    # Narrow gitignore: only the runtime subpaths that get symlinked
    # into the main checkout and the worktree root itself are ignored.
    # Everything else under .plan/ (marshal.json, project-architecture/,
    # etc.) stays tracked.
    (repo / '.gitignore').write_text(
        '.plan/local\n'
        '.plan/execute-script.py\n'
        '.claude/worktrees/\n'
    )
    subprocess.run(['git', '-C', str(repo), 'add', '.'], check=True)
    subprocess.run(['git', '-C', str(repo), 'commit', '-q', '-m', 'init'], check=True)


def _seed_main_shared_plan_paths(repo: Path) -> tuple[Path, Path]:
    """Create the main-checkout symlink targets used by the worktree script.

    The two shared subpaths under ``.plan/`` must exist in the main
    checkout before ``_ensure_worktree_plan_symlinks`` runs, otherwise
    the symlinks it creates would dangle on creation.

    Returns:
        Tuple ``(local_dir, executor_file)`` of absolute paths in the
        main checkout.
    """
    main_plan = repo / '.plan'
    main_plan.mkdir(exist_ok=True)
    local_dir = main_plan / 'local'
    local_dir.mkdir(exist_ok=True)
    executor_file = main_plan / 'execute-script.py'
    if not executor_file.exists():
        executor_file.write_text('#!/usr/bin/env python3\n')
    return local_dir, executor_file


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


def test_create_makes_worktree_with_plan_symlink(tmp_path):
    """Worktree create leaves .plan real but symlinks shared runtime subpaths."""
    repo = tmp_path / 'repo'
    _init_git_repo(repo)
    # The shared subpaths must exist in the main checkout so the
    # worktree script can create symlinks pointing at them.
    main_local, main_executor = _seed_main_shared_plan_paths(repo)

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

    # .plan itself must be a real directory (materialized by git from
    # tracked content), NOT a symlink.
    worktree_plan = worktree / '.plan'
    assert worktree_plan.is_dir(), '.plan must be a real directory in the worktree'
    assert not worktree_plan.is_symlink(), '.plan must not be a symlink anymore'

    # Tracked content committed in _init_git_repo must show up as real
    # per-worktree files.
    worktree_marshal = worktree_plan / 'marshal.json'
    assert worktree_marshal.is_file()
    assert not worktree_marshal.is_symlink()
    worktree_arch = worktree_plan / 'project-architecture' / 'README.md'
    assert worktree_arch.is_file()

    # The two gitignored runtime subpaths must be symlinks pointing
    # back at the main checkout's copies.
    local_link = worktree_plan / 'local'
    assert local_link.is_symlink(), '.plan/local must be a symlink'
    assert local_link.resolve() == main_local.resolve()

    executor_link = worktree_plan / 'execute-script.py'
    assert executor_link.is_symlink(), '.plan/execute-script.py must be a symlink'
    assert executor_link.resolve() == main_executor.resolve()

    # branch should be checked out in the worktree
    head = subprocess.run(
        ['git', '-C', str(worktree), 'rev-parse', '--abbrev-ref', 'HEAD'],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    assert head == 'feature/feature-x'


def test_ensure_worktree_plan_symlinks_refuses_real_local_dir(tmp_path, monkeypatch):
    """_ensure_worktree_plan_symlinks must refuse a pre-existing real .plan/local dir.

    This is the guard that protects against silently clobbering user
    data: if a worktree ends up with a real ``.plan/local`` directory
    (for whatever reason — manual creation, stale state, tool bug),
    the helper must return an error naming the offending subpath
    rather than deleting the directory.

    We invoke the helper directly because ``cmd_create`` refuses to run
    against an existing worktree, making it impractical to reach this
    branch via the CLI in a single test.
    """
    repo = tmp_path / 'repo'
    _init_git_repo(repo)
    main_local, _ = _seed_main_shared_plan_paths(repo)

    # Materialize a worktree manually (bypassing the script's symlink
    # helper) so we can plant a real .plan/local directory inside it.
    worktree = _expected_worktree(repo, 'stale-real')
    worktree.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ['git', '-C', str(repo), 'worktree', 'add', '-b', 'feature/stale-real', str(worktree)],
        check=True,
        capture_output=True,
    )
    # Pre-seed a real .plan/local directory with content. The tracked
    # .plan dir already exists from `git worktree add`, so just add the
    # offending subdir.
    real_local = worktree / '.plan' / 'local'
    real_local.mkdir(parents=True, exist_ok=True)
    (real_local / 'user-data.txt').write_text('important\n')

    module = _load_manage_worktree_module()
    # The helper uses os.getcwd() via git_main_checkout_root, so run it
    # from inside the repo.
    monkeypatch.chdir(repo)
    ok, err = module._ensure_worktree_plan_symlinks(worktree)

    assert ok is False
    assert '.plan/local' in err or str(real_local) in err, (
        f'error must name the offending subpath, got: {err}'
    )
    # User data must still be present — the guard must not delete it.
    assert (real_local / 'user-data.txt').read_text() == 'important\n'
    # And the main-checkout target must be untouched.
    assert main_local.is_dir()


def test_ensure_worktree_plan_symlinks_replaces_stale_symlink(tmp_path, monkeypatch):
    """A pre-existing symlink pointing at the wrong target must be replaced."""
    repo = tmp_path / 'repo'
    _init_git_repo(repo)
    main_local, main_executor = _seed_main_shared_plan_paths(repo)

    # Manually create a worktree so we can plant a stale symlink before
    # invoking the helper.
    worktree = _expected_worktree(repo, 'stale-link')
    worktree.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ['git', '-C', str(repo), 'worktree', 'add', '-b', 'feature/stale-link', str(worktree)],
        check=True,
        capture_output=True,
    )

    # Plant a stale symlink for .plan/local pointing somewhere wrong.
    wrong_target = tmp_path / 'not-the-real-local'
    wrong_target.mkdir()
    stale_link = worktree / '.plan' / 'local'
    # Parent .plan already exists (real dir from git worktree add).
    os.symlink(wrong_target, stale_link, target_is_directory=True)
    assert stale_link.is_symlink()
    assert stale_link.resolve() == wrong_target.resolve()

    module = _load_manage_worktree_module()
    monkeypatch.chdir(repo)
    ok, err = module._ensure_worktree_plan_symlinks(worktree)

    assert ok, f'helper must succeed when replacing stale symlink, got: {err}'
    # The symlink should now point at the main checkout's .plan/local.
    assert stale_link.is_symlink()
    assert stale_link.resolve() == main_local.resolve()
    # And the executor symlink should also have been created.
    executor_link = worktree / '.plan' / 'execute-script.py'
    assert executor_link.is_symlink()
    assert executor_link.resolve() == main_executor.resolve()


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


# =============================================================================
# Pre-bootstrap pyprojectx (best-effort)
# =============================================================================


def _make_fake_pw(worktree: Path, exit_code: int = 0, stderr: str = '') -> Path:
    """Plant a tiny shell script named ``pw`` in the worktree.

    Bash is used directly so the wrapper does not depend on Python or
    pyprojectx — the tests just need to observe the bootstrap subprocess
    exit code and stderr handling.
    """
    pw = worktree / 'pw'
    body = '#!/usr/bin/env bash\n'
    if stderr:
        body += f'echo "{stderr}" 1>&2\n'
    body += f'exit {exit_code}\n'
    pw.write_text(body)
    pw.chmod(0o755)
    return pw


def test_bootstrap_pyprojectx_returns_skipped_when_pw_missing(tmp_path):
    module = _load_manage_worktree_module()
    status, detail = module._bootstrap_pyprojectx(tmp_path)
    assert status == 'skipped'
    assert 'no pw wrapper' in detail


def test_bootstrap_pyprojectx_returns_ok_on_success(tmp_path):
    module = _load_manage_worktree_module()
    _make_fake_pw(tmp_path, exit_code=0)
    status, detail = module._bootstrap_pyprojectx(tmp_path)
    assert status == 'ok'
    assert detail == ''


def test_bootstrap_pyprojectx_returns_warning_on_failure(tmp_path):
    module = _load_manage_worktree_module()
    _make_fake_pw(tmp_path, exit_code=2, stderr='uv: command not found')
    status, detail = module._bootstrap_pyprojectx(tmp_path)
    assert status == 'warning'
    assert 'uv: command not found' in detail


def test_create_records_bootstrap_skipped_when_no_pw(tmp_path):
    """cmd_create returns success with bootstrap=skipped when worktree has no pw wrapper."""
    repo = tmp_path / 'repo'
    _init_git_repo(repo)
    _seed_main_shared_plan_paths(repo)

    result = run_script(
        SCRIPT_PATH,
        'create',
        '--plan-id',
        'no-pw',
        '--branch',
        'feature/no-pw',
        cwd=repo,
    )
    assert result.success, result.stderr
    data = parse_toon(result.stdout)
    assert data['status'] == 'success'
    assert data['bootstrap'] == 'skipped'
    assert 'bootstrap_warning' not in data

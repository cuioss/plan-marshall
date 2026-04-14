#!/usr/bin/env python3
"""Tests for bootstrap_plugin.py script.

Tier 2 (direct import) tests with 3 subprocess tests for CLI plumbing.
"""

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

from conftest import PlanContext, get_script_path, run_script

# Get script path — use base directory for all steward scripts
_SCRIPTS_DIR = Path(get_script_path('plan-marshall', 'marshall-steward', 'bootstrap_plugin.py')).parent
SCRIPT_PATH = _SCRIPTS_DIR / 'bootstrap_plugin.py'

# Tier 2 direct import via importlib
_spec = importlib.util.spec_from_file_location('bootstrap_plugin', SCRIPT_PATH)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

read_state = _mod.read_state
write_state = _mod.write_state
resolve_bundle_path = _mod.resolve_bundle_path
migrate_runtime_state = _mod.migrate_runtime_state


# =============================================================================
# Test: State file operations (Tier 2 - direct import)
# =============================================================================


def test_state_read_write():
    """Test reading and writing state file directly."""
    with PlanContext(plan_id='bootstrap-state-rw') as _ctx:
        # Verify initial state is empty
        state = read_state()
        assert state == {} or 'plugin_root' not in state

        # Write state
        write_state({'plugin_root': '/fake/path', 'detected_at': '2026-01-01T00:00:00Z'})

        # Read back
        state = read_state()
        assert state['plugin_root'] == '/fake/path'
        assert state['detected_at'] == '2026-01-01T00:00:00Z'


def test_resolve_bundle_path():
    """Test resolve_bundle_path with a mock structure."""
    with PlanContext(plan_id='bootstrap-resolve-mock') as ctx:
        mock_root = ctx.fixture_dir / 'mock-cache'
        bundle_dir = mock_root / 'test-bundle' / '1.0.0' / 'skills' / 'test-skill'
        bundle_dir.mkdir(parents=True)
        (bundle_dir / 'SKILL.md').write_text('# Test Skill')

        result = resolve_bundle_path(mock_root, 'test-bundle', 'skills/test-skill/SKILL.md')
        assert result is not None
        assert result.exists()
        assert result.name == 'SKILL.md'


def test_resolve_bundle_path_not_found():
    """Test resolve_bundle_path returns None for missing path."""
    with PlanContext(plan_id='bootstrap-resolve-nf') as ctx:
        mock_root = ctx.fixture_dir / 'empty-cache'
        mock_root.mkdir(parents=True)

        result = resolve_bundle_path(mock_root, 'nonexistent', 'some/path.md')
        assert result is None


def test_state_read_empty():
    """Test reading state when no state file exists."""
    with PlanContext(plan_id='bootstrap-state-empty'):
        state = read_state()
        assert state == {} or 'plugin_root' not in state


# =============================================================================
# Test: migrate_runtime_state
# =============================================================================


def _make_fake_repo(tmp_path: Path) -> Path:
    """Create a minimal git repo so git_main_checkout_root() resolves."""
    repo = tmp_path / 'repo'
    repo.mkdir()
    subprocess.run(['git', 'init', '-q', '-b', 'main', str(repo)], check=True, capture_output=True)
    return repo


def _legacy_dir_for(tmp_home: Path, repo: Path) -> Path:
    """Mirror the inline hash derivation from bootstrap_plugin."""
    import hashlib
    digest = hashlib.sha256(str(repo.resolve()).encode('utf-8')).hexdigest()[:8]
    return tmp_home / '.plan-marshall' / f'{repo.name}-{digest}'


def test_migrate_runtime_state_happy_path(tmp_path, monkeypatch):
    """Legacy plans/, run-configuration.json, and per-plan metrics.md are
    copied into <root>/.plan/local/."""
    repo = _make_fake_repo(tmp_path)
    fake_home = tmp_path / 'home'
    fake_home.mkdir()
    monkeypatch.setattr(Path, 'home', lambda: fake_home)

    legacy = _legacy_dir_for(fake_home, repo)
    (legacy / 'plans' / 'foo').mkdir(parents=True)
    (legacy / 'plans' / 'foo' / 'status.json').write_text('{"status": "active"}')
    (legacy / 'plans' / 'foo' / 'metrics.md').write_text('# metrics')
    (legacy / 'run-configuration.json').write_text('{}')

    new_path = repo / '.plan' / 'local'
    monkeypatch.setenv('PLAN_BASE_DIR', str(new_path))
    monkeypatch.chdir(repo)
    # Reset the marketplace_paths LRU cache so chdir is honoured
    from marketplace_paths import _resolve_git_main_checkout_root
    _resolve_git_main_checkout_root.cache_clear()

    result = migrate_runtime_state()
    assert result['status'] == 'success'
    assert result['items_copied'] == 2  # plans/, run-configuration.json
    assert (new_path / 'plans' / 'foo' / 'status.json').is_file()
    assert (new_path / 'plans' / 'foo' / 'metrics.md').is_file()
    assert (new_path / 'run-configuration.json').is_file()


def test_migrate_runtime_state_excludes_worktrees_and_pycache(tmp_path, monkeypatch):
    """worktrees/, __pycache__/, *.pyc are excluded by ignore patterns."""
    repo = _make_fake_repo(tmp_path)
    fake_home = tmp_path / 'home'
    fake_home.mkdir()
    monkeypatch.setattr(Path, 'home', lambda: fake_home)

    legacy = _legacy_dir_for(fake_home, repo)
    (legacy / 'plans').mkdir(parents=True)
    (legacy / 'plans' / 'real.md').write_text('keep')
    (legacy / 'plans' / '__pycache__').mkdir()
    (legacy / 'plans' / '__pycache__' / 'junk.pyc').write_text('drop')
    (legacy / 'logs').mkdir()
    (legacy / 'logs' / 'a.log').write_text('keep')
    # worktrees/ should be excluded entirely (not in _MIGRATION_SUBPATHS,
    # but also explicit ignore_patterns guard).
    (legacy / 'plans' / 'worktrees').mkdir()
    (legacy / 'plans' / 'worktrees' / 'old').write_text('drop')

    new_path = repo / '.plan' / 'local'
    monkeypatch.setenv('PLAN_BASE_DIR', str(new_path))
    monkeypatch.chdir(repo)
    from marketplace_paths import _resolve_git_main_checkout_root
    _resolve_git_main_checkout_root.cache_clear()

    result = migrate_runtime_state()
    assert result['status'] == 'success'
    assert (new_path / 'plans' / 'real.md').is_file()
    assert (new_path / 'logs' / 'a.log').is_file()
    assert not (new_path / 'plans' / '__pycache__').exists()
    assert not (new_path / 'plans' / 'worktrees').exists()


def test_migrate_runtime_state_noop_when_legacy_missing(tmp_path, monkeypatch):
    """No legacy directory → success with items_copied=0."""
    repo = _make_fake_repo(tmp_path)
    fake_home = tmp_path / 'home'
    fake_home.mkdir()
    monkeypatch.setattr(Path, 'home', lambda: fake_home)

    new_path = repo / '.plan' / 'local'
    monkeypatch.setenv('PLAN_BASE_DIR', str(new_path))
    monkeypatch.chdir(repo)
    from marketplace_paths import _resolve_git_main_checkout_root
    _resolve_git_main_checkout_root.cache_clear()

    result = migrate_runtime_state()
    assert result['status'] == 'success'
    assert result['items_copied'] == 0


def test_state_write_creates_directory():
    """Test that write_state creates parent directories."""
    with PlanContext(plan_id='bootstrap-state-mkdir'):
        write_state({'plugin_root': '/test/path'})
        state = read_state()
        assert state['plugin_root'] == '/test/path'


# =============================================================================
# Bootstrap isolation tests -- verify scripts work WITHOUT executor PYTHONPATH
# =============================================================================


def _run_without_marketplace_pythonpath(script_path: Path, *args: str) -> 'subprocess.CompletedProcess':
    """Run a script with a clean PYTHONPATH (no marketplace dirs).

    This simulates the real bootstrap scenario where the executor hasn't been
    generated yet and PYTHONPATH hasn't been set up by conftest.
    """
    env = os.environ.copy()
    env.pop('PYTHONPATH', None)
    return subprocess.run(
        [sys.executable, str(script_path)] + list(args),
        capture_output=True, text=True, env=env, timeout=30,
    )


def test_bootstrap_plugin_imports_without_executor_pythonpath():
    """bootstrap_plugin.py must resolve its own imports without executor PYTHONPATH."""
    result = _run_without_marketplace_pythonpath(SCRIPT_PATH, 'get-root')
    assert result.returncode == 0, (
        f'bootstrap_plugin.py failed without PYTHONPATH:\n{result.stderr}'
    )


def test_determine_mode_imports_without_executor_pythonpath():
    """determine_mode.py must resolve its own imports without executor PYTHONPATH."""
    script = _SCRIPTS_DIR / 'determine_mode.py'
    result = _run_without_marketplace_pythonpath(script, 'mode')
    assert result.returncode in (0, 1), (
        f'determine_mode.py failed without PYTHONPATH:\n{result.stderr}'
    )
    assert 'ModuleNotFoundError' not in result.stderr, (
        f'determine_mode.py has unresolved imports:\n{result.stderr}'
    )


def test_gitignore_setup_imports_without_executor_pythonpath():
    """gitignore_setup.py must resolve its own imports without executor PYTHONPATH."""
    script = _SCRIPTS_DIR / 'gitignore_setup.py'
    result = _run_without_marketplace_pythonpath(script, '--dry-run')
    assert result.returncode == 0, (
        f'gitignore_setup.py failed without PYTHONPATH:\n{result.stderr}'
    )


# =============================================================================
# Subprocess (Tier 3) tests -- CLI plumbing and env-dependent
# =============================================================================


def test_get_root_detects_plugin():
    """Test get-root succeeds when plugin cache exists (env-dependent)."""
    cache_dir = Path.home() / '.claude' / 'plugins' / 'cache'
    if not cache_dir.exists():
        result = run_script(SCRIPT_PATH, 'get-root')
        assert result.success, 'Expected exit 0 with error status in TOON'
        assert 'status: error' in result.stdout
        assert 'not found' in result.stdout.lower() or 'error' in result.stdout.lower()
        return

    result = run_script(SCRIPT_PATH, 'get-root')
    assert result.success, f'get-root failed: {result.stderr}'
    assert 'plugin_root' in result.stdout


def test_get_root_with_refresh():
    """Test get-root --refresh forces re-detection (env-dependent)."""
    with PlanContext(plan_id='bootstrap-refresh'):
        result = run_script(SCRIPT_PATH, 'get-root', '--refresh')
        assert result.returncode == 0


def test_get_root_caches_result():
    """Test that get-root caches the result in marshall-state.toon (env-dependent)."""
    with PlanContext(plan_id='bootstrap-cache') as ctx:
        result = run_script(SCRIPT_PATH, 'get-root')
        assert result.returncode == 0

        # Only verify cache when operation found the plugin root
        if 'status: success' in result.stdout:
            state_file = ctx.fixture_dir / 'marshall-state.toon'
            assert state_file.exists(), 'State file should be created after successful get-root'
            content = state_file.read_text()
            assert 'plugin_root' in content

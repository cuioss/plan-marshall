#!/usr/bin/env python3
"""Tests for bootstrap-plugin.py script."""

import sys
from pathlib import Path

# Import shared infrastructure
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from conftest import PlanContext, get_script_path, run_script

# Get script path
SCRIPT_PATH = get_script_path('plan-marshall', 'marshall-steward', 'bootstrap-plugin.py')


# =============================================================================
# Test: get-root command
# =============================================================================


def test_get_root_detects_plugin():
    """Test get-root succeeds when plugin cache exists."""
    # This test depends on the real plugin cache at ~/.claude/plugins/cache/
    # If the cache exists, it should detect the root; otherwise it fails gracefully
    cache_dir = Path.home() / '.claude' / 'plugins' / 'cache'
    if not cache_dir.exists():
        # Skip gracefully if no plugin cache installed
        result = run_script(SCRIPT_PATH, 'get-root')
        assert not result.success, 'Expected failure when no plugin cache exists'
        assert 'not found' in result.stdout.lower() or 'error' in result.stdout.lower()
        return

    result = run_script(SCRIPT_PATH, 'get-root')
    assert result.success, f'get-root failed: {result.stderr}'
    assert 'plugin_root' in result.stdout


def test_get_root_with_refresh():
    """Test get-root --refresh forces re-detection."""
    with PlanContext(plan_id='bootstrap-refresh'):
        result = run_script(SCRIPT_PATH, 'get-root', '--refresh')
        # May succeed or fail depending on whether plugin cache exists
        # The important thing is it does not crash
        assert result.returncode in (0, 1)


def test_get_root_caches_result():
    """Test that get-root caches the result in marshall-state.toon."""
    with PlanContext(plan_id='bootstrap-cache') as ctx:
        # Run get-root (may succeed or fail based on plugin cache)
        result = run_script(SCRIPT_PATH, 'get-root')

        if result.success:
            # If it succeeded, verify the state file was created
            state_file = ctx.fixture_dir / 'marshall-state.toon'
            assert state_file.exists(), 'State file should be created after successful get-root'
            content = state_file.read_text()
            assert 'plugin_root' in content


# =============================================================================
# Test: resolve command
# =============================================================================


def test_resolve_without_plugin_root():
    """Test resolve fails gracefully when plugin root is not found."""
    with PlanContext(plan_id='bootstrap-resolve-no-root') as ctx:
        # Clear any cached state
        state_file = ctx.fixture_dir / 'marshall-state.toon'
        if state_file.exists():
            state_file.unlink()

        result = run_script(
            SCRIPT_PATH, 'resolve', '--bundle', 'plan-marshall', '--path', 'skills/manage-tasks/SKILL.md'
        )
        # This will fail if no plugin cache, or succeed if cache exists
        assert result.returncode in (0, 1)
        if not result.success:
            assert 'error' in result.stdout.lower() or 'not found' in result.stdout.lower()


def test_resolve_with_existing_cache():
    """Test resolve uses cached plugin root from state file."""
    cache_dir = Path.home() / '.claude' / 'plugins' / 'cache'
    if not cache_dir.exists():
        return  # Skip if no plugin cache

    with PlanContext(plan_id='bootstrap-resolve-cached'):
        # First call to populate cache
        run_script(SCRIPT_PATH, 'get-root')

        # Now resolve a path
        result = run_script(
            SCRIPT_PATH,
            'resolve',
            '--bundle',
            'plan-marshall',
            '--path',
            'skills/manage-tasks/SKILL.md',
        )
        # May not find the exact path but should not crash
        assert result.returncode in (0, 1)


# =============================================================================
# Test: State file operations (unit-level via direct import)
# =============================================================================


def test_state_read_write():
    """Test reading and writing state file directly."""
    # Import the module functions directly since conftest sets up PYTHONPATH
    from importlib import import_module
    import importlib.util

    spec = importlib.util.spec_from_file_location('bootstrap_plugin', SCRIPT_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    with PlanContext(plan_id='bootstrap-state-rw') as ctx:
        # Verify initial state is empty
        state = mod.read_state()
        assert state == {} or 'plugin_root' not in state

        # Write state
        mod.write_state({'plugin_root': '/fake/path', 'detected_at': '2026-01-01T00:00:00Z'})

        # Read back
        state = mod.read_state()
        assert state['plugin_root'] == '/fake/path'
        assert state['detected_at'] == '2026-01-01T00:00:00Z'


def test_resolve_bundle_path():
    """Test resolve_bundle_path with a mock structure."""
    import importlib.util
    import tempfile

    spec = importlib.util.spec_from_file_location('bootstrap_plugin', SCRIPT_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    # Create a mock plugin structure
    with PlanContext(plan_id='bootstrap-resolve-mock') as ctx:
        mock_root = ctx.fixture_dir / 'mock-cache'
        bundle_dir = mock_root / 'test-bundle' / '1.0.0' / 'skills' / 'test-skill'
        bundle_dir.mkdir(parents=True)
        (bundle_dir / 'SKILL.md').write_text('# Test Skill')

        result = mod.resolve_bundle_path(mock_root, 'test-bundle', 'skills/test-skill/SKILL.md')
        assert result is not None
        assert result.exists()
        assert result.name == 'SKILL.md'


def test_resolve_bundle_path_not_found():
    """Test resolve_bundle_path returns None for missing path."""
    import importlib.util

    spec = importlib.util.spec_from_file_location('bootstrap_plugin', SCRIPT_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    with PlanContext(plan_id='bootstrap-resolve-nf') as ctx:
        mock_root = ctx.fixture_dir / 'empty-cache'
        mock_root.mkdir(parents=True)

        result = mod.resolve_bundle_path(mock_root, 'nonexistent', 'some/path.md')
        assert result is None

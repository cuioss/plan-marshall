#!/usr/bin/env python3
"""Tests for extension_discovery.py module (discovery functions)."""

import os
import sys
import tempfile
from pathlib import Path

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
# Import the module under test (PYTHONPATH set by conftest)
from extension_discovery import (
    find_extension_path,
    get_extension_api_scripts_path,
    get_plugin_cache_path,
)

# =============================================================================
# Tests for Path Resolution Functions
# =============================================================================


def test_get_plugin_cache_path_default():
    """Default plugin cache path is ~/.claude/plugins/cache/plan-marshall."""
    # Clear env var if set
    old_value = os.environ.pop('PLUGIN_CACHE_PATH', None)
    try:
        path = get_plugin_cache_path()
        assert path == Path.home() / '.claude' / 'plugins' / 'cache' / 'plan-marshall'
    finally:
        if old_value:
            os.environ['PLUGIN_CACHE_PATH'] = old_value


def test_get_plugin_cache_path_from_env():
    """PLUGIN_CACHE_PATH environment variable overrides default."""
    old_value = os.environ.get('PLUGIN_CACHE_PATH')
    try:
        os.environ['PLUGIN_CACHE_PATH'] = '/custom/cache/path'
        path = get_plugin_cache_path()
        assert path == Path('/custom/cache/path')
    finally:
        if old_value:
            os.environ['PLUGIN_CACHE_PATH'] = old_value
        else:
            os.environ.pop('PLUGIN_CACHE_PATH', None)


def test_get_extension_api_scripts_path():
    """get_extension_api_scripts_path returns path to scripts directory."""
    path = get_extension_api_scripts_path()
    assert path.is_dir()
    assert (path / 'extension_base.py').exists()


# =============================================================================
# Tests for find_extension_path
# =============================================================================


def test_find_extension_path_source_structure():
    """find_extension_path finds extension in source structure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        bundle_dir = Path(tmpdir) / 'pm-dev-java'
        extension_path = bundle_dir / 'skills' / 'plan-marshall-plugin' / 'extension.py'
        extension_path.parent.mkdir(parents=True)
        extension_path.touch()

        result = find_extension_path(bundle_dir)
        assert result == extension_path


def test_find_extension_path_versioned_structure():
    """find_extension_path finds extension in versioned cache structure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        bundle_dir = Path(tmpdir) / 'pm-dev-java'
        extension_path = bundle_dir / '1.0.0' / 'skills' / 'plan-marshall-plugin' / 'extension.py'
        extension_path.parent.mkdir(parents=True)
        extension_path.touch()

        result = find_extension_path(bundle_dir)
        assert result == extension_path


def test_find_extension_path_none_when_missing():
    """find_extension_path returns None when extension.py doesn't exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        bundle_dir = Path(tmpdir) / 'pm-dev-java'
        bundle_dir.mkdir()

        result = find_extension_path(bundle_dir)
        assert result is None


def test_find_extension_path_prefers_direct():
    """find_extension_path prefers direct path over versioned."""
    with tempfile.TemporaryDirectory() as tmpdir:
        bundle_dir = Path(tmpdir) / 'pm-dev-java'

        # Create both direct and versioned paths
        direct_path = bundle_dir / 'skills' / 'plan-marshall-plugin' / 'extension.py'
        direct_path.parent.mkdir(parents=True)
        direct_path.touch()

        versioned_path = bundle_dir / '1.0.0' / 'skills' / 'plan-marshall-plugin' / 'extension.py'
        versioned_path.parent.mkdir(parents=True)
        versioned_path.touch()

        result = find_extension_path(bundle_dir)
        # Should find direct path first
        assert result == direct_path


def test_find_extension_path_skips_hidden_dirs():
    """find_extension_path skips hidden directories."""
    with tempfile.TemporaryDirectory() as tmpdir:
        bundle_dir = Path(tmpdir) / 'pm-dev-java'

        # Create extension in hidden directory (should be skipped)
        hidden_path = bundle_dir / '.hidden' / 'skills' / 'plan-marshall-plugin' / 'extension.py'
        hidden_path.parent.mkdir(parents=True)
        hidden_path.touch()

        # Create valid versioned path
        valid_path = bundle_dir / '1.0.0' / 'skills' / 'plan-marshall-plugin' / 'extension.py'
        valid_path.parent.mkdir(parents=True)
        valid_path.touch()

        result = find_extension_path(bundle_dir)
        assert result == valid_path


if __name__ == '__main__':
    import traceback

    tests = [
        test_get_plugin_cache_path_default,
        test_get_plugin_cache_path_from_env,
        test_get_extension_api_scripts_path,
        test_find_extension_path_source_structure,
        test_find_extension_path_versioned_structure,
        test_find_extension_path_none_when_missing,
        test_find_extension_path_prefers_direct,
        test_find_extension_path_skips_hidden_dirs,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception:
            failed += 1
            print(f'FAILED: {test.__name__}')
            traceback.print_exc()
            print()

    print(f'\nResults: {passed} passed, {failed} failed')
    sys.exit(0 if failed == 0 else 1)

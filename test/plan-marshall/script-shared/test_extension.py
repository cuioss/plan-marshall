#!/usr/bin/env python3
"""Tests for extension_discovery.py module (discovery functions)."""

import os
import sys
from pathlib import Path

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
# Import the module under test (PYTHONPATH set by conftest)
from extension_discovery import (
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


if __name__ == '__main__':
    import traceback

    tests = [
        test_get_plugin_cache_path_default,
        test_get_plugin_cache_path_from_env,
        test_get_extension_api_scripts_path,
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

#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for extension_discovery.py module (discovery functions)."""

from pathlib import Path

# Import the module under test (PYTHONPATH set by conftest).
from extension_discovery import (
    get_extension_api_scripts_path,
    get_plugin_cache_path,
)


def test_get_plugin_cache_path_default(monkeypatch):
    """Default plugin cache path is ~/.claude/plugins/cache/plan-marshall."""
    monkeypatch.delenv('PLUGIN_CACHE_PATH', raising=False)

    path = get_plugin_cache_path()

    assert path == Path.home() / '.claude' / 'plugins' / 'cache' / 'plan-marshall'


def test_get_plugin_cache_path_from_env(monkeypatch):
    """PLUGIN_CACHE_PATH environment variable overrides default."""
    monkeypatch.setenv('PLUGIN_CACHE_PATH', '/custom/cache/path')

    path = get_plugin_cache_path()

    assert path == Path('/custom/cache/path')


def test_get_extension_api_scripts_path():
    """get_extension_api_scripts_path returns path to scripts directory."""
    path = get_extension_api_scripts_path()
    assert path.is_dir()
    assert (path / 'extension_base.py').exists()

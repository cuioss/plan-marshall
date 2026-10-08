# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the default store locations the plugin_registry reader states.

The registry and the cache root sit under the user's home directory. Every test
points the home directory at a fixture tree, so none of them names — let alone
reads — the home directory of whoever runs the suite.
"""

import json
from pathlib import Path

import pytest
from plugin_registry import (
    MARKETPLACE_NAME,
    REGISTRY_OK,
    default_cache_root,
    default_executor_path,
    default_registry_path,
    newest_cache_version,
    read_executor_version,
    read_registry,
)

VERSION = '0.1.1069'


@pytest.fixture
def fixture_home(tmp_path: Path, monkeypatch) -> Path:
    home = tmp_path / 'home'
    home.mkdir()
    monkeypatch.setenv('HOME', str(home))
    return home


def test_default_registry_path_is_the_plugin_manager_file_under_home(fixture_home):
    assert default_registry_path() == fixture_home / '.claude' / 'plugins' / 'installed_plugins.json'


def test_default_cache_root_is_the_marketplace_cache_directory_under_home(fixture_home):
    assert default_cache_root() == fixture_home / '.claude' / 'plugins' / 'cache' / MARKETPLACE_NAME


def test_default_executor_path_is_under_the_checkout_root(tmp_path):
    assert default_executor_path(tmp_path) == tmp_path / '.plan' / 'execute-script.py'


def test_home_is_resolved_on_every_call_not_at_import(tmp_path, monkeypatch):
    # Arrange — two different home directories, set one after the other.
    first = tmp_path / 'first'
    second = tmp_path / 'second'

    # Act
    monkeypatch.setenv('HOME', str(first))
    under_first = (default_registry_path(), default_cache_root())
    monkeypatch.setenv('HOME', str(second))
    under_second = (default_registry_path(), default_cache_root())

    # Assert — each call followed the home directory in force when it ran.
    assert all(path.is_relative_to(first) for path in under_first)
    assert all(path.is_relative_to(second) for path in under_second)


def test_default_locations_are_where_the_readers_find_the_stores(fixture_home, tmp_path):
    # Arrange — the three stores written at exactly the default locations.
    registry = default_registry_path()
    registry.parent.mkdir(parents=True)
    entry = {'scope': 'user', 'installPath': f'/cache/plan-marshall/plan-marshall/{VERSION}', 'version': VERSION}
    registry.write_text(json.dumps({'plugins': {'plan-marshall@plan-marshall': [entry]}}), encoding='utf-8')
    (default_cache_root() / 'plan-marshall' / VERSION).mkdir(parents=True)
    executor = default_executor_path(tmp_path)
    executor.parent.mkdir(parents=True)
    executor.write_text(f"MARSHALL_VERSION = '{VERSION}'\n", encoding='utf-8')

    # Act
    state, rows = read_registry(default_registry_path())

    # Assert — each reader, handed its default location, reads the store written there.
    assert state == REGISTRY_OK
    assert rows[0]['install_path_version'] == VERSION
    assert newest_cache_version(default_cache_root() / 'plan-marshall') == VERSION
    assert read_executor_version(default_executor_path(tmp_path))[1] == VERSION

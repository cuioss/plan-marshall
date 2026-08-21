#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for permission_common.py shared module.

Tests settings loading, path resolution, and scope resolution used by
both permission_doctor and permission_fix scripts.
"""

import json

from permission_common import (  # noqa: I001
    EXIT_SUCCESS,
    get_project_settings_path,
    get_project_settings_path_for_write,
    load_settings,
    load_settings_path,
    resolve_scope_to_paths,
    save_settings,
)

# =============================================================================
# Test: load_settings
# =============================================================================


class TestLoadSettings:
    """Tests for load_settings function."""

    def test_load_valid_settings(self, tmp_path):
        settings_file = tmp_path / 'settings.json'
        settings_file.write_text(json.dumps({'permissions': {'allow': ['Bash(git:*)'], 'deny': [], 'ask': []}}))

        data, error = load_settings(str(settings_file))
        assert error is None
        assert data['permissions']['allow'] == ['Bash(git:*)']

    def test_load_none_path(self):
        data, error = load_settings(None)
        assert error == 'No settings path provided'
        assert data == {}

    def test_load_missing_file(self, tmp_path):
        data, error = load_settings(str(tmp_path / 'nonexistent.json'))
        assert 'not found' in error
        assert data == {}

    def test_load_invalid_json(self, tmp_path):
        settings_file = tmp_path / 'bad.json'
        settings_file.write_text('not valid json {{{')

        data, error = load_settings(str(settings_file))
        assert 'Invalid JSON' in error
        assert data == {}

    def test_load_adds_missing_permission_keys(self, tmp_path):
        """Settings without permissions key should get defaults added."""
        settings_file = tmp_path / 'settings.json'
        settings_file.write_text(json.dumps({'some_key': 'value'}))

        data, error = load_settings(str(settings_file))
        assert error is None
        assert 'permissions' in data
        assert data['permissions']['allow'] == []
        assert data['permissions']['deny'] == []
        assert data['permissions']['ask'] == []

    def test_load_adds_missing_sub_keys(self, tmp_path):
        """Settings with partial permissions should get missing sub-keys added."""
        settings_file = tmp_path / 'settings.json'
        settings_file.write_text(json.dumps({'permissions': {'allow': ['Bash(git:*)']}}))

        data, error = load_settings(str(settings_file))
        assert error is None
        assert data['permissions']['deny'] == []
        assert data['permissions']['ask'] == []


# =============================================================================
# Test: load_settings_path
# =============================================================================


class TestLoadSettingsPath:
    """Tests for load_settings_path function."""

    def test_load_existing_file(self, tmp_path):
        settings_file = tmp_path / 'settings.json'
        settings_file.write_text(json.dumps({'permissions': {'allow': ['Read(*)'], 'deny': [], 'ask': []}}))

        data = load_settings_path(settings_file)
        assert data['permissions']['allow'] == ['Read(*)']

    def test_load_missing_file_returns_defaults(self, tmp_path):
        data = load_settings_path(tmp_path / 'nonexistent.json')
        assert data == {'permissions': {'allow': [], 'deny': [], 'ask': []}}

    def test_load_invalid_json_returns_error(self, tmp_path):
        settings_file = tmp_path / 'bad.json'
        settings_file.write_text('{invalid')

        data = load_settings_path(settings_file)
        assert 'error' in data
        assert data['permissions']['allow'] == []


# =============================================================================
# Test: save_settings
# =============================================================================


class TestSaveSettings:
    """Tests for save_settings function."""

    def test_save_and_reload(self, tmp_path):
        settings_file = tmp_path / 'settings.json'
        data = {'permissions': {'allow': ['Bash(git:*)'], 'deny': [], 'ask': []}}

        result = save_settings(str(settings_file), data)
        assert result is True

        loaded = json.loads(settings_file.read_text())
        assert loaded == data

    def test_save_creates_parent_dirs(self, tmp_path):
        settings_file = tmp_path / 'deep' / 'nested' / 'settings.json'
        data = {'permissions': {'allow': [], 'deny': [], 'ask': []}}

        result = save_settings(str(settings_file), data)
        assert result is True
        assert settings_file.exists()


# =============================================================================
# Test: get_project_settings_path (the READ preference)
# =============================================================================


class TestProjectSettingsReadPreference:
    """The read path prefers ``settings.local.json``; the write path prefers the shared file.

    Both preferences are the runtime's, and this module delegates BOTH — the
    module docstring says so, and these pin that the behaviour survived the
    delegation. They drive the module's own functions rather than the runtime
    helpers, so a delegation that is reverted to an inline reimplementation with
    different behaviour is caught here rather than in the runtime's tests.
    """

    def _project(self, tmp_path, monkeypatch, *names):
        claude_dir = tmp_path / '.claude'
        claude_dir.mkdir(parents=True, exist_ok=True)
        for name in names:
            (claude_dir / name).write_text('{}', encoding='utf-8')
        monkeypatch.chdir(tmp_path)
        return claude_dir

    def test_prefers_settings_local_json_when_present(self, tmp_path, monkeypatch):
        claude_dir = self._project(tmp_path, monkeypatch, 'settings.local.json', 'settings.json')
        assert get_project_settings_path() == claude_dir / 'settings.local.json'

    def test_reads_settings_local_json_when_it_is_the_only_one(self, tmp_path, monkeypatch):
        claude_dir = self._project(tmp_path, monkeypatch, 'settings.local.json')
        assert get_project_settings_path() == claude_dir / 'settings.local.json'

    def test_falls_back_to_settings_json(self, tmp_path, monkeypatch):
        claude_dir = self._project(tmp_path, monkeypatch, 'settings.json')
        assert get_project_settings_path() == claude_dir / 'settings.json'

    def test_names_settings_json_when_neither_file_exists(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        assert get_project_settings_path() == tmp_path / '.claude' / 'settings.json'

    def test_read_and_write_preferences_are_opposites(self, tmp_path, monkeypatch):
        """With both files present the two selectors must disagree, by design."""
        self._project(tmp_path, monkeypatch, 'settings.local.json', 'settings.json')
        assert get_project_settings_path().name == 'settings.local.json'
        assert get_project_settings_path_for_write().name == 'settings.json'


# =============================================================================
# Test: resolve_scope_to_paths
# =============================================================================


class TestResolveScopeToPaths:
    """Tests for resolve_scope_to_paths function."""

    def test_global_scope(self):
        global_path, local_path = resolve_scope_to_paths('global')
        assert global_path is not None
        assert local_path is None
        assert '.claude/settings.json' in global_path

    def test_project_scope(self):
        global_path, local_path = resolve_scope_to_paths('project')
        assert global_path is None
        assert local_path is not None

    def test_both_scope(self):
        global_path, local_path = resolve_scope_to_paths('both')
        assert global_path is not None
        assert local_path is not None

    def test_invalid_scope(self):
        global_path, local_path = resolve_scope_to_paths('invalid')
        assert global_path is None
        assert local_path is None


# =============================================================================
# Test: exit code constants
# =============================================================================


def test_exit_codes():
    assert EXIT_SUCCESS == 0

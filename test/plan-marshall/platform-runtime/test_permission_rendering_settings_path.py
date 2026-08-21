#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Pins for the Claude project settings-path selectors.

The permission DSL is a target wire format, so it is rendered inside
``claude_runtime`` and never crosses the runtime boundary. The exact strings it
renders are the observable contract: they land in an operator's settings file
and a permission that changes spelling stops matching what it guards.

Expectations here are literals rather than values derived from the renderer. An
expectation computed by the code under test agrees with it by construction and
holds against any rewrite, which is exactly what a byte-level pin must not do.
The one value that cannot be a literal is the home directory, which differs per
machine.

conftest.py sets up PYTHONPATH so the cross-skill imports resolve without manual
sys.path manipulation.
"""
import json
from pathlib import Path

import claude_runtime
from toon_parser import parse_toon


def _parse(raw: str) -> dict:
    """Parse a runtime's TOON response."""
    return parse_toon(raw)

# =============================================================================
# The settings read path
# =============================================================================


class TestProjectSettingsReadPath:
    """The read preference is the runtime's, and it mirrors the write preference."""

    def test_prefers_settings_local_json_when_it_exists(self, tmp_path: Path) -> None:
        claude_dir = tmp_path / '.claude'
        claude_dir.mkdir()
        (claude_dir / 'settings.local.json').write_text('{}', encoding='utf-8')
        (claude_dir / 'settings.json').write_text('{}', encoding='utf-8')
        assert claude_runtime._claude_project_settings_read_path(str(tmp_path)) == (
            claude_dir / 'settings.local.json'
        )

    def test_reads_settings_local_json_when_it_is_the_only_one(self, tmp_path: Path) -> None:
        claude_dir = tmp_path / '.claude'
        claude_dir.mkdir()
        (claude_dir / 'settings.local.json').write_text('{}', encoding='utf-8')
        assert claude_runtime._claude_project_settings_read_path(str(tmp_path)) == (
            claude_dir / 'settings.local.json'
        )

    def test_falls_back_to_settings_json_when_local_absent(self, tmp_path: Path) -> None:
        claude_dir = tmp_path / '.claude'
        claude_dir.mkdir()
        (claude_dir / 'settings.json').write_text('{}', encoding='utf-8')
        assert claude_runtime._claude_project_settings_read_path(str(tmp_path)) == (
            claude_dir / 'settings.json'
        )

    def test_returns_settings_json_when_neither_exists(self, tmp_path: Path) -> None:
        """An absent pair reads as the shared file."""
        assert claude_runtime._claude_project_settings_read_path(str(tmp_path)) == (
            tmp_path / '.claude' / 'settings.json'
        )

    def test_a_directory_at_the_local_path_does_not_shadow_the_shared_file(
        self, tmp_path: Path
    ) -> None:
        """A DIRECTORY named settings.local.json must not be selected.

        Selecting it would load as the empty-permissions skeleton and hide the
        real shared file — an operator's rules silently absent rather than an
        error. The selector tests ``is_file``, so the shared file wins.
        """
        claude_dir = tmp_path / '.claude'
        claude_dir.mkdir()
        (claude_dir / 'settings.local.json').mkdir()
        (claude_dir / 'settings.json').write_text('{}', encoding='utf-8')
        assert claude_runtime._claude_project_settings_read_path(str(tmp_path)) == (
            claude_dir / 'settings.json'
        )

    def test_a_directory_at_the_shared_path_does_not_capture_the_write(
        self, tmp_path: Path
    ) -> None:
        """The write selector makes the same distinction, in the other direction."""
        claude_dir = tmp_path / '.claude'
        claude_dir.mkdir()
        (claude_dir / 'settings.json').mkdir()
        assert claude_runtime._claude_project_settings_path(str(tmp_path)) == (
            claude_dir / 'settings.local.json'
        )

    def test_read_and_write_preferences_are_opposites(self, tmp_path: Path) -> None:
        """Both files present: the read path takes local, the write path takes shared."""
        claude_dir = tmp_path / '.claude'
        claude_dir.mkdir()
        (claude_dir / 'settings.local.json').write_text('{}', encoding='utf-8')
        (claude_dir / 'settings.json').write_text('{}', encoding='utf-8')
        assert claude_runtime._claude_project_settings_read_path(str(tmp_path)).name == (
            'settings.local.json'
        )
        assert claude_runtime._claude_project_settings_path(str(tmp_path)).name == 'settings.json'


class TestSettingsShapeIsMalformedToo:
    """A file that parses but is the wrong SHAPE fails closed like a parse error."""

    def _load(self, tmp_path: Path, payload: str) -> dict:
        settings = tmp_path / 'settings.json'
        settings.write_text(payload, encoding='utf-8')
        return claude_runtime._load_settings(settings)

    def test_a_non_object_permissions_value_is_an_error_not_a_traceback(
        self, tmp_path: Path
    ) -> None:
        """Seeding the three lists into a string raised TypeError out of the loader.

        Every caller branches on the ``error`` key, so a raise here reaches the
        operator as a traceback instead of `invalid_settings`.
        """
        loaded = self._load(tmp_path, '{"permissions": "oops"}')
        assert 'permissions must be an object' in loaded['error']

    def test_a_non_object_root_is_an_error_too(self, tmp_path: Path) -> None:
        """A JSON list is valid JSON and an invalid settings file."""
        loaded = self._load(tmp_path, '["not", "settings"]')
        assert 'must be an object' in loaded['error']

    def test_the_operators_malformed_value_is_never_carried_forward(
        self, tmp_path: Path
    ) -> None:
        """The error skeleton is empty, so a save can never write it back.

        Replacing the bad value with an empty object in place would let a
        subsequent write discard whatever the operator actually had.
        """
        loaded = self._load(tmp_path, '{"permissions": "oops", "other": "kept-on-disk"}')
        assert loaded['permissions'] == {'allow': [], 'deny': [], 'ask': []}
        assert 'other' not in loaded

    def test_a_well_formed_file_missing_a_list_is_still_seeded(
        self, tmp_path: Path
    ) -> None:
        """The shape guard must not reject the file it exists to normalize."""
        loaded = self._load(tmp_path, '{"permissions": {"allow": ["Read(a)"]}}')
        assert 'error' not in loaded
        assert loaded['permissions'] == {'allow': ['Read(a)'], 'deny': [], 'ask': []}


class TestReadOnlyOperationsUseTheReadSelector:
    """An audit must inspect the file whose entries actually take effect.

    The write selector prefers the shared `settings.json`; the read selector
    prefers an operator's `settings.local.json`. With both present they name
    different files, so a read-side operation on the write selector reports on
    rules the operator's own settings override — the audit describing a
    configuration that is not in force.
    """

    def _project(self, tmp_path: Path, shared: list, local: list) -> Path:
        claude_dir = tmp_path / '.claude'
        claude_dir.mkdir()
        (claude_dir / 'settings.json').write_text(
            json.dumps({'permissions': {'allow': shared, 'deny': [], 'ask': []}}),
            encoding='utf-8',
        )
        (claude_dir / 'settings.local.json').write_text(
            json.dumps({'permissions': {'allow': local, 'deny': [], 'ask': []}}),
            encoding='utf-8',
        )
        return tmp_path

    def test_analyze_reads_the_effective_file_not_the_shared_one(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """`Bash(*)` lives only in the LOCAL file, so only a read-side audit sees it."""
        project = self._project(tmp_path, shared=['Read(.plan/**)'], local=['Bash(*)'])
        monkeypatch.chdir(project)

        result = _parse(
            claude_runtime.ClaudeRuntime().permission_analyze('project', ['suspicious'], None)
        )

        assert result['status'] == 'success'
        findings = [f for f in result.get('findings', []) if f['check'] == 'suspicious']
        assert any('Bash(*)' in f['details'] for f in findings), (
            'the audit read the shared file and missed the local rule'
        )

    def test_web_analyze_reads_the_effective_file_too(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """The same rule holds for the WebFetch-domain audit."""
        project = self._project(
            tmp_path,
            shared=['WebFetch(domain:shared.example)'],
            local=['WebFetch(domain:local.example)'],
        )
        monkeypatch.chdir(project)

        result = _parse(claude_runtime.ClaudeRuntime().permission_web_analyze('project'))

        assert result['status'] == 'success'
        rendered = str(result)
        assert 'local.example' in rendered

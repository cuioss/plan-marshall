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
from pathlib import Path

import claude_runtime

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

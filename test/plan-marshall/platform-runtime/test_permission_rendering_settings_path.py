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
import pytest
from toon_parser import parse_toon


def _parse(raw: str) -> dict:
    """Parse a runtime's TOON response."""
    return parse_toon(raw)


# =============================================================================
# The settings read path
# =============================================================================


def _materialize(path: Path, kind: str | None) -> None:
    """Create *path* as a file, as a directory, or not at all.

    ``'dir'`` is a real input rather than a curiosity: a DIRECTORY named
    ``settings.local.json`` would load as the empty-permissions skeleton and hide
    the shared file, so the selector tests ``is_file`` and this helper is what
    lets the table state that case as data alongside the ordinary ones.
    """
    if kind == 'file':
        path.write_text('{}', encoding='utf-8')
    elif kind == 'dir':
        path.mkdir()


#: ``(what sits at settings.local.json, what sits at settings.json, the file the
#: read selector must resolve)``. The read path prefers the operator's own local
#: file, so the first two rows take it and the next two fall through to the
#: shared one — including the row where NEITHER exists, which still resolves to
#: the shared name rather than to nothing. The last row is the shape that makes
#: the preference a real test rather than a name lookup: a directory occupying
#: the local path is not a settings file, so the shared file wins instead of an
#: operator's rules silently reading as empty.
_READ_PATH_CASES = [
    ('file', 'file', 'settings.local.json'),
    ('file', None, 'settings.local.json'),
    (None, 'file', 'settings.json'),
    (None, None, 'settings.json'),
    ('dir', 'file', 'settings.json'),
]

_READ_PATH_IDS = [
    'both-present-local-wins',
    'only-local-present',
    'only-shared-present',
    'neither-present-resolves-the-shared-name',
    'a-directory-at-the-local-path-does-not-shadow-the-shared-file',
]

#: The WRITE selector over the same input space, in the same ``(local, shared,
#: expected)`` shape — the mirror image of ``_READ_PATH_CASES`` rather than a
#: separate idea. The write path prefers the committed, team-visible file, so the
#: rows where the shared file is real take it and the rest fall through to the
#: local name, including the row where NEITHER exists. The last row is the
#: is_file distinction in the other direction: a directory occupying the SHARED
#: path is not a settings file, so the local one wins.
#:
#: Stating both selectors over one input space is what makes them a matched PAIR.
#: A table for the read side alone leaves the preference it is supposedly opposite
#: to unpinned, and a re-key of the write side would then break nothing.
_WRITE_PATH_CASES = [
    ('file', 'file', 'settings.json'),
    ('file', None, 'settings.local.json'),
    (None, 'file', 'settings.json'),
    (None, None, 'settings.local.json'),
    ('file', 'dir', 'settings.local.json'),
]

_WRITE_PATH_IDS = [
    'both-present-shared-wins',
    'only-local-present',
    'only-shared-present',
    'neither-present-resolves-the-local-name',
    'a-directory-at-the-shared-path-does-not-capture-the-write',
]


def _claude_tree(tmp_path: Path, local: str | None, shared: str | None) -> Path:
    """Build ``tmp_path/.claude`` with each candidate materialized as the row says."""
    claude_dir = tmp_path / '.claude'
    claude_dir.mkdir()
    _materialize(claude_dir / 'settings.local.json', local)
    _materialize(claude_dir / 'settings.json', shared)
    return claude_dir


class TestProjectSettingsReadPath:
    """The read preference is the runtime's, and it mirrors the write preference."""

    @pytest.mark.parametrize(('local', 'shared', 'expected'), _READ_PATH_CASES, ids=_READ_PATH_IDS)
    def test_the_read_selector_prefers_the_operators_own_file(
        self, tmp_path: Path, local: str | None, shared: str | None, expected: str
    ) -> None:
        """The read path takes ``settings.local.json`` whenever it is a real file."""
        claude_dir = _claude_tree(tmp_path, local, shared)

        resolved = claude_runtime._claude_project_settings_read_path(str(tmp_path))

        assert resolved == claude_dir / expected

    @pytest.mark.parametrize(('local', 'shared', 'expected'), _WRITE_PATH_CASES, ids=_WRITE_PATH_IDS)
    def test_the_write_selector_prefers_the_shared_file(
        self, tmp_path: Path, local: str | None, shared: str | None, expected: str
    ) -> None:
        """The write path takes ``settings.json`` whenever it is a real file."""
        claude_dir = _claude_tree(tmp_path, local, shared)

        resolved = claude_runtime._claude_project_settings_path(str(tmp_path))

        assert resolved == claude_dir / expected

    def test_read_and_write_preferences_are_opposites(self, tmp_path: Path) -> None:
        """Both files present, one tree: the read path takes local, the write path takes shared.

        Full paths, not filenames. A selector that returned the right basename
        under the wrong directory would satisfy a ``.name`` check while resolving
        a file in neither the project nor the operator's configuration.

        The inequality is asserted in its own right: "opposite" is a claim about
        the two selectors DISAGREEING here, and collapsing them onto one file is
        the specific regression this guards — one that both equality assertions
        above would have to be edited to permit, but that a caller could reach by
        re-pointing either selector at the other.
        """
        claude_dir = _claude_tree(tmp_path, 'file', 'file')

        read_path = claude_runtime._claude_project_settings_read_path(str(tmp_path))
        write_path = claude_runtime._claude_project_settings_path(str(tmp_path))

        assert read_path == claude_dir / 'settings.local.json'
        assert write_path == claude_dir / 'settings.json'
        assert read_path != write_path


class TestSettingsShapeIsMalformedToo:
    """A file that parses but is the wrong SHAPE fails closed like a parse error."""

    def _load(self, tmp_path: Path, payload: str) -> dict:
        settings = tmp_path / 'settings.json'
        settings.write_text(payload, encoding='utf-8')
        return claude_runtime._load_settings(settings)

    def test_a_non_object_permissions_value_is_an_error_not_a_traceback(self, tmp_path: Path) -> None:
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

    def test_the_operators_malformed_value_is_never_carried_forward(self, tmp_path: Path) -> None:
        """The error skeleton is empty, so a save can never write it back.

        Replacing the bad value with an empty object in place would let a
        subsequent write discard whatever the operator actually had.
        """
        loaded = self._load(tmp_path, '{"permissions": "oops", "other": "kept-on-disk"}')
        assert loaded['permissions'] == {'allow': [], 'deny': [], 'ask': []}
        assert 'other' not in loaded

    def test_a_well_formed_file_missing_a_list_is_still_seeded(self, tmp_path: Path) -> None:
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

    def test_analyze_reads_the_effective_file_not_the_shared_one(self, tmp_path: Path, monkeypatch) -> None:
        """`Bash(*)` lives only in the LOCAL file, so only a read-side audit sees it."""
        project = self._project(tmp_path, shared=['Read(.plan/**)'], local=['Bash(*)'])
        monkeypatch.chdir(project)

        result = _parse(claude_runtime.ClaudeRuntime().permission_analyze('project', ['suspicious'], None))

        assert result['status'] == 'success'
        findings = [f for f in result.get('findings', []) if f['check'] == 'suspicious']
        assert any('Bash(*)' in f['details'] for f in findings), (
            'the audit read the shared file and missed the local rule'
        )

    def test_web_analyze_reads_the_effective_file_too(self, tmp_path: Path, monkeypatch) -> None:
        """The same rule holds for the WebFetch-domain audit."""
        project = self._project(
            tmp_path,
            shared=['WebFetch(domain:shared.example)'],
            local=['WebFetch(domain:local.example)'],
        )
        monkeypatch.chdir(project)

        result = _parse(claude_runtime.ClaudeRuntime().permission_web_analyze('project'))

        assert result['status'] == 'success'
        # Presence of the local domain alone would also pass on an implementation
        # that MERGED both files. Asserting the shared domain is absent is what
        # pins precedence rather than mere reachability.
        domains = {row['domain'] for row in result['domains']}
        assert domains == {'domain:local.example'}

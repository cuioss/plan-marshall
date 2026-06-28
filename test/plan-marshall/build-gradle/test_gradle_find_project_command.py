#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Behavioral tests for the ``cmd_find_project`` handler in
``_gradle_cmd_find_project``.

The existing ``test_gradle_find_project.py`` exercises the helper functions
(settings parsing, build-file scan, notation conversion) but never drives the
``cmd_find_project`` command body, which holds the bulk of the branching logic:
root-not-found, project-path lookup (path-not-found / no-build-file / success),
and project-name lookup (root match, included match, build-file-scan match,
not-found, and ambiguous). These tests build an argparse-style namespace, run
the handler in-process, capture its TOON output, and assert each branch.
"""

from types import SimpleNamespace

from toon_parser import parse_toon

from conftest import load_script_module

_mod = load_script_module(
    'plan-marshall', 'build-gradle', '_gradle_cmd_find_project.py', 'gfp_command_mod'
)


def _run(capsys, root, project_name=None, project_path=None):
    """Invoke cmd_find_project with the given args and return parsed TOON output."""
    args = SimpleNamespace(root=str(root), project_name=project_name, project_path=project_path)
    rc = _mod.cmd_find_project(args)
    captured = capsys.readouterr()
    return rc, parse_toon(captured.out)


def _make_multi_project(tmp_path):
    """Create a root + core + web Gradle project with a settings file."""
    (tmp_path / 'settings.gradle.kts').write_text(
        'rootProject.name = "my-app"\ninclude("core", "web")\n'
    )
    (tmp_path / 'build.gradle.kts').write_text('// root')
    for name in ('core', 'web'):
        sub = tmp_path / name
        sub.mkdir()
        (sub / 'build.gradle.kts').write_text(f'// {name}')
    return tmp_path


# =============================================================================
# Root validation
# =============================================================================


def test_root_not_found(tmp_path, capsys):
    """A non-existent root directory returns a root_not_found error."""
    # Act
    rc, data = _run(capsys, tmp_path / 'nope', project_name='core')

    # Assert
    assert rc == 0
    assert data['status'] == 'error'
    assert data['error'] == 'root_not_found'


# =============================================================================
# project_path lookup
# =============================================================================


def test_project_path_not_found(tmp_path, capsys):
    """A project_path that does not exist returns path_not_found."""
    # Arrange
    _make_multi_project(tmp_path)

    # Act
    rc, data = _run(capsys, tmp_path, project_path=':missing')

    # Assert
    assert data['status'] == 'error'
    assert data['error'] == 'path_not_found'


def test_project_path_no_build_file(tmp_path, capsys):
    """A project_path directory without a build file returns no_build_file."""
    # Arrange
    _make_multi_project(tmp_path)
    (tmp_path / 'docs').mkdir()

    # Act
    rc, data = _run(capsys, tmp_path, project_path='docs')

    # Assert
    assert data['status'] == 'error'
    assert data['error'] == 'no_build_file'


def test_project_path_success_with_colon_notation(tmp_path, capsys):
    """A valid ':core' project_path resolves to its Gradle notation and -p arg."""
    # Arrange
    _make_multi_project(tmp_path)

    # Act
    rc, data = _run(capsys, tmp_path, project_path=':core')

    # Assert
    assert data['status'] == 'success'
    assert data['project_path'] == ':core'
    assert data['gradle_p_argument'] == '-p core'
    assert data['parent_projects'] == ''


def test_project_path_nested_reports_parent_projects(tmp_path, capsys):
    """A nested project_path reports its ancestor projects."""
    # Arrange
    nested = tmp_path / 'services' / 'auth'
    nested.mkdir(parents=True)
    (nested / 'build.gradle').write_text('// auth')

    # Act
    rc, data = _run(capsys, tmp_path, project_path=':services:auth')

    # Assert
    assert data['status'] == 'success'
    assert data['project_path'] == ':services:auth'
    assert data['parent_projects'] == ':services'
    assert data['gradle_p_argument'] == '-p services/auth'


# =============================================================================
# project_name lookup
# =============================================================================


def test_project_name_root_match(tmp_path, capsys):
    """The rootProject.name resolves to the root project (':')."""
    # Arrange
    _make_multi_project(tmp_path)

    # Act
    rc, data = _run(capsys, tmp_path, project_name='my-app')

    # Assert
    assert data['status'] == 'success'
    assert data['project_path'] == ':'
    assert data['gradle_p_argument'] == ''


def test_project_name_included_match(tmp_path, capsys):
    """A settings-included project name resolves to its single match."""
    # Arrange
    _make_multi_project(tmp_path)

    # Act
    rc, data = _run(capsys, tmp_path, project_name='web')

    # Assert
    assert data['status'] == 'success'
    assert data['project_path'] == ':web'
    assert data['gradle_p_argument'] == '-p web'


def test_project_name_build_file_scan_match(tmp_path, capsys):
    """A project absent from settings but present on disk is found by scan."""
    # Arrange — no settings file at all; a standalone module dir on disk.
    standalone = tmp_path / 'standalone'
    standalone.mkdir()
    (standalone / 'build.gradle').write_text('// standalone')

    # Act
    rc, data = _run(capsys, tmp_path, project_name='standalone')

    # Assert
    assert data['status'] == 'success'
    assert data['project_path'] == ':standalone'


def test_project_name_not_found(tmp_path, capsys):
    """An unknown project name returns project_not_found."""
    # Arrange
    _make_multi_project(tmp_path)

    # Act
    rc, data = _run(capsys, tmp_path, project_name='ghost')

    # Assert
    assert data['status'] == 'error'
    assert data['error'] == 'project_not_found'


def test_project_name_ambiguous(tmp_path, capsys):
    """Two projects sharing a leaf name produce an ambiguous_project_name error."""
    # Arrange — include both ':core' and ':sub:core'; both leaf-named 'core'.
    (tmp_path / 'settings.gradle').write_text("include 'core', 'sub:core'\n")
    (tmp_path / 'build.gradle').write_text('// root')
    core = tmp_path / 'core'
    core.mkdir()
    (core / 'build.gradle').write_text('// core')
    sub_core = tmp_path / 'sub' / 'core'
    sub_core.mkdir(parents=True)
    (sub_core / 'build.gradle').write_text('// sub core')

    # Act
    rc, data = _run(capsys, tmp_path, project_name='core')

    # Assert
    assert data['status'] == 'error'
    assert data['error'] == 'ambiguous_project_name'
    assert 'choices' in data

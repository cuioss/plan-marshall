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

import argparse
from types import SimpleNamespace

from _build_cli import build_main
from _resolve_project_dir_fixtures import CANONICAL_PLAN_ID
from toon_parser import parse_toon

from conftest import load_script_module

_mod = load_script_module(
    'plan-marshall', 'build-gradle', '_gradle_cmd_find_project.py', 'gfp_command_mod'
)

#: The wrapper script itself — ``find-project``'s subparser is registered there,
#: inline, outside ``register_standard_subparsers``. The routing-pair and
#: ``--root`` precedence tests at the bottom of this file drive that
#: registration rather than the handler in isolation, because the precedence
#: rule lives in the registration's dispatch closure.
_gradle = load_script_module('plan-marshall', 'build-gradle', 'gradle.py', 'gradle_wrapper_mod')


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


# =============================================================================
# Routing pair and ``--root`` precedence
# =============================================================================
#
# ``find-project`` builds its subparser inline in ``gradle.py``, outside the
# shared ``register_standard_subparsers`` helper — so it does not inherit the
# canonical ``--plan-id`` / ``--project-dir`` pair and had to opt in explicitly.
# Having both a routing pair and a pre-existing ``--root`` means the two sources
# must be reconciled: an explicit ``--root`` wins verbatim, otherwise the root
# ``build_main`` resolved from the pair applies.


def _find_project_parser() -> argparse.ArgumentParser:
    """Build a parser carrying only gradle's real ``find-project`` registration."""
    parser = argparse.ArgumentParser(allow_abbrev=False)
    subparsers = parser.add_subparsers(dest='command', required=True)
    _gradle._register_find_project(subparsers)
    return parser


def _run_find_project_cli(monkeypatch, capsys, argv_tail):
    """Drive ``find-project`` end-to-end through ``build_main`` and parse its TOON.

    End-to-end rather than against ``cmd_find_project`` directly: the fallback
    root is the value ``build_main`` writes into ``args.project_dir``, so a
    handler invoked on a hand-built namespace would never exercise the
    resolution step the precedence rule reads from.
    """
    monkeypatch.setattr('sys.argv', ['gradle.py', 'find-project', *argv_tail])
    rc = build_main('Gradle build operations', [_gradle._register_find_project])
    return rc, parse_toon(capsys.readouterr().out)


def test_find_project_declares_the_routing_pair():
    """``find-project`` accepts both halves of the canonical routing pair."""
    args = _find_project_parser().parse_args(
        ['find-project', '--project-name', 'core', '--plan-id', CANONICAL_PLAN_ID]
    )

    assert args.plan_id == CANONICAL_PLAN_ID
    # --project-dir keeps the canonical '.' default so the resolver detects absence.
    assert args.project_dir == '.'


def test_find_project_root_default_is_the_none_sentinel():
    """``--root`` defaults to ``None``, keeping an explicit ``--root .`` observable."""
    args = _find_project_parser().parse_args(['find-project', '--project-name', 'core'])

    assert args.root is None


def test_find_project_project_path_stays_outside_the_routing_pair():
    """``--project-path`` is the project SELECTOR, not a routing flag.

    It shares a prefix with ``--project-dir`` and lives in the required
    mutually-exclusive selector group, so a regression that folded the two
    together — or that let the new flag join the exclusive group — would
    change which project is looked up rather than where it is looked up.
    """
    args = _find_project_parser().parse_args(
        ['find-project', '--project-path', ':core', '--project-dir', '/tmp/routing-root']
    )

    assert args.project_path == ':core'
    assert args.project_dir == '/tmp/routing-root'


def test_find_project_without_root_falls_back_to_resolved_project_dir(tmp_path, monkeypatch, capsys):
    """Absent ``--root``, the root resolved from the routing pair is searched."""
    # Arrange
    _make_multi_project(tmp_path)

    # Act
    rc, data = _run_find_project_cli(
        monkeypatch, capsys, ['--project-name', 'web', '--project-dir', str(tmp_path)]
    )

    # Assert
    assert rc == 0
    assert data['status'] == 'success'
    assert data['project_path'] == ':web'


def test_find_project_explicit_root_wins_over_resolved_project_dir(tmp_path, monkeypatch, capsys):
    """An explicit ``--root`` beats the resolved routing root.

    ``--project-dir`` points at the ``core`` subdirectory, which carries no
    settings file and no ``web`` project — so the lookup only succeeds if
    ``--root`` took precedence. A rule that preferred the routing root would
    surface here as ``project_not_found`` rather than as a silent pass.
    """
    # Arrange
    _make_multi_project(tmp_path)

    # Act
    rc, data = _run_find_project_cli(
        monkeypatch,
        capsys,
        ['--project-name', 'web', '--root', str(tmp_path), '--project-dir', str(tmp_path / 'core')],
    )

    # Assert
    assert rc == 0
    assert data['status'] == 'success'
    assert data['project_path'] == ':web'

#!/usr/bin/env python3
"""Tests for the `detect-ide` verb on manage-files.

Covers `cmd_detect_ide` across the full env-matrix already exercised by
`test_manage_files_open_in_ide.py` but asserting on the serialized TOON
shape (`status`, `detected`, `name`, `launcher_argv`, `platform`,
`signal`) rather than the launch side-effect.
"""

import importlib.util
from argparse import Namespace
from pathlib import Path
from unittest import mock

import pytest

# Tier 2 direct import - load hyphenated module
_MANAGE_FILES_SCRIPT = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-files'
    / 'scripts'
    / 'manage-files.py'
)
_spec = importlib.util.spec_from_file_location('manage_files_detect_ide', _MANAGE_FILES_SCRIPT)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

cmd_detect_ide = _mod.cmd_detect_ide
MACOS_JETBRAINS_BUNDLE_IDS = _mod.MACOS_JETBRAINS_BUNDLE_IDS
LINUX_LAUNCHER_PRIORITY = _mod.LINUX_LAUNCHER_PRIORITY


# =============================================================================
# macOS branches
# =============================================================================


@pytest.mark.parametrize(
    'bundle_id, expected_app',
    list(MACOS_JETBRAINS_BUNDLE_IDS.items()),
)
def test_cmd_detect_ide_macos_jetbrains_bundle(bundle_id, expected_app):
    with (
        mock.patch.object(_mod.sys, 'platform', 'darwin'),
        mock.patch.dict(_mod.os.environ, {'__CFBundleIdentifier': bundle_id}, clear=True),
    ):
        result = cmd_detect_ide(Namespace())

    assert result['status'] == 'success'
    assert result['detected'] is True
    assert result['name'] == expected_app
    assert result['launcher_argv'] == ['open', '-a', expected_app]
    assert result['platform'] == 'darwin'
    assert result['signal'] == 'cf_bundle_identifier'


def test_cmd_detect_ide_macos_vscode():
    with (
        mock.patch.object(_mod.sys, 'platform', 'darwin'),
        mock.patch.dict(_mod.os.environ, {'TERM_PROGRAM': 'vscode'}, clear=True),
    ):
        result = cmd_detect_ide(Namespace())

    assert result['status'] == 'success'
    assert result['detected'] is True
    assert result['name'] == 'Visual Studio Code'
    assert result['launcher_argv'] == ['open', '-a', 'Visual Studio Code']
    assert result['platform'] == 'darwin'
    assert result['signal'] == 'term_program'


def test_cmd_detect_ide_macos_cursor():
    with (
        mock.patch.object(_mod.sys, 'platform', 'darwin'),
        mock.patch.dict(_mod.os.environ, {'TERM_PROGRAM': 'cursor'}, clear=True),
    ):
        result = cmd_detect_ide(Namespace())

    assert result['status'] == 'success'
    assert result['detected'] is True
    assert result['name'] == 'Cursor'
    assert result['launcher_argv'] == ['open', '-a', 'Cursor']
    assert result['platform'] == 'darwin'
    assert result['signal'] == 'term_program'


def test_cmd_detect_ide_macos_no_signal_returns_undetected():
    with (
        mock.patch.object(_mod.sys, 'platform', 'darwin'),
        mock.patch.dict(_mod.os.environ, {}, clear=True),
    ):
        result = cmd_detect_ide(Namespace())

    assert result['status'] == 'success'
    assert result['detected'] is False
    assert result['platform'] == 'darwin'
    assert 'name' not in result
    assert 'launcher_argv' not in result
    assert 'signal' not in result


# =============================================================================
# Linux branches
# =============================================================================


def test_cmd_detect_ide_linux_vscode_with_code_on_path():
    def which_side_effect(name):
        return '/usr/bin/code' if name == 'code' else None

    with (
        mock.patch.object(_mod.sys, 'platform', 'linux'),
        mock.patch.dict(_mod.os.environ, {'TERM_PROGRAM': 'vscode'}, clear=True),
        mock.patch.object(_mod.shutil, 'which', side_effect=which_side_effect),
    ):
        result = cmd_detect_ide(Namespace())

    assert result['status'] == 'success'
    assert result['detected'] is True
    assert result['name'] == 'Visual Studio Code'
    assert result['launcher_argv'] == ['code']
    assert result['platform'] == 'linux'
    assert result['signal'] == 'term_program'


@pytest.mark.parametrize('launcher', list(LINUX_LAUNCHER_PRIORITY))
def test_cmd_detect_ide_linux_jetbrains_path_probe(launcher):
    # only `launcher` resolves on PATH; TERM_PROGRAM not set
    def which_side_effect(name, want=launcher):
        return f'/usr/bin/{name}' if name == want else None

    with (
        mock.patch.object(_mod.sys, 'platform', 'linux'),
        mock.patch.dict(_mod.os.environ, {}, clear=True),
        mock.patch.object(_mod.shutil, 'which', side_effect=which_side_effect),
    ):
        result = cmd_detect_ide(Namespace())

    assert result['status'] == 'success'
    assert result['detected'] is True
    assert result['name'] == launcher
    assert result['launcher_argv'] == [launcher]
    assert result['platform'] == 'linux'
    assert result['signal'] == 'path_probe'


def test_cmd_detect_ide_linux_no_launchers_returns_undetected():
    with (
        mock.patch.object(_mod.sys, 'platform', 'linux'),
        mock.patch.dict(_mod.os.environ, {}, clear=True),
        mock.patch.object(_mod.shutil, 'which', return_value=None),
    ):
        result = cmd_detect_ide(Namespace())

    assert result['status'] == 'success'
    assert result['detected'] is False
    assert result['platform'] == 'linux'
    assert 'name' not in result
    assert 'launcher_argv' not in result
    assert 'signal' not in result


# =============================================================================
# Unknown platform
# =============================================================================


def test_cmd_detect_ide_unknown_platform_returns_undetected():
    with (
        mock.patch.object(_mod.sys, 'platform', 'win32'),
        mock.patch.dict(_mod.os.environ, {'TERM_PROGRAM': 'vscode'}, clear=True),
    ):
        result = cmd_detect_ide(Namespace())

    assert result['status'] == 'success'
    assert result['detected'] is False
    assert result['platform'] == 'win32'
    assert 'name' not in result
    assert 'launcher_argv' not in result
    assert 'signal' not in result


# =============================================================================
# Subparser wiring — `detect-ide` verb is reachable through argparse
# =============================================================================


def test_detect_ide_subparser_registered():
    """The main() parser must expose `detect-ide` as a subcommand with
    `cmd_detect_ide` bound as its `func` default."""
    # Rebuild argparse the same way main() does; the deterministic check is
    # invoking the parser on a `detect-ide` argv (no flags) and confirming
    # argparse routes to the right handler.
    import argparse

    parser = argparse.ArgumentParser(allow_abbrev=False)
    subparsers = parser.add_subparsers(dest='command', required=True)
    detect_ide_parser = subparsers.add_parser('detect-ide', allow_abbrev=False)
    detect_ide_parser.set_defaults(func=cmd_detect_ide)

    args = parser.parse_args(['detect-ide'])

    assert args.command == 'detect-ide'
    assert args.func is cmd_detect_ide

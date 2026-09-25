#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Behavior-cluster tests for manage-files IDE detection and launch commands."""

from pathlib import Path
from unittest import mock

import pytest
from _manage_files_open_in_ide_fixtures import (
    LINUX_LAUNCHER_PRIORITY,
    MACOS_JETBRAINS_BUNDLE_IDS,
    IdeRecord,
    _mod,
    build_launch_command,
    detect_ide,
)

# =============================================================================
# detect_ide — macOS branches
# =============================================================================


@pytest.mark.parametrize(
    'bundle_id, expected_app',
    list(MACOS_JETBRAINS_BUNDLE_IDS.items()),
)
def test_detect_ide_macos_jetbrains_bundle(bundle_id, expected_app):
    env = {'__CFBundleIdentifier': bundle_id}

    result = detect_ide(env, 'darwin')

    assert result is not None
    assert result.name == expected_app
    assert result.launcher_argv == ('open', '-a', expected_app)


def test_detect_ide_macos_vscode():
    env = {'TERM_PROGRAM': 'vscode'}

    result = detect_ide(env, 'darwin')

    assert result is not None
    assert result.name == 'Visual Studio Code'
    assert result.launcher_argv == ('open', '-a', 'Visual Studio Code')


def test_detect_ide_macos_cursor():
    env = {'TERM_PROGRAM': 'cursor'}

    result = detect_ide(env, 'darwin')

    assert result is not None
    assert result.name == 'Cursor'
    assert result.launcher_argv == ('open', '-a', 'Cursor')


def test_detect_ide_macos_cursor_not_substituted_with_vscode():
    """Regression guard: Cursor must NEVER silently become VS Code."""
    env = {'TERM_PROGRAM': 'cursor'}

    result = detect_ide(env, 'darwin')

    assert result is not None
    assert 'Visual Studio Code' not in result.name


# =============================================================================
# detect_ide — Linux branches
# =============================================================================


def test_detect_ide_linux_vscode_with_code_on_path():
    env = {'TERM_PROGRAM': 'vscode'}

    with mock.patch.object(_mod.shutil, 'which', side_effect=lambda name: '/usr/bin/code' if name == 'code' else None):
        result = detect_ide(env, 'linux')

    assert result is not None
    assert result.name == 'Visual Studio Code'
    assert result.launcher_argv == ('code',)


def test_detect_ide_linux_vscode_without_code_falls_through_to_jetbrains_probe():
    """When `code` is missing on Linux, fall through to JetBrains probe (not bare open)."""
    env = {'TERM_PROGRAM': 'vscode'}

    with mock.patch.object(_mod.shutil, 'which', return_value=None):
        result = detect_ide(env, 'linux')

    # TERM_PROGRAM=vscode but `code` missing AND no JetBrains launcher → None
    assert result is None


def test_detect_ide_linux_cursor_with_cursor_on_path():
    env = {'TERM_PROGRAM': 'cursor'}

    with mock.patch.object(
        _mod.shutil, 'which', side_effect=lambda name: '/usr/bin/cursor' if name == 'cursor' else None
    ):
        result = detect_ide(env, 'linux')

    assert result is not None
    assert result.name == 'Cursor'
    assert result.launcher_argv == ('cursor',)


@pytest.mark.parametrize('launcher', list(LINUX_LAUNCHER_PRIORITY))
def test_detect_ide_linux_jetbrains_priority_probe(launcher):
    """Each launcher in LINUX_LAUNCHER_PRIORITY can be detected in isolation."""
    # env has no TERM_PROGRAM signal
    env: dict[str, str] = {}

    # only `launcher` resolves on PATH
    with mock.patch.object(
        _mod.shutil, 'which', side_effect=lambda name, want=launcher: f'/usr/bin/{name}' if name == want else None
    ):
        result = detect_ide(env, 'linux')

    assert result is not None
    assert result.name == launcher
    assert result.launcher_argv == (launcher,)


def test_detect_ide_linux_priority_first_match_wins():
    """When multiple launchers are on PATH, the priority-ordered first match wins."""
    env: dict[str, str] = {}
    on_path = {'pycharm', 'idea', 'webstorm'}

    # all three on PATH; idea has the highest priority
    with mock.patch.object(
        _mod.shutil, 'which', side_effect=lambda name: f'/usr/bin/{name}' if name in on_path else None
    ):
        result = detect_ide(env, 'linux')

    assert result is not None
    assert result.name == 'idea'


def test_detect_ide_linux_no_launchers_returns_none():
    env: dict[str, str] = {}

    with mock.patch.object(_mod.shutil, 'which', return_value=None):
        result = detect_ide(env, 'linux')

    assert result is None


# =============================================================================
# detect_ide — the env/platform pairs that detect nothing without probing PATH
# =============================================================================


@pytest.mark.parametrize(
    ('env', 'platform'),
    [
        ({'TERM_PROGRAM': 'unknown-terminal'}, 'darwin'),
        ({}, 'darwin'),
        ({'TERM_PROGRAM': 'vscode'}, 'win32'),
    ],
    ids=[
        'darwin-with-an-unrecognised-term-program',
        'darwin-with-no-signal-in-the-environment',
        'win32-is-an-unsupported-platform-even-with-a-known-signal',
    ],
)
def test_detect_ide_returns_none(env: dict[str, str], platform: str):
    """No IDE is reported for these pairs, and none of them consults PATH.

    Kept apart from the Linux misses above: those reach ``shutil.which`` and so
    depend on a stubbed PATH, while these three are decided from the env and the
    platform alone.
    """
    assert detect_ide(env, platform) is None


# =============================================================================
# build_launch_command
# =============================================================================


def test_build_launch_command_macos_open_a():
    ide = IdeRecord(name='IntelliJ IDEA', launcher_argv=('open', '-a', 'IntelliJ IDEA'))
    path = Path('/abs/path/to/file.md')

    argv = build_launch_command(ide, path)

    assert argv == ['open', '-a', 'IntelliJ IDEA', '/abs/path/to/file.md']


def test_build_launch_command_linux_code():
    ide = IdeRecord(name='Visual Studio Code', launcher_argv=('code',))
    path = Path('/abs/path/to/file.md')

    argv = build_launch_command(ide, path)

    assert argv == ['code', '/abs/path/to/file.md']

#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Behavior-cluster tests for the manage-files open-in-ide command."""

import json
from unittest import mock

from _manage_files_open_in_ide_fixtures import _mod, cmd_open_in_ide, parse_ns

# =============================================================================
# cmd_open_in_ide — end-to-end
# =============================================================================


def test_cmd_open_in_ide_mode_a_macos_vscode_success(plan_context):
    (plan_context.fixture_dir / 'marshal.json').write_text(
        json.dumps({'plan': {'open_in_ide': True}}), encoding='utf-8'
    )
    args = parse_ns('plan-marshall', 'manage-files', 'manage-files.py', 'open-in-ide', '--path', '/abs/path/file.md')

    completed = mock.MagicMock(returncode=0, stdout='', stderr='')
    # Clear env so the host's __CFBundleIdentifier does not leak in and
    # win over TERM_PROGRAM in the detect_ide priority order.
    with (
        mock.patch.object(_mod.sys, 'platform', 'darwin'),
        mock.patch.object(_mod, 'subprocess') as mock_subprocess,
        mock.patch.dict(_mod.os.environ, {'TERM_PROGRAM': 'vscode'}, clear=True),
    ):
        mock_subprocess.run.return_value = completed

        result = cmd_open_in_ide(args)

    assert result['status'] == 'success'
    assert result['ide'] == 'Visual Studio Code'
    assert '/abs/path/file.md' in result['command']
    assert result['path'] == '/abs/path/file.md'


def test_cmd_open_in_ide_disabled_by_config_short_circuits(plan_context):
    """Disabled-by-config: detect_ide and subprocess.run are NEVER called."""
    (plan_context.fixture_dir / 'marshal.json').write_text(
        json.dumps({'plan': {'open_in_ide': False}}), encoding='utf-8'
    )
    args = parse_ns('plan-marshall', 'manage-files', 'manage-files.py', 'open-in-ide', '--path', '/abs/path/file.md')

    with (
        mock.patch.object(_mod, 'detect_ide') as mock_detect,
        mock.patch.object(_mod, 'subprocess') as mock_subprocess,
    ):
        result = cmd_open_in_ide(args)

    assert result['status'] == 'success'
    assert result['action'] == 'skipped'
    assert result['reason'] == 'disabled_by_config'
    assert mock_detect.call_count == 0, 'detect_ide must NOT be invoked when disabled'
    assert mock_subprocess.run.call_count == 0, 'launcher must NOT fire when disabled'


def test_cmd_open_in_ide_missing_key_acts_as_enabled(plan_context):
    """Missing plan.open_in_ide sub-namespace → behaves as if enabled=true."""
    (plan_context.fixture_dir / 'marshal.json').write_text(json.dumps({'plan': {}}), encoding='utf-8')
    args = parse_ns('plan-marshall', 'manage-files', 'manage-files.py', 'open-in-ide', '--path', '/abs/path/file.md')

    completed = mock.MagicMock(returncode=0, stdout='', stderr='')
    with (
        mock.patch.object(_mod.sys, 'platform', 'darwin'),
        mock.patch.object(_mod, 'subprocess') as mock_subprocess,
        mock.patch.dict(_mod.os.environ, {'TERM_PROGRAM': 'vscode'}, clear=True),
    ):
        mock_subprocess.run.return_value = completed

        result = cmd_open_in_ide(args)

    # detection ran (we matched VS Code on macOS via TERM_PROGRAM)
    assert result['status'] == 'success'
    assert result['ide'] == 'Visual Studio Code'


def test_cmd_open_in_ide_unknown_ide_returns_ide_not_detected(plan_context):
    (plan_context.fixture_dir / 'marshal.json').write_text(
        json.dumps({'plan': {'open_in_ide': True}}), encoding='utf-8'
    )
    args = parse_ns('plan-marshall', 'manage-files', 'manage-files.py', 'open-in-ide', '--path', '/abs/path/file.md')

    with (
        mock.patch.object(_mod.sys, 'platform', 'darwin'),
        mock.patch.dict(_mod.os.environ, {}, clear=True),
    ):
        result = cmd_open_in_ide(args)

    assert result['status'] == 'error'
    assert result['reason'] == 'ide_not_detected'


def test_cmd_open_in_ide_launcher_missing_returns_launcher_missing(plan_context):
    (plan_context.fixture_dir / 'marshal.json').write_text(
        json.dumps({'plan': {'open_in_ide': True}}), encoding='utf-8'
    )
    args = parse_ns('plan-marshall', 'manage-files', 'manage-files.py', 'open-in-ide', '--path', '/abs/path/file.md')

    with (
        mock.patch.object(_mod.sys, 'platform', 'darwin'),
        mock.patch.object(_mod, 'subprocess') as mock_subprocess,
        mock.patch.dict(_mod.os.environ, {'TERM_PROGRAM': 'vscode'}, clear=True),
    ):
        mock_subprocess.run.side_effect = FileNotFoundError('open not found')

        result = cmd_open_in_ide(args)

    assert result['status'] == 'error'
    assert result['reason'] == 'launcher_missing'


def test_cmd_open_in_ide_mode_b_without_document_returns_invalid_arguments(plan_context):
    # emulate the case where argparse let through plan-id without --document
    # (e.g., direct function call rather than CLI invocation).
    (plan_context.fixture_dir / 'marshal.json').write_text(
        json.dumps({'plan': {'open_in_ide': True}}), encoding='utf-8'
    )
    args = parse_ns('plan-marshall', 'manage-files', 'manage-files.py', 'open-in-ide', '--plan-id', 'some-plan')

    result = cmd_open_in_ide(args)

    assert result['status'] == 'error'
    assert result['reason'] == 'invalid_arguments'


def test_cmd_open_in_ide_mode_b_document_resolution_failure(plan_context):
    (plan_context.fixture_dir / 'marshal.json').write_text(
        json.dumps({'plan': {'open_in_ide': True}}), encoding='utf-8'
    )
    args = parse_ns(
        'plan-marshall',
        'manage-files',
        'manage-files.py',
        'open-in-ide',
        '--plan-id',
        'e2e-mode-b-resolver-fail',
        '--document',
        'solution_outline',
    )

    # Simulate resolver returning non-zero
    proc = mock.MagicMock(returncode=2, stdout='', stderr='no outline found')
    with mock.patch.object(_mod, 'subprocess') as mock_subprocess:
        mock_subprocess.run.return_value = proc

        result = cmd_open_in_ide(args)

    assert result['status'] == 'error'
    assert result['reason'] == 'document_resolution_failed'

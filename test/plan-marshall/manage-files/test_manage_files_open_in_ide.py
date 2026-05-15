#!/usr/bin/env python3
"""Tests for the `open-in-ide` verb on manage-files.

Covers:
  * `detect_ide`: macOS JetBrains family, macOS VS Code, macOS Cursor,
    Linux VS Code, Linux Cursor, Linux JetBrains priority probe, all-miss
    branches on both platforms.
  * `build_launch_command`: each IdeRecord -> correct argv.
  * `is_open_in_ide_enabled`: explicit true, explicit false, missing key
    variants (no enabled field; no open_in_ide sub-namespace; no plan
    namespace; no marshal.json file at all).
  * End-to-end `cmd_open_in_ide`: Mode A success, disabled-by-config
    short-circuit (asserts detect/launcher NEVER called), unknown-IDE
    `ide_not_detected` error, launcher_missing error, Mode B
    invalid-arguments error.
  * Static guards: no `tempfile` import in the module's AST; no
    `tempfile|mkstemp|NamedTemporaryFile|mkdtemp` token in the source;
    `--path` and `--plan-id` share the same `add_mutually_exclusive_group`.
"""

import ast
import importlib.util
import json
import re
from argparse import Namespace
from pathlib import Path
from unittest import mock

import pytest

from conftest import PlanContext

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
_spec = importlib.util.spec_from_file_location('manage_files_open_in_ide', _MANAGE_FILES_SCRIPT)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

detect_ide = _mod.detect_ide
build_launch_command = _mod.build_launch_command
is_open_in_ide_enabled = _mod.is_open_in_ide_enabled
cmd_open_in_ide = _mod.cmd_open_in_ide
IdeRecord = _mod.IdeRecord
MACOS_JETBRAINS_BUNDLE_IDS = _mod.MACOS_JETBRAINS_BUNDLE_IDS
LINUX_LAUNCHER_PRIORITY = _mod.LINUX_LAUNCHER_PRIORITY


# =============================================================================
# detect_ide — macOS branches
# =============================================================================


@pytest.mark.parametrize(
    'bundle_id, expected_app',
    list(MACOS_JETBRAINS_BUNDLE_IDS.items()),
)
def test_detect_ide_macos_jetbrains_bundle(bundle_id, expected_app):
    # Arrange
    env = {'__CFBundleIdentifier': bundle_id}

    # Act
    result = detect_ide(env, 'darwin')

    # Assert
    assert result is not None
    assert result.name == expected_app
    assert result.launcher_argv == ('open', '-a', expected_app)


def test_detect_ide_macos_vscode():
    # Arrange
    env = {'TERM_PROGRAM': 'vscode'}

    # Act
    result = detect_ide(env, 'darwin')

    # Assert
    assert result is not None
    assert result.name == 'Visual Studio Code'
    assert result.launcher_argv == ('open', '-a', 'Visual Studio Code')


def test_detect_ide_macos_cursor():
    # Arrange
    env = {'TERM_PROGRAM': 'cursor'}

    # Act
    result = detect_ide(env, 'darwin')

    # Assert
    assert result is not None
    assert result.name == 'Cursor'
    assert result.launcher_argv == ('open', '-a', 'Cursor')


def test_detect_ide_macos_cursor_not_substituted_with_vscode():
    """Regression guard: Cursor must NEVER silently become VS Code."""
    # Arrange
    env = {'TERM_PROGRAM': 'cursor'}

    # Act
    result = detect_ide(env, 'darwin')

    # Assert
    assert result is not None
    assert 'Visual Studio Code' not in result.name


def test_detect_ide_macos_unknown_returns_none():
    # Arrange
    env = {'TERM_PROGRAM': 'unknown-terminal'}

    # Act
    result = detect_ide(env, 'darwin')

    # Assert
    assert result is None


def test_detect_ide_macos_empty_env_returns_none():
    # Arrange
    env: dict[str, str] = {}

    # Act
    result = detect_ide(env, 'darwin')

    # Assert
    assert result is None


# =============================================================================
# detect_ide — Linux branches
# =============================================================================


def test_detect_ide_linux_vscode_with_code_on_path():
    # Arrange
    env = {'TERM_PROGRAM': 'vscode'}

    # Act
    with mock.patch.object(_mod.shutil, 'which', side_effect=lambda name: '/usr/bin/code' if name == 'code' else None):
        result = detect_ide(env, 'linux')

    # Assert
    assert result is not None
    assert result.name == 'Visual Studio Code'
    assert result.launcher_argv == ('code',)


def test_detect_ide_linux_vscode_without_code_falls_through_to_jetbrains_probe():
    """When `code` is missing on Linux, fall through to JetBrains probe (not bare open)."""
    # Arrange
    env = {'TERM_PROGRAM': 'vscode'}

    # Act
    with mock.patch.object(_mod.shutil, 'which', return_value=None):
        result = detect_ide(env, 'linux')

    # Assert: TERM_PROGRAM=vscode but `code` missing AND no JetBrains launcher → None
    assert result is None


def test_detect_ide_linux_cursor_with_cursor_on_path():
    # Arrange
    env = {'TERM_PROGRAM': 'cursor'}

    # Act
    with mock.patch.object(_mod.shutil, 'which', side_effect=lambda name: '/usr/bin/cursor' if name == 'cursor' else None):
        result = detect_ide(env, 'linux')

    # Assert
    assert result is not None
    assert result.name == 'Cursor'
    assert result.launcher_argv == ('cursor',)


@pytest.mark.parametrize('launcher', list(LINUX_LAUNCHER_PRIORITY))
def test_detect_ide_linux_jetbrains_priority_probe(launcher):
    """Each launcher in LINUX_LAUNCHER_PRIORITY can be detected in isolation."""
    # Arrange — env has no TERM_PROGRAM signal
    env: dict[str, str] = {}

    # Act — only `launcher` resolves on PATH
    with mock.patch.object(_mod.shutil, 'which', side_effect=lambda name, want=launcher: f'/usr/bin/{name}' if name == want else None):
        result = detect_ide(env, 'linux')

    # Assert
    assert result is not None
    assert result.name == launcher
    assert result.launcher_argv == (launcher,)


def test_detect_ide_linux_priority_first_match_wins():
    """When multiple launchers are on PATH, the priority-ordered first match wins."""
    # Arrange
    env: dict[str, str] = {}
    on_path = {'pycharm', 'idea', 'webstorm'}

    # Act — all three on PATH; idea has the highest priority
    with mock.patch.object(_mod.shutil, 'which', side_effect=lambda name: f'/usr/bin/{name}' if name in on_path else None):
        result = detect_ide(env, 'linux')

    # Assert
    assert result is not None
    assert result.name == 'idea'


def test_detect_ide_linux_no_launchers_returns_none():
    # Arrange
    env: dict[str, str] = {}

    # Act
    with mock.patch.object(_mod.shutil, 'which', return_value=None):
        result = detect_ide(env, 'linux')

    # Assert
    assert result is None


def test_detect_ide_unknown_platform_returns_none():
    # Arrange
    env = {'TERM_PROGRAM': 'vscode'}

    # Act
    result = detect_ide(env, 'win32')

    # Assert
    assert result is None


# =============================================================================
# build_launch_command
# =============================================================================


def test_build_launch_command_macos_open_a():
    # Arrange
    ide = IdeRecord(name='IntelliJ IDEA', launcher_argv=('open', '-a', 'IntelliJ IDEA'))
    path = Path('/abs/path/to/file.md')

    # Act
    argv = build_launch_command(ide, path)

    # Assert
    assert argv == ['open', '-a', 'IntelliJ IDEA', '/abs/path/to/file.md']


def test_build_launch_command_linux_code():
    # Arrange
    ide = IdeRecord(name='Visual Studio Code', launcher_argv=('code',))
    path = Path('/abs/path/to/file.md')

    # Act
    argv = build_launch_command(ide, path)

    # Assert
    assert argv == ['code', '/abs/path/to/file.md']


# =============================================================================
# is_open_in_ide_enabled — config gate
# =============================================================================


def test_is_open_in_ide_enabled_explicit_true():
    # Arrange
    with PlanContext(plan_id='cfg-true') as ctx:
        (ctx.fixture_dir / 'marshal.json').write_text(
            json.dumps({'plan': {'open_in_ide': {'enabled': True}}}), encoding='utf-8'
        )

        # Act
        result = is_open_in_ide_enabled()

        # Assert
        assert result is True


def test_is_open_in_ide_enabled_explicit_false():
    # Arrange
    with PlanContext(plan_id='cfg-false') as ctx:
        (ctx.fixture_dir / 'marshal.json').write_text(
            json.dumps({'plan': {'open_in_ide': {'enabled': False}}}), encoding='utf-8'
        )

        # Act
        result = is_open_in_ide_enabled()

        # Assert
        assert result is False


def test_is_open_in_ide_enabled_missing_enabled_field_defaults_true():
    """plan.open_in_ide exists but has no `enabled` key → default True."""
    # Arrange
    with PlanContext(plan_id='cfg-no-enabled') as ctx:
        (ctx.fixture_dir / 'marshal.json').write_text(
            json.dumps({'plan': {'open_in_ide': {}}}), encoding='utf-8'
        )

        # Act
        result = is_open_in_ide_enabled()

        # Assert
        assert result is True


def test_is_open_in_ide_enabled_missing_open_in_ide_subnamespace_defaults_true():
    """plan namespace present but no `open_in_ide` key → default True."""
    # Arrange
    with PlanContext(plan_id='cfg-no-subns') as ctx:
        (ctx.fixture_dir / 'marshal.json').write_text(
            json.dumps({'plan': {'phase-1-init': {'use_worktree': True}}}), encoding='utf-8'
        )

        # Act
        result = is_open_in_ide_enabled()

        # Assert
        assert result is True


def test_is_open_in_ide_enabled_missing_plan_namespace_defaults_true():
    """No plan namespace at all → default True."""
    # Arrange
    with PlanContext(plan_id='cfg-no-plan') as ctx:
        (ctx.fixture_dir / 'marshal.json').write_text(
            json.dumps({'skill_domains': {}}), encoding='utf-8'
        )

        # Act
        result = is_open_in_ide_enabled()

        # Assert
        assert result is True


def test_is_open_in_ide_enabled_no_marshal_file_defaults_true():
    """marshal.json absent entirely → default True."""
    # Arrange
    with PlanContext(plan_id='cfg-no-file'):
        # Act
        result = is_open_in_ide_enabled()

        # Assert
        assert result is True


@pytest.mark.parametrize(
    'top_level_value',
    ['[]', '"a string"', '42', 'true', 'null'],
)
def test_is_open_in_ide_enabled_non_dict_top_level_raises_value_error(top_level_value):
    """Non-dict top-level JSON in marshal.json raises ValueError naming the file.

    Regression guard for PR #380 gemini-code-assist finding 8be141: the previous
    implementation called `data.get('plan')` directly, which raises AttributeError
    when `data` is a list/scalar. The guard turns that into a clear ValueError.
    """
    # Arrange
    with PlanContext(plan_id=f'cfg-nondict-{abs(hash(top_level_value))}') as ctx:
        marshal_path = ctx.fixture_dir / 'marshal.json'
        marshal_path.write_text(top_level_value, encoding='utf-8')

        # Act / Assert
        with pytest.raises(ValueError) as exc_info:
            is_open_in_ide_enabled()

        # The file path must appear in the message so the user can diagnose.
        assert str(marshal_path) in str(exc_info.value)
        assert 'JSON object' in str(exc_info.value)


# =============================================================================
# cmd_open_in_ide — end-to-end
# =============================================================================


def test_cmd_open_in_ide_mode_a_macos_vscode_success():
    # Arrange
    with PlanContext(plan_id='e2e-mode-a') as ctx:
        (ctx.fixture_dir / 'marshal.json').write_text(
            json.dumps({'plan': {'open_in_ide': {'enabled': True}}}), encoding='utf-8'
        )
        args = Namespace(path='/abs/path/file.md', plan_id=None, document=None)

        completed = mock.MagicMock(returncode=0, stdout='', stderr='')
        # Clear env so the host's __CFBundleIdentifier does not leak in and
        # win over TERM_PROGRAM in the detect_ide priority order.
        with (
            mock.patch.object(_mod.sys, 'platform', 'darwin'),
            mock.patch.object(_mod, 'subprocess') as mock_subprocess,
            mock.patch.dict(_mod.os.environ, {'TERM_PROGRAM': 'vscode'}, clear=True),
        ):
            mock_subprocess.run.return_value = completed

            # Act
            result = cmd_open_in_ide(args)

        # Assert
        assert result['status'] == 'success'
        assert result['ide'] == 'Visual Studio Code'
        assert '/abs/path/file.md' in result['command']
        assert result['path'] == '/abs/path/file.md'


def test_cmd_open_in_ide_disabled_by_config_short_circuits():
    """Disabled-by-config: detect_ide and subprocess.run are NEVER called."""
    # Arrange
    with PlanContext(plan_id='e2e-disabled') as ctx:
        (ctx.fixture_dir / 'marshal.json').write_text(
            json.dumps({'plan': {'open_in_ide': {'enabled': False}}}), encoding='utf-8'
        )
        args = Namespace(path='/abs/path/file.md', plan_id=None, document=None)

        with (
            mock.patch.object(_mod, 'detect_ide') as mock_detect,
            mock.patch.object(_mod, 'subprocess') as mock_subprocess,
        ):
            # Act
            result = cmd_open_in_ide(args)

        # Assert
        assert result['status'] == 'success'
        assert result['action'] == 'skipped'
        assert result['reason'] == 'disabled_by_config'
        assert mock_detect.call_count == 0, 'detect_ide must NOT be invoked when disabled'
        assert mock_subprocess.run.call_count == 0, 'launcher must NOT fire when disabled'


def test_cmd_open_in_ide_missing_key_acts_as_enabled():
    """Missing plan.open_in_ide sub-namespace → behaves as if enabled=true."""
    # Arrange
    with PlanContext(plan_id='e2e-missing-key') as ctx:
        (ctx.fixture_dir / 'marshal.json').write_text(
            json.dumps({'plan': {}}), encoding='utf-8'
        )
        args = Namespace(path='/abs/path/file.md', plan_id=None, document=None)

        completed = mock.MagicMock(returncode=0, stdout='', stderr='')
        with (
            mock.patch.object(_mod.sys, 'platform', 'darwin'),
            mock.patch.object(_mod, 'subprocess') as mock_subprocess,
            mock.patch.dict(_mod.os.environ, {'TERM_PROGRAM': 'vscode'}, clear=True),
        ):
            mock_subprocess.run.return_value = completed

            # Act
            result = cmd_open_in_ide(args)

        # Assert: detection ran (we matched VS Code on macOS via TERM_PROGRAM)
        assert result['status'] == 'success'
        assert result['ide'] == 'Visual Studio Code'


def test_cmd_open_in_ide_unknown_ide_returns_ide_not_detected():
    # Arrange
    with PlanContext(plan_id='e2e-unknown-ide') as ctx:
        (ctx.fixture_dir / 'marshal.json').write_text(
            json.dumps({'plan': {'open_in_ide': {'enabled': True}}}), encoding='utf-8'
        )
        args = Namespace(path='/abs/path/file.md', plan_id=None, document=None)

        with (
            mock.patch.object(_mod.sys, 'platform', 'darwin'),
            mock.patch.dict(_mod.os.environ, {}, clear=True),
        ):
            # Act
            result = cmd_open_in_ide(args)

        # Assert
        assert result['status'] == 'error'
        assert result['reason'] == 'ide_not_detected'


def test_cmd_open_in_ide_launcher_missing_returns_launcher_missing():
    # Arrange
    with PlanContext(plan_id='e2e-launcher-missing') as ctx:
        (ctx.fixture_dir / 'marshal.json').write_text(
            json.dumps({'plan': {'open_in_ide': {'enabled': True}}}), encoding='utf-8'
        )
        args = Namespace(path='/abs/path/file.md', plan_id=None, document=None)

        with (
            mock.patch.object(_mod.sys, 'platform', 'darwin'),
            mock.patch.object(_mod, 'subprocess') as mock_subprocess,
            mock.patch.dict(_mod.os.environ, {'TERM_PROGRAM': 'vscode'}, clear=True),
        ):
            mock_subprocess.run.side_effect = FileNotFoundError('open not found')

            # Act
            result = cmd_open_in_ide(args)

        # Assert
        assert result['status'] == 'error'
        assert result['reason'] == 'launcher_missing'


def test_cmd_open_in_ide_mode_b_without_document_returns_invalid_arguments():
    # Arrange — emulate the case where argparse let through plan-id without --document
    # (e.g., direct function call rather than CLI invocation).
    with PlanContext(plan_id='e2e-mode-b-no-doc') as ctx:
        (ctx.fixture_dir / 'marshal.json').write_text(
            json.dumps({'plan': {'open_in_ide': {'enabled': True}}}), encoding='utf-8'
        )
        args = Namespace(path=None, plan_id='some-plan', document=None)

        # Act
        result = cmd_open_in_ide(args)

        # Assert
        assert result['status'] == 'error'
        assert result['reason'] == 'invalid_arguments'


def test_cmd_open_in_ide_mode_b_document_resolution_failure():
    # Arrange
    with PlanContext(plan_id='e2e-mode-b-resolver-fail') as ctx:
        (ctx.fixture_dir / 'marshal.json').write_text(
            json.dumps({'plan': {'open_in_ide': {'enabled': True}}}), encoding='utf-8'
        )
        args = Namespace(path=None, plan_id='e2e-mode-b-resolver-fail', document='solution_outline')

        # Simulate resolver returning non-zero
        proc = mock.MagicMock(returncode=2, stdout='', stderr='no outline found')
        with mock.patch.object(_mod, 'subprocess') as mock_subprocess:
            mock_subprocess.run.return_value = proc

            # Act
            result = cmd_open_in_ide(args)

        # Assert
        assert result['status'] == 'error'
        assert result['reason'] == 'document_resolution_failed'


# =============================================================================
# Static guards — enforce hard invariants from solution_outline.md
# =============================================================================


def test_manage_files_source_does_not_import_tempfile():
    """AST guard: `tempfile` MUST NOT appear in any import statement."""
    # Arrange
    source = _MANAGE_FILES_SCRIPT.read_text(encoding='utf-8')
    tree = ast.parse(source)

    # Act
    bad_imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == 'tempfile' or alias.name.startswith('tempfile.'):
                    bad_imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module == 'tempfile' or (node.module or '').startswith('tempfile.'):
                bad_imports.append(node.module or '')

    # Assert
    assert bad_imports == [], f'manage-files.py must not import tempfile, found: {bad_imports}'


def test_manage_files_source_has_no_temp_file_tokens():
    """Regex guard: source must not contain tempfile-related identifiers."""
    # Arrange
    source = _MANAGE_FILES_SCRIPT.read_text(encoding='utf-8')

    # Strip module-level docstring lines that may legitimately mention the token
    # for documentation purposes. We do this by stripping the leading docstring.
    tree = ast.parse(source)
    module_doc = ast.get_docstring(tree)
    if module_doc is not None:
        # Re-emit the source with the docstring removed by replacing it once.
        source_without_doc = source.replace(module_doc, '')
    else:
        source_without_doc = source

    forbidden = ('tempfile', 'NamedTemporaryFile', 'mkstemp', 'mkdtemp')

    # Act
    hits: list[str] = []
    for token in forbidden:
        # Use word-boundary regex so partial matches inside other identifiers
        # are not counted.
        if re.search(rf'\b{re.escape(token)}\b', source_without_doc):
            hits.append(token)

    # Assert
    assert hits == [], f'manage-files.py contains forbidden temp-file tokens (outside docstring): {hits}'


def test_open_in_ide_path_and_plan_id_share_mutex_group():
    """AST guard: --path and --plan-id MUST be added to the same mutex group."""
    # Arrange
    source = _MANAGE_FILES_SCRIPT.read_text(encoding='utf-8')

    # Act / Assert — locate the open-in-ide subparser block and verify both
    # --path and --plan-id are added via the SAME mutex variable.
    # The simplest deterministic check: scan for a block that contains both
    # `open_mutex.add_argument('--path'` and `open_mutex.add_argument('--plan-id'`
    # (or `add_argument(\n        '--plan-id'` style — match flexibly).
    has_path_in_mutex = re.search(
        r"open_mutex\.add_argument\(\s*['\"]--path['\"]",
        source,
    )
    has_plan_id_in_mutex = re.search(
        r"open_mutex\.add_argument\(\s*['\"]--plan-id['\"]",
        source,
    )
    assert has_path_in_mutex, '--path must be added to the open-in-ide mutex group'
    assert has_plan_id_in_mutex, '--plan-id must be added to the open-in-ide mutex group'

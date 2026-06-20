#!/usr/bin/env python3
"""Tests for _gradle_execute.py.

Tests the Gradle execution config and factory-generated functions.
"""

import sys
from unittest.mock import MagicMock

from conftest import load_script_module

sys.modules.setdefault('plan_logging', MagicMock(log_entry=MagicMock()))
sys.modules.setdefault('run_config', MagicMock(timeout_get=MagicMock(return_value=300), timeout_set=MagicMock()))


_gradle_execute_mod = load_script_module('plan-marshall', 'build-gradle', '_gradle_execute.py', '_gradle_execute')

import _build_execute_factory as _factory  # noqa: E402

_CONFIG = _gradle_execute_mod._CONFIG
execute_direct = _gradle_execute_mod.execute_direct


def test_config_tool_name():
    """Config has correct tool name."""
    assert _CONFIG.tool_name == 'gradle'


def test_config_wrapper_names():
    """Config has correct wrapper names for Gradle."""
    assert _CONFIG.unix_wrapper == 'gradlew'
    assert _CONFIG.windows_wrapper == 'gradlew.bat'
    assert _CONFIG.system_fallback == 'gradle'


def test_config_default_timeout():
    """Config has 300s default timeout (unified across all build skills)."""
    assert _CONFIG.default_timeout == 300


def test_config_capture_strategy():
    """Config uses stdout redirect."""
    from _build_execute import CaptureStrategy

    assert _CONFIG.capture_strategy == CaptureStrategy.STDOUT_REDIRECT


def test_command_key_fn_build():
    """Extracts 'build' from args."""
    assert _CONFIG.command_key_fn('build') == 'build'


def test_command_key_fn_module_task():
    """Extracts module:task, colons to underscores."""
    assert _CONFIG.command_key_fn(':core:build') == 'core_build'


def test_command_key_fn_empty():
    """Returns 'default' for empty args."""
    assert _CONFIG.command_key_fn('') == 'default'


def test_scope_fn_default():
    """Scope is 'default' for root build."""
    assert _CONFIG.scope_fn('build') == 'default'


def test_scope_fn_colon_prefix():
    """Extracts module from :module:task format."""
    assert _CONFIG.scope_fn(':auth-service:build') == 'auth-service'


def test_scope_fn_p_flag():
    """Extracts scope from -p flag."""
    assert _CONFIG.scope_fn('-p services/auth build') == 'auth'


def test_build_command_fn():
    """Builds command with --console=plain."""
    cmd_parts, cmd_str = _CONFIG.build_command_fn('./gradlew', 'build', '/tmp/log.log')
    assert cmd_parts == ['./gradlew', 'build', '--console=plain']
    assert '--console=plain' in cmd_str


def test_build_command_fn_with_module():
    """Includes module task in command."""
    cmd_parts, cmd_str = _CONFIG.build_command_fn('./gradlew', ':core:build', '/tmp/log.log')
    assert cmd_parts == ['./gradlew', ':core:build', '--console=plain']


def test_config_require_wrapper_default_on():
    """Gradle defaults to require_wrapper=True — no silent system-gradle fallback."""
    assert _CONFIG.require_wrapper is True


def test_execute_direct_error_on_nonexistent_project(tmp_path, monkeypatch):
    """execute_direct returns the wrapper-not-found error when running in an
    empty directory: with require_wrapper=True the factory gate raises rather
    than falling through to a system gradle."""
    # Pin PLAN_BASE_DIR so the shared learned-timeout machinery
    # (run_config.timeout_set) writes into tmp_path, not the real repo-local
    # run-configuration.json.
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))

    # Empty tmp_path has no gradlew — the require_wrapper=True gate raises and
    # the except-arm converts it to a structured error. NO system gradle runs.
    result = execute_direct(
        args='build',
        command_key='gradle:build',
        project_dir=str(tmp_path),
    )
    assert result['status'] == 'error'
    assert result['exit_code'] == -1
    assert 'No gradle wrapper found' in result['error']


def test_execute_direct_resolves_present_wrapper(tmp_path, monkeypatch):
    """With a present gradlew, the gate passes and the build attempts ./gradlew."""
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
    (tmp_path / 'gradlew').write_text('#!/bin/sh\n')

    calls = []

    def _recorder(**kwargs):
        calls.append(kwargs)
        return {
            'status': 'success',
            'exit_code': 0,
            'duration_seconds': 0,
            'log_file': '',
            'command': './gradlew build',
        }

    monkeypatch.setattr(_factory, 'execute_direct_base', _recorder)

    result = execute_direct(args='build', command_key='gradle:build', project_dir=str(tmp_path))

    assert result['status'] == 'success'
    assert calls[0]['wrapper'] == './gradlew'

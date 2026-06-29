#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for _maven_execute.py.

Tests the Maven execution config and factory-generated functions.
"""

import sys
from unittest.mock import MagicMock

from conftest import load_script_module

sys.modules.setdefault('plan_logging', MagicMock(log_entry=MagicMock()))
sys.modules.setdefault('run_config', MagicMock(timeout_get=MagicMock(return_value=300), timeout_set=MagicMock()))


_maven_execute_mod = load_script_module('plan-marshall', 'build-maven', '_maven_execute.py', '_maven_execute')

import _build_execute_factory as _factory  # noqa: E402

_CONFIG = _maven_execute_mod._CONFIG
execute_direct = _maven_execute_mod.execute_direct

# =============================================================================
# Config Tests
# =============================================================================


def test_config_tool_name():
    """Config has correct tool name."""
    assert _CONFIG.tool_name == 'maven'


def test_config_wrapper_names():
    """Config has correct wrapper names for Maven."""
    assert _CONFIG.unix_wrapper == 'mvnw'
    assert _CONFIG.windows_wrapper == 'mvnw.cmd'
    assert _CONFIG.system_fallback == 'mvn'


def test_config_default_timeout():
    """Config has 300s default timeout (unified across all build skills)."""
    assert _CONFIG.default_timeout == 300


def test_config_capture_strategy():
    """Config uses Maven log flag strategy."""
    from _build_execute import CaptureStrategy

    assert _CONFIG.capture_strategy == CaptureStrategy.TOOL_LOG_FLAG


# =============================================================================
# Command Key Function
# =============================================================================


def test_command_key_fn_verify():
    """Extracts 'verify' from args."""
    assert _CONFIG.command_key_fn('verify') == 'verify'


def test_command_key_fn_clean_install():
    """Scope-aware: full args normalized to underscores."""
    assert _CONFIG.command_key_fn('clean install') == 'clean_install'


def test_command_key_fn_module_tests():
    """Scope-aware: module scope preserved in key to avoid cross-scope collisions."""
    assert _CONFIG.command_key_fn('test -pl core') == 'test__pl_core'


def test_command_key_fn_empty():
    """Returns 'default' for empty args."""
    assert _CONFIG.command_key_fn('') == 'default'


# =============================================================================
# Scope Function
# =============================================================================


def test_scope_fn_default_no_pl():
    """Scope is 'default' when no -pl argument."""
    assert _CONFIG.scope_fn('verify') == 'default'


def test_scope_fn_extracts_module():
    """Extracts module name from -pl argument."""
    assert _CONFIG.scope_fn('verify -pl core-api') == 'core-api'


def test_scope_fn_pl_equals():
    """Handles -pl=module form."""
    assert _CONFIG.scope_fn('verify -pl=my-module') == 'my-module'


# =============================================================================
# Build Command Function
# =============================================================================


def test_build_command_fn():
    """Builds command with -l flag for log file."""
    cmd_parts, cmd_str = _CONFIG.build_command_fn('./mvnw', 'verify', '/tmp/log.log')
    assert cmd_parts == ['./mvnw', '-l', '/tmp/log.log', 'verify']
    assert '-l' in cmd_str
    assert '/tmp/log.log' in cmd_str


def test_build_command_fn_with_module():
    """Includes module argument in command."""
    cmd_parts, cmd_str = _CONFIG.build_command_fn('./mvnw', 'test -pl core', '/tmp/log.log')
    assert cmd_parts == ['./mvnw', '-l', '/tmp/log.log', 'test', '-pl', 'core']


# =============================================================================
# Wrapper Resolution and Execution
# =============================================================================


def test_config_has_no_require_wrapper_knob():
    """The require_wrapper gate is removed — ExecuteConfig no longer carries it,
    so Maven auto-detects the wrapper and falls back to the system binary."""
    assert not hasattr(_CONFIG, 'require_wrapper')


def test_execute_direct_absent_wrapper_resolves_system_binary(tmp_path, monkeypatch):
    """execute_direct auto-resolves to the system 'mvn' binary when running in an
    empty directory: with the gate removed, an absent mvnw falls back to the
    system binary with no wrapper-not-found error and no FileNotFoundError during
    resolution."""
    # Pin PLAN_BASE_DIR so the shared learned-timeout machinery
    # (run_config.timeout_set) writes into tmp_path, not the real repo-local
    # run-configuration.json.
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))

    calls = []

    def _recorder(**kwargs):
        calls.append(kwargs)
        return {'status': 'success', 'exit_code': 0, 'duration_seconds': 0, 'log_file': '', 'command': 'mvn verify'}

    monkeypatch.setattr(_factory, 'execute_direct_base', _recorder)

    # Empty tmp_path has no mvnw — resolution falls back to the system 'mvn'.
    result = execute_direct(
        args='verify',
        command_key='maven:verify',
        project_dir=str(tmp_path),
    )
    assert result['status'] == 'success'
    assert calls[0]['wrapper'] == 'mvn'


def test_execute_direct_resolves_present_wrapper(tmp_path, monkeypatch):
    """With a present mvnw, resolution prefers the project wrapper ./mvnw."""
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
    (tmp_path / 'mvnw').write_text('#!/bin/sh\n')

    calls = []

    def _recorder(**kwargs):
        calls.append(kwargs)
        return {'status': 'success', 'exit_code': 0, 'duration_seconds': 0, 'log_file': '', 'command': './mvnw verify'}

    monkeypatch.setattr(_factory, 'execute_direct_base', _recorder)

    result = execute_direct(args='verify', command_key='maven:verify', project_dir=str(tmp_path))

    assert result['status'] == 'success'
    assert calls[0]['wrapper'] == './mvnw'

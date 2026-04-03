#!/usr/bin/env python3
"""Tests for _gradle_execute.py.

Tests the Gradle execution config and factory-generated functions.
"""

from unittest.mock import MagicMock, patch

import pytest
import sys

sys.modules.setdefault('plan_logging', MagicMock(log_entry=MagicMock()))
sys.modules.setdefault('run_config', MagicMock(timeout_get=MagicMock(return_value=300), timeout_set=MagicMock()))

from _gradle_execute import _CONFIG, execute_direct


# =============================================================================
# Config Tests
# =============================================================================


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


# =============================================================================
# Command Key Function
# =============================================================================


def test_command_key_fn_build():
    """Extracts 'build' from args."""
    assert _CONFIG.command_key_fn('build') == 'build'


def test_command_key_fn_module_task():
    """Extracts module:task, colons to underscores."""
    assert _CONFIG.command_key_fn(':core:build') == 'core_build'


def test_command_key_fn_empty():
    """Returns 'default' for empty args."""
    assert _CONFIG.command_key_fn('') == 'default'


# =============================================================================
# Scope Function
# =============================================================================


def test_scope_fn_default():
    """Scope is 'default' for root build."""
    assert _CONFIG.scope_fn('build') == 'default'


def test_scope_fn_colon_prefix():
    """Extracts module from :module:task format."""
    assert _CONFIG.scope_fn(':auth-service:build') == 'auth-service'


def test_scope_fn_p_flag():
    """Extracts scope from -p flag."""
    assert _CONFIG.scope_fn('-p services/auth build') == 'auth'


# =============================================================================
# Build Command Function
# =============================================================================


def test_build_command_fn():
    """Builds command with --console=plain."""
    cmd_parts, cmd_str = _CONFIG.build_command_fn('./gradlew', 'build', '/tmp/log.log')
    assert cmd_parts == ['./gradlew', 'build', '--console=plain']
    assert '--console=plain' in cmd_str


def test_build_command_fn_with_module():
    """Includes module task in command."""
    cmd_parts, cmd_str = _CONFIG.build_command_fn('./gradlew', ':core:build', '/tmp/log.log')
    assert cmd_parts == ['./gradlew', ':core:build', '--console=plain']


# =============================================================================
# Wrapper Resolution and Execution
# =============================================================================


def test_execute_direct_error_on_nonexistent_project(tmp_path):
    """execute_direct returns error when running in empty directory without wrapper."""
    # Empty tmp_path has no gradlew — if system gradle exists, it will fail
    result = execute_direct(
        args='build',
        command_key='gradle:build',
        project_dir=str(tmp_path),
    )
    # Either wrapper not found (status=error, exit_code=-1) or
    # gradle runs but fails on missing build.gradle (status=error, exit_code!=0)
    assert result['status'] == 'error'
    assert result['exit_code'] != 0

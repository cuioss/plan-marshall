#!/usr/bin/env python3
"""Tests for _python_execute.py.

Tests the Python execution config and factory-generated functions.
"""

from unittest.mock import MagicMock, patch

import pytest

# Mock runtime-only modules before importing
import sys

sys.modules.setdefault('plan_logging', MagicMock(log_entry=MagicMock()))
sys.modules.setdefault('run_config', MagicMock(timeout_get=MagicMock(return_value=300), timeout_set=MagicMock()))

from _python_execute import _CONFIG, execute_direct


# =============================================================================
# Config Tests
# =============================================================================


def test_config_tool_name():
    """Config has correct tool name."""
    assert _CONFIG.tool_name == 'python'


def test_config_wrapper_names():
    """Config has correct wrapper names for pyprojectx."""
    assert _CONFIG.unix_wrapper == 'pw'
    assert _CONFIG.windows_wrapper == 'pw.bat'
    assert _CONFIG.system_fallback == 'pwx'


def test_config_default_timeout():
    """Config has 300s default timeout."""
    assert _CONFIG.default_timeout == 300


def test_config_capture_strategy():
    """Config uses stdout redirect (not log flag)."""
    from _build_execute import CaptureStrategy

    assert _CONFIG.capture_strategy == CaptureStrategy.STDOUT_REDIRECT


# =============================================================================
# Command Key Function
# =============================================================================


def test_command_key_fn_verify():
    """Extracts 'verify' from args."""
    assert _CONFIG.command_key_fn('verify') == 'verify'


def test_command_key_fn_module_tests():
    """Extracts first token, normalizes hyphens."""
    assert _CONFIG.command_key_fn('module-tests core') == 'module_tests'


def test_command_key_fn_empty():
    """Returns 'default' for empty args."""
    assert _CONFIG.command_key_fn('') == 'default'


# =============================================================================
# Scope Function
# =============================================================================


def test_scope_fn_default_for_single_arg():
    """Python scope is 'default' for single-arg commands."""
    assert _CONFIG.scope_fn('verify') == 'default'


def test_scope_fn_extracts_module():
    """Python scope extracts module name from second arg."""
    assert _CONFIG.scope_fn('module-tests core') == 'core'
    assert _CONFIG.scope_fn('verify plan-marshall') == 'plan-marshall'


# =============================================================================
# Build Command Function
# =============================================================================


def test_build_command_fn():
    """Builds command parts from wrapper and args."""
    cmd_parts, cmd_str = _CONFIG.build_command_fn('./pw', 'verify', '/tmp/log.log')
    assert cmd_parts == ['./pw', 'verify']
    assert cmd_str == './pw verify'


def test_build_command_fn_with_module():
    """Includes module argument in command."""
    cmd_parts, cmd_str = _CONFIG.build_command_fn('./pw', 'module-tests core', '/tmp/log.log')
    assert cmd_parts == ['./pw', 'module-tests', 'core']


# =============================================================================
# Wrapper Resolution
# =============================================================================


def test_wrapper_resolve_raises_when_missing(tmp_path):
    """Raises FileNotFoundError when no wrapper found."""
    with patch('_build_execute.shutil.which', return_value=None):
        with pytest.raises(FileNotFoundError, match='No pyprojectx wrapper found'):
            _CONFIG.wrapper_resolve_fn(str(tmp_path))


def test_execute_direct_error_on_missing_wrapper(tmp_path):
    """execute_direct returns error result when wrapper not found."""
    with patch('_build_execute.shutil.which', return_value=None):
        result = execute_direct(
            args='verify',
            command_key='python:verify',
            project_dir=str(tmp_path),
        )
        assert result['status'] == 'error'
        assert result['exit_code'] == -1

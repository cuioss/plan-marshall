#!/usr/bin/env python3
"""Tests for _npm_execute.py.

Tests the npm execution config, npm/npx detection, and factory-generated functions.
"""

from unittest.mock import MagicMock

import sys

sys.modules.setdefault('plan_logging', MagicMock(log_entry=MagicMock()))
sys.modules.setdefault('run_config', MagicMock(timeout_get=MagicMock(return_value=120), timeout_set=MagicMock()))

from _npm_execute import NPX_COMMANDS, _CONFIG, detect_command_type


# =============================================================================
# Config Tests
# =============================================================================


def test_config_tool_name():
    """Config has correct tool name."""
    assert _CONFIG.tool_name == 'npm'


def test_config_default_timeout():
    """Config has 300s default timeout (unified across all build skills)."""
    assert _CONFIG.default_timeout == 300


def test_config_capture_strategy():
    """Config uses stdout redirect."""
    from _build_execute import CaptureStrategy

    assert _CONFIG.capture_strategy == CaptureStrategy.STDOUT_REDIRECT


def test_config_supports_env_vars():
    """Config enables env var support."""
    assert _CONFIG.supports_env_vars is True


def test_config_supports_working_dir():
    """Config enables working dir support."""
    assert _CONFIG.supports_working_dir is True


def test_config_parser_needs_command():
    """Config requires command arg for parser."""
    assert _CONFIG.parser_needs_command is True


# =============================================================================
# detect_command_type - npm vs npx routing
# =============================================================================


def test_detect_npm_for_run():
    """'run test' uses npm."""
    assert detect_command_type('run test') == 'npm'


def test_detect_npm_for_install():
    """'install' uses npm."""
    assert detect_command_type('install') == 'npm'


def test_detect_npx_for_playwright():
    """'playwright test' uses npx."""
    assert detect_command_type('playwright test') == 'npx'


def test_detect_npx_for_eslint():
    """'eslint src/' uses npx."""
    assert detect_command_type('eslint src/') == 'npx'


def test_detect_npx_for_tsc():
    """'tsc --noEmit' uses npx."""
    assert detect_command_type('tsc --noEmit') == 'npx'


def test_detect_npx_for_jest():
    """'jest --coverage' uses npx."""
    assert detect_command_type('jest --coverage') == 'npx'


def test_detect_npx_for_vitest():
    """'vitest run' uses npx."""
    assert detect_command_type('vitest run') == 'npx'


def test_detect_npx_case_insensitive():
    """Detection is case-insensitive."""
    assert detect_command_type('Playwright test') == 'npx'
    assert detect_command_type('ESLINT src/') == 'npx'


def test_detect_npm_for_unknown():
    """Unknown commands default to npm."""
    assert detect_command_type('custom-script') == 'npm'


def test_all_npx_commands_detected():
    """All NPX_COMMANDS are detected as npx."""
    for cmd in NPX_COMMANDS:
        assert detect_command_type(f'{cmd} --help') == 'npx', f'{cmd} should use npx'


# =============================================================================
# Scope Function
# =============================================================================


def test_scope_fn_default():
    """Default scope for commands without workspace."""
    assert _CONFIG.scope_fn('run test') == 'default'


def test_scope_fn_workspace():
    """Extracts workspace name from --workspace= flag."""
    assert _CONFIG.scope_fn('run test --workspace=my-pkg') == 'my-pkg'


def test_scope_fn_prefix():
    """Extracts scope from --prefix flag."""
    assert _CONFIG.scope_fn('run test --prefix packages/core') == 'packages/core'


# =============================================================================
# Command Key Function
# =============================================================================


def test_command_key_fn_run():
    """Extracts 'run' from 'run test'."""
    assert _CONFIG.command_key_fn('run test') == 'run'


def test_command_key_fn_install():
    """Extracts 'install' from 'install'."""
    assert _CONFIG.command_key_fn('install') == 'install'


def test_command_key_fn_empty():
    """Returns 'default' for empty args."""
    assert _CONFIG.command_key_fn('') == 'default'


# =============================================================================
# Build Command Function
# =============================================================================


def test_build_command_fn_npm():
    """Routes to npm for 'run test'."""
    cmd_parts, cmd_str = _CONFIG.build_command_fn('npm', 'run test', '/tmp/log.log')
    assert cmd_parts == ['npm', 'run', 'test']
    assert cmd_str == 'npm run test'


def test_build_command_fn_npx():
    """Routes to npx for 'eslint src/'."""
    cmd_parts, cmd_str = _CONFIG.build_command_fn('npm', 'eslint src/', '/tmp/log.log')
    assert cmd_parts == ['npx', 'eslint', 'src/']
    assert cmd_str == 'npx eslint src/'


# =============================================================================
# Wrapper Resolution
# =============================================================================


def test_wrapper_resolve_fn_returns_npm():
    """npm wrapper resolver always returns 'npm'."""
    assert _CONFIG.wrapper_resolve_fn('.') == 'npm'


# =============================================================================
# Extra Result Function
# =============================================================================


def test_extra_result_fn_npm():
    """Extra result includes command_type=npm for npm commands."""
    result = _CONFIG.extra_result_fn('run test', 'npm')
    assert result == {'command_type': 'npm'}


def test_extra_result_fn_npx():
    """Extra result includes command_type=npx for npx commands."""
    result = _CONFIG.extra_result_fn('eslint src/', 'npm')
    assert result == {'command_type': 'npx'}

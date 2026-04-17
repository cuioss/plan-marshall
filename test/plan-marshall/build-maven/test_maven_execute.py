#!/usr/bin/env python3
"""Tests for _maven_execute.py.

Tests the Maven execution config and factory-generated functions.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.modules.setdefault('plan_logging', MagicMock(log_entry=MagicMock()))
sys.modules.setdefault('run_config', MagicMock(timeout_get=MagicMock(return_value=300), timeout_set=MagicMock()))

# Tier 2 direct imports via importlib for uniform import style
import importlib.util  # noqa: E402

_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace' / 'bundles' / 'plan-marshall' / 'skills' / 'build-maven' / 'scripts'
)


def _load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_maven_execute_mod = _load_module('_maven_execute', '_maven_execute.py')

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


def test_execute_direct_error_on_nonexistent_project(tmp_path, monkeypatch):
    """execute_direct returns error when running in empty directory without wrapper."""
    # Pin PLAN_BASE_DIR so the shared learned-timeout machinery
    # (run_config.timeout_set) writes into tmp_path, not the real repo-local
    # run-configuration.json.
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))

    # Empty tmp_path has no mvnw — if system mvn exists, it will fail on missing pom.xml
    result = execute_direct(
        args='verify',
        command_key='maven:verify',
        project_dir=str(tmp_path),
    )
    # Either wrapper not found (status=error, exit_code=-1) or
    # maven runs but fails on missing pom.xml (status=error, exit_code=1)
    assert result['status'] == 'error'
    assert result['exit_code'] != 0

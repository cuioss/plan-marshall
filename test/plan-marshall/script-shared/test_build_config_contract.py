#!/usr/bin/env python3
"""Cross-build-system contract tests (H48).

Verifies that all four build skill ExecuteConfig objects conform to the
shared contract documented in build-api-reference.md. Ensures the unified
API is actually consistent across Maven, Gradle, npm, and Python.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

# Mock runtime-only modules before importing configs
sys.modules.setdefault('plan_logging', MagicMock(log_entry=MagicMock()))
sys.modules.setdefault('run_config', MagicMock(timeout_get=MagicMock(return_value=300), timeout_set=MagicMock()))

# Tier 2 direct imports via importlib for uniform import style
import importlib.util  # noqa: E402

_BUNDLES_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace' / 'bundles' / 'plan-marshall' / 'skills'
)


def _load_module(name, filename, skill):
    spec = importlib.util.spec_from_file_location(
        name, _BUNDLES_DIR / skill / 'scripts' / filename
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_gradle_execute_mod = _load_module('_gradle_execute', '_gradle_execute.py', 'build-gradle')
_maven_execute_mod = _load_module('_maven_execute', '_maven_execute.py', 'build-maven')
_npm_execute_mod = _load_module('_npm_execute', '_npm_execute.py', 'build-npm')
_python_execute_mod = _load_module('_python_execute', '_python_execute.py', 'build-python')

GRADLE_CONFIG = _gradle_execute_mod._CONFIG
MAVEN_CONFIG = _maven_execute_mod._CONFIG
NPM_CONFIG = _npm_execute_mod._CONFIG
PYTHON_CONFIG = _python_execute_mod._CONFIG

ALL_CONFIGS = {
    'maven': MAVEN_CONFIG,
    'gradle': GRADLE_CONFIG,
    'npm': NPM_CONFIG,
    'python': PYTHON_CONFIG,
}


# =============================================================================
# Shared Contract: All configs must have required attributes
# =============================================================================


def test_all_configs_have_tool_name():
    """Every config has a non-empty tool_name."""
    for name, config in ALL_CONFIGS.items():
        assert hasattr(config, 'tool_name'), f'{name} missing tool_name'
        assert config.tool_name, f'{name} has empty tool_name'


def test_all_configs_have_default_timeout():
    """Every config has a 300s default timeout (unified standard)."""
    for name, config in ALL_CONFIGS.items():
        assert config.default_timeout == 300, f'{name} has non-standard timeout: {config.default_timeout}'


def test_all_configs_have_capture_strategy():
    """Every config specifies a capture strategy."""
    from _build_execute import CaptureStrategy

    for name, config in ALL_CONFIGS.items():
        assert isinstance(config.capture_strategy, CaptureStrategy), f'{name} has invalid capture_strategy'


def test_all_configs_have_callable_scope_fn():
    """Every config has a callable scope_fn."""
    for name, config in ALL_CONFIGS.items():
        assert callable(config.scope_fn), f'{name} scope_fn not callable'


def test_all_configs_have_callable_command_key_fn():
    """Every config has a callable command_key_fn."""
    for name, config in ALL_CONFIGS.items():
        assert callable(config.command_key_fn), f'{name} command_key_fn not callable'


def test_all_configs_have_callable_build_command_fn():
    """Every config has a callable build_command_fn."""
    for name, config in ALL_CONFIGS.items():
        assert callable(config.build_command_fn), f'{name} build_command_fn not callable'


# =============================================================================
# Shared Contract: scope_fn returns 'default' for unscoped commands
# =============================================================================


def test_all_scope_fns_return_default_for_simple_command():
    """Every scope_fn returns 'default' when no module/workspace is specified."""
    # Simple commands without module routing
    simple_args = {
        'maven': 'verify',
        'gradle': 'build',
        'npm': 'run test',
        'python': 'verify',
    }
    for name, config in ALL_CONFIGS.items():
        result = config.scope_fn(simple_args[name])
        assert result == 'default', f'{name} scope_fn("{simple_args[name]}") returned "{result}", expected "default"'


# =============================================================================
# Shared Contract: command_key_fn returns 'default' for empty args
# =============================================================================


def test_all_command_key_fns_handle_empty_args():
    """Every command_key_fn returns 'default' for empty args."""
    for name, config in ALL_CONFIGS.items():
        result = config.command_key_fn('')
        assert result == 'default', f'{name} command_key_fn("") returned "{result}", expected "default"'


# =============================================================================
# Shared Contract: build_command_fn returns tuple of (list, str)
# =============================================================================


def test_all_build_command_fns_return_correct_types():
    """Every build_command_fn returns (list[str], str) tuple."""
    test_args = {
        'maven': ('verify', '/tmp/log.log'),
        'gradle': ('build', '/tmp/log.log'),
        'npm': ('run test', '/tmp/log.log'),
        'python': ('verify', '/tmp/log.log'),
    }
    for name, config in ALL_CONFIGS.items():
        args, log = test_args[name]
        wrapper = f'./test-{name}'
        result = config.build_command_fn(wrapper, args, log)
        assert isinstance(result, tuple), f'{name} build_command_fn should return tuple'
        assert len(result) == 2, f'{name} build_command_fn should return 2-element tuple'
        cmd_parts, cmd_str = result
        assert isinstance(cmd_parts, list), f'{name} cmd_parts should be list'
        assert isinstance(cmd_str, str), f'{name} cmd_str should be string'
        assert all(isinstance(p, str) for p in cmd_parts), f'{name} cmd_parts should contain strings'

#!/usr/bin/env python3
"""Cross-build-system contract tests (H48).

Verifies that all four build skill ExecuteConfig objects conform to the
shared contract documented in build-api-reference.md. Ensures the unified
API is actually consistent across Maven, Gradle, npm, and Python.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Mock runtime-only modules before importing configs
sys.modules.setdefault('plan_logging', MagicMock(log_entry=MagicMock()))
sys.modules.setdefault('run_config', MagicMock(timeout_get=MagicMock(return_value=300), timeout_set=MagicMock()))

import importlib.util  # noqa: E402

_BUNDLES_DIR = Path(__file__).parent.parent.parent.parent / 'marketplace' / 'bundles' / 'plan-marshall' / 'skills'


def _load_module(name, filename, skill):
    spec = importlib.util.spec_from_file_location(name, _BUNDLES_DIR / skill / 'scripts' / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_gradle_execute_mod = _load_module('_gradle_execute', '_gradle_execute.py', 'build-gradle')
_maven_execute_mod = _load_module('_maven_execute', '_maven_execute.py', 'build-maven')
_npm_execute_mod = _load_module('_npm_execute', '_npm_execute.py', 'build-npm')
_pyproject_execute_mod = _load_module('_pyproject_execute', '_pyproject_execute.py', 'build-pyproject')

GRADLE_CONFIG = _gradle_execute_mod._CONFIG
MAVEN_CONFIG = _maven_execute_mod._CONFIG
NPM_CONFIG = _npm_execute_mod._CONFIG
PYTHON_CONFIG = _pyproject_execute_mod._CONFIG

ALL_CONFIGS = {
    'maven': MAVEN_CONFIG,
    'gradle': GRADLE_CONFIG,
    'npm': NPM_CONFIG,
    'python': PYTHON_CONFIG,
}

CONFIG_PARAMS = list(ALL_CONFIGS.items())
CONFIG_IDS = list(ALL_CONFIGS.keys())


@pytest.mark.parametrize('name,config', CONFIG_PARAMS, ids=CONFIG_IDS)
def test_config_has_tool_name(name, config):
    assert hasattr(config, 'tool_name'), f'{name} missing tool_name'
    assert config.tool_name, f'{name} has empty tool_name'


@pytest.mark.parametrize('name,config', CONFIG_PARAMS, ids=CONFIG_IDS)
def test_config_has_default_timeout(name, config):
    assert config.default_timeout == 300, f'{name} has non-standard timeout: {config.default_timeout}'


@pytest.mark.parametrize('name,config', CONFIG_PARAMS, ids=CONFIG_IDS)
def test_config_has_capture_strategy(name, config):
    from _build_execute import CaptureStrategy

    assert isinstance(config.capture_strategy, CaptureStrategy), f'{name} has invalid capture_strategy'


@pytest.mark.parametrize('name,config', CONFIG_PARAMS, ids=CONFIG_IDS)
def test_config_has_callable_scope_fn(name, config):
    assert callable(config.scope_fn), f'{name} scope_fn not callable'


@pytest.mark.parametrize('name,config', CONFIG_PARAMS, ids=CONFIG_IDS)
def test_config_has_callable_command_key_fn(name, config):
    assert callable(config.command_key_fn), f'{name} command_key_fn not callable'


@pytest.mark.parametrize('name,config', CONFIG_PARAMS, ids=CONFIG_IDS)
def test_config_has_callable_build_command_fn(name, config):
    assert callable(config.build_command_fn), f'{name} build_command_fn not callable'


_SIMPLE_ARGS = {
    'maven': 'verify',
    'gradle': 'build',
    'npm': 'run test',
    'python': 'verify',
}


@pytest.mark.parametrize('name,config', CONFIG_PARAMS, ids=CONFIG_IDS)
def test_scope_fn_returns_default_for_simple_command(name, config):
    simple_command = _SIMPLE_ARGS[name]
    result = config.scope_fn(simple_command)
    assert result == 'default', f'{name} scope_fn("{simple_command}") returned "{result}", expected "default"'


@pytest.mark.parametrize('name,config', CONFIG_PARAMS, ids=CONFIG_IDS)
def test_command_key_fn_handles_empty_args(name, config):
    result = config.command_key_fn('')
    assert result == 'default', f'{name} command_key_fn("") returned "{result}", expected "default"'


_BUILD_COMMAND_ARGS = {
    'maven': ('verify', '/tmp/log.log'),
    'gradle': ('build', '/tmp/log.log'),
    'npm': ('run test', '/tmp/log.log'),
    'python': ('verify', '/tmp/log.log'),
}


@pytest.mark.parametrize('name,config', CONFIG_PARAMS, ids=CONFIG_IDS)
def test_build_command_fn_returns_correct_types(name, config):
    args, log = _BUILD_COMMAND_ARGS[name]
    wrapper = f'./test-{name}'
    result = config.build_command_fn(wrapper, args, log)
    assert isinstance(result, tuple), f'{name} build_command_fn should return tuple'
    assert len(result) == 2, f'{name} build_command_fn should return 2-element tuple'
    cmd_parts, cmd_str = result
    assert isinstance(cmd_parts, list), f'{name} cmd_parts should be list'
    assert isinstance(cmd_str, str), f'{name} cmd_str should be string'
    assert all(isinstance(p, str) for p in cmd_parts), f'{name} cmd_parts should contain strings'

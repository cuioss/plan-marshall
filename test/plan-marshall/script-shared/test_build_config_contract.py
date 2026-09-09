#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Cross-build-system contract tests.

Verifies that all four build skill ExecuteConfig objects conform to the
shared contract documented in build-api-reference.md. Ensures the unified
API is actually consistent across Maven, Gradle, npm, and Python.
"""

import dataclasses
import typing
from collections.abc import Callable

import _build_execute_factory
import pytest

from conftest import MARKETPLACE_ROOT, load_script_module

_BUNDLES_DIR = MARKETPLACE_ROOT / 'plan-marshall' / 'skills'


def _load_module(name, filename, skill):
    """Load a build-skill script by (bundle, skill, file) identity."""
    return load_script_module('plan-marshall', skill, filename, name)


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


ExecuteConfig = _build_execute_factory.ExecuteConfig

_CONFIG_FIELDS = dataclasses.fields(ExecuteConfig)


def _required_callable_hooks() -> list[str]:
    """The ``ExecuteConfig`` fields that are BOTH required and callable-typed.

    Derived from the dataclass rather than restated, so a hook added to the
    contract is checked on every build config without an edit here. Two
    conditions, and both are load-bearing:

    * **Required** — the field declares no default and no default factory. A
      defaulted callable field (``wrapper_resolve_fn`` / ``extra_result_fn``) is
      legitimately ``None`` on a config that does not use it, so demanding it be
      callable would fail a conforming config.
    * **Callable-typed** — the resolved annotation is a ``Callable``. Selecting
      on an ``_fn`` name suffix instead would admit exactly those optional
      fields, which is the discrimination this predicate exists to make.
    """
    hints = typing.get_type_hints(ExecuteConfig)
    return [
        f.name
        for f in _CONFIG_FIELDS
        if f.default is dataclasses.MISSING
        and f.default_factory is dataclasses.MISSING
        and typing.get_origin(hints[f.name]) is Callable
    ]


#: The hook attributes every ExecuteConfig must supply as a callable. Each is a
#: seam the shared execute path invokes, so a non-callable is a crash at build
#: time rather than a contract note.
_CALLABLE_CONFIG_HOOKS = _required_callable_hooks()


def test_the_required_callable_hook_set_is_non_empty_and_excludes_the_optional_ones():
    """The derived hook set has members, and is narrower than the ``_fn`` fields.

    The sweep below is parametrized over the derived list, so an empty list
    would collect no rows and report green having checked nothing — the first
    assertion is what makes that state a failure. The second pins the
    discrimination: a predicate that degenerated into "every field named
    ``*_fn``" would pull in the optional, legitimately-``None`` hooks and the
    sweep would fail a conforming config.
    """
    assert _CALLABLE_CONFIG_HOOKS, 'no required callable hooks derived — the sweep collects no rows'
    fn_suffixed = {f.name for f in _CONFIG_FIELDS if f.name.endswith('_fn')}
    assert set(_CALLABLE_CONFIG_HOOKS) < fn_suffixed, (
        'the predicate admitted every *_fn field; the optional ones carry defaults '
        'and must stay out of the required set'
    )


@pytest.mark.parametrize('hook', _CALLABLE_CONFIG_HOOKS, ids=_CALLABLE_CONFIG_HOOKS)
@pytest.mark.parametrize('name,config', CONFIG_PARAMS, ids=CONFIG_IDS)
def test_config_hook_is_callable(name, config, hook):
    assert callable(getattr(config, hook)), f'{name} {hook} not callable'


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

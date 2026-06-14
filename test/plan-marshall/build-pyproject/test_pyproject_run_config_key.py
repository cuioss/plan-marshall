#!/usr/bin/env python3
"""Tests for the ``run-config-key`` CLI subcommand on the build-pyproject skill.

Verifies that ``pyproject_build.py run-config-key --command-args <args>``:

1. Returns TOON with ``build_tool``, ``key_suffix``, and ``command_key`` fields.
2. Produces the same canonical ``command_key`` for each tested args string
   that ``compute_command_key(_CONFIG, args)`` produces directly — i.e., the
   subcommand re-uses the single source of truth for the run-config key
   construction, so there can be no drift between the key the CLI advertises
   and the key that ``cmd_run`` would persist via ``timeout_set`` at execute
   time (round-trip property).
3. Returns JSON when ``--format json`` is passed.
"""

import importlib.util
from pathlib import Path

import pytest

from conftest import get_script_path, run_script

SCRIPT_PATH = get_script_path('plan-marshall', 'build-pyproject', 'pyproject_build.py')

# Load _build_execute_factory and _pyproject_execute by absolute path so the
# test can call ``compute_command_key(_CONFIG, args)`` directly — that pinpoints
# what the CLI ought to print for each canonical args string and demonstrates
# the round-trip property without spinning up a real build.
_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
)
_BUILD_FACTORY_PATH = (
    _SCRIPTS_DIR / 'script-shared' / 'scripts' / 'build' / '_build_execute_factory.py'
)
_PYPROJECT_EXECUTE_PATH = (
    _SCRIPTS_DIR / 'build-pyproject' / 'scripts' / '_pyproject_execute.py'
)


def _load(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_factory = _load('_build_execute_factory', _BUILD_FACTORY_PATH)
_pyproject_execute = _load('_pyproject_execute', _PYPROJECT_EXECUTE_PATH)

compute_command_key = _factory.compute_command_key
_CONFIG = _pyproject_execute._CONFIG


# Canonical args strings the build-pyproject skill is expected to handle.
# Covers full-scope ("verify"), module-scoped ("verify plan-marshall"),
# module-tests scope ("module-tests"), and coverage scope ("coverage <module>").
CANONICAL_ARGS = [
    'verify',
    'verify plan-marshall',
    'module-tests',
    'coverage pm-plugin-development',
    'quality-gate',
]


def test_run_config_key_returns_toon_with_required_fields():
    """``run-config-key`` returns TOON with build_tool, key_suffix, command_key."""
    result = run_script(
        SCRIPT_PATH,
        'run-config-key',
        '--command-args',
        'verify',
    )
    assert result.success, f'Script failed: {result.stderr}'
    data = result.toon()

    assert data['status'] == 'success'
    assert data['build_tool'] == 'python'
    assert data['key_suffix'] == 'verify'
    assert data['command_key'] == 'python:verify'


def test_run_config_key_json_format():
    """``--format json`` produces parseable JSON with the same fields."""
    result = run_script(
        SCRIPT_PATH,
        'run-config-key',
        '--command-args',
        'verify',
        '--format',
        'json',
    )
    assert result.success, f'Script failed: {result.stderr}'
    data = result.json()

    assert data['status'] == 'success'
    assert data['build_tool'] == 'python'
    assert data['key_suffix'] == 'verify'
    assert data['command_key'] == 'python:verify'


@pytest.mark.parametrize(
    'args, expected_suffix',
    [
        ('verify', 'verify'),
        ('verify plan-marshall', 'verify_plan_marshall'),
        ('module-tests', 'module_tests'),
        ('module-tests plan-marshall', 'module_tests_plan_marshall'),
        ('coverage pm-plugin-development', 'coverage_pm_plugin_development'),
        ('quality-gate', 'quality_gate'),
    ],
)
def test_run_config_key_canonical_args(args, expected_suffix):
    """Canonical args strings map to the expected ``key_suffix`` and full ``command_key``."""
    result = run_script(SCRIPT_PATH, 'run-config-key', '--command-args', args)
    assert result.success, f'Script failed: {result.stderr}'
    data = result.toon()

    assert data['build_tool'] == 'python'
    assert data['key_suffix'] == expected_suffix
    assert data['command_key'] == f'python:{expected_suffix}'


@pytest.mark.parametrize('args', CANONICAL_ARGS)
def test_run_config_key_round_trip_matches_compute_command_key(args):
    """The CLI-emitted ``command_key`` exactly matches ``compute_command_key(_CONFIG, args)``.

    Both code paths route through the same helper, so this assertion is a
    structural guard against drift between the key that ``run-config-key``
    advertises and the key that ``cmd_run`` would persist via ``timeout_set``
    at execute time.
    """
    expected_key = compute_command_key(_CONFIG, args)

    result = run_script(SCRIPT_PATH, 'run-config-key', '--command-args', args)
    assert result.success, f'Script failed: {result.stderr}'
    data = result.toon()

    assert data['command_key'] == expected_key, (
        f'CLI command_key {data["command_key"]!r} drifted from '
        f'compute_command_key {expected_key!r} for args={args!r}'
    )


def test_run_config_key_requires_command_args():
    """Omitting ``--command-args`` produces a non-zero exit (argparse rejection)."""
    result = run_script(SCRIPT_PATH, 'run-config-key')
    assert not result.success, 'Expected non-zero exit when --command-args is omitted'

#!/usr/bin/env python3
"""Tests for the ``run-config-key`` CLI subcommand on the build-npm skill.

Verifies that ``npm.py run-config-key --command-args <args>``:

1. Returns TOON with ``build_tool``, ``key_suffix``, and ``command_key`` fields.
2. Produces the same canonical ``command_key`` for each tested args string
   that ``compute_command_key(_CONFIG, args)`` produces directly — the
   round-trip property the run-config-key subcommand exists to expose.
3. Returns JSON when ``--format json`` is passed.
"""

import importlib.util
from pathlib import Path

import pytest

from conftest import get_script_path, run_script

SCRIPT_PATH = get_script_path('plan-marshall', 'build-npm', 'npm.py')

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
_NPM_EXECUTE_PATH = _SCRIPTS_DIR / 'build-npm' / 'scripts' / '_npm_execute.py'


def _load(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_factory = _load('_build_execute_factory', _BUILD_FACTORY_PATH)
_npm_execute = _load('_npm_execute', _NPM_EXECUTE_PATH)

compute_command_key = _factory.compute_command_key
_CONFIG = _npm_execute._CONFIG


# Canonical npm args: script invocations (``test``, ``run build``, ``ci``),
# multi-token scripts that should be underscore-joined by
# ``default_command_key_fn``.
CANONICAL_ARGS = [
    'test',
    'run build',
    'ci',
    'install',
    'run lint',
]


# =============================================================================
# Test: TOON output shape
# =============================================================================


def test_run_config_key_returns_toon_with_required_fields():
    """``run-config-key`` returns TOON with build_tool, key_suffix, command_key."""
    result = run_script(
        SCRIPT_PATH,
        'run-config-key',
        '--command-args',
        'test',
    )
    assert result.success, f'Script failed: {result.stderr}'
    data = result.toon()

    assert data['status'] == 'success'
    assert data['build_tool'] == 'npm'
    assert data['key_suffix'] == 'test'
    assert data['command_key'] == 'npm:test'


def test_run_config_key_json_format():
    """``--format json`` produces parseable JSON with the same fields."""
    result = run_script(
        SCRIPT_PATH,
        'run-config-key',
        '--command-args',
        'test',
        '--format',
        'json',
    )
    assert result.success, f'Script failed: {result.stderr}'
    data = result.json()

    assert data['status'] == 'success'
    assert data['build_tool'] == 'npm'
    assert data['key_suffix'] == 'test'
    assert data['command_key'] == 'npm:test'


# =============================================================================
# Test: Parametrised canonical args -> key suffix mapping
# =============================================================================


@pytest.mark.parametrize(
    'args, expected_suffix',
    [
        ('test', 'test'),
        ('ci', 'ci'),
        ('install', 'install'),
        # default_command_key_fn underscore-joins every token, dashes -> underscores
        ('run build', 'run_build'),
        ('run lint', 'run_lint'),
    ],
)
def test_run_config_key_canonical_args(args, expected_suffix):
    """Canonical npm args strings map to the expected ``key_suffix`` and full ``command_key``."""
    result = run_script(SCRIPT_PATH, 'run-config-key', '--command-args', args)
    assert result.success, f'Script failed: {result.stderr}'
    data = result.toon()

    assert data['build_tool'] == 'npm'
    assert data['key_suffix'] == expected_suffix
    assert data['command_key'] == f'npm:{expected_suffix}'


# =============================================================================
# Test: Round-trip property — CLI key matches compute_command_key directly
# =============================================================================


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


# =============================================================================
# Test: Error handling — missing required flag
# =============================================================================


def test_run_config_key_requires_command_args():
    """Omitting ``--command-args`` produces a non-zero exit (argparse rejection)."""
    result = run_script(SCRIPT_PATH, 'run-config-key')
    assert not result.success, 'Expected non-zero exit when --command-args is omitted'

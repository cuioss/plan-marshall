#!/usr/bin/env python3
"""Tests for the ``run-config-key`` CLI subcommand on the build-maven skill.

Verifies that ``maven.py run-config-key --command-args <args>``:

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

SCRIPT_PATH = get_script_path('plan-marshall', 'build-maven', 'maven.py')

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
_MAVEN_EXECUTE_PATH = _SCRIPTS_DIR / 'build-maven' / 'scripts' / '_maven_execute.py'


def _load(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_factory = _load('_build_execute_factory', _BUILD_FACTORY_PATH)
_maven_execute = _load('_maven_execute', _MAVEN_EXECUTE_PATH)

compute_command_key = _factory.compute_command_key
_CONFIG = _maven_execute._CONFIG


# Canonical Maven args: lifecycle phases and module-scoped invocations.
CANONICAL_ARGS = [
    'verify',
    'verify -pl core',
    'clean verify',
    'test',
    'compile',
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
        'verify',
    )
    assert result.success, f'Script failed: {result.stderr}'
    data = result.toon()

    assert data['status'] == 'success'
    assert data['build_tool'] == 'maven'
    assert data['key_suffix'] == 'verify'
    assert data['command_key'] == 'maven:verify'


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
    assert data['build_tool'] == 'maven'
    assert data['key_suffix'] == 'verify'
    assert data['command_key'] == 'maven:verify'


# =============================================================================
# Test: Parametrised canonical args -> key suffix mapping
# =============================================================================


@pytest.mark.parametrize(
    'args, expected_suffix',
    [
        ('verify', 'verify'),
        ('clean verify', 'clean_verify'),
        ('test', 'test'),
        ('compile', 'compile'),
        # default_command_key_fn underscore-joins tokens THEN replaces dashes
        # with underscores, so the dash in '-pl' becomes an extra underscore.
        ('verify -pl core', 'verify__pl_core'),
    ],
)
def test_run_config_key_canonical_args(args, expected_suffix):
    """Canonical Maven args strings map to the expected ``key_suffix`` and full ``command_key``."""
    result = run_script(SCRIPT_PATH, 'run-config-key', '--command-args', args)
    assert result.success, f'Script failed: {result.stderr}'
    data = result.toon()

    assert data['build_tool'] == 'maven'
    assert data['key_suffix'] == expected_suffix
    assert data['command_key'] == f'maven:{expected_suffix}'


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

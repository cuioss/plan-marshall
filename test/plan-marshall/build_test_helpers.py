#!/usr/bin/env python3
"""Shared test helpers for build-* skill tests.

Provides reusable test functions for coverage reports, execute configs,
and run subcommands that are duplicated across Maven, Gradle, npm, and Python.

Usage:
    from build_test_helpers import assert_coverage_missing_file, assert_coverage_high, ...
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from toon_parser import parse_toon  # type: ignore[import-not-found]

from conftest import run_script  # noqa: E402


# =============================================================================
# Coverage Report Test Helpers
# =============================================================================


def assert_coverage_missing_file(script_path, report_path='/nonexistent/report'):
    """Test coverage-report with non-existent report returns error.

    Shared across all build tools — the behavior is identical.
    """
    result = run_script(
        script_path, 'coverage-report',
        '--report-path', report_path,
    )
    assert not result.success

    data = parse_toon(result.stdout)
    assert data['status'] == 'error'
    assert data['error'] == 'report_not_found'
    return data


def assert_coverage_high(script_path, fixture_path, threshold=80):
    """Test coverage-report with report above threshold passes.

    Shared across all build tools — verifies status, passed, and line coverage.
    """
    result = run_script(
        script_path, 'coverage-report',
        '--report-path', str(fixture_path),
        '--threshold', str(threshold),
    )
    assert result.success, f'Script failed: {result.stderr}'

    data = parse_toon(result.stdout)
    assert data['status'] == 'success'
    assert data['passed'] is True
    assert float(data['overall']['line']) >= threshold
    return data


def assert_coverage_low(script_path, fixture_path, threshold=80):
    """Test coverage-report with report below threshold fails.

    Shared across all build tools — verifies status, passed=False, and message.
    """
    result = run_script(
        script_path, 'coverage-report',
        '--report-path', str(fixture_path),
        '--threshold', str(threshold),
    )
    assert not result.success

    data = parse_toon(result.stdout)
    assert data['status'] == 'success'
    assert data['passed'] is False
    assert 'below threshold' in data['message']
    return data


def assert_coverage_has_low_items(script_path, fixture_path, threshold=80):
    """Test that low-coverage items are identified in report.

    Shared across all build tools — verifies low_coverage list is populated.
    Returns the data dict for tool-specific assertions on item names.
    """
    result = run_script(
        script_path, 'coverage-report',
        '--report-path', str(fixture_path),
        '--threshold', str(threshold),
    )
    data = parse_toon(result.stdout)
    assert 'low_coverage' in data
    assert len(data['low_coverage']) > 0
    return data


def assert_coverage_custom_threshold(script_path, fixture_path, threshold):
    """Test coverage-report with custom threshold that passes.

    Shared across all build tools — verifies passed=True and threshold value.
    """
    result = run_script(
        script_path, 'coverage-report',
        '--report-path', str(fixture_path),
        '--threshold', str(threshold),
    )
    assert result.success, f'Script failed: {result.stderr}'

    data = parse_toon(result.stdout)
    assert data['passed'] is True
    assert str(data['threshold']) == str(threshold)
    return data


# =============================================================================
# Execute Config Test Helpers
# =============================================================================


def assert_execute_config(config, *, tool_name, unix_wrapper, system_fallback):
    """Verify ExecuteConfig has expected base fields.

    Shared across all build tools — checks tool_name, unix_wrapper, system_fallback.
    """
    assert config.tool_name == tool_name
    assert config.unix_wrapper == unix_wrapper
    assert config.system_fallback == system_fallback


def assert_command_key_fn(config, cases):
    """Test command_key_fn with multiple input/expected pairs.

    Args:
        config: ExecuteConfig instance.
        cases: List of (input, expected) tuples.
    """
    for args, expected in cases:
        result = config.command_key_fn(args)
        assert result == expected, f'command_key_fn({args!r}) = {result!r}, expected {expected!r}'


def assert_scope_fn(config, cases):
    """Test scope_fn with multiple input/expected pairs.

    Args:
        config: ExecuteConfig instance.
        cases: List of (input, expected) tuples.
    """
    for args, expected in cases:
        result = config.scope_fn(args)
        assert result == expected, f'scope_fn({args!r}) = {result!r}, expected {expected!r}'


# =============================================================================
# Run Subcommand Test Helpers
# =============================================================================


def assert_run_help(script_path):
    """Test that 'run --help' works without error.

    Shared across all build tools.
    """
    result = run_script(script_path, 'run', '--help')
    assert result.success, f'Help failed: {result.stderr}'
    assert 'command-args' in result.stdout.lower() or 'command_args' in result.stdout.lower()

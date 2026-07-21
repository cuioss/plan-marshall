#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared test helpers for build-* skill tests.

Provides reusable test functions for coverage reports, execute configs,
run subcommands, and the ``run-config-key`` contract that are duplicated across
Maven, Gradle, npm, and Python.

Usage:
    from build_test_helpers import assert_coverage_missing_file, assert_coverage_high, ...
"""

from toon_parser import parse_toon

from conftest import load_script_module, run_script

# =============================================================================
# Coverage Report Test Helpers
# =============================================================================


def assert_coverage_missing_file(script_path, report_path='/nonexistent/report'):
    """Test coverage-report with non-existent report returns error.

    Shared across all build tools — the behavior is identical.
    """
    result = run_script(
        script_path,
        'coverage-report',
        '--report-path',
        report_path,
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
        script_path,
        'coverage-report',
        '--report-path',
        str(fixture_path),
        '--threshold',
        str(threshold),
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
        script_path,
        'coverage-report',
        '--report-path',
        str(fixture_path),
        '--threshold',
        str(threshold),
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
        script_path,
        'coverage-report',
        '--report-path',
        str(fixture_path),
        '--threshold',
        str(threshold),
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
        script_path,
        'coverage-report',
        '--report-path',
        str(fixture_path),
        '--threshold',
        str(threshold),
    )
    assert result.success, f'Script failed: {result.stderr}'

    data = parse_toon(result.stdout)
    assert data['passed'] is True
    assert str(data['threshold']) == str(threshold)
    return data


#: The backend-invariant ``coverage-report`` cases, in execution order. Each
#: name is dispatched by :func:`run_coverage_report_case`; a backend
#: parametrizes over the subset its report format actually supports.
COVERAGE_REPORT_CASES = ('missing_file', 'high', 'low', 'low_items', 'custom_threshold')


def run_coverage_report_case(
    case,
    script_path,
    fixtures_dir,
    *,
    high_report='high-coverage.xml',
    low_report='low-coverage.xml',
    custom_threshold_report='high-coverage.xml',
    custom_threshold=60,
):
    """Dispatch one backend-invariant ``coverage-report`` case.

    Replaces the one-line wrapper function each backend used to re-declare per
    case. Every knob that genuinely differs per backend is a parameter: the
    fixtures directory, the report filenames (XML for the JaCoCo/Cobertura
    backends, JSON for npm), and the custom-threshold pair. Assertions that are
    NOT interchangeable — the per-backend low-coverage item-name checks — stay
    in the backend's own test module and call :func:`assert_coverage_has_low_items`
    directly.

    Args:
        case: One of :data:`COVERAGE_REPORT_CASES`.
        script_path: Path to the backend's entry script.
        fixtures_dir: The backend's own coverage fixtures directory.
        high_report: Filename of the above-threshold report fixture.
        low_report: Filename of the below-threshold report fixture.
        custom_threshold_report: Filename of the report the custom-threshold
            case runs against.
        custom_threshold: Threshold value that the custom-threshold case passes at.

    Returns:
        The parsed TOON data dict for the dispatched case.

    Raises:
        AssertionError: when the dispatched case's contract does not hold.
        ValueError: when ``case`` is not a known case name.
    """
    if case == 'missing_file':
        return assert_coverage_missing_file(script_path)
    if case == 'high':
        return assert_coverage_high(script_path, fixtures_dir / high_report)
    if case == 'low':
        return assert_coverage_low(script_path, fixtures_dir / low_report)
    if case == 'low_items':
        return assert_coverage_has_low_items(script_path, fixtures_dir / low_report)
    if case == 'custom_threshold':
        return assert_coverage_custom_threshold(
            script_path, fixtures_dir / custom_threshold_report, threshold=custom_threshold
        )
    raise ValueError(f'unknown coverage-report case: {case!r}')


# =============================================================================
# run-config-key Contract Helper
# =============================================================================


def assert_run_config_key_contract(script_path, build_tool, canonical_args, *, config, suffix_cases):
    """Assert the whole ``run-config-key`` contract for one build backend.

    Consolidates the five assertions every backend previously re-declared:

    1. **TOON shape** — ``status`` / ``build_tool`` / ``key_suffix`` /
       ``command_key`` are all present and correct.
    2. **JSON format** — ``--format json`` emits the same four fields as
       parseable JSON.
    3. **Canonical args mapping** — each ``(args, expected_suffix)`` case maps to
       the expected ``key_suffix`` and the full ``{build_tool}:{suffix}`` key.
    4. **Round-trip drift guard** — the CLI-emitted ``command_key`` matches
       ``compute_command_key(config, args)`` for every canonical args string.
       This is the structural guard against drift between the key
       ``run-config-key`` advertises and the key ``cmd_run`` persists via
       ``timeout_set`` at execute time; it runs once per backend.
    5. **Required-flag error path** — omitting ``--command-args`` is an
       argparse rejection (non-zero exit).

    Args:
        script_path: Path to the backend's entry script.
        build_tool: The backend's ``build_tool`` value (e.g. ``'gradle'``).
        canonical_args: Args strings driving the round-trip drift guard.
        config: The backend's own ``_CONFIG`` ExecuteConfig — the drift guard's
            left-hand side. Kept per-backend because the key function is
            backend-specific (Gradle strips leading colons and uses only the
            first task; the others use ``default_command_key_fn``).
        suffix_cases: ``(args, expected_suffix)`` pairs. The first pair doubles
            as the representative case for the TOON and JSON shape assertions.

    Raises:
        AssertionError: when any part of the contract does not hold.
    """
    compute_command_key = load_script_module(
        'plan-marshall', 'script-shared', 'build/_build_execute_factory.py'
    ).compute_command_key

    representative_args, representative_suffix = suffix_cases[0]

    # 1. TOON shape.
    result = run_script(script_path, 'run-config-key', '--command-args', representative_args)
    assert result.success, f'Script failed: {result.stderr}'
    data = result.toon()
    assert data['status'] == 'success'
    assert data['build_tool'] == build_tool
    assert data['key_suffix'] == representative_suffix
    assert data['command_key'] == f'{build_tool}:{representative_suffix}'

    # 2. JSON format emits the same four fields.
    result = run_script(
        script_path, 'run-config-key', '--command-args', representative_args, '--format', 'json'
    )
    assert result.success, f'Script failed: {result.stderr}'
    data = result.json()
    assert data['status'] == 'success'
    assert data['build_tool'] == build_tool
    assert data['key_suffix'] == representative_suffix
    assert data['command_key'] == f'{build_tool}:{representative_suffix}'

    # 3. Canonical args -> key_suffix / command_key mapping.
    for args, expected_suffix in suffix_cases:
        result = run_script(script_path, 'run-config-key', '--command-args', args)
        assert result.success, f'Script failed for args={args!r}: {result.stderr}'
        data = result.toon()
        assert data['build_tool'] == build_tool
        assert data['key_suffix'] == expected_suffix, (
            f'key_suffix {data["key_suffix"]!r} != expected {expected_suffix!r} for args={args!r}'
        )
        assert data['command_key'] == f'{build_tool}:{expected_suffix}'

    # 4. Round-trip drift guard against compute_command_key.
    for args in canonical_args:
        expected_key = compute_command_key(config, args)
        result = run_script(script_path, 'run-config-key', '--command-args', args)
        assert result.success, f'Script failed for args={args!r}: {result.stderr}'
        data = result.toon()
        assert data['command_key'] == expected_key, (
            f'CLI command_key {data["command_key"]!r} drifted from '
            f'compute_command_key {expected_key!r} for args={args!r}'
        )

    # 5. Omitting --command-args is an argparse rejection.
    result = run_script(script_path, 'run-config-key')
    assert not result.success, 'Expected non-zero exit when --command-args is omitted'


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

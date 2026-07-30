#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for js-coverage.py - JavaScript test coverage analysis tool.

Tests the analyze subcommand for JavaScript coverage reports.
"""

from pathlib import Path

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
import js_coverage
from _resolve_project_dir_fixtures import (
    CANONICAL_PROJECT_DIR,
    assert_sentinel_accepted,
    assert_worktree_face_routes_through_resolver,
)

from conftest import get_script_path, run_script

SCRIPT_PATH = get_script_path('plan-marshall', 'build-npm', 'js_coverage.py')
FIXTURES_DIR = Path(__file__).parent / 'coverage'


def test_script_exists():
    """Test that the script exists."""
    assert SCRIPT_PATH.exists(), f'Script not found: {SCRIPT_PATH}'


def test_main_help():
    """Test main --help displays all subcommands."""
    result = run_script(SCRIPT_PATH, '--help')
    combined = result.stdout + result.stderr
    assert 'analyze' in combined, 'analyze subcommand in help'


def test_analyze_help():
    """Test analyze --help displays usage."""
    result = run_script(SCRIPT_PATH, 'analyze', '--help')
    combined = result.stdout + result.stderr
    assert 'usage' in combined.lower(), 'Analyze help not shown'


def test_analyze_json_coverage():
    """Test analyzing JSON coverage report."""
    result = run_script(SCRIPT_PATH, 'analyze', '--report', str(FIXTURES_DIR / 'coverage-summary.json'))
    data = result.toon()
    assert data['status'] == 'success', 'Successfully analyzed JSON coverage'


def test_analyze_overall_coverage_present():
    """Test overall coverage metrics are present."""
    result = run_script(SCRIPT_PATH, 'analyze', '--report', str(FIXTURES_DIR / 'coverage-summary.json'))
    data = result.toon()
    assert 'overall_coverage' in data.get('data', {}), 'Overall coverage present'


def test_analyze_line_coverage_numeric():
    """Test line coverage is numeric."""
    result = run_script(SCRIPT_PATH, 'analyze', '--report', str(FIXTURES_DIR / 'coverage-summary.json'))
    data = result.toon()
    line_coverage = data.get('data', {}).get('overall_coverage', {}).get('line_coverage')
    assert isinstance(line_coverage, (int, float)), 'Line coverage is numeric'


def test_analyze_by_file_present():
    """Test by_file array is present."""
    result = run_script(SCRIPT_PATH, 'analyze', '--report', str(FIXTURES_DIR / 'coverage-summary.json'))
    data = result.toon()
    assert 'by_file' in data.get('data', {}), 'By-file data present'


def test_analyze_high_coverage():
    """Test analyzing high coverage report."""
    result = run_script(SCRIPT_PATH, 'analyze', '--report', str(FIXTURES_DIR / 'high-coverage.json'))
    data = result.toon()
    assert data['status'] == 'success', 'Analyzed high coverage report'


def test_analyze_low_coverage():
    """Test analyzing low coverage report identifies issues."""
    result = run_script(
        SCRIPT_PATH, 'analyze', '--report', str(FIXTURES_DIR / 'low-coverage.json'), '--threshold', '80'
    )
    data = result.toon()
    low_coverage = data.get('data', {}).get('low_coverage_files', [])
    assert isinstance(low_coverage, list), 'Low coverage files array present'


def test_analyze_lcov_format():
    """Test analyzing LCOV format report."""
    result = run_script(SCRIPT_PATH, 'analyze', '--report', str(FIXTURES_DIR / 'lcov.info'), '--format', 'lcov')
    data = result.toon()
    assert data['status'] == 'success', 'Successfully analyzed LCOV format'


def test_analyze_missing_report_error():
    """Test error handling for missing report file."""
    result = run_script(SCRIPT_PATH, 'analyze', '--report', 'nonexistent.json')
    data = result.toon()
    assert data['status'] == 'error', 'Returns error for missing file'


def test_analyze_threshold_parameter():
    """Test threshold parameter is accepted."""
    result = run_script(
        SCRIPT_PATH, 'analyze', '--report', str(FIXTURES_DIR / 'coverage-summary.json'), '--threshold', '70'
    )
    data = result.toon()
    assert data.get('metrics', {}).get('threshold') == 70.0, 'Threshold parameter used'


def test_analyze_empty_coverage():
    """Test handling empty coverage report."""
    result = run_script(SCRIPT_PATH, 'analyze', '--report', str(FIXTURES_DIR / 'empty-coverage.json'))
    data = result.toon()
    assert data['status'] in ['success', 'error'], 'Handled empty coverage'


# =============================================================================
# Resolver-migration contract
# =============================================================================
#
# js_coverage binds its working tree through ``resolve_project_dir``, which
# delegates the worktree face to ``file_ops.resolve_plan_context``. The two
# assertions below are bound through the SCRIPT's own imported symbol, so they
# state that THIS script routes through the resolver — not merely that the
# shared helper does.


def _resolve(plan_id):
    """Resolve exactly as ``js_coverage.main`` does, via the script's symbol."""
    return js_coverage.resolve_project_dir(plan_id, '.', default='.')


def test_analyze_declares_both_routing_flags():
    """The two-state ``--plan-id`` / ``--project-dir`` surface is wired.

    Asserted against the script's REAL argparse surface (its own ``--help``
    output) rather than a re-built stand-in parser, so a flag that is dropped
    from the production parser cannot stay green here.
    """
    combined = _analyze_help()
    assert '--plan-id' in combined, 'analyze does not declare --plan-id'
    assert '--project-dir' in combined, 'analyze does not declare --project-dir'


def _analyze_help() -> str:
    result = run_script(SCRIPT_PATH, 'analyze', '--help')
    return f'{result.stdout}{result.stderr}'


def test_worktree_binding_routes_through_the_resolver():
    """The worktree face reaches the single ``get-worktree-path`` seam."""
    assert_worktree_face_routes_through_resolver(_resolve)


def test_no_plan_sentinel_is_accepted():
    """``--plan-id NO_PLAN`` resolves to the main checkout without shelling out."""
    assert_sentinel_accepted(_resolve)


def test_both_routing_flags_are_mutually_exclusive():
    """Supplying both routing sources is refused, not silently ranked."""
    result = run_script(
        SCRIPT_PATH,
        'analyze',
        '--report',
        str(FIXTURES_DIR / 'coverage-summary.json'),
        '--plan-id',
        'some-plan',
        '--project-dir',
        CANONICAL_PROJECT_DIR,
    )
    data = result.toon_or_error()
    assert data.get('error') == 'mutually_exclusive_args', (
        f'Expected mutually_exclusive_args, got: {data!r}'
    )

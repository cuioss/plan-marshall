#!/usr/bin/env python3
"""Tests for js-coverage.py - JavaScript test coverage analysis tool.

Tests the analyze subcommand for JavaScript coverage reports.
"""

from pathlib import Path

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import get_script_path, run_script

# Script under test
SCRIPT_PATH = get_script_path('pm-dev-frontend', 'cui-javascript-unit-testing', 'js-coverage.py')
FIXTURES_DIR = Path(__file__).parent / 'coverage'


# =============================================================================
# Main help tests
# =============================================================================

def test_script_exists():
    """Test that the script exists."""
    assert SCRIPT_PATH.exists(), f"Script not found: {SCRIPT_PATH}"


def test_main_help():
    """Test main --help displays all subcommands."""
    result = run_script(SCRIPT_PATH, '--help')
    combined = result.stdout + result.stderr
    assert 'analyze' in combined, "analyze subcommand in help"


def test_analyze_help():
    """Test analyze --help displays usage."""
    result = run_script(SCRIPT_PATH, 'analyze', '--help')
    combined = result.stdout + result.stderr
    assert 'usage' in combined.lower(), "Analyze help not shown"


# =============================================================================
# Analyze subcommand tests
# =============================================================================

def test_analyze_json_coverage():
    """Test analyzing JSON coverage report."""
    result = run_script(SCRIPT_PATH, 'analyze', '--report', str(FIXTURES_DIR / 'coverage-summary.json'))
    data = result.json()
    assert data['status'] == 'success', "Successfully analyzed JSON coverage"


def test_analyze_overall_coverage_present():
    """Test overall coverage metrics are present."""
    result = run_script(SCRIPT_PATH, 'analyze', '--report', str(FIXTURES_DIR / 'coverage-summary.json'))
    data = result.json()
    assert 'overall_coverage' in data.get('data', {}), "Overall coverage present"


def test_analyze_line_coverage_numeric():
    """Test line coverage is numeric."""
    result = run_script(SCRIPT_PATH, 'analyze', '--report', str(FIXTURES_DIR / 'coverage-summary.json'))
    data = result.json()
    line_coverage = data.get('data', {}).get('overall_coverage', {}).get('line_coverage')
    assert isinstance(line_coverage, (int, float)), "Line coverage is numeric"


def test_analyze_by_file_present():
    """Test by_file array is present."""
    result = run_script(SCRIPT_PATH, 'analyze', '--report', str(FIXTURES_DIR / 'coverage-summary.json'))
    data = result.json()
    assert 'by_file' in data.get('data', {}), "By-file data present"


def test_analyze_high_coverage():
    """Test analyzing high coverage report."""
    result = run_script(SCRIPT_PATH, 'analyze', '--report', str(FIXTURES_DIR / 'high-coverage.json'))
    data = result.json()
    assert data['status'] == 'success', "Analyzed high coverage report"


def test_analyze_low_coverage():
    """Test analyzing low coverage report identifies issues."""
    result = run_script(SCRIPT_PATH, 'analyze', '--report', str(FIXTURES_DIR / 'low-coverage.json'), '--threshold', '80')
    data = result.json()
    low_coverage = data.get('data', {}).get('low_coverage_files', [])
    assert isinstance(low_coverage, list), "Low coverage files array present"


def test_analyze_lcov_format():
    """Test analyzing LCOV format report."""
    result = run_script(SCRIPT_PATH, 'analyze', '--report', str(FIXTURES_DIR / 'lcov.info'), '--format', 'lcov')
    data = result.json()
    assert data['status'] == 'success', "Successfully analyzed LCOV format"


def test_analyze_missing_report_error():
    """Test error handling for missing report file."""
    result = run_script(SCRIPT_PATH, 'analyze', '--report', 'nonexistent.json')
    data = result.json()
    assert data['status'] == 'error', "Returns error for missing file"


def test_analyze_threshold_parameter():
    """Test threshold parameter is accepted."""
    result = run_script(SCRIPT_PATH, 'analyze', '--report', str(FIXTURES_DIR / 'coverage-summary.json'), '--threshold', '70')
    data = result.json()
    assert data.get('metrics', {}).get('threshold') == 70.0, "Threshold parameter used"


def test_analyze_empty_coverage():
    """Test handling empty coverage report."""
    result = run_script(SCRIPT_PATH, 'analyze', '--report', str(FIXTURES_DIR / 'empty-coverage.json'))
    data = result.json()
    # Should handle empty gracefully
    assert data['status'] in ['success', 'error'], "Handled empty coverage"


# =============================================================================
# Main
# =============================================================================

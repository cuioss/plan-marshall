#!/usr/bin/env python3
"""Tests for jsdoc.py - JSDoc documentation analysis tool.

Tests the analyze subcommand for JavaScript JSDoc compliance.
"""

import sys
from pathlib import Path

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import run_script, TestRunner, get_script_path

# Script under test
SCRIPT_PATH = get_script_path('pm-dev-frontend', 'cui-jsdoc', 'jsdoc.py')
FIXTURES_DIR = Path(__file__).parent / 'jsdoc'


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

def test_analyze_valid_jsdoc():
    """Test analyzing file with valid JSDoc."""
    result = run_script(SCRIPT_PATH, 'analyze', '--file', str(FIXTURES_DIR / 'valid-jsdoc.js'))
    data = result.json()
    assert data['status'] in ['clean', 'violations_found'], "Analyzed valid JSDoc file"


def test_analyze_missing_jsdoc():
    """Test analyzing file with missing JSDoc."""
    result = run_script(SCRIPT_PATH, 'analyze', '--file', str(FIXTURES_DIR / 'missing-jsdoc.js'))
    data = result.json()
    violations = data.get('data', {}).get('violations', [])
    assert len(violations) > 0, "Detected missing JSDoc"


def test_analyze_partial_jsdoc():
    """Test analyzing file with partial JSDoc."""
    result = run_script(SCRIPT_PATH, 'analyze', '--file', str(FIXTURES_DIR / 'partial-jsdoc.js'))
    data = result.json()
    assert data['status'] in ['clean', 'violations_found'], "Analyzed partial JSDoc file"


def test_analyze_web_component():
    """Test analyzing web component file."""
    result = run_script(SCRIPT_PATH, 'analyze', '--file', str(FIXTURES_DIR / 'web-component.js'))
    data = result.json()
    assert data['status'] in ['clean', 'violations_found'], "Analyzed web component"


def test_analyze_directory():
    """Test analyzing directory of files."""
    result = run_script(SCRIPT_PATH, 'analyze', '--directory', str(FIXTURES_DIR))
    data = result.json()
    metrics = data.get('metrics', {})
    assert metrics.get('total_files', 0) > 0, "Analyzed multiple files"


def test_analyze_scope_missing():
    """Test missing scope filter."""
    result = run_script(SCRIPT_PATH, 'analyze', '--file', str(FIXTURES_DIR / 'missing-jsdoc.js'), '--scope', 'missing')
    data = result.json()
    assert data['status'] in ['clean', 'violations_found'], "Missing scope filter works"


def test_analyze_scope_syntax():
    """Test syntax scope filter."""
    result = run_script(SCRIPT_PATH, 'analyze', '--file', str(FIXTURES_DIR / 'partial-jsdoc.js'), '--scope', 'syntax')
    data = result.json()
    assert data['status'] in ['clean', 'violations_found'], "Syntax scope filter works"


def test_analyze_missing_file_error():
    """Test error handling for missing file."""
    result = run_script(SCRIPT_PATH, 'analyze', '--file', 'nonexistent.js')
    data = result.json()
    assert data['status'] == 'error', "Returns error for missing file"


def test_analyze_missing_directory_error():
    """Test error handling for missing directory."""
    result = run_script(SCRIPT_PATH, 'analyze', '--directory', '/nonexistent/path')
    data = result.json()
    assert data['status'] == 'error', "Returns error for missing directory"


def test_analyze_metrics_present():
    """Test metrics are present in output."""
    result = run_script(SCRIPT_PATH, 'analyze', '--file', str(FIXTURES_DIR / 'missing-jsdoc.js'))
    data = result.json()
    metrics = data.get('metrics', {})
    assert 'total_violations' in metrics, "Metrics include total_violations"
    assert 'critical' in metrics, "Metrics include critical count"


def test_analyze_violation_has_file_field():
    """Test violations have file field."""
    result = run_script(SCRIPT_PATH, 'analyze', '--file', str(FIXTURES_DIR / 'missing-jsdoc.js'))
    data = result.json()
    violations = data.get('data', {}).get('violations', [])
    if violations:
        assert 'file' in violations[0], "Violation has file field"


def test_analyze_violation_has_line_field():
    """Test violations have line field."""
    result = run_script(SCRIPT_PATH, 'analyze', '--file', str(FIXTURES_DIR / 'missing-jsdoc.js'))
    data = result.json()
    violations = data.get('data', {}).get('violations', [])
    if violations:
        assert 'line' in violations[0], "Violation has line field"


# =============================================================================
# Main
# =============================================================================

if __name__ == '__main__':
    runner = TestRunner()
    runner.add_tests([
        test_script_exists,
        test_main_help,
        test_analyze_help,
        test_analyze_valid_jsdoc,
        test_analyze_missing_jsdoc,
        test_analyze_partial_jsdoc,
        test_analyze_web_component,
        test_analyze_directory,
        test_analyze_scope_missing,
        test_analyze_scope_syntax,
        test_analyze_missing_file_error,
        test_analyze_missing_directory_error,
        test_analyze_metrics_present,
        test_analyze_violation_has_file_field,
        test_analyze_violation_has_line_field,
    ])
    sys.exit(runner.run())

#!/usr/bin/env python3
"""Tests for npm-output.py - npm build output analysis tool.

Tests the parse subcommand for analyzing npm/npx build logs.
"""

import sys
from pathlib import Path

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import run_script, get_script_path

# Script under test
SCRIPT_PATH = get_script_path('pm-dev-frontend', 'cui-javascript-project', 'npm-output.py')
FIXTURES_DIR = Path(__file__).parent / 'build'


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
    assert 'parse' in combined, "parse subcommand in help"


def test_parse_help():
    """Test parse --help displays usage."""
    result = run_script(SCRIPT_PATH, 'parse', '--help')
    combined = result.stdout + result.stderr
    assert 'usage' in combined.lower(), "Parse help not shown"


# =============================================================================
# Parse subcommand tests
# =============================================================================

def test_parse_successful_build():
    """Test parsing successful build log."""
    result = run_script(SCRIPT_PATH, 'parse', '--log', str(FIXTURES_DIR / 'successful-build.log'))
    data = result.json()
    assert data['status'] == 'success', "Successfully parsed build log"


def test_parse_failed_build():
    """Test parsing failed build log."""
    result = run_script(SCRIPT_PATH, 'parse', '--log', str(FIXTURES_DIR / 'failed-build.log'))
    data = result.json()
    assert data['status'] == 'failure', "Detected build failure"


def test_parse_test_failure_log():
    """Test parsing test failure log."""
    result = run_script(SCRIPT_PATH, 'parse', '--log', str(FIXTURES_DIR / 'test-failure.log'))
    data = result.json()
    assert 'metrics' in data, "Metrics present in output"


def test_parse_structured_mode():
    """Test structured output mode."""
    result = run_script(SCRIPT_PATH, 'parse', '--log', str(FIXTURES_DIR / 'failed-build.log'), '--mode', 'structured')
    data = result.json()
    assert 'issues' in data.get('data', {}), "Structured mode has issues array"


def test_parse_errors_mode():
    """Test errors-only output mode."""
    result = run_script(SCRIPT_PATH, 'parse', '--log', str(FIXTURES_DIR / 'failed-build.log'), '--mode', 'errors')
    data = result.json()
    assert 'errors' in data.get('data', {}), "Errors mode has errors array"


def test_parse_missing_log_error():
    """Test error handling for missing log file."""
    result = run_script(SCRIPT_PATH, 'parse', '--log', 'nonexistent.log')
    data = result.json()
    assert data['status'] == 'error', "Returns error for missing file"


def test_parse_output_file_field():
    """Test output_file field is present."""
    result = run_script(SCRIPT_PATH, 'parse', '--log', str(FIXTURES_DIR / 'successful-build.log'))
    data = result.json()
    assert 'output_file' in data.get('data', {}), "output_file field present"


def test_parse_workspace_build():
    """Test parsing workspace/monorepo build log."""
    result = run_script(SCRIPT_PATH, 'parse', '--log', str(FIXTURES_DIR / 'workspace-build.log'))
    data = result.json()
    assert data['status'] in ['success', 'failure'], "Parsed workspace build"


# =============================================================================
# Main
# =============================================================================

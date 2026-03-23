#!/usr/bin/env python3
"""Tests for ci.py provider-agnostic router script.

Tests that the router correctly parses arguments and delegates.
Note: Without marshal.json, the router exits with an error (expected).
"""

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import get_script_path, run_script

# Get script path
SCRIPT_PATH = get_script_path('plan-marshall', 'tools-integration-ci', 'ci.py')


def test_help_flag():
    """Test --help flag works."""
    result = run_script(SCRIPT_PATH, '--help')
    assert result.success, f'--help failed: {result.stderr}'
    assert 'provider-agnostic' in result.stdout.lower() or 'router' in result.stdout.lower() or 'ci' in result.stdout.lower()


def test_no_args_fails_without_config():
    """Test that running without marshal.json config fails gracefully."""
    result = run_script(SCRIPT_PATH)
    # Without marshal.json, should fail with config error or argparse error
    assert not result.success


def test_pr_subcommand_without_config():
    """Test that pr subcommand without config fails gracefully."""
    result = run_script(SCRIPT_PATH, 'pr', 'view')
    # Without marshal.json, should fail with config error
    assert not result.success
    assert 'error' in result.stderr.lower() or 'provider' in result.stderr.lower()

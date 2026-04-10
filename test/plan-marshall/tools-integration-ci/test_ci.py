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
    assert (
        'provider-agnostic' in result.stdout.lower()
        or 'router' in result.stdout.lower()
        or 'ci' in result.stdout.lower()
    )


def test_no_args_outputs_error_without_config():
    """Test that running without CI config returns TOON error."""
    result = run_script(SCRIPT_PATH)
    # Router returns exit 0 with TOON error (three-tier model)
    assert result.success
    assert 'status: error' in result.stdout
    assert 'CI provider not configured' in result.stdout


def test_pr_subcommand_without_config():
    """Test that pr subcommand without CI config returns TOON error."""
    result = run_script(SCRIPT_PATH, 'pr', '--help')
    # Without CI provider configured, router cannot delegate
    assert result.success
    assert 'status: error' in result.stdout

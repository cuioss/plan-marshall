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


def test_no_args_returns_success():
    """Test that running without args returns exit 0 (three-tier error model)."""
    result = run_script(SCRIPT_PATH)
    # Router always returns exit 0 — TOON output indicates success or error
    assert result.success
    assert 'status:' in result.stdout


def test_pr_subcommand_returns_success():
    """Test that pr subcommand returns exit 0."""
    result = run_script(SCRIPT_PATH, 'pr', '--help')
    # Either delegates to provider (shows help) or returns TOON error
    assert result.success

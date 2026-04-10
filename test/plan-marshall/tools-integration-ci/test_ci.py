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


def test_no_args_exits_gracefully():
    """Test that running without args exits without crashing."""
    result = run_script(SCRIPT_PATH)
    # Two valid outcomes depending on marshal.json state:
    # - No CI provider: exit 0 with TOON error
    # - CI provider configured: exit 2 from argparse (no subcommand)
    assert result.returncode in (0, 2)


def test_pr_subcommand_returns_success():
    """Test that pr subcommand returns exit 0."""
    result = run_script(SCRIPT_PATH, 'pr', '--help')
    # Either delegates to provider (shows help) or returns TOON error
    assert result.success

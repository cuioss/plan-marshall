#!/usr/bin/env python3
"""Tests for gitlab.py script.

Tests command structure and argument parsing.
Note: Actual glab CLI operations require authentication and network.
These tests focus on the script interface, not live operations.
"""

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import get_script_path, run_script

# Get script path
SCRIPT_PATH = get_script_path('plan-marshall', 'ci-operations', 'gitlab.py')


def test_help_flag():
    """Test --help flag works."""
    result = run_script(SCRIPT_PATH, '--help')
    assert result.success, f'--help failed: {result.stderr}'
    assert 'pr' in result.stdout
    assert 'ci' in result.stdout
    assert 'issue' in result.stdout


def test_pr_subcommand_help():
    """Test pr subcommand help."""
    result = run_script(SCRIPT_PATH, 'pr', '--help')
    assert result.success, f'pr --help failed: {result.stderr}'
    assert 'create' in result.stdout
    assert 'reviews' in result.stdout


def test_ci_subcommand_help():
    """Test ci subcommand help."""
    result = run_script(SCRIPT_PATH, 'ci', '--help')
    assert result.success, f'ci --help failed: {result.stderr}'
    assert 'status' in result.stdout
    assert 'wait' in result.stdout


def test_issue_subcommand_help():
    """Test issue subcommand help."""
    result = run_script(SCRIPT_PATH, 'issue', '--help')
    assert result.success, f'issue --help failed: {result.stderr}'
    assert 'create' in result.stdout


def test_pr_create_help():
    """Test pr create help shows required arguments."""
    result = run_script(SCRIPT_PATH, 'pr', 'create', '--help')
    assert result.success, f'pr create --help failed: {result.stderr}'
    assert '--title' in result.stdout
    assert '--body' in result.stdout


def test_pr_create_missing_required():
    """Test pr create fails without required arguments."""
    result = run_script(SCRIPT_PATH, 'pr', 'create')
    assert not result.success, 'Expected failure without --title'
    assert 'title' in result.stderr.lower() or 'required' in result.stderr.lower()


def test_pr_reviews_missing_required():
    """Test pr reviews fails without pr-number."""
    result = run_script(SCRIPT_PATH, 'pr', 'reviews')
    assert not result.success, 'Expected failure without --pr-number'


def test_ci_status_missing_required():
    """Test ci status fails without pr-number."""
    result = run_script(SCRIPT_PATH, 'ci', 'status')
    assert not result.success, 'Expected failure without --pr-number'


def test_ci_wait_missing_required():
    """Test ci wait fails without pr-number."""
    result = run_script(SCRIPT_PATH, 'ci', 'wait')
    assert not result.success, 'Expected failure without --pr-number'


def test_issue_create_missing_required():
    """Test issue create fails without required arguments."""
    result = run_script(SCRIPT_PATH, 'issue', 'create')
    assert not result.success, 'Expected failure without --title'


def test_no_subcommand():
    """Test that script requires a subcommand."""
    result = run_script(SCRIPT_PATH)
    assert not result.success, 'Expected failure without subcommand'

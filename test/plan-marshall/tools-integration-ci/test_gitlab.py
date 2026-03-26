#!/usr/bin/env python3
"""Tests for gitlab.py script.

Tests command structure and argument parsing.
Note: Actual glab CLI operations require authentication and network.
These tests focus on the script interface, not live operations.
"""

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import get_script_path, run_script

# Get script path
SCRIPT_PATH = get_script_path('plan-marshall', 'tools-integration-ci', 'gitlab.py')


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
    assert 'view' in result.stdout
    assert 'reply' in result.stdout
    assert 'resolve-thread' in result.stdout
    assert 'thread-reply' in result.stdout
    assert 'merge' in result.stdout
    assert 'auto-merge' in result.stdout
    assert 'close' in result.stdout
    assert 'ready' in result.stdout
    assert 'edit' in result.stdout
    assert 'reviews' in result.stdout
    assert 'list' in result.stdout


def test_ci_subcommand_help():
    """Test ci subcommand help."""
    result = run_script(SCRIPT_PATH, 'ci', '--help')
    assert result.success, f'ci --help failed: {result.stderr}'
    assert 'status' in result.stdout
    assert 'wait' in result.stdout
    assert 'rerun' in result.stdout
    assert 'logs' in result.stdout


def test_issue_subcommand_help():
    """Test issue subcommand help."""
    result = run_script(SCRIPT_PATH, 'issue', '--help')
    assert result.success, f'issue --help failed: {result.stderr}'
    assert 'create' in result.stdout
    assert 'view' in result.stdout
    assert 'close' in result.stdout


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


def test_pr_view_help():
    """Test pr view help works."""
    result = run_script(SCRIPT_PATH, 'pr', 'view', '--help')
    assert result.success, f'pr view --help failed: {result.stderr}'


def test_pr_reply_help():
    """Test pr reply help shows required arguments."""
    result = run_script(SCRIPT_PATH, 'pr', 'reply', '--help')
    assert result.success, f'pr reply --help failed: {result.stderr}'
    assert '--pr-number' in result.stdout
    assert '--body' in result.stdout


def test_pr_reply_missing_required():
    """Test pr reply fails without required arguments."""
    result = run_script(SCRIPT_PATH, 'pr', 'reply')
    assert not result.success, 'Expected failure without --pr-number'


def test_pr_resolve_thread_help():
    """Test pr resolve-thread help shows required arguments."""
    result = run_script(SCRIPT_PATH, 'pr', 'resolve-thread', '--help')
    assert result.success, f'pr resolve-thread --help failed: {result.stderr}'
    assert '--pr-number' in result.stdout
    assert '--thread-id' in result.stdout


def test_pr_resolve_thread_missing_required():
    """Test pr resolve-thread fails without required arguments."""
    result = run_script(SCRIPT_PATH, 'pr', 'resolve-thread')
    assert not result.success, 'Expected failure without --pr-number'


def test_pr_thread_reply_help():
    """Test pr thread-reply help shows required arguments."""
    result = run_script(SCRIPT_PATH, 'pr', 'thread-reply', '--help')
    assert result.success, f'pr thread-reply --help failed: {result.stderr}'
    assert '--pr-number' in result.stdout
    assert '--thread-id' in result.stdout
    assert '--body' in result.stdout


def test_pr_thread_reply_missing_required():
    """Test pr thread-reply fails without required arguments."""
    result = run_script(SCRIPT_PATH, 'pr', 'thread-reply')
    assert not result.success, 'Expected failure without --pr-number'


def test_pr_merge_help():
    """Test pr merge help shows required arguments."""
    result = run_script(SCRIPT_PATH, 'pr', 'merge', '--help')
    assert result.success, f'pr merge --help failed: {result.stderr}'
    assert '--pr-number' in result.stdout


def test_pr_auto_merge_help():
    """Test pr auto-merge help shows required arguments."""
    result = run_script(SCRIPT_PATH, 'pr', 'auto-merge', '--help')
    assert result.success, f'pr auto-merge --help failed: {result.stderr}'
    assert '--pr-number' in result.stdout


def test_pr_close_help():
    """Test pr close help shows required arguments."""
    result = run_script(SCRIPT_PATH, 'pr', 'close', '--help')
    assert result.success, f'pr close --help failed: {result.stderr}'
    assert '--pr-number' in result.stdout


def test_pr_ready_help():
    """Test pr ready help shows required arguments."""
    result = run_script(SCRIPT_PATH, 'pr', 'ready', '--help')
    assert result.success, f'pr ready --help failed: {result.stderr}'
    assert '--pr-number' in result.stdout


def test_pr_edit_help():
    """Test pr edit help shows arguments."""
    result = run_script(SCRIPT_PATH, 'pr', 'edit', '--help')
    assert result.success, f'pr edit --help failed: {result.stderr}'
    assert '--pr-number' in result.stdout
    assert '--title' in result.stdout


def test_ci_rerun_help():
    """Test ci rerun help shows required arguments."""
    result = run_script(SCRIPT_PATH, 'ci', 'rerun', '--help')
    assert result.success, f'ci rerun --help failed: {result.stderr}'
    assert '--run-id' in result.stdout


def test_ci_logs_help():
    """Test ci logs help shows required arguments."""
    result = run_script(SCRIPT_PATH, 'ci', 'logs', '--help')
    assert result.success, f'ci logs --help failed: {result.stderr}'
    assert '--run-id' in result.stdout


def test_issue_close_help():
    """Test issue close help shows required arguments."""
    result = run_script(SCRIPT_PATH, 'issue', 'close', '--help')
    assert result.success, f'issue close --help failed: {result.stderr}'
    assert '--issue' in result.stdout


def test_pr_list_help():
    """Test pr list help shows optional arguments."""
    result = run_script(SCRIPT_PATH, 'pr', 'list', '--help')
    assert result.success, f'pr list --help failed: {result.stderr}'
    assert '--head' in result.stdout
    assert '--state' in result.stdout


def test_pr_list_state_choices():
    """Test pr list accepts valid state choices."""
    result = run_script(SCRIPT_PATH, 'pr', 'list', '--help')
    assert result.success
    assert 'open' in result.stdout


def test_no_subcommand():
    """Test that script requires a subcommand."""
    result = run_script(SCRIPT_PATH)
    assert not result.success, 'Expected failure without subcommand'

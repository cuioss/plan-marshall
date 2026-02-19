#!/usr/bin/env python3
"""Tests for manage-log.py CLI script.

Write API: manage-log {type} --plan-id {plan_id} --level {level} --message "{message}"
- type: script, work, or decision subcommand
- --plan-id: plan identifier (required)
- --level: INFO, WARN, ERROR (required)
- --message: log message (required)

No stdout output, exit code only.
"""

from pathlib import Path

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import PlanContext, get_script_path, run_script

# Get script path
SCRIPT_PATH = get_script_path('plan-marshall', 'manage-logging', 'manage-log.py')


def read_log_file(plan_dir: Path, log_type: str) -> str:
    """Read log file content from logs/ subdirectory."""
    if log_type == 'work':
        filename = 'work.log'
    elif log_type == 'decision':
        filename = 'decision.log'
    else:
        filename = 'script-execution.log'
    log_file = plan_dir / 'logs' / filename
    if log_file.exists():
        return log_file.read_text()
    return ''


# =============================================================================
# Test: Script Type Logging
# =============================================================================


def test_script_success():
    """Test script type logs INFO entry for success."""
    import re

    with PlanContext(plan_id='log-script-success') as ctx:
        result = run_script(SCRIPT_PATH, 'script', '--plan-id', 'log-script-success', '--level', 'INFO', '--message', 'test:skill:script add (0.15s)')
        assert result.success, f'Script failed: {result.stderr}'
        assert result.stdout == '', 'Expected no stdout output'

        log_content = read_log_file(ctx.plan_dir, 'script')
        assert '[INFO]' in log_content
        assert 'test:skill:script add (0.15s)' in log_content
        # Verify hash is present in log format
        assert re.search(r'\[[a-f0-9]{6}\]', log_content), 'Hash should be in log entry'


def test_script_error():
    """Test script type logs ERROR entry."""
    with PlanContext(plan_id='log-script-error') as ctx:
        result = run_script(SCRIPT_PATH, 'script', '--plan-id', 'log-script-error', '--level', 'ERROR', '--message', 'test:skill:script add failed')
        assert result.success, f'Script failed: {result.stderr}'

        log_content = read_log_file(ctx.plan_dir, 'script')
        assert '[ERROR]' in log_content


# =============================================================================
# Test: Work Type Logging
# =============================================================================


def test_work_info():
    """Test work type logs INFO entry."""
    with PlanContext(plan_id='log-work-info') as ctx:
        result = run_script(SCRIPT_PATH, 'work', '--plan-id', 'log-work-info', '--level', 'INFO', '--message', 'Created deliverable: auth module')
        assert result.success, f'Script failed: {result.stderr}'
        assert result.stdout == '', 'Expected no stdout output'

        log_content = read_log_file(ctx.plan_dir, 'work')
        assert '[INFO]' in log_content
        assert 'Created deliverable: auth module' in log_content


def test_work_warn():
    """Test work type logs WARN entry."""
    with PlanContext(plan_id='log-work-warn') as ctx:
        result = run_script(SCRIPT_PATH, 'work', '--plan-id', 'log-work-warn', '--level', 'WARN', '--message', 'Skipped validation step')
        assert result.success, f'Script failed: {result.stderr}'

        log_content = read_log_file(ctx.plan_dir, 'work')
        assert '[WARN]' in log_content


# =============================================================================
# Test: Validation
# =============================================================================


def test_invalid_type():
    """Test that invalid type fails."""
    with PlanContext(plan_id='log-invalid-type'):
        result = run_script(SCRIPT_PATH, 'invalid', '--plan-id', 'log-invalid-type', '--level', 'INFO', '--message', 'Test message')
        assert not result.success, 'Expected failure for invalid type'


def test_invalid_level():
    """Test that invalid level fails."""
    with PlanContext(plan_id='log-invalid-level'):
        result = run_script(SCRIPT_PATH, 'work', '--plan-id', 'log-invalid-level', '--level', 'INVALID', '--message', 'Test message')
        assert not result.success, 'Expected failure for invalid level'


def test_missing_args():
    """Test that missing args fails."""
    result = run_script(SCRIPT_PATH, 'work', '--plan-id', 'my-plan', '--level', 'INFO')
    assert not result.success, 'Expected failure for missing args'


def test_multiple_entries():
    """Test multiple log entries append correctly."""
    with PlanContext(plan_id='log-multiple') as ctx:
        run_script(SCRIPT_PATH, 'work', '--plan-id', 'log-multiple', '--level', 'INFO', '--message', 'First entry')
        run_script(SCRIPT_PATH, 'work', '--plan-id', 'log-multiple', '--level', 'INFO', '--message', 'Second entry')
        run_script(SCRIPT_PATH, 'work', '--plan-id', 'log-multiple', '--level', 'WARN', '--message', 'Third entry')

        log_content = read_log_file(ctx.plan_dir, 'work')
        assert 'First entry' in log_content
        assert 'Second entry' in log_content
        assert 'Third entry' in log_content


# =============================================================================
# Test: Read Subcommand
# =============================================================================


def test_read_work_log():
    """Test read subcommand returns work log entries."""
    with PlanContext(plan_id='log-read-work'):
        # Write some entries first
        run_script(SCRIPT_PATH, 'work', '--plan-id', 'log-read-work', '--level', 'INFO', '--message', 'Test entry one')
        run_script(SCRIPT_PATH, 'work', '--plan-id', 'log-read-work', '--level', 'INFO', '--message', 'Test entry two')

        # Read them back
        result = run_script(SCRIPT_PATH, 'read', '--plan-id', 'log-read-work', '--type', 'work')
        assert result.success, f'Read failed: {result.stderr}'
        assert 'status: success' in result.stdout
        assert 'total_entries: 2' in result.stdout
        assert 'Test entry one' in result.stdout
        assert 'Test entry two' in result.stdout
        # Verify hash_id is present in output
        assert 'hash_id:' in result.stdout, 'hash_id should be in parsed output'


def test_read_work_log_with_limit():
    """Test read subcommand with --limit returns limited entries."""
    with PlanContext(plan_id='log-read-limit'):
        # Write multiple entries
        run_script(SCRIPT_PATH, 'work', '--plan-id', 'log-read-limit', '--level', 'INFO', '--message', 'Entry 1')
        run_script(SCRIPT_PATH, 'work', '--plan-id', 'log-read-limit', '--level', 'INFO', '--message', 'Entry 2')
        run_script(SCRIPT_PATH, 'work', '--plan-id', 'log-read-limit', '--level', 'INFO', '--message', 'Entry 3')
        run_script(SCRIPT_PATH, 'work', '--plan-id', 'log-read-limit', '--level', 'INFO', '--message', 'Entry 4')

        # Read with limit
        result = run_script(SCRIPT_PATH, 'read', '--plan-id', 'log-read-limit', '--type', 'work', '--limit', '2')
        assert result.success, f'Read failed: {result.stderr}'
        assert 'status: success' in result.stdout
        assert 'total_entries: 4' in result.stdout
        assert 'showing: 2' in result.stdout
        # Should show most recent entries
        assert 'Entry 3' in result.stdout
        assert 'Entry 4' in result.stdout


def test_read_empty_log():
    """Test read subcommand on plan with no log entries."""
    with PlanContext(plan_id='log-read-empty'):
        result = run_script(SCRIPT_PATH, 'read', '--plan-id', 'log-read-empty', '--type', 'work')
        assert result.success, f'Read failed: {result.stderr}'
        assert 'status: success' in result.stdout
        assert 'total_entries: 0' in result.stdout


def test_read_script_log():
    """Test read subcommand for script type logs."""
    with PlanContext(plan_id='log-read-script'):
        # Write script log entry
        run_script(SCRIPT_PATH, 'script', '--plan-id', 'log-read-script', '--level', 'INFO', '--message', 'test:skill:script (0.1s)')

        # Read it back
        result = run_script(SCRIPT_PATH, 'read', '--plan-id', 'log-read-script', '--type', 'script')
        assert result.success, f'Read failed: {result.stderr}'
        assert 'status: success' in result.stdout
        assert 'log_type: script' in result.stdout


def test_read_missing_plan_id():
    """Test read subcommand fails without --plan-id."""
    result = run_script(SCRIPT_PATH, 'read', '--type', 'work')
    assert not result.success, 'Expected failure without --plan-id'
    assert '--plan-id' in result.stderr


def test_read_missing_type():
    """Test read subcommand fails without --type."""
    result = run_script(SCRIPT_PATH, 'read', '--plan-id', 'test-plan')
    assert not result.success, 'Expected failure without --type'
    assert '--type' in result.stderr


def test_read_invalid_type():
    """Test read subcommand fails with invalid type."""
    result = run_script(SCRIPT_PATH, 'read', '--plan-id', 'test-plan', '--type', 'invalid')
    assert not result.success, 'Expected failure with invalid type'
    assert 'invalid choice' in result.stderr


# =============================================================================
# Test: Separator Subcommand
# =============================================================================


def test_separator_writes_blank_line():
    """Test separator subcommand appends a blank line to the log."""
    with PlanContext(plan_id='log-separator') as ctx:
        # Write an entry first
        run_script(SCRIPT_PATH, 'work', '--plan-id', 'log-separator', '--level', 'INFO', '--message', 'Before separator')

        # Add separator
        result = run_script(SCRIPT_PATH, 'separator', '--plan-id', 'log-separator', '--type', 'work')
        assert result.success, f'Separator failed: {result.stderr}'
        assert result.stdout == '', 'Expected no stdout output'

        # Write another entry after
        run_script(SCRIPT_PATH, 'work', '--plan-id', 'log-separator', '--level', 'INFO', '--message', 'After separator')

        # Verify blank line exists between entries
        log_content = read_log_file(ctx.plan_dir, 'work')
        assert 'Before separator' in log_content
        assert 'After separator' in log_content
        # The log entry ends with \n, separator adds \n → \n\n creates a blank line
        assert '\n\n' in log_content, 'Separator should create visual gap between entries'


def test_separator_default_type():
    """Test separator defaults to work log type."""
    with PlanContext(plan_id='log-separator-default') as ctx:
        # Write an entry
        run_script(SCRIPT_PATH, 'work', '--plan-id', 'log-separator-default', '--level', 'INFO', '--message', 'Test entry')

        # Add separator without --type (should default to work)
        result = run_script(SCRIPT_PATH, 'separator', '--plan-id', 'log-separator-default')
        assert result.success, f'Separator failed: {result.stderr}'

        log_content = read_log_file(ctx.plan_dir, 'work')
        assert 'Test entry' in log_content
        # Verify blank line was added
        assert log_content.endswith('\n\n'), 'Separator should append blank line after existing content'

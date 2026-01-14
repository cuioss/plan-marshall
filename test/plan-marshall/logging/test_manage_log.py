#!/usr/bin/env python3
"""Tests for manage-log.py CLI script.

New simplified API: manage-log {type} {plan_id} {level} "{message}"
- type: script or work
- plan_id: plan identifier
- level: INFO, WARN, ERROR
- message: log message

No stdout output, exit code only.
"""

from pathlib import Path

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import PlanContext, get_script_path, run_script

# Get script path
SCRIPT_PATH = get_script_path('plan-marshall', 'logging', 'manage-log.py')


def read_log_file(plan_dir: Path, log_type: str) -> str:
    """Read log file content."""
    filename = 'work.log' if log_type == 'work' else 'script-execution.log'
    log_file = plan_dir / filename
    if log_file.exists():
        return log_file.read_text()
    return ''


# =============================================================================
# Test: Script Type Logging
# =============================================================================


def test_script_success():
    """Test script type logs INFO entry for success."""
    with PlanContext(plan_id='log-script-success') as ctx:
        result = run_script(SCRIPT_PATH, 'script', 'log-script-success', 'INFO', 'test:skill:script add (0.15s)')
        assert result.success, f'Script failed: {result.stderr}'
        assert result.stdout == '', 'Expected no stdout output'

        log_content = read_log_file(ctx.plan_dir, 'script')
        assert '[INFO]' in log_content
        assert 'test:skill:script add (0.15s)' in log_content


def test_script_error():
    """Test script type logs ERROR entry."""
    with PlanContext(plan_id='log-script-error') as ctx:
        result = run_script(SCRIPT_PATH, 'script', 'log-script-error', 'ERROR', 'test:skill:script add failed')
        assert result.success, f'Script failed: {result.stderr}'

        log_content = read_log_file(ctx.plan_dir, 'script')
        assert '[ERROR]' in log_content


# =============================================================================
# Test: Work Type Logging
# =============================================================================


def test_work_info():
    """Test work type logs INFO entry."""
    with PlanContext(plan_id='log-work-info') as ctx:
        result = run_script(SCRIPT_PATH, 'work', 'log-work-info', 'INFO', 'Created deliverable: auth module')
        assert result.success, f'Script failed: {result.stderr}'
        assert result.stdout == '', 'Expected no stdout output'

        log_content = read_log_file(ctx.plan_dir, 'work')
        assert '[INFO]' in log_content
        assert 'Created deliverable: auth module' in log_content


def test_work_warn():
    """Test work type logs WARN entry."""
    with PlanContext(plan_id='log-work-warn') as ctx:
        result = run_script(SCRIPT_PATH, 'work', 'log-work-warn', 'WARN', 'Skipped validation step')
        assert result.success, f'Script failed: {result.stderr}'

        log_content = read_log_file(ctx.plan_dir, 'work')
        assert '[WARN]' in log_content


# =============================================================================
# Test: Validation
# =============================================================================


def test_invalid_type():
    """Test that invalid type fails."""
    with PlanContext(plan_id='log-invalid-type'):
        result = run_script(SCRIPT_PATH, 'invalid', 'log-invalid-type', 'INFO', 'Test message')
        assert not result.success, 'Expected failure for invalid type'
        assert 'type must be one of' in result.stderr


def test_invalid_level():
    """Test that invalid level fails."""
    with PlanContext(plan_id='log-invalid-level'):
        result = run_script(SCRIPT_PATH, 'work', 'log-invalid-level', 'INVALID', 'Test message')
        assert not result.success, 'Expected failure for invalid level'
        assert 'level must be one of' in result.stderr


def test_missing_args():
    """Test that missing args fails."""
    result = run_script(SCRIPT_PATH, 'work', 'my-plan', 'INFO')
    assert not result.success, 'Expected failure for missing args'
    assert 'Usage:' in result.stderr


def test_multiple_entries():
    """Test multiple log entries append correctly."""
    with PlanContext(plan_id='log-multiple') as ctx:
        run_script(SCRIPT_PATH, 'work', 'log-multiple', 'INFO', 'First entry')
        run_script(SCRIPT_PATH, 'work', 'log-multiple', 'INFO', 'Second entry')
        run_script(SCRIPT_PATH, 'work', 'log-multiple', 'WARN', 'Third entry')

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
        run_script(SCRIPT_PATH, 'work', 'log-read-work', 'INFO', 'Test entry one')
        run_script(SCRIPT_PATH, 'work', 'log-read-work', 'INFO', 'Test entry two')

        # Read them back
        result = run_script(SCRIPT_PATH, 'read', '--plan-id', 'log-read-work', '--type', 'work')
        assert result.success, f'Read failed: {result.stderr}'
        assert 'status: success' in result.stdout
        assert 'total_entries: 2' in result.stdout
        assert 'Test entry one' in result.stdout
        assert 'Test entry two' in result.stdout


def test_read_work_log_with_limit():
    """Test read subcommand with --limit returns limited entries."""
    with PlanContext(plan_id='log-read-limit'):
        # Write multiple entries
        run_script(SCRIPT_PATH, 'work', 'log-read-limit', 'INFO', 'Entry 1')
        run_script(SCRIPT_PATH, 'work', 'log-read-limit', 'INFO', 'Entry 2')
        run_script(SCRIPT_PATH, 'work', 'log-read-limit', 'INFO', 'Entry 3')
        run_script(SCRIPT_PATH, 'work', 'log-read-limit', 'INFO', 'Entry 4')

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
        run_script(SCRIPT_PATH, 'script', 'log-read-script', 'INFO', 'test:skill:script (0.1s)')

        # Read it back
        result = run_script(SCRIPT_PATH, 'read', '--plan-id', 'log-read-script', '--type', 'script')
        assert result.success, f'Read failed: {result.stderr}'
        assert 'status: success' in result.stdout
        assert 'log_type: script' in result.stdout


def test_read_missing_plan_id():
    """Test read subcommand fails without --plan-id."""
    result = run_script(SCRIPT_PATH, 'read', '--type', 'work')
    assert not result.success, 'Expected failure without --plan-id'
    assert 'missing_argument' in result.stderr
    assert '--plan-id is required' in result.stderr


def test_read_missing_type():
    """Test read subcommand fails without --type."""
    result = run_script(SCRIPT_PATH, 'read', '--plan-id', 'test-plan')
    assert not result.success, 'Expected failure without --type'
    assert 'missing_argument' in result.stderr
    assert '--type is required' in result.stderr


def test_read_invalid_type():
    """Test read subcommand fails with invalid type."""
    result = run_script(SCRIPT_PATH, 'read', '--plan-id', 'test-plan', '--type', 'invalid')
    assert not result.success, 'Expected failure with invalid type'
    assert 'invalid_type' in result.stderr

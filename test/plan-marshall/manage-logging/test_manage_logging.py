#!/usr/bin/env python3
"""Tests for manage-logging.py CLI script.

Write API: manage-log {type} --plan-id {plan_id} --level {level} --message "{message}"
- type: script, work, or decision subcommand
- --plan-id: plan identifier (required)
- --level: INFO, WARNING, ERROR (required)
- --message: log message (required)

No stdout output, exit code only.
"""

import importlib.util
from argparse import Namespace
from pathlib import Path

from conftest import PlanContext, get_script_path, run_script

# Script path for remaining subprocess (CLI plumbing) tests
SCRIPT_PATH = get_script_path('plan-marshall', 'manage-logging', 'manage-logging.py')

# Tier 2 direct imports - load hyphenated module via importlib
_MANAGE_LOGGING_SCRIPT = str(
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-logging'
    / 'scripts'
    / 'manage-logging.py'
)
_spec = importlib.util.spec_from_file_location('manage_logging', _MANAGE_LOGGING_SCRIPT)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

handle_read = _mod.handle_read
handle_write = _mod.handle_write
handle_separator = _mod.handle_separator


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
        result = handle_write(
            Namespace(
                log_type='script', plan_id='log-script-success', level='INFO', message='test:skill:script add (0.15s)'
            )
        )
        assert result is None, 'handle_write returns None on success'

        log_content = read_log_file(ctx.plan_dir, 'script')
        assert '[INFO]' in log_content
        assert 'test:skill:script add (0.15s)' in log_content
        # Verify hash is present in log format
        assert re.search(r'\[[a-f0-9]{6}\]', log_content), 'Hash should be in log entry'


def test_script_error():
    """Test script type logs ERROR entry."""
    with PlanContext(plan_id='log-script-error') as ctx:
        result = handle_write(
            Namespace(
                log_type='script', plan_id='log-script-error', level='ERROR', message='test:skill:script add failed'
            )
        )
        assert result is None, 'handle_write returns None on success'

        log_content = read_log_file(ctx.plan_dir, 'script')
        assert '[ERROR]' in log_content


# =============================================================================
# Test: Work Type Logging
# =============================================================================


def test_work_info():
    """Test work type logs INFO entry."""
    with PlanContext(plan_id='log-work-info') as ctx:
        result = handle_write(
            Namespace(
                log_type='work', plan_id='log-work-info', level='INFO', message='Created deliverable: auth module'
            )
        )
        assert result is None, 'handle_write returns None on success'

        log_content = read_log_file(ctx.plan_dir, 'work')
        assert '[INFO]' in log_content
        assert 'Created deliverable: auth module' in log_content


def test_work_warn():
    """Test work type logs WARNING entry."""
    with PlanContext(plan_id='log-work-warn') as ctx:
        result = handle_write(
            Namespace(log_type='work', plan_id='log-work-warn', level='WARNING', message='Skipped validation step')
        )
        assert result is None, 'handle_write returns None on success'

        log_content = read_log_file(ctx.plan_dir, 'work')
        assert '[WARNING]' in log_content


# =============================================================================
# Test: Multiple Entries
# =============================================================================


def test_multiple_entries():
    """Test multiple log entries append correctly."""
    with PlanContext(plan_id='log-multiple') as ctx:
        handle_write(Namespace(log_type='work', plan_id='log-multiple', level='INFO', message='First entry'))
        handle_write(Namespace(log_type='work', plan_id='log-multiple', level='INFO', message='Second entry'))
        handle_write(Namespace(log_type='work', plan_id='log-multiple', level='WARNING', message='Third entry'))

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
        handle_write(Namespace(log_type='work', plan_id='log-read-work', level='INFO', message='Test entry one'))
        handle_write(Namespace(log_type='work', plan_id='log-read-work', level='INFO', message='Test entry two'))

        # Read them back
        result = handle_read(Namespace(plan_id='log-read-work', type='work', limit=None, phase=None))
        assert result['status'] == 'success'
        assert result['total_entries'] == 2
        # Verify hash_id is present in parsed entries
        assert any('hash_id' in str(e) for e in result.get('entries', [result])), 'hash_id should be in parsed output'


def test_read_work_log_with_limit():
    """Test read subcommand with --limit returns limited entries."""
    with PlanContext(plan_id='log-read-limit'):
        # Write multiple entries
        handle_write(Namespace(log_type='work', plan_id='log-read-limit', level='INFO', message='Entry 1'))
        handle_write(Namespace(log_type='work', plan_id='log-read-limit', level='INFO', message='Entry 2'))
        handle_write(Namespace(log_type='work', plan_id='log-read-limit', level='INFO', message='Entry 3'))
        handle_write(Namespace(log_type='work', plan_id='log-read-limit', level='INFO', message='Entry 4'))

        # Read with limit
        result = handle_read(Namespace(plan_id='log-read-limit', type='work', limit=2, phase=None))
        assert result['status'] == 'success'
        assert result['total_entries'] == 4
        assert result['showing'] == 2


def test_read_empty_log():
    """Test read subcommand on plan with no log entries."""
    with PlanContext(plan_id='log-read-empty'):
        result = handle_read(Namespace(plan_id='log-read-empty', type='work', limit=None, phase=None))
        assert result['status'] == 'success'
        assert result['total_entries'] == 0


def test_read_script_log():
    """Test read subcommand for script type logs."""
    with PlanContext(plan_id='log-read-script'):
        # Write script log entry
        handle_write(
            Namespace(log_type='script', plan_id='log-read-script', level='INFO', message='test:skill:script (0.1s)')
        )

        # Read it back
        result = handle_read(Namespace(plan_id='log-read-script', type='script', limit=None, phase=None))
        assert result['status'] == 'success'
        assert result['log_type'] == 'script'


# =============================================================================
# Test: Separator Subcommand
# =============================================================================


def test_separator_writes_blank_line():
    """Test separator subcommand appends a blank line to the log."""
    with PlanContext(plan_id='log-separator') as ctx:
        # Write an entry first
        handle_write(Namespace(log_type='work', plan_id='log-separator', level='INFO', message='Before separator'))

        # Add separator
        result = handle_separator(Namespace(type='work', plan_id='log-separator'))
        assert result is None, 'handle_separator returns None'

        # Write another entry after
        handle_write(Namespace(log_type='work', plan_id='log-separator', level='INFO', message='After separator'))

        # Verify blank line exists between entries
        log_content = read_log_file(ctx.plan_dir, 'work')
        assert 'Before separator' in log_content
        assert 'After separator' in log_content
        # The log entry ends with \n, separator adds \n -> \n\n creates a blank line
        assert '\n\n' in log_content, 'Separator should create visual gap between entries'


def test_separator_default_type():
    """Test separator defaults to work log type."""
    with PlanContext(plan_id='log-separator-default') as ctx:
        # Write an entry
        handle_write(Namespace(log_type='work', plan_id='log-separator-default', level='INFO', message='Test entry'))

        # Add separator without --type (default is work)
        result = handle_separator(Namespace(type='work', plan_id='log-separator-default'))
        assert result is None, 'handle_separator returns None'

        log_content = read_log_file(ctx.plan_dir, 'work')
        assert 'Test entry' in log_content
        # Verify blank line was added
        assert log_content.endswith('\n\n'), 'Separator should append blank line after existing content'


# =============================================================================
# CLI Plumbing Tests (Tier 3 - subprocess)
# =============================================================================


def test_cli_invalid_type():
    """Test that invalid type fails via argparse."""
    with PlanContext(plan_id='log-invalid-type'):
        result = run_script(
            SCRIPT_PATH, 'invalid', '--plan-id', 'log-invalid-type', '--level', 'INFO', '--message', 'Test message'
        )
        assert not result.success, 'Expected failure for invalid type'


def test_cli_invalid_level():
    """Test that invalid level fails via argparse."""
    with PlanContext(plan_id='log-invalid-level'):
        result = run_script(
            SCRIPT_PATH, 'work', '--plan-id', 'log-invalid-level', '--level', 'INVALID', '--message', 'Test message'
        )
        assert not result.success, 'Expected failure for invalid level'


def test_cli_missing_args():
    """Test that missing args fails via argparse."""
    result = run_script(SCRIPT_PATH, 'work', '--plan-id', 'my-plan', '--level', 'INFO')
    assert not result.success, 'Expected failure for missing args'

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

import pytest

from conftest import get_script_path, run_script

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


@pytest.fixture(autouse=True)
def _seed_status_sentinel(plan_context, monkeypatch):
    """Seed a ``status.json`` sentinel into every plan dir these tests touch.

    ``get_log_path`` resolves plan-scoped logging ONLY when the plan dir carries
    a ``status.json`` sentinel; without it the logging silently falls back to the
    global log. Every test in this file exercises plan-scoped logging, so the
    sentinel must exist before each ``handle_write`` / ``handle_read`` call.

    Two seeding paths are needed because plan dirs are resolved two ways:

    * Tests that call ``plan_context.plan_dir_for(plan_id)`` directly — wrap that
      method so it also writes the sentinel.
    * Tests that only pass a ``plan_id`` string into ``handle_write`` /
      ``handle_read`` (the read round-trip tests) — the logging script computes
      ``get_plans_dir() / plan_id`` itself and never calls ``plan_dir_for``, so
      pre-create+seed those plan dirs eagerly. ``get_plans_dir()`` resolves to
      ``plan_context.plans_dir`` under the fixture's ``PLAN_BASE_DIR`` patch.
    """

    def _seed(plan_dir: Path) -> None:
        sentinel = plan_dir / 'status.json'
        if not sentinel.exists():
            sentinel.write_text('{}', encoding='utf-8')

    _orig = plan_context.plan_dir_for

    def _seeding(plan_id):
        d = _orig(plan_id)
        _seed(d)
        return d

    monkeypatch.setattr(plan_context, 'plan_dir_for', _seeding)

    # Read round-trip tests pass these plan_ids straight into handle_write/
    # handle_read without ever calling plan_dir_for, so seed them eagerly.
    for plan_id in ('log-read-work', 'log-read-limit', 'log-read-empty', 'log-read-script'):
        d = plan_context.plans_dir / plan_id
        d.mkdir(parents=True, exist_ok=True)
        _seed(d)


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


def test_script_success(plan_context):
    """Test script type logs INFO entry for success."""
    import re

    plan_dir = plan_context.plan_dir_for('log-script-success')
    result = handle_write(
        Namespace(
            log_type='script', plan_id='log-script-success', level='INFO', message='test:skill:script add (0.15s)'
        )
    )
    assert result is None, 'handle_write returns None on success'

    log_content = read_log_file(plan_dir, 'script')
    assert '[INFO]' in log_content
    assert 'test:skill:script add (0.15s)' in log_content
    # Verify hash is present in log format
    assert re.search(r'\[[a-f0-9]{6}\]', log_content), 'Hash should be in log entry'


def test_script_error(plan_context):
    """Test script type logs ERROR entry."""
    plan_dir = plan_context.plan_dir_for('log-script-error')
    result = handle_write(
        Namespace(
            log_type='script', plan_id='log-script-error', level='ERROR', message='test:skill:script add failed'
        )
    )
    assert result is None, 'handle_write returns None on success'

    log_content = read_log_file(plan_dir, 'script')
    assert '[ERROR]' in log_content


# =============================================================================
# Test: Work Type Logging
# =============================================================================


def test_work_info(plan_context):
    """Test work type logs INFO entry."""
    plan_dir = plan_context.plan_dir_for('log-work-info')
    result = handle_write(
        Namespace(
            log_type='work', plan_id='log-work-info', level='INFO', message='Created deliverable: auth module'
        )
    )
    assert result is None, 'handle_write returns None on success'

    log_content = read_log_file(plan_dir, 'work')
    assert '[INFO]' in log_content
    assert 'Created deliverable: auth module' in log_content


def test_work_warn(plan_context):
    """Test work type logs WARNING entry."""
    plan_dir = plan_context.plan_dir_for('log-work-warn')
    result = handle_write(
        Namespace(log_type='work', plan_id='log-work-warn', level='WARNING', message='Skipped validation step')
    )
    assert result is None, 'handle_write returns None on success'

    log_content = read_log_file(plan_dir, 'work')
    assert '[WARNING]' in log_content


# =============================================================================
# Test: Multiple Entries
# =============================================================================


def test_multiple_entries(plan_context):
    """Test multiple log entries append correctly."""
    plan_dir = plan_context.plan_dir_for('log-multiple')
    handle_write(Namespace(log_type='work', plan_id='log-multiple', level='INFO', message='First entry'))
    handle_write(Namespace(log_type='work', plan_id='log-multiple', level='INFO', message='Second entry'))
    handle_write(Namespace(log_type='work', plan_id='log-multiple', level='WARNING', message='Third entry'))

    log_content = read_log_file(plan_dir, 'work')
    assert 'First entry' in log_content
    assert 'Second entry' in log_content
    assert 'Third entry' in log_content


# =============================================================================
# Test: Read Subcommand
# =============================================================================


def test_read_work_log(plan_context):
    """Test read subcommand returns work log entries."""
    # Write some entries first
    handle_write(Namespace(log_type='work', plan_id='log-read-work', level='INFO', message='Test entry one'))
    handle_write(Namespace(log_type='work', plan_id='log-read-work', level='INFO', message='Test entry two'))

    # Read them back
    result = handle_read(Namespace(plan_id='log-read-work', type='work', limit=None, phase=None))
    assert result['status'] == 'success'
    assert result['total_entries'] == 2
    # Verify hash_id is present in parsed entries
    assert any('hash_id' in str(e) for e in result.get('entries', [result])), 'hash_id should be in parsed output'


def test_read_work_log_with_limit(plan_context):
    """Test read subcommand with --limit returns limited entries."""
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


def test_read_empty_log(plan_context):
    """Test read subcommand on plan with no log entries."""
    result = handle_read(Namespace(plan_id='log-read-empty', type='work', limit=None, phase=None))
    assert result['status'] == 'success'
    assert result['total_entries'] == 0


def test_read_script_log(plan_context):
    """Test read subcommand for script type logs."""
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


def test_separator_writes_blank_line(plan_context):
    """Test separator subcommand appends a blank line to the log."""
    plan_dir = plan_context.plan_dir_for('log-separator')
    # Write an entry first
    handle_write(Namespace(log_type='work', plan_id='log-separator', level='INFO', message='Before separator'))

    # Add separator
    result = handle_separator(Namespace(type='work', plan_id='log-separator'))
    assert result is None, 'handle_separator returns None'

    # Write another entry after
    handle_write(Namespace(log_type='work', plan_id='log-separator', level='INFO', message='After separator'))

    # Verify blank line exists between entries
    log_content = read_log_file(plan_dir, 'work')
    assert 'Before separator' in log_content
    assert 'After separator' in log_content
    # The log entry ends with \n, separator adds \n -> \n\n creates a blank line
    assert '\n\n' in log_content, 'Separator should create visual gap between entries'


def test_separator_default_type(plan_context):
    """Test separator defaults to work log type."""
    plan_dir = plan_context.plan_dir_for('log-separator-default')
    # Write an entry
    handle_write(Namespace(log_type='work', plan_id='log-separator-default', level='INFO', message='Test entry'))

    # Add separator without --type (default is work)
    result = handle_separator(Namespace(type='work', plan_id='log-separator-default'))
    assert result is None, 'handle_separator returns None'

    log_content = read_log_file(plan_dir, 'work')
    assert 'Test entry' in log_content
    # Verify blank line was added
    assert log_content.endswith('\n\n'), 'Separator should append blank line after existing content'


# =============================================================================
# CLI Plumbing Tests (Tier 3 - subprocess)
# =============================================================================


def test_cli_invalid_type(plan_context):
    """Test that invalid type fails via argparse."""
    result = run_script(
        SCRIPT_PATH, 'invalid', '--plan-id', 'log-invalid-type', '--level', 'INFO', '--message', 'Test message'
    )
    assert not result.success, 'Expected failure for invalid type'


def test_cli_invalid_level(plan_context):
    """Test that invalid level fails via argparse."""
    result = run_script(
        SCRIPT_PATH, 'work', '--plan-id', 'log-invalid-level', '--level', 'INVALID', '--message', 'Test message'
    )
    assert not result.success, 'Expected failure for invalid level'


def test_cli_missing_args():
    """Test that missing args fails via argparse."""
    result = run_script(SCRIPT_PATH, 'work', '--plan-id', 'my-plan', '--level', 'INFO')
    assert not result.success, 'Expected failure for missing args'

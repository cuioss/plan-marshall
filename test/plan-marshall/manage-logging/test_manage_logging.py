#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
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
assert _spec is not None and _spec.loader is not None
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


# =============================================================================
# Global / no-plan logging path + STEWARD audit namespace (D11)
# =============================================================================
#
# manage-logging write subcommands (work / decision / script) accept a plan-less
# call: omitting --plan-id writes to the dated global log under .plan/logs/. This
# is the first-class global path used by plan-less callers such as
# marshall-steward, which emit a [STEWARD] (plan-marshall:marshall-steward) audit
# trail through it. Resolving the global path via the same get_log_path the writer
# uses keeps these tests robust to base-dir resolution under the test fixture.

get_log_path = _mod.get_log_path


def _read_global_log(log_type: str) -> str:
    """Read the dated global log file for log_type (the no-plan target)."""
    path = get_log_path(None, log_type)
    return path.read_text(encoding='utf-8') if path.exists() else ''


def test_write_without_plan_id_targets_global_decision_log(plan_context):
    """A decision write with plan_id=None lands in the dated global decision log.

    Exercises the first-class global/no-plan path: handle_write with plan_id=None
    must route to .plan/logs/decision-{date}.log rather than any plan-scoped log.
    """
    # capture the global decision log content before the write
    before = _read_global_log('decision')
    steward_msg = '[STEWARD] (plan-marshall:marshall-steward) Selected balanced effort preset'

    # plan-less decision write under the STEWARD namespace
    result = handle_write(
        Namespace(log_type='decision', plan_id=None, level='INFO', message=steward_msg)
    )

    # fire-and-forget (None) and the entry landed in the global log
    assert result is None
    after = _read_global_log('decision')
    assert steward_msg in after
    assert steward_msg not in before


def test_write_without_plan_id_targets_global_work_log(plan_context):
    """A work write with plan_id=None lands in the dated global work log."""
    before = _read_global_log('work')
    steward_msg = '[STEWARD] (plan-marshall:marshall-steward) Generated executor with 47 mappings'

    # plan-less work write
    result = handle_write(
        Namespace(log_type='work', plan_id=None, level='INFO', message=steward_msg)
    )

    assert result is None
    after = _read_global_log('work')
    assert steward_msg in after
    assert steward_msg not in before


def test_cli_write_without_plan_id_succeeds(plan_context):
    """CLI: a plan-less decision write under the STEWARD namespace exits cleanly."""
    # no --plan-id supplied (the first-class global path)
    result = run_script(
        SCRIPT_PATH,
        'decision',
        '--level',
        'INFO',
        '--message',
        '[STEWARD] (plan-marshall:marshall-steward) provider auto-selected',
    )

    # the plan-less global call is accepted (not an argparse rejection)
    assert result.success, 'plan-less global write must succeed'


def test_cli_write_with_invalid_plan_id_still_rejected(plan_context):
    """CLI: supplying a malformed --plan-id still fails gracefully with invalid_plan_id.

    Making --plan-id optional must NOT weaken validation when it IS supplied — a
    malformed value is still rejected by the canonical plan-id validator. The
    rejection follows the project-wide manage-* contract: the identifier-validator
    failure exits with code 0 and emits ``status: error / error: invalid_plan_id``
    on stdout (the ``parse_args_with_toon_errors`` helper deliberately does not
    surface argparse's exit-code-2 contract). See ``assert_invalid_field`` in
    ``test/_shared/_input_validation_fixtures.py``.
    """
    # a malformed plan-id value (uppercase + space) is supplied explicitly
    result = run_script(
        SCRIPT_PATH,
        'decision',
        '--plan-id',
        'Not A Valid Plan',
        '--level',
        'INFO',
        '--message',
        '[STEWARD] (plan-marshall:marshall-steward) should be rejected',
    )

    # graceful rejection via the canonical TOON error on stdout (exit 0),
    # NOT a silent success. The malformed value is rejected even though --plan-id
    # is now optional, because validation still fires whenever the flag IS present.
    assert result.returncode == 0, (
        f'identifier-validator failure must exit 0 (got {result.returncode})\n'
        f'stdout={result.stdout!r}\nstderr={result.stderr!r}'
    )
    data = result.toon()
    assert data.get('status') == 'error', f'expected status=error, got {data.get("status")!r}'
    assert data.get('error') == 'invalid_plan_id', (
        f'a malformed --plan-id must still be rejected with invalid_plan_id, '
        f'got error={data.get("error")!r}'
    )

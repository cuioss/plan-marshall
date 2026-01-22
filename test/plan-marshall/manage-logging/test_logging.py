#!/usr/bin/env python3
"""Unit tests for logging module."""

import os
import tempfile
import time
from datetime import date
from pathlib import Path

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
# Import the module under test (PYTHONPATH set by conftest)
import plan_logging as module

# =============================================================================
# TESTS: format_timestamp
# =============================================================================


def test_format_timestamp_iso8601():
    """Timestamp is ISO 8601 format with Z suffix."""
    ts = module.format_timestamp()
    assert ts.endswith('Z'), f'Expected Z suffix, got {ts}'
    assert 'T' in ts, f'Expected T separator, got {ts}'
    assert len(ts) == 20, f'Expected 20 chars, got {len(ts)}: {ts}'


# =============================================================================
# TESTS: format_log_entry
# =============================================================================


def test_format_log_entry_basic():
    """Log entry has correct structure with hash."""
    entry = module.format_log_entry('INFO', 'test message')
    assert '[INFO]' in entry, 'Missing level'
    assert 'test message' in entry, 'Missing message'
    assert entry.endswith('\n'), 'Should end with newline'
    # Hash should be present (6 hex chars in brackets)
    import re

    hash_match = re.search(r'\[[a-f0-9]{6}\]', entry)
    assert hash_match, f'Missing hash in entry: {entry}'


def test_format_log_entry_with_fields():
    """Log entry includes additional fields."""
    entry = module.format_log_entry('ERROR', 'failed', exit_code=1, args='--plan-id test')
    assert '  exit_code: 1' in entry, 'Missing exit_code field'
    assert '  args: --plan-id test' in entry, 'Missing args field'


def test_format_log_entry_skips_empty_fields():
    """Log entry skips None/empty fields."""
    entry = module.format_log_entry('INFO', 'message', phase='init', detail=None, empty='')
    assert '  phase: init' in entry, 'Missing phase field'
    assert 'detail' not in entry, 'Should skip None field'
    assert 'empty' not in entry, 'Should skip empty field'


# =============================================================================
# TESTS: compute_entry_hash
# =============================================================================


def test_compute_entry_hash_deterministic():
    """Same message always produces same hash."""
    message = 'test message content'
    hash1 = module.compute_entry_hash(message)
    hash2 = module.compute_entry_hash(message)
    assert hash1 == hash2, f'Hash not deterministic: {hash1} != {hash2}'


def test_compute_entry_hash_length():
    """Hash is exactly 6 hex characters."""
    message = 'any message'
    hash_id = module.compute_entry_hash(message)
    assert len(hash_id) == 6, f'Expected 6 chars, got {len(hash_id)}'
    assert all(c in '0123456789abcdef' for c in hash_id), f'Not hex: {hash_id}'


def test_compute_entry_hash_different_messages():
    """Different messages produce different hashes."""
    hash1 = module.compute_entry_hash('message one')
    hash2 = module.compute_entry_hash('message two')
    assert hash1 != hash2, 'Different messages should have different hashes'


def test_format_log_entry_hash_deterministic():
    """Same message in format_log_entry produces same hash."""
    import re

    message = 'consistent test message'
    entry1 = module.format_log_entry('INFO', message)
    entry2 = module.format_log_entry('INFO', message)

    # Extract hashes
    hash_pattern = re.compile(r'\[([a-f0-9]{6})\]')
    match1 = hash_pattern.search(entry1)
    match2 = hash_pattern.search(entry2)

    assert match1 and match2, 'Hash not found in entries'
    assert match1.group(1) == match2.group(1), 'Hashes should match for same message'


# =============================================================================
# TESTS: get_log_path
# =============================================================================


def test_get_log_path_plan_scoped_script():
    """Script log path for existing plan."""
    with tempfile.TemporaryDirectory() as tmp:
        plan_base = Path(tmp)
        plan_dir = plan_base / 'plans' / 'my-plan'
        plan_dir.mkdir(parents=True)

        os.environ['PLAN_BASE_DIR'] = str(plan_base)
        try:
            path = module.get_log_path('my-plan', 'script')
            assert path == plan_dir / 'logs' / 'script-execution.log'
        finally:
            del os.environ['PLAN_BASE_DIR']


def test_get_log_path_plan_scoped_work():
    """Work log path for existing plan."""
    with tempfile.TemporaryDirectory() as tmp:
        plan_base = Path(tmp)
        plan_dir = plan_base / 'plans' / 'my-plan'
        plan_dir.mkdir(parents=True)

        os.environ['PLAN_BASE_DIR'] = str(plan_base)
        try:
            path = module.get_log_path('my-plan', 'work')
            assert path == plan_dir / 'logs' / 'work.log'
        finally:
            del os.environ['PLAN_BASE_DIR']


def test_get_log_path_plan_scoped_decision():
    """Decision log path for existing plan."""
    with tempfile.TemporaryDirectory() as tmp:
        plan_base = Path(tmp)
        plan_dir = plan_base / 'plans' / 'my-plan'
        plan_dir.mkdir(parents=True)

        os.environ['PLAN_BASE_DIR'] = str(plan_base)
        try:
            path = module.get_log_path('my-plan', 'decision')
            assert path == plan_dir / 'logs' / 'decision.log'
        finally:
            del os.environ['PLAN_BASE_DIR']


def test_get_log_path_global_fallback():
    """Script log falls back to global when no plan."""
    with tempfile.TemporaryDirectory() as tmp:
        plan_base = Path(tmp)

        os.environ['PLAN_BASE_DIR'] = str(plan_base)
        try:
            path = module.get_log_path(None, 'script')
            assert path.parent == plan_base / 'logs'
            assert path.name.startswith('script-execution-')
            assert str(date.today()) in path.name
        finally:
            del os.environ['PLAN_BASE_DIR']


# =============================================================================
# TESTS: extract_plan_id
# =============================================================================


def test_extract_plan_id_with_space_separator():
    """Extract plan-id with --plan-id value format."""
    args = ['add', '--plan-id', 'my-plan', '--file', 'test.md']
    result = module.extract_plan_id(args)
    assert result == 'my-plan', f"Expected 'my-plan', got {result}"


def test_extract_plan_id_with_equals_separator():
    """Extract plan-id with --plan-id=value format."""
    args = ['add', '--plan-id=my-plan', '--file', 'test.md']
    result = module.extract_plan_id(args)
    assert result == 'my-plan', f"Expected 'my-plan', got {result}"


def test_extract_plan_id_missing():
    """Return None when --plan-id is not present."""
    args = ['add', '--file', 'test.md']
    result = module.extract_plan_id(args)
    assert result is None, f'Expected None, got {result}'


# =============================================================================
# TESTS: log_script_execution
# =============================================================================


def test_log_script_execution_success():
    """Success entry is written to log file."""
    with tempfile.TemporaryDirectory() as tmp:
        plan_base = Path(tmp)
        plan_dir = plan_base / 'plans' / 'test-plan'
        plan_dir.mkdir(parents=True)

        os.environ['PLAN_BASE_DIR'] = str(plan_base)
        try:
            module.log_script_execution(
                notation='test:skill:script',
                subcommand='add',
                args=['--plan-id', 'test-plan'],
                exit_code=0,
                duration=0.15,
            )

            log_file = plan_dir / 'logs' / 'script-execution.log'
            assert log_file.exists(), 'Log file not created'

            content = log_file.read_text()
            assert '[INFO]' in content
            assert 'test:skill:script add' in content
            assert '0.15s' in content
        finally:
            del os.environ['PLAN_BASE_DIR']


def test_log_script_execution_error_with_details():
    """Error entry includes exit_code, args, stderr."""
    with tempfile.TemporaryDirectory() as tmp:
        plan_base = Path(tmp)
        plan_dir = plan_base / 'plans' / 'test-plan'
        plan_dir.mkdir(parents=True)

        os.environ['PLAN_BASE_DIR'] = str(plan_base)
        try:
            module.log_script_execution(
                notation='test:skill:script',
                subcommand='add',
                args=['--plan-id', 'test-plan', '--file', 'missing.md'],
                exit_code=1,
                duration=0.23,
                stderr='FileNotFoundError: missing.md',
            )

            log_file = plan_dir / 'logs' / 'script-execution.log'
            content = log_file.read_text()
            assert '[ERROR]' in content
            assert 'exit_code: 1' in content
            assert 'args:' in content
            assert 'stderr:' in content
            assert 'FileNotFoundError' in content
        finally:
            del os.environ['PLAN_BASE_DIR']


# =============================================================================
# TESTS: cleanup_old_script_logs
# =============================================================================


def test_cleanup_deletes_old_logs():
    """Cleanup deletes logs older than max_age_days."""
    with tempfile.TemporaryDirectory() as tmp:
        plan_base = Path(tmp)
        log_dir = plan_base / 'logs'
        log_dir.mkdir()

        old_log = log_dir / 'script-execution-2020-01-01.log'
        old_log.write_text('old log')
        old_time = time.time() - (30 * 86400)
        os.utime(old_log, (old_time, old_time))

        os.environ['PLAN_BASE_DIR'] = str(plan_base)
        try:
            deleted = module.cleanup_old_script_logs(max_age_days=7)
            assert deleted == 1, f'Expected 1 deleted, got {deleted}'
            assert not old_log.exists(), 'Old log should be deleted'
        finally:
            del os.environ['PLAN_BASE_DIR']


def test_cleanup_preserves_recent_logs():
    """Cleanup preserves logs newer than max_age_days."""
    with tempfile.TemporaryDirectory() as tmp:
        plan_base = Path(tmp)
        log_dir = plan_base / 'logs'
        log_dir.mkdir()

        recent_log = log_dir / f'script-execution-{date.today()}.log'
        recent_log.write_text('recent log')

        os.environ['PLAN_BASE_DIR'] = str(plan_base)
        try:
            deleted = module.cleanup_old_script_logs(max_age_days=7)
            assert deleted == 0, f'Expected 0 deleted, got {deleted}'
            assert recent_log.exists(), 'Recent log should be preserved'
        finally:
            del os.environ['PLAN_BASE_DIR']


# =============================================================================
# TESTS: log_work
# =============================================================================


def test_log_work_default_category():
    """Log work with default PROGRESS category."""
    with tempfile.TemporaryDirectory() as tmp:
        plan_base = Path(tmp)
        plan_dir = plan_base / 'plans' / 'test-plan'
        plan_dir.mkdir(parents=True)

        os.environ['PLAN_BASE_DIR'] = str(plan_base)
        try:
            result = module.log_work(
                plan_id='test-plan', category='PROGRESS', message='Starting init phase', phase='init'
            )

            assert result['status'] == 'success'
            assert result['category'] == 'PROGRESS'
            assert result['total_entries'] == 1

            log_file = plan_dir / 'logs' / 'work.log'
            content = log_file.read_text()
            assert '[INFO]' in content
            assert '[PROGRESS]' in content
            assert 'Starting init phase' in content
            assert 'phase: init' in content
        finally:
            del os.environ['PLAN_BASE_DIR']


def test_log_work_all_categories():
    """Log work with each valid category."""
    # DECISION now goes to decision.log, not work.log
    categories = ['ARTIFACT', 'PROGRESS', 'ERROR', 'OUTCOME', 'FINDING']

    with tempfile.TemporaryDirectory() as tmp:
        plan_base = Path(tmp)
        plan_dir = plan_base / 'plans' / 'test-plan'
        plan_dir.mkdir(parents=True)

        os.environ['PLAN_BASE_DIR'] = str(plan_base)
        try:
            for cat in categories:
                result = module.log_work(plan_id='test-plan', category=cat, message=f'Test {cat}', phase='init')
                assert result['status'] == 'success', f'Failed for {cat}'
                assert result['category'] == cat

            log_file = plan_dir / 'logs' / 'work.log'
            content = log_file.read_text()
            for cat in categories:
                assert f'[{cat}]' in content, f'Missing {cat}'
        finally:
            del os.environ['PLAN_BASE_DIR']


def test_log_work_invalid_plan_id():
    """Log work fails for invalid plan_id."""
    result = module.log_work(plan_id='INVALID_ID', category='PROGRESS', message='Test', phase='init')
    assert result['status'] == 'error'
    assert result['error'] == 'invalid_plan_id'


def test_log_work_invalid_category():
    """Log work fails for invalid category."""
    with tempfile.TemporaryDirectory() as tmp:
        plan_base = Path(tmp)
        plan_dir = plan_base / 'plans' / 'test-plan'
        plan_dir.mkdir(parents=True)

        os.environ['PLAN_BASE_DIR'] = str(plan_base)
        try:
            result = module.log_work(plan_id='test-plan', category='INVALID', message='Test', phase='init')
            assert result['status'] == 'error'
            assert result['error'] == 'invalid_category'
        finally:
            del os.environ['PLAN_BASE_DIR']


# =============================================================================
# TESTS: read_work_log
# =============================================================================


def test_read_work_log_all_entries():
    """Read all work log entries."""
    with tempfile.TemporaryDirectory() as tmp:
        plan_base = Path(tmp)
        plan_dir = plan_base / 'plans' / 'test-plan'
        plan_dir.mkdir(parents=True)

        os.environ['PLAN_BASE_DIR'] = str(plan_base)
        try:
            # Add some entries (DECISION is now separate log)
            module.log_work('test-plan', 'PROGRESS', 'Entry 1', 'init')
            module.log_work('test-plan', 'OUTCOME', 'Entry 2', 'refine')
            module.log_work('test-plan', 'ARTIFACT', 'Entry 3', 'execute')

            result = module.read_work_log('test-plan')
            assert result['status'] == 'success'
            assert result['total_entries'] == 3
            assert len(result['entries']) == 3
            # Each entry should have hash_id
            for entry in result['entries']:
                assert 'hash_id' in entry, f'Missing hash_id in entry: {entry}'
                assert len(entry['hash_id']) == 6, f'Invalid hash_id: {entry["hash_id"]}'
        finally:
            del os.environ['PLAN_BASE_DIR']


def test_read_work_log_filtered_by_phase():
    """Read work log entries filtered by phase."""
    with tempfile.TemporaryDirectory() as tmp:
        plan_base = Path(tmp)
        plan_dir = plan_base / 'plans' / 'test-plan'
        plan_dir.mkdir(parents=True)

        os.environ['PLAN_BASE_DIR'] = str(plan_base)
        try:
            module.log_work('test-plan', 'PROGRESS', 'Init entry', 'init')
            module.log_work('test-plan', 'OUTCOME', 'Refine entry', 'refine')
            module.log_work('test-plan', 'PROGRESS', 'Another init', 'init')

            result = module.read_work_log('test-plan', phase='init')
            assert result['status'] == 'success'
            assert result['total_entries'] == 2
            for entry in result['entries']:
                assert entry['phase'] == 'init'
        finally:
            del os.environ['PLAN_BASE_DIR']


# =============================================================================
# TESTS: list_recent_work
# =============================================================================


def test_list_recent_work_with_limit():
    """List recent entries respects limit."""
    with tempfile.TemporaryDirectory() as tmp:
        plan_base = Path(tmp)
        plan_dir = plan_base / 'plans' / 'test-plan'
        plan_dir.mkdir(parents=True)

        os.environ['PLAN_BASE_DIR'] = str(plan_base)
        try:
            for i in range(5):
                module.log_work('test-plan', 'PROGRESS', f'Entry {i}', 'init')

            result = module.list_recent_work('test-plan', limit=3)
            assert result['status'] == 'success'
            assert result['total_entries'] == 5
            assert result['showing'] == 3
            assert len(result['entries']) == 3
            # Should be most recent
            assert 'Entry 4' in result['entries'][-1]['message']
        finally:
            del os.environ['PLAN_BASE_DIR']

#!/usr/bin/env python3
"""Tests for cleanup.py script (moved from marshall-steward)."""

import json
import os
import shutil
import sys
import time
from pathlib import Path

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import run_script, get_script_path, PlanContext

# Get script path (moved from marshall-steward to run-config)
SCRIPT_PATH = get_script_path('plan-marshall', 'run-config', 'cleanup.py')

# Default retention config for tests
DEFAULT_RETENTION = {
    "logs_days": 1,
    "archived_plans_days": 5,
    "memory_days": 5,
    "temp_on_maintenance": True
}


def clean_fixture_dirs(fixture_dir: Path):
    """Clean up directories that may leak between tests in shared fixture."""
    for subdir in ['temp', 'logs', 'archived-plans', 'memory']:
        path = fixture_dir / subdir
        if path.exists():
            shutil.rmtree(path)


def setup_marshal_json(fixture_dir: Path, retention: dict = None):
    """Create marshal.json with retention settings."""
    config = {
        "system": {
            "retention": retention or DEFAULT_RETENTION
        }
    }
    marshal_path = fixture_dir / 'marshal.json'
    marshal_path.write_text(json.dumps(config, indent=2))


def test_clean_temp():
    """Clean temp directory."""
    with PlanContext(plan_id='test-clean-temp') as ctx:
        setup_marshal_json(ctx.fixture_dir)

        temp_dir = ctx.fixture_dir / 'temp'
        temp_dir.mkdir(parents=True, exist_ok=True)

        # Create test files
        (temp_dir / 'file1.txt').write_text('content1')
        (temp_dir / 'file2.json').write_text('{"key": "value"}')
        subdir = temp_dir / 'subdir'
        subdir.mkdir(exist_ok=True)
        (subdir / 'nested.txt').write_text('nested content')

        result = run_script(SCRIPT_PATH, 'clean', '--target', 'temp')
        assert result.success, f"Script failed: {result.stderr}"
        assert 'status: success' in result.stdout
        assert 'temp_files: 3' in result.stdout

        # Verify files were deleted
        remaining = list(temp_dir.iterdir())
        assert len(remaining) == 0, f"Files remain: {remaining}"


def test_clean_logs():
    """Clean old log files."""
    with PlanContext(plan_id='test-clean-logs') as ctx:
        setup_marshal_json(ctx.fixture_dir)

        logs_dir = ctx.fixture_dir / 'logs'
        logs_dir.mkdir(parents=True, exist_ok=True)

        # Create log files - one old, one recent
        old_log = logs_dir / 'old.log'
        old_log.write_text('old log content')
        # Make it old (2 days ago)
        old_time = time.time() - (2 * 86400)
        os.utime(old_log, (old_time, old_time))

        recent_log = logs_dir / 'recent.log'
        recent_log.write_text('recent log content')

        result = run_script(SCRIPT_PATH, 'clean', '--target', 'logs')
        assert result.success, f"Script failed: {result.stderr}"
        assert 'status: success' in result.stdout
        assert 'logs_deleted: 1' in result.stdout

        # Verify old log deleted, recent kept
        assert not old_log.exists(), "Old log should be deleted"
        assert recent_log.exists(), "Recent log should be kept"


def test_clean_archived_plans():
    """Clean old archived plans."""
    with PlanContext(plan_id='test-clean-archived') as ctx:
        setup_marshal_json(ctx.fixture_dir)

        archived_dir = ctx.fixture_dir / 'archived-plans'
        archived_dir.mkdir(parents=True, exist_ok=True)

        # Create archived plans - one old, one recent
        old_plan = archived_dir / 'old-plan'
        old_plan.mkdir()
        (old_plan / 'config.toon').write_text('config')
        (old_plan / 'plan.md').write_text('plan')
        # Make it old (6 days ago)
        old_time = time.time() - (6 * 86400)
        os.utime(old_plan, (old_time, old_time))

        recent_plan = archived_dir / 'recent-plan'
        recent_plan.mkdir()
        (recent_plan / 'config.toon').write_text('config')

        result = run_script(SCRIPT_PATH, 'clean', '--target', 'archived-plans')
        assert result.success, f"Script failed: {result.stderr}"
        assert 'status: success' in result.stdout
        assert 'archived_plans_deleted: 1' in result.stdout

        # Verify old plan deleted, recent kept
        assert not old_plan.exists(), "Old plan should be deleted"
        assert recent_plan.exists(), "Recent plan should be kept"


def test_clean_memory():
    """Clean old memory files."""
    with PlanContext(plan_id='test-clean-memory') as ctx:
        setup_marshal_json(ctx.fixture_dir)

        memory_dir = ctx.fixture_dir / 'memory' / 'handoffs'
        memory_dir.mkdir(parents=True, exist_ok=True)

        # Create memory files - one old, one recent
        old_file = memory_dir / 'old-handoff.toon'
        old_file.write_text('old memory')
        # Make it old (6 days ago)
        old_time = time.time() - (6 * 86400)
        os.utime(old_file, (old_time, old_time))

        recent_file = memory_dir / 'recent-handoff.toon'
        recent_file.write_text('recent memory')

        result = run_script(SCRIPT_PATH, 'clean', '--target', 'memory')
        assert result.success, f"Script failed: {result.stderr}"
        assert 'status: success' in result.stdout
        assert 'memory_files_deleted: 1' in result.stdout

        # Verify old file deleted, recent kept
        assert not old_file.exists(), "Old memory file should be deleted"
        assert recent_file.exists(), "Recent memory file should be kept"


def test_clean_all():
    """Clean all directories."""
    with PlanContext(plan_id='test-clean-all') as ctx:
        setup_marshal_json(ctx.fixture_dir)

        # Create temp
        temp_dir = ctx.fixture_dir / 'temp'
        temp_dir.mkdir(parents=True, exist_ok=True)
        (temp_dir / 'temp.txt').write_text('temp')

        # Create old log
        logs_dir = ctx.fixture_dir / 'logs'
        logs_dir.mkdir(parents=True, exist_ok=True)
        old_log = logs_dir / 'old.log'
        old_log.write_text('old')
        old_time = time.time() - (2 * 86400)
        os.utime(old_log, (old_time, old_time))

        result = run_script(SCRIPT_PATH, 'clean', '--target', 'all')
        assert result.success, f"Script failed: {result.stderr}"
        assert 'status: success' in result.stdout
        assert 'temp_files: 1' in result.stdout
        assert 'logs_deleted: 1' in result.stdout


def test_clean_dry_run():
    """Dry run shows what would be deleted without deleting."""
    with PlanContext(plan_id='test-dry-run') as ctx:
        setup_marshal_json(ctx.fixture_dir)

        temp_dir = ctx.fixture_dir / 'temp'
        temp_dir.mkdir(parents=True, exist_ok=True)

        test_file = temp_dir / 'keep-me.txt'
        test_file.write_text('should not be deleted')

        result = run_script(SCRIPT_PATH, 'clean', '--dry-run', '--target', 'temp')
        assert result.success, f"Script failed: {result.stderr}"
        assert 'status: dry_run' in result.stdout
        assert 'temp_files: 1' in result.stdout

        # Verify file was NOT deleted
        assert test_file.exists(), "File should not be deleted in dry-run mode"


def test_status():
    """Status command shows directory statistics."""
    with PlanContext(plan_id='test-status') as ctx:
        clean_fixture_dirs(ctx.fixture_dir)  # Ensure clean state
        setup_marshal_json(ctx.fixture_dir)

        # Create temp files
        temp_dir = ctx.fixture_dir / 'temp'
        temp_dir.mkdir(parents=True, exist_ok=True)
        (temp_dir / 'file1.txt').write_text('12345')

        # Create log
        logs_dir = ctx.fixture_dir / 'logs'
        logs_dir.mkdir(parents=True, exist_ok=True)
        (logs_dir / 'test.log').write_text('log')

        result = run_script(SCRIPT_PATH, 'status')
        assert result.success, f"Script failed: {result.stderr}"
        assert 'status: ok' in result.stdout
        assert 'temp_files: 1' in result.stdout
        assert 'logs_total: 1' in result.stdout


def test_clean_nonexistent():
    """Clean on nonexistent directory succeeds with zero counts."""
    with PlanContext(plan_id='test-nonexistent') as ctx:
        clean_fixture_dirs(ctx.fixture_dir)  # Ensure clean state
        setup_marshal_json(ctx.fixture_dir)

        # The fixture_dir exists but temp/logs/etc don't
        result = run_script(SCRIPT_PATH, 'clean', '--target', 'all')
        assert result.success, "Should succeed even if directories don't exist"
        assert 'status: success' in result.stdout
        assert 'temp_files: 0' in result.stdout


def test_missing_marshal_json():
    """Script fails loudly when marshal.json is missing."""
    with PlanContext(plan_id='test-missing-marshal') as ctx:
        # Ensure no marshal.json exists (may persist from other tests)
        marshal_path = ctx.fixture_dir / 'marshal.json'
        if marshal_path.exists():
            marshal_path.unlink()

        result = run_script(SCRIPT_PATH, 'clean', '--target', 'all')
        assert not result.success, "Should fail without marshal.json"
        assert 'error' in result.stdout.lower()
        assert 'marshal.json not found' in result.stdout


def test_missing_retention_config():
    """Script fails loudly when retention config is missing."""
    with PlanContext(plan_id='test-missing-retention') as ctx:
        # Create marshal.json without system.retention section
        marshal_path = ctx.fixture_dir / 'marshal.json'
        marshal_path.write_text(json.dumps({"other": "config"}))

        result = run_script(SCRIPT_PATH, 'clean', '--target', 'all')
        assert not result.success, "Should fail without retention config"
        assert 'error' in result.stdout.lower()
        assert 'system.retention' in result.stdout.lower()


def test_missing_subcommand():
    """Missing required subcommand fails."""
    result = run_script(SCRIPT_PATH)
    assert not result.success, "Should fail without subcommand"
    assert 'required' in result.stderr.lower() or 'error' in result.stderr.lower()

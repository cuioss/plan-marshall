#!/usr/bin/env python3
"""Tests for manage-files.py script."""

import importlib.util
import json
import os
import shutil
from argparse import Namespace
from pathlib import Path

import pytest

from conftest import PlanContext, get_script_path, get_test_fixture_dir, run_script

# Script path for remaining subprocess (CLI plumbing) tests
SCRIPT_PATH = get_script_path('plan-marshall', 'manage-files', 'manage-files.py')

# Tier 2 direct imports - load hyphenated module via importlib
_MANAGE_FILES_SCRIPT = str(
    Path(__file__).parent.parent.parent.parent
    / 'marketplace' / 'bundles' / 'plan-marshall' / 'skills' / 'manage-files' / 'scripts' / 'manage-files.py'
)
_spec = importlib.util.spec_from_file_location('manage_files', _MANAGE_FILES_SCRIPT)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

cmd_read = _mod.cmd_read
cmd_write = _mod.cmd_write
cmd_remove = _mod.cmd_remove
cmd_list = _mod.cmd_list
cmd_exists = _mod.cmd_exists
cmd_mkdir = _mod.cmd_mkdir
cmd_create_or_reference = _mod.cmd_create_or_reference


# =============================================================================
# Helper: EmptyPlanContext (no pre-created plan directory)
# =============================================================================


class EmptyPlanContext:
    """Context manager for test WITHOUT pre-created plan directory."""

    __test__ = False  # Not a test class - prevent pytest collection warning

    def __init__(self):
        self.fixture_dir = None
        self._original_plan_base_dir = None
        self._original_plan_dir_name = None
        self._is_standalone = False

    def __enter__(self):
        self.fixture_dir = get_test_fixture_dir()
        self._is_standalone = 'TEST_FIXTURE_DIR' not in os.environ

        self._original_plan_base_dir = os.environ.get('PLAN_BASE_DIR')
        self._original_plan_dir_name = os.environ.get('PLAN_DIR_NAME')
        os.environ['PLAN_BASE_DIR'] = str(self.fixture_dir)
        os.environ['PLAN_DIR_NAME'] = '.plan'
        # Create plans directory but NOT the plan subdirectory
        (self.fixture_dir / 'plans').mkdir(parents=True, exist_ok=True)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._original_plan_base_dir is None:
            os.environ.pop('PLAN_BASE_DIR', None)
        else:
            os.environ['PLAN_BASE_DIR'] = self._original_plan_base_dir

        if self._original_plan_dir_name is None:
            os.environ.pop('PLAN_DIR_NAME', None)
        else:
            os.environ['PLAN_DIR_NAME'] = self._original_plan_dir_name

        # Only cleanup if running standalone
        if self._is_standalone and self.fixture_dir and self.fixture_dir.exists():
            shutil.rmtree(self.fixture_dir, ignore_errors=True)

    @property
    def temp_dir(self):
        """Return the fixture directory."""
        return self.fixture_dir

    def plan_dir(self, plan_id):
        return self.fixture_dir / 'plans' / plan_id


# =============================================================================
# Test: Write and Read
# =============================================================================


def test_write_file():
    """Test writing a file."""
    with PlanContext(plan_id='file-write') as ctx:
        result = cmd_write(
            Namespace(plan_id='file-write', file='task.md', content='# Task\nDo something', stdin=False)
        )
        assert result['status'] == 'success'
        assert result['action'] == 'created'
        assert result['file'] == 'task.md'
        # Verify file was created
        assert (ctx.plan_dir / 'task.md').exists()
        assert (ctx.plan_dir / 'task.md').read_text().rstrip('\n') == '# Task\nDo something'


def test_read_file(capsys):
    """Test reading a file (cmd_read prints content and returns None)."""
    with PlanContext(plan_id='file-read') as ctx:
        (ctx.plan_dir / 'test.md').write_text('Test content')

        result = cmd_read(Namespace(plan_id='file-read', file='test.md'))
        assert result is None  # cmd_read prints directly, returns None
        captured = capsys.readouterr()
        assert 'Test content' in captured.out


def test_read_nonexistent_file():
    """Test reading a file that doesn't exist."""
    with PlanContext(plan_id='file-noexist'):
        result = cmd_read(Namespace(plan_id='file-noexist', file='missing.md'))
        assert result['status'] == 'error'
        assert result['error'] == 'file_not_found'


# =============================================================================
# Test: List and Exists
# =============================================================================


def test_list_empty():
    """Test listing files in empty plan."""
    with PlanContext(plan_id='file-list-empty'):
        result = cmd_list(Namespace(plan_id='file-list-empty', dir=None))
        assert result['status'] == 'success'
        assert result['files'] == []


def test_list_with_files():
    """Test listing files."""
    with PlanContext(plan_id='file-list') as ctx:
        # Create some files
        (ctx.plan_dir / 'references.json').write_text('{"branch": "main"}')
        (ctx.plan_dir / 'task.md').write_text('Task')

        result = cmd_list(Namespace(plan_id='file-list', dir=None))
        assert result['status'] == 'success'
        assert 'task.md' in result['files']
        assert 'references.json' in result['files']


def test_exists_present():
    """Test checking if file exists (present)."""
    with PlanContext(plan_id='file-exists') as ctx:
        (ctx.plan_dir / 'test.md').write_text('Test')

        result = cmd_exists(Namespace(plan_id='file-exists', file='test.md'))
        assert result['status'] == 'success'
        assert result['exists'] is True
        assert result['plan_id'] == 'file-exists'
        assert result['file'] == 'test.md'
        assert 'path' in result


def test_exists_absent():
    """Test checking if file exists (absent)."""
    with PlanContext(plan_id='file-absent'):
        result = cmd_exists(Namespace(plan_id='file-absent', file='missing.md'))
        assert result['status'] == 'success'
        assert result['exists'] is False
        assert result['plan_id'] == 'file-absent'
        assert result['file'] == 'missing.md'


def test_exists_invalid_plan_id():
    """Test exists with invalid plan ID exits via sys.exit(1)."""
    with PlanContext():
        with pytest.raises(SystemExit) as exc_info:
            cmd_exists(Namespace(plan_id='Invalid_Plan', file='test.md'))
        assert exc_info.value.code == 0


def test_exists_invalid_file_path():
    """Test exists with invalid file path returns error dict."""
    with PlanContext(plan_id='file-exists'):
        result = cmd_exists(Namespace(plan_id='file-exists', file='../escape.md'))
        assert result['status'] == 'error'
        assert result['error'] == 'invalid_path'


# =============================================================================
# Test: Remove and Mkdir
# =============================================================================


def test_remove_file():
    """Test removing a file."""
    with PlanContext(plan_id='file-remove') as ctx:
        (ctx.plan_dir / 'delete-me.md').write_text('Goodbye')

        result = cmd_remove(Namespace(plan_id='file-remove', file='delete-me.md'))
        assert result['status'] == 'success'
        assert result['action'] == 'removed'
        assert not (ctx.plan_dir / 'delete-me.md').exists()


def test_remove_nonexistent_file():
    """Test removing a file that doesn't exist."""
    with PlanContext(plan_id='file-remove-missing'):
        result = cmd_remove(Namespace(plan_id='file-remove-missing', file='ghost.md'))
        assert result['status'] == 'error'
        assert result['error'] == 'file_not_found'


def test_mkdir():
    """Test creating a directory."""
    with PlanContext(plan_id='file-mkdir') as ctx:
        result = cmd_mkdir(Namespace(plan_id='file-mkdir', dir='requirements'))
        assert result['status'] == 'success'
        assert result['action'] == 'created'
        assert (ctx.plan_dir / 'requirements').is_dir()


def test_mkdir_already_exists():
    """Test creating a directory that already exists."""
    with PlanContext(plan_id='file-mkdir-exists') as ctx:
        (ctx.plan_dir / 'existing').mkdir()
        result = cmd_mkdir(Namespace(plan_id='file-mkdir-exists', dir='existing'))
        assert result['status'] == 'success'
        assert result['action'] == 'exists'


# =============================================================================
# Test: Create-or-Reference
# =============================================================================


def test_create_or_reference_new_plan():
    """Test create-or-reference creates new plan directory."""
    with EmptyPlanContext() as ctx:
        result = cmd_create_or_reference(Namespace(plan_id='new-plan'))
        assert result['status'] == 'success'
        assert result['action'] == 'created'
        assert result['plan_id'] == 'new-plan'
        # Verify directory was created
        assert ctx.plan_dir('new-plan').exists()


def test_create_or_reference_existing_plan():
    """Test create-or-reference returns exists for existing plan."""
    with PlanContext(plan_id='existing-plan'):
        result = cmd_create_or_reference(Namespace(plan_id='existing-plan'))
        assert result['status'] == 'success'
        assert result['action'] == 'exists'
        assert result['plan_id'] == 'existing-plan'


def test_create_or_reference_existing_with_status():
    """Test create-or-reference returns phase info when status.json exists."""
    with PlanContext(plan_id='status-plan') as ctx:
        # Create status.json with phase info (domain is in references.json, not status.json)
        status_content = json.dumps({'title': 'Test Plan', 'current_phase': 'outline'})
        (ctx.plan_dir / 'status.json').write_text(status_content)

        result = cmd_create_or_reference(Namespace(plan_id='status-plan'))
        assert result['status'] == 'success'
        assert result['action'] == 'exists'
        assert result['current_phase'] == 'outline'
        # Domain should NOT be in output (stored in references.json, not status.toon)
        assert 'domain' not in result


def test_create_or_reference_invalid_plan_id():
    """Test create-or-reference rejects invalid plan IDs (sys.exit(1))."""
    with EmptyPlanContext():
        with pytest.raises(SystemExit) as exc_info:
            cmd_create_or_reference(Namespace(plan_id='Invalid_Plan'))
        assert exc_info.value.code == 0


# =============================================================================
# Test: Invalid Plan IDs (direct import)
# =============================================================================


def test_invalid_plan_id_uppercase():
    """Test that uppercase plan IDs are rejected."""
    with PlanContext():
        with pytest.raises(SystemExit) as exc_info:
            cmd_list(Namespace(plan_id='My-Plan', dir=None))
        assert exc_info.value.code == 0


def test_invalid_plan_id_underscore():
    """Test that underscore in plan IDs are rejected."""
    with PlanContext():
        with pytest.raises(SystemExit) as exc_info:
            cmd_list(Namespace(plan_id='my_plan', dir=None))
        assert exc_info.value.code == 0


# =============================================================================
# Test: Write edge cases
# =============================================================================


def test_write_missing_content():
    """Test write fails when neither --content nor --stdin provided."""
    with PlanContext(plan_id='file-write-no-content'):
        result = cmd_write(Namespace(plan_id='file-write-no-content', file='test.md', content=None, stdin=False))
        assert result['status'] == 'error'
        assert result['error'] == 'missing_content'


def test_write_invalid_path():
    """Test write rejects path traversal."""
    with PlanContext(plan_id='file-write-escape'):
        result = cmd_write(
            Namespace(plan_id='file-write-escape', file='../escape.md', content='bad', stdin=False)
        )
        assert result['status'] == 'error'
        assert result['error'] == 'invalid_path'


# =============================================================================
# CLI Plumbing Tests (Tier 3 - subprocess)
# =============================================================================


def test_cli_missing_required_args():
    """Test that missing required args produces exit code 2 (argparse error)."""
    with PlanContext():
        result = run_script(SCRIPT_PATH, 'write', '--plan-id', 'test-plan')
        # argparse exits with code 2 for missing required args (--file)
        assert not result.success


def test_cli_help_flag():
    """Test that --help produces exit code 0."""
    with PlanContext():
        result = run_script(SCRIPT_PATH, '--help')
        assert result.success


def test_cli_subcommand_help():
    """Test that subcommand --help produces exit code 0."""
    with PlanContext():
        result = run_script(SCRIPT_PATH, 'write', '--help')
        assert result.success

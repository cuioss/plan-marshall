#!/usr/bin/env python3
"""Tests for manage-files.py script."""

import os
import shutil
import sys
from pathlib import Path

# Import shared infrastructure
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from conftest import PlanContext, get_script_path, get_test_fixture_dir, run_script

# Get script path
SCRIPT_PATH = get_script_path('pm-workflow', 'manage-files', 'manage-files.py')

# Import toon_parser - conftest sets up PYTHONPATH
from toon_parser import parse_toon  # type: ignore[import-not-found]

# Alias for backward compatibility
TestContext = PlanContext


# =============================================================================
# Test: Write and Read
# =============================================================================

def test_write_file():
    """Test writing a file."""
    with TestContext(plan_id='file-write') as ctx:
        result = run_script(SCRIPT_PATH, 'write',
            '--plan-id', 'file-write',
            '--file', 'task.md',
            '--content', '# Task\nDo something'
        )
        assert result.success, f"Script failed: {result.stderr}"
        # Verify file was created
        assert (ctx.plan_dir / 'task.md').exists()


def test_read_file():
    """Test reading a file."""
    with TestContext(plan_id='file-read') as ctx:
        # Create file first
        (ctx.plan_dir / 'test.md').write_text('Test content')

        result = run_script(SCRIPT_PATH, 'read',
            '--plan-id', 'file-read',
            '--file', 'test.md'
        )
        assert result.success, f"Script failed: {result.stderr}"


def test_read_nonexistent_file():
    """Test reading a file that doesn't exist."""
    with TestContext(plan_id='file-noexist'):
        result = run_script(SCRIPT_PATH, 'read',
            '--plan-id', 'file-noexist',
            '--file', 'missing.md'
        )
        assert not result.success, "Expected failure for missing file"


# =============================================================================
# Test: List and Exists
# =============================================================================

def test_list_empty():
    """Test listing files in empty plan."""
    with TestContext(plan_id='file-list-empty'):
        result = run_script(SCRIPT_PATH, 'list',
            '--plan-id', 'file-list-empty'
        )
        assert result.success, f"Script failed: {result.stderr}"


def test_list_with_files():
    """Test listing files."""
    with TestContext(plan_id='file-list') as ctx:
        # Create some files
        (ctx.plan_dir / 'task.md').write_text('Task')
        (ctx.plan_dir / 'config.toon').write_text('plan_type: simple')

        result = run_script(SCRIPT_PATH, 'list',
            '--plan-id', 'file-list'
        )
        assert result.success, f"Script failed: {result.stderr}"


def test_exists_present():
    """Test checking if file exists (present)."""
    with TestContext(plan_id='file-exists') as ctx:
        (ctx.plan_dir / 'test.md').write_text('Test')

        result = run_script(SCRIPT_PATH, 'exists',
            '--plan-id', 'file-exists',
            '--file', 'test.md'
        )
        assert result.success, f"Script failed: {result.stderr}"
        # Output should indicate file exists
        assert 'true' in result.stdout.lower() or result.returncode == 0


def test_exists_absent():
    """Test checking if file exists (absent)."""
    with TestContext(plan_id='file-absent'):
        result = run_script(SCRIPT_PATH, 'exists',
            '--plan-id', 'file-absent',
            '--file', 'missing.md'
        )
        # Script returns exit code 1 when file doesn't exist
        assert not result.success, "Expected exit code 1 for missing file"


# =============================================================================
# Test: Remove and Mkdir
# =============================================================================

def test_remove_file():
    """Test removing a file."""
    with TestContext(plan_id='file-remove') as ctx:
        (ctx.plan_dir / 'delete-me.md').write_text('Goodbye')

        result = run_script(SCRIPT_PATH, 'remove',
            '--plan-id', 'file-remove',
            '--file', 'delete-me.md'
        )
        assert result.success, f"Script failed: {result.stderr}"
        assert not (ctx.plan_dir / 'delete-me.md').exists()


def test_mkdir():
    """Test creating a directory."""
    with TestContext(plan_id='file-mkdir') as ctx:
        result = run_script(SCRIPT_PATH, 'mkdir',
            '--plan-id', 'file-mkdir',
            '--dir', 'requirements'
        )
        assert result.success, f"Script failed: {result.stderr}"
        assert (ctx.plan_dir / 'requirements').is_dir()


# =============================================================================
# Test: Create-or-Reference
# =============================================================================

class EmptyPlanContext:
    """Context manager for test WITHOUT pre-created plan directory."""

    def __init__(self):
        self.fixture_dir = None
        self._original_plan_base_dir = None
        self._is_standalone = False

    def __enter__(self):
        self.fixture_dir = get_test_fixture_dir()
        self._is_standalone = 'TEST_FIXTURE_DIR' not in os.environ

        self._original_plan_base_dir = os.environ.get('PLAN_BASE_DIR')
        os.environ['PLAN_BASE_DIR'] = str(self.fixture_dir)
        # Create plans directory but NOT the plan subdirectory
        (self.fixture_dir / 'plans').mkdir(parents=True, exist_ok=True)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._original_plan_base_dir is None:
            os.environ.pop('PLAN_BASE_DIR', None)
        else:
            os.environ['PLAN_BASE_DIR'] = self._original_plan_base_dir

        # Only cleanup if running standalone
        if self._is_standalone and self.fixture_dir and self.fixture_dir.exists():
            shutil.rmtree(self.fixture_dir, ignore_errors=True)

    @property
    def temp_dir(self):
        """Alias for backward compatibility."""
        return self.fixture_dir

    def plan_dir(self, plan_id):
        return self.fixture_dir / 'plans' / plan_id


def test_create_or_reference_new_plan():
    """Test create-or-reference creates new plan directory."""
    with EmptyPlanContext() as ctx:
        result = run_script(SCRIPT_PATH, 'create-or-reference',
            '--plan-id', 'new-plan'
        )
        assert result.success, f"Script failed: {result.stderr}"
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert data['action'] == 'created'
        assert data['plan_id'] == 'new-plan'
        # Verify directory was created
        assert ctx.plan_dir('new-plan').exists()


def test_create_or_reference_existing_plan():
    """Test create-or-reference returns exists for existing plan."""
    with TestContext(plan_id='existing-plan'):
        result = run_script(SCRIPT_PATH, 'create-or-reference',
            '--plan-id', 'existing-plan'
        )
        assert result.success, f"Script failed: {result.stderr}"
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert data['action'] == 'exists'
        assert data['plan_id'] == 'existing-plan'


def test_create_or_reference_existing_with_status():
    """Test create-or-reference returns phase info when status.toon exists."""
    with TestContext(plan_id='status-plan') as ctx:
        # Create status.toon with phase info (domain is in config.toon, not status.toon)
        status_content = """title: Test Plan
current_phase: outline
"""
        (ctx.plan_dir / 'status.toon').write_text(status_content)

        result = run_script(SCRIPT_PATH, 'create-or-reference',
            '--plan-id', 'status-plan'
        )
        assert result.success, f"Script failed: {result.stderr}"
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert data['action'] == 'exists'
        assert data['current_phase'] == 'outline'
        # Domain should NOT be in output (stored in config.toon, not status.toon)
        assert 'domain' not in data


def test_create_or_reference_invalid_plan_id():
    """Test create-or-reference rejects invalid plan IDs."""
    with EmptyPlanContext():
        result = run_script(SCRIPT_PATH, 'create-or-reference',
            '--plan-id', 'Invalid_Plan'
        )
        assert not result.success, "Expected failure for invalid plan ID"
        data = parse_toon(result.stdout)
        assert data['status'] == 'error'
        assert data['error'] == 'invalid_plan_id'


# =============================================================================
# Test: Delete Plan
# =============================================================================

def test_delete_plan_success():
    """Test deleting an existing plan directory."""
    with TestContext(plan_id='delete-test') as ctx:
        # Create some files in the plan
        (ctx.plan_dir / 'request.md').write_text('# Request')
        (ctx.plan_dir / 'config.toon').write_text('plan_type: test')
        (ctx.plan_dir / 'tasks').mkdir()
        (ctx.plan_dir / 'tasks' / 'TASK-001.toon').write_text('title: Test')

        result = run_script(SCRIPT_PATH, 'delete-plan',
            '--plan-id', 'delete-test'
        )
        assert result.success, f"Script failed: {result.stderr}"
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert data['action'] == 'deleted'
        assert data['plan_id'] == 'delete-test'
        assert data['files_removed'] == 3  # request.md, config.toon, TASK-001.toon
        # Verify directory was deleted
        assert not ctx.plan_dir.exists()


def test_delete_plan_not_found():
    """Test deleting a plan that doesn't exist."""
    with EmptyPlanContext() as ctx:
        result = run_script(SCRIPT_PATH, 'delete-plan',
            '--plan-id', 'nonexistent-plan'
        )
        assert not result.success, "Expected failure for nonexistent plan"
        data = parse_toon(result.stdout)
        assert data['status'] == 'error'
        assert data['error'] == 'plan_not_found'


def test_delete_plan_invalid_id():
    """Test delete-plan rejects invalid plan IDs."""
    with EmptyPlanContext():
        result = run_script(SCRIPT_PATH, 'delete-plan',
            '--plan-id', 'Invalid_Plan'
        )
        assert not result.success, "Expected failure for invalid plan ID"
        data = parse_toon(result.stdout)
        assert data['status'] == 'error'
        assert data['error'] == 'invalid_plan_id'


# =============================================================================
# Test: Invalid Plan IDs
# =============================================================================

def test_invalid_plan_id_uppercase():
    """Test that uppercase plan IDs are rejected."""
    with TestContext():
        result = run_script(SCRIPT_PATH, 'list',
            '--plan-id', 'My-Plan'
        )
        assert not result.success, "Expected failure for uppercase plan ID"


def test_invalid_plan_id_underscore():
    """Test that underscore in plan IDs are rejected."""
    with TestContext():
        result = run_script(SCRIPT_PATH, 'list',
            '--plan-id', 'my_plan'
        )
        assert not result.success, "Expected failure for underscore in plan ID"

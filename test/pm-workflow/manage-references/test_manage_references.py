#!/usr/bin/env python3
"""Tests for manage-references.py script."""

import sys
from pathlib import Path

# Import shared infrastructure
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from conftest import run_script, TestRunner, get_script_path, PlanTestContext

# Get script path
SCRIPT_PATH = get_script_path('pm-workflow', 'manage-references', 'manage-references.py')

# Import toon_parser - conftest sets up PYTHONPATH
from toon_parser import parse_toon  # type: ignore[import-not-found]


# Alias for backward compatibility
TestContext = PlanTestContext


# =============================================================================
# Test: Create Command
# =============================================================================

def test_create_references():
    """Test creating references.toon."""
    with TestContext():
        result = run_script(SCRIPT_PATH, 'create',
            '--plan-id', 'test-plan',
            '--branch', 'feature/test'
        )
        assert result.success, f"Script failed: {result.stderr}"
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert data['created'] == True


def test_create_with_issue_url():
    """Test creating references with issue URL."""
    with TestContext():
        result = run_script(SCRIPT_PATH, 'create',
            '--plan-id', 'test-plan',
            '--branch', 'feature/test',
            '--issue-url', 'https://github.com/org/repo/issues/123'
        )
        assert result.success, f"Script failed: {result.stderr}"


# =============================================================================
# Test: Read Command
# =============================================================================

def test_read_references():
    """Test reading references.toon."""
    with TestContext():
        run_script(SCRIPT_PATH, 'create',
            '--plan-id', 'test-plan',
            '--branch', 'feature/test'
        )
        result = run_script(SCRIPT_PATH, 'read',
            '--plan-id', 'test-plan'
        )
        assert result.success, f"Script failed: {result.stderr}"
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'


# =============================================================================
# Test: Get/Set Commands
# =============================================================================

def test_get_field():
    """Test getting a specific field."""
    with TestContext():
        run_script(SCRIPT_PATH, 'create',
            '--plan-id', 'test-plan',
            '--branch', 'feature/test'
        )
        result = run_script(SCRIPT_PATH, 'get',
            '--plan-id', 'test-plan',
            '--field', 'branch'
        )
        assert result.success, f"Script failed: {result.stderr}"
        data = parse_toon(result.stdout)
        assert data['value'] == 'feature/test'


def test_set_field():
    """Test setting a specific field."""
    with TestContext():
        run_script(SCRIPT_PATH, 'create',
            '--plan-id', 'test-plan',
            '--branch', 'feature/test'
        )
        result = run_script(SCRIPT_PATH, 'set',
            '--plan-id', 'test-plan',
            '--field', 'branch',
            '--value', 'feature/new-branch'
        )
        assert result.success, f"Script failed: {result.stderr}"
        data = parse_toon(result.stdout)
        assert data['value'] == 'feature/new-branch'


# =============================================================================
# Test: Add/Remove File Commands
# =============================================================================

def test_add_file():
    """Test adding a file to modified_files."""
    with TestContext():
        run_script(SCRIPT_PATH, 'create',
            '--plan-id', 'test-plan',
            '--branch', 'feature/test'
        )
        result = run_script(SCRIPT_PATH, 'add-file',
            '--plan-id', 'test-plan',
            '--file', 'src/Main.java'
        )
        assert result.success, f"Script failed: {result.stderr}"
        data = parse_toon(result.stdout)
        assert data['added'] == 'src/Main.java'
        assert data['total'] == 1


# =============================================================================
# Test: Get Context (NEW OPTIMIZATION)
# =============================================================================

def test_get_context():
    """Test get-context returns all relevant references in one call."""
    with TestContext():
        run_script(SCRIPT_PATH, 'create',
            '--plan-id', 'test-plan',
            '--branch', 'feature/test',
            '--issue-url', 'https://github.com/org/repo/issues/123',
            '--build-system', 'maven'
        )
        run_script(SCRIPT_PATH, 'add-file',
            '--plan-id', 'test-plan',
            '--file', 'src/Main.java'
        )
        run_script(SCRIPT_PATH, 'add-file',
            '--plan-id', 'test-plan',
            '--file', 'src/Test.java'
        )

        result = run_script(SCRIPT_PATH, 'get-context',
            '--plan-id', 'test-plan'
        )
        assert result.success, f"Script failed: {result.stderr}"
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        # Should have branch info
        assert data['branch'] == 'feature/test'
        assert data['base_branch'] == 'main'
        # Should have issue URL
        assert data['issue_url'] == 'https://github.com/org/repo/issues/123'
        # Should have build system
        assert data['build_system'] == 'maven'
        # Should have file counts
        assert data['modified_files_count'] == 2


def test_get_context_empty():
    """Test get-context with minimal references."""
    with TestContext():
        run_script(SCRIPT_PATH, 'create',
            '--plan-id', 'test-plan',
            '--branch', 'feature/test'
        )
        result = run_script(SCRIPT_PATH, 'get-context',
            '--plan-id', 'test-plan'
        )
        assert result.success, f"Script failed: {result.stderr}"
        data = parse_toon(result.stdout)
        assert data['modified_files_count'] == 0


def test_get_context_not_found():
    """Test get-context with missing plan."""
    with TestContext():
        result = run_script(SCRIPT_PATH, 'get-context',
            '--plan-id', 'nonexistent'
        )
        assert not result.success, "Expected failure for missing plan"


# =============================================================================
# Test Runner
# =============================================================================

if __name__ == '__main__':
    runner = TestRunner()
    runner.add_tests([
        # Create command
        test_create_references,
        test_create_with_issue_url,
        # Read command
        test_read_references,
        # Get/Set commands
        test_get_field,
        test_set_field,
        # Add file command
        test_add_file,
        # Get context (optimization)
        test_get_context,
        test_get_context_empty,
        test_get_context_not_found,
    ])
    sys.exit(runner.run())

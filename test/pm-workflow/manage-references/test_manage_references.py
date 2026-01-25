#!/usr/bin/env python3
"""Tests for manage-references.py script."""

import sys
from pathlib import Path

# Import shared infrastructure
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from conftest import PlanContext, get_script_path, run_script

# Get script path
SCRIPT_PATH = get_script_path('pm-workflow', 'manage-references', 'manage-references.py')

# Import toon_parser - conftest sets up PYTHONPATH
from toon_parser import parse_toon  # type: ignore[import-not-found]  # noqa: E402

# Alias for backward compatibility
TestContext = PlanContext


# =============================================================================
# Test: Create Command
# =============================================================================


def test_create_references():
    """Test creating references.toon."""
    with TestContext():
        result = run_script(SCRIPT_PATH, 'create', '--plan-id', 'test-plan', '--branch', 'feature/test')
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert data['created'] is True


def test_create_with_issue_url():
    """Test creating references with issue URL."""
    with TestContext():
        result = run_script(
            SCRIPT_PATH,
            'create',
            '--plan-id',
            'test-plan',
            '--branch',
            'feature/test',
            '--issue-url',
            'https://github.com/org/repo/issues/123',
        )
        assert result.success, f'Script failed: {result.stderr}'


# =============================================================================
# Test: Read Command
# =============================================================================


def test_read_references():
    """Test reading references.toon."""
    with TestContext():
        run_script(SCRIPT_PATH, 'create', '--plan-id', 'test-plan', '--branch', 'feature/test')
        result = run_script(SCRIPT_PATH, 'read', '--plan-id', 'test-plan')
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'


# =============================================================================
# Test: Get/Set Commands
# =============================================================================


def test_get_field():
    """Test getting a specific field."""
    with TestContext():
        run_script(SCRIPT_PATH, 'create', '--plan-id', 'test-plan', '--branch', 'feature/test')
        result = run_script(SCRIPT_PATH, 'get', '--plan-id', 'test-plan', '--field', 'branch')
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['value'] == 'feature/test'


def test_set_field():
    """Test setting a specific field."""
    with TestContext():
        run_script(SCRIPT_PATH, 'create', '--plan-id', 'test-plan', '--branch', 'feature/test')
        result = run_script(
            SCRIPT_PATH, 'set', '--plan-id', 'test-plan', '--field', 'branch', '--value', 'feature/new-branch'
        )
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['value'] == 'feature/new-branch'


# =============================================================================
# Test: Add/Remove File Commands
# =============================================================================


def test_add_file():
    """Test adding a file to modified_files."""
    with TestContext():
        run_script(SCRIPT_PATH, 'create', '--plan-id', 'test-plan', '--branch', 'feature/test')
        result = run_script(SCRIPT_PATH, 'add-file', '--plan-id', 'test-plan', '--file', 'src/Main.java')
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['added'] == 'src/Main.java'
        assert data['total'] == 1


# =============================================================================
# Test: Get Context (NEW OPTIMIZATION)
# =============================================================================


def test_get_context():
    """Test get-context returns all relevant references in one call."""
    with TestContext():
        run_script(
            SCRIPT_PATH,
            'create',
            '--plan-id',
            'test-plan',
            '--branch',
            'feature/test',
            '--issue-url',
            'https://github.com/org/repo/issues/123',
            '--build-system',
            'maven',
        )
        run_script(SCRIPT_PATH, 'add-file', '--plan-id', 'test-plan', '--file', 'src/Main.java')
        run_script(SCRIPT_PATH, 'add-file', '--plan-id', 'test-plan', '--file', 'src/Test.java')

        result = run_script(SCRIPT_PATH, 'get-context', '--plan-id', 'test-plan')
        assert result.success, f'Script failed: {result.stderr}'
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
        run_script(SCRIPT_PATH, 'create', '--plan-id', 'test-plan', '--branch', 'feature/test')
        result = run_script(SCRIPT_PATH, 'get-context', '--plan-id', 'test-plan')
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['modified_files_count'] == 0


def test_get_context_not_found():
    """Test get-context with missing plan."""
    with TestContext():
        result = run_script(SCRIPT_PATH, 'get-context', '--plan-id', 'nonexistent')
        assert not result.success, 'Expected failure for missing plan'


# =============================================================================
# Test: Add List Command
# =============================================================================


def test_add_list_new_field():
    """Test adding multiple values to a new list field."""
    with TestContext():
        run_script(SCRIPT_PATH, 'create', '--plan-id', 'test-plan', '--branch', 'feature/test')
        result = run_script(
            SCRIPT_PATH,
            'add-list',
            '--plan-id',
            'test-plan',
            '--field',
            'affected_files',
            '--values',
            'file1.md,file2.md,file3.md',
        )
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert data['field'] == 'affected_files'
        assert data['added_count'] == 3
        assert data['total'] == 3


def test_add_list_existing_field():
    """Test adding values to an existing list field."""
    with TestContext():
        run_script(SCRIPT_PATH, 'create', '--plan-id', 'test-plan', '--branch', 'feature/test')
        run_script(
            SCRIPT_PATH,
            'add-list',
            '--plan-id',
            'test-plan',
            '--field',
            'affected_files',
            '--values',
            'file1.md,file2.md',
        )
        result = run_script(
            SCRIPT_PATH,
            'add-list',
            '--plan-id',
            'test-plan',
            '--field',
            'affected_files',
            '--values',
            'file3.md,file4.md',
        )
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['added_count'] == 2
        assert data['total'] == 4


def test_add_list_no_duplicates():
    """Test that add-list skips duplicate values."""
    with TestContext():
        run_script(SCRIPT_PATH, 'create', '--plan-id', 'test-plan', '--branch', 'feature/test')
        run_script(
            SCRIPT_PATH,
            'add-list',
            '--plan-id',
            'test-plan',
            '--field',
            'affected_files',
            '--values',
            'file1.md,file2.md',
        )
        result = run_script(
            SCRIPT_PATH,
            'add-list',
            '--plan-id',
            'test-plan',
            '--field',
            'affected_files',
            '--values',
            'file1.md,file3.md',
        )
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['added_count'] == 1  # Only file3.md is new
        assert data['total'] == 3


# =============================================================================
# Test: Set List Command (NEW - replaces list entirely)
# =============================================================================


def test_set_list_comma_separated():
    """Test set-list with comma-separated values."""
    with TestContext():
        run_script(SCRIPT_PATH, 'create', '--plan-id', 'test-plan', '--branch', 'feature/test')
        result = run_script(
            SCRIPT_PATH,
            'set-list',
            '--plan-id',
            'test-plan',
            '--field',
            'affected_files',
            '--values',
            'file1.md,file2.md,file3.md',
        )
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert data['field'] == 'affected_files'
        assert data['count'] == 3


def test_set_list_replaces_existing():
    """Test that set-list replaces existing list (not appends)."""
    with TestContext():
        run_script(SCRIPT_PATH, 'create', '--plan-id', 'test-plan', '--branch', 'feature/test')
        # First add some files
        run_script(
            SCRIPT_PATH,
            'add-list',
            '--plan-id',
            'test-plan',
            '--field',
            'affected_files',
            '--values',
            'old1.md,old2.md,old3.md',
        )
        # Now set-list should REPLACE, not append
        result = run_script(
            SCRIPT_PATH,
            'set-list',
            '--plan-id',
            'test-plan',
            '--field',
            'affected_files',
            '--values',
            'new1.md,new2.md',
        )
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['count'] == 2  # Only the new files, not 5

        # Verify by reading the field
        get_result = run_script(SCRIPT_PATH, 'get', '--plan-id', 'test-plan', '--field', 'affected_files')
        get_data = parse_toon(get_result.stdout)
        assert len(get_data['value']) == 2
        assert 'new1.md' in get_data['value']
        assert 'new2.md' in get_data['value']
        assert 'old1.md' not in get_data['value']


def test_set_list_empty_clears():
    """Test that set-list with empty values clears the list."""
    with TestContext():
        run_script(SCRIPT_PATH, 'create', '--plan-id', 'test-plan', '--branch', 'feature/test')
        run_script(
            SCRIPT_PATH,
            'add-list',
            '--plan-id',
            'test-plan',
            '--field',
            'affected_files',
            '--values',
            'file1.md,file2.md',
        )
        # Set to empty
        result = run_script(
            SCRIPT_PATH,
            'set-list',
            '--plan-id',
            'test-plan',
            '--field',
            'affected_files',
            '--values',
            '',
        )
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['count'] == 0


def test_set_list_nonexistent_plan():
    """Test set-list on non-existent plan fails."""
    with TestContext():
        result = run_script(
            SCRIPT_PATH,
            'set-list',
            '--plan-id',
            'nonexistent',
            '--field',
            'affected_files',
            '--values',
            'file1.md',
        )
        assert not result.success, 'Expected failure for non-existent plan'
        data = parse_toon(result.stdout)
        assert data['status'] == 'error'


def test_set_list_returns_previous_count():
    """Test that set-list returns the previous count when replacing."""
    with TestContext():
        run_script(SCRIPT_PATH, 'create', '--plan-id', 'test-plan', '--branch', 'feature/test')
        run_script(
            SCRIPT_PATH,
            'add-list',
            '--plan-id',
            'test-plan',
            '--field',
            'affected_files',
            '--values',
            'old1.md,old2.md,old3.md',
        )
        result = run_script(
            SCRIPT_PATH,
            'set-list',
            '--plan-id',
            'test-plan',
            '--field',
            'affected_files',
            '--values',
            'new1.md,new2.md',
        )
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['previous_count'] == 3
        assert data['count'] == 2

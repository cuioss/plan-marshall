#!/usr/bin/env python3
"""Tests for manage-json-file.py script.

Migrated from test-manage-json-file.sh - tests JSON file CRUD operations
with path notation including read, update, add, and remove operations.
"""

import tempfile
from pathlib import Path

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import get_script_path, run_script

# Script under test
SCRIPT_PATH = get_script_path('plan-marshall', 'tools-json-ops', 'manage-json-file.py')


# =============================================================================
# Test Helpers
# =============================================================================


def create_test_config(temp_dir):
    """Create a test config file."""
    config_file = temp_dir / 'test-config.json'
    config_file.write_text("""{
  "version": 1,
  "commands": {
    "test-cmd": {
      "last_execution": {
        "date": "2025-11-25",
        "status": "SUCCESS"
      },
      "lessons_learned": ["lesson1", "lesson2"]
    }
  },
  "array_field": [1, 2, 3]
}""")
    return config_file


# =============================================================================
# Tests
# =============================================================================


def test_read_entire_file():
    """Test read entire file."""
    with tempfile.TemporaryDirectory() as td:
        temp_dir = Path(td)
        config_file = create_test_config(temp_dir)
        result = run_script(SCRIPT_PATH, 'read', '--file-path', str(config_file))
        data = result.json()

        assert data.get('success') is True, 'Should succeed'
        assert data.get('value', {}).get('version') == 1, 'Version should be 1'


def test_read_field():
    """Test read specific field."""
    with tempfile.TemporaryDirectory() as td:
        temp_dir = Path(td)
        config_file = create_test_config(temp_dir)
        result = run_script(
            SCRIPT_PATH, 'read-field', '--file-path', str(config_file), '--field', 'commands.test-cmd.last_execution.status'
        )
        data = result.json()

        assert data.get('success') is True, 'Should succeed'
        assert data.get('value') == 'SUCCESS', 'Value should be SUCCESS'


def test_read_nested_field():
    """Test read nested array field."""
    with tempfile.TemporaryDirectory() as td:
        temp_dir = Path(td)
        config_file = create_test_config(temp_dir)
        result = run_script(SCRIPT_PATH, 'read-field', '--file-path', str(config_file), '--field', 'commands.test-cmd.lessons_learned')
        data = result.json()

        assert data.get('success') is True, 'Should succeed'
        value = data.get('value', [])
        assert len(value) == 2, 'Should have 2 elements'


def test_read_array_index():
    """Test read array index."""
    with tempfile.TemporaryDirectory() as td:
        temp_dir = Path(td)
        config_file = create_test_config(temp_dir)
        result = run_script(SCRIPT_PATH, 'read-field', '--file-path', str(config_file), '--field', 'array_field[1]')
        data = result.json()

        assert data.get('success') is True, 'Should succeed'
        assert data.get('value') == 2, 'Value should be 2'


def test_read_nonexistent_field():
    """Test read non-existent field returns error."""
    with tempfile.TemporaryDirectory() as td:
        temp_dir = Path(td)
        config_file = create_test_config(temp_dir)
        result = run_script(SCRIPT_PATH, 'read-field', '--file-path', str(config_file), '--field', 'nonexistent.field')
        # Script may output to stderr for errors
        data = result.json_or_error()

        assert data.get('success') is False, 'Should fail for non-existent field'


def test_update_field():
    """Test update field."""
    with tempfile.TemporaryDirectory() as td:
        temp_dir = Path(td)
        config_file = create_test_config(temp_dir)

        # Update field
        run_script(
            SCRIPT_PATH,
            'update-field',
            '--file-path',
            str(config_file),
            '--field',
            'commands.test-cmd.last_execution.status',
            '--value',
            '"UPDATED"',
        )

        # Verify update
        result = run_script(
            SCRIPT_PATH, 'read-field', '--file-path', str(config_file), '--field', 'commands.test-cmd.last_execution.status'
        )
        data = result.json()

        assert data.get('value') == 'UPDATED', 'Value should be UPDATED'


def test_update_creates_path():
    """Test update creates intermediate objects."""
    with tempfile.TemporaryDirectory() as td:
        temp_dir = Path(td)
        config_file = create_test_config(temp_dir)

        # Update creates new path
        run_script(
            SCRIPT_PATH, 'update-field', '--file-path', str(config_file), '--field', 'new_section.nested.value', '--value', '42'
        )

        # Verify update
        result = run_script(SCRIPT_PATH, 'read-field', '--file-path', str(config_file), '--field', 'new_section.nested.value')
        data = result.json()

        assert data.get('value') == 42, 'Value should be 42'


def test_add_entry_to_array():
    """Test add entry to array."""
    with tempfile.TemporaryDirectory() as td:
        temp_dir = Path(td)
        config_file = create_test_config(temp_dir)

        # Add entry
        run_script(
            SCRIPT_PATH,
            'add-entry',
            '--file-path',
            str(config_file),
            '--field',
            'commands.test-cmd.lessons_learned',
            '--value',
            '"lesson3"',
        )

        # Verify
        result = run_script(SCRIPT_PATH, 'read-field', '--file-path', str(config_file), '--field', 'commands.test-cmd.lessons_learned')
        data = result.json()

        value = data.get('value', [])
        assert len(value) == 3, 'Should have 3 elements'
        assert 'lesson3' in value, 'Should include lesson3'


def test_remove_entry_from_array():
    """Test remove entry from array."""
    with tempfile.TemporaryDirectory() as td:
        temp_dir = Path(td)
        config_file = create_test_config(temp_dir)

        # Remove entry
        run_script(
            SCRIPT_PATH,
            'remove-entry',
            '--file-path',
            str(config_file),
            '--field',
            'commands.test-cmd.lessons_learned',
            '--value',
            '"lesson1"',
        )

        # Verify
        result = run_script(SCRIPT_PATH, 'read-field', '--file-path', str(config_file), '--field', 'commands.test-cmd.lessons_learned')
        data = result.json()

        value = data.get('value', [])
        assert len(value) == 1, 'Should have 1 element'
        assert 'lesson1' not in value, 'lesson1 should be removed'


def test_remove_field():
    """Test remove field entirely."""
    with tempfile.TemporaryDirectory() as td:
        temp_dir = Path(td)
        config_file = create_test_config(temp_dir)

        # Remove field
        run_script(SCRIPT_PATH, 'remove-entry', '--file-path', str(config_file), '--field', 'commands.test-cmd.lessons_learned')

        # Verify field is gone
        result = run_script(SCRIPT_PATH, 'read-field', '--file-path', str(config_file), '--field', 'commands.test-cmd.lessons_learned')
        # Script may output to stderr for errors
        data = result.json_or_error()

        assert data.get('success') is False, 'Field should not exist'


def test_write_entire_file():
    """Test write entire file."""
    with tempfile.TemporaryDirectory() as td:
        temp_dir = Path(td)
        new_file = temp_dir / 'new-file.json'

        result = run_script(SCRIPT_PATH, 'write', '--file-path', str(new_file), '--value', '{"test": true, "value": 123}')
        data = result.json()

        assert data.get('success') is True, 'Should succeed'

        # Verify content
        verify = run_script(SCRIPT_PATH, 'read-field', '--file-path', str(new_file), '--field', 'value')
        verify_data = verify.json()
        assert verify_data.get('value') == 123, 'Value should be 123'


def test_file_not_found():
    """Test file not found returns error."""
    with tempfile.TemporaryDirectory() as td:
        temp_dir = Path(td)
        result = run_script(SCRIPT_PATH, 'read', '--file-path', str(temp_dir / 'nonexistent.json'))
        # Script may output to stderr for errors
        data = result.json_or_error()

        assert data.get('success') is False, 'Should fail'
        assert 'not found' in data.get('error', '').lower(), 'Should mention not found'


def test_invalid_json_value():
    """Test invalid JSON value returns error."""
    with tempfile.TemporaryDirectory() as td:
        temp_dir = Path(td)
        config_file = create_test_config(temp_dir)

        result = run_script(
            SCRIPT_PATH, 'update-field', '--file-path', str(config_file), '--field', 'test', '--value', 'not valid json'
        )
        # Script may output to stderr for errors
        data = result.json_or_error()

        assert data.get('success') is False, 'Should fail for invalid JSON value'


# =============================================================================
# Main
# =============================================================================

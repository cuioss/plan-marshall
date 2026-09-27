#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Behavior-cluster tests for manage-files content lifecycle commands."""

import json

import pytest
from _manage_files_fixtures import (
    EmptyPlanContext,
    cmd_create_or_reference,
    cmd_exists,
    cmd_list,
    cmd_mkdir,
    cmd_read,
    cmd_remove,
    cmd_write,
    parse_ns,
)

# =============================================================================
# Test: Write and Read
# =============================================================================


def test_write_file(plan_context):
    """Test writing a file."""
    result = cmd_write(
        parse_ns(
            'plan-marshall',
            'manage-files',
            'manage-files.py',
            'write',
            '--plan-id',
            str(plan_context.plan_id),
            '--file',
            'task.md',
            '--content',
            '# Task\nDo something',
        )
    )
    assert result['status'] == 'success'
    assert result['action'] == 'created'
    assert result['file'] == 'task.md'
    # Verify file was created
    assert (plan_context.plan_dir / 'task.md').exists()
    assert (plan_context.plan_dir / 'task.md').read_text().rstrip('\n') == '# Task\nDo something'


def test_read_file(plan_context, capsys):
    """Test reading a file (cmd_read prints content and returns None)."""
    (plan_context.plan_dir / 'test.md').write_text('Test content')

    result = cmd_read(
        parse_ns(
            'plan-marshall',
            'manage-files',
            'manage-files.py',
            'read',
            '--plan-id',
            str(plan_context.plan_id),
            '--file',
            'test.md',
        )
    )
    assert result is None  # cmd_read prints directly, returns None
    captured = capsys.readouterr()
    assert 'Test content' in captured.out


def test_read_nonexistent_file(plan_context):
    """Test reading a file that doesn't exist."""
    result = cmd_read(
        parse_ns(
            'plan-marshall',
            'manage-files',
            'manage-files.py',
            'read',
            '--plan-id',
            'file-noexist',
            '--file',
            'missing.md',
        )
    )
    assert result['status'] == 'error'
    assert result['error'] == 'file_not_found'


# =============================================================================
# Test: List and Exists
# =============================================================================


def test_list_empty(plan_context):
    """Test listing files in empty plan."""
    result = cmd_list(
        parse_ns('plan-marshall', 'manage-files', 'manage-files.py', 'list', '--plan-id', str(plan_context.plan_id))
    )
    assert result['status'] == 'success'
    assert result['files'] == []


def test_list_with_files(plan_context):
    """Test listing files."""
    # Create some files
    (plan_context.plan_dir / 'references.json').write_text('{"branch": "main"}')
    (plan_context.plan_dir / 'task.md').write_text('Task')

    result = cmd_list(
        parse_ns('plan-marshall', 'manage-files', 'manage-files.py', 'list', '--plan-id', str(plan_context.plan_id))
    )
    assert result['status'] == 'success'
    assert 'task.md' in result['files']
    assert 'references.json' in result['files']


def test_exists_present(plan_context):
    """Test checking if file exists (present)."""
    (plan_context.plan_dir / 'test.md').write_text('Test')

    result = cmd_exists(
        parse_ns(
            'plan-marshall',
            'manage-files',
            'manage-files.py',
            'exists',
            '--plan-id',
            str(plan_context.plan_id),
            '--file',
            'test.md',
        )
    )
    assert result['status'] == 'success'
    assert result['exists'] is True
    assert result['plan_id'] == plan_context.plan_id
    assert result['file'] == 'test.md'
    assert 'path' in result


def test_exists_absent(plan_context):
    """Test checking if file exists (absent)."""
    result = cmd_exists(
        parse_ns(
            'plan-marshall',
            'manage-files',
            'manage-files.py',
            'exists',
            '--plan-id',
            'file-absent',
            '--file',
            'missing.md',
        )
    )
    assert result['status'] == 'success'
    assert result['exists'] is False
    assert result['plan_id'] == 'file-absent'
    assert result['file'] == 'missing.md'


def test_exists_invalid_plan_id(plan_context):
    """Test exists with invalid plan ID exits via sys.exit(1)."""
    with pytest.raises(SystemExit) as exc_info:
        cmd_exists(
            parse_ns(
                'plan-marshall',
                'manage-files',
                'manage-files.py',
                'exists',
                '--plan-id',
                'Invalid_Plan',
                '--file',
                'test.md',
            )
        )
    assert exc_info.value.code == 0


def test_exists_invalid_file_path(plan_context):
    """Test exists with invalid file path returns error dict."""
    result = cmd_exists(
        parse_ns(
            'plan-marshall',
            'manage-files',
            'manage-files.py',
            'exists',
            '--plan-id',
            'file-exists',
            '--file',
            '../escape.md',
        )
    )
    assert result['status'] == 'error'
    assert result['error'] == 'invalid_path'


# =============================================================================
# Test: Remove and Mkdir
# =============================================================================


def test_remove_file(plan_context):
    """Test removing a file."""
    (plan_context.plan_dir / 'delete-me.md').write_text('Goodbye')

    result = cmd_remove(
        parse_ns(
            'plan-marshall',
            'manage-files',
            'manage-files.py',
            'remove',
            '--plan-id',
            str(plan_context.plan_id),
            '--file',
            'delete-me.md',
        )
    )
    assert result['status'] == 'success'
    assert result['action'] == 'removed'
    assert not (plan_context.plan_dir / 'delete-me.md').exists()


def test_remove_nonexistent_file(plan_context):
    """Test removing a file that doesn't exist."""
    result = cmd_remove(
        parse_ns(
            'plan-marshall',
            'manage-files',
            'manage-files.py',
            'remove',
            '--plan-id',
            'file-remove-missing',
            '--file',
            'ghost.md',
        )
    )
    assert result['status'] == 'error'
    assert result['error'] == 'file_not_found'


def test_mkdir(plan_context):
    """Test creating a directory."""
    result = cmd_mkdir(
        parse_ns(
            'plan-marshall',
            'manage-files',
            'manage-files.py',
            'mkdir',
            '--plan-id',
            str(plan_context.plan_id),
            '--dir',
            'requirements',
        )
    )
    assert result['status'] == 'success'
    assert result['action'] == 'created'
    assert (plan_context.plan_dir / 'requirements').is_dir()


def test_mkdir_already_exists(plan_context):
    """Test creating a directory that already exists."""
    (plan_context.plan_dir / 'existing').mkdir()
    result = cmd_mkdir(
        parse_ns(
            'plan-marshall',
            'manage-files',
            'manage-files.py',
            'mkdir',
            '--plan-id',
            str(plan_context.plan_id),
            '--dir',
            'existing',
        )
    )
    assert result['status'] == 'success'
    assert result['action'] == 'exists'


# =============================================================================
# Test: Create-or-Reference
# =============================================================================


def test_create_or_reference_new_plan():
    """Test create-or-reference creates new plan directory."""
    with EmptyPlanContext() as ctx:
        result = cmd_create_or_reference(
            parse_ns('plan-marshall', 'manage-files', 'manage-files.py', 'create-or-reference', '--plan-id', 'new-plan')
        )
        assert result['status'] == 'success'
        assert result['action'] == 'created'
        assert result['plan_id'] == 'new-plan'
        # Verify directory was created
        assert ctx.plan_dir('new-plan').exists()


def test_create_or_reference_existing_plan(plan_context):
    """Test create-or-reference returns exists for existing plan."""
    result = cmd_create_or_reference(
        parse_ns(
            'plan-marshall',
            'manage-files',
            'manage-files.py',
            'create-or-reference',
            '--plan-id',
            str(plan_context.plan_id),
        )
    )
    assert result['status'] == 'success'
    assert result['action'] == 'exists'
    assert result['plan_id'] == plan_context.plan_id


def test_create_or_reference_existing_with_status(plan_context):
    """Test create-or-reference returns phase info when status.json exists."""
    # Create status.json with phase info (domain is in references.json, not status.json)
    status_content = json.dumps({'title': 'Test Plan', 'current_phase': 'outline'})
    (plan_context.plan_dir / 'status.json').write_text(status_content)

    result = cmd_create_or_reference(
        parse_ns(
            'plan-marshall',
            'manage-files',
            'manage-files.py',
            'create-or-reference',
            '--plan-id',
            str(plan_context.plan_id),
        )
    )
    assert result['status'] == 'success'
    assert result['action'] == 'exists'
    assert result['current_phase'] == 'outline'
    # Domain should NOT be in output (stored in references.json, not status.toon)
    assert 'domain' not in result


def test_create_or_reference_invalid_plan_id():
    """Test create-or-reference rejects invalid plan IDs (sys.exit(1))."""
    with EmptyPlanContext():
        with pytest.raises(SystemExit) as exc_info:
            cmd_create_or_reference(
                parse_ns(
                    'plan-marshall',
                    'manage-files',
                    'manage-files.py',
                    'create-or-reference',
                    '--plan-id',
                    'Invalid_Plan',
                )
            )
        assert exc_info.value.code == 0

#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Behavior-cluster tests for manage-files identifier and write validation."""

import pytest
from _manage_files_fixtures import cmd_list, cmd_write, parse_ns

# =============================================================================
# Test: Invalid Plan IDs (direct import)
# =============================================================================


def test_invalid_plan_id_uppercase(plan_context):
    """Test that uppercase plan IDs are rejected."""
    with pytest.raises(SystemExit) as exc_info:
        cmd_list(parse_ns('plan-marshall', 'manage-files', 'manage-files.py', 'list', '--plan-id', 'My-Plan'))
    assert exc_info.value.code == 0


def test_invalid_plan_id_underscore(plan_context):
    """Test that underscore in plan IDs are rejected."""
    with pytest.raises(SystemExit) as exc_info:
        cmd_list(parse_ns('plan-marshall', 'manage-files', 'manage-files.py', 'list', '--plan-id', 'my_plan'))
    assert exc_info.value.code == 0


# =============================================================================
# Test: Write edge cases
# =============================================================================


def test_write_missing_content(plan_context):
    """Test write fails when neither --content nor --stdin provided."""
    result = cmd_write(
        parse_ns(
            'plan-marshall',
            'manage-files',
            'manage-files.py',
            'write',
            '--plan-id',
            'file-write-no-content',
            '--file',
            'test.md',
        )
    )
    assert result['status'] == 'error'
    assert result['error'] == 'missing_content'


def test_write_invalid_path(plan_context):
    """Test write rejects path traversal."""
    result = cmd_write(
        parse_ns(
            'plan-marshall',
            'manage-files',
            'manage-files.py',
            'write',
            '--plan-id',
            'file-write-escape',
            '--file',
            '../escape.md',
            '--content',
            'bad',
        )
    )
    assert result['status'] == 'error'
    assert result['error'] == 'invalid_path'


# =============================================================================
# Test: Write with --content-file
# =============================================================================


def test_write_with_content_file_path_succeeds(plan_context, tmp_path):
    """Test write reads payload from --content-file and writes verbatim."""
    payload = '# Heading\n\nMultiline\npayload\n'
    payload_path = tmp_path / 'payload.md'
    payload_path.write_text(payload, encoding='utf-8')

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
            '--content-file',
            str(payload_path),
        )
    )
    assert result['status'] == 'success'
    assert result['action'] == 'created'
    assert result['file'] == 'task.md'
    # Verify file contents match the staged payload verbatim.
    target = plan_context.plan_dir / 'task.md'
    assert target.exists()
    assert target.read_text(encoding='utf-8') == payload


def test_write_with_content_file_missing_returns_error(plan_context, tmp_path):
    """Test write returns content_file_not_found when --content-file path is absent."""
    missing_path = tmp_path / 'does-not-exist.md'

    result = cmd_write(
        parse_ns(
            'plan-marshall',
            'manage-files',
            'manage-files.py',
            'write',
            '--plan-id',
            'file-write-cf-missing',
            '--file',
            'task.md',
            '--content-file',
            str(missing_path),
        )
    )
    assert result['status'] == 'error'
    assert result['error'] == 'content_file_not_found'
    # The script resolves the path before reporting; assert the resolved
    # form appears in the message so the user can locate the missing file.
    assert str(missing_path.resolve()) in result['message']


def test_write_content_and_content_file_mutually_exclusive(plan_context, tmp_path):
    """Test write rejects --content and --content-file used together."""
    payload_path = tmp_path / 'payload.md'
    payload_path.write_text('payload', encoding='utf-8')

    result = cmd_write(
        parse_ns(
            'plan-marshall',
            'manage-files',
            'manage-files.py',
            'write',
            '--plan-id',
            'file-write-cf-mutex',
            '--file',
            'task.md',
            '--content',
            'inline content',
            '--content-file',
            str(payload_path),
        )
    )
    assert result['status'] == 'error'
    assert result['error'] == 'mutually_exclusive'

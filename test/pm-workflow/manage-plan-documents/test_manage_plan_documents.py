#!/usr/bin/env python3
"""Tests for manage-plan-documents.py script."""

import sys
from pathlib import Path

# Import shared infrastructure
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from conftest import PlanContext, get_script_path, run_script  # noqa: E402

# Get script path
SCRIPT_PATH = get_script_path('pm-workflow', 'manage-plan-documents', 'manage-plan-documents.py')

# Import toon_parser - conftest sets up PYTHONPATH
from toon_parser import parse_toon  # type: ignore[import-not-found]  # noqa: E402

# Alias for backward compatibility
TestContext = PlanContext


# =============================================================================
# Test: List Types
# =============================================================================

def test_list_types():
    """Test listing available document types."""
    with TestContext():
        result = run_script(SCRIPT_PATH, 'list-types')
        assert result.success, f"Script failed: {result.stderr}"
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert 'types' in data
        type_names = [t['name'] for t in data['types']]
        assert 'request' in type_names
        # Note: 'solution' is now handled by manage-solution-outline skill


# =============================================================================
# Test: Request Document
# =============================================================================

def test_request_create():
    """Test creating a request document."""
    with TestContext(plan_id='request-create') as ctx:
        result = run_script(SCRIPT_PATH,
            'request', 'create',
            '--plan-id', 'request-create',
            '--title', 'Test Feature',
            '--source', 'description',
            '--body', 'Implement a test feature'
        )
        assert result.success, f"Script failed: {result.stderr}"
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert data['document'] == 'request'
        assert data['action'] == 'created'
        # Verify file was created
        assert (ctx.plan_dir / 'request.md').exists()


def test_request_create_with_context():
    """Test creating a request document with optional context."""
    with TestContext(plan_id='request-context') as ctx:
        result = run_script(SCRIPT_PATH,
            'request', 'create',
            '--plan-id', 'request-context',
            '--title', 'Test Feature',
            '--source', 'issue',
            '--source-id', 'https://github.com/org/repo/issues/123',
            '--body', 'Implement a test feature',
            '--context', 'Additional context here'
        )
        assert result.success, f"Script failed: {result.stderr}"
        # Verify content
        content = (ctx.plan_dir / 'request.md').read_text()
        assert 'Test Feature' in content
        assert 'Additional context here' in content


def test_request_create_invalid_source():
    """Test that invalid source is rejected."""
    with TestContext(plan_id='request-invalid'):
        result = run_script(SCRIPT_PATH,
            'request', 'create',
            '--plan-id', 'request-invalid',
            '--title', 'Test',
            '--source', 'invalid_source',
            '--body', 'Body'
        )
        assert not result.success, "Expected failure for invalid source"
        data = parse_toon(result.stdout)
        assert data['status'] == 'error'
        assert 'validation_failed' in data.get('error', '')


def test_request_create_missing_required():
    """Test that missing required field is rejected."""
    with TestContext(plan_id='request-missing'):
        result = run_script(SCRIPT_PATH,
            'request', 'create',
            '--plan-id', 'request-missing',
            '--title', 'Test',
            '--source', 'description'
            # Missing --body
        )
        assert not result.success, "Expected failure for missing body"


def test_request_read():
    """Test reading a request document."""
    with TestContext(plan_id='request-read') as ctx:
        # Create file first
        (ctx.plan_dir / 'request.md').write_text('''# Request: Test

plan_id: request-read
source: description

## Original Input

Test body content

## Context

Test context
''')

        result = run_script(SCRIPT_PATH,
            'request', 'read',
            '--plan-id', 'request-read'
        )
        assert result.success, f"Script failed: {result.stderr}"
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert data['document'] == 'request'
        assert 'content' in data


def test_request_read_raw():
    """Test reading a request document in raw mode."""
    with TestContext(plan_id='request-raw') as ctx:
        content = '# Request: Test\n\nRaw content here'
        (ctx.plan_dir / 'request.md').write_text(content)

        result = run_script(SCRIPT_PATH,
            'request', 'read',
            '--plan-id', 'request-raw',
            '--raw'
        )
        assert result.success, f"Script failed: {result.stderr}"
        assert 'Raw content here' in result.stdout


def test_request_read_not_found():
    """Test reading a non-existent request document."""
    with TestContext(plan_id='request-notfound'):
        result = run_script(SCRIPT_PATH,
            'request', 'read',
            '--plan-id', 'request-notfound'
        )
        assert not result.success, "Expected failure for missing document"
        data = parse_toon(result.stdout)
        assert data['status'] == 'error'
        assert data['error'] == 'document_not_found'


def test_request_exists_present():
    """Test checking if request exists (present)."""
    with TestContext(plan_id='request-exists') as ctx:
        (ctx.plan_dir / 'request.md').write_text('# Request')

        result = run_script(SCRIPT_PATH,
            'request', 'exists',
            '--plan-id', 'request-exists'
        )
        assert result.success, f"Script failed: {result.stderr}"
        data = parse_toon(result.stdout)
        assert data['exists'] is True


def test_request_exists_absent():
    """Test checking if request exists (absent)."""
    with TestContext(plan_id='request-absent'):
        result = run_script(SCRIPT_PATH,
            'request', 'exists',
            '--plan-id', 'request-absent'
        )
        # Exit code 1 when not found
        assert not result.success
        data = parse_toon(result.stdout)
        assert data['exists'] is False


def test_request_remove():
    """Test removing a request document."""
    with TestContext(plan_id='request-remove') as ctx:
        (ctx.plan_dir / 'request.md').write_text('# Request')

        result = run_script(SCRIPT_PATH,
            'request', 'remove',
            '--plan-id', 'request-remove'
        )
        assert result.success, f"Script failed: {result.stderr}"
        data = parse_toon(result.stdout)
        assert data['action'] == 'removed'
        assert not (ctx.plan_dir / 'request.md').exists()


# =============================================================================
# Test: Invalid Plan IDs
# =============================================================================

def test_invalid_plan_id_uppercase():
    """Test that uppercase plan IDs are rejected."""
    with TestContext():
        result = run_script(SCRIPT_PATH,
            'request', 'create',
            '--plan-id', 'My-Plan',
            '--title', 'Test',
            '--source', 'description',
            '--body', 'Body'
        )
        assert not result.success, "Expected failure for uppercase plan ID"
        data = parse_toon(result.stdout)
        assert data['error'] == 'invalid_plan_id'


def test_invalid_plan_id_underscore():
    """Test that underscore in plan IDs are rejected."""
    with TestContext():
        result = run_script(SCRIPT_PATH,
            'request', 'create',
            '--plan-id', 'my_plan',
            '--title', 'Test',
            '--source', 'description',
            '--body', 'Body'
        )
        assert not result.success, "Expected failure for underscore in plan ID"


# =============================================================================
# Test: Document Already Exists
# =============================================================================

def test_create_existing_fails():
    """Test that creating over existing document fails without --force."""
    with TestContext(plan_id='exists-fail') as ctx:
        (ctx.plan_dir / 'request.md').write_text('# Existing')

        result = run_script(SCRIPT_PATH,
            'request', 'create',
            '--plan-id', 'exists-fail',
            '--title', 'New',
            '--source', 'description',
            '--body', 'Body'
        )
        assert not result.success, "Expected failure for existing document"
        data = parse_toon(result.stdout)
        assert data['error'] == 'document_exists'


def test_create_existing_with_force():
    """Test that --force overwrites existing document."""
    with TestContext(plan_id='exists-force') as ctx:
        (ctx.plan_dir / 'request.md').write_text('# Old Content')

        result = run_script(SCRIPT_PATH,
            'request', 'create',
            '--plan-id', 'exists-force',
            '--title', 'New Title',
            '--source', 'description',
            '--body', 'New body',
            '--force'
        )
        assert result.success, f"Script failed: {result.stderr}"
        content = (ctx.plan_dir / 'request.md').read_text()
        assert 'New Title' in content


# =============================================================================
# Test: Unknown Document Type
# =============================================================================

def test_unknown_document_type():
    """Test that unknown document type is handled."""
    with TestContext():
        result = run_script(SCRIPT_PATH,
            'unknown', 'create',
            '--plan-id', 'test'
        )
        # argparse will fail before reaching our code
        assert not result.success

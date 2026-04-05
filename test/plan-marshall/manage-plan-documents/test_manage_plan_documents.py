#!/usr/bin/env python3
"""Tests for manage-plan-documents.py script.

Tier 2 (direct import) tests with 2 subprocess tests for CLI plumbing.
"""

import importlib.util
import sys
from argparse import Namespace
from pathlib import Path

# Import shared infrastructure
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from conftest import PlanContext, get_script_path, run_script  # noqa: E402

# Script path for remaining subprocess (CLI plumbing) tests
SCRIPT_PATH = get_script_path('plan-marshall', 'manage-plan-documents', 'manage-plan-documents.py')

# Import toon_parser for subprocess tests
from toon_parser import parse_toon  # type: ignore[import-not-found]  # noqa: E402

_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace' / 'bundles' / 'plan-marshall' / 'skills' / 'manage-plan-documents' / 'scripts'
)


def _load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_cmd_request = _load_module('_cmd_request', '_cmd_request.py')
_cmd_types = _load_module('_cmd_types', '_cmd_types.py')

cmd_clarify = _cmd_request.cmd_clarify
cmd_create = _cmd_request.cmd_create
cmd_exists = _cmd_request.cmd_exists
cmd_read = _cmd_request.cmd_read
cmd_remove = _cmd_request.cmd_remove
cmd_list_types = _cmd_types.cmd_list_types

# =============================================================================
# Test: List Types
# =============================================================================


def test_list_types():
    """Test listing available document types."""
    with PlanContext():
        result = cmd_list_types(Namespace())
        assert result['status'] == 'success'
        assert 'types' in result
        type_names = [t['name'] for t in result['types']]
        assert 'request' in type_names


# =============================================================================
# Test: Request Document
# =============================================================================


def test_request_create():
    """Test creating a request document."""
    with PlanContext(plan_id='request-create') as ctx:
        result = cmd_create(
            'request',
            Namespace(
                plan_id='request-create',
                title='Test Feature',
                source='description',
                source_id=None,
                body='Implement a test feature',
                context=None,
                force=False,
            ),
        )
        assert result['status'] == 'success'
        assert result['document'] == 'request'
        assert result['action'] == 'created'
        # Verify file was created
        assert (ctx.plan_dir / 'request.md').exists()


def test_request_create_with_context():
    """Test creating a request document with optional context."""
    with PlanContext(plan_id='request-context') as ctx:
        result = cmd_create(
            'request',
            Namespace(
                plan_id='request-context',
                title='Test Feature',
                source='issue',
                source_id='https://github.com/org/repo/issues/123',
                body='Implement a test feature',
                context='Additional context here',
                force=False,
            ),
        )
        assert result['status'] == 'success'
        # Verify content
        content = (ctx.plan_dir / 'request.md').read_text()
        assert 'Test Feature' in content
        assert 'Additional context here' in content


def test_request_create_invalid_source():
    """Test that invalid source is rejected."""
    with PlanContext(plan_id='request-invalid'):
        result = cmd_create(
            'request',
            Namespace(
                plan_id='request-invalid',
                title='Test',
                source='invalid_source',
                source_id=None,
                body='Body',
                context=None,
                force=False,
            ),
        )
        assert result['status'] == 'error'
        assert 'validation_failed' in result.get('error', '')


def test_request_read():
    """Test reading a request document."""
    with PlanContext(plan_id='request-read') as ctx:
        # Create file first
        (ctx.plan_dir / 'request.md').write_text("""# Request: Test

plan_id: request-read
source: description

## Original Input

Test body content

## Context

Test context
""")

        result = cmd_read(
            'request',
            Namespace(plan_id='request-read', raw=False, section=None),
        )
        assert result['status'] == 'success'
        assert result['document'] == 'request'
        assert 'content' in result


def test_request_read_raw(capsys):
    """Test reading a request document in raw mode."""
    with PlanContext(plan_id='request-raw') as ctx:
        content = '# Request: Test\n\nRaw content here'
        (ctx.plan_dir / 'request.md').write_text(content)

        result = cmd_read(
            'request',
            Namespace(plan_id='request-raw', raw=True, section=None),
        )
        assert result['status'] == 'success'
        captured = capsys.readouterr()
        assert 'Raw content here' in captured.out


def test_request_read_not_found():
    """Test reading a non-existent request document."""
    with PlanContext(plan_id='request-notfound'):
        result = cmd_read(
            'request',
            Namespace(plan_id='request-notfound', raw=False, section=None),
        )
        assert result['status'] == 'error'
        assert result['error'] == 'document_not_found'


def test_request_exists_present():
    """Test checking if request exists (present)."""
    with PlanContext(plan_id='request-exists') as ctx:
        (ctx.plan_dir / 'request.md').write_text('# Request')

        result = cmd_exists(
            'request',
            Namespace(plan_id='request-exists'),
        )
        assert result['exists'] is True


def test_request_exists_absent():
    """Test checking if request exists (absent)."""
    with PlanContext(plan_id='request-absent'):
        result = cmd_exists(
            'request',
            Namespace(plan_id='request-absent'),
        )
        assert result['exists'] is False


def test_request_remove():
    """Test removing a request document."""
    with PlanContext(plan_id='request-remove') as ctx:
        (ctx.plan_dir / 'request.md').write_text('# Request')

        result = cmd_remove(
            'request',
            Namespace(plan_id='request-remove'),
        )
        assert result['action'] == 'removed'
        assert not (ctx.plan_dir / 'request.md').exists()


# =============================================================================
# Test: Invalid Plan IDs
# =============================================================================


def test_invalid_plan_id_uppercase(capsys):
    """Test that uppercase plan IDs are rejected."""
    with PlanContext():
        result = cmd_create(
            'request',
            Namespace(
                plan_id='My-Plan',
                title='Test',
                source='description',
                source_id=None,
                body='Body',
                context=None,
                force=False,
            ),
        )
        assert result['status'] == 'error'


# =============================================================================
# Test: Document Already Exists
# =============================================================================


def test_create_existing_fails():
    """Test that creating over existing document fails without --force."""
    with PlanContext(plan_id='exists-fail') as ctx:
        (ctx.plan_dir / 'request.md').write_text('# Existing')

        result = cmd_create(
            'request',
            Namespace(
                plan_id='exists-fail',
                title='New',
                source='description',
                source_id=None,
                body='Body',
                context=None,
                force=False,
            ),
        )
        assert result['error'] == 'document_exists'


def test_create_existing_with_force():
    """Test that --force overwrites existing document."""
    with PlanContext(plan_id='exists-force') as ctx:
        (ctx.plan_dir / 'request.md').write_text('# Old Content')

        result = cmd_create(
            'request',
            Namespace(
                plan_id='exists-force',
                title='New Title',
                source='description',
                source_id=None,
                body='New body',
                context=None,
                force=True,
            ),
        )
        assert result['status'] == 'success'
        content = (ctx.plan_dir / 'request.md').read_text()
        assert 'New Title' in content


# =============================================================================
# Test: Section Read with Fallback
# =============================================================================


def test_read_section_clarified_request_fallback():
    """Test that clarified_request falls back to original_input when not present."""
    with PlanContext(plan_id='fallback-test'):
        # Create request
        cmd_create(
            'request',
            Namespace(
                plan_id='fallback-test',
                title='Test',
                source='description',
                source_id=None,
                body='Original body content',
                context=None,
                force=False,
            ),
        )

        # Request clarified_request - should return original_input
        result = cmd_read(
            'request',
            Namespace(plan_id='fallback-test', raw=False, section='clarified_request'),
        )
        assert result['status'] == 'success'
        assert result['section'] == 'original_input'  # actual section returned
        assert result['requested_section'] == 'clarified_request'
        assert 'Original body content' in result['content']


def test_read_section_clarified_request_when_present():
    """Test that clarified_request returns actual section when present."""
    with PlanContext(plan_id='clarified-present'):
        # Create request
        cmd_create(
            'request',
            Namespace(
                plan_id='clarified-present',
                title='Test',
                source='description',
                source_id=None,
                body='Original body',
                context=None,
                force=False,
            ),
        )

        # Add clarified_request via clarify command
        cmd_clarify(
            'request',
            Namespace(
                plan_id='clarified-present',
                clarifications='Q: What? A: This.',
                clarified_request='Clarified version of the request',
            ),
        )

        # Request clarified_request - should return the actual section
        result = cmd_read(
            'request',
            Namespace(plan_id='clarified-present', raw=False, section='clarified_request'),
        )
        assert result['section'] == 'clarified_request'
        assert 'Clarified version' in result['content']


# =============================================================================
# CLI Plumbing Tests (Tier 3 subprocess - kept for end-to-end coverage)
# =============================================================================


def test_cli_unknown_document_type():
    """Test that unknown document type is handled via CLI."""
    with PlanContext():
        result = run_script(SCRIPT_PATH, 'unknown', 'create', '--plan-id', 'test')
        # argparse will fail before reaching our code
        assert not result.success


def test_cli_missing_required_body():
    """Test that missing required field is rejected via CLI argparse."""
    with PlanContext(plan_id='request-missing'):
        result = run_script(
            SCRIPT_PATH,
            'request',
            'create',
            '--plan-id',
            'request-missing',
            '--title',
            'Test',
            '--source',
            'description',
            # Missing --body
        )
        assert not result.success


def test_cli_request_create_roundtrip():
    """Test full CLI create + read roundtrip for end-to-end plumbing."""
    with PlanContext(plan_id='cli-roundtrip'):
        result = run_script(
            SCRIPT_PATH,
            'request',
            'create',
            '--plan-id',
            'cli-roundtrip',
            '--title',
            'CLI Test',
            '--source',
            'description',
            '--body',
            'CLI body content',
        )
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert data['action'] == 'created'

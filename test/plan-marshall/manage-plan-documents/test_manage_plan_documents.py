#!/usr/bin/env python3
"""Tests for manage-plan-documents.py script.

Tier 2 (direct import) tests with 2 subprocess tests for CLI plumbing.

Exercises the three-step path-allocate pattern for request editing:
    1. `request path`           → script returns the canonical artifact path
    2. Main context edits file  → direct Read/Edit/Write (no shell boundary)
    3. `request mark-clarified` → script validates and records the transition
"""

import importlib.util
import sys
from argparse import Namespace
from pathlib import Path

from conftest import PlanContext, get_script_path, run_script

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

cmd_create = _cmd_request.cmd_create
cmd_exists = _cmd_request.cmd_exists
cmd_mark_clarified = _cmd_request.cmd_mark_clarified
cmd_path = _cmd_request.cmd_path
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
# Test: request path (Step 1 of edit flow)
# =============================================================================


def test_request_path_returns_canonical_path():
    """`request path` returns the absolute path to the existing request.md."""
    with PlanContext(plan_id='path-ok') as ctx:
        (ctx.plan_dir / 'request.md').write_text("""# Request: Test

plan_id: path-ok
source: description

## Original Input

Body

## Context

Ctx
""")

        result = cmd_path(
            'request',
            Namespace(plan_id='path-ok'),
        )
        assert result['status'] == 'success'
        assert result['document'] == 'request'
        assert result['file'] == 'request.md'
        # Path must be absolute and point to the actual file
        returned = Path(result['path'])
        assert returned.is_absolute()
        assert returned == (ctx.plan_dir / 'request.md').resolve()
        # Sections list is advertised for caller convenience
        assert 'sections' in result
        assert isinstance(result['sections'], list)
        assert 'original_input' in result['sections']


def test_request_path_missing_document():
    """`request path` errors when the request document does not exist yet."""
    with PlanContext(plan_id='path-missing'):
        result = cmd_path(
            'request',
            Namespace(plan_id='path-missing'),
        )
        assert result['status'] == 'error'


# =============================================================================
# Test: request mark-clarified (Step 3 of edit flow)
# =============================================================================


def test_mark_clarified_succeeds_when_section_present():
    """mark-clarified returns success when Clarified Request section exists."""
    with PlanContext(plan_id='mc-ok') as ctx:
        (ctx.plan_dir / 'request.md').write_text("""# Request: Test

plan_id: mc-ok
source: description

## Original Input

Body

## Clarifications

Q: What? A: This.

## Clarified Request

Clarified version of the request
""")
        result = cmd_mark_clarified(
            'request',
            Namespace(plan_id='mc-ok'),
        )
        assert result['status'] == 'success'
        assert result['clarified'] is True
        assert result['has_clarifications_section'] is True


def test_mark_clarified_succeeds_without_clarifications_section():
    """mark-clarified still succeeds when only Clarified Request is present."""
    with PlanContext(plan_id='mc-no-clar') as ctx:
        (ctx.plan_dir / 'request.md').write_text("""# Request: Test

plan_id: mc-no-clar
source: description

## Original Input

Body

## Clarified Request

Clarified content
""")
        result = cmd_mark_clarified(
            'request',
            Namespace(plan_id='mc-no-clar'),
        )
        assert result['status'] == 'success'
        assert result['clarified'] is True
        assert result['has_clarifications_section'] is False


def test_mark_clarified_fails_without_clarified_section():
    """mark-clarified errors when Clarified Request section is absent."""
    with PlanContext(plan_id='mc-missing') as ctx:
        (ctx.plan_dir / 'request.md').write_text("""# Request: Test

plan_id: mc-missing
source: description

## Original Input

Body
""")
        result = cmd_mark_clarified(
            'request',
            Namespace(plan_id='mc-missing'),
        )
        assert result['status'] == 'error'
        assert result['error'] == 'not_clarified'


def test_mark_clarified_fails_when_document_missing():
    """mark-clarified errors when the request document itself does not exist."""
    with PlanContext(plan_id='mc-no-doc'):
        result = cmd_mark_clarified(
            'request',
            Namespace(plan_id='mc-no-doc'),
        )
        assert result['status'] == 'error'


def test_three_step_edit_roundtrip():
    """End-to-end three-step pattern: create → path → direct edit → mark-clarified."""
    with PlanContext(plan_id='three-step') as ctx:
        # Step 0: create original document
        cmd_create(
            'request',
            Namespace(
                plan_id='three-step',
                title='Test',
                source='description',
                source_id=None,
                body='Original body',
                context=None,
                force=False,
            ),
        )

        # Step 1: script allocates path
        path_result = cmd_path(
            'request',
            Namespace(plan_id='three-step'),
        )
        assert path_result['status'] == 'success'
        target = Path(path_result['path'])

        # Step 2: main context edits the file directly (simulated)
        existing = target.read_text(encoding='utf-8')
        updated = existing + '\n## Clarified Request\n\nClarified version here\n'
        target.write_text(updated, encoding='utf-8')

        # Step 3: script validates and records transition
        mark_result = cmd_mark_clarified(
            'request',
            Namespace(plan_id='three-step'),
        )
        assert mark_result['status'] == 'success'
        assert mark_result['clarified'] is True

        # And a subsequent section read returns the clarified content
        read_result = cmd_read(
            'request',
            Namespace(plan_id='three-step', raw=False, section='clarified_request'),
        )
        assert read_result['status'] == 'success'
        assert read_result['section'] == 'clarified_request'
        assert 'Clarified version here' in read_result['content']

        # Sanity: plan context fixture directory was actually used
        assert ctx.plan_dir.exists()


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
    """Clarified section falls back to original_input when not present."""
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


def test_read_section_returns_clarified_when_present_after_direct_edit():
    """After a direct edit adds a Clarified Request section, read returns it."""
    with PlanContext(plan_id='clarified-present') as ctx:
        # Step 0: create the request
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

        # Step 1: script allocates canonical path
        path_result = cmd_path(
            'request',
            Namespace(plan_id='clarified-present'),
        )
        target = Path(path_result['path'])

        # Step 2: caller edits the file directly (no content crosses the shell)
        existing = target.read_text(encoding='utf-8')
        target.write_text(
            existing + '\n## Clarifications\n\nQ: What? A: This.\n\n## Clarified Request\n\nClarified version of the request\n',
            encoding='utf-8',
        )

        # Step 3: record the transition
        cmd_mark_clarified(
            'request',
            Namespace(plan_id='clarified-present'),
        )

        # Subsequent read of clarified_request returns the edited section
        result = cmd_read(
            'request',
            Namespace(plan_id='clarified-present', raw=False, section='clarified_request'),
        )
        assert result['section'] == 'clarified_request'
        assert 'Clarified version' in result['content']
        assert ctx.plan_dir.exists()


# =============================================================================
# Test: Header Metadata Section Reads (regression for phase-1-init header shape)
# =============================================================================


_PHASE_1_INIT_REQUEST_TEMPLATE = """# Request: Header Metadata Test

plan_id: {plan_id}
source: issue
source_id: https://github.com/org/repo/issues/42
created: 2026-04-14T10:00:00Z

## Original Input

Body content for header metadata regression.

## Context

Additional context for header metadata regression.
"""


def _write_phase1_request(ctx, plan_id: str) -> str:
    """Write a request.md using the phase-1-init header block shape."""
    content = _PHASE_1_INIT_REQUEST_TEMPLATE.format(plan_id=plan_id)
    (ctx.plan_dir / 'request.md').write_text(content)
    return content


def test_read_section_source_from_header():
    """Regression: `--section source` must resolve against header key:value lines."""
    with PlanContext(plan_id='header-source') as ctx:
        _write_phase1_request(ctx, 'header-source')

        result = cmd_read(
            'request',
            Namespace(plan_id='header-source', raw=False, section='source'),
        )
        assert result['status'] == 'success'
        assert result['section'] == 'source'
        assert result['requested_section'] == 'source'
        assert result['content'] == 'issue'


def test_read_section_source_id_from_header():
    """Regression: `--section source_id` must resolve against header key:value lines."""
    with PlanContext(plan_id='header-source-id') as ctx:
        _write_phase1_request(ctx, 'header-source-id')

        result = cmd_read(
            'request',
            Namespace(plan_id='header-source-id', raw=False, section='source_id'),
        )
        assert result['status'] == 'success'
        assert result['section'] == 'source_id'
        assert result['content'] == 'https://github.com/org/repo/issues/42'


def test_read_section_plan_id_from_header():
    """Regression: `--section plan_id` must resolve against header key:value lines."""
    with PlanContext(plan_id='header-plan-id') as ctx:
        _write_phase1_request(ctx, 'header-plan-id')

        result = cmd_read(
            'request',
            Namespace(plan_id='header-plan-id', raw=False, section='plan_id'),
        )
        assert result['status'] == 'success'
        assert result['section'] == 'plan_id'
        assert result['content'] == 'header-plan-id'


def test_read_section_created_from_header():
    """Regression: `--section created` must resolve against header key:value lines."""
    with PlanContext(plan_id='header-created') as ctx:
        _write_phase1_request(ctx, 'header-created')

        result = cmd_read(
            'request',
            Namespace(plan_id='header-created', raw=False, section='created'),
        )
        assert result['status'] == 'success'
        assert result['section'] == 'created'
        assert result['content'] == '2026-04-14T10:00:00Z'


def test_read_section_header_preserves_original_block():
    """The _header virtual section must return the full original header block unchanged."""
    with PlanContext(plan_id='header-preserved') as ctx:
        _write_phase1_request(ctx, 'header-preserved')

        result = cmd_read(
            'request',
            Namespace(plan_id='header-preserved', raw=False, section='_header'),
        )
        assert result['status'] == 'success'
        assert result['section'] == '_header'
        content = result['content']
        # Full header block (title + all key:value lines) is preserved.
        assert '# Request: Header Metadata Test' in content
        assert 'plan_id: header-preserved' in content
        assert 'source: issue' in content
        assert 'source_id: https://github.com/org/repo/issues/42' in content
        assert 'created: 2026-04-14T10:00:00Z' in content


def test_read_unknown_section_lists_header_fields_as_available():
    """Unknown sections still error, but available_sections now advertises header virtuals."""
    with PlanContext(plan_id='header-unknown') as ctx:
        _write_phase1_request(ctx, 'header-unknown')

        result = cmd_read(
            'request',
            Namespace(plan_id='header-unknown', raw=False, section='does_not_exist'),
        )
        assert result['status'] == 'error'
        assert result['error'] == 'section_not_found'
        assert result['section'] == 'does_not_exist'
        available = result['available_sections']
        # Both H2 sections and promoted header virtuals must be listed.
        assert '_header' in available
        assert 'original_input' in available
        assert 'context' in available
        assert 'plan_id' in available
        assert 'source' in available
        assert 'source_id' in available
        assert 'created' in available


def test_cli_archive_plan_source_section_read():
    """End-to-end: exact CLI shape used by archive-plan.md (`request read --section source`)."""
    with PlanContext(plan_id='archive-plan-source') as ctx:
        _write_phase1_request(ctx, 'archive-plan-source')

        result = run_script(
            SCRIPT_PATH,
            'request',
            'read',
            '--plan-id',
            'archive-plan-source',
            '--section',
            'source',
        )
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert data['section'] == 'source'
        assert data['content'] == 'issue'


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


def test_cli_request_path_subcommand():
    """CLI plumbing: `request path` returns canonical path via TOON."""
    with PlanContext(plan_id='cli-path'):
        # Create first
        run_script(
            SCRIPT_PATH,
            'request',
            'create',
            '--plan-id',
            'cli-path',
            '--title',
            'Test',
            '--source',
            'description',
            '--body',
            'Body',
        )
        result = run_script(
            SCRIPT_PATH,
            'request',
            'path',
            '--plan-id',
            'cli-path',
        )
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert 'path' in data
        assert data['path'].endswith('request.md')


def test_cli_request_mark_clarified_subcommand():
    """CLI plumbing: `request mark-clarified` validates the edited file."""
    with PlanContext(plan_id='cli-mc') as ctx:
        # Create, then directly edit to add Clarified Request section
        run_script(
            SCRIPT_PATH,
            'request',
            'create',
            '--plan-id',
            'cli-mc',
            '--title',
            'Test',
            '--source',
            'description',
            '--body',
            'Body',
        )
        target = ctx.plan_dir / 'request.md'
        target.write_text(
            target.read_text() + '\n## Clarified Request\n\nClarified text\n'
        )
        result = run_script(
            SCRIPT_PATH,
            'request',
            'mark-clarified',
            '--plan-id',
            'cli-mc',
        )
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'

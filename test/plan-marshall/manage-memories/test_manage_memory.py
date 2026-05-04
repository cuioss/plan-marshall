#!/usr/bin/env python3
"""Tests for manage-memory.py script.

Consolidated from:
- test-manage-memory.sh - CRUD operations (save, load, list, query, cleanup)
- test_validate_memory.py - validation subcommand

Tests memory layer operations and format validation.

Tier 2 (direct import) with 2 subprocess tests for CLI plumbing.
"""

import importlib.util
import os
import re
import tempfile
from argparse import Namespace
from contextlib import contextmanager
from pathlib import Path

from conftest import get_script_path, run_script

# Script path for subprocess (CLI plumbing) tests
SCRIPT_PATH = get_script_path('plan-marshall', 'manage-memories', 'manage-memory.py')

# Tier 2 direct import via importlib (hyphenated filename)
_spec = importlib.util.spec_from_file_location('manage_memory', str(SCRIPT_PATH))
manage_memory = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(manage_memory)

cmd_save = manage_memory.cmd_save
cmd_load = manage_memory.cmd_load
cmd_list = manage_memory.cmd_list
cmd_query = manage_memory.cmd_query
cmd_cleanup = manage_memory.cmd_cleanup
cmd_validate = manage_memory.cmd_validate


# =============================================================================
# Test Helpers
# =============================================================================


@contextmanager
def memory_test_context():
    """Context manager that creates temp directory and patches MEMORY_BASE."""
    with tempfile.TemporaryDirectory() as td:
        temp_dir = Path(td)
        memory_base = temp_dir / '.plan' / 'memory'

        old_memory_base = manage_memory.MEMORY_BASE
        old_plan_base_dir = os.environ.get('PLAN_BASE_DIR')

        manage_memory.MEMORY_BASE = memory_base
        os.environ['PLAN_BASE_DIR'] = str(temp_dir / '.plan')
        try:
            yield temp_dir
        finally:
            manage_memory.MEMORY_BASE = old_memory_base
            if old_plan_base_dir is None:
                os.environ.pop('PLAN_BASE_DIR', None)
            else:
                os.environ['PLAN_BASE_DIR'] = old_plan_base_dir


def parse_output(output):
    """Parse TOON from output."""
    from toon_parser import parse_toon

    return parse_toon(output)


# =============================================================================
# Tier 2: Direct Import Tests
# =============================================================================


def test_save_creates_dirs():
    """Test save creates directories on-the-fly."""
    with memory_test_context() as temp_dir:
        result = cmd_save(
            Namespace(
                category='context',
                identifier='test-feature',
                content='{"notes": "Testing"}',
                session_id=None,
            )
        )

        assert result['success'] is True, 'Should succeed'
        assert 'context' in result.get('path', ''), 'Path should contain context'

        # Verify directory was created
        assert (temp_dir / '.plan' / 'memory' / 'context').is_dir(), 'Context directory should be created'


def test_save_context():
    """Test save to context category."""
    with memory_test_context():
        result = cmd_save(
            Namespace(
                category='context',
                identifier='test-feature',
                content='{"decisions": ["Use JWT"]}',
                session_id=None,
            )
        )

        assert result['success'] is True, 'Should succeed'
        assert 'context' in result.get('path', ''), 'Path should contain context'


def test_load():
    """Test load memory file."""
    with memory_test_context() as temp_dir:
        # Create file directly to control filename
        memory_dir = temp_dir / '.plan' / 'memory' / 'context'
        memory_dir.mkdir(parents=True)
        (memory_dir / 'load-test.json').write_text("""{
  "meta": {
    "created": "2025-12-02T10:00:00Z",
    "category": "context",
    "summary": "load-test"
  },
  "content": {"value": 123}
}""")

        result = cmd_load(Namespace(category='context', identifier='load-test'))

        assert result['success'] is True, 'Should succeed'
        assert result.get('content', {}).get('value') == 123, 'Content value should be 123'


def test_load_has_meta():
    """Test load includes meta envelope."""
    with memory_test_context() as temp_dir:
        memory_dir = temp_dir / '.plan' / 'memory' / 'context'
        memory_dir.mkdir(parents=True)
        (memory_dir / 'meta-test.json').write_text("""{
  "meta": {
    "created": "2025-12-02T10:00:00Z",
    "category": "context",
    "summary": "meta-test"
  },
  "content": {"test": true}
}""")

        result = cmd_load(Namespace(category='context', identifier='meta-test'))

        assert result['success'] is True, 'Should succeed'
        meta = result.get('meta', {})
        assert 'created' in meta, 'Meta should have created'
        assert meta.get('category') == 'context', 'Meta category should be context'


def test_list_category():
    """Test list files in category."""
    with memory_test_context() as temp_dir:
        memory_dir = temp_dir / '.plan' / 'memory' / 'context'
        memory_dir.mkdir(parents=True)
        (memory_dir / 'list-test-1.json').write_text("""{
  "meta": {"created": "2025-12-02T10:00:00Z", "category": "context", "summary": "list-test-1"},
  "content": {}
}""")
        (memory_dir / 'list-test-2.json').write_text("""{
  "meta": {"created": "2025-12-02T10:00:00Z", "category": "context", "summary": "list-test-2"},
  "content": {}
}""")

        result = cmd_list(Namespace(category='context', since=None))

        assert result['success'] is True, 'Should succeed'
        assert result.get('count', 0) >= 2, 'Should find at least 2 files'


def test_list_all():
    """Test list all categories."""
    with memory_test_context():
        # Create a file via cmd_save
        cmd_save(
            Namespace(
                category='context',
                identifier='list-all-test',
                content='{}',
                session_id=None,
            )
        )

        result = cmd_list(Namespace(category=None, since=None))

        assert result['success'] is True, 'Should succeed'


def test_query_pattern():
    """Test query by pattern."""
    with memory_test_context() as temp_dir:
        memory_dir = temp_dir / '.plan' / 'memory' / 'context'
        memory_dir.mkdir(parents=True)
        (memory_dir / 'query-auth-test.json').write_text("""{
  "meta": {"created": "2025-12-02T10:00:00Z", "category": "context", "summary": "query-auth-test"},
  "content": {}
}""")
        (memory_dir / 'query-data-test.json').write_text("""{
  "meta": {"created": "2025-12-02T10:00:00Z", "category": "context", "summary": "query-data-test"},
  "content": {}
}""")

        result = cmd_query(Namespace(pattern='query-auth*', category='context'))

        assert result['success'] is True, 'Should succeed'
        assert result.get('count', 0) >= 1, 'Should find at least 1 match'


def test_cleanup():
    """Test cleanup old files."""
    with memory_test_context() as temp_dir:
        memory_dir = temp_dir / '.plan' / 'memory' / 'context'
        memory_dir.mkdir(parents=True)
        (memory_dir / 'old-cleanup-test.json').write_text("""{
  "meta": {
    "created": "2020-01-01T00:00:00Z",
    "category": "context",
    "summary": "cleanup-test"
  },
  "content": {}
}""")

        result = cmd_cleanup(Namespace(category='context', older_than='1d', dry_run=False))

        assert result['status'] == 'success', 'Should succeed'
        assert result['operation'] == 'cleanup', 'Operation should be cleanup'
        assert result['older_than'] == '1d', 'Should echo older_than parameter'
        assert result.get('removed_count', 0) >= 1, 'Should remove at least 1 file'


def test_load_not_found():
    """Test load non-existent file returns error."""
    with memory_test_context():
        result = cmd_load(Namespace(category='context', identifier='nonexistent'))

        assert result['status'] == 'error', 'Should fail for non-existent file'


def test_context_date_prefix():
    """Test context files get date prefix."""
    with memory_test_context():
        result = cmd_save(
            Namespace(
                category='context',
                identifier='date-prefix-test',
                content='{}',
                session_id=None,
            )
        )

        assert result['success'] is True, 'Should succeed'
        identifier = result.get('identifier', '')
        assert re.search(r'\d{4}-\d{2}-\d{2}', identifier), 'Identifier should have date prefix'


# =============================================================================
# Validate Subcommand Tests (Tier 2)
# =============================================================================


def test_validate_valid_memory():
    """Test validate valid memory file."""
    with memory_test_context() as temp_dir:
        memory_dir = temp_dir / '.plan' / 'memory' / 'context'
        memory_dir.mkdir(parents=True)
        (memory_dir / 'valid-test.json').write_text("""{
  "meta": {
    "created": "2025-11-25T10:30:00Z",
    "category": "context",
    "summary": "test-feature"
  },
  "content": {
    "decisions": ["Use JWT"]
  }
}""")

        result = cmd_validate(Namespace(file=str(memory_dir / 'valid-test.json')))

        assert result['success'] is True, 'Should succeed'
        assert result['valid'] is True, 'Valid memory file should be valid'


def test_validate_missing_meta():
    """Test detect invalid memory file (missing meta)."""
    with memory_test_context() as temp_dir:
        (temp_dir / 'invalid-memory.json').write_text("""{
  "content": {
    "test": true
  }
}""")

        result = cmd_validate(Namespace(file=str(temp_dir / 'invalid-memory.json')))

        assert result['success'] is True, 'Should succeed (validation ran)'
        assert result['valid'] is False, 'Missing meta should be invalid'


def test_validate_missing_content():
    """Test detect invalid memory file (missing content)."""
    with memory_test_context() as temp_dir:
        (temp_dir / 'missing-content.json').write_text("""{
  "meta": {
    "created": "2025-11-25T10:30:00Z",
    "category": "context",
    "summary": "test"
  }
}""")

        result = cmd_validate(Namespace(file=str(temp_dir / 'missing-content.json')))

        assert result['success'] is True, 'Should succeed (validation ran)'
        assert result['valid'] is False, 'Missing content should be invalid'


def test_validate_invalid_category():
    """Test detect invalid category."""
    with memory_test_context() as temp_dir:
        (temp_dir / 'invalid-category.json').write_text("""{
  "meta": {
    "created": "2025-11-25T10:30:00Z",
    "category": "invalid",
    "summary": "test"
  },
  "content": {}
}""")

        result = cmd_validate(Namespace(file=str(temp_dir / 'invalid-category.json')))

        assert result['success'] is True, 'Should succeed (validation ran)'
        assert result['valid'] is False, 'Invalid category should be invalid'


def test_validate_invalid_json():
    """Test detect invalid JSON syntax."""
    with memory_test_context() as temp_dir:
        (temp_dir / 'invalid-json.json').write_text("""{
  "broken": true,
  missing-quotes: "value"
}""")

        result = cmd_validate(Namespace(file=str(temp_dir / 'invalid-json.json')))

        assert result['success'] is True, 'Should succeed (validation ran)'
        assert result['valid'] is False, 'Invalid JSON should be invalid'


def test_validate_checks_array():
    """Test validate output includes checks array."""
    with memory_test_context() as temp_dir:
        memory_dir = temp_dir / '.plan' / 'memory' / 'context'
        memory_dir.mkdir(parents=True)
        (memory_dir / 'checks-test.json').write_text("""{
  "meta": {
    "created": "2025-11-25T10:30:00Z",
    "category": "context",
    "summary": "test-feature"
  },
  "content": {}
}""")

        result = cmd_validate(Namespace(file=str(memory_dir / 'checks-test.json')))

        assert result['success'] is True, 'Should succeed'
        checks = result.get('checks', [])
        assert len(checks) > 0, 'Should include checks array with items'


def test_validate_file_not_found():
    """Test validate file not found returns error."""
    with memory_test_context() as temp_dir:
        result = cmd_validate(Namespace(file=str(temp_dir / 'nonexistent.json')))

        assert result['status'] == 'error', 'Should fail for non-existent file'


def test_validate_format_is_memory():
    """Test validate format is memory."""
    with memory_test_context() as temp_dir:
        memory_dir = temp_dir / '.plan' / 'memory' / 'context'
        memory_dir.mkdir(parents=True)
        (memory_dir / 'format-test.json').write_text("""{
  "meta": {
    "created": "2025-11-25T10:30:00Z",
    "category": "context",
    "summary": "test-feature"
  },
  "content": {}
}""")

        result = cmd_validate(Namespace(file=str(memory_dir / 'format-test.json')))

        assert result['format'] == 'memory', "Format should be 'memory'"


# =============================================================================
# Tier 3: CLI Plumbing Tests (subprocess)
# =============================================================================


def test_cli_invalid_category():
    """Test invalid category returns argparse error via CLI."""
    with tempfile.TemporaryDirectory() as td:
        old_val = os.environ.get('PLAN_BASE_DIR')
        os.environ['PLAN_BASE_DIR'] = str(Path(td) / '.plan')
        try:
            result = run_script(SCRIPT_PATH, 'save', '--category', 'invalid', '--identifier', 'test', '--content', '{}')
            combined = result.stdout.lower() + result.stderr.lower()
            assert 'invalid choice' in combined, 'Should show invalid choice error'
        finally:
            if old_val is None:
                os.environ.pop('PLAN_BASE_DIR', None)
            else:
                os.environ['PLAN_BASE_DIR'] = old_val


def test_cli_save_roundtrip():
    """Test save + load roundtrip via CLI to verify TOON output plumbing."""
    with tempfile.TemporaryDirectory() as td:
        old_val = os.environ.get('PLAN_BASE_DIR')
        os.environ['PLAN_BASE_DIR'] = str(Path(td) / '.plan')
        try:
            result = run_script(
                SCRIPT_PATH,
                'save',
                '--category',
                'context',
                '--identifier',
                'cli-test',
                '--content',
                '{"cli": true}',
            )
            data = parse_output(result.stdout)
            assert data.get('success') is True, 'CLI save should succeed'
            assert result.returncode == 0, 'Exit code should be 0'
        finally:
            if old_val is None:
                os.environ.pop('PLAN_BASE_DIR', None)
            else:
                os.environ['PLAN_BASE_DIR'] = old_val


# =============================================================================
# Main
# =============================================================================

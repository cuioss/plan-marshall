#!/usr/bin/env python3
"""Tests for manage-memory.py script.

Consolidated from:
- test-manage-memory.sh - CRUD operations (save, load, list, query, cleanup)
- test_validate_memory.py - validation subcommand

Tests memory layer operations and format validation.
"""

import os
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import _MARKETPLACE_SCRIPT_DIRS, get_script_path

# Script under test
SCRIPT_PATH = get_script_path('plan-marshall', 'manage-memories', 'manage-memory.py')


# =============================================================================
# Test Helpers
# =============================================================================


@contextmanager
def memory_test_context():
    """Context manager that creates temp directory and sets PLAN_BASE_DIR."""
    with tempfile.TemporaryDirectory() as td:
        temp_dir = Path(td)
        old_plan_base_dir = os.environ.get('PLAN_BASE_DIR')
        # Set PLAN_BASE_DIR to temp_dir/.plan for script to find files
        os.environ['PLAN_BASE_DIR'] = str(temp_dir / '.plan')
        try:
            yield temp_dir
        finally:
            # Restore original PLAN_BASE_DIR
            if old_plan_base_dir is None:
                os.environ.pop('PLAN_BASE_DIR', None)
            else:
                os.environ['PLAN_BASE_DIR'] = old_plan_base_dir


def run_memory_script(*args):
    """Run the memory script with arguments."""
    env = os.environ.copy()
    pythonpath = os.pathsep.join(_MARKETPLACE_SCRIPT_DIRS)
    if 'PYTHONPATH' in env:
        pythonpath = pythonpath + os.pathsep + env['PYTHONPATH']
    env['PYTHONPATH'] = pythonpath
    proc = subprocess.run(['python3', str(SCRIPT_PATH), *args], capture_output=True, text=True, env=env)
    return proc


def parse_json(output):
    """Parse JSON from output."""
    import json

    return json.loads(output)


# =============================================================================
# Tests
# =============================================================================


def test_save_creates_dirs():
    """Test save creates directories on-the-fly."""
    with memory_test_context() as temp_dir:
        result = run_memory_script(
            'save', '--category', 'context', '--identifier', 'test-feature', '--content', '{"notes": "Testing"}'
        )
        data = parse_json(result.stdout)

        assert data.get('success') is True, 'Should succeed'
        assert 'context' in data.get('path', ''), 'Path should contain context'

        # Verify directory was created (uses .plan/memory, not .claude/memory)
        assert (temp_dir / '.plan' / 'memory' / 'context').is_dir(), 'Context directory should be created'


def test_save_context():
    """Test save to context category."""
    with memory_test_context():
        result = run_memory_script(
            'save', '--category', 'context', '--identifier', 'test-feature', '--content', '{"decisions": ["Use JWT"]}'
        )
        data = parse_json(result.stdout)

        assert data.get('success') is True, 'Should succeed'
        assert 'context' in data.get('path', ''), 'Path should contain context'


def test_load():
    """Test load memory file."""
    with memory_test_context() as temp_dir:
        # First save - context category adds date prefix, so create file directly
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

        result = run_memory_script('load', '--category', 'context', '--identifier', 'load-test')
        data = parse_json(result.stdout)

        assert data.get('success') is True, 'Should succeed'
        assert data.get('content', {}).get('value') == 123, 'Content value should be 123'


def test_load_has_meta():
    """Test load includes meta envelope."""
    with memory_test_context() as temp_dir:
        # Create file directly to avoid date prefix
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

        result = run_memory_script('load', '--category', 'context', '--identifier', 'meta-test')
        data = parse_json(result.stdout)

        assert data.get('success') is True, 'Should succeed'
        meta = data.get('meta', {})
        assert 'created' in meta, 'Meta should have created'
        assert meta.get('category') == 'context', 'Meta category should be context'


def test_list_category():
    """Test list files in category."""
    with memory_test_context() as temp_dir:
        # Create files directly to avoid date prefix issues
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

        result = run_memory_script('list', '--category', 'context')
        data = parse_json(result.stdout)

        assert data.get('success') is True, 'Should succeed'
        assert data.get('count', 0) >= 2, 'Should find at least 2 files'


def test_list_all():
    """Test list all categories."""
    with memory_test_context():
        # Create at least one file
        run_memory_script('save', '--category', 'context', '--identifier', 'list-all-test', '--content', '{}')

        result = run_memory_script('list')
        data = parse_json(result.stdout)

        assert data.get('success') is True, 'Should succeed'


def test_query_pattern():
    """Test query by pattern."""
    with memory_test_context() as temp_dir:
        # Create files directly to avoid date prefix issues
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

        result = run_memory_script('query', '--pattern', 'query-auth*', '--category', 'context')
        data = parse_json(result.stdout)

        assert data.get('success') is True, 'Should succeed'
        assert data.get('count', 0) >= 1, 'Should find at least 1 match'


def test_cleanup():
    """Test cleanup old files."""
    with memory_test_context() as temp_dir:
        # Create a file with an old created timestamp directly in the JSON
        # Uses .plan/memory, not .claude/memory
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

        result = run_memory_script('cleanup', '--category', 'context', '--older-than', '1d')
        data = parse_json(result.stdout)

        assert data.get('success') is True, 'Should succeed'
        assert data.get('removed_count', 0) >= 1, 'Should remove at least 1 file'


def test_load_not_found():
    """Test load non-existent file returns error."""
    with memory_test_context():
        result = run_memory_script('load', '--category', 'context', '--identifier', 'nonexistent')
        # Script may output to stderr for errors
        output = result.stdout if result.stdout.strip() else result.stderr
        data = parse_json(output)

        assert data.get('success') is False, 'Should fail for non-existent file'


def test_invalid_category():
    """Test invalid category returns error."""
    with memory_test_context():
        result = run_memory_script('save', '--category', 'invalid', '--identifier', 'test', '--content', '{}')

        combined = result.stdout.lower() + result.stderr.lower()
        assert 'invalid choice' in combined, 'Should show invalid choice error'


def test_context_date_prefix():
    """Test context files get date prefix."""
    with memory_test_context():
        import re

        result = run_memory_script(
            'save', '--category', 'context', '--identifier', 'date-prefix-test', '--content', '{}'
        )
        data = parse_json(result.stdout)

        assert data.get('success') is True, 'Should succeed'
        identifier = data.get('identifier', '')
        assert re.search(r'\d{4}-\d{2}-\d{2}', identifier), 'Identifier should have date prefix'


# =============================================================================
# Validate Subcommand Tests
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

        result = run_memory_script('validate', '--file', str(memory_dir / 'valid-test.json'))
        data = parse_json(result.stdout)

        assert data.get('success') is True, 'Should succeed'
        assert data.get('valid') is True, 'Valid memory file should be valid'


def test_validate_missing_meta():
    """Test detect invalid memory file (missing meta)."""
    with memory_test_context() as temp_dir:
        (temp_dir / 'invalid-memory.json').write_text("""{
  "content": {
    "test": true
  }
}""")

        result = run_memory_script('validate', '--file', str(temp_dir / 'invalid-memory.json'))
        data = parse_json(result.stdout)

        assert data.get('success') is True, 'Should succeed (validation ran)'
        assert data.get('valid') is False, 'Missing meta should be invalid'


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

        result = run_memory_script('validate', '--file', str(temp_dir / 'missing-content.json'))
        data = parse_json(result.stdout)

        assert data.get('success') is True, 'Should succeed (validation ran)'
        assert data.get('valid') is False, 'Missing content should be invalid'


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

        result = run_memory_script('validate', '--file', str(temp_dir / 'invalid-category.json'))
        data = parse_json(result.stdout)

        assert data.get('success') is True, 'Should succeed (validation ran)'
        assert data.get('valid') is False, 'Invalid category should be invalid'


def test_validate_invalid_json():
    """Test detect invalid JSON syntax."""
    with memory_test_context() as temp_dir:
        (temp_dir / 'invalid-json.json').write_text("""{
  "broken": true,
  missing-quotes: "value"
}""")

        result = run_memory_script('validate', '--file', str(temp_dir / 'invalid-json.json'))
        data = parse_json(result.stdout)

        assert data.get('success') is True, 'Should succeed (validation ran)'
        assert data.get('valid') is False, 'Invalid JSON should be invalid'


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

        result = run_memory_script('validate', '--file', str(memory_dir / 'checks-test.json'))
        data = parse_json(result.stdout)

        assert data.get('success') is True, 'Should succeed'
        checks = data.get('checks', [])
        assert len(checks) > 0, 'Should include checks array with items'


def test_validate_file_not_found():
    """Test validate file not found returns error."""
    with memory_test_context() as temp_dir:
        result = run_memory_script('validate', '--file', str(temp_dir / 'nonexistent.json'))
        output = result.stdout if result.stdout.strip() else result.stderr
        data = parse_json(output)

        assert data.get('success') is False, 'Should fail for non-existent file'


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

        result = run_memory_script('validate', '--file', str(memory_dir / 'format-test.json'))
        data = parse_json(result.stdout)

        assert data.get('format') == 'memory', "Format should be 'memory'"


# =============================================================================
# Main
# =============================================================================

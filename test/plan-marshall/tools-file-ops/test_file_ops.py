#!/usr/bin/env python3
"""
Tests for the file_ops.py module.

Tests functions:
- atomic_write_file: Atomic file writing with temp file + rename
- ensure_directory: Directory creation (mkdir -p equivalent)
- output_success/output_error: TOON output helpers
- parse_markdown_metadata: Key=value metadata parsing
- generate_markdown_metadata: Metadata block generation
- update_markdown_metadata: Metadata field updates
- get_metadata_content_split: Split metadata from body
- get_base_dir/set_base_dir/base_path: Base directory configuration
"""

import sys
from io import StringIO
from pathlib import Path

from file_ops import (
    atomic_write_file,
    base_path,
    ensure_directory,
    generate_markdown_metadata,
    get_base_dir,
    get_metadata_content_split,
    get_temp_dir,
    output_error,
    output_success,
    parse_markdown_metadata,
    set_base_dir,
    update_markdown_metadata,
)
from toon_parser import parse_toon

# =============================================================================
# get_temp_dir tests
# =============================================================================


def test_get_temp_dir_default(tmp_path, monkeypatch):
    """Test get_temp_dir returns .plan/temp by default."""
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
    result = get_temp_dir()
    assert result == tmp_path / 'temp'


def test_get_temp_dir_with_subdir(tmp_path, monkeypatch):
    """Test get_temp_dir with subdirectory appends correctly."""
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
    result = get_temp_dir('tools-marketplace-inventory')
    assert result == tmp_path / 'temp' / 'tools-marketplace-inventory'


def test_get_temp_dir_without_subdir_is_none(tmp_path, monkeypatch):
    """Test get_temp_dir with None subdir returns temp root."""
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
    result = get_temp_dir(None)
    assert result == tmp_path / 'temp'


# =============================================================================
# atomic_write_file tests
# =============================================================================


def test_atomic_write_file_creates_file(tmp_path):
    """Test atomic_write_file creates file with content."""
    path = tmp_path / 'test.txt'
    content = 'Hello, World!'

    atomic_write_file(path, content)

    assert path.exists()
    assert path.read_text() == content + '\n'


def test_atomic_write_file_creates_parent_dirs(tmp_path):
    """Test atomic_write_file creates parent directories."""
    path = tmp_path / 'nested' / 'dir' / 'test.txt'
    content = 'Nested content'

    atomic_write_file(path, content)

    assert path.exists()
    assert path.read_text() == content + '\n'


def test_atomic_write_file_preserves_trailing_newline(tmp_path):
    """Test atomic_write_file doesn't double newlines."""
    path = tmp_path / 'test.txt'
    content = 'Content with newline\n'

    atomic_write_file(path, content)

    assert path.read_text() == content


# =============================================================================
# ensure_directory tests
# =============================================================================


def test_ensure_directory_creates_directory(tmp_path):
    """Test ensure_directory creates directory."""
    path = tmp_path / 'new' / 'nested' / 'dir'

    result = ensure_directory(path)

    assert path.exists()
    assert path.is_dir()
    assert result == path


def test_ensure_directory_with_file_path(tmp_path):
    """Test ensure_directory creates parent when given file path."""
    path = tmp_path / 'parent' / 'file.txt'

    result = ensure_directory(path)

    expected_dir = tmp_path / 'parent'
    assert expected_dir.exists()
    assert expected_dir.is_dir()
    assert result == expected_dir


def test_ensure_directory_idempotent(tmp_path):
    """Test ensure_directory is idempotent."""
    path = tmp_path / 'existing'
    path.mkdir()

    result = ensure_directory(path)

    assert path.exists()
    assert result == path


# =============================================================================
# output_success/output_error tests (TOON format)
# =============================================================================


def test_output_success_format():
    """Test output_success produces correct TOON."""
    old_stdout = sys.stdout
    sys.stdout = StringIO()

    output_success('test-op', file='test.txt', count=5)

    output = sys.stdout.getvalue()
    sys.stdout = old_stdout

    result = parse_toon(output)
    assert result['success'] is True
    assert result['operation'] == 'test-op'
    assert result['file'] == 'test.txt'
    assert result['count'] == 5


def test_output_error_format():
    """Test output_error produces correct TOON to stderr."""
    old_stderr = sys.stderr
    sys.stderr = StringIO()

    output_error('test-op', 'Something went wrong')

    output = sys.stderr.getvalue()
    sys.stderr = old_stderr

    result = parse_toon(output)
    assert result['success'] is False
    assert result['operation'] == 'test-op'
    assert result['error'] == 'Something went wrong'


# =============================================================================
# parse_markdown_metadata tests
# =============================================================================


def test_parse_markdown_metadata_basic():
    """Test parse_markdown_metadata with basic content."""
    content = """id=2025-11-28-001
component.type=command
applied=false

# Title

Content here..."""

    result = parse_markdown_metadata(content)

    assert result['id'] == '2025-11-28-001'
    assert result['component.type'] == 'command'
    assert result['applied'] == 'false'
    assert len(result) == 3


def test_parse_markdown_metadata_empty_content():
    """Test parse_markdown_metadata with empty content."""
    result = parse_markdown_metadata('')
    assert result == {}


def test_parse_markdown_metadata_no_metadata():
    """Test parse_markdown_metadata with only content."""
    content = """# Title

Just content, no metadata."""

    result = parse_markdown_metadata(content)
    assert result == {}


def test_parse_markdown_metadata_with_equals_in_value():
    """Test parse_markdown_metadata handles = in values."""
    content = """key=value=with=equals
other=normal

# Title"""

    result = parse_markdown_metadata(content)

    assert result['key'] == 'value=with=equals'
    assert result['other'] == 'normal'


# =============================================================================
# generate_markdown_metadata tests
# =============================================================================


def test_generate_markdown_metadata_basic():
    """Test generate_markdown_metadata with basic data."""
    data = {'id': '2025-11-28-001', 'component.type': 'command', 'applied': 'false'}

    result = generate_markdown_metadata(data)

    assert 'id=2025-11-28-001' in result
    assert 'component.type=command' in result
    assert 'applied=false' in result


def test_generate_markdown_metadata_empty():
    """Test generate_markdown_metadata with empty data."""
    result = generate_markdown_metadata({})
    assert result == ''


# =============================================================================
# update_markdown_metadata tests
# =============================================================================


def test_update_markdown_metadata_updates_existing():
    """Test update_markdown_metadata updates existing keys."""
    content = """id=2025-11-28-001
applied=false

# Title

Content"""

    result = update_markdown_metadata(content, {'applied': 'true'})

    assert 'applied=true' in result
    assert 'applied=false' not in result
    assert 'id=2025-11-28-001' in result
    assert '# Title' in result


def test_update_markdown_metadata_adds_new():
    """Test update_markdown_metadata adds new keys."""
    content = """id=2025-11-28-001

# Title"""

    result = update_markdown_metadata(content, {'new_key': 'new_value'})

    assert 'id=2025-11-28-001' in result
    assert 'new_key=new_value' in result


# =============================================================================
# get_metadata_content_split tests
# =============================================================================


def test_get_metadata_content_split_basic():
    """Test get_metadata_content_split with basic content."""
    content = """id=2025-11-28-001
applied=false

# Title

Content here..."""

    metadata, body = get_metadata_content_split(content)

    assert 'id=2025-11-28-001' in metadata
    assert 'applied=false' in metadata
    assert '# Title' in body
    assert 'Content here' in body


def test_get_metadata_content_split_no_metadata():
    """Test get_metadata_content_split with no metadata."""
    content = """# Title

Just content"""

    metadata, body = get_metadata_content_split(content)

    assert metadata == ''
    assert '# Title' in body


# =============================================================================
# Integration tests
# =============================================================================


def test_roundtrip_metadata():
    """Test that generate and parse are inverse operations."""
    original = {'id': '2025-11-28-001', 'component.type': 'command', 'component.name': 'test-cmd', 'applied': 'false'}

    generated = generate_markdown_metadata(original)
    parsed = parse_markdown_metadata(generated)

    assert parsed == original


# =============================================================================
# get_base_dir/set_base_dir tests
# =============================================================================


def test_get_base_dir_default():
    """Test get_base_dir returns default .plan path."""
    set_base_dir('.plan')
    result = get_base_dir()
    assert result == Path('.plan')


def test_set_base_dir_changes_default():
    """Test set_base_dir changes the base directory."""
    original = get_base_dir()
    try:
        set_base_dir('/custom/path')
        result = get_base_dir()
        assert result == Path('/custom/path')
    finally:
        set_base_dir(original)


def test_set_base_dir_accepts_string():
    """Test set_base_dir accepts string argument."""
    original = get_base_dir()
    try:
        set_base_dir('/string/path')
        result = get_base_dir()
        assert isinstance(result, Path)
        assert result == Path('/string/path')
    finally:
        set_base_dir(original)


# =============================================================================
# base_path tests
# =============================================================================


def test_base_path_basic():
    """Test base_path constructs path within base directory."""
    set_base_dir('.plan')
    result = base_path('plans', 'my-task', 'plan.md')
    assert result == Path('.plan/plans/my-task/plan.md')


def test_base_path_single_part():
    """Test base_path with single path part."""
    set_base_dir('.plan')
    result = base_path('config.json')
    assert result == Path('.plan/config.json')


def test_base_path_no_parts():
    """Test base_path with no parts returns base directory."""
    set_base_dir('.plan')
    result = base_path()
    assert result == Path('.plan')


def test_base_path_respects_custom_base():
    """Test base_path uses custom base directory."""
    original = get_base_dir()
    try:
        set_base_dir('/custom/base')
        result = base_path('plans', 'task')
        assert result == Path('/custom/base/plans/task')
    finally:
        set_base_dir(original)

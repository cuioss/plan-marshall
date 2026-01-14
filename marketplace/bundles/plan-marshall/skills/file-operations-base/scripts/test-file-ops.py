#!/usr/bin/env python3
"""
Test suite for file_ops.py module.

Usage:
    python3 test-file-ops.py
"""

import json
import sys
import tempfile
from io import StringIO
from pathlib import Path

# Import module under test
from file_ops import (
    atomic_write_file,
    base_path,
    ensure_directory,
    generate_markdown_metadata,
    get_base_dir,
    get_metadata_content_split,
    output_error,
    output_success,
    parse_markdown_metadata,
    set_base_dir,
    update_markdown_metadata,
)


class TestRunner:
    """Simple test runner for stdlib-only testing."""

    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.failures = []

    def run_test(self, name: str, test_func):
        """Run a single test function."""
        self.tests_run += 1
        try:
            test_func()
            self.tests_passed += 1
            print(f"  ✓ {name}")
        except AssertionError as e:
            self.tests_failed += 1
            self.failures.append((name, str(e)))
            print(f"  ✗ {name}: {e}")
        except Exception as e:
            self.tests_failed += 1
            self.failures.append((name, f"Exception: {e}"))
            print(f"  ✗ {name}: Exception: {e}")

    def summary(self):
        """Print test summary and return exit code."""
        print("\n" + "=" * 50)
        print(f"Tests: {self.tests_run}, Passed: {self.tests_passed}, Failed: {self.tests_failed}")

        if self.failures:
            print("\nFailures:")
            for name, msg in self.failures:
                print(f"  - {name}: {msg}")

        return 0 if self.tests_failed == 0 else 1


def test_atomic_write_file_creates_file():
    """Test atomic_write_file creates file with content."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test.txt"
        content = "Hello, World!"

        atomic_write_file(path, content)

        assert path.exists(), "File should exist"
        assert path.read_text() == content + "\n", "Content should match (with newline)"


def test_atomic_write_file_creates_parent_dirs():
    """Test atomic_write_file creates parent directories."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "nested" / "dir" / "test.txt"
        content = "Nested content"

        atomic_write_file(path, content)

        assert path.exists(), "File should exist"
        assert path.read_text() == content + "\n", "Content should match"


def test_atomic_write_file_preserves_trailing_newline():
    """Test atomic_write_file doesn't double newlines."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test.txt"
        content = "Content with newline\n"

        atomic_write_file(path, content)

        assert path.read_text() == content, "Should not add extra newline"


def test_ensure_directory_creates_directory():
    """Test ensure_directory creates directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "new" / "nested" / "dir"

        result = ensure_directory(path)

        assert path.exists(), "Directory should exist"
        assert path.is_dir(), "Should be a directory"
        assert result == path, "Should return path"


def test_ensure_directory_with_file_path():
    """Test ensure_directory creates parent when given file path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "parent" / "file.txt"

        result = ensure_directory(path)

        expected_dir = Path(tmpdir) / "parent"
        assert expected_dir.exists(), "Parent directory should exist"
        assert expected_dir.is_dir(), "Should be a directory"
        assert result == expected_dir, "Should return parent directory"


def test_ensure_directory_idempotent():
    """Test ensure_directory is idempotent."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "existing"
        path.mkdir()

        # Should not raise
        result = ensure_directory(path)

        assert path.exists(), "Directory should still exist"
        assert result == path, "Should return path"


def test_output_success_format():
    """Test output_success produces correct JSON."""
    # Capture stdout
    old_stdout = sys.stdout
    sys.stdout = StringIO()

    output_success("test-op", file="test.txt", count=5)

    output = sys.stdout.getvalue()
    sys.stdout = old_stdout

    result = json.loads(output)
    assert result["success"] is True, "success should be True"
    assert result["operation"] == "test-op", "operation should match"
    assert result["file"] == "test.txt", "file should match"
    assert result["count"] == 5, "count should match"


def test_output_error_format():
    """Test output_error produces correct JSON to stderr."""
    # Capture stderr
    old_stderr = sys.stderr
    sys.stderr = StringIO()

    output_error("test-op", "Something went wrong")

    output = sys.stderr.getvalue()
    sys.stderr = old_stderr

    result = json.loads(output)
    assert result["success"] is False, "success should be False"
    assert result["operation"] == "test-op", "operation should match"
    assert result["error"] == "Something went wrong", "error should match"


def test_parse_markdown_metadata_basic():
    """Test parse_markdown_metadata with basic content."""
    content = """id=2025-11-28-001
component.type=command
applied=false

# Title

Content here..."""

    result = parse_markdown_metadata(content)

    assert result["id"] == "2025-11-28-001", "id should match"
    assert result["component.type"] == "command", "component.type should match"
    assert result["applied"] == "false", "applied should match"
    assert len(result) == 3, "Should have 3 keys"


def test_parse_markdown_metadata_empty_content():
    """Test parse_markdown_metadata with empty content."""
    result = parse_markdown_metadata("")

    assert result == {}, "Should return empty dict"


def test_parse_markdown_metadata_no_metadata():
    """Test parse_markdown_metadata with only content."""
    content = """# Title

Just content, no metadata."""

    result = parse_markdown_metadata(content)

    assert result == {}, "Should return empty dict"


def test_parse_markdown_metadata_with_equals_in_value():
    """Test parse_markdown_metadata handles = in values."""
    content = """key=value=with=equals
other=normal

# Title"""

    result = parse_markdown_metadata(content)

    assert result["key"] == "value=with=equals", "Should preserve = in value"
    assert result["other"] == "normal", "other should match"


def test_generate_markdown_metadata_basic():
    """Test generate_markdown_metadata with basic data."""
    data = {
        "id": "2025-11-28-001",
        "component.type": "command",
        "applied": "false"
    }

    result = generate_markdown_metadata(data)

    assert "id=2025-11-28-001" in result, "Should contain id"
    assert "component.type=command" in result, "Should contain component.type"
    assert "applied=false" in result, "Should contain applied"


def test_generate_markdown_metadata_empty():
    """Test generate_markdown_metadata with empty data."""
    result = generate_markdown_metadata({})

    assert result == "", "Should return empty string"


def test_update_markdown_metadata_updates_existing():
    """Test update_markdown_metadata updates existing keys."""
    content = """id=2025-11-28-001
applied=false

# Title

Content"""

    result = update_markdown_metadata(content, {"applied": "true"})

    assert "applied=true" in result, "Should update applied"
    assert "applied=false" not in result, "Should not have old value"
    assert "id=2025-11-28-001" in result, "Should preserve other keys"
    assert "# Title" in result, "Should preserve content"


def test_update_markdown_metadata_adds_new():
    """Test update_markdown_metadata adds new keys."""
    content = """id=2025-11-28-001

# Title"""

    result = update_markdown_metadata(content, {"new_key": "new_value"})

    assert "id=2025-11-28-001" in result, "Should preserve existing"
    assert "new_key=new_value" in result, "Should add new key"


def test_get_metadata_content_split_basic():
    """Test get_metadata_content_split with basic content."""
    content = """id=2025-11-28-001
applied=false

# Title

Content here..."""

    metadata, body = get_metadata_content_split(content)

    assert "id=2025-11-28-001" in metadata, "Metadata should contain id"
    assert "applied=false" in metadata, "Metadata should contain applied"
    assert "# Title" in body, "Body should contain title"
    assert "Content here" in body, "Body should contain content"


def test_get_metadata_content_split_no_metadata():
    """Test get_metadata_content_split with no metadata."""
    content = """# Title

Just content"""

    metadata, body = get_metadata_content_split(content)

    assert metadata == "", "Metadata should be empty"
    assert "# Title" in body, "Body should contain title"


def test_roundtrip_metadata():
    """Test that generate and parse are inverse operations."""
    original = {
        "id": "2025-11-28-001",
        "component.type": "command",
        "component.name": "test-cmd",
        "applied": "false"
    }

    generated = generate_markdown_metadata(original)
    parsed = parse_markdown_metadata(generated)

    assert parsed == original, "Roundtrip should preserve data"


def test_get_base_dir_default():
    """Test get_base_dir returns default .plan path."""
    # Reset to default first
    set_base_dir('.plan')

    result = get_base_dir()

    assert result == Path('.plan'), "Default should be .plan"


def test_set_base_dir_changes_default():
    """Test set_base_dir changes the base directory."""
    # Save original
    original = get_base_dir()

    try:
        set_base_dir('/custom/path')
        result = get_base_dir()
        assert result == Path('/custom/path'), "Should be changed to custom path"
    finally:
        # Restore original
        set_base_dir(original)


def test_set_base_dir_accepts_string():
    """Test set_base_dir accepts string argument."""
    original = get_base_dir()

    try:
        set_base_dir('/string/path')
        result = get_base_dir()
        assert isinstance(result, Path), "Should return Path object"
        assert result == Path('/string/path'), "Should be correct path"
    finally:
        set_base_dir(original)


def test_base_path_basic():
    """Test base_path constructs path within base directory."""
    set_base_dir('.plan')

    result = base_path('plans', 'my-task', 'plan.md')

    assert result == Path('.plan/plans/my-task/plan.md'), "Should construct full path"


def test_base_path_single_part():
    """Test base_path with single path part."""
    set_base_dir('.plan')

    result = base_path('config.json')

    assert result == Path('.plan/config.json'), "Should construct single-level path"


def test_base_path_no_parts():
    """Test base_path with no parts returns base directory."""
    set_base_dir('.plan')

    result = base_path()

    assert result == Path('.plan'), "Should return base directory"


def test_base_path_respects_custom_base():
    """Test base_path uses custom base directory."""
    original = get_base_dir()

    try:
        set_base_dir('/custom/base')
        result = base_path('plans', 'task')
        assert result == Path('/custom/base/plans/task'), "Should use custom base"
    finally:
        set_base_dir(original)


def main():
    """Run all tests."""
    print("=" * 50)
    print("Test Suite: file_ops.py")
    print("=" * 50)
    print()

    runner = TestRunner()

    # atomic_write_file tests
    print("atomic_write_file:")
    runner.run_test("creates file", test_atomic_write_file_creates_file)
    runner.run_test("creates parent dirs", test_atomic_write_file_creates_parent_dirs)
    runner.run_test("preserves trailing newline", test_atomic_write_file_preserves_trailing_newline)

    # ensure_directory tests
    print("\nensure_directory:")
    runner.run_test("creates directory", test_ensure_directory_creates_directory)
    runner.run_test("with file path", test_ensure_directory_with_file_path)
    runner.run_test("idempotent", test_ensure_directory_idempotent)

    # output_success/output_error tests
    print("\noutput_success/output_error:")
    runner.run_test("success format", test_output_success_format)
    runner.run_test("error format", test_output_error_format)

    # parse_markdown_metadata tests
    print("\nparse_markdown_metadata:")
    runner.run_test("basic", test_parse_markdown_metadata_basic)
    runner.run_test("empty content", test_parse_markdown_metadata_empty_content)
    runner.run_test("no metadata", test_parse_markdown_metadata_no_metadata)
    runner.run_test("equals in value", test_parse_markdown_metadata_with_equals_in_value)

    # generate_markdown_metadata tests
    print("\ngenerate_markdown_metadata:")
    runner.run_test("basic", test_generate_markdown_metadata_basic)
    runner.run_test("empty", test_generate_markdown_metadata_empty)

    # update_markdown_metadata tests
    print("\nupdate_markdown_metadata:")
    runner.run_test("updates existing", test_update_markdown_metadata_updates_existing)
    runner.run_test("adds new", test_update_markdown_metadata_adds_new)

    # get_metadata_content_split tests
    print("\nget_metadata_content_split:")
    runner.run_test("basic", test_get_metadata_content_split_basic)
    runner.run_test("no metadata", test_get_metadata_content_split_no_metadata)

    # Integration tests
    print("\nIntegration:")
    runner.run_test("roundtrip metadata", test_roundtrip_metadata)

    # base directory tests
    print("\nget_base_dir/set_base_dir:")
    runner.run_test("default value", test_get_base_dir_default)
    runner.run_test("changes default", test_set_base_dir_changes_default)
    runner.run_test("accepts string", test_set_base_dir_accepts_string)

    # base_path tests
    print("\nbase_path:")
    runner.run_test("basic", test_base_path_basic)
    runner.run_test("single part", test_base_path_single_part)
    runner.run_test("no parts", test_base_path_no_parts)
    runner.run_test("respects custom base", test_base_path_respects_custom_base)

    return runner.summary()


if __name__ == '__main__':
    sys.exit(main())

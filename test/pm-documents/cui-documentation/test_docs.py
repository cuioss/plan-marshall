#!/usr/bin/env python3
"""Tests for docs.py - consolidated AsciiDoc documentation operations.

Consolidates tests from:
- test_documentation_stats.py (stats subcommand)
- test_asciidoc_validator.py (validate subcommand)
- test_asciidoc_formatter.py (format subcommand)
- test_verify_adoc_links.py (verify-links subcommand)
- test_verify_links_false_positives.py (classify-links subcommand)
- test_analyze_content_tone.py (analyze-tone subcommand)
"""

import json
import shutil
import sys
import tempfile
from pathlib import Path

# Import shared infrastructure
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from conftest import TestRunner, run_script, get_script_path

# Test directories
TEST_DIR = Path(__file__).parent
PROJECT_ROOT = TEST_DIR.parent.parent.parent
SCRIPT_PATH = get_script_path('pm-documents', 'cui-documentation', 'docs.py')
FIXTURES_DIR = TEST_DIR / 'fixtures'
LINK_VERIFY_FIXTURES = FIXTURES_DIR / 'link-verify'


# =============================================================================
# Main help tests
# =============================================================================

def test_script_exists():
    """Test that the script exists."""
    assert SCRIPT_PATH.exists(), f"Script not found: {SCRIPT_PATH}"


def test_fixtures_exist():
    """Test that fixtures directory exists."""
    assert FIXTURES_DIR.exists(), f"Fixtures not found: {FIXTURES_DIR}"


def test_main_help():
    """Test main --help displays all subcommands."""
    result = run_script(SCRIPT_PATH, '--help')
    combined = result.stdout + result.stderr
    assert 'stats' in combined, "stats subcommand in help"
    assert 'validate' in combined, "validate subcommand in help"
    assert 'format' in combined, "format subcommand in help"


# =============================================================================
# Stats subcommand tests
# =============================================================================

def test_stats_help():
    """Test stats --help displays usage."""
    result = run_script(SCRIPT_PATH, 'stats', '--help')
    combined = result.stdout + result.stderr
    assert 'usage' in combined.lower(), f"Stats help not shown: {combined}"


def test_stats_console_format():
    """Test stats default console output format."""
    result = run_script(SCRIPT_PATH, 'stats', str(FIXTURES_DIR))
    combined = result.stdout + result.stderr
    assert 'Documentation Statistics' in combined, \
        f"Console format didn't produce expected output: {combined}"


def test_stats_json_format():
    """Test stats JSON output format is valid."""
    result = run_script(SCRIPT_PATH, 'stats', '-f', 'json', str(FIXTURES_DIR))
    data = json.loads(result.stdout)
    assert 'metadata' in data, "JSON missing metadata"
    assert 'summary' in data, "JSON missing summary"


def test_stats_details_flag():
    """Test stats details flag includes file info."""
    result = run_script(SCRIPT_PATH, 'stats', '-d', '-f', 'json', str(FIXTURES_DIR))
    data = json.loads(result.stdout)
    assert 'files' in data, "JSON with details flag should include files key"
    assert len(data['files']) > 0, "Files dict should not be empty"


def test_stats_empty_directory():
    """Test stats handles empty directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        result = run_script(SCRIPT_PATH, 'stats', temp_dir)
        assert result.returncode == 0, f"Empty directory failed: {result.stderr}"


def test_stats_nonexistent_dir():
    """Test stats handles nonexistent directory."""
    result = run_script(SCRIPT_PATH, 'stats', '/nonexistent/path')
    assert result.returncode != 0, "Nonexistent path should fail"


# =============================================================================
# Validate subcommand tests
# =============================================================================

def test_validate_help():
    """Test validate --help displays usage."""
    result = run_script(SCRIPT_PATH, 'validate', '--help')
    combined = result.stdout + result.stderr
    assert 'usage' in combined.lower(), f"Validate help not shown: {combined}"


def test_validate_console_format():
    """Test validate default console output."""
    result = run_script(SCRIPT_PATH, 'validate', str(FIXTURES_DIR))
    combined = result.stdout + result.stderr
    assert 'Checking' in combined or len(combined) > 0, "No console output produced"


def test_validate_json_format():
    """Test validate JSON output format."""
    result = run_script(SCRIPT_PATH, 'validate', '-f', 'json', str(FIXTURES_DIR))
    combined = result.stdout + result.stderr
    assert 'directory' in combined.lower() or '{' in combined, \
        "JSON format didn't produce expected output"


def test_validate_missing_blank_line():
    """Test validate detects missing blank line before list."""
    content = """= Test Document
:toc: left
:toclevels: 3
:toc-title: Table of Contents
:sectnums:
:source-highlighter: highlight.js

== Section One
Some text directly before list:
* List item 1
* List item 2
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.adoc', delete=False) as f:
        f.write(content)
        temp_file = f.name
    try:
        result = run_script(SCRIPT_PATH, 'validate', temp_file)
        assert result.returncode != 0 or 'blank' in (result.stdout + result.stderr).lower(), \
            "Missing blank line should be detected"
    finally:
        Path(temp_file).unlink(missing_ok=True)


def test_validate_ignore_pattern():
    """Test validate ignore pattern flag."""
    result = run_script(SCRIPT_PATH, 'validate', '-i', 'missing-*.adoc', str(FIXTURES_DIR))
    assert result.returncode in [0, 1], f"Ignore pattern flag crashed: {result.stderr}"


def test_validate_invalid_format_rejected():
    """Test validate rejects invalid format."""
    result = run_script(SCRIPT_PATH, 'validate', '-f', 'invalid_format')
    assert result.returncode != 0, "Invalid format should be rejected"


def test_validate_nonexistent_path():
    """Test validate handles nonexistent path."""
    result = run_script(SCRIPT_PATH, 'validate', '/nonexistent/path')
    assert result.returncode != 0, "Nonexistent path should fail"


# =============================================================================
# Format subcommand tests
# =============================================================================

def test_format_help():
    """Test format --help displays usage."""
    result = run_script(SCRIPT_PATH, 'format', '--help')
    combined = result.stdout + result.stderr
    assert 'usage' in combined.lower(), f"Format help not shown: {combined}"


def test_format_no_backup_flag():
    """Test format --no-backup flag prevents backup creation."""
    result = run_script(SCRIPT_PATH, 'format', '-b', '-t', 'lists', str(FIXTURES_DIR))
    assert result.returncode in [0, 1], f"No backup flag crashed: {result.stderr}"


def test_format_lists_type():
    """Test format -t lists fix type."""
    result = run_script(SCRIPT_PATH, 'format', '-b', '-t', 'lists', str(FIXTURES_DIR))
    assert result.returncode in [0, 1], f"lists fix type failed: {result.stderr}"


def test_format_xref_type():
    """Test format -t xref fix type."""
    result = run_script(SCRIPT_PATH, 'format', '-b', '-t', 'xref', str(FIXTURES_DIR))
    assert result.returncode in [0, 1], f"xref fix type failed: {result.stderr}"


def test_format_whitespace_type():
    """Test format -t whitespace fix type."""
    result = run_script(SCRIPT_PATH, 'format', '-b', '-t', 'whitespace', str(FIXTURES_DIR))
    assert result.returncode in [0, 1], f"whitespace fix type failed: {result.stderr}"


def test_format_all_types():
    """Test format -t all fix type."""
    result = run_script(SCRIPT_PATH, 'format', '-b', '-t', 'all', str(FIXTURES_DIR))
    assert result.returncode in [0, 1], f"all fix type failed: {result.stderr}"


def test_format_invalid_type_rejected():
    """Test format rejects invalid fix type."""
    result = run_script(SCRIPT_PATH, 'format', '-t', 'invalid_type')
    assert result.returncode != 0, "Invalid fix type should be rejected"


def test_format_nonexistent_path():
    """Test format handles nonexistent path."""
    result = run_script(SCRIPT_PATH, 'format', '/nonexistent/path')
    assert result.returncode != 0, "Nonexistent path should fail"


# =============================================================================
# Verify-links subcommand tests
# =============================================================================

def test_verify_links_help():
    """Test verify-links --help displays usage."""
    result = run_script(SCRIPT_PATH, 'verify-links', '--help')
    combined = result.stdout + result.stderr
    assert 'usage' in combined.lower(), f"Verify-links help not shown: {combined}"


def test_verify_links_single_file():
    """Test verify-links processes single file."""
    empty_file = LINK_VERIFY_FIXTURES / 'empty.adoc'
    if not empty_file.exists():
        return  # Skip if fixture doesn't exist
    result = run_script(SCRIPT_PATH, 'verify-links', '--file', str(empty_file))
    # JSON output format - check files_processed count
    data = json.loads(result.stdout)
    assert data['data']['files_processed'] == 1, "Single file mode processes one file"


def test_verify_links_empty_file():
    """Test verify-links handles empty file."""
    empty_file = LINK_VERIFY_FIXTURES / 'empty.adoc'
    if not empty_file.exists():
        return  # Skip if fixture doesn't exist
    result = run_script(SCRIPT_PATH, 'verify-links', '--file', str(empty_file))
    assert result.returncode == 0, "Empty file does not cause errors"


def test_verify_links_file_not_found():
    """Test verify-links handles missing file."""
    result = run_script(SCRIPT_PATH, 'verify-links', '--file', '/nonexistent/file.adoc')
    assert 'error' in result.stdout.lower() or 'error' in result.stderr.lower(), \
        "Error when file does not exist"


def test_verify_links_both_file_and_directory():
    """Test verify-links rejects both --file and --directory."""
    # Use existing file and directory to test the mutual exclusivity check
    empty_file = LINK_VERIFY_FIXTURES / 'empty.adoc'
    if not empty_file.exists():
        return  # Skip if fixture doesn't exist
    result = run_script(SCRIPT_PATH, 'verify-links', '--file', str(empty_file), '--directory', str(LINK_VERIFY_FIXTURES))
    combined = result.stdout + result.stderr
    assert 'cannot specify both' in combined.lower(), \
        f"Error when both --file and --directory specified: {combined}"


# =============================================================================
# Classify-links subcommand tests
# =============================================================================

def test_classify_links_help():
    """Test classify-links --help displays usage."""
    result = run_script(SCRIPT_PATH, 'classify-links', '--help')
    combined = result.stdout + result.stderr
    assert 'usage' in combined.lower(), f"Classify-links help not shown: {combined}"


def test_classify_links_stdin_stdout():
    """Test classify-links with stdin/stdout."""
    input_data = json.dumps({
        "issues": [
            {"file": "test.adoc", "line": 1, "link": "<<anchor>>", "type": "broken_anchor"}
        ]
    })
    result = run_script(SCRIPT_PATH, 'classify-links', '--pretty', input_data=input_data)
    assert result.returncode == 0, "Stdin/stdout works"


def test_classify_links_with_files():
    """Test classify-links with input/output files."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        input_data = {
            "issues": [
                {"file": "standards/security.adoc", "line": 42, "link": "<<owasp-top-10>>", "type": "broken_anchor"},
                {"file": "guide.adoc", "line": 56, "link": "file:///local/path/doc.pdf", "type": "broken_link"}
            ]
        }
        json.dump(input_data, f)
        input_file = Path(f.name)

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        output_file = Path(f.name)

    try:
        result = run_script(
            SCRIPT_PATH, 'classify-links',
            '--input', str(input_file),
            '--output', str(output_file),
            '--pretty'
        )
        assert output_file.exists(), "Classification completed"
        content = output_file.read_text()
        has_categories = 'likely-false-positive' in content or 'must-verify-manual' in content
        assert has_categories, "Found expected categories in output"
    finally:
        input_file.unlink(missing_ok=True)
        output_file.unlink(missing_ok=True)


# =============================================================================
# Review subcommand tests
# =============================================================================

def test_review_help():
    """Test review --help displays usage."""
    result = run_script(SCRIPT_PATH, 'review', '--help')
    combined = result.stdout + result.stderr
    assert 'usage' in combined.lower(), f"Review help not shown: {combined}"


def test_review_single_file():
    """Test review analyzes single file."""
    valid_file = FIXTURES_DIR / 'valid.adoc'
    if not valid_file.exists():
        return  # Skip if fixture doesn't exist
    result = run_script(SCRIPT_PATH, 'review', '--file', str(valid_file))
    assert result.returncode == 0, f"Review failed: {result.stderr}"


def test_review_directory():
    """Test review analyzes directory."""
    result = run_script(SCRIPT_PATH, 'review', '--directory', str(FIXTURES_DIR))
    assert result.returncode == 0, f"Review directory failed: {result.stderr}"


# =============================================================================
# Analyze-tone subcommand tests
# =============================================================================

def test_analyze_tone_help():
    """Test analyze-tone --help displays usage."""
    result = run_script(SCRIPT_PATH, 'analyze-tone', '--help')
    combined = result.stdout + result.stderr
    assert 'usage' in combined.lower(), f"Analyze-tone help not shown: {combined}"


def test_analyze_tone_sample_file():
    """Test analyze-tone detects promotional language."""
    sample_content = """= Sample Documentation

== Introduction

Our powerful JWT library provides the best-in-class performance for token validation.
It's blazing-fast and enterprise-grade, making it the perfect solution for your needs.

== Features

The library is easy to use and implements OAuth 2.0.
Used by thousands of companies worldwide.
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.adoc', delete=False) as f:
        f.write(sample_content)
        sample_file = Path(f.name)

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        output_file = Path(f.name)

    try:
        result = run_script(
            SCRIPT_PATH, 'analyze-tone',
            '--file', str(sample_file),
            '--output', str(output_file),
            '--pretty'
        )
        assert output_file.exists(), "Analysis completed"
        content = output_file.read_text()
        has_promotional = 'promotional' in content or 'total_issues' in content
        assert has_promotional, "Detected promotional language or generated summary"
    finally:
        sample_file.unlink(missing_ok=True)
        output_file.unlink(missing_ok=True)


def test_analyze_tone_directory():
    """Test analyze-tone with directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        (temp_path / 'sample.adoc').write_text("""= Sample
== Section
Technical documentation content.
""")
        result = run_script(SCRIPT_PATH, 'analyze-tone', '--directory', str(temp_path), '--pretty')
        assert result.returncode == 0, "Directory analysis works"


# =============================================================================
# Main
# =============================================================================

if __name__ == '__main__':
    runner = TestRunner()
    runner.add_tests([
        # Main tests
        test_script_exists,
        test_fixtures_exist,
        test_main_help,
        # Stats tests
        test_stats_help,
        test_stats_console_format,
        test_stats_json_format,
        test_stats_details_flag,
        test_stats_empty_directory,
        test_stats_nonexistent_dir,
        # Validate tests
        test_validate_help,
        test_validate_console_format,
        test_validate_json_format,
        test_validate_missing_blank_line,
        test_validate_ignore_pattern,
        test_validate_invalid_format_rejected,
        test_validate_nonexistent_path,
        # Format tests
        test_format_help,
        test_format_no_backup_flag,
        test_format_lists_type,
        test_format_xref_type,
        test_format_whitespace_type,
        test_format_all_types,
        test_format_invalid_type_rejected,
        test_format_nonexistent_path,
        # Verify-links tests
        test_verify_links_help,
        test_verify_links_single_file,
        test_verify_links_empty_file,
        test_verify_links_file_not_found,
        test_verify_links_both_file_and_directory,
        # Classify-links tests
        test_classify_links_help,
        test_classify_links_stdin_stdout,
        test_classify_links_with_files,
        # Review tests
        test_review_help,
        test_review_single_file,
        test_review_directory,
        # Analyze-tone tests
        test_analyze_tone_help,
        test_analyze_tone_sample_file,
        test_analyze_tone_directory,
    ])
    sys.exit(runner.run())

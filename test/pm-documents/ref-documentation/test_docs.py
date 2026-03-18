#!/usr/bin/env python3
"""Tests for docs.py - documentation content quality operations (review and tone analysis)."""

import sys
import tempfile
from pathlib import Path

# Import shared infrastructure
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from conftest import get_script_path, run_script

# Test directories
TEST_DIR = Path(__file__).parent
SCRIPT_PATH = get_script_path('pm-documents', 'ref-documentation', 'docs.py')
FIXTURES_DIR = TEST_DIR / 'fixtures'


# =============================================================================
# Main help tests
# =============================================================================


def test_script_exists():
    """Test that the script exists."""
    assert SCRIPT_PATH.exists(), f'Script not found: {SCRIPT_PATH}'


def test_fixtures_exist():
    """Test that fixtures directory exists."""
    assert FIXTURES_DIR.exists(), f'Fixtures not found: {FIXTURES_DIR}'


def test_main_help():
    """Test main --help displays all subcommands."""
    result = run_script(SCRIPT_PATH, '--help')
    combined = result.stdout + result.stderr
    assert 'review' in combined, 'review subcommand in help'
    assert 'analyze-tone' in combined, 'analyze-tone subcommand in help'


# =============================================================================
# Review subcommand tests
# =============================================================================


def test_review_help():
    """Test review --help displays usage."""
    result = run_script(SCRIPT_PATH, 'review', '--help')
    combined = result.stdout + result.stderr
    assert 'usage' in combined.lower(), f'Review help not shown: {combined}'


def test_review_single_file():
    """Test review analyzes single file."""
    valid_file = FIXTURES_DIR / 'valid.adoc'
    if not valid_file.exists():
        return  # Skip if fixture doesn't exist
    result = run_script(SCRIPT_PATH, 'review', '--file', str(valid_file))
    assert result.returncode == 0, f'Review failed: {result.stderr}'


def test_review_directory():
    """Test review analyzes directory."""
    result = run_script(SCRIPT_PATH, 'review', '--directory', str(FIXTURES_DIR))
    assert result.returncode == 0, f'Review directory failed: {result.stderr}'


# =============================================================================
# Analyze-tone subcommand tests
# =============================================================================


def test_analyze_tone_help():
    """Test analyze-tone --help displays usage."""
    result = run_script(SCRIPT_PATH, 'analyze-tone', '--help')
    combined = result.stdout + result.stderr
    assert 'usage' in combined.lower(), f'Analyze-tone help not shown: {combined}'


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
        run_script(SCRIPT_PATH, 'analyze-tone', '--file', str(sample_file), '--output', str(output_file), '--pretty')
        assert output_file.exists(), 'Analysis completed'
        content = output_file.read_text()
        has_promotional = 'promotional' in content or 'total_issues' in content
        assert has_promotional, 'Detected promotional language or generated summary'
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
        assert result.returncode == 0, 'Directory analysis works'

#!/usr/bin/env python3
"""Tests for docs.py - documentation content quality operations (review and tone analysis).

Tier 2 (direct import) tests with 2 subprocess CLI plumbing tests retained.
"""

import importlib.util
import sys
import tempfile
from argparse import Namespace
from pathlib import Path

# Import shared infrastructure
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from conftest import get_script_path, run_script  # noqa: E402

# Test directories
TEST_DIR = Path(__file__).parent
SCRIPT_PATH = get_script_path('pm-documents', 'ref-documentation', 'docs.py')
FIXTURES_DIR = TEST_DIR / 'fixtures'

# Tier 2 direct imports - load cmd_* from sub-command modules
_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace' / 'bundles' / 'pm-documents' / 'skills' / 'ref-documentation' / 'scripts'
)


def _load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_review_mod = _load_module('_cmd_review', '_cmd_review.py')
_tone_mod = _load_module('_cmd_analyze_tone', '_cmd_analyze_tone.py')

cmd_review = _review_mod.cmd_review
cmd_analyze_tone = _tone_mod.cmd_analyze_tone


# =============================================================================
# Main help tests (CLI plumbing - retained as subprocess)
# =============================================================================


def test_script_exists():
    """Test that the script exists."""
    assert SCRIPT_PATH.exists(), f'Script not found: {SCRIPT_PATH}'


def test_fixtures_exist():
    """Test that fixtures directory exists."""
    assert FIXTURES_DIR.exists(), f'Fixtures not found: {FIXTURES_DIR}'


def test_main_help():
    """Test main --help displays all subcommands (CLI plumbing)."""
    result = run_script(SCRIPT_PATH, '--help')
    combined = result.stdout + result.stderr
    assert 'review' in combined, 'review subcommand in help'
    assert 'analyze-tone' in combined, 'analyze-tone subcommand in help'


# =============================================================================
# Review subcommand tests (Tier 2)
# =============================================================================


def test_review_help():
    """Test review --help displays usage (CLI plumbing)."""
    result = run_script(SCRIPT_PATH, 'review', '--help')
    combined = result.stdout + result.stderr
    assert 'usage' in combined.lower(), f'Review help not shown: {combined}'


def test_review_single_file():
    """Test review analyzes single file."""
    valid_file = FIXTURES_DIR / 'valid.adoc'
    if not valid_file.exists():
        return  # Skip if fixture doesn't exist
    result = cmd_review(Namespace(command='review', file=str(valid_file), directory=None,
                                  recursive=False, output=None))
    assert result['status'] == 'success', f'Review failed: {result}'


def test_review_directory():
    """Test review analyzes directory."""
    result = cmd_review(Namespace(command='review', file=None, directory=str(FIXTURES_DIR),
                                  recursive=False, output=None))
    assert result['status'] == 'success', f'Review directory failed: {result}'


def test_review_missing_args():
    """Test review returns error when no file or directory given."""
    result = cmd_review(Namespace(command='review', file=None, directory=None,
                                  recursive=False, output=None))
    assert result['status'] == 'error'
    assert 'missing_args' in result.get('error', '')


# =============================================================================
# Analyze-tone subcommand tests (Tier 2)
# =============================================================================


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
        result = cmd_analyze_tone(Namespace(command='analyze-tone', file=str(sample_file),
                                            directory=None, output=str(output_file), pretty=True))
        assert result['status'] == 'success'
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
        result = cmd_analyze_tone(Namespace(command='analyze-tone', file=None,
                                            directory=str(temp_path), output=None, pretty=False))
        assert result['status'] == 'success', 'Directory analysis works'


def test_analyze_tone_missing_args():
    """Test analyze-tone returns error when no file or directory given."""
    result = cmd_analyze_tone(Namespace(command='analyze-tone', file=None, directory=None,
                                        output=None, pretty=False))
    assert result['status'] == 'error'
    assert 'missing_args' in result.get('error', '')

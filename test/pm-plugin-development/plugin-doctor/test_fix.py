#!/usr/bin/env python3
"""Tests for fix.py - consolidated plugin fix tools.

Tests plugin component fix capabilities including:
- extract: Extract fixable issues from diagnosis
- categorize: Categorize fixes as safe/risky
- apply: Apply a single fix
- verify: Verify a fix was applied
"""

import json
import tempfile
from pathlib import Path

# Import shared infrastructure
from conftest import get_script_path, run_script

# Script under test
SCRIPT_PATH = get_script_path('pm-plugin-development', 'plugin-doctor', '_fix.py')
FIXTURES_DIR = Path(__file__).parent / 'fixtures' / 'fix'


# =============================================================================
# Main help tests
# =============================================================================

def test_script_exists():
    """Test that script exists."""
    assert Path(SCRIPT_PATH).exists(), f"Script not found: {SCRIPT_PATH}"


def test_main_help():
    """Test main --help displays all subcommands."""
    result = run_script(SCRIPT_PATH, '--help')
    combined = result.stdout + result.stderr
    assert 'extract' in combined, "extract subcommand in help"
    assert 'categorize' in combined, "categorize subcommand in help"
    assert 'apply' in combined, "apply subcommand in help"
    assert 'verify' in combined, "verify subcommand in help"


# =============================================================================
# Extract Subcommand Tests
# =============================================================================

def test_extract_help():
    """Test extract --help is available."""
    result = run_script(SCRIPT_PATH, 'extract', '--help')
    assert 'input' in result.stdout or 'input' in result.stderr, \
        "Help should mention input option"


def test_extract_from_stdin():
    """Test extract accepts JSON from stdin."""
    diagnosis = {
        "issues": [
            {"type": "missing-frontmatter", "severity": "high", "fixable": True},
            {"type": "bloat", "severity": "medium", "fixable": False}
        ]
    }
    result = run_script(SCRIPT_PATH, 'extract', input_data=json.dumps(diagnosis))
    data = result.json()
    assert data is not None, "Should return valid JSON"
    assert 'fixable_issues' in data or 'issues' in data, "Should have issues field"


# =============================================================================
# Categorize Subcommand Tests
# =============================================================================

def test_categorize_help():
    """Test categorize --help is available."""
    result = run_script(SCRIPT_PATH, 'categorize', '--help')
    assert 'input' in result.stdout or 'input' in result.stderr, \
        "Help should mention input option"


def test_categorize_safe_issues():
    """Test categorize identifies safe fixes."""
    issues = {
        "issues": [
            {"type": "missing-frontmatter", "file": "test.md"},
            {"type": "trailing-whitespace", "file": "test.md"}
        ]
    }
    result = run_script(SCRIPT_PATH, 'categorize', input_data=json.dumps(issues))
    data = result.json()
    assert data is not None, "Should return valid JSON"
    # Should have safe_fixes or similar field
    assert 'safe_fixes' in data or 'safe' in data or 'categorized' in data, \
        "Should categorize fixes"


# =============================================================================
# Apply Subcommand Tests
# =============================================================================

def test_apply_help():
    """Test apply --help is available."""
    result = run_script(SCRIPT_PATH, 'apply', '--help')
    combined = result.stdout + result.stderr
    assert 'fix' in combined.lower(), "Help should mention fix option"


def test_apply_missing_arguments():
    """Test apply requires fix and bundle-dir."""
    result = run_script(SCRIPT_PATH, 'apply')
    assert result.returncode != 0, "Should error without arguments"


# =============================================================================
# Verify Subcommand Tests
# =============================================================================

def test_verify_help():
    """Test verify --help is available."""
    result = run_script(SCRIPT_PATH, 'verify', '--help')
    combined = result.stdout + result.stderr
    assert 'fix-type' in combined or 'file' in combined, \
        "Help should mention fix-type or file option"


def test_verify_missing_arguments():
    """Test verify requires arguments."""
    result = run_script(SCRIPT_PATH, 'verify')
    assert result.returncode != 0, "Should error without arguments"


def test_verify_with_valid_file():
    """Test verify with a valid file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write('---\nname: test\ndescription: Test\n---\n\n# Test\n')
        f.flush()

        result = run_script(SCRIPT_PATH, 'verify', '--fix-type', 'missing-frontmatter', '--file', f.name)
        data = result.json()
        assert data is not None, "Should return valid JSON"

        Path(f.name).unlink()


# =============================================================================
# Main
# =============================================================================

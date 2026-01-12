#!/usr/bin/env python3
"""Tests for validate.py - consolidated plugin validation tools.

Tests plugin validation capabilities including:
- references: Validate plugin references
- cross-file: Verify cross-file findings
- inventory: Scan skill inventory
"""

import json
import sys
import tempfile
from pathlib import Path

# Import shared infrastructure
from conftest import run_script, TestRunner, get_script_path

# Script under test
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
SCRIPT_PATH = get_script_path('pm-plugin-development', 'plugin-doctor', '_validate.py')


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
    assert 'references' in combined, "references subcommand in help"
    assert 'cross-file' in combined, "cross-file subcommand in help"
    assert 'inventory' in combined, "inventory subcommand in help"


# =============================================================================
# References Subcommand Tests
# =============================================================================

def test_references_help():
    """Test references --help is available."""
    result = run_script(SCRIPT_PATH, 'references', '--help')
    assert 'file' in result.stdout or 'file' in result.stderr, \
        "Help should mention file option"


def test_references_missing_file():
    """Test references requires file argument."""
    result = run_script(SCRIPT_PATH, 'references')
    assert result.returncode != 0, "Should error without file"


def test_references_nonexistent_file():
    """Test references handles nonexistent file."""
    result = run_script(SCRIPT_PATH, 'references', '--file', '/nonexistent/file.md')
    assert result.returncode != 0 or 'error' in result.stdout.lower() or 'error' in result.stderr.lower(), \
        "Should error for nonexistent file"


def test_references_valid_file():
    """Test references with a valid markdown file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write('---\nname: test\ndescription: Test\n---\n\n# Test\n\nSee [link](./other.md)\n')
        f.flush()

        result = run_script(SCRIPT_PATH, 'references', '--file', f.name)
        data = result.json()
        assert data is not None, "Should return valid JSON"

        Path(f.name).unlink()


# =============================================================================
# Cross-File Subcommand Tests
# =============================================================================

def test_crossfile_help():
    """Test cross-file --help is available."""
    result = run_script(SCRIPT_PATH, 'cross-file', '--help')
    combined = result.stdout + result.stderr
    assert 'analysis' in combined or 'findings' in combined, \
        "Help should mention analysis or findings option"


def test_crossfile_missing_arguments():
    """Test cross-file requires arguments."""
    result = run_script(SCRIPT_PATH, 'cross-file')
    assert result.returncode != 0, "Should error without arguments"


# =============================================================================
# Inventory Subcommand Tests
# =============================================================================

def test_inventory_help():
    """Test inventory --help is available."""
    result = run_script(SCRIPT_PATH, 'inventory', '--help')
    assert 'skill-path' in result.stdout or 'skill-path' in result.stderr, \
        "Help should mention skill-path option"


def test_inventory_missing_path():
    """Test inventory requires skill-path."""
    result = run_script(SCRIPT_PATH, 'inventory')
    assert result.returncode != 0, "Should error without skill-path"


def test_inventory_nonexistent_path():
    """Test inventory handles nonexistent path."""
    result = run_script(SCRIPT_PATH, 'inventory', '--skill-path', '/nonexistent/skill')
    assert result.returncode != 0 or 'error' in result.stdout.lower() or 'error' in result.stderr.lower(), \
        "Should error for nonexistent path"


def test_inventory_real_skill():
    """Test inventory on a real skill directory."""
    skill_dir = PROJECT_ROOT / 'marketplace' / 'bundles' / 'pm-plugin-development' / 'skills' / 'plugin-doctor'
    if not skill_dir.exists():
        return  # Skip if not found

    result = run_script(SCRIPT_PATH, 'inventory', '--skill-path', str(skill_dir))
    data = result.json()
    assert data is not None, "Should return valid JSON"
    assert 'files' in data or 'inventory' in data or 'skill_path' in data, \
        "Should have inventory data"


# =============================================================================
# Main
# =============================================================================

if __name__ == '__main__':
    runner = TestRunner()
    runner.add_tests([
        # Main tests
        test_script_exists,
        test_main_help,
        # References subcommand tests
        test_references_help,
        test_references_missing_file,
        test_references_nonexistent_file,
        test_references_valid_file,
        # Cross-file subcommand tests
        test_crossfile_help,
        test_crossfile_missing_arguments,
        # Inventory subcommand tests
        test_inventory_help,
        test_inventory_missing_path,
        test_inventory_nonexistent_path,
        test_inventory_real_skill,
    ])
    sys.exit(runner.run())

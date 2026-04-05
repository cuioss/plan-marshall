#!/usr/bin/env python3
"""Tests for validate.py - consolidated plugin validation tools.

Tests plugin validation capabilities including:
- references: Validate plugin references
- cross-file: Verify cross-file findings
- inventory: Scan skill inventory
"""

import tempfile
from argparse import Namespace
from pathlib import Path

# Import shared infrastructure
from conftest import get_script_path, run_script

# Script under test
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
SCRIPT_PATH = get_script_path('pm-plugin-development', 'plugin-doctor', '_validate.py')

# Direct imports for Tier 2 testing
from _cmd_inventory import cmd_inventory  # noqa: E402
from _cmd_references import cmd_references  # noqa: E402

# =============================================================================
# CLI plumbing tests (Tier 3 - subprocess)
# =============================================================================


def test_script_exists():
    """Test that script exists."""
    assert Path(SCRIPT_PATH).exists(), f'Script not found: {SCRIPT_PATH}'


def test_main_help():
    """Test main --help displays all subcommands."""
    result = run_script(SCRIPT_PATH, '--help')
    combined = result.stdout + result.stderr
    assert 'references' in combined, 'references subcommand in help'
    assert 'cross-file' in combined, 'cross-file subcommand in help'
    assert 'inventory' in combined, 'inventory subcommand in help'


def test_references_missing_file():
    """Test references requires file argument."""
    result = run_script(SCRIPT_PATH, 'references')
    assert result.returncode != 0, 'Should error without file'


# =============================================================================
# References Subcommand Tests (Tier 2 - direct import)
# =============================================================================


def test_references_nonexistent_file():
    """Test references handles nonexistent file."""
    args = Namespace(file='/nonexistent/file.md')
    result = cmd_references(args)
    assert result is not None, 'Should return a result dict'


def test_references_valid_file():
    """Test references with a valid markdown file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write('---\nname: test\ndescription: Test\n---\n\n# Test\n\nSee [link](./other.md)\n')
        f.flush()

        args = Namespace(file=f.name)
        data = cmd_references(args)
        assert data is not None, 'Should return valid dict'

        Path(f.name).unlink()


# =============================================================================
# Inventory Subcommand Tests (Tier 2 - direct import)
# =============================================================================


def test_inventory_nonexistent_path():
    """Test inventory handles nonexistent path."""
    args = Namespace(skill_path='/nonexistent/skill', include_hidden=False)
    data = cmd_inventory(args)
    assert data is not None, 'Should return a result dict'
    assert 'error' in str(data).lower() or data.get('status') == 'error', 'Should error for nonexistent path'


def test_inventory_real_skill():
    """Test inventory on a real skill directory."""
    skill_dir = PROJECT_ROOT / 'marketplace' / 'bundles' / 'pm-plugin-development' / 'skills' / 'plugin-doctor'
    if not skill_dir.exists():
        return  # Skip if not found

    args = Namespace(skill_path=str(skill_dir), include_hidden=False)
    data = cmd_inventory(args)
    assert data is not None, 'Should return valid dict'
    assert 'files' in data or 'inventory' in data or 'skill_path' in data, 'Should have inventory data'


# =============================================================================
# Main
# =============================================================================

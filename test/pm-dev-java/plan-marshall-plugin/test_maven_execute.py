#!/usr/bin/env python3
"""Tests for maven.py CLI - run subcommand.

Tests the Maven build execution through the public CLI interface.
"""

import subprocess
import sys
from pathlib import Path

# Import shared infrastructure
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from conftest import (
    get_script_path,
    TestRunner,
    BuildTestContext,
)

# Get CLI entry point
MAVEN_CLI = get_script_path('pm-dev-java', 'plan-marshall-plugin', 'maven.py')


# =============================================================================
# Test: CLI interface
# =============================================================================

def test_cli_help():
    """Test maven.py --help works."""
    result = subprocess.run(
        ['python3', str(MAVEN_CLI), '--help'],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    assert 'run' in result.stdout
    assert 'parse' in result.stdout


def test_cli_run_help():
    """Test maven.py run --help works."""
    result = subprocess.run(
        ['python3', str(MAVEN_CLI), 'run', '--help'],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    assert '--commandArgs' in result.stdout
    assert '--timeout' in result.stdout


def test_cli_parse_help():
    """Test maven.py parse --help works."""
    result = subprocess.run(
        ['python3', str(MAVEN_CLI), 'parse', '--help'],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    assert '--log' in result.stdout


# =============================================================================
# Runner
# =============================================================================

if __name__ == '__main__':
    runner = TestRunner()
    runner.add_tests([
        test_cli_help,
        test_cli_run_help,
        test_cli_parse_help,
    ])
    sys.exit(runner.run())

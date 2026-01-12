#!/usr/bin/env python3
"""Tests for gradle.py CLI - run subcommand.

Tests the Gradle build execution through the public CLI interface.
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
GRADLE_CLI = get_script_path('pm-dev-java', 'plan-marshall-plugin', 'gradle.py')


# =============================================================================
# Test: CLI interface
# =============================================================================

def test_cli_help():
    """Test gradle.py --help works."""
    result = subprocess.run(
        ['python3', str(GRADLE_CLI), '--help'],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    assert 'run' in result.stdout
    assert 'parse' in result.stdout
    assert 'find-project' in result.stdout


def test_cli_run_help():
    """Test gradle.py run --help works."""
    result = subprocess.run(
        ['python3', str(GRADLE_CLI), 'run', '--help'],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    assert '--commandArgs' in result.stdout
    assert '--timeout' in result.stdout


def test_cli_parse_help():
    """Test gradle.py parse --help works."""
    result = subprocess.run(
        ['python3', str(GRADLE_CLI), 'parse', '--help'],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    assert '--log' in result.stdout


def test_cli_find_project_help():
    """Test gradle.py find-project --help works."""
    result = subprocess.run(
        ['python3', str(GRADLE_CLI), 'find-project', '--help'],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    assert '--project-name' in result.stdout


# =============================================================================
# Runner
# =============================================================================

if __name__ == '__main__':
    runner = TestRunner()
    runner.add_tests([
        test_cli_help,
        test_cli_run_help,
        test_cli_parse_help,
        test_cli_find_project_help,
    ])
    sys.exit(runner.run())

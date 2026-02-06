#!/usr/bin/env python3
"""Tests for gradle.py CLI - run subcommand.

Tests the Gradle build execution through the public CLI interface.
"""

import subprocess
import sys
from pathlib import Path

# Import shared infrastructure
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
import os

from conftest import _MARKETPLACE_SCRIPT_DIRS, get_script_path

# Get CLI entry point
GRADLE_CLI = get_script_path('pm-dev-java', 'plan-marshall-plugin', 'gradle.py')


def run_cli(*args, **kwargs):
    """Run subprocess with marketplace PYTHONPATH."""
    env = os.environ.copy()
    pythonpath = os.pathsep.join(_MARKETPLACE_SCRIPT_DIRS)
    if 'PYTHONPATH' in env:
        pythonpath = pythonpath + os.pathsep + env['PYTHONPATH']
    env['PYTHONPATH'] = pythonpath
    return subprocess.run(args, capture_output=True, text=True, env=env, **kwargs)


# =============================================================================
# Test: CLI interface
# =============================================================================


def test_cli_help():
    """Test gradle.py --help works."""
    result = run_cli('python3', str(GRADLE_CLI), '--help')
    assert result.returncode == 0
    assert 'run' in result.stdout
    assert 'parse' in result.stdout
    assert 'find-project' in result.stdout


def test_cli_run_help():
    """Test gradle.py run --help works."""
    result = run_cli('python3', str(GRADLE_CLI), 'run', '--help')
    assert result.returncode == 0
    assert '--command-args' in result.stdout
    assert '--timeout' in result.stdout


def test_cli_parse_help():
    """Test gradle.py parse --help works."""
    result = run_cli('python3', str(GRADLE_CLI), 'parse', '--help')
    assert result.returncode == 0
    assert '--log' in result.stdout


def test_cli_find_project_help():
    """Test gradle.py find-project --help works."""
    result = run_cli('python3', str(GRADLE_CLI), 'find-project', '--help')
    assert result.returncode == 0
    assert '--project-name' in result.stdout


# =============================================================================
# Runner
# =============================================================================

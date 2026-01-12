#!/usr/bin/env python3
"""Tests for npm.py script.

Tests the foundation layer for npm command execution including
command type detection, timeout handling, and command execution.
"""

import sys
from pathlib import Path

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import (
    get_script_path,
    TestRunner,
    BuildTestContext
)

# Get script path
SCRIPT_PATH = get_script_path('pm-dev-frontend', 'plan-marshall-plugin', 'npm.py')

# Import modules under test (PYTHONPATH set by conftest)
from npm import detect_command_type, get_bash_timeout, execute_direct


# =============================================================================
# Test: API functions (via import)
# =============================================================================

def test_api_detect_command_type():
    """Test detect_command_type API function."""
    # Test npm commands
    assert detect_command_type('run test') == 'npm'
    assert detect_command_type('install') == 'npm'
    assert detect_command_type('run build') == 'npm'

    # Test npx commands
    assert detect_command_type('playwright test') == 'npx'
    assert detect_command_type('eslint src/') == 'npx'
    assert detect_command_type('jest --coverage') == 'npx'
    assert detect_command_type('prettier --check .') == 'npx'


def test_api_get_bash_timeout():
    """Test get_bash_timeout API adds buffer correctly."""
    # Test various values
    assert get_bash_timeout(300) == 330  # 300 + 30 buffer
    assert get_bash_timeout(60) == 90    # 60 + 30 buffer
    assert get_bash_timeout(120) == 150  # 120 + 30 buffer


def test_api_execute_direct_success():
    """Test execute_direct API with successful command."""
    with BuildTestContext() as ctx:
        result = execute_direct(
            args='--version',
            command_key='test:version',
            default_timeout=10,
            project_dir=str(ctx.temp_dir)
        )

        # npm --version should succeed (npm is available in most environments)
        assert result['status'] == 'success'
        assert result['exit_code'] == 0
        assert result['command_type'] == 'npm'


def test_api_execute_direct_returns_log_file():
    """Test execute_direct API returns log_file (R1 compliance)."""
    with BuildTestContext() as ctx:
        result = execute_direct(
            args='--version',
            command_key='test:log_file',
            default_timeout=10,
            project_dir=str(ctx.temp_dir)
        )

        # R1: All build output must go to a log file
        assert 'log_file' in result
        assert result['log_file'], "log_file should not be empty"
        assert '.plan/temp/build-output' in result['log_file']
        assert 'npm-' in result['log_file']  # Build system in filename


def test_api_execute_direct_npx_command():
    """Test execute_direct API with npx command."""
    with BuildTestContext() as ctx:
        result = execute_direct(
            args='--version',
            command_key='test:npx_version',
            default_timeout=10,
            project_dir=str(ctx.temp_dir)
        )

        # --version is detected as npm not npx (starts with -)
        assert result['status'] == 'success'
        assert result['command_type'] == 'npm'


# =============================================================================
# Runner
# =============================================================================

if __name__ == '__main__':
    runner = TestRunner()
    runner.add_tests([
        # API functions
        test_api_detect_command_type,
        test_api_get_bash_timeout,
        test_api_execute_direct_success,
        test_api_execute_direct_returns_log_file,
        test_api_execute_direct_npx_command,
    ])
    sys.exit(runner.run())

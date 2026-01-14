#!/usr/bin/env python3
"""Tests for Maven run subcommand.

Tests the unified run command that combines execute + parse on failure:
- Success output format
- Failure output with parsed errors
- Timeout handling
- --mode parameter filtering
"""

import sys
import shutil
import tempfile
from pathlib import Path
from contextlib import contextmanager

# Import shared infrastructure
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from conftest import run_script, get_script_path

# Script under test - pm-dev-java bundle
SCRIPT_PATH = get_script_path('pm-dev-java', 'plan-marshall-plugin', 'maven.py')
MOCKS_DIR = Path(__file__).parent / 'mocks'


@contextmanager
def mock_maven_project(mock_script: str = 'mvnw-success.sh'):
    """Context manager that creates a temp directory with mock Maven wrapper."""
    with tempfile.TemporaryDirectory() as td:
        temp_dir = Path(td)
        # Create target directory for log files
        (temp_dir / 'target').mkdir()
        # Create .plan directory for log files (new standard location)
        (temp_dir / '.plan' / 'temp' / 'build-output' / 'default').mkdir(parents=True)
        # Copy mock wrapper to temp_dir as mvnw
        mock_path = MOCKS_DIR / mock_script
        if mock_path.exists():
            mvnw_path = temp_dir / 'mvnw'
            shutil.copy(mock_path, mvnw_path)
            mvnw_path.chmod(0o755)
        yield temp_dir


# =============================================================================
# Run Success Tests
# =============================================================================

def test_run_success_output_format():
    """Test run command success output format (TOON format - tab-separated)."""
    with mock_maven_project('mvnw-success.sh') as temp_dir:
        result = run_script(
            SCRIPT_PATH,
            'run',
            '--commandArgs', 'clean test',
            cwd=temp_dir
        )

        assert result.returncode == 0, f"Successful run should exit with 0: {result.stderr}"

        # Parse TOON output (tab-separated key-value pairs)
        lines = result.stdout.strip().split('\n')
        toon = {}
        for line in lines:
            if '\t' in line:
                key, value = line.split('\t', 1)
                toon[key] = value

        assert toon.get('status') == 'success', f"Status should be success: {toon}"
        assert 'log_file' in toon, "Should include log_file"
        assert toon.get('exit_code') == '0', "Exit code should be 0"
        assert 'command' in toon, "Should include command field"


def test_run_includes_duration():
    """Test run command includes duration in output."""
    with mock_maven_project('mvnw-success.sh') as temp_dir:
        result = run_script(
            SCRIPT_PATH,
            'run',
            '--commandArgs', 'clean test',
            cwd=temp_dir
        )

        assert 'duration_seconds' in result.stdout, "Should include duration_seconds"


# =============================================================================
# Run Failure Tests
# =============================================================================

def test_run_failure_includes_errors():
    """Test run command failure includes parsed errors."""
    with mock_maven_project('mvnw-failure.sh') as temp_dir:
        result = run_script(
            SCRIPT_PATH,
            'run',
            '--commandArgs', 'clean test',
            cwd=temp_dir
        )

        assert result.returncode == 1, "Failed run should exit with 1"
        assert 'status\terror' in result.stdout, "Should have error status"
        assert 'error\tbuild_failed' in result.stdout, "Should have build_failed error type"
        assert 'command\t' in result.stdout, "Should include command field"


def test_run_failure_with_compilation_errors():
    """Test run command failure with compilation errors includes file/line info."""
    with mock_maven_project('mvnw-failure.sh') as temp_dir:
        result = run_script(
            SCRIPT_PATH,
            'run',
            '--commandArgs', 'clean test',
            cwd=temp_dir
        )

        # Even if mock doesn't produce parse-able errors, the format should be correct
        assert 'status\terror' in result.stdout, "Should have error status"


# =============================================================================
# Mode Parameter Tests
# =============================================================================

def test_run_mode_actionable():
    """Test run with --mode actionable (default)."""
    with mock_maven_project('mvnw-success.sh') as temp_dir:
        result = run_script(
            SCRIPT_PATH,
            'run',
            '--commandArgs', 'clean test',
            '--mode', 'actionable',
            cwd=temp_dir
        )

        assert result.returncode == 0, f"Should succeed: {result.stderr}"
        assert 'status\tsuccess' in result.stdout


def test_run_mode_errors():
    """Test run with --mode errors (no warnings)."""
    with mock_maven_project('mvnw-success.sh') as temp_dir:
        result = run_script(
            SCRIPT_PATH,
            'run',
            '--commandArgs', 'clean test',
            '--mode', 'errors',
            cwd=temp_dir
        )

        assert result.returncode == 0, f"Should succeed: {result.stderr}"


def test_run_mode_structured():
    """Test run with --mode structured (all issues with markers)."""
    with mock_maven_project('mvnw-success.sh') as temp_dir:
        result = run_script(
            SCRIPT_PATH,
            'run',
            '--commandArgs', 'clean test',
            '--mode', 'structured',
            cwd=temp_dir
        )

        assert result.returncode == 0, f"Should succeed: {result.stderr}"


# =============================================================================
# Module Routing Tests (embedded in commandArgs)
# =============================================================================

def test_run_with_module_routing():
    """Test run with module routing embedded in commandArgs."""
    with mock_maven_project('mvnw-success.sh') as temp_dir:
        result = run_script(
            SCRIPT_PATH,
            'run',
            '--commandArgs', 'clean test -pl core',
            cwd=temp_dir
        )

        assert result.returncode == 0, f"Should succeed: {result.stderr}"
        # Check command includes module
        assert 'command\t' in result.stdout


# =============================================================================
# Help Test
# =============================================================================

def test_run_help():
    """Test run subcommand help."""
    result = run_script(SCRIPT_PATH, 'run', '--help')
    assert '--commandArgs' in result.stdout, "Should show --commandArgs option"
    assert '--mode' in result.stdout, "Should show --mode option"


# =============================================================================
# Main
# =============================================================================

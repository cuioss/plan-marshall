#!/usr/bin/env python3
"""Tests for Gradle run subcommand.

Tests the unified run command that combines execute + parse on failure:
- Success output format (TOON tab-separated and JSON)
- Failure output with parsed errors
- --mode parameter filtering
- --format parameter for output format
- Log file location (.plan/temp/build-output/)
"""

import json
import sys
import shutil
import tempfile
from pathlib import Path
from contextlib import contextmanager

# Import shared infrastructure
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from conftest import run_script, TestRunner, get_script_path

# Script under test - pm-dev-java bundle
SCRIPT_PATH = get_script_path('pm-dev-java', 'plan-marshall-plugin', 'gradle.py')
MOCKS_DIR = Path(__file__).parent / 'mocks'


@contextmanager
def mock_gradle_project(mock_script: str = 'gradlew-success.sh'):
    """Context manager that creates a temp directory with mock Gradle wrapper."""
    with tempfile.TemporaryDirectory() as td:
        temp_dir = Path(td)
        # Create .plan directory for log files (new standard location)
        (temp_dir / '.plan' / 'temp' / 'build-output' / 'default').mkdir(parents=True)
        # Copy mock wrapper to temp_dir as gradlew
        mock_path = MOCKS_DIR / mock_script
        if mock_path.exists():
            gradlew_path = temp_dir / 'gradlew'
            shutil.copy(mock_path, gradlew_path)
            gradlew_path.chmod(0o755)
        yield temp_dir


# =============================================================================
# Run Success Tests
# =============================================================================

def test_run_success_output_format():
    """Test run command success output format (TOON format with tab separator)."""
    with mock_gradle_project('gradlew-success.sh') as temp_dir:
        result = run_script(
            SCRIPT_PATH,
            'run',
            '--commandArgs', 'clean test',
            cwd=temp_dir
        )

        assert result.returncode == 0, f"Successful run should exit with 0: {result.stderr}"

        # Parse tab-separated TOON output
        lines = result.stdout.strip().split('\n')
        toon = {}
        for line in lines:
            if '\t' in line:
                key, value = line.split('\t', 1)
                toon[key] = value

        assert toon.get('status') == 'success', f"Status should be success: {toon}"
        assert 'log_file' in toon, "Should include log_file"
        assert toon.get('exit_code') == '0', "Exit code should be 0"
        assert 'command' in toon, "Should include command (not command_executed)"


def test_run_includes_duration():
    """Test run command includes duration in output."""
    with mock_gradle_project('gradlew-success.sh') as temp_dir:
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
    """Test run command failure includes error status."""
    with mock_gradle_project('gradlew-failure.sh') as temp_dir:
        result = run_script(
            SCRIPT_PATH,
            'run',
            '--commandArgs', 'clean test',
            cwd=temp_dir
        )

        assert result.returncode == 1, "Failed run should exit with 1"
        assert 'status\terror' in result.stdout, "Should have error status (tab-separated)"


# =============================================================================
# Mode Parameter Tests
# =============================================================================

def test_run_mode_actionable():
    """Test run with --mode actionable (default)."""
    with mock_gradle_project('gradlew-success.sh') as temp_dir:
        result = run_script(
            SCRIPT_PATH,
            'run',
            '--commandArgs', 'clean test',
            '--mode', 'actionable',
            cwd=temp_dir
        )

        assert result.returncode == 0, f"Should succeed: {result.stderr}"
        assert 'status\tsuccess' in result.stdout, "Should have success status (tab-separated)"


def test_run_mode_errors():
    """Test run with --mode errors (no warnings)."""
    with mock_gradle_project('gradlew-success.sh') as temp_dir:
        result = run_script(
            SCRIPT_PATH,
            'run',
            '--commandArgs', 'clean test',
            '--mode', 'errors',
            cwd=temp_dir
        )

        assert result.returncode == 0, f"Should succeed: {result.stderr}"


# =============================================================================
# Module Routing Tests (embedded in commandArgs)
# =============================================================================

def test_run_with_module_routing():
    """Test run with module routing embedded in commandArgs."""
    with mock_gradle_project('gradlew-success.sh') as temp_dir:
        # Create scope directory for the module
        (temp_dir / '.plan' / 'temp' / 'build-output' / 'core').mkdir(parents=True)
        result = run_script(
            SCRIPT_PATH,
            'run',
            '--commandArgs', ':core:clean :core:test',
            cwd=temp_dir
        )

        assert result.returncode == 0, f"Should succeed: {result.stderr}"
        # Log file should be in the core scope
        assert '.plan/temp/build-output/core/gradle-' in result.stdout, "Log file should be in core scope"


# =============================================================================
# Format Parameter Tests
# =============================================================================

def test_run_format_json():
    """Test run with --format json produces valid JSON output."""
    with mock_gradle_project('gradlew-success.sh') as temp_dir:
        result = run_script(
            SCRIPT_PATH,
            'run',
            '--commandArgs', 'clean test',
            '--format', 'json',
            cwd=temp_dir
        )

        assert result.returncode == 0, f"Should succeed: {result.stderr}"
        # Should be valid JSON
        data = json.loads(result.stdout)
        assert data['status'] == 'success', "Status should be success"
        assert data['exit_code'] == 0, "Exit code should be 0"
        assert 'command' in data, "Should include command"
        assert 'log_file' in data, "Should include log_file"
        assert 'duration_seconds' in data, "Should include duration_seconds"


def test_run_format_toon_default():
    """Test run defaults to TOON format."""
    with mock_gradle_project('gradlew-success.sh') as temp_dir:
        result = run_script(
            SCRIPT_PATH,
            'run',
            '--commandArgs', 'clean test',
            cwd=temp_dir
        )

        assert result.returncode == 0, f"Should succeed: {result.stderr}"
        # Should be tab-separated, not JSON
        assert '\t' in result.stdout, "Should use tab separator"
        assert '{' not in result.stdout.split('\n')[0], "First line should not be JSON"


# =============================================================================
# Log File Location Tests
# =============================================================================

def test_run_log_file_location():
    """Test log file is created in .plan/temp/build-output/."""
    with mock_gradle_project('gradlew-success.sh') as temp_dir:
        result = run_script(
            SCRIPT_PATH,
            'run',
            '--commandArgs', 'clean test',
            cwd=temp_dir
        )

        assert result.returncode == 0, f"Should succeed: {result.stderr}"
        assert '.plan/temp/build-output/' in result.stdout, "Log should be in .plan/temp/build-output/"
        assert 'gradle-' in result.stdout, "Log file should have gradle- prefix"


# =============================================================================
# Help Test
# =============================================================================

def test_run_help():
    """Test run subcommand help."""
    result = run_script(SCRIPT_PATH, 'run', '--help')
    assert '--commandArgs' in result.stdout, "Should show --commandArgs option"
    assert '--mode' in result.stdout, "Should show --mode option"
    assert '--format' in result.stdout, "Should show --format option"


# =============================================================================
# Main
# =============================================================================

if __name__ == '__main__':
    runner = TestRunner()
    runner.add_tests([
        test_run_success_output_format,
        test_run_includes_duration,
        test_run_failure_includes_errors,
        test_run_mode_actionable,
        test_run_mode_errors,
        test_run_with_module_routing,
        test_run_format_json,
        test_run_format_toon_default,
        test_run_log_file_location,
        test_run_help,
    ])
    sys.exit(runner.run())

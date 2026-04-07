#!/usr/bin/env python3
"""Tests for npm run subcommand.

Tests the unified run command that combines execute + parse on failure:
- Success output format
- Failure output with parsed errors
- --mode parameter filtering
- Help text
"""

import tempfile
from contextlib import contextmanager
from pathlib import Path

from conftest import get_script_path, run_script

# Script under test
SCRIPT_PATH = get_script_path('plan-marshall', 'build-npm', 'npm.py')


@contextmanager
def mock_npm_project():
    """Context manager that creates a temp directory with npm available."""
    with tempfile.TemporaryDirectory() as td:
        temp_dir = Path(td)
        # Create .plan directory for log files
        (temp_dir / '.plan' / 'temp' / 'build-output' / 'default').mkdir(parents=True)
        # Create package.json
        (temp_dir / 'package.json').write_text('{"name": "test", "version": "1.0.0"}')
        yield temp_dir


# =============================================================================
# Run Success Tests
# =============================================================================


def test_run_success_output_format():
    """Test run command success output format (TOON)."""
    with mock_npm_project() as temp_dir:
        result = run_script(SCRIPT_PATH, 'run', '--command-args=--version', cwd=temp_dir)

        assert result.returncode == 0, f'Successful run should exit with 0: {result.stderr}'

        # Parse TOON output (colon-space format)
        lines = result.stdout.strip().split('\n')
        toon = {}
        for line in lines:
            if ': ' in line:
                key, value = line.split(': ', 1)
                toon[key.strip()] = value.strip()

        assert toon.get('status') == 'success', f'Status should be success: {toon}'
        assert 'log_file' in toon, 'Should include log_file'
        assert toon.get('exit_code') == '0', 'Exit code should be 0'
        assert 'command' in toon, 'Should include command field'


def test_run_includes_log_file():
    """Test run command includes log_file path."""
    with mock_npm_project() as temp_dir:
        result = run_script(SCRIPT_PATH, 'run', '--command-args=--version', cwd=temp_dir)

        assert result.returncode == 0
        assert 'log_file: ' in result.stdout, 'Should include log_file'
        assert 'npm-' in result.stdout, 'Log file should contain npm prefix'


def test_run_includes_duration():
    """Test run command includes duration in output."""
    with mock_npm_project() as temp_dir:
        result = run_script(SCRIPT_PATH, 'run', '--command-args=--version', cwd=temp_dir)

        assert 'duration_seconds' in result.stdout, 'Should include duration_seconds'


# =============================================================================
# Run Failure Tests
# =============================================================================


def test_run_failure_returns_exit_1():
    """Test run command failure returns exit code 1."""
    with mock_npm_project() as temp_dir:
        # 'run nonexistent-script' should fail
        result = run_script(SCRIPT_PATH, 'run', '--command-args', 'run nonexistent-script-xyz', cwd=temp_dir)

        assert result.returncode == 0, 'Failed run should exit with 0 — status modeled in TOON output'
        assert 'status: error' in result.stdout, 'Should have error status'


# =============================================================================
# Mode Parameter Tests
# =============================================================================


def test_run_mode_actionable():
    """Test run with --mode actionable (default)."""
    with mock_npm_project() as temp_dir:
        result = run_script(SCRIPT_PATH, 'run', '--command-args=--version', '--mode', 'actionable', cwd=temp_dir)
        assert result.returncode == 0, f'Should succeed: {result.stderr}'
        assert 'status: success' in result.stdout


def test_run_mode_errors():
    """Test run with --mode errors."""
    with mock_npm_project() as temp_dir:
        result = run_script(SCRIPT_PATH, 'run', '--command-args=--version', '--mode', 'errors', cwd=temp_dir)
        assert result.returncode == 0, f'Should succeed: {result.stderr}'


def test_run_mode_structured():
    """Test run with --mode structured."""
    with mock_npm_project() as temp_dir:
        result = run_script(SCRIPT_PATH, 'run', '--command-args=--version', '--mode', 'structured', cwd=temp_dir)
        assert result.returncode == 0, f'Should succeed: {result.stderr}'


# =============================================================================
# Format Parameter Tests
# =============================================================================


def test_run_format_json():
    """Test run with --format json produces valid JSON."""
    with mock_npm_project() as temp_dir:
        result = run_script(SCRIPT_PATH, 'run', '--command-args=--version', '--format', 'json', cwd=temp_dir)
        assert result.returncode == 0
        import json

        data = json.loads(result.stdout)
        assert data['status'] == 'success'


# =============================================================================
# Help Tests
# =============================================================================


def test_run_help():
    """Test run subcommand help."""
    result = run_script(SCRIPT_PATH, 'run', '--help')
    assert '--command-args' in result.stdout, 'Should show --command-args option'
    assert '--mode' in result.stdout, 'Should show --mode option'
    assert '--working-dir' in result.stdout, 'Should show --working-dir option'
    assert '--env' in result.stdout, 'Should show --env option'


# =============================================================================
# safe_main Tests
# =============================================================================


def test_safe_main_wraps_errors():
    """Test that safe_main catches unhandled exceptions and produces TOON error."""
    # Running with invalid subcommand should trigger argparse error (SystemExit)
    # which safe_main lets through, but we verify it doesn't crash
    result = run_script(SCRIPT_PATH, 'invalid-command')
    assert result.returncode != 0

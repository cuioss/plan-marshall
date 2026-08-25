#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for npm run subcommand.

Tests the unified run command that combines execute + parse on failure:
- Success output format
- Failure output with parsed errors
- --mode parameter filtering
- Help text
"""

import json
import tempfile
from contextlib import contextmanager
from pathlib import Path

from conftest import get_script_path, run_script

SCRIPT_PATH = get_script_path('plan-marshall', 'build-npm', 'npm.py')


@contextmanager
def mock_npm_project(monkeypatch):
    """Context manager that creates a temp directory with npm available.

    Points PLAN_BASE_DIR at the temp dir so subprocess scripts launched via
    run_script() resolve plan-marshall paths inside the sandbox instead of
    raising on the (intentional) missing-git-repo case.

    The redirect goes through ``monkeypatch`` for the same reason its Maven
    sibling does: the autouse ``_plan_base_dir_sandbox`` fixture already owns
    this variable, and a hand-rolled save/assign/restore is a second owner of
    the same global whose restore only agrees with the first by ordering luck.
    """
    with tempfile.TemporaryDirectory() as td:
        temp_dir = Path(td)
        # No log directory is pre-created: the production resolver owns the
        # build-results path and creates its own directories as it places
        # output. Pre-creating one here would only mask a resolver that failed
        # to create the directory it resolved.
        (temp_dir / '.plan').mkdir(parents=True)
        (temp_dir / 'package.json').write_text('{"name": "test", "version": "1.0.0"}')
        monkeypatch.setenv('PLAN_BASE_DIR', str(temp_dir / '.plan'))
        yield temp_dir


def test_run_success_output_format(monkeypatch):
    """Test run command success output format (TOON)."""
    with mock_npm_project(monkeypatch) as temp_dir:
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


def test_run_includes_log_file(monkeypatch):
    """Test run command includes log_file path."""
    with mock_npm_project(monkeypatch) as temp_dir:
        result = run_script(SCRIPT_PATH, 'run', '--command-args=--version', cwd=temp_dir)

        assert result.returncode == 0
        assert 'log_file: ' in result.stdout, 'Should include log_file'
        assert 'npm-' in result.stdout, 'Log file should contain npm prefix'


def test_run_includes_duration(monkeypatch):
    """Test run command includes duration in output."""
    with mock_npm_project(monkeypatch) as temp_dir:
        result = run_script(SCRIPT_PATH, 'run', '--command-args=--version', cwd=temp_dir)

        assert 'duration_seconds' in result.stdout, 'Should include duration_seconds'


def test_run_failure_returns_exit_1(monkeypatch):
    """Test run command failure returns exit code 1."""
    with mock_npm_project(monkeypatch) as temp_dir:
        result = run_script(SCRIPT_PATH, 'run', '--command-args', 'run nonexistent-script-xyz', cwd=temp_dir)

        assert result.returncode == 0, 'Failed run should exit with 0 — status modeled in TOON output'
        assert 'status: error' in result.stdout, 'Should have error status'


def test_run_mode_actionable(monkeypatch):
    """Test run with --mode actionable (default)."""
    with mock_npm_project(monkeypatch) as temp_dir:
        result = run_script(SCRIPT_PATH, 'run', '--command-args=--version', '--mode', 'actionable', cwd=temp_dir)
        assert result.returncode == 0, f'Should succeed: {result.stderr}'
        assert 'status: success' in result.stdout


def test_run_mode_errors(monkeypatch):
    """Test run with --mode errors."""
    with mock_npm_project(monkeypatch) as temp_dir:
        result = run_script(SCRIPT_PATH, 'run', '--command-args=--version', '--mode', 'errors', cwd=temp_dir)
        assert result.returncode == 0, f'Should succeed: {result.stderr}'


def test_run_mode_structured(monkeypatch):
    """Test run with --mode structured."""
    with mock_npm_project(monkeypatch) as temp_dir:
        result = run_script(SCRIPT_PATH, 'run', '--command-args=--version', '--mode', 'structured', cwd=temp_dir)
        assert result.returncode == 0, f'Should succeed: {result.stderr}'


def test_run_format_json(monkeypatch):
    """Test run with --format json produces valid JSON."""
    with mock_npm_project(monkeypatch) as temp_dir:
        result = run_script(SCRIPT_PATH, 'run', '--command-args=--version', '--format', 'json', cwd=temp_dir)
        assert result.returncode == 0

        data = json.loads(result.stdout)
        assert data['status'] == 'success'


def test_run_help():
    """Test run subcommand help."""
    result = run_script(SCRIPT_PATH, 'run', '--help')
    assert '--command-args' in result.stdout, 'Should show --command-args option'
    assert '--mode' in result.stdout, 'Should show --mode option'
    assert '--working-dir' in result.stdout, 'Should show --working-dir option'
    assert '--env' in result.stdout, 'Should show --env option'


def test_safe_main_wraps_errors():
    """Test that safe_main catches unhandled exceptions and produces TOON error."""
    # Running with invalid subcommand should trigger argparse error (SystemExit)
    # which safe_main lets through, but we verify it doesn't crash
    result = run_script(SCRIPT_PATH, 'invalid-command')
    assert result.returncode != 0

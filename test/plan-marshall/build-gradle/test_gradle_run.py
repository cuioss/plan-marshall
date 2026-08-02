#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for Gradle run subcommand.

Tests the unified run command that combines execute + parse on failure:
- Success output format (TOON tab-separated and JSON)
- Failure output with parsed errors
- --mode parameter filtering
- --format parameter for output format
- Log file location (the resolving plan's build-results/ directory)

These invocations pass no ``--plan-id``, so ``build_main`` resolves the absent
flag to the ``NO_PLAN`` sentinel and the logs land under that sentinel plan's
directory — the plan-less build is still attributed, just to no real plan.
"""

import json
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path

from conftest import get_script_path, run_script

# Script under test - plan-marshall bundle
SCRIPT_PATH = get_script_path('plan-marshall', 'build-gradle', 'gradle.py')
MOCKS_DIR = Path(__file__).parent / 'mocks'


@contextmanager
def mock_gradle_project(monkeypatch, mock_script: str = 'gradlew-success.sh'):
    """Context manager that creates a temp directory with mock Gradle wrapper.

    Uses ``monkeypatch.setenv`` to redirect ``PLAN_BASE_DIR`` and ``HOME``
    at the env-var level so subprocess scripts launched via ``run_script()``
    resolve plan-marshall paths (including ``~/.plan-marshall-credentials``
    and the run-configuration.json default location) inside the sandbox.
    The caller MUST pass in the test's ``monkeypatch`` fixture — the
    previous try/finally pattern against the shared host env leaked on
    exception paths and relied on cleanup rather than redirection.
    """
    with tempfile.TemporaryDirectory() as td:
        temp_dir = Path(td)
        # Only the PLAN_BASE_DIR root is staged. The log directory itself is
        # NOT pre-created: the production resolver owns the build-results path
        # and creates its own directories as it places output, so pre-creating
        # one would mask a resolver that failed to create what it resolved.
        (temp_dir / '.plan').mkdir(parents=True)
        # Copy mock wrapper to temp_dir as gradlew
        mock_path = MOCKS_DIR / mock_script
        if mock_path.exists():
            gradlew_path = temp_dir / 'gradlew'
            shutil.copy(mock_path, gradlew_path)
            gradlew_path.chmod(0o755)
        monkeypatch.setenv('PLAN_BASE_DIR', str(temp_dir / '.plan'))
        monkeypatch.setenv('HOME', str(temp_dir))
        yield temp_dir


def test_run_success_output_format(monkeypatch):
    """Test run command success output format (TOON format with tab separator)."""
    with mock_gradle_project(monkeypatch, 'gradlew-success.sh') as temp_dir:
        result = run_script(SCRIPT_PATH, 'run', '--command-args', 'clean test', cwd=temp_dir)

        assert result.returncode == 0, f'Successful run should exit with 0: {result.stderr}'

        # Parse TOON output
        data = result.toon()

        assert data.get('status') == 'success', f'Status should be success: {data}'
        assert 'log_file' in data, 'Should include log_file'
        assert str(data.get('exit_code')) == '0', 'Exit code should be 0'
        assert 'command' in data, 'Should include command (not command_executed)'


def test_run_includes_duration(monkeypatch):
    """Test run command includes duration in output."""
    with mock_gradle_project(monkeypatch, 'gradlew-success.sh') as temp_dir:
        result = run_script(SCRIPT_PATH, 'run', '--command-args', 'clean test', cwd=temp_dir)

        assert 'duration_seconds' in result.stdout, 'Should include duration_seconds'


def test_run_failure_includes_errors(monkeypatch):
    """Test run command failure includes error status."""
    with mock_gradle_project(monkeypatch, 'gradlew-failure.sh') as temp_dir:
        result = run_script(SCRIPT_PATH, 'run', '--command-args', 'clean test', cwd=temp_dir)

        assert result.returncode == 0, 'Failed run should exit with 0 — status modeled in TOON output'
        assert 'status: error' in result.stdout, 'Should have error status'


def test_run_mode_actionable(monkeypatch):
    """Test run with --mode actionable (default)."""
    with mock_gradle_project(monkeypatch, 'gradlew-success.sh') as temp_dir:
        result = run_script(SCRIPT_PATH, 'run', '--command-args', 'clean test', '--mode', 'actionable', cwd=temp_dir)

        assert result.returncode == 0, f'Should succeed: {result.stderr}'
        assert 'status: success' in result.stdout, 'Should have success status'


def test_run_mode_errors(monkeypatch):
    """Test run with --mode errors (no warnings)."""
    with mock_gradle_project(monkeypatch, 'gradlew-success.sh') as temp_dir:
        result = run_script(SCRIPT_PATH, 'run', '--command-args', 'clean test', '--mode', 'errors', cwd=temp_dir)

        assert result.returncode == 0, f'Should succeed: {result.stderr}'


def test_run_with_module_routing(monkeypatch):
    """Test run with module routing embedded in command-args."""
    with mock_gradle_project(monkeypatch, 'gradlew-success.sh') as temp_dir:
        result = run_script(SCRIPT_PATH, 'run', '--command-args', ':core:clean :core:test', cwd=temp_dir)

        assert result.returncode == 0, f'Should succeed: {result.stderr}'
        # Log file should be in the core scope, under the resolving plan's dir.
        assert '/plans/NO_PLAN/build-results/core/gradle-' in result.stdout, (
            'Log file should be in the core scope of the resolving plan'
        )


def test_run_format_json(monkeypatch):
    """Test run with --format json produces valid JSON output."""
    with mock_gradle_project(monkeypatch, 'gradlew-success.sh') as temp_dir:
        result = run_script(SCRIPT_PATH, 'run', '--command-args', 'clean test', '--format', 'json', cwd=temp_dir)

        assert result.returncode == 0, f'Should succeed: {result.stderr}'
        # Should be valid JSON
        data = json.loads(result.stdout)
        assert data['status'] == 'success', 'Status should be success'
        assert data['exit_code'] == 0, 'Exit code should be 0'
        assert 'command' in data, 'Should include command'
        assert 'log_file' in data, 'Should include log_file'
        assert 'duration_seconds' in data, 'Should include duration_seconds'


def test_run_format_toon_default(monkeypatch):
    """Test run defaults to TOON format."""
    with mock_gradle_project(monkeypatch, 'gradlew-success.sh') as temp_dir:
        result = run_script(SCRIPT_PATH, 'run', '--command-args', 'clean test', cwd=temp_dir)

        assert result.returncode == 0, f'Should succeed: {result.stderr}'
        # Should be TOON format (key: value), not JSON
        assert 'status: ' in result.stdout, 'Should use TOON key: value format'
        assert '{' not in result.stdout.split('\n')[0], 'First line should not be JSON'


def test_run_log_file_location(monkeypatch):
    """Test the log is created in the resolving plan's build-results directory."""
    with mock_gradle_project(monkeypatch, 'gradlew-success.sh') as temp_dir:
        result = run_script(SCRIPT_PATH, 'run', '--command-args', 'clean test', cwd=temp_dir)

        assert result.returncode == 0, f'Should succeed: {result.stderr}'
        assert '/plans/NO_PLAN/build-results/' in result.stdout, (
            "Log should be under the resolving plan's build-results directory"
        )
        assert 'gradle-' in result.stdout, 'Log file should have gradle- prefix'


def test_run_help():
    """Test run subcommand help."""
    result = run_script(SCRIPT_PATH, 'run', '--help')
    assert '--command-args' in result.stdout, 'Should show --command-args option'
    assert '--mode' in result.stdout, 'Should show --mode option'
    assert '--format' in result.stdout, 'Should show --format option'

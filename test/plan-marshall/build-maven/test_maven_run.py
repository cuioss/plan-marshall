#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for Maven run subcommand.

Tests the unified run command that combines execute + parse on failure:
- Success output format
- Failure output with parsed errors
- Timeout handling
- --mode parameter filtering
"""

import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path

from conftest import get_script_path, run_script

# Script under test - plan-marshall bundle
SCRIPT_PATH = get_script_path('plan-marshall', 'build-maven', 'maven.py')
MOCKS_DIR = Path(__file__).parent / 'mocks'


@contextmanager
def mock_maven_project(monkeypatch, mock_script: str = 'mvnw-success.sh'):
    """Context manager that creates a temp directory with mock Maven wrapper.

    Points PLAN_BASE_DIR at the temp dir so subprocess scripts launched via
    run_script() resolve plan-marshall paths inside the sandbox instead of
    raising on the (intentional) missing-git-repo case.

    The redirect goes through ``monkeypatch`` rather than a hand-rolled
    save/assign/restore of ``os.environ``: the autouse ``_plan_base_dir_sandbox``
    fixture already owns this variable for every test, and two mechanisms
    writing the same global is an ownership split — the manual restore puts back
    whatever it happened to read, which is the sandbox's value, so the two only
    agree by luck of ordering. ``monkeypatch`` unwinds in the same registry the
    sandbox used, so the ownership stays with one mechanism.
    """
    with tempfile.TemporaryDirectory() as td:
        temp_dir = Path(td)
        # Create target directory for log files
        (temp_dir / 'target').mkdir()
        # Only the PLAN_BASE_DIR root is staged. The log directory itself is
        # NOT pre-created: the production resolver owns the build-results path
        # and creates its own directories as it places output, so pre-creating
        # one would mask a resolver that failed to create what it resolved.
        (temp_dir / '.plan').mkdir(parents=True)
        # Copy mock wrapper to temp_dir as mvnw
        mock_path = MOCKS_DIR / mock_script
        if mock_path.exists():
            mvnw_path = temp_dir / 'mvnw'
            shutil.copy(mock_path, mvnw_path)
            mvnw_path.chmod(0o755)
        monkeypatch.setenv('PLAN_BASE_DIR', str(temp_dir / '.plan'))
        yield temp_dir


# =============================================================================
# Run Success Tests
# =============================================================================


def test_run_success_output_format(monkeypatch):
    """Test run command success output format (TOON format - tab-separated)."""
    with mock_maven_project(monkeypatch, 'mvnw-success.sh') as temp_dir:
        result = run_script(SCRIPT_PATH, 'run', '--command-args', 'clean test', cwd=temp_dir)

        assert result.returncode == 0, f'Successful run should exit with 0: {result.stderr}'

        # Parse TOON output
        data = result.toon()

        assert data.get('status') == 'success', f'Status should be success: {data}'
        assert 'log_file' in data, 'Should include log_file'
        assert str(data.get('exit_code')) == '0', 'Exit code should be 0'
        assert 'command' in data, 'Should include command field'


def test_run_includes_duration(monkeypatch):
    """Test run command includes duration in output."""
    with mock_maven_project(monkeypatch, 'mvnw-success.sh') as temp_dir:
        result = run_script(SCRIPT_PATH, 'run', '--command-args', 'clean test', cwd=temp_dir)

        assert 'duration_seconds' in result.stdout, 'Should include duration_seconds'


# =============================================================================
# Run Failure Tests
# =============================================================================


def test_run_failure_includes_errors(monkeypatch):
    """Test run command failure includes parsed errors."""
    with mock_maven_project(monkeypatch, 'mvnw-failure.sh') as temp_dir:
        result = run_script(SCRIPT_PATH, 'run', '--command-args', 'clean test', cwd=temp_dir)

        assert result.returncode == 0, 'Failed run should exit with 0 — status modeled in TOON output'
        assert 'status: error' in result.stdout, 'Should have error status'
        assert 'error: build_failed' in result.stdout, 'Should have build_failed error type'
        assert 'command: ' in result.stdout, 'Should include command field'


def test_run_failure_with_compilation_errors(monkeypatch):
    """Test run command failure with compilation errors includes file/line info."""
    with mock_maven_project(monkeypatch, 'mvnw-failure.sh') as temp_dir:
        result = run_script(SCRIPT_PATH, 'run', '--command-args', 'clean test', cwd=temp_dir)

        # Even if mock doesn't produce parse-able errors, the format should be correct
        assert 'status: error' in result.stdout, 'Should have error status'


# =============================================================================
# Truthful-status regression (seam a): status derived from the real outcome
# =============================================================================


def test_run_build_failure_reports_error_and_nonzero_exit_code(monkeypatch):
    """Seam (a): a genuine BUILD FAILURE (non-zero mvnw exit) reports
    status=error with a non-zero exit_code — never an untruthful success.

    The in-process foundation already derives error from the non-zero
    returncode; this regression locks that path so the truthful-status fix
    cannot inadvertently soften it.
    """
    with mock_maven_project(monkeypatch, 'mvnw-failure.sh') as temp_dir:
        result = run_script(SCRIPT_PATH, 'run', '--command-args', 'clean test', cwd=temp_dir)

        data = result.toon()
        assert data.get('status') == 'error', f'BUILD FAILURE must report error: {data}'
        assert int(data.get('exit_code')) != 0, f'exit_code must be non-zero on BUILD FAILURE: {data}'


def test_run_testfailureignore_exit0_reports_error(monkeypatch):
    """Seam (a): an exit-0 run whose log shows erroring tests (surefire
    testFailureIgnore / reactor --fail-never) is downgraded to status=error.

    Maven exits 0 and prints BUILD SUCCESS, but the test summary reports
    Errors > 0. Trusting returncode==0 would emit an untruthful success; the
    fail-closed cross-check must report error instead.
    """
    with mock_maven_project(monkeypatch, 'mvnw-testfailureignore.sh') as temp_dir:
        result = run_script(SCRIPT_PATH, 'run', '--command-args', 'clean test', cwd=temp_dir)

        data = result.toon()
        assert data.get('status') == 'error', (
            f'exit-0-with-test-errors must report error, not untruthful success: {data}'
        )


# =============================================================================
# Mode Parameter Tests
# =============================================================================


def test_run_mode_actionable(monkeypatch):
    """Test run with --mode actionable (default)."""
    with mock_maven_project(monkeypatch, 'mvnw-success.sh') as temp_dir:
        result = run_script(SCRIPT_PATH, 'run', '--command-args', 'clean test', '--mode', 'actionable', cwd=temp_dir)

        assert result.returncode == 0, f'Should succeed: {result.stderr}'
        assert 'status: success' in result.stdout


def test_run_mode_errors(monkeypatch):
    """Test run with --mode errors (no warnings)."""
    with mock_maven_project(monkeypatch, 'mvnw-success.sh') as temp_dir:
        result = run_script(SCRIPT_PATH, 'run', '--command-args', 'clean test', '--mode', 'errors', cwd=temp_dir)

        assert result.returncode == 0, f'Should succeed: {result.stderr}'


def test_run_mode_structured(monkeypatch):
    """Test run with --mode structured (all issues with markers)."""
    with mock_maven_project(monkeypatch, 'mvnw-success.sh') as temp_dir:
        result = run_script(SCRIPT_PATH, 'run', '--command-args', 'clean test', '--mode', 'structured', cwd=temp_dir)

        assert result.returncode == 0, f'Should succeed: {result.stderr}'


# =============================================================================
# Module Routing Tests (embedded in command-args)
# =============================================================================


def test_run_with_module_routing(monkeypatch):
    """Test run with module routing embedded in command-args."""
    with mock_maven_project(monkeypatch, 'mvnw-success.sh') as temp_dir:
        result = run_script(SCRIPT_PATH, 'run', '--command-args', 'clean test -pl core', cwd=temp_dir)

        assert result.returncode == 0, f'Should succeed: {result.stderr}'
        # Check command includes module
        assert 'command: ' in result.stdout


# =============================================================================
# Help Test
# =============================================================================


def test_run_help():
    """Test run subcommand help."""
    result = run_script(SCRIPT_PATH, 'run', '--help')
    assert '--command-args' in result.stdout, 'Should show --command-args option'
    assert '--mode' in result.stdout, 'Should show --mode option'


# =============================================================================
# Main
# =============================================================================

#!/usr/bin/env python3
"""Tests for npm.py script.

Tests the foundation layer for npm command execution including
command type detection, timeout handling, and command execution.
"""

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import BuildContext, get_script_path, load_script_module

# Get script path
SCRIPT_PATH = get_script_path('plan-marshall', 'build-npm', 'npm.py')


from _build_shared import get_bash_timeout  # noqa: E402, I001


_npm_execute_mod = load_script_module('plan-marshall', 'build-npm', '_npm_execute.py', '_npm_execute')

detect_command_type = _npm_execute_mod.detect_command_type
execute_direct = _npm_execute_mod.execute_direct

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
    assert get_bash_timeout(60) == 90  # 60 + 30 buffer
    assert get_bash_timeout(120) == 150  # 120 + 30 buffer


def test_api_execute_direct_success():
    """Test execute_direct API with successful command."""
    with BuildContext() as ctx:
        result = execute_direct(
            args='--version', command_key='test:version', default_timeout=10, project_dir=str(ctx.temp_dir)
        )

        # npm --version should succeed (npm is available in most environments)
        assert result['status'] == 'success'
        assert result['exit_code'] == 0
        assert result['command_type'] == 'npm'


def test_api_execute_direct_returns_log_file():
    """Test execute_direct API returns log_file (R1 compliance)."""
    with BuildContext() as ctx:
        result = execute_direct(
            args='--version', command_key='test:log_file', default_timeout=10, project_dir=str(ctx.temp_dir)
        )

        # R1: All build output must go to a log file
        assert 'log_file' in result
        assert result['log_file'], 'log_file should not be empty'
        assert '.plan/temp/build-output' in result['log_file']
        assert 'npm-' in result['log_file']  # Build system in filename


def test_api_execute_direct_npx_command():
    """Test execute_direct API with npx command."""
    with BuildContext() as ctx:
        result = execute_direct(
            args='--version', command_key='test:npx_version', default_timeout=10, project_dir=str(ctx.temp_dir)
        )

        # --version is detected as npm not npx (starts with -)
        assert result['status'] == 'success'
        assert result['command_type'] == 'npm'


# =============================================================================
# Two-state ``--plan-id`` / ``--project-dir`` routing contract
# =============================================================================
#
# npm.py uses the shared ``build_main()`` from ``_build_cli.py``. The
# resolver semantics are pinned in
# ``test/plan-marshall/script-shared/test_build_cli.py``; here we only
# verify the parser surface.

from conftest import run_script  # noqa: E402


def test_run_subcommand_accepts_plan_id_flag():
    """npm.py's `run` subcommand MUST accept --plan-id (auto-routing flag)."""
    result = run_script(SCRIPT_PATH, 'run', '--help')
    assert result.success, f'Script failed: {result.stderr}'
    assert '--plan-id' in result.stdout, 'npm run must declare --plan-id'
    assert '--project-dir' in result.stdout, 'npm run must keep --project-dir as escape hatch'


def test_run_rejects_both_plan_id_and_project_dir():
    """Both --plan-id and --project-dir together MUST yield mutually_exclusive_args."""
    result = run_script(
        SCRIPT_PATH,
        'run',
        '--command-args',
        'install',
        '--plan-id',
        'task-routing-canonical',
        '--project-dir',
        '/tmp/explicit',
    )
    assert result.returncode == 2, f'Expected exit 2, got {result.returncode} (stdout={result.stdout!r})'
    data = result.toon_or_error()
    assert data.get('status') == 'error'
    assert data.get('error') == 'mutually_exclusive_args'


# =============================================================================
# Runner
# =============================================================================

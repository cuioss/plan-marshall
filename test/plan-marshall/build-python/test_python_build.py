#!/usr/bin/env python3
"""Tests for plan-marshall build-python python_build.py.

Tests the Python build operations including:
- parse_log() - Log parsing for errors
- execute_direct() - Foundation API (mocked subprocess)
"""

import importlib.util
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import BuildContext

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
BUILD_SCRIPT = (
    PROJECT_ROOT
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'build-python'
    / 'scripts'
    / 'python_build.py'
)


def _load_python_build():
    """Load python_build module with minimal mocking.

    Only mocks plan_logging and run_config which are provided by the executor
    at runtime but not available in test PYTHONPATH.
    """
    spec = importlib.util.spec_from_file_location('python_build', BUILD_SCRIPT)
    module = importlib.util.module_from_spec(spec)

    import sys

    mock_modules = {
        'plan_logging': MagicMock(log_entry=MagicMock()),
        'run_config': MagicMock(timeout_get=MagicMock(return_value=300), timeout_set=MagicMock()),
    }

    # Save originals so we can restore after loading
    saved = {name: sys.modules.get(name) for name in mock_modules}
    for name, mock in mock_modules.items():
        sys.modules[name] = mock

    spec.loader.exec_module(module)

    # Restore original modules to avoid polluting sys.modules for other tests
    for name, original in saved.items():
        if original is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = original

    return module


python_build = _load_python_build()

# Direct imports for functions no longer re-exported through python_build
from _python_cmd_parse import parse_log  # noqa: E402
from _python_execute import execute_direct  # noqa: E402


# =============================================================================
# Test: Wrapper resolution (via _python_execute)
# =============================================================================


def test_wrapper_resolution_finds_local_pw():
    """Wrapper resolution finds ./pw when pw exists in project root."""
    from _python_execute import _python_wrapper_resolve_fn

    with BuildContext() as ctx:
        pw = ctx.temp_dir / 'pw'
        pw.write_text('#!/bin/bash\necho "pw"')
        pw.chmod(0o755)

        result = _python_wrapper_resolve_fn(str(ctx.temp_dir))
        assert result == './pw'


def test_wrapper_resolution_falls_back_to_system_pwx():
    """Wrapper resolution returns pwx when no local pw but pwx is in PATH."""
    from _python_execute import _python_wrapper_resolve_fn

    with BuildContext() as ctx:
        with patch('shutil.which', return_value='/usr/local/bin/pwx'):
            result = _python_wrapper_resolve_fn(str(ctx.temp_dir))
            assert result == 'pwx'


def test_wrapper_resolution_raises_when_no_wrapper():
    """Wrapper resolution raises FileNotFoundError when no wrapper available."""
    from _python_execute import _python_wrapper_resolve_fn

    with BuildContext() as ctx:
        with patch('shutil.which', return_value=None):
            with pytest.raises(FileNotFoundError, match='No pyprojectx wrapper found'):
                _python_wrapper_resolve_fn(str(ctx.temp_dir))


# =============================================================================
# Test: parse_log() - Error Parsing
# =============================================================================


def test_parse_log_parses_mypy_errors():
    """parse_log() extracts mypy type errors."""
    log_content = """
src/main.py:10: error: Incompatible types in assignment
src/utils.py:25: error: Missing return statement
"""
    with BuildContext() as ctx:
        log_file = ctx.temp_dir / 'build.log'
        log_file.write_text(log_content)

        issues, test_summary, build_status = parse_log(str(log_file))

        assert len(issues) == 2
        assert issues[0].file == 'src/main.py'
        assert issues[0].line == 10
        assert 'Incompatible types' in issues[0].message
        assert issues[0].category == 'type_error'


def test_parse_log_parses_ruff_errors():
    """parse_log() extracts ruff lint errors."""
    log_content = """
src/main.py:15:1: E501 Line too long (120 > 88)
src/utils.py:30:5: F401 'os' imported but unused
"""
    with BuildContext() as ctx:
        log_file = ctx.temp_dir / 'build.log'
        log_file.write_text(log_content)

        issues, test_summary, build_status = parse_log(str(log_file))

        assert len(issues) == 2
        assert issues[0].file == 'src/main.py'
        assert issues[0].line == 15
        assert 'E501' in issues[0].message
        assert issues[0].category == 'lint_error'


def test_parse_log_parses_pytest_failures():
    """parse_log() extracts pytest test failures."""
    log_content = """
FAILED test/test_main.py::test_addition - AssertionError: assert 1 == 2
FAILED test/test_utils.py::test_helper
"""
    with BuildContext() as ctx:
        log_file = ctx.temp_dir / 'build.log'
        log_file.write_text(log_content)

        issues, test_summary, build_status = parse_log(str(log_file))

        assert len(issues) == 2
        assert issues[0].file == 'test/test_main.py'
        assert 'AssertionError' in issues[0].message
        assert issues[0].category == 'test_failure'
        assert issues[1].file == 'test/test_utils.py'


def test_parse_log_extracts_test_summary():
    """parse_log() extracts pytest summary statistics."""
    log_content = """
================ 40 passed, 2 failed, 1 skipped in 5.23s ================
"""
    with BuildContext() as ctx:
        log_file = ctx.temp_dir / 'build.log'
        log_file.write_text(log_content)

        issues, test_summary, build_status = parse_log(str(log_file))

        assert test_summary is not None
        assert test_summary.passed == 40
        assert test_summary.failed == 2
        assert test_summary.skipped == 1


def test_parse_log_handles_missing_file():
    """parse_log() returns empty results for missing log file."""
    issues, test_summary, build_status = parse_log('/nonexistent/path.log')

    assert issues == []
    assert test_summary is None
    assert build_status == 'FAILURE'


def test_parse_log_handles_empty_file():
    """parse_log() returns empty results for empty log file."""
    with BuildContext() as ctx:
        log_file = ctx.temp_dir / 'build.log'
        log_file.write_text('')

        issues, test_summary, build_status = parse_log(str(log_file))

        assert issues == []
        assert test_summary is None


# =============================================================================
# Test: execute_direct() - Mocked Execution
# =============================================================================


def test_execute_direct_returns_error_when_no_wrapper():
    """execute_direct() returns error when no wrapper is found."""
    with BuildContext() as ctx:
        # No ./pw and no system pwx
        with patch('shutil.which', return_value=None):
            result = execute_direct(
                args='verify', command_key='python:verify', default_timeout=300, project_dir=str(ctx.temp_dir)
            )

            assert result['status'] == 'error'
            assert result['exit_code'] == -1
            assert 'No pyprojectx wrapper found' in result['error']


def test_execute_direct_returns_success_on_zero_exit():
    """execute_direct() returns success when command exits with 0."""
    with BuildContext() as ctx:
        # Create ./pw wrapper
        pw = ctx.temp_dir / 'pw'
        pw.write_text('#!/bin/bash\necho "success"')
        pw.chmod(0o755)

        # Create .plan/temp directory for log file
        plan_temp = ctx.temp_dir / '.plan' / 'temp' / 'build-output' / 'default'
        plan_temp.mkdir(parents=True)

        # Mock subprocess.run to return success
        mock_result = MagicMock()
        mock_result.returncode = 0

        with (
            patch('subprocess.run', return_value=mock_result),
            patch('_build_execute.create_log_file', return_value=str(ctx.temp_dir / 'test.log')),
        ):
            result = execute_direct(
                args='verify', command_key='python:verify', default_timeout=300, project_dir=str(ctx.temp_dir)
            )

            assert result['status'] == 'success'
            assert result['exit_code'] == 0
            assert result['wrapper'] == './pw'


def test_execute_direct_returns_error_on_nonzero_exit():
    """execute_direct() returns error when command exits with non-zero."""
    with BuildContext() as ctx:
        # Create ./pw wrapper
        pw = ctx.temp_dir / 'pw'
        pw.write_text('#!/bin/bash\nexit 1')
        pw.chmod(0o755)

        # Mock subprocess.run to return failure
        mock_result = MagicMock()
        mock_result.returncode = 1

        with (
            patch('subprocess.run', return_value=mock_result),
            patch('_build_execute.create_log_file', return_value=str(ctx.temp_dir / 'test.log')),
        ):
            result = execute_direct(
                args='verify', command_key='python:verify', default_timeout=300, project_dir=str(ctx.temp_dir)
            )

            assert result['status'] == 'error'
            assert result['exit_code'] == 1
            assert 'Build failed' in result['error']


def test_execute_direct_returns_timeout_on_timeout():
    """execute_direct() returns timeout when command times out."""
    import subprocess

    with BuildContext() as ctx:
        # Create ./pw wrapper
        pw = ctx.temp_dir / 'pw'
        pw.write_text('#!/bin/bash\nsleep 100')
        pw.chmod(0o755)

        with (
            patch('subprocess.run', side_effect=subprocess.TimeoutExpired(cmd='./pw verify', timeout=60)),
            patch('_build_execute.create_log_file', return_value=str(ctx.temp_dir / 'test.log')),
        ):
            result = execute_direct(
                args='verify', command_key='python:verify', default_timeout=60, project_dir=str(ctx.temp_dir)
            )

            assert result['status'] == 'timeout'
            assert 'timed out' in result['error']


# =============================================================================
# Test: Constants
# =============================================================================


def test_default_timeout_is_reasonable():
    """Default timeout in execute config is set to a reasonable value."""
    from _python_execute import _CONFIG
    assert _CONFIG.default_timeout == 300  # 5 minutes, unified across all build skills


def test_min_timeout_is_enforced():
    """MIN_TIMEOUT is enforced globally in _build_execute."""
    from _build_execute import MIN_TIMEOUT
    assert MIN_TIMEOUT == 60  # 1 minute minimum, enforced for all build systems

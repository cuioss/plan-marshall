#!/usr/bin/env python3
"""Tests for pm-dev-python python_build.py.

Tests the Python build operations including:
- detect_wrapper() - Wrapper detection
- parse_python_log() - Log parsing for errors
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
    / 'pm-dev-python'
    / 'skills'
    / 'plan-marshall-plugin'
    / 'scripts'
    / 'python_build.py'
)


def _load_python_build():
    """Load python_build module avoiding conflicts."""
    spec = importlib.util.spec_from_file_location('python_build', BUILD_SCRIPT)
    module = importlib.util.module_from_spec(spec)

    # Mock the cross-skill imports before loading
    import sys

    mock_modules = {
        '_build_format': MagicMock(format_json=MagicMock(return_value='{}'), format_toon=MagicMock(return_value='')),
        '_build_parse': MagicMock(
            Issue=MagicMock,
            UnitTestSummary=MagicMock,
            filter_warnings=MagicMock(return_value=[]),
            load_acceptable_warnings=MagicMock(return_value=[]),
            partition_issues=MagicMock(return_value=([], [])),
        ),
        '_build_result': MagicMock(
            ERROR_BUILD_FAILED='build_failed',
            ERROR_EXECUTION_FAILED='execution_failed',
            ERROR_LOG_FILE_FAILED='log_file_creation_failed',
            DirectCommandResult=dict,
            create_log_file=MagicMock(return_value='/tmp/test.log'),
            error_result=MagicMock(return_value={}),
            success_result=MagicMock(return_value={}),
            timeout_result=MagicMock(return_value={}),
        ),
        'plan_logging': MagicMock(log_entry=MagicMock()),
        'run_config': MagicMock(timeout_get=MagicMock(return_value=300), timeout_set=MagicMock()),
    }
    for name, mock in mock_modules.items():
        sys.modules[name] = mock

    spec.loader.exec_module(module)
    return module


python_build = _load_python_build()


# =============================================================================
# Test: detect_wrapper()
# =============================================================================


def test_detect_wrapper_finds_local_pw():
    """detect_wrapper() returns ./pw when pw exists in project root."""
    with BuildContext() as ctx:
        # Create ./pw wrapper
        pw = ctx.temp_dir / 'pw'
        pw.write_text('#!/bin/bash\necho "pw"')
        pw.chmod(0o755)

        result = python_build.detect_wrapper(str(ctx.temp_dir))
        assert result == './pw'


def test_detect_wrapper_falls_back_to_system_pwx():
    """detect_wrapper() returns pwx when no local pw but pwx is in PATH."""
    with BuildContext() as ctx:
        # No ./pw exists, mock shutil.which to return pwx
        with patch('shutil.which', return_value='/usr/local/bin/pwx'):
            result = python_build.detect_wrapper(str(ctx.temp_dir))
            assert result == 'pwx'


def test_detect_wrapper_raises_when_no_wrapper():
    """detect_wrapper() raises FileNotFoundError when no wrapper available."""
    with BuildContext() as ctx:
        # No ./pw exists, mock shutil.which to return None
        with patch('shutil.which', return_value=None):
            with pytest.raises(FileNotFoundError, match='No pyprojectx wrapper found'):
                python_build.detect_wrapper(str(ctx.temp_dir))


# =============================================================================
# Test: parse_python_log() - Error Parsing
# =============================================================================


def test_parse_python_log_parses_mypy_errors():
    """parse_python_log() extracts mypy type errors."""
    log_content = """
src/main.py:10: error: Incompatible types in assignment
src/utils.py:25: error: Missing return statement
"""
    with BuildContext() as ctx:
        log_file = ctx.temp_dir / 'build.log'
        log_file.write_text(log_content)

        issues, test_summary, build_status = python_build.parse_python_log(str(log_file))

        assert len(issues) == 2
        assert issues[0].file == 'src/main.py'
        assert issues[0].line == 10
        assert 'Incompatible types' in issues[0].message
        assert issues[0].category == 'type_error'


def test_parse_python_log_parses_ruff_errors():
    """parse_python_log() extracts ruff lint errors."""
    log_content = """
src/main.py:15:1: E501 Line too long (120 > 88)
src/utils.py:30:5: F401 'os' imported but unused
"""
    with BuildContext() as ctx:
        log_file = ctx.temp_dir / 'build.log'
        log_file.write_text(log_content)

        issues, test_summary, build_status = python_build.parse_python_log(str(log_file))

        assert len(issues) == 2
        assert issues[0].file == 'src/main.py'
        assert issues[0].line == 15
        assert 'E501' in issues[0].message
        assert issues[0].category == 'lint_error'


def test_parse_python_log_parses_pytest_failures():
    """parse_python_log() extracts pytest test failures."""
    log_content = """
FAILED test/test_main.py::test_addition - AssertionError: assert 1 == 2
FAILED test/test_utils.py::test_helper
"""
    with BuildContext() as ctx:
        log_file = ctx.temp_dir / 'build.log'
        log_file.write_text(log_content)

        issues, test_summary, build_status = python_build.parse_python_log(str(log_file))

        assert len(issues) == 2
        assert issues[0].file == 'test/test_main.py'
        assert 'AssertionError' in issues[0].message
        assert issues[0].category == 'test_failure'
        assert issues[1].file == 'test/test_utils.py'


def test_parse_python_log_extracts_test_summary():
    """parse_python_log() extracts pytest summary statistics."""
    log_content = """
================ 40 passed, 2 failed, 1 skipped in 5.23s ================
"""
    with BuildContext() as ctx:
        log_file = ctx.temp_dir / 'build.log'
        log_file.write_text(log_content)

        issues, test_summary, build_status = python_build.parse_python_log(str(log_file))

        assert test_summary is not None
        assert test_summary.passed == 40
        assert test_summary.failed == 2
        assert test_summary.skipped == 1


def test_parse_python_log_handles_missing_file():
    """parse_python_log() returns empty results for missing log file."""
    issues, test_summary, build_status = python_build.parse_python_log('/nonexistent/path.log')

    assert issues == []
    assert test_summary is None
    assert build_status == 'FAILURE'


def test_parse_python_log_handles_empty_file():
    """parse_python_log() returns empty results for empty log file."""
    with BuildContext() as ctx:
        log_file = ctx.temp_dir / 'build.log'
        log_file.write_text('')

        issues, test_summary, build_status = python_build.parse_python_log(str(log_file))

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
            result = python_build.execute_direct(
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
            patch.object(python_build, 'create_log_file', return_value=str(ctx.temp_dir / 'test.log')),
        ):
            result = python_build.execute_direct(
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
            patch.object(python_build, 'create_log_file', return_value=str(ctx.temp_dir / 'test.log')),
        ):
            result = python_build.execute_direct(
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
            patch.object(python_build, 'create_log_file', return_value=str(ctx.temp_dir / 'test.log')),
        ):
            result = python_build.execute_direct(
                args='verify', command_key='python:verify', default_timeout=60, project_dir=str(ctx.temp_dir)
            )

            assert result['status'] == 'timeout'
            assert 'timed out' in result['error']


# =============================================================================
# Test: Constants
# =============================================================================


def test_default_timeout_is_reasonable():
    """DEFAULT_TIMEOUT is set to a reasonable value."""
    assert python_build.DEFAULT_TIMEOUT == 300  # 5 minutes


def test_min_timeout_is_enforced():
    """MIN_TIMEOUT prevents too-short timeouts."""
    assert python_build.MIN_TIMEOUT == 60  # 1 minute minimum

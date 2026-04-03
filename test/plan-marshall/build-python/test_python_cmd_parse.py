#!/usr/bin/env python3
"""Tests for _python_cmd_parse.py (direct parser API).

Tests the Python build log parser directly (not through python_build.py).

Note: test_python_build.py also tests parse_log() but through the build script
module loader with mocked dependencies. This file tests the parser in isolation
for detailed coverage of mypy/ruff/pytest output patterns.
"""

import tempfile
from pathlib import Path

import pytest

from _build_parse import Issue, UnitTestSummary
from _python_cmd_parse import parse_log


# =============================================================================
# mypy error parsing
# =============================================================================


def test_parse_mypy_errors():
    """Extracts mypy type errors with file and line."""
    content = """src/main.py:10: error: Incompatible types in assignment
src/utils.py:25: error: Missing return statement
Found 2 errors in 2 files
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
        f.write(content)
        f.flush()
        issues, _, _ = parse_log(f.name)
        Path(f.name).unlink()

    assert len(issues) == 2
    assert issues[0].file == 'src/main.py'
    assert issues[0].line == 10
    assert issues[0].category == 'type_error'
    assert issues[0].severity == 'error'
    assert 'Incompatible types' in issues[0].message


def test_parse_mypy_no_errors():
    """Returns empty issues for clean mypy output."""
    content = """Success: no issues found in 5 source files\n"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
        f.write(content)
        f.flush()
        issues, _, _ = parse_log(f.name)
        Path(f.name).unlink()

    assert len(issues) == 0


# =============================================================================
# ruff error parsing
# =============================================================================


def test_parse_ruff_errors():
    """Extracts ruff lint errors with file, line, and rule code."""
    content = """src/main.py:15:1: E501 Line too long (120 > 88)
src/utils.py:30:5: F401 'os' imported but unused
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
        f.write(content)
        f.flush()
        issues, _, _ = parse_log(f.name)
        Path(f.name).unlink()

    assert len(issues) == 2
    assert issues[0].file == 'src/main.py'
    assert issues[0].line == 15
    assert issues[0].category == 'lint_error'
    assert 'E501' in issues[0].message


# =============================================================================
# pytest failure parsing
# =============================================================================


def test_parse_pytest_failures():
    """Extracts pytest test failures with file and message."""
    content = """FAILED test/test_main.py::test_addition - AssertionError: assert 1 == 2
FAILED test/test_utils.py::test_helper
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
        f.write(content)
        f.flush()
        issues, _, _ = parse_log(f.name)
        Path(f.name).unlink()

    assert len(issues) == 2
    assert issues[0].file == 'test/test_main.py'
    assert issues[0].category == 'test_failure'
    assert 'AssertionError' in issues[0].message
    assert issues[1].message == 'Test test_helper failed'


# =============================================================================
# pytest summary parsing
# =============================================================================


def test_parse_pytest_summary():
    """Extracts pytest summary with passed, failed, skipped counts."""
    content = """================ 40 passed, 2 failed, 1 skipped in 5.23s ================\n"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
        f.write(content)
        f.flush()
        _, test_summary, _ = parse_log(f.name)
        Path(f.name).unlink()

    assert isinstance(test_summary, UnitTestSummary)
    assert test_summary.passed == 40
    assert test_summary.failed == 2
    assert test_summary.skipped == 1
    assert test_summary.total == 43


def test_parse_pytest_summary_passed_only():
    """Handles pytest summary with only passed tests."""
    content = """================ 100 passed in 12.5s ================\n"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
        f.write(content)
        f.flush()
        _, test_summary, _ = parse_log(f.name)
        Path(f.name).unlink()

    assert test_summary is not None
    assert test_summary.passed == 100
    assert test_summary.failed == 0
    assert test_summary.skipped == 0


def test_parse_no_test_summary():
    """Returns None when no pytest summary found."""
    content = """mypy: success\n"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
        f.write(content)
        f.flush()
        _, test_summary, _ = parse_log(f.name)
        Path(f.name).unlink()

    assert test_summary is None


# =============================================================================
# Edge cases
# =============================================================================


def test_parse_missing_file():
    """Returns empty results for missing log file."""
    issues, test_summary, build_status = parse_log('/nonexistent/path.log')
    assert issues == []
    assert test_summary is None
    assert build_status == 'FAILURE'


def test_parse_empty_file():
    """Returns empty results for empty log file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
        f.write('')
        f.flush()
        issues, test_summary, build_status = parse_log(f.name)
        Path(f.name).unlink()

    assert issues == []
    assert test_summary is None


def test_parse_mixed_output():
    """Handles log with mypy, ruff, and pytest output together."""
    content = """src/main.py:10: error: Argument has incompatible type
src/main.py:15:1: E501 Line too long
FAILED test/test_main.py::test_foo - assert False
================ 5 passed, 1 failed in 2.1s ================
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
        f.write(content)
        f.flush()
        issues, test_summary, build_status = parse_log(f.name)
        Path(f.name).unlink()

    categories = [i.category for i in issues]
    assert 'type_error' in categories
    assert 'lint_error' in categories
    assert 'test_failure' in categories
    assert test_summary is not None
    assert test_summary.failed == 1


def test_parse_issues_are_issue_instances():
    """All returned issues are Issue dataclass instances."""
    content = """src/main.py:10: error: Bad type\n"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
        f.write(content)
        f.flush()
        issues, _, _ = parse_log(f.name)
        Path(f.name).unlink()

    for issue in issues:
        assert isinstance(issue, Issue)

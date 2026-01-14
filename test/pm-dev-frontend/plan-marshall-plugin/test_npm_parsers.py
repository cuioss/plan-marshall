#!/usr/bin/env python3
"""Tests for npm log parsers (internal module testing).

Note: These tests import internal modules directly for detailed testing.
Public API tests should use npm.py CLI instead.
"""

import sys
import tempfile
from pathlib import Path

from _build_parse import SEVERITY_ERROR, SEVERITY_WARNING, Issue, UnitTestSummary
from _npm_parse_errors import parse_log as parse_errors
from _npm_parse_eslint import parse_log as parse_eslint
from _npm_parse_jest import parse_log as parse_jest
from _npm_parse_tap import parse_log as parse_tap

# Modules under test (PYTHONPATH set by conftest)
from _npm_parse_typescript import parse_log as parse_typescript

# Test data location (fixtures in test directory)
TEST_DATA_DIR = Path(__file__).parent / 'fixtures' / 'log-test-data'


# =============================================================================
# TypeScript Parser Tests
# =============================================================================


def test_typescript_parse_log_returns_tuple():
    """parse_log returns tuple of (issues, test_summary, build_status)."""
    log_file = TEST_DATA_DIR / 'npm-typescript-error-real.log'
    result = parse_typescript(log_file)

    assert isinstance(result, tuple)
    assert len(result) == 3


def test_typescript_parse_log_extracts_errors():
    """TypeScript errors are extracted with correct fields."""
    log_file = TEST_DATA_DIR / 'npm-typescript-error-real.log'
    issues, test_summary, build_status = parse_typescript(log_file)

    assert len(issues) >= 1
    assert build_status == 'FAILURE'
    assert test_summary is None

    error = issues[0]
    assert isinstance(error, Issue)
    assert error.file is not None
    assert error.line is not None
    assert error.severity == SEVERITY_ERROR
    assert error.category == 'typescript_error'


def test_typescript_no_test_summary():
    """TypeScript parser returns None for test_summary."""
    log_file = TEST_DATA_DIR / 'npm-typescript-error-real.log'
    issues, test_summary, build_status = parse_typescript(log_file)

    assert test_summary is None


def test_typescript_success_on_empty():
    """Empty log returns SUCCESS status."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
        f.write('> tsc --build\n\nBuild succeeded.\n')
        f.flush()

        issues, test_summary, build_status = parse_typescript(f.name)

        assert build_status == 'SUCCESS'
        assert len(issues) == 0

        Path(f.name).unlink()


# =============================================================================
# Jest Parser Tests
# =============================================================================


def test_jest_parse_log_returns_tuple():
    """parse_log returns tuple of (issues, test_summary, build_status)."""
    log_file = TEST_DATA_DIR / 'npm-jest-test-failure.log'
    result = parse_jest(log_file)

    assert isinstance(result, tuple)
    assert len(result) == 3


def test_jest_parse_log_failure_status():
    """Jest failures return FAILURE status."""
    log_file = TEST_DATA_DIR / 'npm-jest-test-failure.log'
    issues, test_summary, build_status = parse_jest(log_file)

    assert build_status == 'FAILURE'


def test_jest_extracts_test_summary():
    """Jest parser extracts test summary counts."""
    log_file = TEST_DATA_DIR / 'npm-jest-test-failure.log'
    issues, test_summary, build_status = parse_jest(log_file)

    assert isinstance(test_summary, UnitTestSummary)
    assert test_summary.total > 0


def test_jest_extracts_failures():
    """Jest parser extracts test failures as issues."""
    log_file = TEST_DATA_DIR / 'npm-jest-test-failure.log'
    issues, test_summary, build_status = parse_jest(log_file)

    failures = [i for i in issues if i.category == 'test_failure']
    assert len(failures) >= 1


# =============================================================================
# TAP Parser Tests
# =============================================================================


def test_tap_parse_log_success():
    """TAP success log returns SUCCESS status."""
    log_file = TEST_DATA_DIR / 'npm-tap-test-real.log'
    issues, test_summary, build_status = parse_tap(log_file)

    assert build_status == 'SUCCESS'
    assert len(issues) == 0


def test_tap_parse_log_failure():
    """TAP failure log returns FAILURE status."""
    log_file = TEST_DATA_DIR / 'npm-tap-test-failure-real.log'
    issues, test_summary, build_status = parse_tap(log_file)

    assert build_status == 'FAILURE'


def test_tap_extracts_test_summary_success():
    """TAP parser extracts test summary from success log."""
    log_file = TEST_DATA_DIR / 'npm-tap-test-real.log'
    issues, test_summary, build_status = parse_tap(log_file)

    assert isinstance(test_summary, UnitTestSummary)
    assert test_summary.total == 5
    assert test_summary.passed == 5
    assert test_summary.failed == 0


def test_tap_extracts_test_summary_failure():
    """TAP parser extracts test summary from failure log."""
    log_file = TEST_DATA_DIR / 'npm-tap-test-failure-real.log'
    issues, test_summary, build_status = parse_tap(log_file)

    assert isinstance(test_summary, UnitTestSummary)
    assert test_summary.total == 3
    assert test_summary.passed == 1
    assert test_summary.failed == 2


def test_tap_extracts_failures():
    """TAP parser extracts test failures with location info."""
    log_file = TEST_DATA_DIR / 'npm-tap-test-failure-real.log'
    issues, test_summary, build_status = parse_tap(log_file)

    assert len(issues) >= 1
    # Check that at least one issue has location extracted
    issues_with_file = [i for i in issues if i.file is not None]
    assert len(issues_with_file) >= 1


# =============================================================================
# ESLint Parser Tests
# =============================================================================


def test_eslint_parse_log_returns_tuple():
    """parse_log returns tuple of (issues, test_summary, build_status)."""
    log_file = TEST_DATA_DIR / 'npm-eslint-errors.log'
    result = parse_eslint(log_file)

    assert isinstance(result, tuple)
    assert len(result) == 3


def test_eslint_extracts_errors():
    """ESLint parser extracts errors from output."""
    log_file = TEST_DATA_DIR / 'npm-eslint-errors.log'
    issues, test_summary, build_status = parse_eslint(log_file)

    errors = [i for i in issues if i.severity == SEVERITY_ERROR]
    assert len(errors) >= 1
    assert build_status == 'FAILURE'


def test_eslint_extracts_warnings():
    """ESLint parser extracts warnings from output."""
    log_file = TEST_DATA_DIR / 'npm-eslint-errors.log'
    issues, test_summary, build_status = parse_eslint(log_file)

    warnings = [i for i in issues if i.severity == SEVERITY_WARNING]
    assert len(warnings) >= 1


def test_eslint_issue_fields():
    """ESLint issues have correct fields populated."""
    log_file = TEST_DATA_DIR / 'npm-eslint-errors.log'
    issues, test_summary, build_status = parse_eslint(log_file)

    assert len(issues) >= 1
    issue = issues[0]
    assert isinstance(issue, Issue)
    assert issue.file is not None
    assert issue.line is not None
    assert issue.category == 'eslint'
    assert issue.message is not None


def test_eslint_no_test_summary():
    """ESLint parser returns None for test_summary."""
    log_file = TEST_DATA_DIR / 'npm-eslint-errors.log'
    issues, test_summary, build_status = parse_eslint(log_file)

    assert test_summary is None


# =============================================================================
# npm Error Parser Tests
# =============================================================================


def test_npm_errors_eresolve():
    """npm error parser extracts ERESOLVE errors."""
    log_file = TEST_DATA_DIR / 'npm-dependency-error.log'
    issues, test_summary, build_status = parse_errors(log_file)

    assert build_status == 'FAILURE'
    assert len(issues) >= 1
    assert 'ERESOLVE' in issues[0].message
    assert issues[0].category == 'npm_dependency'


def test_npm_errors_e404():
    """npm error parser extracts E404 errors."""
    log_file = TEST_DATA_DIR / 'npm-404-error.log'
    issues, test_summary, build_status = parse_errors(log_file)

    assert build_status == 'FAILURE'
    assert len(issues) >= 1
    assert 'E404' in issues[0].message
    assert issues[0].category == 'npm_error'


def test_npm_errors_no_test_summary():
    """npm error parser returns None for test_summary."""
    log_file = TEST_DATA_DIR / 'npm-dependency-error.log'
    issues, test_summary, build_status = parse_errors(log_file)

    assert test_summary is None


def test_npm_errors_success_on_empty():
    """Empty log returns SUCCESS status."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
        f.write('> npm install\nadded 150 packages in 10s\n')
        f.flush()

        issues, test_summary, build_status = parse_errors(f.name)

        assert build_status == 'SUCCESS'
        assert len(issues) == 0

        Path(f.name).unlink()


# =============================================================================
# Issue Object Tests
# =============================================================================


def test_issue_to_dict():
    """Issue.to_dict() returns proper dict structure."""
    log_file = TEST_DATA_DIR / 'npm-eslint-errors.log'
    issues, test_summary, build_status = parse_eslint(log_file)

    if issues:
        issue = issues[0]
        d = issue.to_dict()

        assert 'file' in d
        assert 'line' in d
        assert 'message' in d
        assert 'severity' in d


def test_test_summary_to_dict():
    """UnitTestSummary.to_dict() returns proper dict structure."""
    log_file = TEST_DATA_DIR / 'npm-tap-test-real.log'
    issues, test_summary, build_status = parse_tap(log_file)

    assert test_summary is not None
    d = test_summary.to_dict()

    assert d['passed'] == 5
    assert d['failed'] == 0
    assert d['skipped'] == 0
    assert d['total'] == 5


# =============================================================================
# Edge Cases
# =============================================================================


def test_parse_log_file_not_found():
    """Raises FileNotFoundError for missing log file."""
    try:
        parse_typescript('/nonexistent/path/to/log.log')
        assert False, 'Should have raised FileNotFoundError'
    except FileNotFoundError:
        pass  # Expected


if __name__ == '__main__':
    import traceback

    tests = [
        # TypeScript tests
        test_typescript_parse_log_returns_tuple,
        test_typescript_parse_log_extracts_errors,
        test_typescript_no_test_summary,
        test_typescript_success_on_empty,
        # Jest tests
        test_jest_parse_log_returns_tuple,
        test_jest_parse_log_failure_status,
        test_jest_extracts_test_summary,
        test_jest_extracts_failures,
        # TAP tests
        test_tap_parse_log_success,
        test_tap_parse_log_failure,
        test_tap_extracts_test_summary_success,
        test_tap_extracts_test_summary_failure,
        test_tap_extracts_failures,
        # ESLint tests
        test_eslint_parse_log_returns_tuple,
        test_eslint_extracts_errors,
        test_eslint_extracts_warnings,
        test_eslint_issue_fields,
        test_eslint_no_test_summary,
        # npm error tests
        test_npm_errors_eresolve,
        test_npm_errors_e404,
        test_npm_errors_no_test_summary,
        test_npm_errors_success_on_empty,
        # Object tests
        test_issue_to_dict,
        test_test_summary_to_dict,
        # Edge cases
        test_parse_log_file_not_found,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception:
            failed += 1
            print(f'FAILED: {test.__name__}')
            traceback.print_exc()
            print()

    print(f'\nResults: {passed} passed, {failed} failed')
    sys.exit(0 if failed == 0 else 1)

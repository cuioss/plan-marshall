#!/usr/bin/env python3
"""Tests for npm log parsers (internal module testing).

Note: These tests import internal modules directly for detailed testing.
Public API tests should use npm.py CLI instead.
"""

# Tier 2 direct imports via importlib for uniform import style
import importlib.util  # noqa: E402
import tempfile
from pathlib import Path

# Cross-skill imports (PYTHONPATH set by conftest)
from _build_parse import SEVERITY_ERROR, SEVERITY_WARNING, Issue, UnitTestSummary

_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'build-npm'
    / 'scripts'
)


def _load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_npm_parse_errors_mod = _load_module('_npm_parse_errors', '_npm_parse_errors.py')
_npm_parse_eslint_mod = _load_module('_npm_parse_eslint', '_npm_parse_eslint.py')
_npm_parse_jest_mod = _load_module('_npm_parse_jest', '_npm_parse_jest.py')
_npm_parse_tap_mod = _load_module('_npm_parse_tap', '_npm_parse_tap.py')
_npm_parse_typescript_mod = _load_module('_npm_parse_typescript', '_npm_parse_typescript.py')

parse_errors = _npm_parse_errors_mod.parse_log
parse_eslint = _npm_parse_eslint_mod.parse_log
parse_jest = _npm_parse_jest_mod.parse_log
parse_tap = _npm_parse_tap_mod.parse_log
parse_typescript = _npm_parse_typescript_mod.parse_log

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
    assert error.category == 'compilation_error'


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
    assert issue.category == 'lint_error'
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
    import pytest

    with pytest.raises(FileNotFoundError):
        parse_typescript('/nonexistent/path/to/log.log')


def test_mixed_typescript_and_jest_output():
    """Test parsing log with both TypeScript errors and Jest failures (H51).

    Verifies that when multiple tool outputs are in a single log,
    at least one parser detects the issues.
    """
    content = """
src/components/App.tsx(15,3): error TS2339: Property 'x' does not exist on type 'Props'.
src/utils/helper.ts(42,10): error TS2345: Argument of type 'string' is not assignable.

FAIL src/components/__tests__/App.test.tsx
  ● App component › should render correctly

    expect(received).toBe(expected)

    Expected: true
    Received: false

      at Object.<anonymous> (src/components/__tests__/App.test.tsx:25:10)

Tests:       1 failed, 5 passed, 6 total
Test Suites: 1 failed, 2 passed, 3 total
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
        f.write(content)
        f.flush()

        # TypeScript parser should detect TS errors
        ts_issues, _, ts_status = parse_typescript(f.name)
        assert len(ts_issues) >= 2, 'TypeScript parser should find TS errors'
        assert ts_status == 'FAILURE'

        # Jest parser should detect test failures
        jest_issues, jest_summary, jest_status = parse_jest(f.name)
        assert jest_status == 'FAILURE'
        assert jest_summary is not None
        assert jest_summary.failed >= 1

        Path(f.name).unlink()

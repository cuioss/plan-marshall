#!/usr/bin/env python3
"""Tests for maven parse functionality (internal module testing).

Note: These tests import internal modules directly for detailed testing.
Public API tests should use maven.py CLI instead.
"""

# Direct imports - conftest sets up PYTHONPATH (cross-skill)
# Tier 2 direct imports via importlib for uniform import style
import importlib.util
from pathlib import Path

from _build_parse import SEVERITY_ERROR, SEVERITY_WARNING, Issue, UnitTestSummary

_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'build-maven'
    / 'scripts'
)


def _load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_maven_cmd_parse_mod = _load_module('_maven_cmd_parse', '_maven_cmd_parse.py')

parse_log = _maven_cmd_parse_mod.parse_log

# Test data location (fixtures in test directory)
TEST_DATA_DIR = Path(__file__).parent / 'fixtures' / 'log-test-data'


# =============================================================================
# Success Log Tests
# =============================================================================


def test_parse_log_success_returns_tuple():
    """parse_log returns tuple of (issues, test_summary, build_status)."""
    log_file = TEST_DATA_DIR / 'maven-success-real.log'
    result = parse_log(log_file)

    assert isinstance(result, tuple)
    assert len(result) == 3


def test_parse_log_success_build_status():
    """Successful build returns SUCCESS status."""
    log_file = TEST_DATA_DIR / 'maven-success-real.log'
    issues, test_summary, build_status = parse_log(log_file)

    assert build_status == 'SUCCESS'


def test_parse_log_success_test_summary():
    """Successful build returns UnitTestSummary with correct counts."""
    log_file = TEST_DATA_DIR / 'maven-success-real.log'
    issues, test_summary, build_status = parse_log(log_file)

    assert isinstance(test_summary, UnitTestSummary)
    assert test_summary.total == 4892
    assert test_summary.passed == 4892
    assert test_summary.failed == 0
    assert test_summary.skipped == 0


def test_parse_log_success_issues_are_issue_objects():
    """Issues in result are Issue dataclass instances."""
    log_file = TEST_DATA_DIR / 'maven-success-real.log'
    issues, test_summary, build_status = parse_log(log_file)

    # All issues should be Issue instances
    for issue in issues:
        assert isinstance(issue, Issue)


def test_parse_log_success_no_errors():
    """Successful build has no ERROR severity issues."""
    log_file = TEST_DATA_DIR / 'maven-success-real.log'
    issues, test_summary, build_status = parse_log(log_file)

    errors = [i for i in issues if i.severity == SEVERITY_ERROR]
    assert len(errors) == 0


# =============================================================================
# Failure Log Tests
# =============================================================================


def test_parse_log_failure_build_status():
    """Failed build returns FAILURE status."""
    log_file = TEST_DATA_DIR / 'maven-failure-real.log'
    issues, test_summary, build_status = parse_log(log_file)

    assert build_status == 'FAILURE'


def test_parse_log_failure_has_errors():
    """Failed build returns errors in issues list."""
    log_file = TEST_DATA_DIR / 'maven-failure-real.log'
    issues, test_summary, build_status = parse_log(log_file)

    errors = [i for i in issues if i.severity == SEVERITY_ERROR]
    assert len(errors) > 0


def test_parse_log_failure_error_fields():
    """Error issues have correct fields populated."""
    log_file = TEST_DATA_DIR / 'maven-failure-real.log'
    issues, test_summary, build_status = parse_log(log_file)

    errors = [i for i in issues if i.severity == SEVERITY_ERROR]

    # Find the "cannot find symbol" error
    symbol_errors = [e for e in errors if 'cannot find symbol' in e.message]
    assert len(symbol_errors) >= 1

    error = symbol_errors[0]
    assert error.file is not None
    assert error.file.endswith('.java')
    assert error.line is not None
    assert error.category == 'compilation_error'


def test_parse_log_failure_has_warnings():
    """Failed build includes warnings in issues list."""
    log_file = TEST_DATA_DIR / 'maven-failure-real.log'
    issues, test_summary, build_status = parse_log(log_file)

    warnings = [i for i in issues if i.severity == SEVERITY_WARNING]
    assert len(warnings) >= 1


def test_parse_log_failure_warning_category():
    """Warnings have correct category assigned."""
    log_file = TEST_DATA_DIR / 'maven-failure-real.log'
    issues, test_summary, build_status = parse_log(log_file)

    warnings = [i for i in issues if i.severity == SEVERITY_WARNING]

    # Should have deprecation warning
    deprecation = [w for w in warnings if 'deprecation' in w.category]
    assert len(deprecation) >= 1


def test_parse_log_failure_test_summary():
    """Failed build returns UnitTestSummary with failures."""
    log_file = TEST_DATA_DIR / 'maven-failure-real.log'
    issues, test_summary, build_status = parse_log(log_file)

    assert isinstance(test_summary, UnitTestSummary)
    assert test_summary.total == 51
    assert test_summary.failed == 2  # Maven: Failures(2) + Errors(0)
    assert test_summary.skipped == 0
    assert test_summary.passed == 49  # 51 - 2 - 0


# =============================================================================
# Issue Object Tests
# =============================================================================


def test_issue_to_dict():
    """Issue.to_dict() returns proper dict structure."""
    log_file = TEST_DATA_DIR / 'maven-failure-real.log'
    issues, test_summary, build_status = parse_log(log_file)

    if issues:
        issue = issues[0]
        d = issue.to_dict()

        assert 'file' in d
        assert 'line' in d
        assert 'message' in d
        assert 'severity' in d


def test_test_summary_to_dict():
    """UnitTestSummary.to_dict() returns proper dict structure."""
    log_file = TEST_DATA_DIR / 'maven-success-real.log'
    issues, test_summary, build_status = parse_log(log_file)

    d = test_summary.to_dict()

    assert d['passed'] == 4892
    assert d['failed'] == 0
    assert d['skipped'] == 0
    assert d['total'] == 4892


# =============================================================================
# Edge Cases
# =============================================================================


def test_parse_log_file_not_found():
    """Raises FileNotFoundError for missing log file."""
    import pytest

    with pytest.raises(FileNotFoundError):
        parse_log('/nonexistent/path/to/log.log')


def test_parse_log_no_tests():
    """Handles log without test summary gracefully."""
    # Create a minimal log without tests
    import tempfile

    content = """[INFO] Scanning for projects...
[INFO] BUILD SUCCESS
[INFO] Total time: 1.234 s
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
        f.write(content)
        f.flush()

        issues, test_summary, build_status = parse_log(f.name)

        assert build_status == 'SUCCESS'
        assert test_summary is None

        Path(f.name).unlink()

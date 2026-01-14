#!/usr/bin/env python3
"""Tests for gradle parse functionality (internal module testing).

Note: These tests import internal modules directly for detailed testing.
Public API tests should use gradle.py CLI instead.
"""

import sys
from pathlib import Path

# Import shared infrastructure (sets up PYTHONPATH for cross-skill imports)
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Direct imports - conftest sets up PYTHONPATH
from _build_parse import SEVERITY_ERROR, SEVERITY_WARNING, Issue, UnitTestSummary
from _gradle_cmd_parse import parse_log

# Test data location (fixtures in test directory)
TEST_DATA_DIR = Path(__file__).parent / "fixtures" / "log-test-data"


# =============================================================================
# Success Log Tests
# =============================================================================

def test_parse_log_success_returns_tuple():
    """parse_log returns tuple of (issues, test_summary, build_status)."""
    log_file = TEST_DATA_DIR / "gradle-success-real.log"
    result = parse_log(log_file)

    assert isinstance(result, tuple)
    assert len(result) == 3


def test_parse_log_success_build_status():
    """Successful build returns SUCCESS status."""
    log_file = TEST_DATA_DIR / "gradle-success-real.log"
    issues, test_summary, build_status = parse_log(log_file)

    assert build_status == "SUCCESS"


def test_parse_log_success_no_errors():
    """Successful build has no ERROR severity issues."""
    log_file = TEST_DATA_DIR / "gradle-success-real.log"
    issues, test_summary, build_status = parse_log(log_file)

    errors = [i for i in issues if i.severity == SEVERITY_ERROR]
    assert len(errors) == 0


def test_parse_log_success_issues_are_issue_objects():
    """Issues in result are Issue dataclass instances."""
    log_file = TEST_DATA_DIR / "gradle-success-real.log"
    issues, test_summary, build_status = parse_log(log_file)

    for issue in issues:
        assert isinstance(issue, Issue)


# =============================================================================
# Failure Log Tests (Compilation)
# =============================================================================

def test_parse_log_failure_build_status():
    """Failed build returns FAILURE status."""
    log_file = TEST_DATA_DIR / "gradle-failure-real.log"
    issues, test_summary, build_status = parse_log(log_file)

    assert build_status == "FAILURE"


def test_parse_log_failure_has_errors():
    """Failed build returns errors in issues list."""
    log_file = TEST_DATA_DIR / "gradle-failure-real.log"
    issues, test_summary, build_status = parse_log(log_file)

    errors = [i for i in issues if i.severity == SEVERITY_ERROR]
    assert len(errors) > 0


def test_parse_log_failure_error_fields():
    """Error issues have correct fields populated."""
    log_file = TEST_DATA_DIR / "gradle-failure-real.log"
    issues, test_summary, build_status = parse_log(log_file)

    errors = [i for i in issues if i.severity == SEVERITY_ERROR]

    # Find the "cannot find symbol" error
    symbol_errors = [e for e in errors if "cannot find symbol" in e.message]
    assert len(symbol_errors) >= 1

    error = symbol_errors[0]
    assert error.file is not None
    assert error.file.endswith(".java")
    assert error.line is not None
    assert error.category == "compilation_error"


def test_parse_log_failure_has_warnings():
    """Failed build includes warnings in issues list."""
    log_file = TEST_DATA_DIR / "gradle-failure-real.log"
    issues, test_summary, build_status = parse_log(log_file)

    warnings = [i for i in issues if i.severity == SEVERITY_WARNING]
    assert len(warnings) >= 1


def test_parse_log_failure_warning_category():
    """Warnings have correct category assigned."""
    log_file = TEST_DATA_DIR / "gradle-failure-real.log"
    issues, test_summary, build_status = parse_log(log_file)

    warnings = [i for i in issues if i.severity == SEVERITY_WARNING]

    # Should have deprecation warning
    deprecation = [w for w in warnings if w.category == "deprecation_warning"]
    assert len(deprecation) >= 1


# =============================================================================
# Test Failure Log Tests
# =============================================================================

def test_parse_log_test_failure_build_status():
    """Test failure build returns FAILURE status."""
    log_file = TEST_DATA_DIR / "gradle-test-failure-real.log"
    issues, test_summary, build_status = parse_log(log_file)

    assert build_status == "FAILURE"


def test_parse_log_test_failure_test_summary():
    """Test failure build returns UnitTestSummary with failures."""
    log_file = TEST_DATA_DIR / "gradle-test-failure-real.log"
    issues, test_summary, build_status = parse_log(log_file)

    assert isinstance(test_summary, UnitTestSummary)
    assert test_summary.total == 5
    assert test_summary.failed == 2
    assert test_summary.passed == 3  # 5 - 2 - 0
    assert test_summary.skipped == 0


# =============================================================================
# Issue Object Tests
# =============================================================================

def test_issue_to_dict():
    """Issue.to_dict() returns proper dict structure."""
    log_file = TEST_DATA_DIR / "gradle-failure-real.log"
    issues, test_summary, build_status = parse_log(log_file)

    if issues:
        issue = issues[0]
        d = issue.to_dict()

        assert "file" in d
        assert "line" in d
        assert "message" in d
        assert "severity" in d


def test_test_summary_to_dict():
    """UnitTestSummary.to_dict() returns proper dict structure."""
    log_file = TEST_DATA_DIR / "gradle-test-failure-real.log"
    issues, test_summary, build_status = parse_log(log_file)

    assert test_summary is not None
    d = test_summary.to_dict()

    assert d["passed"] == 3
    assert d["failed"] == 2
    assert d["skipped"] == 0
    assert d["total"] == 5


# =============================================================================
# Edge Cases
# =============================================================================

def test_parse_log_file_not_found():
    """Raises FileNotFoundError for missing log file."""
    try:
        parse_log("/nonexistent/path/to/log.log")
        assert False, "Should have raised FileNotFoundError"
    except FileNotFoundError:
        pass  # Expected


def test_parse_log_no_tests():
    """Handles log without test summary gracefully."""
    import tempfile

    content = """> Task :compileJava
BUILD SUCCESSFUL in 5s
3 actionable tasks: 3 executed
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
        f.write(content)
        f.flush()

        issues, test_summary, build_status = parse_log(f.name)

        assert build_status == "SUCCESS"
        assert test_summary is None

        Path(f.name).unlink()


def test_parse_log_deduplicates_issues():
    """Issues are deduplicated."""
    import tempfile

    # Same error appearing multiple times
    content = """/path/to/File.java:10: error: cannot find symbol
/path/to/File.java:10: error: cannot find symbol
/path/to/File.java:10: error: cannot find symbol
BUILD SUCCESSFUL in 1s
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
        f.write(content)
        f.flush()

        issues, test_summary, build_status = parse_log(f.name)

        # Should only have 1 compilation_error issue, not 3
        compilation_errors = [i for i in issues if i.category == "compilation_error"]
        assert len(compilation_errors) == 1

        Path(f.name).unlink()


if __name__ == "__main__":
    import traceback

    tests = [
        test_parse_log_success_returns_tuple,
        test_parse_log_success_build_status,
        test_parse_log_success_no_errors,
        test_parse_log_success_issues_are_issue_objects,
        test_parse_log_failure_build_status,
        test_parse_log_failure_has_errors,
        test_parse_log_failure_error_fields,
        test_parse_log_failure_has_warnings,
        test_parse_log_failure_warning_category,
        test_parse_log_test_failure_build_status,
        test_parse_log_test_failure_test_summary,
        test_issue_to_dict,
        test_test_summary_to_dict,
        test_parse_log_file_not_found,
        test_parse_log_no_tests,
        test_parse_log_deduplicates_issues,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception:
            failed += 1
            print(f"FAILED: {test.__name__}")
            traceback.print_exc()
            print()

    print(f"\nResults: {passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)

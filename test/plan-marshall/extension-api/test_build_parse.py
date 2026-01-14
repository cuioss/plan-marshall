#!/usr/bin/env python3
"""Tests for build_parse.py module."""

import json
import sys
import tempfile
from pathlib import Path

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
# Import modules under test (PYTHONPATH set by conftest)
from _build_parse import (
    MODE_ACTIONABLE,
    MODE_ERRORS,
    MODE_STRUCTURED,
    SEVERITY_ERROR,
    SEVERITY_WARNING,
    Issue,
    UnitTestSummary,
    filter_warnings,
    is_warning_accepted,
    load_acceptable_warnings,
    partition_issues,
)


def test_severity_constants():
    """Severity constants have expected values."""
    assert SEVERITY_ERROR == "error"
    assert SEVERITY_WARNING == "warning"


def test_mode_constants():
    """Mode constants have expected values."""
    assert MODE_ACTIONABLE == "actionable"
    assert MODE_STRUCTURED == "structured"
    assert MODE_ERRORS == "errors"


def test_issue_creation_minimal():
    """Issue can be created with minimal fields."""
    issue = Issue(
        file="Main.java",
        line=15,
        message="cannot find symbol",
        severity=SEVERITY_ERROR
    )
    assert issue.file == "Main.java"
    assert issue.line == 15
    assert issue.message == "cannot find symbol"
    assert issue.severity == SEVERITY_ERROR
    assert issue.category is None
    assert issue.stack_trace is None
    assert issue.accepted is False


def test_issue_creation_full():
    """Issue can be created with all fields."""
    issue = Issue(
        file="Test.java",
        line=42,
        message="test failed",
        severity=SEVERITY_ERROR,
        category="test_failure",
        stack_trace="at Test.method(Test.java:42)",
        accepted=True
    )
    assert issue.category == "test_failure"
    assert issue.stack_trace == "at Test.method(Test.java:42)"
    assert issue.accepted is True


def test_issue_none_file_and_line():
    """Issue can have None file and line."""
    issue = Issue(
        file=None,
        line=None,
        message="general warning",
        severity=SEVERITY_WARNING
    )
    assert issue.file is None
    assert issue.line is None


def test_issue_to_dict_minimal():
    """to_dict returns minimal required fields."""
    issue = Issue(
        file="Main.java",
        line=15,
        message="error",
        severity=SEVERITY_ERROR
    )
    result = issue.to_dict()

    assert result["file"] == "Main.java"
    assert result["line"] == 15
    assert result["message"] == "error"
    assert result["severity"] == SEVERITY_ERROR
    assert "category" not in result
    assert "stack_trace" not in result
    assert "accepted" not in result


def test_issue_to_dict_with_category():
    """to_dict includes category when present."""
    issue = Issue(
        file="Main.java",
        line=15,
        message="error",
        severity=SEVERITY_ERROR,
        category="compilation"
    )
    result = issue.to_dict()
    assert result["category"] == "compilation"


def test_issue_to_dict_with_stack_trace():
    """to_dict includes stack_trace when present."""
    issue = Issue(
        file="Test.java",
        line=42,
        message="test failed",
        severity=SEVERITY_ERROR,
        stack_trace="stack trace here"
    )
    result = issue.to_dict()
    assert result["stack_trace"] == "stack trace here"


def test_issue_to_dict_with_accepted():
    """to_dict includes accepted when True."""
    issue = Issue(
        file="Main.java",
        line=15,
        message="warning",
        severity=SEVERITY_WARNING,
        accepted=True
    )
    result = issue.to_dict()
    assert result["accepted"] is True


def test_issue_to_dict_without_accepted_false():
    """to_dict excludes accepted when False."""
    issue = Issue(
        file="Main.java",
        line=15,
        message="warning",
        severity=SEVERITY_WARNING,
        accepted=False
    )
    result = issue.to_dict()
    assert "accepted" not in result


def test_test_summary_creation():
    """UnitTestSummary can be created with all fields."""
    summary = UnitTestSummary(passed=10, failed=2, skipped=1, total=13)
    assert summary.passed == 10
    assert summary.failed == 2
    assert summary.skipped == 1
    assert summary.total == 13


def test_test_summary_to_dict():
    """to_dict returns all fields."""
    summary = UnitTestSummary(passed=10, failed=2, skipped=1, total=13)
    result = summary.to_dict()

    assert result["passed"] == 10
    assert result["failed"] == 2
    assert result["skipped"] == 1
    assert result["total"] == 13


def test_test_summary_zero_values():
    """UnitTestSummary handles zero values."""
    summary = UnitTestSummary(passed=0, failed=0, skipped=0, total=0)
    result = summary.to_dict()
    assert all(v == 0 for v in result.values())


def test_load_acceptable_warnings_nonexistent():
    """Returns empty list when config doesn't exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = load_acceptable_warnings(tmpdir, "maven")
        assert result == []


def test_load_acceptable_warnings_missing_build_system():
    """Returns empty list when build system not in config."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir) / ".plan"
        config_dir.mkdir()
        config = {"npm": {"acceptable_warnings": ["pattern"]}}
        (config_dir / "run-configuration.json").write_text(json.dumps(config))

        result = load_acceptable_warnings(tmpdir, "maven")
        assert result == []


def test_load_acceptable_warnings_missing_key():
    """Returns empty list when acceptable_warnings not in build system config."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir) / ".plan"
        config_dir.mkdir()
        config = {"maven": {"other_key": "value"}}
        (config_dir / "run-configuration.json").write_text(json.dumps(config))

        result = load_acceptable_warnings(tmpdir, "maven")
        assert result == []


def test_load_acceptable_warnings_loads():
    """Loads patterns from config."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir) / ".plan"
        config_dir.mkdir()
        config = {
            "maven": {
                "acceptable_warnings": [
                    "unchecked",
                    "deprecated",
                    "^.*raw type.*$"
                ]
            }
        }
        (config_dir / "run-configuration.json").write_text(json.dumps(config))

        result = load_acceptable_warnings(tmpdir, "maven")
        assert len(result) == 3
        assert "unchecked" in result
        assert "deprecated" in result


def test_load_acceptable_warnings_invalid_json():
    """Returns empty list for invalid JSON."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir) / ".plan"
        config_dir.mkdir()
        (config_dir / "run-configuration.json").write_text("not valid json")

        result = load_acceptable_warnings(tmpdir, "maven")
        assert result == []


def test_is_warning_accepted_empty_patterns():
    """Returns False with empty patterns."""
    warning = Issue(None, None, "some warning", SEVERITY_WARNING)
    assert not is_warning_accepted(warning, [])


def test_is_warning_accepted_substring():
    """Matches substring pattern."""
    warning = Issue(None, None, "uses unchecked or unsafe operations", SEVERITY_WARNING)
    assert is_warning_accepted(warning, ["unchecked"])


def test_is_warning_accepted_substring_case_insensitive():
    """Substring matching is case-insensitive."""
    warning = Issue(None, None, "Uses UNCHECKED operations", SEVERITY_WARNING)
    assert is_warning_accepted(warning, ["unchecked"])


def test_is_warning_accepted_substring_no_match():
    """Returns False when substring doesn't match."""
    warning = Issue(None, None, "some warning", SEVERITY_WARNING)
    assert not is_warning_accepted(warning, ["unchecked"])


def test_is_warning_accepted_regex():
    """Matches regex pattern starting with ^."""
    warning = Issue(None, None, "raw type usage in Main.java", SEVERITY_WARNING)
    assert is_warning_accepted(warning, ["^.*raw type.*$"])


def test_is_warning_accepted_regex_case_insensitive():
    """Regex matching is case-insensitive."""
    warning = Issue(None, None, "RAW TYPE usage", SEVERITY_WARNING)
    assert is_warning_accepted(warning, ["^.*raw type.*$"])


def test_is_warning_accepted_regex_no_match():
    """Returns False when regex doesn't match."""
    warning = Issue(None, None, "some warning", SEVERITY_WARNING)
    assert not is_warning_accepted(warning, ["^.*unchecked.*$"])


def test_is_warning_accepted_invalid_regex():
    """Skips invalid regex patterns."""
    warning = Issue(None, None, "some warning", SEVERITY_WARNING)
    assert not is_warning_accepted(warning, ["^(invalid"])


def test_is_warning_accepted_multiple_patterns():
    """Returns True if any pattern matches."""
    warning = Issue(None, None, "deprecated API", SEVERITY_WARNING)
    patterns = ["unchecked", "deprecated", "raw type"]
    assert is_warning_accepted(warning, patterns)


def test_filter_warnings_actionable():
    """Actionable mode filters out accepted warnings."""
    warnings = [
        Issue(None, None, "unchecked operation", SEVERITY_WARNING),
        Issue(None, None, "other warning", SEVERITY_WARNING),
    ]
    patterns = ["unchecked"]

    result = filter_warnings(warnings, patterns, MODE_ACTIONABLE)
    assert len(result) == 1
    assert result[0].message == "other warning"


def test_filter_warnings_default_mode():
    """Actionable is the default mode."""
    warnings = [Issue(None, None, "unchecked", SEVERITY_WARNING)]
    patterns = ["unchecked"]

    result = filter_warnings(warnings, patterns)
    assert len(result) == 0


def test_filter_warnings_structured_keeps_all():
    """Structured mode keeps all warnings."""
    warnings = [
        Issue(None, None, "unchecked operation", SEVERITY_WARNING),
        Issue(None, None, "other warning", SEVERITY_WARNING),
    ]
    patterns = ["unchecked"]

    result = filter_warnings(warnings, patterns, MODE_STRUCTURED)
    assert len(result) == 2


def test_filter_warnings_structured_marks_accepted():
    """Structured mode marks accepted warnings."""
    warnings = [
        Issue(None, None, "unchecked operation", SEVERITY_WARNING),
        Issue(None, None, "other warning", SEVERITY_WARNING),
    ]
    patterns = ["unchecked"]

    result = filter_warnings(warnings, patterns, MODE_STRUCTURED)
    accepted = [w for w in result if w.accepted]
    not_accepted = [w for w in result if not w.accepted]

    assert len(accepted) == 1
    assert accepted[0].message == "unchecked operation"
    assert len(not_accepted) == 1
    assert not_accepted[0].message == "other warning"


def test_filter_warnings_errors_returns_empty():
    """Errors mode returns empty list."""
    warnings = [
        Issue(None, None, "warning 1", SEVERITY_WARNING),
        Issue(None, None, "warning 2", SEVERITY_WARNING),
    ]

    result = filter_warnings(warnings, [], MODE_ERRORS)
    assert result == []


def test_filter_warnings_preserves_fields():
    """Structured mode preserves all Issue fields."""
    warning = Issue(
        file="Main.java",
        line=15,
        message="unchecked",
        severity=SEVERITY_WARNING,
        category="type_safety",
        stack_trace="trace"
    )

    result = filter_warnings([warning], ["unchecked"], MODE_STRUCTURED)
    assert len(result) == 1
    assert result[0].file == "Main.java"
    assert result[0].line == 15
    assert result[0].category == "type_safety"
    assert result[0].stack_trace == "trace"


def test_partition_issues_empty():
    """Returns empty lists for empty input."""
    errors, warnings = partition_issues([])
    assert errors == []
    assert warnings == []


def test_partition_issues_errors_only():
    """Correctly partitions errors only."""
    issues = [
        Issue(None, None, "error 1", SEVERITY_ERROR),
        Issue(None, None, "error 2", SEVERITY_ERROR),
    ]
    errors, warnings = partition_issues(issues)
    assert len(errors) == 2
    assert len(warnings) == 0


def test_partition_issues_warnings_only():
    """Correctly partitions warnings only."""
    issues = [
        Issue(None, None, "warning 1", SEVERITY_WARNING),
        Issue(None, None, "warning 2", SEVERITY_WARNING),
    ]
    errors, warnings = partition_issues(issues)
    assert len(errors) == 0
    assert len(warnings) == 2


def test_partition_issues_mixed():
    """Correctly partitions mixed issues."""
    issues = [
        Issue(None, None, "error 1", SEVERITY_ERROR),
        Issue(None, None, "warning 1", SEVERITY_WARNING),
        Issue(None, None, "error 2", SEVERITY_ERROR),
        Issue(None, None, "warning 2", SEVERITY_WARNING),
    ]
    errors, warnings = partition_issues(issues)
    assert len(errors) == 2
    assert len(warnings) == 2
    assert all(e.severity == SEVERITY_ERROR for e in errors)
    assert all(w.severity == SEVERITY_WARNING for w in warnings)


def test_partition_issues_preserves_order():
    """Preserves order within each partition."""
    issues = [
        Issue(None, None, "error 1", SEVERITY_ERROR),
        Issue(None, None, "error 2", SEVERITY_ERROR),
        Issue(None, None, "warning 1", SEVERITY_WARNING),
    ]
    errors, warnings = partition_issues(issues)
    assert errors[0].message == "error 1"
    assert errors[1].message == "error 2"


if __name__ == "__main__":
    import traceback

    tests = [
        test_severity_constants,
        test_mode_constants,
        test_issue_creation_minimal,
        test_issue_creation_full,
        test_issue_none_file_and_line,
        test_issue_to_dict_minimal,
        test_issue_to_dict_with_category,
        test_issue_to_dict_with_stack_trace,
        test_issue_to_dict_with_accepted,
        test_issue_to_dict_without_accepted_false,
        test_test_summary_creation,
        test_test_summary_to_dict,
        test_test_summary_zero_values,
        test_load_acceptable_warnings_nonexistent,
        test_load_acceptable_warnings_missing_build_system,
        test_load_acceptable_warnings_missing_key,
        test_load_acceptable_warnings_loads,
        test_load_acceptable_warnings_invalid_json,
        test_is_warning_accepted_empty_patterns,
        test_is_warning_accepted_substring,
        test_is_warning_accepted_substring_case_insensitive,
        test_is_warning_accepted_substring_no_match,
        test_is_warning_accepted_regex,
        test_is_warning_accepted_regex_case_insensitive,
        test_is_warning_accepted_regex_no_match,
        test_is_warning_accepted_invalid_regex,
        test_is_warning_accepted_multiple_patterns,
        test_filter_warnings_actionable,
        test_filter_warnings_default_mode,
        test_filter_warnings_structured_keeps_all,
        test_filter_warnings_structured_marks_accepted,
        test_filter_warnings_errors_returns_empty,
        test_filter_warnings_preserves_fields,
        test_partition_issues_empty,
        test_partition_issues_errors_only,
        test_partition_issues_warnings_only,
        test_partition_issues_mixed,
        test_partition_issues_preserves_order,
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

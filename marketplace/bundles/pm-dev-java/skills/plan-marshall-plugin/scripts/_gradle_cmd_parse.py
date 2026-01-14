#!/usr/bin/env python3
"""Parse subcommand for Gradle build output.

Implements BuildParser protocol for unified build log parsing.
Internal module - use gradle.py CLI entry point instead.

Usage (internal):
    from _gradle_cmd_parse import parse_log

    issues, test_summary, build_status = parse_log("path/to/build.log")
"""

import json
import re
from pathlib import Path
from typing import List, Optional, Tuple

# Direct imports - executor sets up PYTHONPATH for cross-skill imports
from _build_parse import Issue, UnitTestSummary, SEVERITY_ERROR, SEVERITY_WARNING
from plan_logging import log_entry


# Pattern definitions for categorizing build output
COMPILATION_PATTERNS = [
    r"error:\s+cannot find symbol", r"error:\s+incompatible types", r"error:\s+illegal start",
    r"error:\s+';' expected", r"error:\s+class .* is public", r"error:\s+package .* does not exist",
    r"error:\s+method .* cannot be applied", r"error:\s+unreported exception",
    r"error:\s+variable .* might not have been initialized", r"error:\s+cannot access",
    r"Execution failed for task ':.*:compileJava'", r"Execution failed for task ':.*:compileKotlin'",
]
TEST_FAILURE_PATTERNS = [r">\s+\d+ tests? completed, \d+ failed", r"FAILED", r"AssertionFailedError", r"AssertionError", r"Execution failed for task ':.*:test'"]
DEPENDENCY_PATTERNS = [r"Could not resolve", r"Could not find", r"Could not download", r"Failed to resolve", r"Cannot resolve external dependency"]
JAVADOC_PATTERNS = [r"warning:\s+no @param", r"warning:\s+no @return", r"warning:\s+missing @", r"javadoc", r"Execution failed for task ':.*:javadoc'"]
DEPRECATION_PATTERNS = [r"\[deprecation\]", r"has been deprecated", r"is deprecated"]
UNCHECKED_PATTERNS = [r"\[unchecked\]", r"unchecked conversion", r"unchecked call"]


def categorize_line(line: str) -> Optional[str]:
    """Categorize a log line by issue type."""
    for pattern in COMPILATION_PATTERNS:
        if re.search(pattern, line, re.IGNORECASE): return "compilation_error"
    for pattern in TEST_FAILURE_PATTERNS:
        if re.search(pattern, line, re.IGNORECASE): return "test_failure"
    for pattern in DEPENDENCY_PATTERNS:
        if re.search(pattern, line, re.IGNORECASE): return "dependency_error"
    for pattern in JAVADOC_PATTERNS:
        if re.search(pattern, line, re.IGNORECASE): return "javadoc_warning"
    for pattern in DEPRECATION_PATTERNS:
        if re.search(pattern, line, re.IGNORECASE): return "deprecation_warning"
    for pattern in UNCHECKED_PATTERNS:
        if re.search(pattern, line, re.IGNORECASE): return "unchecked_warning"
    return None


def extract_file_location(line: str) -> Tuple[str, int, int]:
    """Extract file path, line, and column from error message."""
    match = re.search(r"([^\s:]+\.(java|kt|groovy)):(\d+):?(\d+)?", line)
    if match:
        return match.group(1), int(match.group(3)), int(match.group(4)) if match.group(4) else 0
    return "", 0, 0


def parse_build_status(lines: List[str]) -> str:
    """Determine overall build status from log lines."""
    for line in reversed(lines[-50:]):
        if "BUILD SUCCESSFUL" in line: return "SUCCESS"
        if "BUILD FAILED" in line: return "FAILURE"
    return "UNKNOWN"


def parse_metrics(lines: List[str]) -> dict:
    """Extract build metrics from log."""
    metrics = {"duration_ms": 0, "tasks_executed": 0, "tests_run": 0, "tests_failed": 0}
    for line in lines:
        duration_match = re.search(r"BUILD (?:SUCCESSFUL|FAILED) in (?:(\d+)h\s*)?(?:(\d+)m\s*)?(?:(\d+)s)?", line)
        if duration_match:
            hours, minutes, seconds = int(duration_match.group(1) or 0), int(duration_match.group(2) or 0), int(duration_match.group(3) or 0)
            metrics["duration_ms"] = (hours * 3600 + minutes * 60 + seconds) * 1000
        tasks_match = re.search(r"(\d+) actionable tasks?: (\d+) executed", line)
        if tasks_match: metrics["tasks_executed"] = int(tasks_match.group(2))
        test_match = re.search(r"(\d+) tests? completed(?:, (\d+) failed)?(?:, (\d+) skipped)?", line)
        if test_match:
            metrics["tests_run"] = int(test_match.group(1))
            metrics["tests_failed"] = int(test_match.group(2) or 0)
    return metrics


# =============================================================================
# BuildParser Protocol Implementation
# =============================================================================

def parse_log(log_file: str | Path) -> tuple[list[Issue], UnitTestSummary | None, str]:
    """Parse Gradle build log file.

    Implements BuildParser protocol for unified build log parsing.

    Args:
        log_file: Path to the Gradle build log file.

    Returns:
        Tuple of (issues, test_summary, build_status):
        - issues: list[Issue] - all errors and warnings found
        - test_summary: UnitTestSummary | None - test counts if tests ran
        - build_status: "SUCCESS" | "FAILURE"

    Raises:
        FileNotFoundError: If log file doesn't exist.
    """
    path = Path(log_file)
    content = path.read_text(encoding="utf-8", errors="replace")
    lines = content.split("\n")

    issues = _extract_issues_as_dataclass(lines)
    test_summary = _extract_test_summary_as_dataclass(lines)
    build_status = _detect_build_status(lines)

    return issues, test_summary, build_status


def _detect_build_status(lines: List[str]) -> str:
    """Determine overall build status from log lines.

    Args:
        lines: Log file lines.

    Returns:
        "SUCCESS" or "FAILURE" (never UNKNOWN per contract).
    """
    for line in reversed(lines[-50:]):
        if "BUILD SUCCESSFUL" in line:
            return "SUCCESS"
        if "BUILD FAILED" in line:
            return "FAILURE"
    # If neither found, assume failure (conservative)
    return "FAILURE"


def _extract_issues_as_dataclass(lines: List[str]) -> list[Issue]:
    """Extract all issues from Gradle output as Issue dataclasses.

    Args:
        lines: Log file lines.

    Returns:
        List of Issue dataclasses with severity, file, line, message, category.
        Deduplicates issues by key (type:file:line:message_prefix).
    """
    issues = []
    seen = set()

    for line in lines:
        issue_type = categorize_line(line)
        if not issue_type:
            continue

        file_path, file_line, _ = extract_file_location(line)
        message = line.strip()

        # Deduplication
        dedup_key = f"{issue_type}:{file_path}:{file_line}:{message[:100]}"
        if dedup_key in seen:
            continue
        seen.add(dedup_key)

        # Map type to severity
        severity = SEVERITY_ERROR if "error" in issue_type else SEVERITY_WARNING

        issues.append(Issue(
            file=file_path if file_path else None,
            line=file_line if file_line else None,
            message=message[:500],
            severity=severity,
            category=issue_type,
        ))

    return issues


def _extract_test_summary_as_dataclass(lines: List[str]) -> UnitTestSummary | None:
    """Extract test execution summary as UnitTestSummary dataclass.

    Args:
        lines: Log file lines.

    Returns:
        UnitTestSummary dataclass if tests were run, None otherwise.

    Note:
        Gradle format: "5 tests completed, 2 failed" or "5 tests completed, 2 failed, 1 skipped"
    """
    # Look for test completion line
    pattern = r"(\d+) tests? completed(?:, (\d+) failed)?(?:, (\d+) skipped)?"

    for line in lines:
        match = re.search(pattern, line)
        if match:
            total = int(match.group(1))
            failed = int(match.group(2) or 0)
            skipped = int(match.group(3) or 0)
            passed = total - failed - skipped

            return UnitTestSummary(
                passed=passed,
                failed=failed,
                skipped=skipped,
                total=total,
            )

    return None


def cmd_parse(args):
    """Handle parse subcommand."""
    path = Path(args.log)
    if not path.exists():
        log_entry('script', 'global', 'ERROR', f"[GRADLE-PARSE] Log file not found: {args.log}")
        print(json.dumps({"status": "error", "error": "file_not_found", "message": f"Log file not found: {args.log}"}, indent=2))
        return 1

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    issues, seen = [], set()
    for line_num, line in enumerate(lines, 1):
        issue_type = categorize_line(line)
        if issue_type:
            file_path, file_line, file_col = extract_file_location(line)
            message = line.strip()
            dedup_key = f"{issue_type}:{file_path}:{file_line}:{message[:100]}"
            if dedup_key in seen: continue
            seen.add(dedup_key)
            severity = "ERROR" if "error" in issue_type else "WARNING"
            issues.append({"type": issue_type, "file": file_path, "line": file_line, "column": file_col, "message": message[:500], "severity": severity, "log_line": line_num})

    build_status = parse_build_status(lines)
    metrics = parse_metrics(lines)

    if args.mode == "errors":
        issues = [i for i in issues if i["severity"] == "ERROR"]

    summary = {"compilation_errors": sum(1 for i in issues if i["type"] == "compilation_error"), "test_failures": sum(1 for i in issues if i["type"] == "test_failure"), "javadoc_warnings": sum(1 for i in issues if i["type"] == "javadoc_warning"), "deprecation_warnings": sum(1 for i in issues if i["type"] == "deprecation_warning"), "unchecked_warnings": sum(1 for i in issues if i["type"] == "unchecked_warning"), "dependency_errors": sum(1 for i in issues if i["type"] == "dependency_error"), "total_issues": len(issues)}

    log_entry('script', 'global', 'INFO', f"[GRADLE-PARSE] Parsed log: status={build_status}, issues={len(issues)}, tests_run={metrics['tests_run']}")

    result = {"status": "success", "data": {"build_status": build_status, "issues": issues, "summary": summary}, "metrics": metrics}

    if args.mode == "default":
        output_lines = [f"Build Status: {build_status}", f"Duration: {metrics['duration_ms']}ms", f"Tasks: {metrics['tasks_executed']} executed", f"Tests: {metrics['tests_run']} run, {metrics['tests_failed']} failed", "", "Issues Summary:", f"  Compilation Errors: {summary['compilation_errors']}", f"  Test Failures: {summary['test_failures']}", f"  Javadoc Warnings: {summary['javadoc_warnings']}", f"  Total: {summary['total_issues']}"]
        print("\n".join(output_lines))
        return 0

    print(json.dumps(result, indent=2))
    return 0

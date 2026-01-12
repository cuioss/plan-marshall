#!/usr/bin/env python3
"""Jest test output parser for npm test output.

Implements BuildParser protocol for Jest test results.

Usage:
    from npm_parse_jest import parse_log

    issues, test_summary, build_status = parse_log("path/to/test.log")
"""

import re
from pathlib import Path

# Cross-skill imports (PYTHONPATH set by executor)
from _build_parse import Issue, TestSummary, SEVERITY_ERROR  # type: ignore[import-not-found]


# Jest failure header pattern
FAIL_PATTERN = re.compile(r"^\s*FAIL\s+(.+)$", re.MULTILINE)

# Jest test summary pattern: Tests: N failed, N passed, N total
SUMMARY_PATTERN = re.compile(
    r"Tests:\s+(?:(\d+)\s+failed,\s+)?(?:(\d+)\s+skipped,\s+)?(?:(\d+)\s+passed,\s+)?(\d+)\s+total"
)


def parse_log(log_file: str | Path) -> tuple[list[Issue], TestSummary | None, str]:
    """Parse Jest test log file.

    Implements BuildParser protocol for Jest test results.

    Args:
        log_file: Path to the Jest test log file.

    Returns:
        Tuple of (issues, test_summary, build_status):
        - issues: list[Issue] - all test failures found
        - test_summary: TestSummary with test counts
        - build_status: "SUCCESS" | "FAILURE"

    Raises:
        FileNotFoundError: If log file doesn't exist.
    """
    path = Path(log_file)
    content = path.read_text(encoding="utf-8", errors="replace")

    issues = _extract_issues(content)
    test_summary = _extract_test_summary(content)
    build_status = "FAILURE" if issues else "SUCCESS"

    return issues, test_summary, build_status


def _extract_issues(content: str) -> list[Issue]:
    """Extract Jest test failures from log content.

    Args:
        content: Log file content.

    Returns:
        List of Issue dataclasses with test failures.
    """
    issues = []
    lines = content.split("\n")
    current_file = None
    current_test = None
    collecting_stack = False
    stack_lines = []

    for i, line in enumerate(lines):
        # Check for FAIL marker
        fail_match = FAIL_PATTERN.match(line)
        if fail_match:
            current_file = fail_match.group(1).strip()
            continue

        # Check for test name (● TestSuite › test name)
        if line.strip().startswith("●"):
            # Save previous test if collecting
            if current_test and stack_lines:
                _add_issue(issues, current_file, current_test, stack_lines)
                stack_lines = []

            current_test = line.strip()[1:].strip()  # Remove ● prefix
            collecting_stack = True
            continue

        # Collect stack trace lines
        if collecting_stack:
            stripped = line.strip()
            if stripped and not stripped.startswith("at "):
                stack_lines.append(line)
            elif stripped.startswith("at "):
                stack_lines.append(line)
            elif not stripped:
                # Empty line might end the stack trace
                if stack_lines and any("at " in l for l in stack_lines):
                    _add_issue(issues, current_file, current_test, stack_lines)
                    stack_lines = []
                    collecting_stack = False
                    current_test = None

    # Handle final test if still collecting
    if current_test and stack_lines:
        _add_issue(issues, current_file, current_test, stack_lines)

    return issues


def _add_issue(issues: list, file: str | None, test: str, stack_lines: list[str]) -> None:
    """Add a test failure issue.

    Args:
        issues: List to append to.
        file: Test file path.
        test: Test name.
        stack_lines: Stack trace lines.
    """
    # Extract line number from stack trace
    line_num = None
    for sl in stack_lines:
        match = re.search(r":(\d+):\d+\)?$", sl)
        if match:
            line_num = int(match.group(1))
            break

    stack_trace = "\n".join(stack_lines) if stack_lines else None

    issues.append(Issue(
        file=file,
        line=line_num,
        message=test,
        severity=SEVERITY_ERROR,
        category="test_failure",
        stack_trace=stack_trace,
    ))


def _extract_test_summary(content: str) -> TestSummary | None:
    """Extract Jest test summary from log content.

    Args:
        content: Log file content.

    Returns:
        TestSummary dataclass if found, None otherwise.
    """
    match = SUMMARY_PATTERN.search(content)
    if not match:
        return None

    failed = int(match.group(1) or 0)
    skipped = int(match.group(2) or 0)
    passed = int(match.group(3) or 0)
    total = int(match.group(4))

    return TestSummary(
        passed=passed,
        failed=failed,
        skipped=skipped,
        total=total,
    )

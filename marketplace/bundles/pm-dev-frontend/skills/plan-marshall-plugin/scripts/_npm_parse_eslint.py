#!/usr/bin/env python3
"""ESLint output parser for npm lint output.

Implements BuildParser protocol for ESLint results.

Usage:
    from npm_parse_eslint import parse_log

    issues, test_summary, build_status = parse_log("path/to/lint.log")
"""

import re
from pathlib import Path

# Cross-skill imports (PYTHONPATH set by executor)
from _build_parse import Issue, TestSummary, SEVERITY_ERROR, SEVERITY_WARNING  # type: ignore[import-not-found]


# ESLint issue pattern: "  line:col  severity  message  rule-name"
ESLINT_ISSUE_PATTERN = re.compile(
    r"^\s+(\d+):(\d+)\s+(error|warning)\s+(.+?)\s{2,}(\S+)\s*$"
)

# ESLint summary pattern: "✖ N problems (N errors, N warnings)"
ESLINT_SUMMARY_PATTERN = re.compile(
    r"[✖✗]\s*(\d+)\s+problems?\s+\((\d+)\s+errors?,\s+(\d+)\s+warnings?\)"
)

# File path line pattern (starts with / or drive letter, no leading whitespace)
FILE_PATH_PATTERN = re.compile(r"^(/[^\s:]+|[A-Z]:\\[^\s:]+)$")


def parse_log(log_file: str | Path) -> tuple[list[Issue], TestSummary | None, str]:
    """Parse ESLint log file.

    Implements BuildParser protocol for ESLint results.

    Args:
        log_file: Path to the ESLint log file.

    Returns:
        Tuple of (issues, test_summary, build_status):
        - issues: list[Issue] - all ESLint errors and warnings found
        - test_summary: None (ESLint doesn't run tests)
        - build_status: "SUCCESS" | "FAILURE"

    Raises:
        FileNotFoundError: If log file doesn't exist.
    """
    path = Path(log_file)
    content = path.read_text(encoding="utf-8", errors="replace")

    issues = _extract_issues(content)
    errors = [i for i in issues if i.severity == SEVERITY_ERROR]
    build_status = "FAILURE" if errors else "SUCCESS"

    return issues, None, build_status


def _extract_issues(content: str) -> list[Issue]:
    """Extract ESLint issues from log content.

    Args:
        content: Log file content.

    Returns:
        List of Issue dataclasses with ESLint errors and warnings.
    """
    issues = []
    lines = content.split("\n")
    current_file = None
    seen = set()

    for line in lines:
        # Check if this line is a file path
        file_match = FILE_PATH_PATTERN.match(line)
        if file_match:
            current_file = file_match.group(1)
            continue

        # Check if this line is an issue
        issue_match = ESLINT_ISSUE_PATTERN.match(line)
        if issue_match and current_file:
            line_num = int(issue_match.group(1))
            col = int(issue_match.group(2))
            severity_str = issue_match.group(3)
            message = issue_match.group(4).strip()
            rule = issue_match.group(5)

            # Determine severity
            severity = SEVERITY_ERROR if severity_str == "error" else SEVERITY_WARNING

            # Deduplication key
            dedup_key = f"{current_file}:{line_num}:{col}:{rule}"
            if dedup_key in seen:
                continue
            seen.add(dedup_key)

            issues.append(Issue(
                file=current_file,
                line=line_num,
                message=f"{rule}: {message}",
                severity=severity,
                category="eslint",
            ))

    return issues

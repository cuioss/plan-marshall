#!/usr/bin/env python3
"""TypeScript error parser for npm build output.

Implements BuildParser protocol for TypeScript compilation errors.

Usage:
    from npm_parse_typescript import parse_log

    issues, test_summary, build_status = parse_log("path/to/build.log")
"""

import re
from pathlib import Path

# Cross-skill imports (PYTHONPATH set by executor)
from _build_parse import Issue, TestSummary, SEVERITY_ERROR  # type: ignore[import-not-found]


# TypeScript error pattern: path(line,col): error TSNNNN: message
TS_ERROR_PATTERN = re.compile(
    r"^(.+?)\((\d+),(\d+)\):\s*(error)\s+(TS\d+):\s*(.+)$",
    re.MULTILINE
)

# Alternative pattern: path:line:col - message
TS_ERROR_ALT_PATTERN = re.compile(
    r"^(.+?):(\d+):(\d+)\s*-\s*(error)\s+(TS\d+):\s*(.+)$",
    re.MULTILINE
)


def parse_log(log_file: str | Path) -> tuple[list[Issue], TestSummary | None, str]:
    """Parse TypeScript compilation log file.

    Implements BuildParser protocol for TypeScript errors.

    Args:
        log_file: Path to the TypeScript build log file.

    Returns:
        Tuple of (issues, test_summary, build_status):
        - issues: list[Issue] - all TypeScript errors found
        - test_summary: None (TypeScript doesn't run tests)
        - build_status: "SUCCESS" | "FAILURE"

    Raises:
        FileNotFoundError: If log file doesn't exist.
    """
    path = Path(log_file)
    content = path.read_text(encoding="utf-8", errors="replace")

    issues = _extract_issues(content)
    build_status = "FAILURE" if issues else "SUCCESS"

    return issues, None, build_status


def _extract_issues(content: str) -> list[Issue]:
    """Extract TypeScript errors from log content.

    Args:
        content: Log file content.

    Returns:
        List of Issue dataclasses with TypeScript errors.
    """
    issues = []
    seen = set()

    # Try primary pattern: path(line,col): error TSNNNN: message
    for match in TS_ERROR_PATTERN.finditer(content):
        file_path, line, col, severity, code, message = match.groups()
        dedup_key = f"{file_path}:{line}:{col}:{code}"

        if dedup_key in seen:
            continue
        seen.add(dedup_key)

        issues.append(Issue(
            file=file_path,
            line=int(line),
            message=f"{code}: {message}",
            severity=SEVERITY_ERROR,
            category="typescript_error",
        ))

    # Try alternative pattern if no matches: path:line:col - message
    if not issues:
        for match in TS_ERROR_ALT_PATTERN.finditer(content):
            file_path, line, col, severity, code, message = match.groups()
            dedup_key = f"{file_path}:{line}:{col}:{code}"

            if dedup_key in seen:
                continue
            seen.add(dedup_key)

            issues.append(Issue(
                file=file_path,
                line=int(line),
                message=f"{code}: {message}",
                severity=SEVERITY_ERROR,
                category="typescript_error",
            ))

    return issues

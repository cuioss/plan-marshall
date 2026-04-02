#!/usr/bin/env python3
"""Parse subcommand for Gradle build output.

Implements BuildParser protocol for unified build log parsing.
Internal module - use gradle.py CLI entry point instead.

Usage (internal):
    from _gradle_cmd_parse import parse_log

    issues, test_summary, build_status = parse_log("path/to/build.log")
"""

import re
from pathlib import Path

# Direct imports - executor sets up PYTHONPATH for cross-skill imports
from _build_parse import (
    SEVERITY_ERROR,
    SEVERITY_WARNING,
    CategoryPatterns,
    Issue,
    UnitTestSummary,
    categorize_issue,
    collect_stack_traces,
    extract_test_summary,
)
from _build_parse import (
    detect_build_status as _detect_build_status_base,
)

# Gradle-specific categorization patterns. Uses regex patterns for
# Gradle task-specific markers alongside shared JVM patterns.
GRADLE_PATTERNS: CategoryPatterns = {
    'compilation_error': [
        r'error:\s+cannot find symbol',
        r'error:\s+incompatible types',
        r'error:\s+illegal start',
        r"error:\s+';' expected",
        r'error:\s+class .* is public',
        r'error:\s+package .* does not exist',
        r'error:\s+method .* cannot be applied',
        r'error:\s+unreported exception',
        r'error:\s+variable .* might not have been initialized',
        r'error:\s+cannot access',
        r"Execution failed for task ':.*:compileJava'",
        r"Execution failed for task ':.*:compileKotlin'",
    ],
    'test_failure': [
        r'>\s+\d+ tests? completed, \d+ failed',
        r'FAILED',
        r'AssertionFailedError',
        r'AssertionError',
        r"Execution failed for task ':.*:test'",
    ],
    'dependency_error': [
        r'Could not resolve',
        r'Could not find',
        r'Could not download',
        r'Failed to resolve',
        r'Cannot resolve external dependency',
    ],
    'javadoc_warning': [
        r'warning:\s+no @param',
        r'warning:\s+no @return',
        r'warning:\s+missing @',
        'javadoc',
        r"Execution failed for task ':.*:javadoc'",
    ],
    'deprecation_warning': [
        r'\[deprecation\]',
        'has been deprecated',
        'is deprecated',
    ],
    'unchecked_warning': [
        r'\[unchecked\]',
        'unchecked conversion',
        'unchecked call',
    ],
    'openrewrite_info': [
        r'org\.openrewrite',
        r'rewrite-gradle-plugin',
        'rewrite:',
    ],
}


def extract_file_location(line: str) -> tuple[str, int, int]:
    """Extract file path, line, and column from error message."""
    match = re.search(r'([^\s:]+\.(java|kt|groovy)):(\d+):?(\d+)?', line)
    if match:
        return match.group(1), int(match.group(3)), int(match.group(4)) if match.group(4) else 0
    return '', 0, 0


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
    content = path.read_text(encoding='utf-8', errors='replace')
    lines = content.split('\n')

    issues = _extract_issues(lines)
    test_summary = _extract_test_summary(content)
    build_status = _detect_build_status(content)

    return issues, test_summary, build_status


def _detect_build_status(content: str) -> str:
    """Detect Gradle build status using shared detector."""
    return _detect_build_status_base(
        content,
        success_markers=['BUILD SUCCESSFUL'],
        failure_markers=['BUILD FAILED'],
        default='FAILURE',
    )


def _extract_issues(lines: list[str]) -> list[Issue]:
    """Extract all issues from Gradle output as Issue dataclasses.

    Uses shared categorize_issue with Gradle-specific patterns.
    Deduplicates issues by key (type:file:line:message_prefix).
    """
    issues: list[Issue] = []
    seen: set[str] = set()

    for line in lines:
        stripped = line.strip()

        # Skip stack trace lines (handled by collect_stack_traces)
        if stripped.startswith('at ') or stripped.startswith('Caused by:'):
            continue

        issue_type = categorize_issue(line, GRADLE_PATTERNS)
        if issue_type == 'other':
            continue

        file_path, file_line, _ = extract_file_location(line)
        message = stripped

        # Deduplication
        dedup_key = f'{issue_type}:{file_path}:{file_line}:{message[:100]}'
        if dedup_key in seen:
            continue
        seen.add(dedup_key)

        # Map type to severity
        severity = SEVERITY_ERROR if 'error' in issue_type else SEVERITY_WARNING

        issues.append(
            Issue(
                file=file_path if file_path else None,
                line=file_line if file_line else None,
                message=message[:500],
                severity=severity,
                category=issue_type,
            )
        )

    # Attach stack traces to issues
    collect_stack_traces(lines, issues)

    return issues


def _extract_test_summary(content: str) -> UnitTestSummary | None:
    """Extract Gradle test summary using shared extractor.

    Gradle format: "5 tests completed, 2 failed" or "5 tests completed, 2 failed, 1 skipped"
    """
    return extract_test_summary(
        content,
        r'(\d+) tests? completed(?:, (\d+) failed)?(?:, (\d+) skipped)?',
        group_map={'total': 1, 'failed': 2, 'skipped': 3},
    )

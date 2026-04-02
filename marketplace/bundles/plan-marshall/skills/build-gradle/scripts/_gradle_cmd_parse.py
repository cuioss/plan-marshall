#!/usr/bin/env python3
"""Parse subcommand for Gradle build output.

Implements BuildParser protocol for unified build log parsing.
Uses the shared ParserRegistry for consistent detection and routing.
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
    make_dedup_key,
)
from _build_parse import (
    detect_build_status as _detect_build_status_base,
)
from _build_parser_registry import DetectionRule, ParserRegistry  # noqa: F401 - re-exported for test access

# Gradle-specific categorization patterns. Uses regex patterns for
# Gradle task-specific markers alongside shared JVM patterns.
GRADLE_PATTERNS: CategoryPatterns = {
    'compilation_error': [
        # Java errors
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
        # Kotlin errors
        r'Unresolved reference',
        r'Type mismatch',
        r'Smart cast to .* is impossible',
        r'None of the following candidates is applicable',
        r'Overload resolution ambiguity',
        r"Val cannot be reassigned",
        # Task failure markers
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


def parse_file_location(line: str) -> dict[str, str | int | None]:
    """Extract file, line, and column from a Gradle error/warning line.

    Supports Java, Kotlin, and Groovy source file patterns.
    Returns dict with consistent keys matching Maven's parse_file_location().
    """
    result: dict[str, str | int | None] = {'file': None, 'line': None, 'column': None}
    match = re.search(r'([^\s:]+\.(java|kt|groovy)):(\d+):?(\d+)?', line)
    if match:
        result['file'] = match.group(1)
        result['line'] = int(match.group(3))
        result['column'] = int(match.group(4)) if match.group(4) else None
    return result


# =============================================================================
# Gradle-specific parser function
# =============================================================================


def _parse_gradle_log(log_file: str) -> tuple[list[Issue], UnitTestSummary | None, str]:
    """Parse Gradle build log file."""
    path = Path(log_file)
    content = path.read_text(encoding='utf-8', errors='replace')
    lines = content.split('\n')

    issues = _extract_issues(lines)
    test_summary = _extract_test_summary(content)
    build_status = _detect_build_status(content)

    return issues, test_summary, build_status


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
    return _parse_gradle_log(str(log_file))


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

        # Skip continuation lines (multi-line error messages)
        if stripped.startswith('->') or stripped.startswith('>'):
            continue

        issue_type = categorize_issue(line, GRADLE_PATTERNS)
        if issue_type == 'other':
            continue

        location = parse_file_location(line)
        message = stripped

        # Deduplication using shared key format
        dedup_key = make_dedup_key(issue_type, location.get('file'), location.get('line'), message)
        if dedup_key in seen:
            continue
        seen.add(dedup_key)

        # Map type to severity
        severity = SEVERITY_ERROR if 'error' in issue_type else SEVERITY_WARNING

        issues.append(
            Issue(
                file=location.get('file'),
                line=location.get('line'),
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

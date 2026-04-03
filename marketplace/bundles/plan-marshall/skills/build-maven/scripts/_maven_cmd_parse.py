#!/usr/bin/env python3
"""Parse subcommand for Maven build output.

Implements BuildParser protocol for unified build log parsing.
Uses the shared ParserRegistry for consistent detection and routing.
Internal module - use maven.py CLI entry point instead.

Usage (internal):
    from _maven_cmd_parse import parse_log

    issues, test_summary, build_status = parse_log("path/to/build.log")
"""

import re
from pathlib import Path

# Direct imports - executor sets up PYTHONPATH for cross-skill imports
from _build_jvm_patterns import JVM_BASE_PATTERNS, merge_patterns, parse_jvm_file_location
from _build_parse import (
    SEVERITY_ERROR,
    SEVERITY_WARNING,
    CategoryPatterns,
    Issue,
    UnitTestSummary,
    add_issue_deduped,
    categorize_issue,
    collect_stack_traces,
)
from _build_parse import (
    detect_build_status as _detect_build_status_base,
)
# Maven-specific categorization patterns. Extends shared JVM base patterns
# with Maven-specific additions (substring matching by default).
MAVEN_PATTERNS: CategoryPatterns = merge_patterns(JVM_BASE_PATTERNS, {
    # Override openrewrite_info to include Maven-specific plugin name
    'openrewrite_info': [
        'org.openrewrite',
        'rewrite-maven-plugin',
        'rewrite:',
    ],
})


def parse_file_location(line: str) -> dict[str, str | int | None]:
    """Extract file, line, and column from a Maven error/warning line.

    Delegates to shared parse_jvm_file_location from _build_jvm_patterns.
    """
    return parse_jvm_file_location(line)


# =============================================================================
# BuildParser Protocol Implementation
# =============================================================================


def parse_log(log_file: str | Path) -> tuple[list[Issue], UnitTestSummary | None, str]:
    """Parse Maven build log file.

    Implements BuildParser protocol for unified build log parsing.

    Args:
        log_file: Path to the Maven build log file.

    Returns:
        Tuple of (issues, test_summary, build_status):
        - issues: list[Issue] - all errors and warnings found
        - test_summary: UnitTestSummary | None - test counts if tests ran
        - build_status: "SUCCESS" | "FAILURE"

    Raises:
        FileNotFoundError: If log file doesn't exist.
    """
    content = Path(str(log_file)).read_text(encoding='utf-8', errors='replace')

    issues = _extract_issues(content)
    test_summary = _extract_test_summary(content)
    build_status = _detect_build_status(content)

    return issues, test_summary, build_status


def _extract_issues(content: str) -> list[Issue]:
    """Extract all issues from Maven output as Issue dataclasses.

    Deduplicates issues by key (category:file:line:message_prefix) to avoid
    duplicates from reactor summary and per-module output in multi-module builds.
    """
    issues: list[Issue] = []
    seen: set[str] = set()

    for line in content.split('\n'):
        stripped = line.strip()

        # Skip stack trace lines (handled by collect_stack_traces)
        if stripped.startswith('at ') or stripped.startswith('Caused by:'):
            continue

        severity = None
        if '[ERROR]' in line:
            severity = SEVERITY_ERROR
        elif '[WARNING]' in line:
            severity = SEVERITY_WARNING

        if severity:
            message = re.sub(r'^\[(INFO|ERROR|WARNING)\]\s*', '', stripped)
            # Skip empty messages and continuation lines
            if not message or message.startswith('->'):
                continue

            location = parse_file_location(line)
            category = categorize_issue(message, MAVEN_PATTERNS)
            loc_file = location.get('file')
            loc_line = location.get('line')

            add_issue_deduped(
                issues, seen,
                file=str(loc_file) if loc_file is not None else None,
                line=int(loc_line) if loc_line is not None else None,
                message=message,
                severity=severity,
                category=category,
            )

    # Attach stack traces to issues
    collect_stack_traces(content.split('\n'), issues)

    return issues


def _detect_build_status(content: str) -> str:
    """Detect Maven build status.

    Maven-specific: also checks for [ERROR] lines as failure indicator.
    """
    return _detect_build_status_base(
        content,
        success_markers=['BUILD SUCCESS'],
        failure_markers=['BUILD FAILURE', '[ERROR]'],
        default='FAILURE',
    )


def _extract_test_summary(content: str) -> UnitTestSummary | None:
    """Extract Maven test summary.

    Does NOT use the shared extract_test_summary() helper because Maven
    reports Failures and Errors as separate fields that must be combined
    into a single 'failed' count — a pattern the shared helper doesn't support.
    """
    # Maven format: Tests run: X, Failures: Y, Errors: Z, Skipped: W
    pattern = r'Tests run:\s*(\d+),\s*Failures:\s*(\d+),\s*Errors:\s*(\d+),\s*Skipped:\s*(\d+)'
    matches = list(re.finditer(pattern, content))
    if not matches:
        return None

    m = matches[-1]
    total = int(m.group(1))
    failures = int(m.group(2))
    errors = int(m.group(3))
    skipped = int(m.group(4))
    failed = failures + errors

    return UnitTestSummary(
        passed=total - failed - skipped,
        failed=failed,
        skipped=skipped,
        total=total,
    )

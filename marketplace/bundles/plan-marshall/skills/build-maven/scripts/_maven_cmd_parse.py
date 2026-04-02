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
from _build_parse import (
    SEVERITY_ERROR,
    SEVERITY_WARNING,
    CategoryPatterns,
    Issue,
    UnitTestSummary,
    categorize_issue,
    collect_stack_traces,
)
from _build_parse import (
    detect_build_status as _detect_build_status_base,
)
from _build_parser_registry import DetectionRule, ParserRegistry

# Maven-specific categorization patterns (substring matching by default,
# regex when metacharacters are present).
MAVEN_PATTERNS: CategoryPatterns = {
    'compilation_error': [
        'cannot find symbol',
        'incompatible types',
        'illegal start',
        'class, interface, or enum expected',
        'unreported exception',
        'method does not override',
        'not a statement',
        'package does not exist',
        'cannot be applied',
    ],
    'test_failure': [
        'tests run:',
        'failure!',
        'test failure',
        'assertionfailed',
        'expected:',
    ],
    'dependency_error': [
        'could not resolve dependencies',
        'could not find artifact',
        'missing, no dependency',
        'artifact not found',
        'non-resolvable',
    ],
    'javadoc_warning': [
        'javadoc',
        'no @param',
        'no @return',
        '@param name',
        'missing @',
    ],
    'deprecation_warning': [
        '[deprecation]',
        'has been deprecated',
    ],
    'unchecked_warning': [
        '[unchecked]',
        'unchecked conversion',
    ],
    'openrewrite_info': [
        'org.openrewrite',
        'rewrite-maven-plugin',
        'rewrite:',
    ],
}


def parse_file_location(line: str) -> dict:
    """Extract file, line, and column from a Maven error/warning line."""
    result = {'file': None, 'line': None, 'column': None}
    match = re.search(r'([^\s\[\]]+\.java):\[(\d+),(\d+)\]', line)
    if match:
        return {'file': match.group(1), 'line': int(match.group(2)), 'column': int(match.group(3))}
    match = re.search(r'([^\s\[\]]+\.java):(\d+):', line)
    if match:
        return {'file': match.group(1), 'line': int(match.group(2)), 'column': None}
    match = re.search(r'(\w+Test)\.(\w+):(\d+)', line)
    if match:
        return {'file': f'{match.group(1)}.java', 'line': int(match.group(3)), 'column': None, 'method': match.group(2)}
    return result


# =============================================================================
# Maven-specific parser function
# =============================================================================


def _parse_maven_log(log_file: str) -> tuple[list[Issue], UnitTestSummary | None, str]:
    """Parse Maven build log file."""
    path = Path(log_file)
    content = path.read_text(encoding='utf-8', errors='replace')

    issues = _extract_issues(content)
    test_summary = _extract_test_summary(content)
    build_status = _detect_build_status(content)

    return issues, test_summary, build_status


def _has_maven_output(content: str) -> bool:
    """Detect Maven output from content."""
    return '[INFO] BUILD' in content or '[ERROR]' in content or '[WARNING]' in content


# Registry with single Maven parser
_REGISTRY = ParserRegistry([
    DetectionRule('maven', ('mvn', 'mvnw'), _has_maven_output, _parse_maven_log),
])


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
    return _parse_maven_log(str(log_file))


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

            # Deduplication
            dedup_key = f'{category}:{location.get("file")}:{location.get("line")}:{message[:100]}'
            if dedup_key in seen:
                continue
            seen.add(dedup_key)

            issues.append(
                Issue(
                    file=location.get('file'),
                    line=location.get('line'),
                    message=message[:500],
                    severity=severity,
                    category=category,
                )
            )

    # Attach stack traces to issues
    collect_stack_traces(content.split('\n'), issues)

    return issues


def _detect_build_status(content: str) -> str:
    """Detect Maven build status.

    Maven-specific: also checks for [ERROR] lines as failure indicator.
    """
    status = _detect_build_status_base(
        content,
        success_markers=['BUILD SUCCESS'],
        failure_markers=['BUILD FAILURE'],
        default='SUCCESS',
    )
    if status == 'SUCCESS' and re.search(r'^\[ERROR\]', content, re.MULTILINE):
        return 'FAILURE'
    return status


def _extract_test_summary(content: str) -> UnitTestSummary | None:
    """Extract Maven test summary.

    Maven reports Failures and Errors separately; we combine them into failed.
    Uses shared extract_test_summary with custom post-processing.
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

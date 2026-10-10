#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
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
from _build_jvm_patterns import JVM_BASE_PATTERNS, override_patterns, parse_jvm_file_location
from _build_parse import (
    POPULATION_MEASURED,
    POPULATION_UNMEASURED,
    SEVERITY_ERROR,
    SEVERITY_WARNING,
    CategoryPatterns,
    Issue,
    UnitTestSummary,
    add_issue_deduped,
    categorize_issue,
    collect_stack_traces,
    read_log_text,
)
from _build_parse import (
    detect_build_status as _detect_build_status_base,
)

# Maven-specific categorization patterns. Extends shared JVM base patterns
# with Maven-specific additions (substring matching by default).
MAVEN_PATTERNS: CategoryPatterns = override_patterns(
    JVM_BASE_PATTERNS,
    {
        # Override openrewrite_info to include Maven-specific plugin name
        'openrewrite_info': [
            'org.openrewrite',
            'rewrite-maven-plugin',
            'rewrite:',
        ],
    },
)


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
    content = read_log_text(log_file)

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
                issues,
                seen,
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


# Maven/Surefire/Failsafe count line: Tests run: X, Failures: Y, Errors: Z, Skipped: W
_TESTS_RUN_PATTERN = re.compile(r'Tests run:\s*(\d+),\s*Failures:\s*(\d+),\s*Errors:\s*(\d+),\s*Skipped:\s*(\d+)')

# Plugin execution header, e.g. `--- surefire:3.5.2:test (default-test) @ core ---`
# (Maven 3.9 / 4) or `--- maven-surefire-plugin:3.5.2:test (default-test) @ core ---`
# (Maven 3.8). Every header opens a new execution; the plugin token names it.
_EXECUTION_HEADER_PATTERN = re.compile(r'---\s+([\w.\-]+):[\w.\-]+:[\w.\-]+\s.*@.*---')

# Plugin token -> test runner it belongs to (short and long header forms).
_TEST_RUNNERS = {
    'surefire': 'surefire',
    'maven-surefire-plugin': 'surefire',
    'failsafe': 'failsafe',
    'maven-failsafe-plugin': 'failsafe',
}

# Marker Surefire/Failsafe print immediately before an execution's summary block.
_RESULTS_MARKER_PATTERN = re.compile(r'^(?:\[(?:INFO|ERROR|WARNING)\]\s*)?Results\s*:\s*$')

# Banner of a parallel (`-T`) build: independent modules may interleave, so the
# nearest preceding execution header no longer reliably names a summary's runner.
_PARALLEL_BUILD_BANNER = 'MultiThreadedBuilder'


def _sum_counts(matches: list[re.Match[str]]) -> tuple[int, int, int]:
    """Sum (total, failed, skipped) over Maven count lines; failed = failures + errors."""
    total = sum(int(m.group(1)) for m in matches)
    failed = sum(int(m.group(2)) + int(m.group(3)) for m in matches)
    skipped = sum(int(m.group(4)) for m in matches)
    return total, failed, skipped


def _extract_test_summary(content: str) -> UnitTestSummary | None:
    """Extract the Maven test summary by summing every summary block.

    Does NOT use the shared extract_test_summary() helper: Maven reports Failures
    and Errors as separate fields combined into one 'failed' count, and a Maven
    log carries several summary blocks (one per module, one per test plugin), so
    keeping the last match would report only one of them.

    Every ``Tests run:`` line is classified:

    - **per-class** — the line carries ``Time elapsed``; it repeats counts already
      in a summary line and is excluded.
    - **summary** — no ``Time elapsed``, and it follows a ``Results:`` marker
      inside the current test-plugin execution (an execution ends at the next
      ``--- plugin:version:goal ... @ module ---`` header). Summary lines are
      summed across modules and plugins.
    - **ambiguous** — any other ``Tests run:`` line (e.g. a quiet ``-q`` log, where
      the ``[INFO] Results:`` marker is suppressed).

    Each summary line is attributed to the nearest preceding ``surefire`` /
    ``failsafe`` execution header (the Maven 3.8 long form
    ``maven-surefire-plugin:`` / ``maven-failsafe-plugin:`` is accepted), and
    ``by_runner`` carries the executed count (passed + failed) per runner — a
    runner absent from the log is absent from the dict. Attribution by nearest
    header is only reliable for a sequential build: when the log carries the
    ``MultiThreadedBuilder`` banner the summed total is kept but ``by_runner`` is
    omitted.

    The summary is declared ``population='unmeasured'`` when any ambiguous line
    exists, or when no summary line was recognised while per-class lines were.
    Its counts are then the sum of the non-per-class lines (or of the per-class
    lines when nothing else exists), so a failed test stays visible to the
    truthful-status check, and ``by_runner`` is omitted because nothing was
    attributed from a recognised summary.

    Returns:
        The summed summary, or None only when the log has no ``Tests run:`` line.
    """
    summary_lines: list[re.Match[str]] = []
    ambiguous_lines: list[re.Match[str]] = []
    per_class_lines: list[re.Match[str]] = []
    runner_executed: dict[str, int] = {}

    current_runner: str | None = None
    results_seen = False

    for line in content.split('\n'):
        header = _EXECUTION_HEADER_PATTERN.search(line)
        if header:
            current_runner = _TEST_RUNNERS.get(header.group(1))
            results_seen = False
            continue

        stripped = line.strip()
        if _RESULTS_MARKER_PATTERN.match(stripped):
            results_seen = True
            continue

        match = _TESTS_RUN_PATTERN.search(line)
        if not match:
            continue

        if 'Time elapsed' in line:
            per_class_lines.append(match)
        elif results_seen:
            summary_lines.append(match)
            if current_runner is not None:
                executed = int(match.group(1)) - int(match.group(4))
                runner_executed[current_runner] = runner_executed.get(current_runner, 0) + executed
        else:
            ambiguous_lines.append(match)

    if not (summary_lines or ambiguous_lines or per_class_lines):
        return None

    unmeasured = bool(ambiguous_lines) or (not summary_lines and bool(per_class_lines))
    counted = (summary_lines + ambiguous_lines) or per_class_lines
    total, failed, skipped = _sum_counts(counted)

    by_runner: dict[str, int] | None = None
    if not unmeasured and runner_executed and _PARALLEL_BUILD_BANNER not in content:
        by_runner = runner_executed

    return UnitTestSummary(
        passed=total - failed - skipped,
        failed=failed,
        skipped=skipped,
        total=total,
        by_runner=by_runner,
        population=POPULATION_UNMEASURED if unmeasured else POPULATION_MEASURED,
    )

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
    make_dedup_key,
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


# Maven's failure epilogue: fixed advice, report pointers and banners Maven and
# Surefire print at [ERROR] level after a failed build. None of them is a
# diagnostic, so none may become an issue (and through it a blocking finding).
# Derived from real failing builds on Maven 3.8.8, 3.9.16 and 4.0.0-rc-7, plus
# both Surefire report-pointer wordings ("Please refer to ..." in older Surefire,
# "See ..." in Surefire 3.5.x). Each pattern is matched with ``fullmatch``
# against the prefix-stripped message, so a reworded line is filed again
# (fail-visible) rather than a genuine diagnostic being silently dropped.
_MAVEN_EPILOGUE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"To see the full stack trace of the errors, re-run Maven with the '?-e'? switch\.?"),
    re.compile(r"Re-run Maven using the '?-X'? switch to enable (full debug logging|verbose output)\.?"),
    re.compile(r'For more information about the errors and possible solutions, please read the following articles:'),
    re.compile(r'\[Help \d+\] https?://\S+'),
    re.compile(r'After correcting the problems, you can resume the build with the command'),
    re.compile(r'mvn (<args>|\[args\]) -r(f :\S+)?'),
    re.compile(r'(Please refer to|See) .+ for the individual test results\.'),
    re.compile(r'(Please refer to|See) dump files \(if any exist\) .+'),
    # Maven 4 logs the failing reactor-summary rows and the banner at [ERROR].
    re.compile(r'\S.* \.{3,} (SUCCESS|FAILURE|SKIPPED)( \[.+\])?'),
    re.compile(r'BUILD FAILURE'),
    # Section banners: Surefire's results-section headers and the compiler
    # plugin's banner. The rows UNDER the header carry the diagnostics; the
    # header itself carries none.
    re.compile(r'Failures:'),
    re.compile(r'Errors:'),
    re.compile(r'COMPILATION ERROR :'),
)

# Javac's continuation fields. They are printed under the compiler error line
# that produced them and carry the name that line refers to, so they are
# attached to that error as its DETAIL rather than filed as issues of their
# own — but never dropped, and never attached to nothing: a continuation line
# with no compiler error before it stays filed (fail-visible).
_COMPILER_CONTINUATION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r'symbol:\s+\S.*'),
    re.compile(r'location:\s+\S.*'),
)


def _is_epilogue(message: str) -> bool:
    """Whether a prefix-stripped message is a line of Maven's failure epilogue."""
    return any(pattern.fullmatch(message) for pattern in _MAVEN_EPILOGUE_PATTERNS)


def _is_compiler_continuation(message: str) -> bool:
    """Whether a prefix-stripped message is a javac continuation field."""
    return any(pattern.fullmatch(message) for pattern in _COMPILER_CONTINUATION_PATTERNS)


def _append_detail(issue: Issue, line: str) -> None:
    """Attach a continuation line to an issue's detail once, preserving order.

    Maven re-prints the compiler's continuation fields at ``[ERROR]`` inside the
    goal-failure block, so the same line can arrive twice for one issue (the
    second time after the error itself was de-duplicated). Appending blindly
    would publish each field twice.
    """
    existing = issue.detail.split('\n') if issue.detail else []
    if line in existing:
        return
    issue.detail = '\n'.join([*existing, line])


def _is_passing_test_count(message: str) -> bool:
    """Whether a message is a ``Tests run:`` line reporting no failure and no error."""
    match = _TESTS_RUN_PATTERN.search(message)
    return match is not None and int(match.group(2)) == 0 and int(match.group(3)) == 0


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
    Lines of Maven's failure epilogue, section banners and ``Tests run:`` lines
    with zero failures and zero errors are not issues and are skipped.

    Javac's ``symbol:`` / ``location:`` continuation fields are attached to the
    compiler error they follow as its ``detail``, because dropping them would
    lose the name the error refers to. A continuation field with no compiler
    error before it is filed like any other diagnostic.
    """
    issues: list[Issue] = []
    seen: set[str] = set()
    issues_by_key: dict[str, Issue] = {}
    last_compiler_error: Issue | None = None

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
            if last_compiler_error is not None and _is_compiler_continuation(message):
                _append_detail(last_compiler_error, message)
                continue
            if _is_epilogue(message) or _is_passing_test_count(message):
                last_compiler_error = None
                continue

            location = parse_file_location(line)
            category = categorize_issue(message, MAVEN_PATTERNS)
            loc_file = location.get('file')
            loc_line = location.get('line')

            added = add_issue_deduped(
                issues,
                seen,
                file=str(loc_file) if loc_file is not None else None,
                line=int(loc_line) if loc_line is not None else None,
                message=message,
                severity=severity,
                category=category,
            )
            key = make_dedup_key(
                category,
                str(loc_file) if loc_file is not None else None,
                int(loc_line) if loc_line is not None else None,
                message,
            )
            if added:
                issue = issues[-1]
                issues_by_key[key] = issue
            else:
                issue = issues_by_key[key]
            # A compiler error opens the window its continuation fields attach
            # to; any other diagnostic closes it.
            last_compiler_error = issue if category == 'compilation_error' else None
            continue

        # An UNPREFIXED javac continuation line under a compiler error is that
        # error's detail: a compile-only log prints them bare, without Maven
        # re-printing the block at [ERROR], so dropping them here would lose the
        # name that the error's own message does not carry. Any other unprefixed
        # line closes the window, so a stray `symbol:` far below the error is
        # never adopted.
        if last_compiler_error is not None and _is_compiler_continuation(stripped):
            _append_detail(last_compiler_error, stripped)
        else:
            last_compiler_error = None

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


# =============================================================================
# Surefire -Dtest selectors that matched nothing
# =============================================================================

TEST_SELECTOR_MATCHED_NOTHING = 'test_selector_matched_nothing'
"""Reason token for a Surefire ``-Dtest`` selector that matched no test.

Distinct from a test failure: nothing ran, so there is no failing test to fix —
the selector is wrong. Kept as a token rather than prose so the run path, the
emitted result and a report can agree on one name.
"""

# Surefire's goal failure when a selector matched nothing:
#   No tests matching pattern "Awaits#runs" were executed!
#   (Set -Dsurefire.failIfNoSpecifiedTests=false to ignore this error.)
_SELECTOR_MISS_PATTERN = re.compile(r'No tests matching pattern "?([^"!\n]*)"? were executed')

# The selector a Maven command carries, e.g. ``-Dtest=Awaits#runs`` or
# ``-Dtest="Awaits#runs"``.
_DTEST_SELECTOR_PATTERN = re.compile(r'-Dtest="?([^"\s]+)"?')


def dtest_selector(command: str | None) -> str | None:
    """Return the ``-Dtest`` selector a Maven command carries, or None.

    Args:
        command: The full Maven command string, when the run path knows it.

    Returns:
        The selector as written after ``-Dtest=``, or None when the command
        carries none.
    """
    if not command:
        return None
    match = _DTEST_SELECTOR_PATTERN.search(command)
    return match.group(1) if match else None


def selector_miss_reason(log_text: str, command: str | None = None) -> str | None:
    """Return the named reason a Surefire selector matched nothing, or None.

    Two shapes mean the same thing, and both are checked because only one of
    them reaches a failing build:

    - Surefire's own goal failure, ``No tests matching pattern … were executed``,
      which ends the build non-zero.
    - A ``-Dtest`` run that parsed a summary claiming ZERO collected tests. With
      ``-Dsurefire.failIfNoSpecifiedTests=false`` the same miss exits 0 and
      prints a passing-looking summary, so the command is needed to know a
      selector was in play at all. A selector that matched a class whose tests
      are all skipped collects them, so it is NOT a miss however many executed.

    Args:
        log_text: The captured build log, already read as text.
        command: The Maven command string, when the caller knows it.

    Returns:
        ``TEST_SELECTOR_MATCHED_NOTHING`` when a selector matched nothing,
        otherwise None. None is also the answer when the population cannot be
        determined — a run with no parsed summary is not evidence of zero tests.
    """
    if _SELECTOR_MISS_PATTERN.search(log_text):
        return TEST_SELECTOR_MATCHED_NOTHING
    if dtest_selector(command) is None:
        return None
    summary = _extract_test_summary(log_text)
    # ``total`` — the COLLECTED count — is the population test, not ``executed``.
    # A selector that matched a class whose tests are all ``@Disabled`` collects
    # them and runs none: ``executed`` is zero there too, yet the selector did
    # match and the run is a truthful green. A selector that matched NOTHING
    # collects nothing at all, so ``total`` is zero.
    if summary is not None and summary.total == 0:
        return TEST_SELECTOR_MATCHED_NOTHING
    return None

#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Parse functionality for Pyproject (Python/pyprojectx) build output.

Uses the shared ParserRegistry for consistent detection and routing.
Handles output from mypy, ruff, and pytest.

Usage (internal):
    from _pyproject_cmd_parse import parse_log
"""

import re
from pathlib import Path

from _build_parse import (
    SEVERITY_ERROR,
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
from _build_parser_registry import DetectionRule, ParserRegistry

# Pre-compiled patterns for tool-specific parsers
_MYPY_ERROR_PATTERN = re.compile(r'^(.+\.py):(\d+): error: (.+)$', re.MULTILINE)
_RUFF_ISSUE_PATTERN = re.compile(r'^(.+\.py):(\d+):\d+: ([A-Z]+\d+) (.+)$', re.MULTILINE)
_PYTEST_FAILED_PATTERN = re.compile(r'^FAILED (.+\.py)::(\S+)(?: - (.+))?$', re.MULTILINE)

# Python-specific categorization patterns for use with shared categorize_issue().
# Patterns are checked case-insensitively; regex metacharacters trigger regex mode.
PYTHON_PATTERNS: CategoryPatterns = {
    'type_error': [
        r'\.py:\d+: error:',
        'incompatible type',
        'incompatible return value',
        'has no attribute',
        'missing positional argument',
    ],
    'lint_error': [
        r'\.py:\d+:\d+: [A-Z]+\d+',
        'ruff',
    ],
    'test_failure': [
        r'^FAILED ',
        'AssertionError',
        'assert ',
    ],
    'import_error': [
        'ModuleNotFoundError',
        'ImportError',
        'No module named',
    ],
}


# =============================================================================
# Tool-specific parsers
# =============================================================================


def _parse_mypy(log_file: str) -> tuple[list[Issue], UnitTestSummary | None, str]:
    """Parse mypy type-check output."""
    content = read_log_text(log_file)
    issues: list[Issue] = []
    seen: set[str] = set()

    for match in _MYPY_ERROR_PATTERN.finditer(content):
        file_path = match.group(1)
        line = int(match.group(2))
        message = match.group(3)
        category = categorize_issue(message, PYTHON_PATTERNS) or 'type_error'
        if category == 'other':
            category = 'type_error'

        add_issue_deduped(
            issues,
            seen,
            file=file_path,
            line=line,
            message=message,
            severity=SEVERITY_ERROR,
            category=category,
        )

    status = _detect_build_status_base(
        content,
        success_markers=['Success: no issues found'],
        failure_markers=['error:'],
        default='FAILURE' if issues else 'SUCCESS',
    )
    return issues, None, status


def _parse_ruff(log_file: str) -> tuple[list[Issue], UnitTestSummary | None, str]:
    """Parse ruff lint output."""
    content = read_log_text(log_file)
    issues: list[Issue] = []
    seen: set[str] = set()

    for match in _RUFF_ISSUE_PATTERN.finditer(content):
        file_path = match.group(1)
        line = int(match.group(2))
        message = f'{match.group(3)} {match.group(4)}'

        add_issue_deduped(
            issues,
            seen,
            file=file_path,
            line=line,
            message=message,
            severity=SEVERITY_ERROR,
            category='lint_error',
        )

    status = 'FAILURE' if issues else 'SUCCESS'
    return issues, None, status


def _parse_pytest(log_file: str) -> tuple[list[Issue], UnitTestSummary | None, str]:
    """Parse pytest test output.

    Extracts file locations from FAILED lines and attempts to find line numbers
    from traceback context in the output.
    """
    content = read_log_text(log_file)
    lines = content.split('\n')
    issues: list[Issue] = []
    seen: set[str] = set()

    for match in _PYTEST_FAILED_PATTERN.finditer(content):
        file_path = match.group(1)
        test_name = match.group(2)
        message = match.group(3) if match.group(3) else f'Test {test_name} failed'

        # Try to extract line number from traceback (file.py:NN: message)
        line_num = _find_pytest_line_number(content, file_path, test_name)

        add_issue_deduped(
            issues,
            seen,
            file=file_path,
            line=line_num,
            message=message,
            severity=SEVERITY_ERROR,
            category='test_failure',
        )

    # Attach stack traces to issues
    collect_stack_traces(lines, issues)

    test_summary = _extract_pytest_summary(content)

    status = _detect_build_status_base(
        content,
        success_markers=['passed'],
        failure_markers=['FAILED', 'error'],
        default='FAILURE' if issues else 'SUCCESS',
    )
    return issues, test_summary, status


def _find_pytest_line_number(content: str, file_path: str, test_name: str) -> int | None:
    """Try to extract line number for a pytest failure from traceback output.

    Looks for patterns like 'file.py:42: AssertionError' in the output.
    """
    # Pattern: file.py:NN: in test_name or file.py:NN: AssertionError
    escaped_file = re.escape(file_path)
    pattern = re.compile(rf'{escaped_file}:(\d+):')
    matches = list(pattern.finditer(content))
    if matches:
        # Return last match (closest to the actual failure point)
        return int(matches[-1].group(1))
    return None


# Independent per-count patterns for the pytest summary line. Each count is
# matched on its own so extraction is independent of the order in which pytest
# renders them (`N passed, M failed` vs `M failed, N passed`). Word boundaries
# keep `failed` / `passed` from matching inside `xfailed` / `xpassed`.
_PYTEST_SUMMARY_COUNTS: dict[str, re.Pattern[str]] = {
    'passed': re.compile(r'\b(\d+) passed\b'),
    'failed': re.compile(r'\b(\d+) failed\b'),
    'skipped': re.compile(r'\b(\d+) skipped\b'),
}


def _extract_pytest_summary(content: str) -> UnitTestSummary | None:
    """Extract the pytest summary independent of count ordering.

    pytest renders its summary counts in a tool-determined order — a passing-
    dominant run shows `10308 passed, 1 failed` while a failing-dominant run can
    show `1 failed, 10308 passed`. Each count is matched with its own pattern
    (LAST occurrence wins, mirroring the aggregate-line convention for the
    shared extractor), so both orderings yield identical counts.

    Args:
        content: Log file content (already ANSI-stripped by the caller).

    Returns:
        UnitTestSummary if any of passed/failed/skipped is present, else None.
    """
    counts: dict[str, int] = {}
    for key, pattern in _PYTEST_SUMMARY_COUNTS.items():
        matches = pattern.findall(content)
        if matches:
            counts[key] = int(matches[-1])

    if not counts:
        return None

    passed = counts.get('passed', 0)
    failed = counts.get('failed', 0)
    skipped = counts.get('skipped', 0)
    return UnitTestSummary(
        passed=passed,
        failed=failed,
        skipped=skipped,
        total=passed + failed + skipped,
    )


# =============================================================================
# Content detection functions
# =============================================================================


def _has_mypy_output(content: str) -> bool:
    return bool(re.search(r'\.py:\d+: error:', content))


def _has_ruff_output(content: str) -> bool:
    return bool(re.search(r'\.py:\d+:\d+: [A-Z]+\d+', content))


def _has_pytest_output(content: str) -> bool:
    """Detect pytest output. Uses specific markers to avoid false positives."""
    # FAILED lines are definitive pytest markers
    if 'FAILED ' in content:
        return True
    # pytest summary line uses '=' separators with pass/fail counts
    return '==' in content and ('passed' in content or 'failed' in content)


# =============================================================================
# Registry
# =============================================================================

_REGISTRY = ParserRegistry(
    [
        DetectionRule('mypy', ('mypy',), _has_mypy_output, _parse_mypy),
        DetectionRule('ruff', ('ruff',), _has_ruff_output, _parse_ruff),
        DetectionRule('pytest', ('pytest', 'test'), _has_pytest_output, _parse_pytest),
    ]
)


# =============================================================================
# Public API
# =============================================================================


def parse_log(log_file: str | Path) -> tuple[list[Issue], UnitTestSummary | None, str]:
    """Parse Python build log for errors.

    Handles output from mypy, ruff, and pytest using the shared
    ParserRegistry for detection and routing. When multiple tools
    are present in the output (common with pyprojectx verify),
    results from all matching parsers are combined.

    Args:
        log_file: Path to the log file.

    Returns:
        Tuple of (issues, test_summary, build_status)
    """
    # Python build output often contains output from multiple tools
    # (mypy + ruff + pytest in a single verify run), so we run all parsers
    # and combine results instead of using registry's single-match routing.
    return _REGISTRY.parse_multi(log_file)

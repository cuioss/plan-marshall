#!/usr/bin/env python3
"""Parse functionality for Python build output.

Uses the shared ParserRegistry for consistent detection and routing.
Handles output from mypy, ruff, and pytest.

Usage (internal):
    from _python_cmd_parse import parse_log
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
    extract_test_summary,
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
    content = Path(log_file).read_text(encoding='utf-8', errors='replace')
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
            issues, seen,
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
    content = Path(log_file).read_text(encoding='utf-8', errors='replace')
    issues: list[Issue] = []
    seen: set[str] = set()

    for match in _RUFF_ISSUE_PATTERN.finditer(content):
        file_path = match.group(1)
        line = int(match.group(2))
        message = f'{match.group(3)} {match.group(4)}'

        add_issue_deduped(
            issues, seen,
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
    content = Path(log_file).read_text(encoding='utf-8', errors='replace')
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
            issues, seen,
            file=file_path,
            line=line_num,
            message=message,
            severity=SEVERITY_ERROR,
            category='test_failure',
        )

    # Attach stack traces to issues
    collect_stack_traces(lines, issues)

    test_summary = extract_test_summary(
        content,
        r'(\d+) passed(?:.*?(\d+) failed)?(?:.*?(\d+) skipped)?',
        group_map={'passed': 1, 'failed': 2, 'skipped': 3},
    )

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

_REGISTRY = ParserRegistry([
    DetectionRule('mypy', ('mypy',), _has_mypy_output, _parse_mypy),
    DetectionRule('ruff', ('ruff',), _has_ruff_output, _parse_ruff),
    DetectionRule('pytest', ('pytest', 'test'), _has_pytest_output, _parse_pytest),
])


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

#!/usr/bin/env python3
"""Parse functionality for Python build output.

Uses the shared ParserRegistry for consistent detection and routing.
Handles output from mypy, ruff, and pytest.

Usage (internal):
    from _python_cmd_parse import parse_log
"""

import re
from pathlib import Path

from _build_parse import Issue, UnitTestSummary, extract_test_summary  # noqa: F401 - used by parsers below
from _build_parser_registry import DetectionRule, ParserRegistry


# =============================================================================
# Tool-specific parsers
# =============================================================================


def _parse_mypy(log_file: str) -> tuple[list[Issue], UnitTestSummary | None, str]:
    """Parse mypy type-check output."""
    content = Path(log_file).read_text(encoding='utf-8', errors='replace')
    issues: list[Issue] = []

    pattern = re.compile(r'^(.+\.py):(\d+): error: (.+)$', re.MULTILINE)
    for match in pattern.finditer(content):
        issues.append(
            Issue(
                file=match.group(1),
                line=int(match.group(2)),
                message=match.group(3),
                category='type_error',
                severity='error',
            )
        )

    status = 'FAILURE' if issues else 'SUCCESS'
    return issues, None, status


def _parse_ruff(log_file: str) -> tuple[list[Issue], UnitTestSummary | None, str]:
    """Parse ruff lint output."""
    content = Path(log_file).read_text(encoding='utf-8', errors='replace')
    issues: list[Issue] = []

    pattern = re.compile(r'^(.+\.py):(\d+):\d+: ([A-Z]+\d+) (.+)$', re.MULTILINE)
    for match in pattern.finditer(content):
        issues.append(
            Issue(
                file=match.group(1),
                line=int(match.group(2)),
                message=f'{match.group(3)} {match.group(4)}',
                category='lint_error',
                severity='error',
            )
        )

    status = 'FAILURE' if issues else 'SUCCESS'
    return issues, None, status


def _parse_pytest(log_file: str) -> tuple[list[Issue], UnitTestSummary | None, str]:
    """Parse pytest test output."""
    content = Path(log_file).read_text(encoding='utf-8', errors='replace')
    issues: list[Issue] = []

    pattern = re.compile(r'^FAILED (.+\.py)::(\S+)(?: - (.+))?$', re.MULTILINE)
    for match in pattern.finditer(content):
        message = match.group(3) if match.group(3) else f'Test {match.group(2)} failed'
        issues.append(
            Issue(
                file=match.group(1),
                line=-1,  # pytest doesn't give line numbers in summary
                message=message,
                category='test_failure',
                severity='error',
            )
        )

    test_summary = extract_test_summary(
        content,
        r'(\d+) passed(?:.*?(\d+) failed)?(?:.*?(\d+) skipped)?',
        group_map={'passed': 1, 'failed': 2, 'skipped': 3},
    )

    status = 'FAILURE' if issues else 'SUCCESS'
    return issues, test_summary, status


# =============================================================================
# Content detection functions
# =============================================================================


def _has_mypy_output(content: str) -> bool:
    return bool(re.search(r'\.py:\d+: error:', content))


def _has_ruff_output(content: str) -> bool:
    return bool(re.search(r'\.py:\d+:\d+: [A-Z]+\d+', content))


def _has_pytest_output(content: str) -> bool:
    return 'FAILED ' in content or ' passed' in content


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


def parse_log(log_file: str) -> tuple[list[Issue], UnitTestSummary | None, str]:
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

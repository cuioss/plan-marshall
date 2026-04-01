#!/usr/bin/env python3
"""Parse functionality for Python build output.

Handles output from mypy, ruff, and pytest.

Usage (internal):
    from _python_cmd_parse import parse_python_log
"""

import re
from pathlib import Path

from _build_parse import Issue, UnitTestSummary


def parse_python_log(log_file: str) -> tuple[list[Issue], UnitTestSummary | None, str]:
    """Parse Python build log for errors.

    Handles output from:
    - mypy: file.py:line: error: message
    - ruff: file.py:line:col: CODE message
    - pytest: FAILED test_file.py::test_name - ...

    Args:
        log_file: Path to the log file.

    Returns:
        Tuple of (issues, test_summary, build_status)
    """
    issues: list[Issue] = []
    test_summary: UnitTestSummary | None = None
    build_status = 'FAILURE'

    try:
        content = Path(log_file).read_text(encoding='utf-8', errors='replace')
    except OSError:
        return issues, test_summary, build_status

    # Parse mypy errors: file.py:line: error: message
    mypy_pattern = re.compile(r'^(.+\.py):(\d+): error: (.+)$', re.MULTILINE)
    for match in mypy_pattern.finditer(content):
        issues.append(
            Issue(
                file=match.group(1),
                line=int(match.group(2)),
                message=match.group(3),
                category='type_error',
                severity='error',
            )
        )

    # Parse ruff errors: file.py:line:col: CODE message
    ruff_pattern = re.compile(r'^(.+\.py):(\d+):\d+: ([A-Z]+\d+) (.+)$', re.MULTILINE)
    for match in ruff_pattern.finditer(content):
        issues.append(
            Issue(
                file=match.group(1),
                line=int(match.group(2)),
                message=f'{match.group(3)} {match.group(4)}',
                category='lint_error',
                severity='error',
            )
        )

    # Parse pytest failures: FAILED test_file.py::test_name - message
    pytest_pattern = re.compile(r'^FAILED (.+\.py)::(\S+)(?: - (.+))?$', re.MULTILINE)
    for match in pytest_pattern.finditer(content):
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

    # Parse pytest summary: X passed, Y failed, Z skipped
    summary_pattern = re.compile(r'(\d+) passed(?:.*?(\d+) failed)?(?:.*?(\d+) skipped)?')
    summary_match = summary_pattern.search(content)
    if summary_match:
        passed = int(summary_match.group(1))
        failed = int(summary_match.group(2)) if summary_match.group(2) else 0
        skipped = int(summary_match.group(3)) if summary_match.group(3) else 0
        total = passed + failed + skipped
        test_summary = UnitTestSummary(passed=passed, failed=failed, skipped=skipped, total=total)

    return issues, test_summary, build_status

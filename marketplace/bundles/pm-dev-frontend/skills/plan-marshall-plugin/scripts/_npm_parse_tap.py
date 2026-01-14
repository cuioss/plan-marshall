#!/usr/bin/env python3
"""TAP (Test Anything Protocol) output parser for npm test output.

Implements BuildParser protocol for Node.js TAP test results.

Usage:
    from npm_parse_tap import parse_log

    issues, test_summary, build_status = parse_log("path/to/test.log")
"""

import re
from pathlib import Path

# Cross-skill imports (PYTHONPATH set by executor)
from _build_parse import SEVERITY_ERROR, Issue, UnitTestSummary  # type: ignore[import-not-found]

# TAP summary patterns
TESTS_PATTERN = re.compile(r'^#\s*tests\s+(\d+)', re.MULTILINE)
PASS_PATTERN = re.compile(r'^#\s*pass\s+(\d+)', re.MULTILINE)
FAIL_PATTERN = re.compile(r'^#\s*fail\s+(\d+)', re.MULTILINE)
SKIPPED_PATTERN = re.compile(r'^#\s*skipped\s+(\d+)', re.MULTILINE)

# TAP failure pattern: "not ok N - test name"
NOT_OK_PATTERN = re.compile(r'^\s*not ok\s+\d+\s*-\s*(.+)$', re.MULTILINE)


def parse_log(log_file: str | Path) -> tuple[list[Issue], UnitTestSummary | None, str]:
    """Parse TAP test log file.

    Implements BuildParser protocol for TAP test results.

    Args:
        log_file: Path to the TAP test log file.

    Returns:
        Tuple of (issues, test_summary, build_status):
        - issues: list[Issue] - all test failures found
        - test_summary: UnitTestSummary with test counts
        - build_status: "SUCCESS" | "FAILURE"

    Raises:
        FileNotFoundError: If log file doesn't exist.
    """
    path = Path(log_file)
    content = path.read_text(encoding='utf-8', errors='replace')

    issues = _extract_issues(content)
    test_summary = _extract_test_summary(content)
    build_status = 'FAILURE' if issues else 'SUCCESS'

    return issues, test_summary, build_status


def _extract_issues(content: str) -> list[Issue]:
    """Extract TAP test failures from log content.

    Args:
        content: Log file content.

    Returns:
        List of Issue dataclasses with test failures.
    """
    issues = []
    lines = content.split('\n')
    i = 0

    while i < len(lines):
        line = lines[i]
        not_ok_match = NOT_OK_PATTERN.match(line)

        if not_ok_match:
            test_name = not_ok_match.group(1).strip()
            error_msg = None
            location = None
            stack_trace = None
            stack_lines = []

            # Look for YAML block after "not ok" line
            i += 1
            in_yaml_block = False
            in_stack = False

            while i < len(lines):
                yaml_line = lines[i]
                stripped = yaml_line.strip()

                if stripped == '---':
                    in_yaml_block = True
                    i += 1
                    continue
                elif stripped == '...':
                    break
                elif in_yaml_block:
                    if stripped.startswith('error:'):
                        error_msg = stripped[6:].strip().strip('\'"')
                    elif stripped.startswith('location:'):
                        location = stripped[9:].strip().strip('\'"')
                    elif stripped.startswith('stack:'):
                        in_stack = True
                        # Check if value is on same line
                        stack_val = stripped[6:].strip()
                        if stack_val and stack_val != '|':
                            stack_lines.append(stack_val)
                    elif in_stack and yaml_line.startswith('        '):
                        stack_lines.append(stripped)
                    elif not yaml_line.startswith(' '):
                        break
                else:
                    break
                i += 1

            # Build stack trace
            if stack_lines:
                stack_trace = '\n'.join(stack_lines)

            # Extract file and line from location
            file_path = None
            line_num = None
            if location:
                loc_match = re.match(r'(.+):(\d+):\d+', location)
                if loc_match:
                    file_path = loc_match.group(1)
                    line_num = int(loc_match.group(2))

            message = error_msg if error_msg else test_name

            issues.append(
                Issue(
                    file=file_path,
                    line=line_num,
                    message=message,
                    severity=SEVERITY_ERROR,
                    category='test_failure',
                    stack_trace=stack_trace,
                )
            )
        else:
            i += 1

    return issues


def _extract_test_summary(content: str) -> UnitTestSummary | None:
    """Extract TAP test summary from log content.

    Args:
        content: Log file content.

    Returns:
        UnitTestSummary dataclass if found, None otherwise.
    """
    tests_match = TESTS_PATTERN.search(content)
    if not tests_match:
        return None

    total = int(tests_match.group(1))

    pass_match = PASS_PATTERN.search(content)
    passed = int(pass_match.group(1)) if pass_match else 0

    fail_match = FAIL_PATTERN.search(content)
    failed = int(fail_match.group(1)) if fail_match else 0

    skipped_match = SKIPPED_PATTERN.search(content)
    skipped = int(skipped_match.group(1)) if skipped_match else 0

    return UnitTestSummary(
        passed=passed,
        failed=failed,
        skipped=skipped,
        total=total,
    )

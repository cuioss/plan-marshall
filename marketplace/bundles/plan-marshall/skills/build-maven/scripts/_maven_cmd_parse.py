#!/usr/bin/env python3
"""Parse subcommand for Maven build output.

Implements BuildParser protocol for unified build log parsing.
Internal module - use maven.py CLI entry point instead.

Usage (internal):
    from _maven_cmd_parse import parse_log

    issues, test_summary, build_status = parse_log("path/to/build.log")
"""

import json
import re
from pathlib import Path

# Direct imports - executor sets up PYTHONPATH for cross-skill imports
from _build_parse import SEVERITY_ERROR, SEVERITY_WARNING, Issue, UnitTestSummary
from plan_logging import log_entry


def detect_build_status(content: str) -> str:
    """Detect overall build status from log content."""
    if 'BUILD SUCCESS' in content:
        return 'SUCCESS'
    if 'BUILD FAILURE' in content:
        return 'FAILURE'
    if re.search(r'^\[ERROR\]', content, re.MULTILINE):
        return 'FAILURE'
    return 'SUCCESS'


def extract_duration(content: str) -> int | None:
    """Extract total build time in milliseconds."""
    match = re.search(r'Total time:\s+([\d.]+)\s+s', content)
    if match:
        return int(float(match.group(1)) * 1000)
    match = re.search(r'Total time:\s+(\d+):(\d+)\s+min', content)
    if match:
        return (int(match.group(1)) * 60 + int(match.group(2))) * 1000
    return None


def extract_test_summary(content: str) -> dict:
    """Extract test execution summary."""
    pattern = r'Tests run:\s*(\d+),\s*Failures:\s*(\d+),\s*Errors:\s*(\d+),\s*Skipped:\s*(\d+)'
    matches = list(re.finditer(pattern, content))
    if matches:
        m = matches[-1]
        return {
            'tests_run': int(m.group(1)),
            'failures': int(m.group(2)),
            'errors': int(m.group(3)),
            'skipped': int(m.group(4)),
        }
    return {'tests_run': 0, 'failures': 0, 'errors': 0, 'skipped': 0}


def categorize_issue(message: str) -> str:
    """Categorize an issue based on its message content."""
    lower_msg = message.lower()
    if any(
        p in lower_msg
        for p in [
            'cannot find symbol',
            'incompatible types',
            'illegal start',
            'class, interface, or enum expected',
            'unreported exception',
            'method does not override',
            'not a statement',
            'package does not exist',
            'cannot be applied',
        ]
    ):
        return 'compilation_error'
    if any(p in lower_msg for p in ['tests run:', 'failure!', 'test failure', 'assertionfailed', 'expected:']):
        return 'test_failure'
    if any(
        p in lower_msg
        for p in [
            'could not resolve dependencies',
            'could not find artifact',
            'missing, no dependency',
            'artifact not found',
            'non-resolvable',
        ]
    ):
        return 'dependency_error'
    if any(p in lower_msg for p in ['javadoc', 'no @param', 'no @return', '@param name', 'missing @']):
        return 'javadoc_warning'
    if '[deprecation]' in lower_msg or 'has been deprecated' in lower_msg:
        return 'deprecation_warning'
    if '[unchecked]' in lower_msg or 'unchecked conversion' in lower_msg:
        return 'unchecked_warning'
    if any(p in lower_msg for p in ['org.openrewrite', 'rewrite-maven-plugin', 'rewrite:']):
        return 'openrewrite_info'
    return 'other'


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


def extract_issues(content: str, include_warnings: bool = True) -> list:
    """Extract all issues from Maven output."""
    issues = []
    for line_num, line in enumerate(content.split('\n'), 1):
        severity = None
        if '[ERROR]' in line:
            severity = 'ERROR'
        elif include_warnings and '[WARNING]' in line:
            severity = 'WARNING'
        if severity:
            message = re.sub(r'^\[(INFO|ERROR|WARNING)\]\s*', '', line.strip())
            if not message or message.startswith('->') or message.startswith('at '):
                continue
            location = parse_file_location(line)
            issues.append(
                {
                    'type': categorize_issue(message),
                    'file': location.get('file'),
                    'line': location.get('line'),
                    'column': location.get('column'),
                    'message': message[:500],
                    'severity': severity,
                    'log_line': line_num,
                }
            )
    return issues


def generate_summary(issues: list) -> dict:
    """Generate issue summary by category."""
    summary = {
        'compilation_errors': 0,
        'test_failures': 0,
        'javadoc_warnings': 0,
        'deprecation_warnings': 0,
        'unchecked_warnings': 0,
        'dependency_errors': 0,
        'openrewrite_info': 0,
        'other_warnings': 0,
        'other_errors': 0,
        'total_issues': len(issues),
    }
    for issue in issues:
        t, s = issue['type'], issue['severity']
        if t == 'compilation_error':
            summary['compilation_errors'] += 1
        elif t == 'test_failure':
            summary['test_failures'] += 1
        elif t == 'javadoc_warning':
            summary['javadoc_warnings'] += 1
        elif t == 'deprecation_warning':
            summary['deprecation_warnings'] += 1
        elif t == 'unchecked_warning':
            summary['unchecked_warnings'] += 1
        elif t == 'dependency_error':
            summary['dependency_errors'] += 1
        elif t == 'openrewrite_info':
            summary['openrewrite_info'] += 1
        elif s == 'ERROR':
            summary['other_errors'] += 1
        else:
            summary['other_warnings'] += 1
    return summary


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
    path = Path(log_file)
    content = path.read_text(encoding='utf-8', errors='replace')

    issues = _extract_issues_as_dataclass(content)
    test_summary = _extract_test_summary_as_dataclass(content)
    build_status = detect_build_status(content)

    return issues, test_summary, build_status


def _extract_issues_as_dataclass(content: str) -> list[Issue]:
    """Extract all issues from Maven output as Issue dataclasses.

    Args:
        content: Maven log file content.

    Returns:
        List of Issue dataclasses with severity, file, line, message, category.
    """
    issues = []
    for line in content.split('\n'):
        severity = None
        if '[ERROR]' in line:
            severity = SEVERITY_ERROR
        elif '[WARNING]' in line:
            severity = SEVERITY_WARNING

        if severity:
            message = re.sub(r'^\[(INFO|ERROR|WARNING)\]\s*', '', line.strip())
            # Skip empty messages, continuation lines, stack traces
            if not message or message.startswith('->') or message.startswith('at '):
                continue

            location = parse_file_location(line)
            category = categorize_issue(message)

            issues.append(
                Issue(
                    file=location.get('file'),
                    line=location.get('line'),
                    message=message[:500],
                    severity=severity,
                    category=category,
                )
            )

    return issues


def _extract_test_summary_as_dataclass(content: str) -> UnitTestSummary | None:
    """Extract test execution summary as UnitTestSummary dataclass.

    Args:
        content: Maven log file content.

    Returns:
        UnitTestSummary dataclass if tests were run, None otherwise.

    Note:
        Maven reports "Failures" (assertion failures) and "Errors" (exceptions)
        separately. This combines them into the "failed" count per UnitTestSummary spec.
    """
    pattern = r'Tests run:\s*(\d+),\s*Failures:\s*(\d+),\s*Errors:\s*(\d+),\s*Skipped:\s*(\d+)'
    matches = list(re.finditer(pattern, content))

    if not matches:
        return None

    # Use the last match (final summary)
    m = matches[-1]
    tests_run = int(m.group(1))
    failures = int(m.group(2))
    errors = int(m.group(3))
    skipped = int(m.group(4))

    # Maven distinguishes failures from errors; we combine them
    failed = failures + errors
    passed = tests_run - failed - skipped

    return UnitTestSummary(
        passed=passed,
        failed=failed,
        skipped=skipped,
        total=tests_run,
    )


def cmd_parse(args):
    """Handle parse subcommand."""
    path = Path(args.log)
    if not path.exists():
        log_entry('script', 'global', 'ERROR', f'[MAVEN-PARSE] Log file not found: {args.log}')
        print(json.dumps({'status': 'error', 'error': f'Log file not found: {args.log}'}, indent=2))
        return 1
    try:
        content = path.read_text(encoding='utf-8', errors='replace')
    except Exception as e:
        log_entry('script', 'global', 'ERROR', f'[MAVEN-PARSE] Failed to read log file: {e}')
        print(json.dumps({'status': 'error', 'error': f'Failed to read log file: {str(e)}'}, indent=2))
        return 1

    build_status = detect_build_status(content)
    duration = extract_duration(content)
    test_summary = extract_test_summary(content)
    issues = extract_issues(content, args.mode not in ['errors'])
    if args.mode == 'no-openrewrite':
        issues = [i for i in issues if i['type'] != 'openrewrite_info']
    summary = generate_summary(issues)

    log_entry(
        'script',
        'global',
        'INFO',
        f'[MAVEN-PARSE] Parsed log: status={build_status}, issues={len(issues)}, tests_run={test_summary["tests_run"]}',
    )

    result = {
        'status': 'success' if build_status == 'SUCCESS' else 'error',
        'data': {'build_status': build_status, 'issues': issues, 'summary': summary},
        'metrics': {
            'duration_ms': duration,
            'tests_run': test_summary['tests_run'],
            'tests_failed': test_summary['failures'] + test_summary['errors'],
        },
    }
    print(json.dumps(result, indent=2))
    return 0

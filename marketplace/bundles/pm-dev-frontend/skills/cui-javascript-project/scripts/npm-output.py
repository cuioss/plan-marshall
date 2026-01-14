#!/usr/bin/env python3
"""
npm build output analysis tool.

Subcommands:
    parse  - Parse npm/npx build output logs and categorize issues

Usage:
    npm-output.py parse --log target/npm-output-2024-01-15.log
    npm-output.py parse --log build.log --mode structured
"""

import argparse
import json
import os
import re
import sys

EXIT_SUCCESS = 0
EXIT_ERROR = 1
EXIT_FAILURE = 2


# =============================================================================
# PARSE SUBCOMMAND
# =============================================================================

# Error patterns by category
ERROR_PATTERNS = {
    'compilation_error': [
        re.compile(r'SyntaxError:\s*(.+)', re.IGNORECASE),
        re.compile(r'TypeError:\s*(.+)', re.IGNORECASE),
        re.compile(r'ReferenceError:\s*(.+)', re.IGNORECASE),
        re.compile(r'error TS\d+:\s*(.+)', re.IGNORECASE),  # TypeScript
    ],
    'test_failure': [
        re.compile(r'✘|✖'),  # Jest/Vitest failure markers
        re.compile(r'FAIL\s+(.+)', re.IGNORECASE),
        re.compile(r'Expected.*to.*but.*received', re.IGNORECASE),
        re.compile(r'(\d+)\s+(?:test|tests)\s+failed', re.IGNORECASE),
        re.compile(r'Test\s+Suites?:\s+\d+\s+failed', re.IGNORECASE),
    ],
    'lint_error': [
        re.compile(r'eslint', re.IGNORECASE),
        re.compile(r'stylelint', re.IGNORECASE),
        re.compile(r'prettier', re.IGNORECASE),
        re.compile(r'(\d+):(\d+)\s+(error|warning)\s+(.+?)\s+(\S+)$'),  # ESLint format
    ],
    'dependency_error': [
        re.compile(r'Cannot find module\s+[\'"]([^\'"]+)[\'"]', re.IGNORECASE),
        re.compile(r'Module not found:\s*(.+)', re.IGNORECASE),
        re.compile(r'npm ERR! 404\s*(.+)', re.IGNORECASE),
        re.compile(r'ERESOLVE\s+(.+)', re.IGNORECASE),
    ],
    'playwright_error': [
        re.compile(r'playwright', re.IGNORECASE),
        re.compile(r'browser.*error', re.IGNORECASE),
        re.compile(r'page\.goto:\s*Timeout', re.IGNORECASE),
        re.compile(r'locator\.\w+:\s*Timeout', re.IGNORECASE),
        re.compile(r'selector.*not found', re.IGNORECASE),
    ],
}

# General error/warning patterns
GENERAL_ERROR_PATTERN = re.compile(r'(?:Error|ERROR|error)[:\s]+(.+)', re.IGNORECASE)
GENERAL_WARNING_PATTERN = re.compile(r'(?:Warning|WARN|warning)[:\s]+(.+)', re.IGNORECASE)
NPM_ERROR_PATTERN = re.compile(r'npm ERR!\s*(.+)')

# File location patterns
FILE_LOCATION_PATTERNS = [
    re.compile(r'([^\s:]+\.[jt]sx?):(\d+):(\d+)'),
    re.compile(r'@\s+([^\s]+\.[jt]sx?)\s+(\d+):(\d+)'),
    re.compile(r'\(([^\s:]+\.[jt]sx?):(\d+):(\d+)\)'),
    re.compile(r'(tests?/[^\s:]+\.[jt]sx?):(\d+):(\d+)'),
]


def extract_file_location(line: str) -> tuple:
    """Extract file path, line, and column from an error line."""
    for pattern in FILE_LOCATION_PATTERNS:
        match = pattern.search(line)
        if match:
            groups = match.groups()
            file_path = groups[0]
            line_num = int(groups[1]) if len(groups) > 1 else None
            column = int(groups[2]) if len(groups) > 2 else None
            return file_path, line_num, column
    return None, None, None


def categorize_line(line: str) -> tuple:
    """Categorize a line and return (category, severity)."""
    for category, patterns in ERROR_PATTERNS.items():
        for pattern in patterns:
            if pattern.search(line):
                if category == 'lint_error':
                    if 'warning' in line.lower():
                        return category, 'WARNING'
                    return category, 'ERROR'
                return category, 'ERROR'

    if NPM_ERROR_PATTERN.search(line):
        return 'npm_error', 'ERROR'
    if GENERAL_ERROR_PATTERN.search(line):
        return 'other', 'ERROR'
    if GENERAL_WARNING_PATTERN.search(line):
        return 'other', 'WARNING'

    return None, None


def determine_build_status(lines: list, exit_code: int | None = None) -> str:
    """Determine overall build status from output."""
    for line in lines:
        if 'npm ERR!' in line:
            return 'FAILURE'
        if re.search(r'Test Suites?:\s+\d+\s+failed', line, re.IGNORECASE):
            return 'FAILURE'
        if '✘' in line or '✖' in line:
            return 'FAILURE'
        if re.search(r'FAIL\s+', line):
            return 'FAILURE'

    if exit_code is not None and exit_code != 0:
        return 'FAILURE'

    return 'SUCCESS'


def parse_npm_output(log_path: str, mode: str) -> dict:
    """Parse npm output log file."""
    if not os.path.exists(log_path):
        return {
            'status': 'error',
            'error': 'LOG_NOT_FOUND',
            'message': f'Log file not found: {log_path}'
        }

    try:
        with open(log_path, encoding='utf-8', errors='replace') as f:
            content = f.read()
    except Exception as e:
        return {
            'status': 'error',
            'error': 'READ_ERROR',
            'message': f'Failed to read log file: {e}'
        }

    lines = content.split('\n')
    build_status = determine_build_status(lines, None)

    issues = []
    errors_only = []
    warnings = []

    for line_num, line in enumerate(lines, 1):
        line = line.strip()
        if not line:
            continue

        category, severity = categorize_line(line)

        if category:
            file_path, file_line, column = extract_file_location(line)

            issue = {
                'type': category,
                'file': file_path,
                'line': file_line,
                'column': column,
                'message': line,
                'severity': severity,
                'log_line': line_num
            }

            issues.append(issue)

            if severity == 'ERROR':
                errors_only.append(f'{line_num}: {line}')
            else:
                warnings.append(f'{line_num}: {line}')

    summary = {
        'compilation_errors': sum(1 for i in issues if i['type'] == 'compilation_error'),
        'test_failures': sum(1 for i in issues if i['type'] == 'test_failure'),
        'lint_errors': sum(1 for i in issues if i['type'] == 'lint_error' and i['severity'] == 'ERROR'),
        'lint_warnings': sum(1 for i in issues if i['type'] == 'lint_error' and i['severity'] == 'WARNING'),
        'dependency_errors': sum(1 for i in issues if i['type'] == 'dependency_error'),
        'playwright_errors': sum(1 for i in issues if i['type'] == 'playwright_error'),
        'npm_errors': sum(1 for i in issues if i['type'] == 'npm_error'),
        'other_errors': sum(1 for i in issues if i['type'] == 'other' and i['severity'] == 'ERROR'),
        'other_warnings': sum(1 for i in issues if i['type'] == 'other' and i['severity'] == 'WARNING'),
        'total_errors': sum(1 for i in issues if i['severity'] == 'ERROR'),
        'total_warnings': sum(1 for i in issues if i['severity'] == 'WARNING'),
        'total_issues': len(issues)
    }

    if mode == 'structured':
        return {
            'status': build_status.lower(),
            'data': {
                'output_file': log_path,
                'issues': issues
            },
            'metrics': summary
        }
    elif mode == 'errors':
        return {
            'status': build_status.lower(),
            'data': {
                'output_file': log_path,
                'errors': errors_only
            },
            'metrics': {
                'total_errors': summary['total_errors']
            }
        }
    else:  # default
        return {
            'status': build_status.lower(),
            'data': {
                'output_file': log_path,
                'errors': errors_only,
                'warnings': warnings
            },
            'metrics': {
                'total_errors': summary['total_errors'],
                'total_warnings': summary['total_warnings']
            }
        }


def cmd_parse(args) -> int:
    """Handle parse subcommand."""
    result = parse_npm_output(args.log, args.mode)
    print(json.dumps(result, indent=2))

    if result.get('status') == 'error':
        return EXIT_ERROR
    elif result.get('status') == 'failure':
        return EXIT_FAILURE
    return EXIT_SUCCESS


# =============================================================================
# MAIN
# =============================================================================

def main() -> int:
    parser = argparse.ArgumentParser(
        description="npm build output analysis tool",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # parse subcommand
    parse_parser = subparsers.add_parser("parse", help="Parse npm/npx build output logs and categorize issues")
    parse_parser.add_argument("--log", required=True, help="Path to npm output log file")
    parse_parser.add_argument("--mode", choices=['default', 'errors', 'structured'], default='default',
                              help="Output mode: default, errors, or structured")
    parse_parser.set_defaults(func=cmd_parse)

    args = parser.parse_args()
    result: int = args.func(args)
    return result


if __name__ == "__main__":
    sys.exit(main())

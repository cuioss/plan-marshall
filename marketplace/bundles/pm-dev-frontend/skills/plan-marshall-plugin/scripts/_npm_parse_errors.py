#!/usr/bin/env python3
"""npm error parser for npm install/dependency errors.

Implements BuildParser protocol for npm command errors (ERESOLVE, E404, etc.).

Usage:
    from npm_parse_errors import parse_log

    issues, test_summary, build_status = parse_log("path/to/npm-error.log")
"""

import re
from pathlib import Path

# Cross-skill imports (PYTHONPATH set by executor)
from _build_parse import SEVERITY_ERROR, Issue, UnitTestSummary  # type: ignore[import-not-found]

# npm error code pattern: "npm ERR! code XXXXX"
NPM_ERROR_CODE_PATTERN = re.compile(r'^npm ERR! code (\S+)', re.MULTILINE)

# npm error message patterns for specific error types
ERESOLVE_PATTERN = re.compile(r'npm ERR! ERESOLVE unable to resolve dependency tree', re.MULTILINE)
ERESOLVE_CONFLICT_PATTERN = re.compile(
    r'npm ERR! Could not resolve dependency:\s*\n.*peer\s+(\S+)\s+from\s+(\S+)', re.MULTILINE | re.DOTALL
)

E404_PATTERN = re.compile(r"npm ERR! 404\s+'([^']+)'\s+is not in this registry", re.MULTILINE)

# Generic npm ERR! line pattern
NPM_ERR_LINE_PATTERN = re.compile(r'^npm ERR! (.+)$', re.MULTILINE)


def parse_log(log_file: str | Path) -> tuple[list[Issue], UnitTestSummary | None, str]:
    """Parse npm error log file.

    Implements BuildParser protocol for npm command errors.

    Args:
        log_file: Path to the npm error log file.

    Returns:
        Tuple of (issues, test_summary, build_status):
        - issues: list[Issue] - all npm errors found
        - test_summary: None (npm errors don't have test results)
        - build_status: "SUCCESS" | "FAILURE"

    Raises:
        FileNotFoundError: If log file doesn't exist.
    """
    path = Path(log_file)
    content = path.read_text(encoding='utf-8', errors='replace')

    issues = _extract_issues(content)
    build_status = 'FAILURE' if issues else 'SUCCESS'

    return issues, None, build_status


def _extract_issues(content: str) -> list[Issue]:
    """Extract npm errors from log content.

    Args:
        content: Log file content.

    Returns:
        List of Issue dataclasses with npm errors.
    """
    issues: list[Issue] = []

    # Get error code if present
    code_match = NPM_ERROR_CODE_PATTERN.search(content)
    error_code = code_match.group(1) if code_match else None

    if not error_code:
        return issues

    # Handle specific error types
    if error_code == 'ERESOLVE':
        issue = _parse_eresolve_error(content)
        if issue:
            issues.append(issue)
    elif error_code == 'E404':
        issue = _parse_e404_error(content)
        if issue:
            issues.append(issue)
    else:
        # Generic npm error
        issue = _parse_generic_error(content, error_code)
        if issue:
            issues.append(issue)

    return issues


def _parse_eresolve_error(content: str) -> Issue | None:
    """Parse ERESOLVE dependency resolution error.

    Args:
        content: Log file content.

    Returns:
        Issue dataclass or None.
    """
    # Try to extract specific conflict info
    conflict_match = ERESOLVE_CONFLICT_PATTERN.search(content)
    if conflict_match:
        peer_dep = conflict_match.group(1)
        from_pkg = conflict_match.group(2)
        message = f'ERESOLVE: Could not resolve peer dependency {peer_dep} from {from_pkg}'
    else:
        message = 'ERESOLVE: Unable to resolve dependency tree'

    return Issue(
        file='package.json',
        line=None,
        message=message,
        severity=SEVERITY_ERROR,
        category='npm_dependency',
    )


def _parse_e404_error(content: str) -> Issue | None:
    """Parse E404 package not found error.

    Args:
        content: Log file content.

    Returns:
        Issue dataclass or None.
    """
    match = E404_PATTERN.search(content)
    if match:
        package = match.group(1)
        message = f"E404: Package '{package}' not found in registry"
    else:
        message = 'E404: Package not found'

    return Issue(
        file='package.json',
        line=None,
        message=message,
        severity=SEVERITY_ERROR,
        category='npm_error',
    )


def _parse_generic_error(content: str, error_code: str) -> Issue | None:
    """Parse generic npm error.

    Args:
        content: Log file content.
        error_code: The npm error code.

    Returns:
        Issue dataclass or None.
    """
    # Get first meaningful error line after the code line
    lines = content.split('\n')
    message_lines = []

    for line in lines:
        if line.startswith('npm ERR! '):
            err_content = line[9:].strip()
            # Skip empty lines and boilerplate
            if err_content and not err_content.startswith('A complete log'):
                message_lines.append(err_content)
                if len(message_lines) >= 3:
                    break

    if not message_lines:
        message = f'{error_code}: npm command failed'
    else:
        message = f'{error_code}: {message_lines[0]}'

    return Issue(
        file=None,
        line=None,
        message=message,
        severity=SEVERITY_ERROR,
        category='npm_error',
    )

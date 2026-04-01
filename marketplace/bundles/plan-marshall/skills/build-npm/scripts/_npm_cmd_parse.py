#!/usr/bin/env python3
"""Parse functionality for npm build output.

Implements multi-parser architecture for detecting and parsing output from
npm ecosystem tools (TypeScript, Jest, ESLint, TAP, npm errors).

Usage (internal):
    from _npm_cmd_parse import parse_with_detector, detect_tool_type
"""

from collections.abc import Callable
from pathlib import Path

from _build_parse import Issue, UnitTestSummary
from _npm_parse_errors import parse_log as parse_npm_errors
from _npm_parse_eslint import parse_log as parse_eslint
from _npm_parse_jest import parse_log as parse_jest
from _npm_parse_tap import parse_log as parse_tap
from _npm_parse_typescript import parse_log as parse_typescript


def detect_tool_type(content: str, command: str) -> str:
    """Detect which tool produced the output.

    Args:
        content: Log file content.
        command: Original command string.

    Returns:
        Tool type: "typescript", "jest", "tap", "eslint", "npm_error", or "generic"
    """
    command_lower = command.lower()

    # Check command first
    if 'tsc' in command_lower or 'typescript' in command_lower:
        return 'typescript'
    if 'jest' in command_lower:
        return 'jest'
    if 'eslint' in command_lower:
        return 'eslint'

    # Check content patterns
    if 'npm ERR!' in content:
        return 'npm_error'
    if 'TAP version' in content or '# tests' in content:
        return 'tap'
    if 'error TS' in content or '): error TS' in content or ': error TS' in content:
        return 'typescript'
    if 'FAIL ' in content and ('Tests:' in content or 'Test Suites:' in content):
        return 'jest'
    if 'problem' in content.lower() and 'error' in content.lower():
        # Check for ESLint-style output
        if any(line.strip().endswith(')') for line in content.split('\n') if 'error' in line.lower()):
            return 'eslint'

    return 'generic'


def parse_with_detector(log_file: str, command: str) -> tuple[list[Issue], UnitTestSummary | None, str]:
    """Parse log file using appropriate tool-specific parser.

    Args:
        log_file: Path to the log file.
        command: Original command string.

    Returns:
        Tuple of (issues, test_summary, build_status)
    """
    content = Path(log_file).read_text(encoding='utf-8', errors='replace')
    tool_type = detect_tool_type(content, command)

    try:
        if tool_type == 'typescript':
            return parse_typescript(log_file)
        elif tool_type == 'jest':
            return parse_jest(log_file)
        elif tool_type == 'tap':
            return parse_tap(log_file)
        elif tool_type == 'eslint':
            return parse_eslint(log_file)
        elif tool_type == 'npm_error':
            return parse_npm_errors(log_file)
        else:
            # Generic fallback - try each parser and use first with results
            parsers: list[Callable[[str], tuple[list[Issue], UnitTestSummary | None, str]]] = [
                parse_npm_errors,
                parse_typescript,
                parse_eslint,
                parse_jest,
                parse_tap,
            ]
            for parser in parsers:
                try:
                    issues, test_summary, build_status = parser(log_file)
                    if issues:
                        return issues, test_summary, build_status
                except Exception:
                    continue
            return [], None, 'FAILURE'
    except Exception:
        return [], None, 'FAILURE'

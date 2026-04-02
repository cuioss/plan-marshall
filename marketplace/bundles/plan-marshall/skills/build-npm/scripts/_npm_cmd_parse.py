#!/usr/bin/env python3
"""Parse functionality for npm build output.

Implements registry-based multi-parser architecture for detecting and parsing
output from npm ecosystem tools (TypeScript, Jest, ESLint, TAP, npm errors).

Usage (internal):
    from _npm_cmd_parse import parse_log, detect_tool_type
"""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

from _build_parse import Issue, UnitTestSummary
from _npm_parse_errors import parse_log as parse_npm_errors
from _npm_parse_eslint import parse_log as parse_eslint
from _npm_parse_jest import parse_log as parse_jest
from _npm_parse_tap import parse_log as parse_tap
from _npm_parse_typescript import parse_log as parse_typescript

ParserResult = tuple[list[Issue], UnitTestSummary | None, str]
ParserFn = Callable[[str], ParserResult]


class _DetectionRule(NamedTuple):
    """A rule that maps command/content patterns to a tool type."""
    tool: str
    command_patterns: tuple[str, ...]
    content_check: Callable[[str], bool] | None


def _has_npm_error(content: str) -> bool:
    return 'npm ERR!' in content


def _has_tap_markers(content: str) -> bool:
    return 'TAP version' in content or '# tests' in content


def _has_typescript_errors(content: str) -> bool:
    return 'error TS' in content or '): error TS' in content or ': error TS' in content


def _has_jest_output(content: str) -> bool:
    return 'FAIL ' in content and ('Tests:' in content or 'Test Suites:' in content)


def _has_eslint_output(content: str) -> bool:
    if 'problem' not in content.lower() or 'error' not in content.lower():
        return False
    return any(line.strip().endswith(')') for line in content.split('\n') if 'error' in line.lower())


# Detection rules checked in priority order.
# Command patterns are checked first (faster, more precise), then content checks.
_DETECTION_RULES: tuple[_DetectionRule, ...] = (
    _DetectionRule('typescript', ('tsc', 'typescript'), _has_typescript_errors),
    _DetectionRule('jest', ('jest',), _has_jest_output),
    _DetectionRule('eslint', ('eslint',), _has_eslint_output),
    _DetectionRule('npm_error', (), _has_npm_error),
    _DetectionRule('tap', (), _has_tap_markers),
)

# Maps tool type to parser function.
_PARSERS: dict[str, ParserFn] = {
    'typescript': parse_typescript,
    'jest': parse_jest,
    'tap': parse_tap,
    'eslint': parse_eslint,
    'npm_error': parse_npm_errors,
}


def detect_tool_type(content: str, command: str) -> str:
    """Detect which tool produced the output.

    Checks command string first (fast path), then falls back to content
    pattern matching. Rules are evaluated in priority order.

    Args:
        content: Log file content.
        command: Original command string.

    Returns:
        Tool type: "typescript", "jest", "tap", "eslint", "npm_error", or "generic"
    """
    command_lower = command.lower()

    # Phase 1: check command patterns
    for rule in _DETECTION_RULES:
        if any(pat in command_lower for pat in rule.command_patterns):
            return rule.tool

    # Phase 2: check content patterns
    for rule in _DETECTION_RULES:
        if rule.content_check is not None and rule.content_check(content):
            return rule.tool

    return 'generic'


def parse_log(log_file: str, command: str = '') -> ParserResult:
    """Parse log file using appropriate tool-specific parser.

    Args:
        log_file: Path to the log file.
        command: Original command string (used for tool type detection).

    Returns:
        Tuple of (issues, test_summary, build_status)
    """
    content = Path(log_file).read_text(encoding='utf-8', errors='replace')
    tool_type = detect_tool_type(content, command)

    if tool_type in _PARSERS:
        return _PARSERS[tool_type](log_file)

    # Generic fallback — try each parser and use first with results
    for parser in _PARSERS.values():
        try:
            issues, test_summary, build_status = parser(log_file)
            if issues:
                return issues, test_summary, build_status
        except (ValueError, KeyError, IndexError, AttributeError, OSError):
            continue
    return [], None, 'FAILURE'

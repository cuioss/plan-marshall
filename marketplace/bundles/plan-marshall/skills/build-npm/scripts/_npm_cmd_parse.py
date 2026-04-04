#!/usr/bin/env python3
"""Parse functionality for npm build output.

Implements registry-based multi-parser architecture for detecting and parsing
output from npm ecosystem tools (TypeScript, Jest, ESLint, TAP, npm errors).

Usage (internal):
    from _npm_cmd_parse import parse_log, detect_tool_type
"""

from __future__ import annotations

from pathlib import Path

from _build_parser_registry import DetectionRule, ParserRegistry
from _npm_parse_errors import parse_log as parse_npm_errors
from _npm_parse_eslint import parse_log as parse_eslint
from _npm_parse_jest import parse_log as parse_jest
from _npm_parse_tap import parse_log as parse_tap
from _npm_parse_typescript import parse_log as parse_typescript


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


# Registry with detection rules checked in priority order.
_REGISTRY = ParserRegistry(
    [
        DetectionRule('typescript', ('tsc', 'typescript'), _has_typescript_errors, parse_typescript),
        DetectionRule('jest', ('jest',), _has_jest_output, parse_jest),
        DetectionRule('eslint', ('eslint',), _has_eslint_output, parse_eslint),
        DetectionRule('npm_error', (), _has_npm_error, parse_npm_errors),
        DetectionRule('tap', (), _has_tap_markers, parse_tap),
    ]
)


def detect_tool_type(content: str, command: str) -> str:
    """Detect which tool produced the output (delegates to registry)."""
    return _REGISTRY.detect_tool_type(content, command)


def parse_log(log_file: str | Path, command: str = '') -> tuple:
    """Parse log file using appropriate tool-specific parser."""
    return _REGISTRY.parse(log_file, command)

#!/usr/bin/env python3
"""Shared parser registry for build output detection and routing.

Provides a registry-based architecture for detecting which tool produced
build output and routing to the appropriate parser. Originally developed
for npm's multi-parser system, now shared across all build skills.

Usage:
    from _build_parser_registry import ParserRegistry, DetectionRule

    registry = ParserRegistry([
        DetectionRule('typescript', ('tsc',), _has_typescript_errors, parse_typescript),
        DetectionRule('jest', ('jest',), _has_jest_output, parse_jest),
    ])

    issues, summary, status = registry.parse(log_file, command='npm run test')
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

logger = logging.getLogger(__name__)

from _build_parse import Issue, UnitTestSummary

ParserResult = tuple[list[Issue], UnitTestSummary | None, str]
ParserFn = Callable[[str], ParserResult]
ContentCheckFn = Callable[[str], bool]


class DetectionRule(NamedTuple):
    """A rule that maps command/content patterns to a tool type and parser.

    Attributes:
        tool: Tool identifier (e.g., 'typescript', 'jest', 'mypy').
        command_patterns: Substrings to check in the command string (fast path).
        content_check: Function to detect tool from log content, or None.
        parser: Parser function that processes the log file.
    """
    tool: str
    command_patterns: tuple[str, ...]
    content_check: ContentCheckFn | None
    parser: ParserFn


class ParserRegistry:
    """Registry-based multi-parser for build output.

    Detects which tool produced the output using a two-phase approach:
    1. Check command string for known patterns (fast path)
    2. Check content patterns (fallback)

    Then routes to the appropriate parser function.
    """

    def __init__(self, rules: list[DetectionRule] | tuple[DetectionRule, ...]):
        self._rules = rules

    def detect_tool_type(self, content: str, command: str) -> str:
        """Detect which tool produced the output.

        Args:
            content: Log file content.
            command: Original command string.

        Returns:
            Tool type string, or 'generic' if no match.
        """
        command_lower = command.lower()

        # Phase 1: check command patterns (fast path)
        for rule in self._rules:
            if any(pat in command_lower for pat in rule.command_patterns):
                return rule.tool

        # Phase 2: check content patterns
        for rule in self._rules:
            if rule.content_check is not None and rule.content_check(content):
                return rule.tool

        return 'generic'

    def parse(self, log_file: str | Path, command: str = '') -> ParserResult:
        """Parse log file using the appropriate tool-specific parser.

        Detects the tool type, then routes to the matching parser.
        Falls back to trying each parser in sequence if no match.

        Args:
            log_file: Path to the log file.
            command: Original command string (used for tool detection).

        Returns:
            Tuple of (issues, test_summary, build_status).
        """
        content = Path(log_file).read_text(encoding='utf-8', errors='replace')
        tool_type = self.detect_tool_type(content, command)

        # Direct match
        for rule in self._rules:
            if rule.tool == tool_type:
                return rule.parser(str(log_file))

        # Generic fallback: try each parser, use first with results
        for rule in self._rules:
            try:
                issues, test_summary, build_status = rule.parser(str(log_file))
                if issues:
                    return issues, test_summary, build_status
            except (ValueError, KeyError, IndexError, AttributeError, OSError) as e:
                logger.debug('Parser %s failed for %s: %s', rule.tool, log_file, e)
                continue

        return [], None, 'FAILURE'

    def parse_multi(self, log_file: str | Path) -> ParserResult:
        """Parse log file by running all matching parsers and combining results.

        Unlike parse() which routes to a single parser, this runs every parser
        whose content_check matches and merges their results. Useful when build
        output contains output from multiple tools (e.g., mypy + ruff + pytest
        in a single pyprojectx verify run).

        Args:
            log_file: Path to the log file.

        Returns:
            Tuple of (issues, test_summary, build_status).
        """
        try:
            content = Path(log_file).read_text(encoding='utf-8', errors='replace')
        except OSError as e:
            logger.warning('Failed to read log file %s: %s', log_file, e)
            return [], None, 'FAILURE'

        all_issues: list[Issue] = []
        test_summary: UnitTestSummary | None = None

        for rule in self._rules:
            if rule.content_check is not None and rule.content_check(content):
                issues, summary, _ = rule.parser(str(log_file))
                all_issues.extend(issues)
                if summary is not None:
                    test_summary = summary

        error_issues = [i for i in all_issues if i.severity == 'error']
        build_status = 'FAILURE' if error_issues else 'SUCCESS'

        return all_issues, test_summary, build_status

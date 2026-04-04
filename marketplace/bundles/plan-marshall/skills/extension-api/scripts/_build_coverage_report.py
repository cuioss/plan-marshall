#!/usr/bin/env python3
"""Shared coverage-report subcommand logic for all build skills.

Extracts the common cmd_coverage_report() flow that was duplicated across
build-maven, build-gradle, build-npm, and build-python. Each skill provides
its own search paths and error message; the logic is identical.

Use create_coverage_report_handler() to build a tool-specific handler from config.
"""

from __future__ import annotations

from collections.abc import Callable

from _coverage_parse import find_report, parse_coverage_report  # type: ignore[import-not-found]
from toon_parser import serialize_toon  # type: ignore[import-not-found]


def create_coverage_report_handler(
    search_paths: list[tuple[str, str]],
    not_found_message: str = 'No coverage report found. Run coverage build first.',
) -> Callable:
    """Factory: create a tool-specific coverage-report subcommand handler.

    Args:
        search_paths: Ordered list of (relative_path, format_hint) tuples.
        not_found_message: Error message when no report is found.

    Returns:
        A cmd_coverage_report(args) -> int function ready for argparse set_defaults.
    """

    def cmd_coverage_report(args) -> int:
        return cmd_coverage_report_base(args, search_paths, not_found_message)

    return cmd_coverage_report


def cmd_coverage_report_base(
    args,
    search_paths: list[tuple[str, str]],
    not_found_message: str = 'No coverage report found. Run coverage build first.',
) -> int:
    """Handle coverage-report subcommand with tool-specific search paths.

    Args:
        args: Parsed argparse namespace. Expects optional attributes:
            project_path (base path for search),
            report_path (explicit override), threshold (int, default 80).
        search_paths: Ordered list of (relative_path, format_hint) tuples.
        not_found_message: Error message when no report is found.

    Returns:
        Exit code: 0 if coverage meets threshold, 1 otherwise.
    """
    base_path = getattr(args, 'project_path', None)
    report_file, fmt = find_report(
        search_paths,
        base_path=base_path,
        explicit_path=getattr(args, 'report_path', None),
    )

    if not report_file:
        result = {
            'status': 'error',
            'error': 'report_not_found',
            'message': not_found_message,
            'searched': [p for p, _ in search_paths],
        }
        print(serialize_toon(result))
        return 1

    threshold = getattr(args, 'threshold', 80) or 80
    result = parse_coverage_report(report_file, fmt, threshold)
    print(serialize_toon(result))
    return 0 if result.get('passed', False) else 1

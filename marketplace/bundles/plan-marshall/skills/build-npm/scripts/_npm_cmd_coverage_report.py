#!/usr/bin/env python3
"""Coverage-report subcommand for npm — delegates to shared base."""

from _build_coverage_report import cmd_coverage_report_base  # type: ignore[import-not-found]

NPM_SEARCH_PATHS = [
    ('coverage/coverage-summary.json', 'jest_json'),
    ('coverage/lcov.info', 'lcov'),
    ('dist/coverage/coverage-summary.json', 'jest_json'),
]


def cmd_coverage_report(args) -> int:
    """Handle coverage-report subcommand."""
    return cmd_coverage_report_base(
        args, NPM_SEARCH_PATHS,
        not_found_message='No coverage report found. Run tests with coverage first.',
    )

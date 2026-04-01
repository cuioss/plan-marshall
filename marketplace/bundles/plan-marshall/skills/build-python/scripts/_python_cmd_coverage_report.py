#!/usr/bin/env python3
"""Coverage-report subcommand for Python — delegates to shared base."""

from _build_coverage_report import cmd_coverage_report_base  # type: ignore[import-not-found]

PYTHON_SEARCH_PATHS = [
    ('coverage.xml', 'cobertura'),
    ('htmlcov/coverage.xml', 'cobertura'),
]


def cmd_coverage_report(args) -> int:
    """Handle coverage-report subcommand."""
    return cmd_coverage_report_base(
        args, PYTHON_SEARCH_PATHS,
        not_found_message='No coverage.py XML report found. Run pytest with --cov --cov-report=xml first.',
    )

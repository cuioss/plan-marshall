#!/usr/bin/env python3
"""Coverage-report subcommand for Maven — delegates to shared base."""

from _build_coverage_report import cmd_coverage_report_base  # type: ignore[import-not-found]

JACOCO_SEARCH_PATHS = [
    ('target/site/jacoco/jacoco.xml', 'jacoco'),
    ('target/jacoco/report.xml', 'jacoco'),
    ('target/site/jacoco-aggregate/jacoco.xml', 'jacoco'),
]


def cmd_coverage_report(args) -> int:
    """Handle coverage-report subcommand."""
    return cmd_coverage_report_base(
        args, JACOCO_SEARCH_PATHS,
        not_found_message='No JaCoCo XML report found. Run coverage build first.',
    )

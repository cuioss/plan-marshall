#!/usr/bin/env python3
"""
Maven build operations - run, parse, search markers, check warnings, coverage report.

Usage:
    maven.py run --command-args <args> [options]
    maven.py parse --log <path> [--mode <mode>]
    maven.py search-markers --source-dir <dir>
    maven.py check-warnings --warnings <json> [--acceptable-warnings <json>]
    maven.py coverage-report [--project-path <path>] [--threshold <percent>]
    maven.py --help

Subcommands:
    run             Execute build and auto-parse on failure (primary API)
    parse           Parse Maven build output and categorize issues
    search-markers  Search for OpenRewrite TODO markers in source files
    check-warnings  Categorize build warnings against acceptable patterns
    coverage-report Parse JaCoCo coverage report
"""

import sys

from _build_check_warnings import create_check_warnings_handler
from _build_coverage_report import create_coverage_report_handler
from _build_shared import (
    add_check_warnings_subparser,
    add_coverage_subparser,
    add_parse_subparser,
    add_run_subparser,
    build_main,
    safe_main,
)
from _markers_search import cmd_search_markers
from _maven_cmd_parse import parse_log
from _maven_execute import cmd_run

# --- Tool-specific configuration inlined from former wrapper files ---

cmd_coverage_report = create_coverage_report_handler(
    search_paths=[
        ('target/site/jacoco/jacoco.xml', 'jacoco'),
        ('target/jacoco/report.xml', 'jacoco'),
        ('target/site/jacoco-aggregate/jacoco.xml', 'jacoco'),
    ],
    not_found_message='No JaCoCo XML report found. Run coverage build first.',
)

cmd_check_warnings = create_check_warnings_handler(
    matcher='substring',
    filter_severity='WARNING',
    supports_patterns_arg=False,
)


def _register_run(subparsers):
    run_parser = add_run_subparser(
        subparsers,
        command_args_help="Complete Maven command arguments (e.g., 'verify -Ppre-commit -pl my-module')",
    )
    run_parser.set_defaults(func=cmd_run)


def _register_parse(subparsers):
    add_parse_subparser(
        subparsers, parse_log,
        help_text='Parse Maven build output and categorize issues',
        extra_modes=['no-openrewrite'],
        extra_filters={'no-openrewrite': lambda i: i.category != 'openrewrite_info'},
    )


def _register_search_markers(subparsers):
    markers_parser = subparsers.add_parser('search-markers', help='Search for OpenRewrite TODO markers')
    markers_parser.add_argument('--source-dir', default='src', help='Directory to search')
    markers_parser.add_argument('--extensions', default='.java', help='Comma-separated extensions')
    markers_parser.set_defaults(func=cmd_search_markers)


def _register_coverage(subparsers):
    cov_parser = add_coverage_subparser(subparsers, help_text='Parse JaCoCo coverage report')
    cov_parser.set_defaults(func=cmd_coverage_report)


def _register_check_warnings(subparsers):
    add_check_warnings_subparser(subparsers, cmd_check_warnings)


def main() -> int:
    """Main entry point."""
    return build_main('Maven build operations', [
        _register_run,
        _register_parse,
        _register_search_markers,
        _register_coverage,
        _register_check_warnings,
    ])


if __name__ == '__main__':
    sys.exit(safe_main(main))

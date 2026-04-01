#!/usr/bin/env python3
"""
Maven build operations - run, parse, search markers, check warnings, coverage report.

Usage:
    maven.py run --command-args <args> [options]
    maven.py parse --log <path> [--mode <mode>]
    maven.py search-markers --source-dir <dir>
    maven.py check-warnings --warnings <json> [--patterns <json>]
    maven.py coverage-report [--module-path <path>] [--threshold <percent>]
    maven.py --help

Subcommands:
    run             Execute build and auto-parse on failure (primary API)
    parse           Parse Maven build output and categorize issues
    search-markers  Search for OpenRewrite TODO markers in source files
    check-warnings  Categorize build warnings against acceptable patterns
    coverage-report Parse JaCoCo coverage report
"""

import argparse
import sys

from _build_check_warnings import create_check_warnings_handler
from _build_coverage_report import create_coverage_report_handler
from _build_shared import add_coverage_subparser, add_run_subparser
from _markers_search import cmd_search_markers
from _maven_cmd_parse import cmd_parse
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
    supports_patterns_arg=True,
)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Maven build operations', formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    # run subcommand (primary API)
    run_parser = add_run_subparser(
        subparsers,
        command_args_help="Complete Maven command arguments (e.g., 'verify -Ppre-commit -pl my-module')",
    )
    run_parser.set_defaults(func=cmd_run)

    # parse subcommand
    parse_parser = subparsers.add_parser('parse', help='Parse Maven build output and categorize issues')
    parse_parser.add_argument('--log', required=True, help='Path to Maven build log file')
    parse_parser.add_argument(
        '--mode',
        choices=['default', 'errors', 'structured', 'no-openrewrite'],
        default='structured',
        help='Output mode',
    )
    parse_parser.set_defaults(func=cmd_parse)

    # search-markers subcommand
    markers_parser = subparsers.add_parser('search-markers', help='Search for OpenRewrite TODO markers')
    markers_parser.add_argument('--source-dir', default='src', help='Directory to search')
    markers_parser.add_argument('--extensions', default='.java', help='Comma-separated extensions')
    markers_parser.set_defaults(func=cmd_search_markers)

    # coverage-report subcommand
    cov_parser = add_coverage_subparser(subparsers, help_text='Parse JaCoCo coverage report')
    cov_parser.set_defaults(func=cmd_coverage_report)

    # check-warnings subcommand
    warn_parser = subparsers.add_parser('check-warnings', help='Categorize build warnings')
    warn_parser.add_argument('--warnings', help='JSON array of warning objects')
    warn_parser.add_argument('--patterns', help='JSON array of acceptable patterns')
    warn_parser.add_argument(
        '--acceptable-warnings', dest='acceptable_warnings', help='JSON object with categorized patterns'
    )
    warn_parser.set_defaults(func=cmd_check_warnings)

    args = parser.parse_args()
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())

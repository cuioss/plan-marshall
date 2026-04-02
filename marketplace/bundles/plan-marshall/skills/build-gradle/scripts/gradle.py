#!/usr/bin/env python3
"""
Gradle build operations - run, parse, find projects, search markers, check warnings, coverage report.

Usage:
    gradle.py run --command-args <args> [--format toon|json] [--mode actionable|structured|errors] [options]
    gradle.py parse --log <path> [--mode <mode>]
    gradle.py find-project --project-name <name> | --project-path <path>
    gradle.py search-markers --source-dir <dir>
    gradle.py check-warnings --warnings <json> [--acceptable-warnings <json>]
    gradle.py coverage-report [--project-path <path>] [--threshold <percent>]
    gradle.py --help

Subcommands:
    run             Execute build and auto-parse on failure (primary API)
    parse           Parse Gradle build output and categorize issues
    find-project    Find Gradle project path from project name
    search-markers  Search for OpenRewrite TODO markers in source files
    check-warnings  Categorize build warnings against acceptable patterns
    coverage-report Parse JaCoCo coverage report
"""

import argparse
import sys

from _build_check_warnings import create_check_warnings_handler
from _build_coverage_report import create_coverage_report_handler
from _build_shared import (
    add_check_warnings_subparser,
    add_coverage_subparser,
    add_parse_subparser,
    add_run_subparser,
)
from _gradle_cmd_find_project import cmd_find_project
from _gradle_cmd_parse import parse_log
from _gradle_execute import cmd_run
from _markers_search import cmd_search_markers

# --- Tool-specific configuration inlined from former wrapper files ---

cmd_coverage_report = create_coverage_report_handler(
    search_paths=[
        ('build/reports/jacoco/test/jacocoTestReport.xml', 'jacoco'),
        ('build/reports/jacoco/jacocoTestReport.xml', 'jacoco'),
    ],
    not_found_message='No JaCoCo XML report found. Run coverage build first.',
)

cmd_check_warnings = create_check_warnings_handler(
    matcher='wildcard',
    supports_patterns_arg=False,
)


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Gradle build operations', formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    # run subcommand (primary API)
    run_parser = add_run_subparser(
        subparsers,
        command_args_help="Complete Gradle command arguments (e.g., ':module:build' or 'build')",
    )
    run_parser.set_defaults(func=cmd_run)

    # parse subcommand
    add_parse_subparser(subparsers, parse_log, help_text='Parse Gradle build output and categorize issues')

    # find-project subcommand
    find_parser = subparsers.add_parser('find-project', help='Find Gradle project path from project name')
    find_group = find_parser.add_mutually_exclusive_group(required=True)
    find_group.add_argument('--project-name', help='Project name to search for')
    find_group.add_argument('--project-path', help='Explicit project path to validate')
    find_parser.add_argument('--root', default='.', help='Project root directory')
    find_parser.set_defaults(func=cmd_find_project)

    # coverage-report subcommand
    cov_parser = add_coverage_subparser(subparsers, help_text='Parse JaCoCo coverage report')
    cov_parser.set_defaults(func=cmd_coverage_report)

    # search-markers subcommand
    markers_parser = subparsers.add_parser('search-markers', help='Search for OpenRewrite TODO markers')
    markers_parser.add_argument('--source-dir', default='src', help='Directory to search')
    markers_parser.add_argument('--extensions', default='.java,.kt', help='Comma-separated extensions')
    markers_parser.set_defaults(func=cmd_search_markers)

    # check-warnings subcommand
    add_check_warnings_subparser(subparsers, cmd_check_warnings)

    args = parser.parse_args()
    result: int = args.func(args)
    return result


if __name__ == '__main__':
    sys.exit(main())

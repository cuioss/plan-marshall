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
    add_search_markers_subparser,
    build_main,
    register_standard_subparsers,
    safe_main,
)
from _markers_search import cmd_search_markers
from _maven_cmd_discover import discover_maven_modules
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
)


def main() -> int:
    """Main entry point."""
    return build_main('Maven build operations', register_standard_subparsers(
        run_handler=cmd_run,
        run_args_help="Complete Maven command arguments (e.g., 'verify -Ppre-commit -pl my-module')",
        parse_handler=parse_log,
        parse_help='Parse Maven build output and categorize issues',
        parse_extra_modes=['no-openrewrite'],
        parse_extra_filters={'no-openrewrite': lambda i: i.category != 'openrewrite_info'},
        coverage_handler=cmd_coverage_report,
        coverage_help='Parse JaCoCo coverage report',
        check_warnings_handler=cmd_check_warnings,
        discover_handler=discover_maven_modules,
        discover_help='Discover Maven modules',
        extra_register_fns=[
            lambda sp: add_search_markers_subparser(sp, cmd_search_markers, default_extensions='.java'),
        ],
    ))


if __name__ == '__main__':
    sys.exit(safe_main(main))

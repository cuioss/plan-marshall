#!/usr/bin/env python3
"""Python build operations - run, parse, check warnings, coverage report.

Usage:
    python_build.py run --command-args <args> [options]
    python_build.py parse --log <path> [--mode <mode>]
    python_build.py check-warnings --warnings <json> [--acceptable-warnings <json>]
    python_build.py coverage-report [--project-path <path>] [--threshold <percent>]
    python_build.py --help

Subcommands:
    run             Execute build and auto-parse on failure (primary API)
    parse           Parse pyprojectx build output and categorize issues
    check-warnings  Categorize build warnings against acceptable patterns
    coverage-report Parse coverage.py XML report
"""

import sys

from _build_check_warnings import create_check_warnings_handler
from _build_coverage_report import create_coverage_report_handler
from _build_shared import (
    add_check_warnings_subparser,
    add_coverage_subparser,
    add_discover_subparser,
    add_parse_subparser,
    add_run_subparser,
    build_main,
    safe_main,
)
from _python_cmd_discover import discover_python_modules
from _python_cmd_parse import parse_log
from _python_execute import cmd_run

# --- Tool-specific configuration inlined from former wrapper files ---

cmd_coverage_report = create_coverage_report_handler(
    search_paths=[
        ('coverage.xml', 'cobertura'),
        ('htmlcov/coverage.xml', 'cobertura'),
    ],
    not_found_message='No coverage.py XML report found. Run pytest with --cov --cov-report=xml first.',
)

cmd_check_warnings = create_check_warnings_handler(
    matcher='substring',
    supports_patterns_arg=False,
)


def _register_run(subparsers):
    run_parser = add_run_subparser(
        subparsers,
        command_args_help="Canonical command to execute (e.g., 'verify', 'module-tests', 'quality-gate')",
    )
    run_parser.set_defaults(func=cmd_run)


def _register_parse(subparsers):
    add_parse_subparser(subparsers, parse_log, help_text='Parse pyprojectx build output and categorize issues')


def _register_coverage(subparsers):
    cov_parser = add_coverage_subparser(subparsers, help_text='Parse coverage.py XML report')
    cov_parser.set_defaults(func=cmd_coverage_report)


def _register_check_warnings(subparsers):
    add_check_warnings_subparser(subparsers, cmd_check_warnings)


def _register_discover(subparsers):
    add_discover_subparser(subparsers, discover_python_modules, help_text='Discover Python modules')


def main() -> int:
    """Main entry point."""
    return build_main('Python/pyprojectx build operations', [
        _register_run,
        _register_parse,
        _register_coverage,
        _register_check_warnings,
        _register_discover,
    ])


if __name__ == '__main__':
    sys.exit(safe_main(main))

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
    build_main,
    register_standard_subparsers,
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
)


def main() -> int:
    """Main entry point."""
    return build_main('Python/pyprojectx build operations', register_standard_subparsers(
        run_handler=cmd_run,
        run_args_help="Canonical command to execute (e.g., 'verify', 'module-tests', 'quality-gate')",
        parse_handler=parse_log,
        parse_help='Parse pyprojectx build output and categorize issues',
        coverage_handler=cmd_coverage_report,
        coverage_help='Parse coverage.py XML report',
        check_warnings_handler=cmd_check_warnings,
        discover_handler=discover_python_modules,
        discover_help='Discover Python modules',
    ))


if __name__ == '__main__':
    sys.exit(safe_main(main))

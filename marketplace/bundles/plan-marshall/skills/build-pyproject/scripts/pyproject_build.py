#!/usr/bin/env python3
"""Pyproject build operations - run, parse, check warnings, coverage report.

Usage:
    pyproject_build.py run --command-args <args> [options]
    pyproject_build.py parse --log <path> [--mode <mode>]
    pyproject_build.py check-warnings --warnings <json> [--acceptable-warnings <json>]
    pyproject_build.py coverage-report [--project-path <path>] [--threshold <percent>]
    pyproject_build.py --help

Subcommands:
    run             Execute build and auto-parse on failure (primary API)
    parse           Parse pyprojectx build output and categorize issues
    check-warnings  Categorize build warnings against acceptable patterns
    coverage-report Ad-hoc diagnostic parser invoked manually for inspection.
                    NOT part of the default:coverage_check verify-step pipeline
                    (which uses single-resolver native enforcement via the
                    architecture-resolved coverage command, with the pytest
                    --cov-fail-under flag enforcing the threshold inside the
                    build itself). Use this subcommand for manual local
                    inspection of coverage.py XML output only.
"""

import sys

from _build_check_warnings import create_check_warnings_handler
from _build_cli import (
    build_main,
    register_standard_subparsers,
    safe_main,
)
from _build_coverage_report import create_coverage_report_handler
from _pyproject_cmd_discover import discover_python_modules
from _pyproject_cmd_parse import parse_log
from _pyproject_execute import _CONFIG, cmd_run

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
    return build_main(
        'Python/pyprojectx (build-pyproject) build operations',
        register_standard_subparsers(
            run_handler=cmd_run,
            run_args_help="Canonical command to execute (e.g., 'verify', 'module-tests', 'quality-gate')",
            parse_handler=parse_log,
            parse_help='Parse pyprojectx build output and categorize issues',
            coverage_handler=cmd_coverage_report,
            coverage_help='Parse coverage.py XML report',
            check_warnings_handler=cmd_check_warnings,
            discover_handler=discover_python_modules,
            discover_help='Discover Python modules',
            run_config_key_config=_CONFIG,
        ),
    )


if __name__ == '__main__':
    sys.exit(safe_main(main))

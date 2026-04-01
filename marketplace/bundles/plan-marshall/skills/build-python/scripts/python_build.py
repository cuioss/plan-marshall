#!/usr/bin/env python3
"""Python build operations - run command with auto-parse on failure.

CLI entry point for pyprojectx build execution. The primary API
(execute_direct, cmd_run) lives in _python_execute.py.

Usage:
    python3 .plan/execute-script.py plan-marshall:build-python:python_build run --command-args "verify"
"""

import argparse
import sys

from _build_coverage_report import create_coverage_report_handler  # type: ignore[import-not-found]
from _build_shared import add_run_subparser  # type: ignore[import-not-found]
from _python_execute import cmd_run  # type: ignore[import-not-found]

# =============================================================================
# Constants
# =============================================================================

# Default timeout for Python builds (seconds)
DEFAULT_TIMEOUT = 300

# --- Tool-specific coverage configuration (inlined from former wrapper) ---

cmd_coverage_report = create_coverage_report_handler(
    search_paths=[
        ('coverage.xml', 'cobertura'),
        ('htmlcov/coverage.xml', 'cobertura'),
    ],
    not_found_message='No coverage.py XML report found. Run pytest with --cov --cov-report=xml first.',
)


# =============================================================================
# Main
# =============================================================================


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Python/pyprojectx build operations',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    # run subcommand (primary API)
    run_parser = add_run_subparser(
        subparsers,
        command_args_help="Canonical command to execute (e.g., 'verify', 'module-tests', 'quality-gate')",
        default_timeout=DEFAULT_TIMEOUT,
    )
    run_parser.set_defaults(func=cmd_run)

    # coverage-report subcommand
    cov_parser = subparsers.add_parser('coverage-report', help='Parse coverage.py XML report')
    cov_parser.add_argument('--project-path', dest='project_path', help='Project directory path')
    cov_parser.add_argument('--report-path', dest='report_path', help='Override coverage XML report path')
    cov_parser.add_argument('--threshold', type=int, default=80, help='Coverage threshold percent (default: 80)')
    cov_parser.set_defaults(func=cmd_coverage_report)

    args = parser.parse_args()
    result: int = args.func(args)
    return result


if __name__ == '__main__':
    sys.exit(main())

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

import argparse
import sys

from _build_check_warnings import create_check_warnings_handler
from _build_coverage_report import create_coverage_report_handler
from _build_shared import add_coverage_subparser, add_run_subparser, cmd_parse_common
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


def _cmd_parse(args):
    """Handle parse subcommand using shared parse_log."""
    return cmd_parse_common(args, parse_log)


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
    )
    run_parser.set_defaults(func=cmd_run)

    # parse subcommand
    parse_parser = subparsers.add_parser('parse', help='Parse pyprojectx build output and categorize issues')
    parse_parser.add_argument('--log', required=True, help='Path to build log file')
    parse_parser.add_argument(
        '--mode', choices=['default', 'errors', 'structured'], default='structured', help='Output mode'
    )
    parse_parser.add_argument(
        '--format', choices=['toon', 'json'], default='toon', help='Output format (default: toon)',
    )
    parse_parser.set_defaults(func=_cmd_parse)

    # coverage-report subcommand
    cov_parser = add_coverage_subparser(subparsers, help_text='Parse coverage.py XML report')
    cov_parser.set_defaults(func=cmd_coverage_report)

    # check-warnings subcommand
    warn_parser = subparsers.add_parser('check-warnings', help='Categorize build warnings')
    warn_parser.add_argument('--warnings', help='JSON array of warnings')
    warn_parser.add_argument(
        '--acceptable-warnings', dest='acceptable_warnings', help='JSON object with acceptable patterns'
    )
    warn_parser.set_defaults(func=cmd_check_warnings)

    args = parser.parse_args()
    result: int = args.func(args)
    return result


if __name__ == '__main__':
    sys.exit(main())

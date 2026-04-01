#!/usr/bin/env python3
"""npm build operations - run command with auto-parse on failure.

Provides:
- execute_direct(): Foundation API for npm command execution
- cmd_run(): Run subcommand handler (execute + auto-parse on failure)
- detect_command_type(): npm vs npx detection

Usage:
    from npm import execute_direct, cmd_run

    # Foundation API
    result = execute_direct(
        args="run test",
        command_key="npm:test",
        default_timeout=300
    )

    # Run subcommand (CLI entry point)
    cmd_run(args)  # args from argparse
"""

import argparse
import sys

from _build_coverage_report import create_coverage_report_handler
from _build_shared import add_run_subparser

# Re-export from _npm_execute for backward compatibility
from _npm_execute import cmd_run, detect_command_type, execute_direct  # noqa: F401

# --- Tool-specific coverage configuration (inlined from former wrapper) ---

cmd_coverage_report = create_coverage_report_handler(
    search_paths=[
        ('coverage/coverage-summary.json', 'jest_json'),
        ('coverage/lcov.info', 'lcov'),
        ('dist/coverage/coverage-summary.json', 'jest_json'),
    ],
    not_found_message='No coverage report found. Run tests with coverage first.',
)


# =============================================================================
# Main
# =============================================================================


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='npm/npx build operations', formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    def _npm_extra_args(run_parser):
        run_parser.add_argument('--working-dir', dest='working_dir', help='Working directory for command execution')
        run_parser.add_argument('--env', help="Environment variables (e.g., 'NODE_ENV=test CI=true')")

    # run subcommand (primary API)
    run_parser = add_run_subparser(
        subparsers,
        command_args_help="Complete npm command arguments (e.g., 'run test' or 'run test --workspace=pkg')",
        default_timeout=120,
        extra_args_fn=_npm_extra_args,
    )
    run_parser.set_defaults(func=cmd_run)

    # coverage-report subcommand
    cov_parser = subparsers.add_parser('coverage-report', help='Parse JavaScript coverage report')
    cov_parser.add_argument('--project-path', dest='project_path', help='Project directory path')
    cov_parser.add_argument('--report-path', dest='report_path', help='Override coverage report path')
    cov_parser.add_argument('--threshold', type=int, default=80, help='Coverage threshold percent (default: 80)')
    cov_parser.set_defaults(func=cmd_coverage_report)

    args = parser.parse_args()
    result: int = args.func(args)
    return result


if __name__ == '__main__':
    sys.exit(main())

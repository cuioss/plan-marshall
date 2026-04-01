#!/usr/bin/env python3
"""npm build operations - run command with auto-parse on failure.

CLI entry point for npm/npx build execution. The primary API
(execute_direct, cmd_run, detect_command_type) lives in _npm_execute.py.

Usage:
    python3 .plan/execute-script.py plan-marshall:build-npm:npm run --command-args "run test"
"""

import argparse
import sys

from _build_coverage_report import create_coverage_report_handler
from _build_shared import add_run_subparser
from _npm_execute import cmd_run

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

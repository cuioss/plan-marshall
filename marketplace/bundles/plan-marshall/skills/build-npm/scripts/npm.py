#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""npm build operations - run, parse, check warnings, coverage report.

Usage:
    npm.py run --command-args <args> [options]
    npm.py parse --log <path> [--mode <mode>]
    npm.py check-warnings --warnings <json> [--acceptable-warnings <json>]
    npm.py coverage-report [--project-path <path>] [--threshold <percent>]
    npm.py --help

Subcommands:
    run             Execute build and auto-parse on failure (primary API)
    parse           Parse npm/npx build output and categorize issues
    check-warnings  Categorize build warnings against acceptable patterns
    coverage-report Parse JavaScript coverage report
"""

from _build_check_warnings import create_check_warnings_handler
from _build_cli import (
    build_main,
    register_standard_subparsers,
    safe_main,
)
from _build_coverage_report import create_coverage_report_handler
from _npm_cmd_discover import discover_npm_modules
from _npm_cmd_parse import parse_log
from _npm_execute import _CONFIG, cmd_run

# --- Tool-specific configuration inlined from former wrapper files ---

cmd_coverage_report = create_coverage_report_handler(
    search_paths=[
        ('coverage/coverage-summary.json', 'jest_json'),
        ('coverage/lcov.info', 'lcov'),
        ('dist/coverage/coverage-summary.json', 'jest_json'),
    ],
    not_found_message='No coverage report found. Run tests with coverage first.',
)

cmd_check_warnings = create_check_warnings_handler(
    matcher='substring',
)


def _npm_extra_args(run_parser):
    run_parser.add_argument('--working-dir', dest='working_dir', help='Working directory for command execution')
    run_parser.add_argument('--env', help="Environment variables (e.g., 'NODE_ENV=test CI=true')")


def _npm_check_warnings_extra_args(warn_parser):
    warn_parser.add_argument(
        '--warning-baseline',
        dest='warning_baseline',
        type=int,
        help='Fail (exit 1) when actionable warnings (fixable + unknown) exceed this committed baseline',
    )


def main() -> int:
    """Main entry point."""
    return build_main(
        'npm/npx build operations',
        register_standard_subparsers(
            run_handler=cmd_run,
            run_args_help="Complete npm command arguments (e.g., 'run test' or 'run test --workspace=pkg')",
            run_extra_args_fn=_npm_extra_args,
            parse_handler=parse_log,
            parse_help='Parse npm/npx build output and categorize issues',
            parse_needs_command=True,
            coverage_handler=cmd_coverage_report,
            coverage_help='Parse JavaScript coverage report',
            check_warnings_handler=cmd_check_warnings,
            check_warnings_extra_args_fn=_npm_check_warnings_extra_args,
            discover_handler=discover_npm_modules,
            discover_help='Discover npm modules',
            run_config_key_config=_CONFIG,
        ),
    )


if __name__ == '__main__':
    safe_main(main)()

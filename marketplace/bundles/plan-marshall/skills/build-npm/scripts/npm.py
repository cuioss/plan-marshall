#!/usr/bin/env python3
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

import argparse
import json
import sys
from pathlib import Path

from _build_check_warnings import create_check_warnings_handler
from _build_coverage_report import create_coverage_report_handler
from _build_parse import SEVERITY_ERROR, generate_summary_from_issues
from _build_shared import add_coverage_subparser, add_run_subparser
from _npm_cmd_parse import parse_log
from _npm_execute import cmd_run

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
    supports_patterns_arg=False,
)


def _cmd_parse(args):
    """Handle parse subcommand using shared parse_log."""
    log_path = Path(args.log)
    if not log_path.exists():
        print(json.dumps({'status': 'error', 'error': f'Log file not found: {args.log}'}, indent=2))
        return 1

    issues, test_summary, build_status = parse_log(log_path, getattr(args, 'command', ''))

    if args.mode == 'errors':
        issues = [i for i in issues if i.severity == SEVERITY_ERROR]

    summary = generate_summary_from_issues(issues)
    result = {
        'status': 'success' if build_status == 'SUCCESS' else 'error',
        'data': {
            'build_status': build_status,
            'issues': [i.to_dict() for i in issues],
            'summary': summary,
        },
        'metrics': {
            'tests_run': test_summary.total if test_summary else 0,
            'tests_failed': test_summary.failed if test_summary else 0,
        },
    }
    print(json.dumps(result, indent=2))
    return 0


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
        extra_args_fn=_npm_extra_args,
    )
    run_parser.set_defaults(func=cmd_run)

    # parse subcommand
    parse_parser = subparsers.add_parser('parse', help='Parse npm/npx build output and categorize issues')
    parse_parser.add_argument('--log', required=True, help='Path to npm build log file')
    parse_parser.add_argument(
        '--mode', choices=['default', 'errors', 'structured'], default='structured', help='Output mode'
    )
    parse_parser.set_defaults(func=_cmd_parse)

    # coverage-report subcommand
    cov_parser = add_coverage_subparser(subparsers, help_text='Parse JavaScript coverage report')
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

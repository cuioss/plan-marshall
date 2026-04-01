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

import argparse
import json
import sys
from pathlib import Path

from _build_check_warnings import create_check_warnings_handler
from _build_coverage_report import create_coverage_report_handler
from _build_parse import SEVERITY_ERROR, generate_summary_from_issues
from _build_shared import add_coverage_subparser, add_run_subparser
from _markers_search import cmd_search_markers
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
    supports_patterns_arg=False,
)


def _cmd_parse(args):
    """Handle parse subcommand using shared parse_log."""
    log_path = Path(args.log)
    if not log_path.exists():
        print(json.dumps({'status': 'error', 'error': f'Log file not found: {args.log}'}, indent=2))
        return 1

    issues, test_summary, build_status = parse_log(log_path)

    if args.mode == 'errors':
        issues = [i for i in issues if i.severity == SEVERITY_ERROR]
    elif args.mode == 'no-openrewrite':
        issues = [i for i in issues if i.category != 'openrewrite_info']

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


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Maven build operations', formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    # run subcommand (primary API)
    run_parser = add_run_subparser(
        subparsers,
        command_args_help="Complete Maven command arguments (e.g., 'verify -Ppre-commit -pl my-module')",
    )
    run_parser.set_defaults(func=cmd_run)

    # parse subcommand
    parse_parser = subparsers.add_parser('parse', help='Parse Maven build output and categorize issues')
    parse_parser.add_argument('--log', required=True, help='Path to Maven build log file')
    parse_parser.add_argument(
        '--mode',
        choices=['default', 'errors', 'structured', 'no-openrewrite'],
        default='structured',
        help='Output mode',
    )
    parse_parser.set_defaults(func=_cmd_parse)

    # search-markers subcommand
    markers_parser = subparsers.add_parser('search-markers', help='Search for OpenRewrite TODO markers')
    markers_parser.add_argument('--source-dir', default='src', help='Directory to search')
    markers_parser.add_argument('--extensions', default='.java', help='Comma-separated extensions')
    markers_parser.set_defaults(func=cmd_search_markers)

    # coverage-report subcommand
    cov_parser = add_coverage_subparser(subparsers, help_text='Parse JaCoCo coverage report')
    cov_parser.set_defaults(func=cmd_coverage_report)

    # check-warnings subcommand
    warn_parser = subparsers.add_parser('check-warnings', help='Categorize build warnings')
    warn_parser.add_argument('--warnings', help='JSON array of warning objects')
    warn_parser.add_argument(
        '--acceptable-warnings', dest='acceptable_warnings', help='JSON object with acceptable patterns'
    )
    warn_parser.set_defaults(func=cmd_check_warnings)

    args = parser.parse_args()
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())

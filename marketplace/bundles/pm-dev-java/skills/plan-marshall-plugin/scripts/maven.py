#!/usr/bin/env python3
"""
Maven build operations - run, parse, search markers, check warnings.

Usage:
    maven.py run --command-args <args> [options]
    maven.py parse --log <path> [--mode <mode>]
    maven.py search-markers --source-dir <dir>
    maven.py check-warnings --warnings <json> [--patterns <json>]
    maven.py --help

Subcommands:
    run             Execute build and auto-parse on failure (primary API)
    parse           Parse Maven build output and categorize issues
    search-markers  Search for OpenRewrite TODO markers in source files
    check-warnings  Categorize build warnings against acceptable patterns
"""

import argparse
import sys

from _maven_cmd_check_warnings import cmd_check_warnings
from _maven_cmd_parse import cmd_parse
from _maven_cmd_search_markers import cmd_search_markers

# Import command handlers from internal modules (underscore prefix = private)
from _maven_execute import cmd_run


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Maven build operations', formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    # run subcommand (primary API)
    run_parser = subparsers.add_parser('run', help='Execute build and auto-parse on failure (primary API)')
    run_parser.add_argument(
        '--command-args', dest='command_args',
        required=True,
        help="Complete Maven command arguments (e.g., 'verify -Ppre-commit -pl my-module')",
    )
    run_parser.add_argument(
        '--timeout', type=int, default=120000, help='Build timeout in milliseconds (default: 120000 = 2 min)'
    )
    run_parser.add_argument('--format', choices=['toon', 'json'], default='toon', help='Output format (default: toon)')
    run_parser.add_argument(
        '--mode', choices=['actionable', 'structured', 'errors'], default='actionable', help='Output mode'
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
    parse_parser.set_defaults(func=cmd_parse)

    # search-markers subcommand
    markers_parser = subparsers.add_parser('search-markers', help='Search for OpenRewrite TODO markers')
    markers_parser.add_argument('--source-dir', default='src', help='Directory to search')
    markers_parser.add_argument('--extensions', default='.java', help='Comma-separated extensions')
    markers_parser.set_defaults(func=cmd_search_markers)

    # check-warnings subcommand
    warn_parser = subparsers.add_parser('check-warnings', help='Categorize build warnings')
    warn_parser.add_argument('--warnings', help='JSON array of warning objects')
    warn_parser.add_argument('--patterns', help='JSON array of acceptable patterns')
    warn_parser.add_argument(
        '--acceptable-warnings', dest='acceptable_warnings', help='JSON object with categorized patterns'
    )
    warn_parser.set_defaults(func=cmd_check_warnings)

    args = parser.parse_args()
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())

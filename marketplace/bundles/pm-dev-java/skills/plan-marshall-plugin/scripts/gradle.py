#!/usr/bin/env python3
"""
Gradle build operations - run, parse, find projects, search markers, check warnings.

Usage:
    gradle.py run --commandArgs <args> [--format toon|json] [--mode actionable|structured|errors] [options]
    gradle.py parse --log <path> [--mode <mode>]
    gradle.py find-project --project-name <name> | --project-path <path>
    gradle.py search-markers --source-dir <dir>
    gradle.py check-warnings --warnings <json> [--acceptable-warnings <json>]
    gradle.py --help

Subcommands:
    run             Execute build and auto-parse on failure (primary API)
    parse           Parse Gradle build output and categorize issues
    find-project    Find Gradle project path from project name
    search-markers  Search for OpenRewrite TODO markers in source files
    check-warnings  Categorize build warnings against acceptable patterns
"""

import argparse
import sys

from _gradle_cmd_check_warnings import cmd_check_warnings
from _gradle_cmd_find_project import cmd_find_project
from _gradle_cmd_parse import cmd_parse
from _gradle_cmd_search_markers import cmd_search_markers

# Import command handlers from internal modules (underscore prefix = private)
from _gradle_execute import cmd_run


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Gradle build operations', formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    # run subcommand (primary API)
    run_parser = subparsers.add_parser('run', help='Execute build and auto-parse on failure (primary API)')
    run_parser.add_argument(
        '--commandArgs', required=True, help="Complete Gradle command arguments (e.g., ':module:build' or 'build')"
    )
    run_parser.add_argument('--format', choices=['toon', 'json'], default='toon', help='Output format (default: toon)')
    run_parser.add_argument(
        '--mode',
        choices=['actionable', 'structured', 'errors'],
        default='actionable',
        help='Content mode for warnings/errors',
    )
    run_parser.add_argument(
        '--timeout', type=int, default=120000, help='Build timeout in milliseconds (default: 120000 = 2 min)'
    )
    run_parser.set_defaults(func=cmd_run)

    # parse subcommand
    parse_parser = subparsers.add_parser('parse', help='Parse Gradle build output and categorize issues')
    parse_parser.add_argument('--log', required=True, help='Path to Gradle build log file')
    parse_parser.add_argument(
        '--mode', choices=['default', 'errors', 'structured'], default='structured', help='Output mode'
    )
    parse_parser.set_defaults(func=cmd_parse)

    # find-project subcommand
    find_parser = subparsers.add_parser('find-project', help='Find Gradle project path from project name')
    find_group = find_parser.add_mutually_exclusive_group(required=True)
    find_group.add_argument('--project-name', help='Project name to search for')
    find_group.add_argument('--project-path', help='Explicit project path to validate')
    find_parser.add_argument('--root', default='.', help='Project root directory')
    find_parser.set_defaults(func=cmd_find_project)

    # search-markers subcommand
    markers_parser = subparsers.add_parser('search-markers', help='Search for OpenRewrite TODO markers')
    markers_parser.add_argument('--source-dir', default='src', help='Directory to search')
    markers_parser.add_argument('--extensions', default='.java,.kt', help='Comma-separated extensions')
    markers_parser.set_defaults(func=cmd_search_markers)

    # check-warnings subcommand
    warn_parser = subparsers.add_parser('check-warnings', help='Categorize build warnings')
    warn_parser.add_argument('--warnings', help='JSON array of warnings')
    warn_parser.add_argument(
        '--acceptable-warnings', dest='acceptable_warnings', help='JSON object with acceptable patterns'
    )
    warn_parser.set_defaults(func=cmd_check_warnings)

    args = parser.parse_args()
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())

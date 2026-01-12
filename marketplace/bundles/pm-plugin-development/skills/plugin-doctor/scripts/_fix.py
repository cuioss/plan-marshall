#!/usr/bin/env python3
"""
fix.py - Plugin component fix tools.

Consolidated from:
- extract-fixable-issues.py → extract subcommand
- categorize-fixes.py → categorize subcommand
- apply-fix.py → apply subcommand
- verify-fix.py → verify subcommand

Manages extraction, categorization, application, and verification of fixes.

Output: JSON to stdout.

Usage:
    fix.py extract --input <diagnosis.json>
    fix.py categorize --input <extracted.json>
    fix.py apply --fix <fix.json> --bundle-dir <path>
    fix.py verify --fix-type <type> --file <path>
"""

import argparse
import sys

from _cmd_extract import cmd_extract
from _cmd_categorize import cmd_categorize
from _cmd_apply import cmd_apply
from _cmd_verify import cmd_verify


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Plugin component fix tools',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract fixable issues from diagnosis
  %(prog)s extract --input diagnosis.json

  # Categorize fixes as safe/risky
  %(prog)s categorize --input extracted.json

  # Apply a fix
  %(prog)s apply --fix fix.json --bundle-dir /path/to/bundle

  # Verify a fix was applied
  %(prog)s verify --fix-type missing-frontmatter --file agent.md
"""
    )

    subparsers = parser.add_subparsers(dest='command', help='Operation to perform')

    # extract subcommand
    p_extract = subparsers.add_parser('extract', help='Extract fixable issues')
    p_extract.add_argument(
        '--input', '-i',
        default='-',
        help="Path to diagnosis JSON file, or '-' for stdin (default: stdin)"
    )
    p_extract.set_defaults(func=cmd_extract)

    # categorize subcommand
    p_categorize = subparsers.add_parser('categorize', help='Categorize fixes as safe/risky')
    p_categorize.add_argument(
        '--input', '-i',
        default='-',
        help="Path to extracted issues JSON, or '-' for stdin (default: stdin)"
    )
    p_categorize.set_defaults(func=cmd_categorize)

    # apply subcommand
    p_apply = subparsers.add_parser('apply', help='Apply a single fix')
    p_apply.add_argument(
        '--fix', '-f',
        required=True,
        help="Path to fix JSON file, or '-' for stdin"
    )
    p_apply.add_argument(
        '--bundle-dir', '-b',
        required=True,
        help="Path to bundle directory"
    )
    p_apply.set_defaults(func=cmd_apply)

    # verify subcommand
    p_verify = subparsers.add_parser('verify', help='Verify a fix was applied')
    p_verify.add_argument(
        '--fix-type', '-t',
        required=True,
        help="Type of fix to verify"
    )
    p_verify.add_argument(
        '--file', '-f',
        required=True,
        help="Path to the component file that was fixed"
    )
    p_verify.set_defaults(func=cmd_verify)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())

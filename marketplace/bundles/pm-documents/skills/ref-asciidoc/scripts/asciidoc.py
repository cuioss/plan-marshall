#!/usr/bin/env python3
"""
AsciiDoc formatting, validation, and link operations.

Usage:
    asciidoc.py stats [OPTIONS] [directory]
    asciidoc.py validate [OPTIONS] [path]
    asciidoc.py format [OPTIONS] [path]
    asciidoc.py verify-links [OPTIONS]
    asciidoc.py classify-links [OPTIONS]
    asciidoc.py --help

Subcommands:
    stats           Generate documentation statistics and metrics
    validate        Validate AsciiDoc files for compliance
    format          Auto-fix common AsciiDoc formatting issues
    verify-links    Verify all links in AsciiDoc files
    classify-links  Classify broken links to reduce false positives
"""

import argparse

from _cmd_classify_links import cmd_classify_links
from _cmd_format import cmd_format
from _cmd_stats import cmd_stats
from _cmd_validate import cmd_validate
from _cmd_verify_links import cmd_verify_links
from file_ops import output_toon, safe_main  # type: ignore[import-not-found]


@safe_main
def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='AsciiDoc formatting, validation, and link operations',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    # stats subcommand
    stats_parser = subparsers.add_parser('stats', help='Generate documentation statistics')
    stats_parser.add_argument('--directory', default='.', help='Directory to analyze')
    stats_parser.add_argument(
        '-f', '--format', dest='format', default='console', choices=['console', 'json'], help='Output format'
    )
    stats_parser.add_argument('-d', '--details', action='store_true', help='Include detailed per-file statistics')
    stats_parser.set_defaults(func=cmd_stats)

    # validate subcommand
    validate_parser = subparsers.add_parser('validate', help='Validate AsciiDoc files for compliance')
    validate_parser.add_argument('--path', default='standards', help='File or directory to check')
    validate_parser.add_argument(
        '-f', '--format', dest='format', default='console', choices=['console', 'json'], help='Output format'
    )
    validate_parser.add_argument('-i', '--ignore', action='append', dest='ignore_patterns', help='Ignore pattern')
    validate_parser.set_defaults(func=cmd_validate)

    # format subcommand
    format_parser = subparsers.add_parser('format', help='Auto-fix AsciiDoc formatting issues')
    format_parser.add_argument('--path', default='.', help='File or directory to format')
    format_parser.add_argument(
        '-t',
        '--type',
        action='append',
        dest='fix_types',
        choices=['all', 'lists', 'xref', 'whitespace'],
        help='Fix types',
    )
    format_parser.add_argument('-b', '--no-backup', action='store_true', help="Don't create backup files")
    format_parser.set_defaults(func=cmd_format)

    # verify-links subcommand
    links_parser = subparsers.add_parser('verify-links', help='Verify links in AsciiDoc files')
    links_parser.add_argument('--file', type=str, help='Single file to verify')
    links_parser.add_argument('--directory', type=str, help='Directory to verify')
    links_parser.add_argument('--recursive', action='store_true', help='Scan subdirectories')
    links_parser.add_argument('--report', type=str, help='Output report file')
    links_parser.set_defaults(func=cmd_verify_links)

    # classify-links subcommand
    classify_parser = subparsers.add_parser('classify-links', help='Classify broken links to reduce false positives')
    classify_parser.add_argument('--input', type=str, help='Input JSON file')
    classify_parser.add_argument('--output', type=str, help='Output JSON file')
    classify_parser.add_argument('--pretty', action='store_true', help='Pretty-print JSON')
    classify_parser.set_defaults(func=cmd_classify_links)

    args = parser.parse_args()
    result = args.func(args)
    output_toon(result)
    return 0


if __name__ == '__main__':
    main()

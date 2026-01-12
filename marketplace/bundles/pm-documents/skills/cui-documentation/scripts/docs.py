#!/usr/bin/env python3
"""
AsciiDoc documentation operations - stats, validation, formatting, and analysis.

Usage:
    docs.py stats [OPTIONS] [directory]
    docs.py validate [OPTIONS] [path]
    docs.py format [OPTIONS] [path]
    docs.py verify-links [OPTIONS]
    docs.py classify-links [OPTIONS]
    docs.py review [OPTIONS]
    docs.py analyze-tone [OPTIONS]
    docs.py --help

Subcommands:
    stats           Generate documentation statistics and metrics
    validate        Validate AsciiDoc files for compliance
    format          Auto-fix common AsciiDoc formatting issues
    verify-links    Verify all links in AsciiDoc files
    classify-links  Classify broken links to reduce false positives
    review          Analyze content for quality issues
    analyze-tone    Detect promotional language and missing sources
"""

import argparse
import sys

from _cmd_stats import cmd_stats
from _cmd_validate import cmd_validate
from _cmd_format import cmd_format
from _cmd_verify_links import cmd_verify_links
from _cmd_classify_links import cmd_classify_links
from _cmd_review import cmd_review
from _cmd_analyze_tone import cmd_analyze_tone


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="AsciiDoc documentation operations", formatter_class=argparse.RawDescriptionHelpFormatter)
    subparsers = parser.add_subparsers(dest="command", required=True)

    # stats subcommand
    stats_parser = subparsers.add_parser("stats", help="Generate documentation statistics")
    stats_parser.add_argument('directory', nargs='?', default='.', help='Directory to analyze')
    stats_parser.add_argument('-f', '--format', dest='format', default='console', choices=['console', 'json'], help='Output format')
    stats_parser.add_argument('-d', '--details', action='store_true', help='Include detailed per-file statistics')
    stats_parser.set_defaults(func=cmd_stats)

    # validate subcommand
    validate_parser = subparsers.add_parser("validate", help="Validate AsciiDoc files for compliance")
    validate_parser.add_argument('path', nargs='?', default='standards', help='File or directory to check')
    validate_parser.add_argument('-f', '--format', dest='format', default='console', choices=['console', 'json'], help='Output format')
    validate_parser.add_argument('-i', '--ignore', action='append', dest='ignore_patterns', help='Ignore pattern')
    validate_parser.set_defaults(func=cmd_validate)

    # format subcommand
    format_parser = subparsers.add_parser("format", help="Auto-fix AsciiDoc formatting issues")
    format_parser.add_argument('path', nargs='?', default='.', help='File or directory to format')
    format_parser.add_argument('-t', '--type', action='append', dest='fix_types', choices=['all', 'lists', 'xref', 'whitespace'], help='Fix types')
    format_parser.add_argument('-b', '--no-backup', action='store_true', help="Don't create backup files")
    format_parser.set_defaults(func=cmd_format)

    # verify-links subcommand
    links_parser = subparsers.add_parser("verify-links", help="Verify links in AsciiDoc files")
    links_parser.add_argument('--file', type=str, help='Single file to verify')
    links_parser.add_argument('--directory', type=str, help='Directory to verify')
    links_parser.add_argument('--recursive', action='store_true', help='Scan subdirectories')
    links_parser.add_argument('--report', type=str, help='Output report file')
    links_parser.set_defaults(func=cmd_verify_links)

    # classify-links subcommand
    classify_parser = subparsers.add_parser("classify-links", help="Classify broken links to reduce false positives")
    classify_parser.add_argument('--input', type=str, help='Input JSON file')
    classify_parser.add_argument('--output', type=str, help='Output JSON file')
    classify_parser.add_argument('--pretty', action='store_true', help='Pretty-print JSON')
    classify_parser.set_defaults(func=cmd_classify_links)

    # review subcommand
    review_parser = subparsers.add_parser("review", help="Analyze content for quality issues")
    review_parser.add_argument('--file', '-f', type=str, help='Single file to analyze')
    review_parser.add_argument('--directory', '-d', type=str, help='Directory to analyze')
    review_parser.add_argument('--recursive', '-r', action='store_true', help='Analyze subdirectories')
    review_parser.add_argument('--output', '-o', type=str, help='Output file')
    review_parser.set_defaults(func=cmd_review)

    # analyze-tone subcommand
    tone_parser = subparsers.add_parser("analyze-tone", help="Detect promotional language and missing sources")
    tone_parser.add_argument('--file', type=str, help='Single file to analyze')
    tone_parser.add_argument('--directory', type=str, help='Directory to analyze')
    tone_parser.add_argument('--output', type=str, help='Output JSON file')
    tone_parser.add_argument('--pretty', action='store_true', help='Pretty-print JSON')
    tone_parser.set_defaults(func=cmd_analyze_tone)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

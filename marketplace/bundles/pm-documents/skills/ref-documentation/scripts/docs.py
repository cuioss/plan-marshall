#!/usr/bin/env python3
"""
Documentation content quality operations - review and tone analysis.

Usage:
    docs.py review [OPTIONS]
    docs.py analyze-tone [OPTIONS]
    docs.py --help

Subcommands:
    review          Analyze content for quality issues
    analyze-tone    Detect promotional language and missing sources
"""

import argparse
import sys

from _cmd_analyze_tone import cmd_analyze_tone
from _cmd_review import cmd_review


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Documentation content quality operations', formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    # review subcommand
    review_parser = subparsers.add_parser('review', help='Analyze content for quality issues')
    review_parser.add_argument('--file', '-f', type=str, help='Single file to analyze')
    review_parser.add_argument('--directory', '-d', type=str, help='Directory to analyze')
    review_parser.add_argument('--recursive', '-r', action='store_true', help='Analyze subdirectories')
    review_parser.add_argument('--output', '-o', type=str, help='Output file')
    review_parser.set_defaults(func=cmd_review)

    # analyze-tone subcommand
    tone_parser = subparsers.add_parser('analyze-tone', help='Detect promotional language and missing sources')
    tone_parser.add_argument('--file', type=str, help='Single file to analyze')
    tone_parser.add_argument('--directory', type=str, help='Directory to analyze')
    tone_parser.add_argument('--output', type=str, help='Output JSON file')
    tone_parser.add_argument('--pretty', action='store_true', help='Pretty-print JSON')
    tone_parser.set_defaults(func=cmd_analyze_tone)

    args = parser.parse_args()
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())

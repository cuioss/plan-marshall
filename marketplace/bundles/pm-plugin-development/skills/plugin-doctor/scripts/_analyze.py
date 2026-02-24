#!/usr/bin/env python3
"""
analyze.py - Plugin component analysis tools.

Consolidated from:
- analyze-markdown-file.py → markdown subcommand
- analyze-skill-structure.py → structure subcommand
- analyze-tool-coverage.py → coverage subcommand
- analyze-cross-file-content.py → cross-file subcommand

Provides comprehensive analysis for plugin components.

Output: JSON to stdout.
"""

import argparse
import sys

from _analyze_coverage import analyze_tool_coverage, cmd_coverage
from _analyze_crossfile import DEFAULT_SIMILARITY_THRESHOLD, cmd_cross_file

# Import subcommand handlers
from _analyze_markdown import analyze_markdown_file, cmd_markdown

# Re-export shared utilities for other scripts that import from analyze
from _analyze_shared import (
    detect_component_type,
    extract_frontmatter,
)
from _analyze_structure import analyze_skill_structure, cmd_structure

# Re-export API functions for backward compatibility
# These are used by doctor_analysis.py and other scripts
__all__ = [
    'analyze_markdown_file',
    'analyze_skill_structure',
    'analyze_tool_coverage',
    'detect_component_type',
    'extract_frontmatter',
]


def main():
    parser = argparse.ArgumentParser(
        description='Plugin component analysis tools',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze markdown file structure
  %(prog)s markdown --file agent.md

  # Analyze skill directory structure
  %(prog)s structure --directory skills/plugin-doctor

  # Analyze tool coverage in file
  %(prog)s coverage --file agent.md

  # Analyze cross-file content
  %(prog)s cross-file --skill-path skills/plugin-doctor
""",
    )

    subparsers = parser.add_subparsers(dest='command', required=True, help='Operation to perform')

    # markdown subcommand
    p_md = subparsers.add_parser('markdown', help='Analyze markdown file structure')
    p_md.add_argument('--file', '-f', required=True, help='Path to markdown file')
    p_md.add_argument(
        '--type',
        '-t',
        default='auto',
        choices=['agent', 'command', 'skill', 'subdoc', 'auto'],
        help='Component type (default: auto-detect)',
    )
    p_md.set_defaults(func=cmd_markdown)

    # structure subcommand
    p_struct = subparsers.add_parser('structure', help='Analyze skill directory structure')
    p_struct.add_argument('--directory', '-d', required=True, help='Path to skill directory')
    p_struct.set_defaults(func=cmd_structure)

    # coverage subcommand
    p_cov = subparsers.add_parser('coverage', help='Analyze tool coverage')
    p_cov.add_argument('--file', '-f', required=True, help='Path to component file')
    p_cov.set_defaults(func=cmd_coverage)

    # cross-file subcommand
    p_cross = subparsers.add_parser('cross-file', help='Analyze cross-file content')
    p_cross.add_argument('--skill-path', '-s', required=True, help='Path to skill directory')
    p_cross.add_argument(
        '--similarity-threshold',
        '-t',
        type=float,
        default=DEFAULT_SIMILARITY_THRESHOLD,
        help=f'Similarity threshold (default: {DEFAULT_SIMILARITY_THRESHOLD})',
    )
    p_cross.set_defaults(func=cmd_cross_file)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())

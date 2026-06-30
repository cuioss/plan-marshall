#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
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

from _analyze_coverage import cmd_coverage
from _analyze_crossfile import DEFAULT_SIMILARITY_THRESHOLD, cmd_cross_file
from _analyze_markdown import cmd_markdown
from _analyze_structure import cmd_structure
from file_ops import output_toon, safe_main  # type: ignore[import-not-found]

# The former ``__all__`` re-export surface is removed. ``_analyze.py`` is now a
# thin CLI entry point; consumers import each analyzer directly from its owning
# ``_analyze_*`` module (or discover it through ``_rule_registry``), so the
# hand-maintained re-export list is no longer the public API mirror.


@safe_main
def main() -> int:
    parser = argparse.ArgumentParser(
        description='Plugin component analysis tools',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
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
    p_md = subparsers.add_parser('markdown', help='Analyze markdown file structure', allow_abbrev=False)
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
    p_struct = subparsers.add_parser('structure', help='Analyze skill directory structure', allow_abbrev=False)
    p_struct.add_argument('--directory', '-d', required=True, help='Path to skill directory')
    p_struct.set_defaults(func=cmd_structure)

    # coverage subcommand
    p_cov = subparsers.add_parser('coverage', help='Analyze tool coverage', allow_abbrev=False)
    p_cov.add_argument('--file', '-f', required=True, help='Path to component file')
    p_cov.set_defaults(func=cmd_coverage)

    # cross-file subcommand
    p_cross = subparsers.add_parser('cross-file', help='Analyze cross-file content', allow_abbrev=False)
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

    result = args.func(args)
    output_toon(result)
    return 0


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
Plugin component maintenance tools.

Consolidates:
- update-component.py → update subcommand
- check-duplication.py → check-duplication subcommand
- analyze-component.py → analyze subcommand
- generate-readme.py → readme subcommand

Usage:
    maintain.py update --component <path> --updates <json>
    maintain.py check-duplication --skill-path <path> --content-file <path>
    maintain.py analyze --component <path>
    maintain.py readme --bundle-path <path>
"""

import argparse
import sys

from _cmd_analyze import cmd_analyze
from _cmd_check_duplication import cmd_check_duplication
from _cmd_readme import cmd_readme
from _cmd_update import cmd_update
from _maintain_shared import EXIT_ERROR


def main():
    parser = argparse.ArgumentParser(
        description='Plugin component maintenance tools',
        epilog="""
Examples:
  # Apply updates to a component
  maintain.py update --component agent.md --updates '{"updates": [...]}'

  # Check for duplicate knowledge
  maintain.py check-duplication --skill-path ./skills/my-skill --content-file ./new.md

  # Analyze a component for quality
  maintain.py analyze --component ./agents/my-agent.md

  # Generate README for a bundle
  maintain.py readme --bundle-path ./marketplace/bundles/my-bundle
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest='command', required=True, help='Operation to perform')

    # Update subcommand
    p_update = subparsers.add_parser('update', help='Apply updates to a component')
    p_update.add_argument('--component', required=True, help='Path to component file')
    p_update.add_argument('--updates', help='JSON updates (or read from stdin)')
    p_update.set_defaults(func=cmd_update)

    # Check-duplication subcommand
    p_dup = subparsers.add_parser('check-duplication', help='Check for duplicate knowledge')
    p_dup.add_argument('--skill-path', required=True, help='Path to skill directory')
    p_dup.add_argument('--content-file', required=True, help='Path to new content file')
    p_dup.set_defaults(func=cmd_check_duplication)

    # Analyze subcommand
    p_analyze = subparsers.add_parser('analyze', help='Analyze component for quality')
    p_analyze.add_argument('--component', required=True, help='Path to component file')
    p_analyze.set_defaults(func=cmd_analyze)

    # Readme subcommand
    p_readme = subparsers.add_parser('readme', help='Generate README for a bundle')
    p_readme.add_argument('--bundle-path', required=True, help='Path to bundle directory')
    p_readme.set_defaults(func=cmd_readme)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return EXIT_ERROR

    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())

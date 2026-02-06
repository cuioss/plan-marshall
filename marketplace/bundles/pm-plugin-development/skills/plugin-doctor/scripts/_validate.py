#!/usr/bin/env python3
"""
validate.py - Plugin validation and inventory tools.

Consolidated from:
- validate-references.py → references subcommand
- verify-cross-file-findings.py → cross-file subcommand
- scan-skill-inventory.py → inventory subcommand

Validates plugin components and manages skill inventory.

Output: JSON to stdout.

Usage:
    validate.py references --file <markdown-file>
    validate.py cross-file --analysis <json-file> [--llm-findings <json-file>]
    validate.py inventory --skill-path <directory>
    validate.py extension [--extension <path> | --bundle <path> | --marketplace <path>]
"""

import argparse
import sys

from _cmd_cross_file import cmd_cross_file
from _cmd_extension import cmd_extension
from _cmd_inventory import cmd_inventory
from _cmd_references import cmd_references


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Plugin validation and inventory tools',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate plugin references
  %(prog)s references --file agent.md

  # Verify cross-file findings
  %(prog)s cross-file --analysis analysis.json --llm-findings findings.json

  # Scan skill inventory
  %(prog)s inventory --skill-path skills/plugin-doctor

  # Validate all extensions in marketplace
  %(prog)s extension --marketplace marketplace

  # Validate single extension
  %(prog)s extension --extension marketplace/bundles/pm-dev-java/skills/plan-marshall-plugin/extension.py

  # Validate bundle extension
  %(prog)s extension --bundle marketplace/bundles/pm-dev-java
""",
    )

    subparsers = parser.add_subparsers(dest='command', required=True, help='Operation to perform')

    # references subcommand
    p_refs = subparsers.add_parser('references', help='Validate plugin references')
    p_refs.add_argument('--file', '-f', required=True, help='Path to markdown file')
    p_refs.set_defaults(func=cmd_references)

    # cross-file subcommand
    p_cross = subparsers.add_parser('cross-file', help='Verify cross-file findings')
    p_cross.add_argument('--analysis', '-a', required=True, help='Path to script analysis JSON')
    p_cross.add_argument('--llm-findings', '-l', help='Path to LLM findings JSON (stdin if omitted)')
    p_cross.set_defaults(func=cmd_cross_file)

    # inventory subcommand
    p_inv = subparsers.add_parser('inventory', help='Scan skill inventory')
    p_inv.add_argument('--skill-path', '-s', required=True, help='Path to skill directory')
    p_inv.add_argument('--include-hidden', action='store_true', help='Include hidden files')
    p_inv.set_defaults(func=cmd_inventory)

    # extension subcommand
    p_ext = subparsers.add_parser('extension', help='Validate extension.py files')
    p_ext.add_argument('--extension', '-e', dest='extension_path', help='Path to extension.py file')
    p_ext.add_argument('--bundle', '-b', dest='bundle_path', help='Path to bundle directory')
    p_ext.add_argument('--marketplace', '-m', dest='marketplace_path', help='Path to marketplace directory')
    p_ext.set_defaults(func=cmd_extension)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())

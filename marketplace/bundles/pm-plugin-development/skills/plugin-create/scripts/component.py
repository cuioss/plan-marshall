#!/usr/bin/env python3
"""
component.py - Marketplace component creation utilities.

Consolidated from:
- generate-frontmatter.py → generate subcommand
- validate-component.py → validate subcommand

Provides frontmatter generation and component validation for agents, commands, and skills.

Output: YAML for generate, JSON for validate.

Usage:
    component.py generate --type <type> --config <json>
    component.py validate --file <path> --type <type>
"""

import argparse
import sys

from cmd_generate import cmd_generate
from cmd_validate import cmd_validate


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Marketplace component creation utilities',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate agent frontmatter
  %(prog)s generate --type agent --config '{"name": "my-agent", "description": "Does things", "tools": ["Read", "Write"]}'

  # Generate command frontmatter
  %(prog)s generate --type command --config '{"name": "my-cmd", "description": "A command"}'

  # Generate skill frontmatter
  %(prog)s generate --type skill --config '{"name": "my-skill", "description": "A skill"}'

  # Validate agent
  %(prog)s validate --file ./agents/my-agent.md --type agent

  # Validate command
  %(prog)s validate --file ./commands/my-command.md --type command

  # Validate skill
  %(prog)s validate --file ./skills/my-skill/SKILL.md --type skill
""",
    )

    subparsers = parser.add_subparsers(dest='command', help='Operation to perform')

    # generate command
    p_generate = subparsers.add_parser('generate', help='Generate YAML frontmatter')
    p_generate.add_argument('--type', required=True, choices=['agent', 'command', 'skill'], help='Component type')
    p_generate.add_argument('--config', required=True, help='JSON string with component configuration')
    p_generate.set_defaults(func=cmd_generate)

    # validate command
    p_validate = subparsers.add_parser('validate', help='Validate component structure')
    p_validate.add_argument('--file', required=True, help='Path to component file')
    p_validate.add_argument('--type', required=True, choices=['agent', 'command', 'skill'], help='Component type')
    p_validate.set_defaults(func=cmd_validate)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/env python3
"""Generate subcommand for creating YAML frontmatter."""

import json
import sys


def generate_agent_frontmatter(answers):
    """Generate frontmatter for agent component."""
    frontmatter = {'name': answers['name'], 'description': answers['description']}

    # Add optional model field if present
    if 'model' in answers and answers['model']:
        frontmatter['model'] = answers['model']

    # Format tools as comma-separated string (not array)
    if 'tools' in answers:
        tools = answers['tools']
        if isinstance(tools, list):
            if len(tools) == 0:
                raise ValueError('Error: Agents must have at least one tool')
            frontmatter['tools'] = ', '.join(tools)
        else:
            frontmatter['tools'] = tools
    else:
        raise ValueError("Error: Agents must have 'tools' field")

    return frontmatter


def generate_command_frontmatter(answers):
    """Generate frontmatter for command component."""
    frontmatter = {'name': answers['name'], 'description': answers['description']}
    return frontmatter


def generate_skill_frontmatter(answers):
    """Generate frontmatter for skill component.

    Skill frontmatter permits only: name, description, user-invocable.
    """
    frontmatter = {'name': answers['name'], 'description': answers['description']}

    # user-invocable defaults to false for skills
    frontmatter['user-invocable'] = answers.get('user-invocable', False)

    return frontmatter


def format_frontmatter(frontmatter_dict):
    """Format frontmatter as YAML with --- delimiters."""
    lines = []

    for key, value in frontmatter_dict.items():
        # Quote value if it contains special characters
        if isinstance(value, str) and ('"' in value or "'" in value or ':' in value):
            # Escape double quotes and wrap in quotes
            escaped_value = value.replace('"', '\\"')
            lines.append(f'{key}: "{escaped_value}"')
        else:
            lines.append(f'{key}: {value}')

    yaml_content = '\n'.join(lines)
    return f'---\n{yaml_content}\n---'


def cmd_generate(args) -> int:
    """Generate YAML frontmatter for marketplace component."""
    try:
        answers = json.loads(args.config)
    except json.JSONDecodeError as e:
        print(f'Error: Invalid JSON - {str(e)}', file=sys.stderr)
        return 1

    # Validate component type
    if args.type not in ['agent', 'command', 'skill']:
        print(f"Error: Invalid component type '{args.type}'. Must be 'agent', 'command', or 'skill'", file=sys.stderr)
        return 1

    # Generate frontmatter based on type
    try:
        if args.type == 'agent':
            frontmatter_dict = generate_agent_frontmatter(answers)
        elif args.type == 'command':
            frontmatter_dict = generate_command_frontmatter(answers)
        elif args.type == 'skill':
            frontmatter_dict = generate_skill_frontmatter(answers)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 1

    # Format as YAML with delimiters
    print(format_frontmatter(frontmatter_dict))
    return 0

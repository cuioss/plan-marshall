#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Generate subcommand for creating YAML frontmatter."""

import argparse
import json
from typing import Any


def generate_agent_frontmatter(answers: dict[str, Any]) -> dict[str, Any]:
    """Generate frontmatter for agent component.

    Raises:
        ValueError: If the ``tools`` field is missing or empty.
    """
    frontmatter: dict[str, Any] = {'name': answers['name'], 'description': answers['description']}

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


def generate_command_frontmatter(answers: dict[str, Any]) -> dict[str, Any]:
    """Generate frontmatter for command component."""
    return {'name': answers['name'], 'description': answers['description']}


def generate_skill_frontmatter(answers: dict[str, Any]) -> dict[str, Any]:
    """Generate frontmatter for skill component.

    Skill frontmatter permits only: name, description, user-invocable.
    """
    frontmatter: dict[str, Any] = {'name': answers['name'], 'description': answers['description']}

    # user-invocable defaults to false for skills
    frontmatter['user-invocable'] = answers.get('user-invocable', False)

    return frontmatter


def format_frontmatter(frontmatter_dict: dict[str, Any]) -> str:
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


def cmd_generate(args: argparse.Namespace) -> dict[str, Any]:
    """Generate YAML frontmatter for marketplace component."""
    try:
        answers = json.loads(args.config)
    except json.JSONDecodeError as e:
        return {'status': 'error', 'error': 'invalid_json', 'message': f'Invalid JSON - {str(e)}'}

    # Validate component type
    if args.type not in ['agent', 'command', 'skill']:
        return {
            'status': 'error',
            'error': 'invalid_type',
            'message': f"Invalid component type '{args.type}'. Must be 'agent', 'command', or 'skill'",
        }

    # Generate frontmatter based on type
    try:
        if args.type == 'agent':
            frontmatter_dict = generate_agent_frontmatter(answers)
        elif args.type == 'command':
            frontmatter_dict = generate_command_frontmatter(answers)
        else:
            frontmatter_dict = generate_skill_frontmatter(answers)
    except ValueError as e:
        return {'status': 'error', 'error': 'generation_failed', 'message': str(e)}

    # Format as YAML with delimiters
    return {'status': 'success', 'frontmatter': format_frontmatter(frontmatter_dict)}

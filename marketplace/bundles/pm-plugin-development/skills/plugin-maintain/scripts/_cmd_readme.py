#!/usr/bin/env python3
"""Readme subcommand for generating bundle README files."""

import json
import re
from pathlib import Path


def extract_description(file_path: Path) -> str:
    """Extract description from YAML frontmatter."""
    if not file_path.exists():
        return 'No description'

    try:
        content = file_path.read_text(encoding='utf-8', errors='replace')
    except OSError:
        return 'No description'

    # Check for YAML frontmatter
    if not content.startswith('---'):
        return 'No description'

    # Extract frontmatter
    match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if not match:
        return 'No description'

    frontmatter = match.group(1)

    # Extract description field
    for line in frontmatter.split('\n'):
        if line.startswith('description:'):
            desc = line[len('description:') :].strip()
            return desc if desc else 'No description'

    return 'No description'


def get_bundle_name(bundle_path: Path) -> str:
    """Extract bundle name from plugin.json."""
    # Check both locations: .claude-plugin/plugin.json (standard) and plugin.json (legacy)
    plugin_json = bundle_path / '.claude-plugin' / 'plugin.json'
    if not plugin_json.exists():
        plugin_json = bundle_path / 'plugin.json'

    if not plugin_json.exists():
        return 'Unknown'

    try:
        with open(plugin_json, encoding='utf-8') as f:
            data = json.load(f)
            name: str = data.get('name', 'Unknown')
            return name
    except (OSError, json.JSONDecodeError):
        return 'Unknown'


def discover_commands(bundle_path: Path) -> list[dict]:
    """Discover command .md files in bundle/commands/."""
    commands_dir = bundle_path / 'commands'
    if not commands_dir.is_dir():
        return []

    commands = []
    for cmd_file in sorted(commands_dir.glob('*.md')):
        if cmd_file.is_file():
            commands.append({'name': cmd_file.stem, 'description': extract_description(cmd_file)})
    return commands


def discover_agents(bundle_path: Path) -> list[dict]:
    """Discover agent .md files in bundle/agents/."""
    agents_dir = bundle_path / 'agents'
    if not agents_dir.is_dir():
        return []

    agents = []
    for agent_file in sorted(agents_dir.glob('*.md')):
        if agent_file.is_file():
            agents.append({'name': agent_file.stem, 'description': extract_description(agent_file)})
    return agents


def discover_skills(bundle_path: Path) -> list[dict]:
    """Discover skill directories containing SKILL.md."""
    skills_dir = bundle_path / 'skills'
    if not skills_dir.is_dir():
        return []

    skills = []
    for skill_md in sorted(skills_dir.glob('*/SKILL.md')):
        skill_dir = skill_md.parent
        skills.append({'name': skill_dir.name, 'description': extract_description(skill_md)})
    return skills


def generate_readme_content(bundle_name: str, commands: list[dict], agents: list[dict], skills: list[dict]) -> str:
    """Generate README markdown content."""
    lines = [f'# {bundle_name}', '']

    # Commands section
    if commands:
        lines.extend(['## Commands', ''])
        for cmd in commands:
            lines.append(f'- **{cmd["name"]}** - {cmd["description"]}')
        lines.append('')

    # Agents section
    if agents:
        lines.extend(['## Agents', ''])
        for agent in agents:
            lines.append(f'- **{agent["name"]}** - {agent["description"]}')
        lines.append('')

    # Skills section
    if skills:
        lines.extend(['## Skills', ''])
        for skill in skills:
            lines.append(f'- **{skill["name"]}** - {skill["description"]}')
        lines.append('')

    # Installation section
    lines.extend(['## Installation', '', 'Add to your AI assistant settings or install via marketplace.'])

    return '\n'.join(lines)


def cmd_readme(args) -> dict:
    """Handle readme subcommand."""
    bundle_path = Path(args.bundle_path)

    # Validate path
    if not bundle_path.exists():
        return {
            'status': 'error',
            'error': 'not_found',
            'message': f'Bundle directory not found: {args.bundle_path}',
        }

    if not bundle_path.is_dir():
        return {'status': 'error', 'error': 'not_directory', 'message': f'Not a directory: {args.bundle_path}'}

    # Check for plugin.json (both standard and legacy locations)
    plugin_json = bundle_path / '.claude-plugin' / 'plugin.json'
    if not plugin_json.exists():
        plugin_json = bundle_path / 'plugin.json'
    if not plugin_json.exists():
        return {
            'status': 'error',
            'error': 'missing_plugin_json',
            'message': f'Missing plugin.json in bundle: {args.bundle_path}',
        }

    # Get bundle name
    bundle_name = get_bundle_name(bundle_path)

    # Discover components
    commands = discover_commands(bundle_path)
    agents = discover_agents(bundle_path)
    skills = discover_skills(bundle_path)

    # Generate README content
    readme_content = generate_readme_content(bundle_name, commands, agents, skills)

    # Build result
    return {
        'status': 'success',
        'bundle_path': str(bundle_path),
        'bundle_name': bundle_name,
        'readme_generated': True,
        'components': {'commands': len(commands), 'agents': len(agents), 'skills': len(skills)},
        'readme_content': readme_content,
        'commands': commands,
        'agents': agents,
        'skills': skills,
    }

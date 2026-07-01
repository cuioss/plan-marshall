#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Validate subcommand for validating marketplace component structure."""

import argparse
import re
from typing import Any

from _dep_detection import extract_frontmatter  # type: ignore[import-not-found]

Finding = dict[str, Any]
Frontmatter = dict[str, Any]


def validate_frontmatter_agent(frontmatter: Frontmatter) -> tuple[list[Finding], list[Finding]]:
    """Validate agent frontmatter fields."""
    errors: list[Finding] = []
    warnings: list[Finding] = []

    for field in ['name', 'description']:
        if field not in frontmatter:
            errors.append(
                {
                    'type': 'frontmatter_field_missing',
                    'field': field,
                    'message': f"Required frontmatter field '{field}' not found",
                }
            )

    if 'tools' not in frontmatter:
        errors.append(
            {
                'type': 'frontmatter_field_missing',
                'field': 'tools',
                'message': "Required frontmatter field 'tools' not found",
            }
        )
    else:
        tools = frontmatter['tools']

        if isinstance(tools, list):
            warnings.append(
                {
                    'type': 'tools_format',
                    'field': 'tools',
                    'message': f"Tools field uses array syntax {tools} - should use comma-separated format '{', '.join(tools)}'",
                }
            )
            tools_list = tools
        elif isinstance(tools, str):
            tools_list = [t.strip() for t in tools.split(',')]
        else:
            errors.append(
                {'type': 'tools_format', 'field': 'tools', 'message': 'Tools field must be comma-separated string'}
            )
            tools_list = []

        # Check for prohibited Task tool (Rule 6)
        if 'Task' in tools_list:
            errors.append(
                {
                    'type': 'prohibited_tool',
                    'field': 'tools',
                    'message': 'Agents cannot use Task tool (Rule 6) - unavailable at runtime',
                }
            )

    return errors, warnings


def validate_frontmatter_command(frontmatter: Frontmatter) -> tuple[list[Finding], list[Finding]]:
    """Validate command frontmatter fields."""
    errors: list[Finding] = []
    warnings: list[Finding] = []

    for field in ['name', 'description']:
        if field not in frontmatter:
            errors.append(
                {
                    'type': 'frontmatter_field_missing',
                    'field': field,
                    'message': f"Required frontmatter field '{field}' not found",
                }
            )

    if 'tools' in frontmatter:
        warnings.append(
            {
                'type': 'unexpected_field',
                'field': 'tools',
                'message': "Commands typically don't have 'tools' in frontmatter",
            }
        )

    return errors, warnings


def validate_frontmatter_skill(frontmatter: Frontmatter) -> tuple[list[Finding], list[Finding]]:
    """Validate skill frontmatter fields.

    Skill frontmatter permits only: name, description, user-invocable.
    """
    errors: list[Finding] = []
    warnings: list[Finding] = []

    for field in ['name', 'description']:
        if field not in frontmatter:
            errors.append(
                {
                    'type': 'frontmatter_field_missing',
                    'field': field,
                    'message': f"Required frontmatter field '{field}' not found",
                }
            )

    # Flag prohibited fields that must not appear in skill frontmatter
    prohibited_fields = ['tools', 'allowed-tools', 'model', 'color']
    for field in prohibited_fields:
        if field in frontmatter:
            errors.append(
                {
                    'type': 'prohibited_field',
                    'field': field,
                    'message': f"Skill frontmatter must not contain '{field}' — only name, description, user-invocable are permitted",
                }
            )

    return errors, warnings


def validate_agent_content(content: str) -> tuple[list[Finding], list[Finding]]:
    """Validate agent-specific content rules."""
    errors: list[Finding] = []
    warnings: list[Finding] = []

    if '## CONTINUOUS IMPROVEMENT RULE' not in content:
        warnings.append(
            {
                'type': 'missing_section',
                'section': 'CONTINUOUS IMPROVEMENT RULE',
                'message': 'Agent should have CONTINUOUS IMPROVEMENT RULE section',
            }
        )
    else:
        # Check for self-invocation pattern (Pattern 22)
        problematic_patterns = [
            r'YOU MUST.*using\s+/plugin-',
            r'invoke\s+/plugin-',
            r'call\s+/plugin-',
            r'SlashCommand:\s*/plugin-',
        ]

        for pattern in problematic_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                errors.append(
                    {
                        'type': 'self_invocation',
                        'section': 'CONTINUOUS IMPROVEMENT RULE',
                        'message': 'Agent uses self-invocation pattern (Pattern 22) - agents must REPORT improvements, not invoke commands',
                    }
                )
                break

    required_sections = ['# ', '## Workflow', '## Tool Usage']
    for section in required_sections:
        if section not in content:
            warnings.append(
                {
                    'type': 'missing_section',
                    'section': section.replace('## ', '').replace('# ', 'Title'),
                    'message': f"Expected section '{section}' not found",
                }
            )

    return errors, warnings


def validate_command_content(content: str) -> tuple[list[Finding], list[Finding]]:
    """Validate command-specific content rules."""
    errors: list[Finding] = []
    warnings: list[Finding] = []

    required_sections = ['# ', '## WORKFLOW', '## USAGE EXAMPLES']

    for section in required_sections:
        if section not in content:
            section_name = section.replace('## ', '').replace('# ', 'Title')
            errors.append(
                {
                    'type': 'missing_section',
                    'section': section_name,
                    'message': f"Required section '{section_name}' not found",
                }
            )

    if '## CONTINUOUS IMPROVEMENT RULE' not in content:
        warnings.append(
            {
                'type': 'missing_section',
                'section': 'CONTINUOUS IMPROVEMENT RULE',
                'message': 'Command should have CONTINUOUS IMPROVEMENT RULE section',
            }
        )

    return errors, warnings


def validate_skill_content(content: str) -> tuple[list[Finding], list[Finding]]:
    """Validate skill-specific content rules."""
    errors: list[Finding] = []
    warnings: list[Finding] = []

    required_sections = ['# ', '## What This Skill Provides', '## When to', '## Workflow']

    for section in required_sections:
        if section not in content:
            section_name = section.replace('## ', '').replace('# ', 'Title')
            warnings.append(
                {
                    'type': 'missing_section',
                    'section': section_name,
                    'message': f"Expected section '{section_name}' not found in SKILL.md",
                }
            )

    if '## CONTINUOUS IMPROVEMENT RULE' in content:
        warnings.append(
            {
                'type': 'unexpected_section',
                'section': 'CONTINUOUS IMPROVEMENT RULE',
                'message': 'Skills should not have CONTINUOUS IMPROVEMENT RULE section',
            }
        )

    return errors, warnings


def cmd_validate(args: argparse.Namespace) -> dict[str, Any]:
    """Validate marketplace component structure."""
    errors: list[Finding] = []
    warnings: list[Finding] = []

    # Read file
    try:
        with open(args.file, encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        return {
            'status': 'error',
            'valid': False,
            'errors': [{'type': 'file_not_found', 'message': f'File not found: {args.file}'}],
            'warnings': [],
        }
    except OSError as e:
        return {
            'status': 'error',
            'valid': False,
            'errors': [{'type': 'read_error', 'message': f'Error reading file: {str(e)}'}],
            'warnings': [],
        }

    # Extract and validate frontmatter via the single canonical parser.
    record = extract_frontmatter(content)

    if not record.present:
        errors.append(
            {'type': 'frontmatter_missing', 'message': 'YAML frontmatter not found (must be between --- delimiters)'}
        )
    else:
        frontmatter = record.fields
        # Validate frontmatter based on component type
        if args.type == 'agent':
            fm_errors, fm_warnings = validate_frontmatter_agent(frontmatter)
        elif args.type == 'command':
            fm_errors, fm_warnings = validate_frontmatter_command(frontmatter)
        elif args.type == 'skill':
            fm_errors, fm_warnings = validate_frontmatter_skill(frontmatter)
        else:
            errors.append(
                {
                    'type': 'invalid_type',
                    'message': f"Invalid component type: {args.type}. Must be 'agent', 'command', or 'skill'",
                }
            )
            return {'status': 'error', 'valid': False, 'errors': errors, 'warnings': warnings}

        errors.extend(fm_errors)
        warnings.extend(fm_warnings)

    # Validate content structure based on component type
    if args.type == 'agent':
        content_errors, content_warnings = validate_agent_content(content)
    elif args.type == 'command':
        content_errors, content_warnings = validate_command_content(content)
    elif args.type == 'skill':
        content_errors, content_warnings = validate_skill_content(content)
    else:
        content_errors, content_warnings = [], []

    errors.extend(content_errors)
    warnings.extend(content_warnings)

    # Determine validity
    valid = len(errors) == 0

    return {'status': 'success' if valid else 'error', 'valid': valid, 'errors': errors, 'warnings': warnings}

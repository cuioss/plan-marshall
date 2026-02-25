#!/usr/bin/env python3
"""Verify subcommand for verifying that fixes were successfully applied."""

import json
import re
import sys
from pathlib import Path

from _fix_shared import extract_frontmatter, resolve_issue_type


def verify_frontmatter_fix(file_path: Path) -> dict:
    """Verify frontmatter was added with required fields."""
    try:
        content = file_path.read_text(encoding='utf-8', errors='replace')
    except OSError as e:
        return {'verified': False, 'error': f'Failed to read file: {e}'}

    frontmatter_present, frontmatter = extract_frontmatter(content)

    if not frontmatter_present:
        return {'verified': True, 'issue_resolved': False, 'details': 'Still missing frontmatter'}

    has_name = bool(re.search(r'^name:', frontmatter, re.MULTILINE))
    has_desc = bool(re.search(r'^description:', frontmatter, re.MULTILINE))

    if has_name and has_desc:
        return {'verified': True, 'issue_resolved': True, 'details': 'Frontmatter present with required fields'}

    return {
        'verified': True,
        'issue_resolved': False,
        'details': f'Frontmatter present but missing fields (name: {has_name}, description: {has_desc})',
    }


def verify_array_syntax_fix(file_path: Path) -> dict:
    """Verify tools no longer uses array syntax."""
    try:
        content = file_path.read_text(encoding='utf-8', errors='replace')
    except OSError as e:
        return {'verified': False, 'error': f'Failed to read file: {e}'}

    frontmatter_present, frontmatter = extract_frontmatter(content)

    if not frontmatter_present:
        return {'verified': True, 'issue_resolved': True, 'details': 'No frontmatter to check'}

    if re.search(r'^tools:.*\[', frontmatter, re.MULTILINE):
        return {'verified': True, 'issue_resolved': False, 'details': 'Still using array syntax for tools'}

    return {'verified': True, 'issue_resolved': True, 'details': 'Tools now using comma-separated format'}


def verify_task_tool_fix(file_path: Path) -> dict:
    """Verify Task tool was removed from declaration."""
    try:
        content = file_path.read_text(encoding='utf-8', errors='replace')
    except OSError as e:
        return {'verified': False, 'error': f'Failed to read file: {e}'}

    frontmatter_present, frontmatter = extract_frontmatter(content)

    if not frontmatter_present:
        return {'verified': True, 'issue_resolved': True, 'details': 'No frontmatter to check'}

    if re.search(r'^tools:.*\bTask\b', frontmatter, re.MULTILINE):
        return {
            'verified': True,
            'issue_resolved': False,
            'details': 'Task tool still declared (agent-task-tool-prohibited)',
        }

    return {'verified': True, 'issue_resolved': True, 'details': 'Task tool removed from declaration'}


def verify_trailing_whitespace_fix(file_path: Path) -> dict:
    """Verify trailing whitespace was removed."""
    try:
        content = file_path.read_text(encoding='utf-8', errors='replace')
    except OSError as e:
        return {'verified': False, 'error': f'Failed to read file: {e}'}

    trailing_count = len(re.findall(r'[ \t]+$', content, re.MULTILINE))

    if trailing_count > 0:
        return {
            'verified': True,
            'issue_resolved': False,
            'details': f'Still has trailing whitespace on {trailing_count} lines',
        }

    return {'verified': True, 'issue_resolved': True, 'details': 'No trailing whitespace found'}


def verify_lessons_via_skill_fix(file_path: Path) -> dict:
    """Verify self-update patterns were removed."""
    try:
        content = file_path.read_text(encoding='utf-8', errors='replace')
    except OSError as e:
        return {'verified': False, 'error': f'Failed to read file: {e}'}

    if re.search(r'/plugin-update-agent|/plugin-update-command', content, re.IGNORECASE):
        return {
            'verified': True,
            'issue_resolved': False,
            'details': 'Still contains self-update commands (agent-lessons-via-skill violation)',
        }

    return {'verified': True, 'issue_resolved': True, 'details': 'Self-update patterns removed'}


def verify_skill_tool_visibility_fix(file_path: Path) -> dict:
    """Verify Skill tool was added to agent's tools declaration."""
    try:
        content = file_path.read_text(encoding='utf-8', errors='replace')
    except OSError as e:
        return {'verified': False, 'error': f'Failed to read file: {e}'}

    frontmatter_present, frontmatter = extract_frontmatter(content)

    if not frontmatter_present:
        return {'verified': True, 'issue_resolved': True, 'details': 'No frontmatter to check'}

    # If no tools field, inherits all (including Skill) — resolved
    if not re.search(r'^(?:tools|allowed-tools):', frontmatter, re.MULTILINE):
        return {'verified': True, 'issue_resolved': True, 'details': 'No tools field — inherits all including Skill'}

    # Extract tools and check for Skill
    tools_match = re.search(r'^(?:tools|allowed-tools):\s*(.+)$', frontmatter, re.MULTILINE)
    if tools_match:
        tools_str = tools_match.group(1).strip().strip('[]')
        tools = [t.strip().strip('"').strip("'") for t in tools_str.split(',')]
        if 'Skill' in tools:
            return {'verified': True, 'issue_resolved': True, 'details': 'Skill tool present in declaration'}

    return {
        'verified': True,
        'issue_resolved': False,
        'details': 'Skill tool still missing from tools declaration (agent-skill-tool-visibility violation)',
    }


def verify_unsupported_tools_field_fix(file_path: Path) -> dict:
    """Verify unsupported tools/allowed-tools field was removed from skill frontmatter."""
    try:
        content = file_path.read_text(encoding='utf-8', errors='replace')
    except OSError as e:
        return {'verified': False, 'error': f'Failed to read file: {e}'}

    frontmatter_present, frontmatter = extract_frontmatter(content)

    if not frontmatter_present:
        return {'verified': True, 'issue_resolved': True, 'details': 'No frontmatter to check'}

    if re.search(r'^(?:allowed-tools|tools):', frontmatter, re.MULTILINE):
        return {
            'verified': True,
            'issue_resolved': False,
            'details': 'Unsupported tools/allowed-tools field still present in skill frontmatter',
        }

    return {'verified': True, 'issue_resolved': True, 'details': 'Unsupported tools field removed'}


def verify_misspelled_user_invokable_fix(file_path: Path) -> dict:
    """Verify misspelled user-invocable was renamed to user-invokable."""
    try:
        content = file_path.read_text(encoding='utf-8', errors='replace')
    except OSError as e:
        return {'verified': False, 'error': f'Failed to read file: {e}'}

    frontmatter_present, frontmatter = extract_frontmatter(content)

    if not frontmatter_present:
        return {'verified': True, 'issue_resolved': True, 'details': 'No frontmatter to check'}

    if re.search(r'^user-invocable:', frontmatter, re.MULTILINE):
        return {
            'verified': True,
            'issue_resolved': False,
            'details': 'Still using misspelled user-invocable (should be user-invokable)',
        }

    return {'verified': True, 'issue_resolved': True, 'details': 'Field correctly named user-invokable'}


def verify_generic(file_path: Path, fix_type: str) -> dict:
    """Generic verification for unknown fix types."""
    return {'verified': True, 'issue_resolved': None, 'details': 'Manual verification recommended'}


def cmd_verify(args) -> int:
    """Verify that a fix was successfully applied."""
    file_path = Path(args.file)

    if not file_path.exists():
        print(json.dumps({'verified': False, 'error': f'File not found: {args.file}'}), file=sys.stderr)
        return 1

    if not file_path.is_file():
        print(json.dumps({'verified': False, 'error': f'Not a file: {args.file}'}), file=sys.stderr)
        return 1

    fix_type = resolve_issue_type(args.fix_type)

    if fix_type in ('missing-frontmatter', 'missing-name-field', 'missing-description-field', 'missing-tools-field'):
        result = verify_frontmatter_fix(file_path)
    elif fix_type == 'array-syntax-tools':
        result = verify_array_syntax_fix(file_path)
    elif fix_type == 'agent-task-tool-prohibited':
        result = verify_task_tool_fix(file_path)
    elif fix_type == 'trailing-whitespace':
        result = verify_trailing_whitespace_fix(file_path)
    elif fix_type == 'agent-lessons-via-skill':
        result = verify_lessons_via_skill_fix(file_path)
    elif fix_type == 'agent-skill-tool-visibility':
        result = verify_skill_tool_visibility_fix(file_path)
    elif fix_type == 'unsupported-skill-tools-field':
        result = verify_unsupported_tools_field_fix(file_path)
    elif fix_type == 'misspelled-user-invokable':
        result = verify_misspelled_user_invokable_fix(file_path)
    else:
        result = verify_generic(file_path, fix_type)

    print(json.dumps(result, indent=2))
    return 0

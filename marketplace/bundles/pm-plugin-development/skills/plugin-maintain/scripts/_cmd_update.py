#!/usr/bin/env python3
"""Update subcommand for applying updates to component files."""

import json
import re
import shutil
import sys
from pathlib import Path

from _maintain_shared import EXIT_SUCCESS, EXIT_ERROR, output_json


def create_backup(path: Path) -> str:
    """Create backup of file."""
    backup_path = path.with_suffix(path.suffix + '.maintain-backup')
    shutil.copy2(path, backup_path)
    return str(backup_path)


def restore_backup(path: Path, backup_path: str):
    """Restore file from backup."""
    shutil.copy2(backup_path, path)


def apply_frontmatter_update(content: str, field: str, value: str) -> str:
    """Update or add a frontmatter field."""
    lines = content.split('\n')

    if not content.startswith('---'):
        # No frontmatter, create it
        new_fm = f'---\n{field}: {value}\n---\n\n'
        return new_fm + content

    # Find frontmatter end
    end_idx = -1
    for i, line in enumerate(lines[1:], 1):
        if line.strip() == '---':
            end_idx = i
            break

    if end_idx == -1:
        return content  # Malformed, don't modify

    # Check if field exists
    field_found = False
    for i in range(1, end_idx):
        if lines[i].startswith(f'{field}:'):
            lines[i] = f'{field}: {value}'
            field_found = True
            break

    if not field_found:
        # Insert before closing ---
        lines.insert(end_idx, f'{field}: {value}')

    return '\n'.join(lines)


def apply_section_update(content: str, section: str, new_content: str) -> str:
    """Update or add a section."""
    # Find section header
    pattern = rf'^(#{1,4})\s+{re.escape(section)}\s*$'
    match = re.search(pattern, content, re.MULTILINE | re.IGNORECASE)

    if match:
        # Find end of section (next header of same or higher level)
        header_level = len(match.group(1))
        start = match.end()

        # Find next section of same or higher level
        next_pattern = rf'^#{{{1},{header_level}}}\s+'
        next_match = re.search(next_pattern, content[start:], re.MULTILINE)

        if next_match:
            end = start + next_match.start()
            content = content[:start] + '\n\n' + new_content + '\n\n' + content[end:]
        else:
            # Section goes to end
            content = content[:start] + '\n\n' + new_content + '\n'
    else:
        # Add new section at end
        content = content.rstrip() + f'\n\n## {section}\n\n{new_content}\n'

    return content


def apply_updates(component_path: str, updates: list) -> dict:
    """Apply a list of updates to component."""
    path = Path(component_path)

    if not path.exists():
        return {
            'error': f'File not found: {component_path}',
            'component_path': component_path,
            'success': False
        }

    # Create backup
    backup_path = create_backup(path)

    try:
        content = path.read_text()
        updates_applied = 0
        changes = []

        for update in updates:
            update_type = update.get('type', '')

            if update_type == 'frontmatter':
                field = update.get('field', '')
                value = update.get('value', '')
                if field:
                    content = apply_frontmatter_update(content, field, value)
                    changes.append(f'Updated frontmatter field: {field}')
                    updates_applied += 1

            elif update_type == 'section':
                section = update.get('section', '')
                new_content = update.get('content', '')
                if section:
                    content = apply_section_update(content, section, new_content)
                    changes.append(f'Updated section: {section}')
                    updates_applied += 1

            elif update_type == 'replace':
                old_text = update.get('old', '')
                new_text = update.get('new', '')
                if old_text and old_text in content:
                    content = content.replace(old_text, new_text, 1)
                    changes.append(f'Replaced text: {old_text[:30]}...')
                    updates_applied += 1

            elif update_type == 'append':
                text = update.get('text', '')
                if text:
                    content = content.rstrip() + '\n\n' + text + '\n'
                    changes.append('Appended content')
                    updates_applied += 1

        # Write updated content
        path.write_text(content)

        return {
            'component_path': component_path,
            'updates_applied': updates_applied,
            'success': True,
            'changes': changes,
            'backup_created': backup_path,
            'validation_errors': []
        }

    except Exception as e:
        # Restore backup on error
        restore_backup(path, backup_path)
        return {
            'component_path': component_path,
            'success': False,
            'error': str(e),
            'backup_restored': True
        }


def cmd_update(args) -> int:
    """Handle update subcommand."""
    # Read updates from stdin or --updates argument
    if args.updates:
        try:
            input_data = json.loads(args.updates)
        except json.JSONDecodeError as e:
            output_json({'error': f'Invalid JSON in --updates: {e}'})
            return EXIT_ERROR
    else:
        try:
            input_data = json.loads(sys.stdin.read())
        except json.JSONDecodeError as e:
            output_json({'error': f'Invalid JSON input: {e}'})
            return EXIT_ERROR

    updates = input_data.get('updates', [])
    result = apply_updates(args.component, updates)
    output_json(result)
    return EXIT_SUCCESS if result.get('success') else EXIT_ERROR

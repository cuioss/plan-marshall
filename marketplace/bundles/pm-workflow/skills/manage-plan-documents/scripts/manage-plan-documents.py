#!/usr/bin/env python3
"""
Generic engine for plan document management.

Manages typed documents (request) within plan directories.
Document types are defined declaratively in documents/*.toon files.
Delegates file I/O to manage-files.

Usage:
    python3 manage-plan-document.py request create --plan-id my-plan --title "..." --source description --body "..."
    python3 manage-plan-document.py request read --plan-id my-plan
    python3 manage-plan-document.py request update --plan-id my-plan --section context --content "..."

Note: Solution documents are managed by the manage-solution-outline skill.
"""

import argparse
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from _plan_parsing import parse_document_sections  # type: ignore[import-not-found]
from file_ops import atomic_write_file, base_path  # type: ignore[import-not-found]
from toon_parser import parse_toon, serialize_toon  # type: ignore[import-not-found]

# Skill directory paths for document definitions and templates
SKILL_DIR = Path(__file__).parent.parent
DOCUMENTS_DIR = SKILL_DIR / 'documents'
TEMPLATES_DIR = SKILL_DIR / 'templates'


def load_document_type(doc_type: str) -> dict[Any, Any] | None:
    """Load document definition from documents/{type}.toon"""
    doc_file = DOCUMENTS_DIR / f'{doc_type}.toon'
    if not doc_file.exists():
        return None
    return cast(dict[Any, Any], parse_toon(doc_file.read_text(encoding='utf-8')))


def get_available_types() -> list[str]:
    """Get list of available document types."""
    if not DOCUMENTS_DIR.exists():
        return []
    return [f.stem for f in DOCUMENTS_DIR.glob('*.toon')]


def validate_plan_id(plan_id: str) -> bool:
    """Validate plan_id is kebab-case with no special characters."""
    return bool(re.match(r'^[a-z][a-z0-9-]*$', plan_id))


def validate_fields(doc_def: dict, provided: dict) -> list[str]:
    """Validate provided fields against document definition."""
    errors = []
    fields = doc_def.get('fields', [])

    for field in fields:
        name = field['name']
        required = field.get('required') == 'true' or field.get('required') is True
        field_type = field.get('type', 'string')

        value = provided.get(name)

        if required and not value:
            errors.append(f'Missing required field: {name}')
        elif value:
            # Type-specific validation
            if field_type.startswith('enum('):
                allowed = field_type[5:-1].split('|')
                if value not in allowed:
                    errors.append(f'Invalid {name}: must be one of {allowed}')

    return errors


def render_template(doc_def: dict, fields: dict, plan_id: str) -> str:
    """Render template with field substitution."""
    template_rel = doc_def.get('template', '')
    template_name = template_rel.replace('templates/', '') if template_rel else f'{doc_def["name"]}.md'
    template_path = TEMPLATES_DIR / template_name

    if not template_path.exists():
        # Generate basic template if not found
        lines = [f'# {doc_def["name"].title()}: {fields.get("title", plan_id)}']
        lines.append(f'\nplan_id: {plan_id}')
        lines.append(f'created: {datetime.now(UTC).isoformat()}')
        for name, value in fields.items():
            if value and name != 'title':
                lines.append(f'\n## {name.replace("_", " ").title()}\n\n{value}')
        return '\n'.join(lines)

    template = template_path.read_text(encoding='utf-8')

    # Built-in placeholders
    template = template.replace('{plan_id}', plan_id)
    template = template.replace('{timestamp}', datetime.now(UTC).isoformat())

    # Field placeholders
    for key, value in fields.items():
        placeholder = f'{{{key}}}'
        template = template.replace(placeholder, value if value else '')

    # Clean up unreplaced placeholders (optional fields not provided)
    template = _cleanup_unreplaced_placeholders(template)

    return template


def _cleanup_unreplaced_placeholders(content: str) -> str:
    """Remove lines with unreplaced placeholders and empty sections.

    Handles:
    - Metadata lines like "source_id: {source_id}" - remove entire line
    - Section content lines with only placeholder - remove line
    - Empty sections (heading followed by blank or another heading) - remove section
    """
    import re

    lines = content.split('\n')
    cleaned_lines = []
    placeholder_pattern = re.compile(r'\{[a-z_]+\}')

    i = 0
    while i < len(lines):
        line = lines[i]

        # Check if line contains unreplaced placeholder
        if placeholder_pattern.search(line):
            # Metadata line pattern: "key: {placeholder}" - skip entire line
            if re.match(r'^[a-z_]+:\s*\{[a-z_]+\}\s*$', line):
                i += 1
                continue
            # Line is ONLY a placeholder - skip it
            if re.match(r'^\s*\{[a-z_]+\}\s*$', line):
                i += 1
                continue
            # Otherwise replace placeholder with empty string
            line = placeholder_pattern.sub('', line)

        cleaned_lines.append(line)
        i += 1

    # Remove empty sections (## heading followed by blank lines then another ## or EOF)
    final_lines = []
    i = 0
    while i < len(cleaned_lines):
        line = cleaned_lines[i]

        if line.startswith('## '):
            # Look ahead to see if section is empty
            section_has_content = False
            j = i + 1
            while j < len(cleaned_lines):
                next_line = cleaned_lines[j]
                if next_line.startswith('## ') or next_line.startswith('# '):
                    # Hit another heading - section was empty
                    break
                if next_line.strip():
                    # Found non-empty content
                    section_has_content = True
                    break
                j += 1

            if not section_has_content:
                # Skip this empty section heading and any blank lines after it
                i = j
                continue

        final_lines.append(line)
        i += 1

    # Clean up trailing blank lines
    while final_lines and not final_lines[-1].strip():
        final_lines.pop()

    return '\n'.join(final_lines) + '\n'


def get_plan_dir(plan_id: str) -> Path:
    """Get the plan directory path."""
    return cast(Path, base_path('plans', plan_id))


# =============================================================================
# Commands
# =============================================================================


def cmd_create(doc_type: str, args) -> int:
    """Create a new document."""
    doc_def = load_document_type(doc_type)
    if not doc_def:
        print(
            serialize_toon(
                {
                    'status': 'error',
                    'error': 'unknown_document_type',
                    'document': doc_type,
                    'available': get_available_types(),
                }
            )
        )
        return 1

    if not validate_plan_id(args.plan_id):
        print(
            serialize_toon(
                {
                    'status': 'error',
                    'error': 'invalid_plan_id',
                    'plan_id': args.plan_id,
                    'message': 'Plan ID must be kebab-case (lowercase, hyphens only)',
                }
            )
        )
        return 1

    # Collect fields from args
    fields = {}
    for field_def in doc_def.get('fields', []):
        name = field_def['name']
        value = getattr(args, name.replace('-', '_'), None)
        if value:
            fields[name] = value

    # Validate
    errors = validate_fields(doc_def, fields)
    if errors:
        print(serialize_toon({'status': 'error', 'error': 'validation_failed', 'errors': errors}))
        return 1

    # Check if document already exists
    plan_dir = get_plan_dir(args.plan_id)
    file_name = doc_def.get('file', f'{doc_type}.md')
    file_path = plan_dir / file_name

    if file_path.exists() and not getattr(args, 'force', False):
        print(
            serialize_toon(
                {
                    'status': 'error',
                    'error': 'document_exists',
                    'plan_id': args.plan_id,
                    'document': doc_type,
                    'file': file_name,
                    'message': 'Document already exists. Use --force to overwrite.',
                }
            )
        )
        return 1

    # Render and write
    content = render_template(doc_def, fields, args.plan_id)
    atomic_write_file(file_path, content)

    print(
        serialize_toon(
            {
                'status': 'success',
                'plan_id': args.plan_id,
                'document': doc_type,
                'file': file_name,
                'action': 'created',
                'document_info': {
                    'title': fields.get('title', ''),
                    'sections': ','.join(f['name'] for f in doc_def.get('fields', [])),
                },
            }
        )
    )
    return 0


def cmd_read(doc_type: str, args) -> int:
    """Read a document."""
    doc_def = load_document_type(doc_type)
    if not doc_def:
        print(serialize_toon({'status': 'error', 'error': 'unknown_document_type', 'document': doc_type}))
        return 1

    if not validate_plan_id(args.plan_id):
        print(serialize_toon({'status': 'error', 'error': 'invalid_plan_id', 'plan_id': args.plan_id}))
        return 1

    plan_dir = get_plan_dir(args.plan_id)
    file_name = doc_def.get('file', f'{doc_type}.md')
    file_path = plan_dir / file_name

    if not file_path.exists():
        print(
            serialize_toon(
                {
                    'status': 'error',
                    'error': 'document_not_found',
                    'plan_id': args.plan_id,
                    'document': doc_type,
                    'file': file_name,
                    'suggestions': [f'Create the {doc_type} document first', 'Check plan_id spelling'],
                }
            )
        )
        return 1

    content = file_path.read_text(encoding='utf-8')

    if getattr(args, 'raw', False):
        # Output raw content
        print(content)
    elif getattr(args, 'section', None):
        # Extract specific section
        section_name = args.section.lower().replace(' ', '_')
        sections = parse_document_sections(content)
        section_content = sections.get(section_name, '')

        # Special case: clarified_request falls back to original_input if not found
        actual_section = section_name
        if not section_content and section_name == 'clarified_request':
            section_content = sections.get('original_input', '')
            actual_section = 'original_input'

        if not section_content:
            print(
                serialize_toon(
                    {
                        'status': 'error',
                        'error': 'section_not_found',
                        'plan_id': args.plan_id,
                        'document': doc_type,
                        'section': section_name,
                        'available_sections': list(sections.keys()),
                    }
                )
            )
            return 1
        print(
            serialize_toon(
                {
                    'status': 'success',
                    'plan_id': args.plan_id,
                    'document': doc_type,
                    'section': actual_section,
                    'requested_section': section_name,
                    'content': section_content,
                }
            )
        )
    else:
        # Parse into sections
        sections = parse_document_sections(content)
        print(
            serialize_toon(
                {
                    'status': 'success',
                    'plan_id': args.plan_id,
                    'document': doc_type,
                    'file': file_name,
                    'content': sections,
                }
            )
        )

    return 0


def cmd_update(doc_type: str, args) -> int:
    """Update a document section."""
    doc_def = load_document_type(doc_type)
    if not doc_def:
        print(serialize_toon({'status': 'error', 'error': 'unknown_document_type', 'document': doc_type}))
        return 1

    if not validate_plan_id(args.plan_id):
        print(serialize_toon({'status': 'error', 'error': 'invalid_plan_id', 'plan_id': args.plan_id}))
        return 1

    plan_dir = get_plan_dir(args.plan_id)
    file_name = doc_def.get('file', f'{doc_type}.md')
    file_path = plan_dir / file_name

    if not file_path.exists():
        print(
            serialize_toon(
                {'status': 'error', 'error': 'document_not_found', 'plan_id': args.plan_id, 'document': doc_type}
            )
        )
        return 1

    content = file_path.read_text(encoding='utf-8')
    section = args.section.lower().replace(' ', '_')
    new_content = args.content

    # Find and replace section
    lines = content.split('\n')
    new_lines = []
    in_section = False
    section_found = False
    section_heading = f'## {section.replace("_", " ").title()}'

    for line in lines:
        if line.lower().startswith('## '):
            current_heading = line[3:].strip().lower().replace(' ', '_')
            if current_heading == section:
                # Found target section
                section_found = True
                in_section = True
                new_lines.append(line)
                new_lines.append('')
                new_lines.append(new_content)
                continue
            elif in_section:
                # Exiting target section
                in_section = False
                new_lines.append('')
                new_lines.append(line)
                continue

        if not in_section:
            new_lines.append(line)

    if not section_found:
        # Append new section at end
        new_lines.append('')
        new_lines.append(section_heading)
        new_lines.append('')
        new_lines.append(new_content)

    atomic_write_file(file_path, '\n'.join(new_lines))

    print(
        serialize_toon(
            {'status': 'success', 'plan_id': args.plan_id, 'document': doc_type, 'section': section, 'updated': True}
        )
    )
    return 0


def cmd_clarify(doc_type: str, args) -> int:
    """Add clarifications and clarified request to a document.

    This command adds:
    1. A ## Clarifications section with Q&A pairs
    2. A ## Clarified Request section with the synthesized request

    Expected for request documents to support the uncertainty resolution flow.
    """
    doc_def = load_document_type(doc_type)
    if not doc_def:
        print(serialize_toon({'status': 'error', 'error': 'unknown_document_type', 'document': doc_type}))
        return 1

    if not validate_plan_id(args.plan_id):
        print(serialize_toon({'status': 'error', 'error': 'invalid_plan_id', 'plan_id': args.plan_id}))
        return 1

    plan_dir = get_plan_dir(args.plan_id)
    file_name = doc_def.get('file', f'{doc_type}.md')
    file_path = plan_dir / file_name

    if not file_path.exists():
        print(
            serialize_toon(
                {'status': 'error', 'error': 'document_not_found', 'plan_id': args.plan_id, 'document': doc_type}
            )
        )
        return 1

    content = file_path.read_text(encoding='utf-8')
    lines = content.split('\n')

    # Check if clarifications section already exists
    has_clarifications = any(line.strip().lower() == '## clarifications' for line in lines)
    has_clarified_request = any(line.strip().lower() == '## clarified request' for line in lines)

    # Build new sections
    new_sections = []

    # Add Clarifications section if provided and doesn't exist
    clarifications = getattr(args, 'clarifications', None)
    if clarifications:
        if has_clarifications:
            # Update existing section via cmd_update
            args_update = type('Args', (), {'plan_id': args.plan_id, 'section': 'clarifications', 'content': clarifications})()
            return cmd_update(doc_type, args_update)
        else:
            new_sections.append('\n## Clarifications\n')
            new_sections.append(clarifications)

    # Add Clarified Request section if provided and doesn't exist
    clarified_request = getattr(args, 'clarified_request', None)
    if clarified_request:
        if has_clarified_request:
            # Update existing section via cmd_update
            args_update = type('Args', (), {'plan_id': args.plan_id, 'section': 'clarified_request', 'content': clarified_request})()
            return cmd_update(doc_type, args_update)
        else:
            new_sections.append('\n## Clarified Request\n')
            new_sections.append(clarified_request)

    if not new_sections:
        print(
            serialize_toon(
                {
                    'status': 'error',
                    'error': 'no_content',
                    'message': 'Provide --clarifications and/or --clarified-request',
                }
            )
        )
        return 1

    # Append new sections to content
    new_content = content.rstrip() + '\n' + '\n'.join(new_sections) + '\n'
    atomic_write_file(file_path, new_content)

    print(
        serialize_toon(
            {
                'status': 'success',
                'plan_id': args.plan_id,
                'document': doc_type,
                'sections_added': [s.strip().replace('## ', '') for s in new_sections if s.startswith('\n##')],
            }
        )
    )
    return 0


def cmd_exists(doc_type: str, args) -> int:
    """Check if document exists."""
    doc_def = load_document_type(doc_type)
    if not doc_def:
        print(serialize_toon({'status': 'error', 'error': 'unknown_document_type', 'document': doc_type}))
        return 1

    if not validate_plan_id(args.plan_id):
        print(serialize_toon({'status': 'error', 'error': 'invalid_plan_id', 'plan_id': args.plan_id}))
        return 1

    plan_dir = get_plan_dir(args.plan_id)
    file_name = doc_def.get('file', f'{doc_type}.md')
    file_path = plan_dir / file_name

    exists = file_path.exists()
    print(
        serialize_toon(
            {'status': 'success', 'plan_id': args.plan_id, 'document': doc_type, 'file': file_name, 'exists': exists}
        )
    )

    return 0 if exists else 1


def cmd_remove(doc_type: str, args) -> int:
    """Remove a document."""
    doc_def = load_document_type(doc_type)
    if not doc_def:
        print(serialize_toon({'status': 'error', 'error': 'unknown_document_type', 'document': doc_type}))
        return 1

    if not validate_plan_id(args.plan_id):
        print(serialize_toon({'status': 'error', 'error': 'invalid_plan_id', 'plan_id': args.plan_id}))
        return 1

    plan_dir = get_plan_dir(args.plan_id)
    file_name = doc_def.get('file', f'{doc_type}.md')
    file_path = plan_dir / file_name

    if not file_path.exists():
        print(
            serialize_toon(
                {'status': 'error', 'error': 'document_not_found', 'plan_id': args.plan_id, 'document': doc_type}
            )
        )
        return 1

    file_path.unlink()

    print(
        serialize_toon(
            {'status': 'success', 'plan_id': args.plan_id, 'document': doc_type, 'file': file_name, 'action': 'removed'}
        )
    )
    return 0


def cmd_list_types(args) -> int:
    """List available document types."""
    types = get_available_types()
    type_info = []

    for doc_type in types:
        doc_def = load_document_type(doc_type)
        if doc_def:
            type_info.append(
                {
                    'name': doc_type,
                    'file': doc_def.get('file', f'{doc_type}.md'),
                    'fields': len(doc_def.get('fields', [])),
                }
            )

    print(serialize_toon({'status': 'success', 'types': type_info}))
    return 0


# =============================================================================
# Main
# =============================================================================


def main():
    parser = argparse.ArgumentParser(description='Manage typed documents within plan directories')
    subparsers = parser.add_subparsers(dest='doc_type', help='Document type or command')

    # Special command: list-types
    list_parser = subparsers.add_parser('list-types', help='List available document types')
    list_parser.set_defaults(func=lambda args: cmd_list_types(args))

    # Dynamic subparsers for each document type
    available_types = get_available_types()

    for doc_type in available_types:
        doc_def = load_document_type(doc_type)
        if not doc_def:
            continue

        type_parser = subparsers.add_parser(doc_type, help=f'Manage {doc_type} documents')
        type_subparsers = type_parser.add_subparsers(dest='verb', help='Operation')

        # Create
        create_parser = type_subparsers.add_parser('create', help='Create document')
        create_parser.add_argument('--plan-id', required=True, help='Plan identifier')
        create_parser.add_argument('--force', action='store_true', help='Overwrite if exists')

        # Add field arguments dynamically
        for field_def in doc_def.get('fields', []):
            name = field_def['name']
            required = field_def.get('required') == 'true' or field_def.get('required') is True
            field_type = field_def.get('type', 'string')

            help_text = f'{name} ({field_type})'
            if field_type.startswith('enum('):
                allowed = field_type[5:-1]
                help_text = f'{name} - one of: {allowed}'

            create_parser.add_argument(f'--{name.replace("_", "-")}', required=required, help=help_text)

        create_parser.set_defaults(func=lambda args, dt=doc_type: cmd_create(dt, args))

        # Read
        read_parser = type_subparsers.add_parser('read', help='Read document')
        read_parser.add_argument('--plan-id', required=True, help='Plan identifier')
        read_parser.add_argument('--raw', action='store_true', help='Output raw content')
        read_parser.add_argument('--section', help='Read specific section (e.g., clarified_request)')
        read_parser.set_defaults(func=lambda args, dt=doc_type: cmd_read(dt, args))

        # Update
        update_parser = type_subparsers.add_parser('update', help='Update document section')
        update_parser.add_argument('--plan-id', required=True, help='Plan identifier')
        update_parser.add_argument('--section', required=True, help='Section to update')
        update_parser.add_argument('--content', required=True, help='New content')
        update_parser.set_defaults(func=lambda args, dt=doc_type: cmd_update(dt, args))

        # Exists
        exists_parser = type_subparsers.add_parser('exists', help='Check if document exists')
        exists_parser.add_argument('--plan-id', required=True, help='Plan identifier')
        exists_parser.set_defaults(func=lambda args, dt=doc_type: cmd_exists(dt, args))

        # Remove
        remove_parser = type_subparsers.add_parser('remove', help='Remove document')
        remove_parser.add_argument('--plan-id', required=True, help='Plan identifier')
        remove_parser.set_defaults(func=lambda args, dt=doc_type: cmd_remove(dt, args))

        # Clarify (add clarifications and clarified request)
        clarify_parser = type_subparsers.add_parser('clarify', help='Add clarifications to document')
        clarify_parser.add_argument('--plan-id', required=True, help='Plan identifier')
        clarify_parser.add_argument('--clarifications', help='Q&A clarifications content')
        clarify_parser.add_argument('--clarified-request', dest='clarified_request', help='Synthesized clarified request')
        clarify_parser.set_defaults(func=lambda args, dt=doc_type: cmd_clarify(dt, args))

    args = parser.parse_args()

    if not args.doc_type:
        parser.print_help()
        return 1

    if hasattr(args, 'func'):
        return args.func(args)
    else:
        parser.print_help()
        return 1


if __name__ == '__main__':
    sys.exit(main())

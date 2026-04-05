#!/usr/bin/env python3
"""
Request command handlers for manage-plan-documents.py.

Contains: create, read, update, clarify, exists, remove subcommands.
All operate on typed documents within plan directories.
"""

import argparse

from _documents_core import (  # type: ignore[import-not-found]
    atomic_write_file,
    output_error,
    render_template,
    resolve_document_path,
    validate_doc_type_and_plan,
    validate_fields,
)
from _plan_parsing import parse_document_sections  # type: ignore[import-not-found]


def cmd_create(doc_type: str, args) -> dict:
    """Create a new document."""
    doc_def = validate_doc_type_and_plan(doc_type, args.plan_id)
    if not doc_def:
        return {'status': 'error', 'error': 'validation_failed'}

    # For unknown type, include available types in error
    # (validate_doc_type_and_plan already handles this, but create adds extras)
    # Re-check to provide available types list
    if doc_def is None:
        return {'status': 'error', 'error': 'validation_failed'}

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
        return {'status': 'error', 'error': 'validation_failed', 'errors': errors}

    # Check if document already exists
    file_path, file_name = resolve_document_path(doc_def, doc_type, args.plan_id)

    if file_path.exists() and not getattr(args, 'force', False):
        return {
            'status': 'error',
            'error': 'document_exists',
            'plan_id': args.plan_id,
            'document': doc_type,
            'file': file_name,
            'message': 'Document already exists. Use --force to overwrite.',
        }

    # Render and write
    content = render_template(doc_def, fields, args.plan_id)
    atomic_write_file(file_path, content)

    return {
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


def cmd_read(doc_type: str, args) -> dict:
    """Read a document."""
    doc_def = validate_doc_type_and_plan(doc_type, args.plan_id)
    if not doc_def:
        return {'status': 'error', 'error': 'validation_failed'}

    file_path, file_name = resolve_document_path(doc_def, doc_type, args.plan_id)

    if not file_path.exists():
        return {
            'status': 'error',
            'error': 'document_not_found',
            'plan_id': args.plan_id,
            'document': doc_type,
            'file': file_name,
            'suggestions': [f'Create the {doc_type} document first', 'Check plan_id spelling'],
        }

    content = file_path.read_text(encoding='utf-8')

    if getattr(args, 'raw', False):
        # Output raw content
        print(content)
        return {'status': 'success', 'plan_id': args.plan_id, 'document': doc_type, 'raw': True}
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
            return {
                'status': 'error',
                'error': 'section_not_found',
                'plan_id': args.plan_id,
                'document': doc_type,
                'section': section_name,
                'available_sections': list(sections.keys()),
            }
        return {
            'status': 'success',
            'plan_id': args.plan_id,
            'document': doc_type,
            'section': actual_section,
            'requested_section': section_name,
            'content': section_content,
        }
    else:
        # Parse into sections
        sections = parse_document_sections(content)
        return {
            'status': 'success',
            'plan_id': args.plan_id,
            'document': doc_type,
            'file': file_name,
            'content': sections,
        }


def cmd_update(doc_type: str, args) -> dict:
    """Update a document section."""
    doc_def = validate_doc_type_and_plan(doc_type, args.plan_id)
    if not doc_def:
        return {'status': 'error', 'error': 'validation_failed'}

    file_path, _file_name = resolve_document_path(doc_def, doc_type, args.plan_id)

    if not file_path.exists():
        output_error('document_not_found', plan_id=args.plan_id, document=doc_type)
        return {'status': 'error', 'error': 'validation_failed'}

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

    return {'status': 'success', 'plan_id': args.plan_id, 'document': doc_type, 'section': section, 'updated': True}


def cmd_clarify(doc_type: str, args) -> dict:
    """Add clarifications and clarified request to a document.

    This command adds:
    1. A ## Clarifications section with Q&A pairs
    2. A ## Clarified Request section with the synthesized request

    Expected for request documents to support the uncertainty resolution flow.
    """
    doc_def = validate_doc_type_and_plan(doc_type, args.plan_id)
    if not doc_def:
        return {'status': 'error', 'error': 'validation_failed'}

    file_path, _file_name = resolve_document_path(doc_def, doc_type, args.plan_id)

    if not file_path.exists():
        output_error('document_not_found', plan_id=args.plan_id, document=doc_type)
        return {'status': 'error', 'error': 'validation_failed'}

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
            args_update = argparse.Namespace(plan_id=args.plan_id, section='clarifications', content=clarifications)
            return cmd_update(doc_type, args_update)
        else:
            new_sections.append('\n## Clarifications\n')
            new_sections.append(clarifications)

    # Add Clarified Request section if provided and doesn't exist
    clarified_request = getattr(args, 'clarified_request', None)
    if clarified_request:
        if has_clarified_request:
            # Update existing section via cmd_update
            args_update = argparse.Namespace(
                plan_id=args.plan_id, section='clarified_request', content=clarified_request
            )
            return cmd_update(doc_type, args_update)
        else:
            new_sections.append('\n## Clarified Request\n')
            new_sections.append(clarified_request)

    if not new_sections:
        return {
            'status': 'error',
            'error': 'no_content',
            'message': 'Provide --clarifications and/or --clarified-request',
        }

    # Append new sections to content
    new_content = content.rstrip() + '\n' + '\n'.join(new_sections) + '\n'
    atomic_write_file(file_path, new_content)

    return {
        'status': 'success',
        'plan_id': args.plan_id,
        'document': doc_type,
        'sections_added': [s.strip().replace('## ', '') for s in new_sections if s.startswith('\n##')],
    }


def cmd_exists(doc_type: str, args) -> dict:
    """Check if document exists."""
    doc_def = validate_doc_type_and_plan(doc_type, args.plan_id)
    if not doc_def:
        return {'status': 'error', 'error': 'validation_failed'}

    file_path, file_name = resolve_document_path(doc_def, doc_type, args.plan_id)

    exists = file_path.exists()
    return {'status': 'success', 'plan_id': args.plan_id, 'document': doc_type, 'file': file_name, 'exists': exists}


def cmd_remove(doc_type: str, args) -> dict:
    """Remove a document."""
    doc_def = validate_doc_type_and_plan(doc_type, args.plan_id)
    if not doc_def:
        return {'status': 'error', 'error': 'validation_failed'}

    file_path, file_name = resolve_document_path(doc_def, doc_type, args.plan_id)

    if not file_path.exists():
        output_error('document_not_found', plan_id=args.plan_id, document=doc_type)
        return {'status': 'error', 'error': 'validation_failed'}

    file_path.unlink()

    return {'status': 'success', 'plan_id': args.plan_id, 'document': doc_type, 'file': file_name, 'action': 'removed'}

#!/usr/bin/env python3
"""
Request command handlers for manage-plan-documents.py.

Contains: create, read, path, mark-clarified, exists, remove subcommands.

Editing flow (three-step pattern):
    1. `request path`         → script returns the canonical artifact path
    2. Main context writes/edits the returned file with Read/Edit/Write
    3. `request mark-clarified` → script validates and records the transition

No multi-line content is ever marshalled through the shell boundary.
"""

from _documents_core import (  # type: ignore[import-not-found]
    output_error,
    render_template,
    resolve_document_path,
    validate_doc_type_and_plan,
    validate_fields,
)
from _plan_parsing import parse_document_sections  # type: ignore[import-not-found]
from file_ops import atomic_write_file  # type: ignore[import-not-found]


def cmd_create(doc_type: str, args) -> dict:
    """Create a new document."""
    doc_def = validate_doc_type_and_plan(doc_type, args.plan_id)
    if not doc_def:
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


def cmd_path(doc_type: str, args) -> dict:
    """Return the canonical absolute path for a document (Step 1 of edit flow).

    The script owns path allocation. Main context never invents paths.
    Returns the canonical artifact location the caller will Edit/Write directly.
    Document must already exist (use `create` to allocate a fresh one).
    """
    doc_def = validate_doc_type_and_plan(doc_type, args.plan_id)
    if not doc_def:
        return {'status': 'error', 'error': 'validation_failed'}

    file_path, file_name = resolve_document_path(doc_def, doc_type, args.plan_id)

    if not file_path.exists():
        output_error('document_not_found', plan_id=args.plan_id, document=doc_type)
        return {'status': 'error', 'error': 'validation_failed'}

    sections = list(parse_document_sections(file_path.read_text(encoding='utf-8')).keys())

    return {
        'status': 'success',
        'plan_id': args.plan_id,
        'document': doc_type,
        'file': file_name,
        'path': str(file_path.resolve()),
        'sections': sections,
    }


def cmd_mark_clarified(doc_type: str, args) -> dict:
    """Validate that clarifications have been written and record the transition.

    Step 3 of the edit flow for request clarification: the caller has already
    edited the file directly with Read/Edit/Write. This subcommand verifies
    the edit landed (Clarified Request section present) and returns a status
    transition. No content crosses the shell boundary.
    """
    doc_def = validate_doc_type_and_plan(doc_type, args.plan_id)
    if not doc_def:
        return {'status': 'error', 'error': 'validation_failed'}

    file_path, file_name = resolve_document_path(doc_def, doc_type, args.plan_id)

    if not file_path.exists():
        output_error('document_not_found', plan_id=args.plan_id, document=doc_type)
        return {'status': 'error', 'error': 'validation_failed'}

    content = file_path.read_text(encoding='utf-8')
    sections = parse_document_sections(content)

    has_clarified_request = 'clarified_request' in sections and bool(sections.get('clarified_request', '').strip())

    if not has_clarified_request:
        return {
            'status': 'error',
            'error': 'not_clarified',
            'plan_id': args.plan_id,
            'document': doc_type,
            'file': file_name,
            'message': 'Document has no Clarified Request section. Edit the file (see `request path`) before calling mark-clarified.',
        }

    has_clarifications = 'clarifications' in sections and bool(sections.get('clarifications', '').strip())

    return {
        'status': 'success',
        'plan_id': args.plan_id,
        'document': doc_type,
        'file': file_name,
        'clarified': True,
        'has_clarifications_section': has_clarifications,
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

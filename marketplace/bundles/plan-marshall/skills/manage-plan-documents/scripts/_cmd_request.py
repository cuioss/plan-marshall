#!/usr/bin/env python3
"""
Request command handlers for manage-plan-documents.py.

Contains: create, read, path, mark-clarified, exists, remove subcommands.

Editing flow (three-step pattern):
    1. `request path`         → script returns the canonical artifact path
    2. Main context writes/edits the returned file with Read/Edit/Write
    3. `request mark-clarified` → script validates and records the transition

No multi-line content is ever marshalled through the shell boundary. For
initial body creation, `request create` either emits a metadata-only stub
(caller writes the body via Write(path)) or accepts `--body-file PATH` to
splice a pre-written body into the rendered stub.
"""

from pathlib import Path

from _documents_core import (  # type: ignore[import-not-found]
    output_error,
    render_template,
    resolve_document_path,
    validate_doc_type_and_plan,
    validate_fields,
)
from _plan_parsing import parse_document_sections  # type: ignore[import-not-found]
from file_ops import atomic_write_file  # type: ignore[import-not-found]

# Placeholder paragraph emitted by templates/request.md when no body is provided.
# When --body-file is supplied, cmd_create replaces this line with the file contents.
# Keep in sync with templates/request.md.
_BODY_STUB = '_Body not yet provided — write content here._'


def cmd_create(doc_type: str, args) -> dict:
    """Create a new document.

    Body handling (path-allocate convention):
      * No `--body-file`:    render the metadata-only stub. The placeholder
                             paragraph stays in place; the caller is expected
                             to write the body directly via `Write(path)`,
                             using the `path` field returned below.
      * `--body-file PATH`:  read PATH (UTF-8) and splice the contents into
                             the rendered stub in place of the placeholder
                             paragraph. PATH must point to an existing regular
                             file — otherwise returns `body_file_not_found`.

    The returned dict always includes `path` (absolute resolved path of the
    created file) so callers can pipe directly into the Write tool.
    """
    doc_def = validate_doc_type_and_plan(doc_type, args.plan_id)
    if not doc_def:
        return {'status': 'error', 'error': 'validation_failed'}

    # Resolve destination path up-front so body_file_not_found can cite `file`.
    file_path, file_name = resolve_document_path(doc_def, doc_type, args.plan_id)

    # Collect metadata fields (title, source, source_id). body_file is a pure
    # input alias and never reaches the template renderer.
    fields: dict[str, str] = {}
    for field_def in doc_def.get('fields', []):
        name = field_def['name']
        if name == 'body_file':
            continue
        value = getattr(args, name.replace('-', '_'), None)
        if value:
            fields[name] = value

    # Validate metadata fields.
    errors = validate_fields(doc_def, fields)
    if errors:
        return {'status': 'error', 'error': 'validation_failed', 'errors': errors}

    # Optional --body-file shortcut: load the body contents or fail fast.
    body_file_raw = getattr(args, 'body_file', None)
    body: str | None = None
    if body_file_raw:
        body_file_path = Path(body_file_raw).expanduser().resolve()
        if not body_file_path.exists() or not body_file_path.is_file():
            return {
                'status': 'error',
                'error': 'body_file_not_found',
                'plan_id': args.plan_id,
                'document': doc_type,
                'file': file_name,
                'body_file': str(body_file_path),
                'message': f'body_file does not exist or is not a regular file: {body_file_path}',
            }
        body = body_file_path.read_text(encoding='utf-8')

    # Refuse to overwrite unless --force.
    if file_path.exists() and not getattr(args, 'force', False):
        return {
            'status': 'error',
            'error': 'document_exists',
            'plan_id': args.plan_id,
            'document': doc_type,
            'file': file_name,
            'message': 'Document already exists. Use --force to overwrite.',
        }

    # Render stub, then splice in the body (if supplied) by replacing the
    # placeholder paragraph. Trailing newline on body is stripped so the
    # spliced block matches the surrounding template formatting.
    content = render_template(doc_def, fields, args.plan_id)
    if body is not None:
        body_block = body.rstrip('\n')
        content = content.replace(_BODY_STUB, body_block)

    atomic_write_file(file_path, content)

    return {
        'status': 'success',
        'plan_id': args.plan_id,
        'document': doc_type,
        'file': file_name,
        'path': str(file_path.resolve()),
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

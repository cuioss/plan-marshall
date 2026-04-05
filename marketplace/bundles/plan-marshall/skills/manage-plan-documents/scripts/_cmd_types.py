#!/usr/bin/env python3
"""
Document type command handlers for manage-plan-documents.py.

Contains: list-types subcommand and type enumeration logic.
"""

from _documents_core import (  # type: ignore[import-not-found]
    get_available_types,
    load_document_type,
)


def cmd_list_types(args) -> dict:
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

    return {'status': 'success', 'types': type_info}

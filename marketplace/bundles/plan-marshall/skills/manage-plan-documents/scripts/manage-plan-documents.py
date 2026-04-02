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
import sys

from _cmd_request import cmd_clarify, cmd_create, cmd_exists, cmd_read, cmd_remove, cmd_update
from _cmd_types import cmd_list_types
from _documents_core import get_available_types, load_document_type, serialize_toon


def build_parser() -> argparse.ArgumentParser:
    """Build argument parser with dynamic subparsers for document types."""
    parser = argparse.ArgumentParser(description='Manage typed documents within plan directories')
    subparsers = parser.add_subparsers(dest='doc_type', required=True, help='Document type or command')

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
        type_subparsers = type_parser.add_subparsers(dest='verb', required=True, help='Operation')

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
        clarify_parser.add_argument(
            '--clarified-request', dest='clarified_request', help='Synthesized clarified request'
        )
        clarify_parser.set_defaults(func=lambda args, dt=doc_type: cmd_clarify(dt, args))

    return parser


def main() -> int:
    """Main entry point."""
    parser = build_parser()
    args = parser.parse_args()

    if not args.doc_type:
        parser.print_help()
        return 1

    if hasattr(args, 'func'):
        result = args.func(args)
        return int(result) if result is not None else 0
    else:
        parser.print_help()
        return 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as e:
        print(serialize_toon({'status': 'error', 'error': 'unexpected', 'message': str(e)}), file=sys.stderr)
        sys.exit(1)

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

from _cmd_request import cmd_clarify, cmd_create, cmd_exists, cmd_read, cmd_remove, cmd_update
from _cmd_types import cmd_list_types
from _documents_core import get_available_types, load_document_type
from file_ops import safe_main  # type: ignore[import-not-found]
from input_validation import add_plan_id_arg  # type: ignore[import-not-found]


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
        add_plan_id_arg(create_parser)
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
        add_plan_id_arg(read_parser)
        read_parser.add_argument('--raw', action='store_true', help='Output raw content')
        read_parser.add_argument('--section', help='Read specific section (e.g., clarified_request)')
        read_parser.set_defaults(func=lambda args, dt=doc_type: cmd_read(dt, args))

        # Update
        update_parser = type_subparsers.add_parser('update', help='Update document section')
        add_plan_id_arg(update_parser)
        update_parser.add_argument('--section', required=True, help='Section to update')
        update_parser.add_argument('--content', required=True, help='New content')
        update_parser.set_defaults(func=lambda args, dt=doc_type: cmd_update(dt, args))

        # Exists
        exists_parser = type_subparsers.add_parser('exists', help='Check if document exists')
        add_plan_id_arg(exists_parser)
        exists_parser.set_defaults(func=lambda args, dt=doc_type: cmd_exists(dt, args))

        # Remove
        remove_parser = type_subparsers.add_parser('remove', help='Remove document')
        add_plan_id_arg(remove_parser)
        remove_parser.set_defaults(func=lambda args, dt=doc_type: cmd_remove(dt, args))

        # Clarify (add clarifications and clarified request)
        clarify_parser = type_subparsers.add_parser('clarify', help='Add clarifications to document')
        add_plan_id_arg(clarify_parser)
        clarify_parser.add_argument('--clarifications', help='Q&A clarifications content')
        clarify_parser.add_argument(
            '--clarified-request', dest='clarified_request', help='Synthesized clarified request'
        )
        clarify_parser.set_defaults(func=lambda args, dt=doc_type: cmd_clarify(dt, args))

    return parser


@safe_main
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
    main()

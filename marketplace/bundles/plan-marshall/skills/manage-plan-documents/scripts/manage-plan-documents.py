#!/usr/bin/env python3
"""
Generic engine for plan document management.

Manages typed documents (request) within plan directories.
Document types are defined declaratively in documents/*.toon files.
Delegates file I/O to manage-files.

Usage:
    # Create a metadata-only stub and write the body via Write(path)
    python3 manage-plan-document.py request create --plan-id my-plan --title "..." --source description
    # (then the main context calls Write(path) using the returned `path` field)

    # Create with a pre-written body file as a shortcut
    python3 manage-plan-document.py request create --plan-id my-plan --title "..." --source description --body-file /tmp/body.md

    python3 manage-plan-document.py request read --plan-id my-plan
    python3 manage-plan-document.py request path --plan-id my-plan
    python3 manage-plan-document.py request mark-clarified --plan-id my-plan

Body handling (path-allocate convention): `request create` never accepts inline
multi-line body/context/clarification arguments. The two supported flows are:

  1. Stub + Write: call `request create` with metadata only; it returns `path`
     pointing at the freshly created file. The main context then writes the
     body directly via the Write tool against that path.
  2. Body-file shortcut: pass `--body-file PATH` to splice a pre-written body
     into the rendered stub at creation time. Missing/non-regular paths return
     `status: error, error: body_file_not_found`.

Clarification flow (three-step pattern): call `request path` to get the
canonical artifact path, edit the file directly with Read/Edit/Write in the
main context, then call `request mark-clarified` to record the transition.
No multi-line content crosses the shell boundary.

Note: Solution documents are managed by the manage-solution-outline skill.
"""

import argparse

from _cmd_request import cmd_create, cmd_exists, cmd_mark_clarified, cmd_path, cmd_read, cmd_remove
from _cmd_types import cmd_list_types
from _documents_core import get_available_types, load_document_type
from file_ops import output_toon, safe_main  # type: ignore[import-not-found]
from input_validation import (  # type: ignore[import-not-found]
    add_plan_id_arg,
    parse_args_with_toon_errors,
)


def build_parser() -> argparse.ArgumentParser:
    """Build argument parser with dynamic subparsers for document types."""
    parser = argparse.ArgumentParser(
        description='Manage typed documents within plan directories', allow_abbrev=False
    )
    subparsers = parser.add_subparsers(dest='doc_type', required=True, help='Document type or command')

    # Special command: list-types
    list_parser = subparsers.add_parser('list-types', help='List available document types', allow_abbrev=False)
    list_parser.set_defaults(func=lambda args: cmd_list_types(args))

    # Dynamic subparsers for each document type
    available_types = get_available_types()

    for doc_type in available_types:
        doc_def = load_document_type(doc_type)
        if not doc_def:
            continue

        type_parser = subparsers.add_parser(
            doc_type, help=f'Manage {doc_type} documents', allow_abbrev=False
        )
        type_subparsers = type_parser.add_subparsers(dest='verb', required=True, help='Operation')

        # Create
        # allow_abbrev=False prevents argparse from prefix-matching removed inline
        # arguments (e.g. --body) against the live --body-file flag. The path-allocate
        # refactor deliberately removed --body/--context/--clarifications/--clarified-request
        # — any such invocation MUST fail with "unrecognized argument", not silently
        # rebind to a different flag. See task-006 / solution_outline deliverable 6.
        create_parser = type_subparsers.add_parser('create', help='Create document', allow_abbrev=False)
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
        read_parser = type_subparsers.add_parser('read', help='Read document', allow_abbrev=False)
        add_plan_id_arg(read_parser)
        read_parser.add_argument('--raw', action='store_true', help='Output raw content')
        read_parser.add_argument('--section', help='Read specific section (e.g., clarified_request)')
        read_parser.set_defaults(func=lambda args, dt=doc_type: cmd_read(dt, args))

        # Path (Step 1 of edit flow: script allocates canonical artifact path)
        path_parser = type_subparsers.add_parser(
            'path',
            help='Return canonical artifact path for direct edit (Step 1 of edit flow)',
            allow_abbrev=False,
        )
        add_plan_id_arg(path_parser)
        path_parser.set_defaults(func=lambda args, dt=doc_type: cmd_path(dt, args))

        # Exists
        exists_parser = type_subparsers.add_parser(
            'exists', help='Check if document exists', allow_abbrev=False
        )
        add_plan_id_arg(exists_parser)
        exists_parser.set_defaults(func=lambda args, dt=doc_type: cmd_exists(dt, args))

        # Remove
        remove_parser = type_subparsers.add_parser('remove', help='Remove document', allow_abbrev=False)
        add_plan_id_arg(remove_parser)
        remove_parser.set_defaults(func=lambda args, dt=doc_type: cmd_remove(dt, args))

        # Mark-clarified (Step 3: validate edited file and record transition)
        mark_clarified_parser = type_subparsers.add_parser(
            'mark-clarified',
            help='Record clarification transition after direct edit (Step 3 of edit flow)',
            allow_abbrev=False,
        )
        add_plan_id_arg(mark_clarified_parser)
        mark_clarified_parser.set_defaults(func=lambda args, dt=doc_type: cmd_mark_clarified(dt, args))

    return parser


@safe_main
def main() -> int:
    """Main entry point."""
    parser = build_parser()
    args = parse_args_with_toon_errors(parser)

    if not args.doc_type:
        parser.print_help()
        return 1

    if hasattr(args, 'func'):
        result = args.func(args)
        if isinstance(result, dict):
            output_toon(result)
            return 0
        return int(result) if result is not None else 0
    else:
        parser.print_help()
        return 1


if __name__ == '__main__':
    main()

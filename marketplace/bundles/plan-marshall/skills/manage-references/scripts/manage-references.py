#!/usr/bin/env python3
"""
Manage references.json files with field-level access and list management.

Tracks files, branches, and external references for a plan.
Storage: JSON format (.plan/plans/{plan_id}/references.json)
Output: TOON format for API responses

Usage:
    python3 manage-references.py create --plan-id my-plan --branch feature/x
    python3 manage-references.py read --plan-id my-plan
    python3 manage-references.py get --plan-id my-plan --field branch
    python3 manage-references.py set --plan-id my-plan --field branch --value feature/x
    python3 manage-references.py add-file --plan-id my-plan --file src/Main.java
    python3 manage-references.py add-list --plan-id my-plan --field affected_files --values file1.md,file2.md
    python3 manage-references.py set-list --plan-id my-plan --field affected_files --values file1.md,file2.md
"""

import argparse

from file_ops import output_toon, safe_main  # type: ignore[import-not-found]
from input_validation import add_plan_id_arg  # type: ignore[import-not-found]


@safe_main
def main() -> int:
    parser = argparse.ArgumentParser(description='Manage references.json files')
    subparsers = parser.add_subparsers(dest='command', required=True)

    # create
    create_parser = subparsers.add_parser('create', help='Create references.json')
    add_plan_id_arg(create_parser)
    create_parser.add_argument('--branch', required=True, help='Git branch name')
    create_parser.add_argument('--issue-url', help='GitHub issue URL')
    create_parser.add_argument('--build-system', help='Build system (maven, gradle, npm)')
    create_parser.add_argument('--domains', help='Comma-separated domain list (e.g., java,documentation)')

    # read
    read_parser = subparsers.add_parser('read', help='Read entire references')
    add_plan_id_arg(read_parser)

    # get
    get_parser = subparsers.add_parser('get', help='Get specific field')
    add_plan_id_arg(get_parser)
    get_parser.add_argument('--field', required=True, help='Field name')

    # set
    set_parser = subparsers.add_parser('set', help='Set specific field')
    add_plan_id_arg(set_parser)
    set_parser.add_argument('--field', required=True, help='Field name')
    set_parser.add_argument('--value', required=True, help='Field value')

    # add-file
    add_file_parser = subparsers.add_parser('add-file', help='Add file to modified_files')
    add_plan_id_arg(add_file_parser)
    add_file_parser.add_argument('--file', required=True, help='File path to add')

    # remove-file
    remove_file_parser = subparsers.add_parser('remove-file', help='Remove file from modified_files')
    add_plan_id_arg(remove_file_parser)
    remove_file_parser.add_argument('--file', required=True, help='File path to remove')

    # add-list
    add_list_parser = subparsers.add_parser('add-list', help='Add multiple values to a list field')
    add_plan_id_arg(add_list_parser)
    add_list_parser.add_argument('--field', required=True, help='List field name')
    add_list_parser.add_argument('--values', required=True, help='Comma-separated values to add')

    # set-list
    set_list_parser = subparsers.add_parser('set-list', help='Set a list field (replaces existing)')
    add_plan_id_arg(set_list_parser)
    set_list_parser.add_argument('--field', required=True, help='List field name')
    set_list_parser.add_argument('--values', required=True, help='Comma-separated values')

    # get-context
    get_context_parser = subparsers.add_parser('get-context', help='Get all references context in one call')
    add_plan_id_arg(get_context_parser)
    get_context_parser.add_argument('--include-files', action='store_true', help='Include full file lists in output')

    args = parser.parse_args()

    # Import command handlers
    from _cmd_context import cmd_get_context
    from _cmd_crud import cmd_create, cmd_get, cmd_read, cmd_set
    from _cmd_list import cmd_add_file, cmd_add_list, cmd_remove_file, cmd_set_list

    # Dispatch to handlers
    handlers = {
        'create': cmd_create,
        'read': cmd_read,
        'get': cmd_get,
        'set': cmd_set,
        'add-file': cmd_add_file,
        'remove-file': cmd_remove_file,
        'add-list': cmd_add_list,
        'set-list': cmd_set_list,
        'get-context': cmd_get_context,
    }

    handler = handlers.get(args.command)
    if handler:
        result = handler(args)
        output_toon(result)
        return 0
    else:
        parser.print_help()
    return 0


if __name__ == '__main__':
    main()

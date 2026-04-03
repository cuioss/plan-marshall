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
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description='Manage references.json files')
    subparsers = parser.add_subparsers(dest='command', required=True)

    # create
    create_parser = subparsers.add_parser('create', help='Create references.json')
    create_parser.add_argument('--plan-id', required=True, help='Plan identifier')
    create_parser.add_argument('--branch', required=True, help='Git branch name')
    create_parser.add_argument('--issue-url', help='GitHub issue URL')
    create_parser.add_argument('--build-system', help='Build system (maven, gradle, npm)')
    create_parser.add_argument('--domains', help='Comma-separated domain list (e.g., java,documentation)')

    # read
    read_parser = subparsers.add_parser('read', help='Read entire references')
    read_parser.add_argument('--plan-id', required=True, help='Plan identifier')

    # get
    get_parser = subparsers.add_parser('get', help='Get specific field')
    get_parser.add_argument('--plan-id', required=True, help='Plan identifier')
    get_parser.add_argument('--field', required=True, help='Field name')

    # set
    set_parser = subparsers.add_parser('set', help='Set specific field')
    set_parser.add_argument('--plan-id', required=True, help='Plan identifier')
    set_parser.add_argument('--field', required=True, help='Field name')
    set_parser.add_argument('--value', required=True, help='Field value')

    # add-file
    add_file_parser = subparsers.add_parser('add-file', help='Add file to modified_files')
    add_file_parser.add_argument('--plan-id', required=True, help='Plan identifier')
    add_file_parser.add_argument('--file', required=True, help='File path to add')

    # remove-file
    remove_file_parser = subparsers.add_parser('remove-file', help='Remove file from modified_files')
    remove_file_parser.add_argument('--plan-id', required=True, help='Plan identifier')
    remove_file_parser.add_argument('--file', required=True, help='File path to remove')

    # add-list
    add_list_parser = subparsers.add_parser('add-list', help='Add multiple values to a list field')
    add_list_parser.add_argument('--plan-id', required=True, help='Plan identifier')
    add_list_parser.add_argument('--field', required=True, help='List field name')
    add_list_parser.add_argument('--values', required=True, help='Comma-separated values to add')

    # set-list
    set_list_parser = subparsers.add_parser('set-list', help='Set a list field (replaces existing)')
    set_list_parser.add_argument('--plan-id', required=True, help='Plan identifier')
    set_list_parser.add_argument('--field', required=True, help='List field name')
    set_list_parser.add_argument('--values', required=True, help='Comma-separated values')

    # get-context
    get_context_parser = subparsers.add_parser('get-context', help='Get all references context in one call')
    get_context_parser.add_argument('--plan-id', required=True, help='Plan identifier')
    get_context_parser.add_argument('--include-files', action='store_true', help='Include full file lists in output')

    args = parser.parse_args()

    # Import command handlers
    from _ref_cmd_context import cmd_get_context
    from _ref_cmd_crud import cmd_create, cmd_get, cmd_read, cmd_set
    from _ref_cmd_list import cmd_add_file, cmd_add_list, cmd_remove_file, cmd_set_list

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
        handler(args)
    else:
        parser.print_help()
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as e:
        from toon_parser import serialize_toon
        print(serialize_toon({'status': 'error', 'error': 'unexpected', 'message': str(e)}), file=sys.stderr)
        sys.exit(1)

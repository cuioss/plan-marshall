#!/usr/bin/env python3
"""
Manage references.json files with field-level access and list management.

Tracks files, branches, and external references for a plan.
Storage: JSON format (.plan/local/plans/{plan_id}/references.json)
Output: TOON format for API responses

Usage:
    python3 manage-references.py create --plan-id EXAMPLE-PLAN --branch feature/x
    python3 manage-references.py read --plan-id EXAMPLE-PLAN
    python3 manage-references.py get --plan-id EXAMPLE-PLAN --field branch
    python3 manage-references.py set --plan-id EXAMPLE-PLAN --field branch --value feature/x
    python3 manage-references.py add-list --plan-id EXAMPLE-PLAN --field affected_files --values file1.md,file2.md
    python3 manage-references.py set-list --plan-id EXAMPLE-PLAN --field affected_files --values file1.md,file2.md
"""

import argparse

from file_ops import output_toon, safe_main  # type: ignore[import-not-found]
from input_validation import (  # type: ignore[import-not-found]
    add_field_arg,
    add_plan_id_arg,
    parse_args_with_toon_errors,
)


@safe_main
def main() -> int:
    parser = argparse.ArgumentParser(description='Manage references.json files', allow_abbrev=False)
    subparsers = parser.add_subparsers(dest='command', required=True)

    # create
    create_parser = subparsers.add_parser('create', help='Create references.json', allow_abbrev=False)
    add_plan_id_arg(create_parser)
    create_parser.add_argument('--branch', required=True, help='Git branch name')
    create_parser.add_argument('--issue-url', help='GitHub issue URL')
    create_parser.add_argument('--build-system', help='Build system (maven, gradle, npm)')
    create_parser.add_argument('--domains', help='Comma-separated domain list (e.g., java,documentation)')

    # read
    read_parser = subparsers.add_parser('read', help='Read entire references', allow_abbrev=False)
    add_plan_id_arg(read_parser)

    # get
    get_parser = subparsers.add_parser('get', help='Get specific field', allow_abbrev=False)
    add_plan_id_arg(get_parser)
    add_field_arg(get_parser)

    # set
    set_parser = subparsers.add_parser('set', help='Set specific field', allow_abbrev=False)
    add_plan_id_arg(set_parser)
    add_field_arg(set_parser)
    set_parser.add_argument('--value', required=True, help='Field value')

    # add-list
    add_list_parser = subparsers.add_parser('add-list', help='Add multiple values to a list field', allow_abbrev=False)
    add_plan_id_arg(add_list_parser)
    add_field_arg(add_list_parser)
    add_list_parser.add_argument('--values', required=True, help='Comma-separated values to add')

    # set-list
    set_list_parser = subparsers.add_parser('set-list', help='Set a list field (replaces existing)', allow_abbrev=False)
    add_plan_id_arg(set_list_parser)
    add_field_arg(set_list_parser)
    set_list_parser.add_argument('--values', required=True, help='Comma-separated values')

    # get-context
    get_context_parser = subparsers.add_parser(
        'get-context', help='Get all references context in one call', allow_abbrev=False
    )
    add_plan_id_arg(get_context_parser)

    # compute-footprint
    compute_footprint_parser = subparsers.add_parser(
        'compute-footprint',
        help='Derive the live plan footprint from the worktree git state (read-only)',
        allow_abbrev=False,
    )
    add_plan_id_arg(compute_footprint_parser)
    compute_footprint_parser.add_argument(
        '--worktree-path',
        required=True,
        help='Absolute path to the active git worktree',
    )
    compute_footprint_parser.add_argument(
        '--base-ref',
        help='Base ref for the diff (defaults to references.base_branch, falling back to main)',
    )

    args = parse_args_with_toon_errors(parser)

    # Import command handlers
    from _cmd_compute_footprint import cmd_compute_footprint
    from _cmd_context import cmd_get_context
    from _cmd_list import cmd_add_list, cmd_set_list
    from _references_crud import cmd_create, cmd_get, cmd_read, cmd_set

    # Dispatch to handlers
    handlers = {
        'create': cmd_create,
        'read': cmd_read,
        'get': cmd_get,
        'set': cmd_set,
        'add-list': cmd_add_list,
        'set-list': cmd_set_list,
        'get-context': cmd_get_context,
        'compute-footprint': cmd_compute_footprint,
    }

    handler = handlers.get(args.command)
    if handler:
        result = handler(args)
        if result is not None:
            output_toon(result)
            # Operation failures (file not found, validation failure, etc.)
            # are reported via the TOON ``status: error`` payload already
            # emitted above and exit 0 — the script ran successfully, only
            # the operation failed. Callers branch on the TOON ``status``
            # field, never on the process exit code. Exit 1 is reserved for
            # genuine script-execution crashes (handled by ``safe_main``).
        return 0
    else:
        parser.print_help()
    return 0


if __name__ == '__main__':
    main()

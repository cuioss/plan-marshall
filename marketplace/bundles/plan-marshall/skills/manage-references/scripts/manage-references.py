#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
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
    python3 manage-references.py sync-affected-files --plan-id EXAMPLE-PLAN
    python3 manage-references.py reconcile-scope --plan-id EXAMPLE-PLAN
"""

import argparse

from file_ops import output_toon, safe_main
from input_validation import (
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

    # sync-affected-files — re-derive the DECLARED footprint from the solution
    # outline's structured per-deliverable data and union it into
    # references.affected_files. Takes no value argument by design: the outline is
    # the input, so there is no CSV for a caller to compose (and therefore none to
    # compose wrongly). It is the write-side counterpart of compute-footprint,
    # which derives the REALIZED footprint from the worktree.
    sync_affected_files_parser = subparsers.add_parser(
        'sync-affected-files',
        help=(
            'Re-derive references.affected_files from the solution outline\'s structured '
            'deliverable data (set union — never removes an already-recorded path)'
        ),
        allow_abbrev=False,
    )
    add_plan_id_arg(sync_affected_files_parser)

    # reconcile-scope — compare the RECORDED declaration
    # (references.affected_files), the DECLARED derivation (the outline's
    # structured mutation-intent paths) and the REALIZED footprint (the shared
    # whole-chain resolver) pairwise, by symmetric difference in both directions.
    # Read-only: it writes no key and emits no finding. Takes no value argument —
    # all three sides are derived, so there is nothing for a caller to supply and
    # therefore nothing to supply wrongly.
    reconcile_scope_parser = subparsers.add_parser(
        'reconcile-scope',
        help=(
            'Reconcile the recorded, declared and realized file sets three ways by '
            'symmetric difference, publishing both difference directions per pair (read-only)'
        ),
        allow_abbrev=False,
    )
    add_plan_id_arg(reconcile_scope_parser)

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

    # capture-footprint — compute the live footprint AND persist it to
    # references.realized_footprint (the capture-while-true side effect).
    capture_footprint_parser = subparsers.add_parser(
        'capture-footprint',
        help='Compute the live plan footprint and persist it to references.realized_footprint',
        allow_abbrev=False,
    )
    add_plan_id_arg(capture_footprint_parser)
    capture_footprint_parser.add_argument(
        '--worktree-path',
        required=True,
        help='Absolute path to the active git worktree (must still exist at capture time)',
    )
    capture_footprint_parser.add_argument(
        '--base-ref',
        help='Base ref for the diff (defaults to references.base_branch, falling back to main)',
    )

    args = parse_args_with_toon_errors(parser)

    # Import command handlers
    from _cmd_compute_footprint import cmd_capture_footprint, cmd_compute_footprint
    from _cmd_context import cmd_get_context
    from _cmd_list import cmd_add_list, cmd_set_list
    from _cmd_reconcile_scope import cmd_reconcile_scope
    from _references_crud import (
        cmd_create,
        cmd_get,
        cmd_read,
        cmd_set,
        cmd_sync_affected_files,
    )

    # Dispatch to handlers
    handlers = {
        'create': cmd_create,
        'read': cmd_read,
        'get': cmd_get,
        'set': cmd_set,
        'add-list': cmd_add_list,
        'set-list': cmd_set_list,
        'sync-affected-files': cmd_sync_affected_files,
        'reconcile-scope': cmd_reconcile_scope,
        'get-context': cmd_get_context,
        'compute-footprint': cmd_compute_footprint,
        'capture-footprint': cmd_capture_footprint,
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

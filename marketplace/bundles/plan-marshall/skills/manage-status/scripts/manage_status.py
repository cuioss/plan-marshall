#!/usr/bin/env python3
"""
Manage status.json files with phase tracking, metadata, and lifecycle operations.

Handles plan status storage (JSON), phase operations, metadata management,
plan discovery, phase transitions, archiving, and routing.
Storage: JSON format (.plan/plans/{plan_id}/status.json)
Output: TOON format for API responses

Usage:
    python3 manage_status.py create --plan-id my-plan --title "Title" --phases 1-init,2-refine,3-outline
    python3 manage_status.py read --plan-id my-plan
    python3 manage_status.py set-phase --plan-id my-plan --phase 2-refine
    python3 manage_status.py update-phase --plan-id my-plan --phase 1-init --status done
    python3 manage_status.py progress --plan-id my-plan
    python3 manage_status.py metadata --plan-id my-plan --set --field change_type --value feature
    python3 manage_status.py metadata --plan-id my-plan --get --field change_type
    python3 manage_status.py get-context --plan-id my-plan
    python3 manage_status.py list
    python3 manage_status.py transition --plan-id my-plan --completed 1-init
    python3 manage_status.py archive --plan-id my-plan
    python3 manage_status.py route --phase 1-init
    python3 manage_status.py get-routing-context --plan-id my-plan
    python3 manage_status.py mark-step-done --plan-id my-plan --phase 5-execute --step discovery --outcome done
"""

import argparse

from _cmd_lifecycle import cmd_archive, cmd_create, cmd_delete_plan, cmd_transition
from _cmd_mark_step import cmd_mark_step_done
from _cmd_routing import cmd_get_routing_context, cmd_route, cmd_self_test
from _status_query import (
    cmd_get_context,
    cmd_list,
    cmd_metadata,
    cmd_progress,
    cmd_read,
    cmd_set_phase,
    cmd_update_phase,
)
from file_ops import output_toon, safe_main  # type: ignore[import-not-found]
from input_validation import add_plan_id_arg  # type: ignore[import-not-found]


@safe_main
def main() -> int:
    parser = argparse.ArgumentParser(description='Manage status.json files with phase tracking and metadata')
    subparsers = parser.add_subparsers(dest='command', required=True)

    # create
    create_parser = subparsers.add_parser('create', help='Create status.json')
    add_plan_id_arg(create_parser)
    create_parser.add_argument('--title', required=True, help='Plan title')
    create_parser.add_argument(
        '--phases',
        required=True,
        help='Comma-separated phase names (e.g., 1-init,2-refine,3-outline,4-plan,5-execute,6-finalize)',
    )
    create_parser.add_argument('--force', action='store_true', help='Overwrite existing status')
    create_parser.set_defaults(func=cmd_create)

    # read
    read_parser = subparsers.add_parser('read', help='Read plan status')
    add_plan_id_arg(read_parser)
    read_parser.set_defaults(func=cmd_read)

    # set-phase
    set_phase_parser = subparsers.add_parser('set-phase', help='Set current phase')
    add_plan_id_arg(set_phase_parser)
    set_phase_parser.add_argument('--phase', required=True, help='Phase name')
    set_phase_parser.set_defaults(func=cmd_set_phase)

    # update-phase
    update_phase_parser = subparsers.add_parser('update-phase', help='Update phase status')
    add_plan_id_arg(update_phase_parser)
    update_phase_parser.add_argument('--phase', required=True, help='Phase name')
    update_phase_parser.add_argument(
        '--status', required=True, choices=['pending', 'in_progress', 'done'], help='Phase status'
    )
    update_phase_parser.set_defaults(func=cmd_update_phase)

    # progress
    progress_parser = subparsers.add_parser('progress', help='Calculate progress')
    add_plan_id_arg(progress_parser)
    progress_parser.set_defaults(func=cmd_progress)

    # metadata
    metadata_parser = subparsers.add_parser('metadata', help='Get or set metadata fields')
    add_plan_id_arg(metadata_parser)
    metadata_parser.add_argument('--get', action='store_true', help='Get metadata field')
    metadata_parser.add_argument('--set', action='store_true', help='Set metadata field')
    metadata_parser.add_argument('--field', required=True, help='Metadata field name')
    metadata_parser.add_argument('--value', help='Metadata field value (required for --set)')
    metadata_parser.set_defaults(func=cmd_metadata)

    # get-context
    get_context_parser = subparsers.add_parser('get-context', help='Get combined status context')
    add_plan_id_arg(get_context_parser)
    get_context_parser.set_defaults(func=cmd_get_context)

    # list
    list_parser = subparsers.add_parser('list', help='Discover all plans')
    list_parser.add_argument('--filter', help='Filter by phases (comma-separated)')
    list_parser.set_defaults(func=cmd_list)

    # transition
    transition_parser = subparsers.add_parser('transition', help='Transition to next phase')
    add_plan_id_arg(transition_parser)
    transition_parser.add_argument('--completed', required=True, help='Completed phase')
    transition_parser.set_defaults(func=cmd_transition)

    # archive
    archive_parser = subparsers.add_parser('archive', help='Archive completed plan')
    add_plan_id_arg(archive_parser)
    archive_parser.add_argument('--dry-run', action='store_true', help='Show what would be done')
    archive_parser.set_defaults(func=cmd_archive)

    # route
    route_parser = subparsers.add_parser('route', help='Get skill for phase')
    route_parser.add_argument('--phase', required=True, help='Phase name')
    route_parser.set_defaults(func=cmd_route)

    # get-routing-context
    routing_context_parser = subparsers.add_parser(
        'get-routing-context', help='Get combined routing context (phase, skill, progress)'
    )
    add_plan_id_arg(routing_context_parser)
    routing_context_parser.set_defaults(func=cmd_get_routing_context)

    # delete-plan
    delete_plan_parser = subparsers.add_parser('delete-plan', help='Delete entire plan directory')
    add_plan_id_arg(delete_plan_parser)
    delete_plan_parser.set_defaults(func=cmd_delete_plan)

    # mark-step-done
    mark_step_parser = subparsers.add_parser(
        'mark-step-done', help='Mark a phase step outcome in status.metadata.phase_steps'
    )
    add_plan_id_arg(mark_step_parser)
    mark_step_parser.add_argument('--phase', required=True, help='Phase name (e.g., 5-execute)')
    mark_step_parser.add_argument('--step', required=True, help='Step identifier within the phase')
    mark_step_parser.add_argument(
        '--outcome', required=True, choices=['done', 'skipped'], help='Step outcome'
    )
    mark_step_parser.add_argument(
        '--force', action='store_true', help='Overwrite an existing conflicting outcome'
    )
    mark_step_parser.add_argument(
        '--display-detail',
        default=None,
        help='One-line user-facing detail string describing the step outcome (required for phase-6-finalize steps).',
    )
    mark_step_parser.set_defaults(func=cmd_mark_step_done)

    # self-test
    self_test_parser = subparsers.add_parser('self-test', help='Verify manage-status health')
    self_test_parser.set_defaults(func=cmd_self_test)

    args = parser.parse_args()
    result = args.func(args)
    if result is not None:
        output_toon(result)
    return 0


if __name__ == '__main__':
    main()

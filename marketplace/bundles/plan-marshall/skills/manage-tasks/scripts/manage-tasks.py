#!/usr/bin/env python3
"""
Manage implementation tasks with sequential sub-steps within a plan.

Single CLI with subcommands for CRUD operations on task files.
Storage: JSON format (TASK-{NNN}.json)
Output: TOON format for LLM-optimized consumption.
Each task references deliverables from solution_outline.md.

Subcommands:
  prepare-add      - Allocate a scratch path for a pending task definition
  commit-add       - Read the prepared file and create TASK-NNN.json
  batch-add        - Atomically create multiple tasks from a JSON array
  update           - Update an existing task
  remove           - Remove a task
  list             - List all tasks (summary)
  read             - Read a single task by number
  exists           - Boolean probe: does a task exist? (never errors on absence)
  next             - Get next pending task/step for execution
  tasks-by-domain  - List tasks filtered by domain
  tasks-by-profile - List tasks filtered by profile
  next-tasks       - Get all tasks ready for parallel execution
  finalize-step    - Complete a step with outcome (done/skipped)
  add-step         - Add a new step to a task
  remove-step      - Remove a step from a task
  rename-path      - Record a path rename mapping

Output: TOON format for all operations.

Add flow (path-allocate pattern — no content crosses the shell boundary):

  1. python3 manage-tasks.py prepare-add --plan-id my-plan [--slot my-slot]
     → returns {path: /abs/.../work/pending-tasks/default.toon}

  2. Write the TOON task definition to the returned path using your native
     Write/Edit tools. Example TOON content:

        title: My Task Title
        deliverable: 1
        domain: java
        steps:
          - src/main/java/File.java
        depends_on: none

  3. python3 manage-tasks.py commit-add --plan-id my-plan [--slot my-slot]
     → reads the file, validates it, creates TASK-NNN.json, deletes the scratch
"""

import argparse

from _cmd_rename import cmd_rename_path
from _cmd_step import cmd_add_step, cmd_finalize_step, cmd_remove_step
from _tasks_crud import cmd_batch_add, cmd_commit_add, cmd_prepare_add, cmd_remove, cmd_update
from _tasks_query import (
    cmd_exists,
    cmd_list,
    cmd_next,
    cmd_next_tasks,
    cmd_read,
    cmd_tasks_by_domain,
    cmd_tasks_by_profile,
)
from file_ops import output_toon, safe_main  # type: ignore[import-not-found]
from input_validation import add_plan_id_arg  # type: ignore[import-not-found]


def build_parser() -> argparse.ArgumentParser:
    """Build argument parser with subcommands."""
    parser = argparse.ArgumentParser(
        description='Manage implementation tasks with sequential sub-steps',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
    )

    subparsers = parser.add_subparsers(dest='command', required=True)

    # prepare-add: allocate a scratch path for a pending task definition
    p_prepare = subparsers.add_parser(
        'prepare-add',
        help='Allocate a scratch path for a pending task definition (Step 1 of add flow)',
        allow_abbrev=False,
    )
    add_plan_id_arg(p_prepare)
    p_prepare.add_argument(
        '--slot',
        default=None,
        help='Optional slot identifier for concurrent prepared tasks (default: "default")',
    )

    # commit-add: read the prepared file and create TASK-NNN.json
    p_commit = subparsers.add_parser(
        'commit-add',
        help='Read the prepared task file and create TASK-NNN.json (Step 3 of add flow)',
        allow_abbrev=False,
    )
    add_plan_id_arg(p_commit)
    p_commit.add_argument(
        '--slot',
        default=None,
        help='Slot identifier matching the prior prepare-add call (default: "default")',
    )

    # batch-add: atomically add multiple tasks from a JSON array
    p_batch = subparsers.add_parser(
        'batch-add',
        help='Atomically add multiple tasks from a JSON array (one transaction)',
        description=(
            'Atomically append every task record in a JSON array to the plan. '
            'Pass the array via --tasks-json, --tasks-file PATH, or stdin '
            '(--tasks-json and --tasks-file are mutually exclusive; stdin is used '
            'when neither flag is given). Validation is performed before any file '
            'is written; on any validation failure no TASK-NNN.json file is created. '
            'On success, sequential TASK numbers are assigned and a single result '
            'describes the created tasks.'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
    )
    add_plan_id_arg(p_batch)
    # --tasks-json and --tasks-file are mutually exclusive. Stdin remains a
    # third independent input that is selected when neither flag is given.
    p_batch_input = p_batch.add_mutually_exclusive_group()
    p_batch_input.add_argument(
        '--tasks-json',
        default=None,
        help='Raw JSON array of task records. Mutually exclusive with --tasks-file.',
    )
    p_batch_input.add_argument(
        '--tasks-file',
        default=None,
        help=(
            'Path to a file containing the JSON array of task records. '
            'Mutually exclusive with --tasks-json. If neither flag is given, '
            'the array is read from stdin.'
        ),
    )

    # update
    p_update = subparsers.add_parser('update', help='Update an existing task', allow_abbrev=False)
    add_plan_id_arg(p_update)
    p_update.add_argument('--task-number', required=True, type=int, help='Task number')
    p_update.add_argument('--title', help='New title')
    p_update.add_argument('--description', help='New description')
    p_update.add_argument('--depends-on', nargs='*', help='Update dependencies (TASK-N references or "none" to clear)')
    p_update.add_argument('--status', help='New status (pending/in_progress/done/blocked)')
    p_update.add_argument('--domain', help='Task domain (e.g., java, javascript)')
    p_update.add_argument('--profile', help='Task profile (arbitrary key from marshal.json)')
    p_update.add_argument('--skills', help='Skills list (comma-separated bundle:skill format)')
    p_update.add_argument('--deliverable', type=int, help='Deliverable number (single integer)')

    # remove
    p_remove = subparsers.add_parser('remove', help='Remove a task', allow_abbrev=False)
    add_plan_id_arg(p_remove)
    p_remove.add_argument('--task-number', required=True, type=int, help='Task number')

    # list
    p_list = subparsers.add_parser(
        'list',
        help='List all tasks (tabular — see description for shape contract)',
        description=(
            'List all tasks in a plan.\n\n'
            'Shape contract — authoritative for downstream callers:\n'
            '  Emits a TABULAR ``tasks_table[N]{...}`` whose reachable fields are\n'
            '  exactly: number, title, domain, profile, deliverable, status,\n'
            '  progress. Rich fields (``depends_on``, ``sub_steps``/``steps``,\n'
            '  ``description``, ``verification``, ``skills``) are NOT reachable\n'
            '  from ``list``. Callers that need them must iterate ``tasks_table``\n'
            '  for task numbers and then call ``read --task-number N`` per task.\n'
            '  Invariants such as ``_capture_task_state_hash`` rely on this\n'
            '  contract.'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
    )
    add_plan_id_arg(p_list)
    p_list.add_argument(
        '--status', choices=['pending', 'in_progress', 'done', 'blocked', 'all'], default='all', help='Filter by status'
    )
    p_list.add_argument('--deliverable', type=int, help='Filter by deliverable number')
    p_list.add_argument('--ready', action='store_true', help='Only show tasks with no unmet dependencies')
    p_read = subparsers.add_parser('read', help='Read a single task', allow_abbrev=False)
    add_plan_id_arg(p_read)
    p_read.add_argument('--task-number', required=True, type=int, help='Task number')

    # exists
    p_exists = subparsers.add_parser(
        'exists',
        help='Check whether a task exists (boolean probe — never errors on absence)',
        description=(
            'Defensive presence probe. Returns ``status: success`` with '
            '``exists: true|false`` for any task number. Use this instead '
            'of ``read`` when you need a boolean check, so a missing task '
            'does not generate a recoverable [ERROR] row in '
            'script-execution.log.'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
    )
    add_plan_id_arg(p_exists)
    p_exists.add_argument('--task-number', required=True, type=int, help='Task number')

    # next
    p_next = subparsers.add_parser('next', help='Get next pending task/step', allow_abbrev=False)
    add_plan_id_arg(p_next)
    p_next.add_argument('--include-context', action='store_true', help='Include deliverable details in output')
    p_next.add_argument('--ignore-deps', action='store_true', help='Ignore dependency constraints')

    # tasks-by-domain
    p_by_domain = subparsers.add_parser(
        'tasks-by-domain', help='List tasks filtered by domain', allow_abbrev=False
    )
    add_plan_id_arg(p_by_domain)
    p_by_domain.add_argument('--domain', required=True, help='Domain to filter by (e.g., java, javascript)')

    # tasks-by-profile
    p_by_profile = subparsers.add_parser(
        'tasks-by-profile', help='List tasks filtered by profile', allow_abbrev=False
    )
    add_plan_id_arg(p_by_profile)
    p_by_profile.add_argument(
        '--profile', required=True, help='Profile to filter by (e.g., implementation, module_testing)'
    )

    # next-tasks
    p_next_tasks = subparsers.add_parser(
        'next-tasks', help='Get all tasks ready for parallel execution', allow_abbrev=False
    )
    add_plan_id_arg(p_next_tasks)

    # finalize-step (consolidates step-done and step-skip)
    p_finalize = subparsers.add_parser(
        'finalize-step', help='Complete a step with outcome (done/skipped/failed)', allow_abbrev=False
    )
    add_plan_id_arg(p_finalize)
    p_finalize.add_argument('--task-number', required=True, type=int, help='Task number')
    p_finalize.add_argument('--step', required=True, type=int, help='Step number')
    p_finalize.add_argument('--outcome', required=True, choices=['done', 'skipped', 'failed'], help='Step outcome')
    p_finalize.add_argument('--reason', help='Reason for skipping or failure (optional)')

    # add-step
    p_add_step = subparsers.add_parser('add-step', help='Add a new step to a task', allow_abbrev=False)
    add_plan_id_arg(p_add_step)
    p_add_step.add_argument('--task-number', required=True, type=int, help='Task number')
    p_add_step.add_argument('--target', required=True, help='Step target (file path or verification command)')
    p_add_step.add_argument('--after', type=int, help='Insert after this step number')

    # remove-step
    p_remove_step = subparsers.add_parser(
        'remove-step', help='Remove a step from a task', allow_abbrev=False
    )
    add_plan_id_arg(p_remove_step)
    p_remove_step.add_argument('--task-number', required=True, type=int, help='Task number')
    p_remove_step.add_argument('--step', required=True, type=int, help='Step number')

    # rename-path
    p_rename = subparsers.add_parser(
        'rename-path', help='Record a path rename mapping', allow_abbrev=False
    )
    add_plan_id_arg(p_rename)
    p_rename.add_argument('--old-path', required=True, help='Original path before rename')
    p_rename.add_argument('--new-path', required=True, help='New path after rename')

    return parser


# Command dispatch map
COMMANDS = {
    'prepare-add': cmd_prepare_add,
    'commit-add': cmd_commit_add,
    'batch-add': cmd_batch_add,
    'update': cmd_update,
    'remove': cmd_remove,
    'list': cmd_list,
    'read': cmd_read,
    'exists': cmd_exists,
    'next': cmd_next,
    'tasks-by-domain': cmd_tasks_by_domain,
    'tasks-by-profile': cmd_tasks_by_profile,
    'next-tasks': cmd_next_tasks,
    'finalize-step': cmd_finalize_step,
    'add-step': cmd_add_step,
    'remove-step': cmd_remove_step,
    'rename-path': cmd_rename_path,
}


@safe_main
def main() -> int:
    """Main entry point."""
    parser = build_parser()
    args = parser.parse_args()

    handler = COMMANDS.get(args.command)
    if handler:
        result = handler(args)
        output_toon(result)
        return 0
    else:
        output_toon({'status': 'error', 'error': 'error', 'message': f'Unknown command: {args.command}'})
        return 1


if __name__ == '__main__':
    main()

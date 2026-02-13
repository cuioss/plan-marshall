#!/usr/bin/env python3
"""
Manage implementation tasks with sequential sub-steps within a plan.

Single CLI with subcommands for CRUD operations on task files.
Storage: JSON format (TASK-{NNN}.json)
Output: TOON format for LLM-optimized consumption.
Each task references deliverables from solution_outline.md.

Subcommands:
  add              - Add a new task (reads task definition from stdin)
  update           - Update an existing task
  remove           - Remove a task
  list             - List all tasks (summary)
  get              - Get a single task by number
  next             - Get next pending task/step for execution
  tasks-by-domain  - List tasks filtered by domain
  tasks-by-profile - List tasks filtered by profile
  next-tasks       - Get all tasks ready for parallel execution
  finalize-step    - Complete a step with outcome (done/skipped)
  add-step         - Add a new step to a task
  remove-step      - Remove a step from a task

Output: TOON format for all operations.

Add command usage (stdin-based API):
  python3 manage-task.py add --plan-id my-plan <<'EOF'
  title: My Task Title
  deliverable: 1
  domain: plan-marshall-plugin-dev
  phase: 5-execute
  description: |
    Task description here
  steps:
    - First step
    - Second step
  depends_on: none
  verification:
    commands:
      - grep -l '```json' *.md | wc -l
    criteria: All grep commands return 0
  EOF
"""

import argparse
import sys

from _cmd_crud import cmd_add, cmd_remove, cmd_update
from _cmd_query import cmd_get, cmd_list, cmd_next, cmd_next_tasks, cmd_tasks_by_domain, cmd_tasks_by_profile
from _cmd_step import cmd_add_step, cmd_finalize_step, cmd_remove_step
from _manage_tasks_shared import output_error


def build_parser() -> argparse.ArgumentParser:
    """Build argument parser with subcommands."""
    parser = argparse.ArgumentParser(
        description='Manage implementation tasks with sequential sub-steps',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest='command', required=True)

    # add (stdin-based API)
    p_add = subparsers.add_parser('add', help='Add a new task (reads definition from stdin)')
    p_add.add_argument('--plan-id', required=True, help='Plan identifier')

    # update
    p_update = subparsers.add_parser('update', help='Update an existing task')
    p_update.add_argument('--plan-id', required=True, help='Plan identifier')
    p_update.add_argument('--number', required=True, type=int, help='Task number')
    p_update.add_argument('--title', help='New title')
    p_update.add_argument('--description', help='New description')
    p_update.add_argument('--depends-on', nargs='*', help='Update dependencies (TASK-N references or "none" to clear)')
    p_update.add_argument('--status', help='New status (pending/in_progress/done/blocked)')
    p_update.add_argument('--domain', help='Task domain (e.g., java, javascript)')
    p_update.add_argument('--profile', help='Task profile (arbitrary key from marshal.json)')
    p_update.add_argument('--skills', help='Skills list (comma-separated bundle:skill format)')
    p_update.add_argument('--deliverable', type=int, help='Deliverable number (single integer)')

    # remove
    p_remove = subparsers.add_parser('remove', help='Remove a task')
    p_remove.add_argument('--plan-id', required=True, help='Plan identifier')
    p_remove.add_argument('--number', required=True, type=int, help='Task number')

    # list
    p_list = subparsers.add_parser('list', help='List all tasks')
    p_list.add_argument('--plan-id', required=True, help='Plan identifier')
    p_list.add_argument(
        '--status', choices=['pending', 'in_progress', 'done', 'blocked', 'all'], default='all', help='Filter by status'
    )
    p_list.add_argument(
        '--phase',
        choices=['1-init', '2-refine', '3-outline', '4-plan', '5-execute', '6-verify', '7-finalize'],
        help='Filter by phase',
    )
    p_list.add_argument('--deliverable', type=int, help='Filter by deliverable number')
    p_list.add_argument('--ready', action='store_true', help='Only show tasks with no unmet dependencies')

    # get
    p_get = subparsers.add_parser('get', help='Get a single task')
    p_get.add_argument('--plan-id', required=True, help='Plan identifier')
    p_get.add_argument('--number', required=True, type=int, help='Task number')

    # next
    p_next = subparsers.add_parser('next', help='Get next pending task/step')
    p_next.add_argument('--plan-id', required=True, help='Plan identifier')
    p_next.add_argument(
        '--phase',
        choices=['1-init', '2-refine', '3-outline', '4-plan', '5-execute', '6-verify', '7-finalize'],
        help='Filter by phase',
    )
    p_next.add_argument('--include-context', action='store_true', help='Include deliverable details in output')
    p_next.add_argument('--ignore-deps', action='store_true', help='Ignore dependency constraints')

    # tasks-by-domain
    p_by_domain = subparsers.add_parser('tasks-by-domain', help='List tasks filtered by domain')
    p_by_domain.add_argument('--plan-id', required=True, help='Plan identifier')
    p_by_domain.add_argument('--domain', required=True, help='Domain to filter by (e.g., java, javascript)')

    # tasks-by-profile
    p_by_profile = subparsers.add_parser('tasks-by-profile', help='List tasks filtered by profile')
    p_by_profile.add_argument('--plan-id', required=True, help='Plan identifier')
    p_by_profile.add_argument(
        '--profile', required=True, help='Profile to filter by (e.g., implementation, module_testing)'
    )

    # next-tasks
    p_next_tasks = subparsers.add_parser('next-tasks', help='Get all tasks ready for parallel execution')
    p_next_tasks.add_argument('--plan-id', required=True, help='Plan identifier')

    # finalize-step (consolidates step-done and step-skip)
    p_finalize = subparsers.add_parser('finalize-step', help='Complete a step with outcome (done/skipped)')
    p_finalize.add_argument('--plan-id', required=True, help='Plan identifier')
    p_finalize.add_argument('--task', required=True, type=int, help='Task number')
    p_finalize.add_argument('--step', required=True, type=int, help='Step number')
    p_finalize.add_argument('--outcome', required=True, choices=['done', 'skipped'], help='Step outcome')
    p_finalize.add_argument('--reason', help='Reason for skipping (optional, for skipped steps)')

    # add-step
    p_add_step = subparsers.add_parser('add-step', help='Add a new step to a task')
    p_add_step.add_argument('--plan-id', required=True, help='Plan identifier')
    p_add_step.add_argument('--task', required=True, type=int, help='Task number')
    p_add_step.add_argument('--target', required=True, help='Step target (file path or verification command)')
    p_add_step.add_argument('--after', type=int, help='Insert after this step number')

    # remove-step
    p_remove_step = subparsers.add_parser('remove-step', help='Remove a step from a task')
    p_remove_step.add_argument('--plan-id', required=True, help='Plan identifier')
    p_remove_step.add_argument('--task', required=True, type=int, help='Task number')
    p_remove_step.add_argument('--step', required=True, type=int, help='Step number')

    return parser


# Command dispatch map
COMMANDS = {
    'add': cmd_add,
    'update': cmd_update,
    'remove': cmd_remove,
    'list': cmd_list,
    'get': cmd_get,
    'next': cmd_next,
    'tasks-by-domain': cmd_tasks_by_domain,
    'tasks-by-profile': cmd_tasks_by_profile,
    'next-tasks': cmd_next_tasks,
    'finalize-step': cmd_finalize_step,
    'add-step': cmd_add_step,
    'remove-step': cmd_remove_step,
}


def main() -> int:
    """Main entry point."""
    parser = build_parser()
    args = parser.parse_args()

    try:
        handler = COMMANDS.get(args.command)
        if handler:
            return handler(args)
        else:
            output_error(f'Unknown command: {args.command}')
            return 1
    except Exception as e:
        output_error(str(e))
        return 1


if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
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
  list             - List all tasks (summary; supports --domain / --profile filters)
  read             - Read a single task by number
  exists           - Boolean probe: does a task exist? (never errors on absence)
  next             - Get next pending task/step for execution
  next-tasks       - Get all tasks ready for parallel execution
  finalize-step    - Complete a step with outcome (done/skipped)
  add-step         - Add a new step to a task
  remove-step      - Remove a step from a task
  rename-path      - Record a path rename mapping
  loop-exit-guard  - Script-level enforcement that the phase-5-execute
                     dispatch loop MUST continue while pending tasks remain
  pre-commit-verify-freshness
                   - Script-level enforcement that the worktree state has
                     been observed by a fresh ``verify`` run before the
                     orchestrator may transition out of phase-5-execute or
                     dispatch ``commit-push`` in phase-6-finalize. Returns
                     ``fresh``, ``stale``, or ``undecidable``; non-``fresh``
                     statuses are gate failures (fail-closed contract)
  derive-cost-size - Deterministically derive a task's cost_size (S/M/L/XL) and
                     predicted_cost_tokens from plan-time signals (step count,
                     profile, skills count, distinct target-file count).
                     Implements phase-4-plan/standards/cost-sizing.md
  pack-envelopes   - Pack the plan's sized tasks (number order) into
                     budget-bounded execution envelope groups under
                     --per-envelope-budget-tokens, assigning each task an
                     envelope_id. Consumes the predicted_cost_tokens stamped
                     by derive-cost-size

Output: TOON format for all operations.

Add flow (path-allocate pattern — no content crosses the shell boundary):

  1. python3 manage-tasks.py prepare-add --plan-id EXAMPLE-PLAN [--slot my-slot]
     → returns {path: /abs/.../work/pending-tasks/default.toon}

  2. Write the TOON task definition to the returned path using your native
     Write/Edit tools. Example TOON content:

        title: My Task Title
        deliverable: 1
        domain: java
        steps:
          - src/main/java/File.java
        depends_on: none

  3. python3 manage-tasks.py commit-add --plan-id EXAMPLE-PLAN [--slot my-slot]
     → reads the file, validates it, creates TASK-NNN.json, deletes the scratch

Validation: Lesson-ID References (commit-add and batch-add)
-----------------------------------------------------------
Both write paths (``commit-add`` and ``batch-add``) scan each task's
``title`` and ``description`` for lesson-ID-shaped tokens
(``YYYY-MM-DD-HH-N+``) using ``scan_lesson_id_tokens`` from
``tools-input-validation``, then verify every token against the live
``manage-lessons`` inventory via ``verify_lesson_ids_exist``. On ANY
unresolved ID the entire write is aborted atomically — no ``TASK-NNN.json``
file is created. The error response carries
``status: error / validation_error: lesson_id_not_found / unresolved_ids:
<list> / task_index: <N>`` so the caller can correct the plan before
re-attempting. The lesson inventory is the single source of truth — neither
write path auto-rewrites descriptions nor downgrades the failure to a
warning. The rationale: plan-authoring once emitted tasks that named lesson
IDs which did not exist in the inventory.
"""

import argparse

from _cmd_cost import cmd_derive_cost_size
from _cmd_envelope import cmd_pack_envelopes
from _cmd_pre_commit_verify_freshness import cmd_pre_commit_verify_freshness
from _cmd_qgate_mechanical import cmd_qgate_mechanical
from _cmd_rename import cmd_rename_path
from _cmd_step import cmd_add_step, cmd_finalize_step, cmd_remove_step, cmd_update_step
from _tasks_crud import cmd_batch_add, cmd_commit_add, cmd_prepare_add, cmd_remove, cmd_update
from _tasks_query import (
    cmd_exists,
    cmd_list,
    cmd_loop_exit_guard,
    cmd_next,
    cmd_next_tasks,
    cmd_read,
)
from constants import VALID_STEP_INTENTS  # type: ignore[import-not-found]
from file_ops import output_toon, safe_main  # type: ignore[import-not-found]
from input_validation import (  # type: ignore[import-not-found]
    add_domain_arg,
    add_plan_id_arg,
    add_task_number_arg,
    parse_args_with_toon_errors,
)


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
    add_task_number_arg(p_update)
    p_update.add_argument('--title', help='New title')
    p_update.add_argument('--description', help='New description')
    p_update.add_argument('--depends-on', nargs='*', help='Update dependencies (TASK-N references or "none" to clear)')
    p_update.add_argument('--status', help='New status (pending/in_progress/done/blocked/infeasible)')
    add_domain_arg(p_update, required=False)
    p_update.add_argument('--profile', help='Task profile (arbitrary key from marshal.json)')
    p_update.add_argument('--skills', help='Skills list (comma-separated bundle:skill format)')
    p_update.add_argument('--deliverable', type=int, help='Deliverable number (single integer)')
    # Cost-field write-back (the only persistence path for the T-shirt cost
    # mechanism — the derive-cost-size / pack-envelopes compute verbs stay pure).
    p_update.add_argument(
        '--cost-size',
        dest='cost_size',
        default=None,
        help='Persist the derived T-shirt cost size (one of S/M/L/XL) onto the task record',
    )
    p_update.add_argument(
        '--predicted-cost-tokens',
        dest='predicted_cost_tokens',
        type=int,
        default=None,
        help='Persist the derived predicted token cost (non-negative integer) onto the task record',
    )
    p_update.add_argument(
        '--envelope-id',
        dest='envelope_id',
        type=int,
        default=None,
        help='Persist the assigned execution envelope id (1-based positive integer) onto the task record',
    )

    # remove
    p_remove = subparsers.add_parser('remove', help='Remove a task', allow_abbrev=False)
    add_plan_id_arg(p_remove)
    add_task_number_arg(p_remove)

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
        '--status',
        choices=['pending', 'in_progress', 'done', 'blocked', 'infeasible', 'all'],
        default='all',
        help='Filter by status',
    )
    p_list.add_argument('--deliverable', type=int, help='Filter by deliverable number')
    p_list.add_argument('--ready', action='store_true', help='Only show tasks with no unmet dependencies')
    add_domain_arg(p_list, required=False)
    p_list.add_argument('--profile', help='Filter by profile (e.g., implementation, module_testing)')
    # read (get is an accepted alias for the same operation)
    p_read = subparsers.add_parser('read', aliases=['get'], help='Read a single task', allow_abbrev=False)
    add_plan_id_arg(p_read)
    add_task_number_arg(p_read)

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
    add_task_number_arg(p_exists)

    # next
    p_next = subparsers.add_parser('next', help='Get next pending task/step', allow_abbrev=False)
    add_plan_id_arg(p_next)
    p_next.add_argument('--include-context', action='store_true', help='Include deliverable details in output')
    p_next.add_argument('--ignore-deps', action='store_true', help='Ignore dependency constraints')

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
    add_task_number_arg(p_finalize)
    p_finalize.add_argument('--step', required=True, type=int, help='Step number')
    p_finalize.add_argument('--outcome', required=True, choices=['done', 'skipped', 'failed'], help='Step outcome')
    p_finalize.add_argument('--reason', help='Reason for skipping or failure (optional)')
    # Optional overrides for the script-level [OUTCOME] emission. The defaults
    # cover the common phase-5-execute path; non-default values let other
    # orchestrators (or tests) shape the emitted line. See _cmd_step.py
    # (cmd_finalize_step) for the contract.
    p_finalize.add_argument(
        '--outcome-task-title',
        dest='outcome_task_title',
        default=None,
        help='Override the task title rendered in the [OUTCOME] log line (default: task.title from disk).',
    )
    p_finalize.add_argument(
        '--outcome-step-count',
        dest='outcome_step_count',
        type=int,
        default=None,
        help='Override the step count rendered in the [OUTCOME] log line (default: len(task.steps)).',
    )
    p_finalize.add_argument(
        '--outcome-caller',
        dest='outcome_caller',
        default=None,
        help=(
            'Override the bundle:skill caller marker rendered in the [OUTCOME] log line '
            '(default: plan-marshall:phase-5-execute).'
        ),
    )

    # add-step
    p_add_step = subparsers.add_parser('add-step', help='Add a new step to a task', allow_abbrev=False)
    add_plan_id_arg(p_add_step)
    add_task_number_arg(p_add_step)
    p_add_step.add_argument('--target', required=True, help='Step target (file path or verification command)')
    p_add_step.add_argument(
        '--intent',
        required=True,
        choices=list(VALID_STEP_INTENTS),
        help='Required per-step existence intent (read|write-new|write-replace|delete)',
    )
    p_add_step.add_argument('--after', type=int, help='Insert after this step number')

    # update-step (sanctioned intent-override escape hatch — usable from
    # execution AND finding-triage; hand-editing a stored intent is a contract
    # violation)
    p_update_step = subparsers.add_parser(
        'update-step',
        help='Override a step intent with a mandatory recorded reason (sanctioned escape hatch)',
        allow_abbrev=False,
    )
    add_plan_id_arg(p_update_step)
    add_task_number_arg(p_update_step)
    p_update_step.add_argument('--step-number', required=True, type=int, help='Step number to update')
    p_update_step.add_argument(
        '--intent',
        required=True,
        choices=list(VALID_STEP_INTENTS),
        help='New per-step intent (read|write-new|write-replace|delete)',
    )
    p_update_step.add_argument('--reason', required=True, help='Mandatory rationale for the intent override (persisted)')
    p_update_step.add_argument(
        '--finding-id', help='Optional manage-findings finding id linking a triage-driven override'
    )

    # remove-step
    p_remove_step = subparsers.add_parser('remove-step', help='Remove a step from a task', allow_abbrev=False)
    add_plan_id_arg(p_remove_step)
    add_task_number_arg(p_remove_step)
    p_remove_step.add_argument('--step', required=True, type=int, help='Step number')

    # rename-path
    p_rename = subparsers.add_parser('rename-path', help='Record a path rename mapping', allow_abbrev=False)
    add_plan_id_arg(p_rename)
    p_rename.add_argument('--old-path', required=True, help='Original path before rename')
    p_rename.add_argument('--new-path', required=True, help='New path after rename')

    # qgate-mechanical-checks
    p_qgate = subparsers.add_parser(
        'qgate-mechanical-checks',
        help='Run deterministic Q-Gate checks for phase-4-plan Step 9 (no LLM dispatch)',
        description=(
            'Run the six deterministic Q-Gate checks over the just-written tasks '
            'and parent deliverables: coverage, skill-resolution, acyclic, '
            'files-exist, keyword-drift, structural-token-drift. Each failure is '
            'emitted as a Q-Gate finding under --source qgate so phase-4-plan\'s '
            'existing aggregate loop consumes it without modification. Pure regex '
            '+ graph + filesystem; no LLM dispatch. Use --no-emit to inspect the '
            'check results without writing findings.'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
    )
    add_plan_id_arg(p_qgate)
    p_qgate.add_argument(
        '--no-emit',
        action='store_true',
        help='Run the checks and return the result TOON without writing any findings (dry-run).',
    )

    # loop-exit-guard
    p_loop_guard = subparsers.add_parser(
        'loop-exit-guard',
        help='Script-level enforcement: continue dispatch loop while pending tasks remain',
        description=(
            'Read the pending-task count via the same machinery as '
            '``list --status pending`` and emit a structured TOON result the '
            'orchestrator MUST consult before exiting the phase-5-execute '
            'dispatch loop. Emits ``status: continue`` (with ``pending_count`` '
            'and ``pending_ids``) when pending > 0 — the non-success status '
            'forces the orchestrator to re-dispatch. Emits ``status: success`` '
            '(with ``pending_count: 0``) only when the queue is genuinely '
            'empty. This is the script-level enforcement of the '
            '"pending > 0 → must continue" invariant; the phase-5-execute '
            'SKILL.md prose is a thin pointer to this verb.'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
    )
    add_plan_id_arg(p_loop_guard)

    # pre-commit-verify-freshness
    p_freshness = subparsers.add_parser(
        'pre-commit-verify-freshness',
        help='Script-level enforcement: worktree state must be observed by a fresh build run',
        description=(
            'Query the unified change-ledger for a ``kind=build`` entry whose '
            '``exit_code == 0`` and whose ``worktree_sha`` equals the CURRENT '
            'working-tree currency hash. The query is build-tool-agnostic and '
            'tier-agnostic: it filters on ``kind``, ``exit_code`` and '
            '``worktree_sha`` only — never ``notation`` or ``plan_id`` — so a '
            'Maven/Gradle/npm build, or an orchestrator-driven global-tier build '
            'with ``plan_id: null``, satisfies the gate exactly as a plan-scoped '
            'build does. The primitive is the *working-tree* currency '
            '(uncommitted staged+unstaged+untracked state), NOT the committed '
            '``HEAD``: this is a pre-commit gate, so a HEAD-sha primitive would '
            'match trivially regardless of uncommitted edits and produce a '
            'false-positive ``fresh``. Returns ``status: fresh`` when a matching '
            'successful build entry exists, ``status: stale`` when the ledger has '
            'entries but none matches the current working-tree sha (the worktree '
            'has been mutated since the last observed build), and '
            '``status: undecidable`` when no positive proof can be established '
            '(``reason: no_registry`` — ledger absent/empty; '
            '``reason: head_unresolvable`` — working-tree sha undefined). The '
            'gate is fail-closed: only ``fresh`` permits transition. Wired as a '
            'precondition by ``phase-5-execute`` Step 12a and ``phase-6-finalize`` '
            '``commit-push``.'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
    )
    add_plan_id_arg(p_freshness)

    # derive-cost-size
    p_cost = subparsers.add_parser(
        'derive-cost-size',
        help='Derive a task cost_size (S/M/L/XL) and predicted_cost_tokens from plan-time signals',
        description=(
            'Deterministically derive a task\'s T-shirt cost size and predicted '
            'token cost from the plan-time signals already present on the task '
            'record: --step-count (dominant), --profile, --skills-count, and '
            '--target-file-count. Build count is excluded (builds are '
            'token-cheap). The size->token table may be injected via --size-table '
            '(JSON object S/M/L/XL -> magnitude); when omitted the canonical '
            'rubric default is used. Emits {status, cost_size, '
            'predicted_cost_tokens}. Implements '
            'phase-4-plan/standards/cost-sizing.md.'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
    )
    p_cost.add_argument('--step-count', dest='step_count', required=True, type=int, help='len(task.steps) (dominant)')
    p_cost.add_argument('--profile', required=True, help='Task profile (implementation/module_testing/verification)')
    p_cost.add_argument('--skills-count', dest='skills_count', required=True, type=int, help='len(task.skills)')
    p_cost.add_argument(
        '--target-file-count',
        dest='target_file_count',
        required=True,
        type=int,
        help='Count of distinct steps[].target values',
    )
    p_cost.add_argument(
        '--size-table',
        dest='size_table',
        default=None,
        help='Optional JSON object mapping S/M/L/XL to a token magnitude (default: rubric table)',
    )

    # pack-envelopes
    p_envelope = subparsers.add_parser(
        'pack-envelopes',
        help='Pack the plan\'s sized tasks into budget-bounded execution envelope groups',
        description=(
            'Deterministically pack the plan\'s tasks (number order) into '
            'execution envelope groups bounded by --per-envelope-budget-tokens. '
            'Each task must already carry a predicted_cost_tokens magnitude '
            '(stamped by derive-cost-size); the packer sums those values via '
            'Next-Fit in task order and never re-derives a task\'s cost. A task '
            'whose cost alone exceeds the budget lands alone in its envelope. '
            'Emits {status, per_envelope_budget_tokens, envelope_count, '
            'assignments_table, envelopes_table}. The size->token mapping is '
            'owned by phase-4-plan/standards/cost-sizing.md.'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
    )
    add_plan_id_arg(p_envelope)
    p_envelope.add_argument(
        '--per-envelope-budget-tokens',
        dest='per_envelope_budget_tokens',
        required=True,
        type=int,
        help='Per-envelope token ceiling (config: plan.phase-5-execute.per_envelope_budget_tokens)',
    )

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
    'get': cmd_read,  # accepted alias for 'read' (argparse subparser alias → same handler)
    'exists': cmd_exists,
    'next': cmd_next,
    'next-tasks': cmd_next_tasks,
    'finalize-step': cmd_finalize_step,
    'add-step': cmd_add_step,
    'update-step': cmd_update_step,
    'remove-step': cmd_remove_step,
    'rename-path': cmd_rename_path,
    'qgate-mechanical-checks': cmd_qgate_mechanical,
    'loop-exit-guard': cmd_loop_exit_guard,
    'pre-commit-verify-freshness': cmd_pre_commit_verify_freshness,
    'derive-cost-size': cmd_derive_cost_size,
    'pack-envelopes': cmd_pack_envelopes,
}


@safe_main
def main() -> int:
    """Main entry point."""
    parser = build_parser()
    args = parse_args_with_toon_errors(parser)

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

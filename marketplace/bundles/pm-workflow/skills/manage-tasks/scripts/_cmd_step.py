#!/usr/bin/env python3
"""
Step management command handlers for manage-tasks.py.

Contains: finalize-step, add-step, remove-step subcommands.
"""

from _manage_tasks_shared import (
    calculate_progress,
    find_task_file,
    format_task_file,
    get_tasks_dir,
    now_iso,
    output_error,
    output_toon,
    parse_task_file,
)
from file_ops import atomic_write_file  # type: ignore[import-not-found]
from plan_logging import log_entry  # type: ignore[import-not-found]


def cmd_finalize_step(args) -> int:
    """Handle 'finalize-step' subcommand.

    Consolidates step-done and step-skip into a single command with --outcome parameter.
    Marks step with outcome (done/skipped), auto-advances current_step, and
    auto-completes task if all steps are finished.

    Returns structured output with:
    - finalized: details of the completed step
    - next_step: next pending step (or null)
    - task_complete: whether all steps are done
    - progress: "completed/total" string
    """
    task_dir = get_tasks_dir(args.plan_id)

    filepath = find_task_file(task_dir, args.task)
    if not filepath:
        output_error(f'Task TASK-{args.task} not found')
        return 1

    content = filepath.read_text(encoding='utf-8')
    task = parse_task_file(content)

    steps = task.get('steps', [])
    step_found = None
    for step in steps:
        if step['number'] == args.step:
            step_found = step
            break

    if not step_found:
        output_error(f'Step {args.step} not found in TASK-{args.task}')
        return 1

    # Mark step with outcome
    step_found['status'] = args.outcome
    task['status'] = 'in_progress'
    task['updated'] = now_iso()

    # Check if all steps are complete
    all_done = all(s['status'] in ('done', 'skipped') for s in steps)

    # Find next pending step
    next_step_info = None
    for step in steps:
        if step['status'] == 'pending':
            next_step_info = {'number': step['number'], 'title': step['title']}
            break

    # Update task state
    if all_done:
        task['status'] = 'done'
        task['current_step'] = len(steps)
    elif next_step_info:
        task['current_step'] = next_step_info['number']

    new_content = format_task_file(task)
    atomic_write_file(filepath, new_content)

    # Logging
    if all_done:
        log_entry('work', args.plan_id, 'INFO', f'[MANAGE-TASKS] Completed TASK-{args.task:03d}')
    else:
        log_entry('work', args.plan_id, 'INFO', f'[MANAGE-TASKS] TASK-{args.task:03d} step {args.step} {args.outcome}')

    # Calculate progress
    completed, total = calculate_progress(task)

    result = {
        'status': 'success',
        'plan_id': args.plan_id,
        'finalized': {
            'step_number': args.step,
            'step_title': step_found['title'],
            'outcome': args.outcome,
        },
        'next_step': next_step_info,
        'task_complete': all_done,
        'task_status': task['status'],
        'progress': f'{completed}/{total}',
    }

    # Include reason if provided (for skipped steps)
    if getattr(args, 'reason', None):
        result['finalized']['reason'] = args.reason

    output_toon(result)
    return 0


def cmd_add_step(args) -> int:
    """Handle 'add-step' subcommand."""
    task_dir = get_tasks_dir(args.plan_id)

    filepath = find_task_file(task_dir, args.task)
    if not filepath:
        output_error(f'Task TASK-{args.task} not found')
        return 1

    content = filepath.read_text(encoding='utf-8')
    task = parse_task_file(content)

    steps = task.get('steps', [])

    if args.after is not None:
        insert_pos = args.after
        if insert_pos < 0 or insert_pos > len(steps):
            output_error(f'Invalid position: after step {insert_pos}')
            return 1
    else:
        insert_pos = len(steps)

    new_step = {'number': insert_pos + 1, 'title': args.title, 'status': 'pending'}

    steps.insert(insert_pos, new_step)
    for i, step in enumerate(steps):
        step['number'] = i + 1

    task['steps'] = steps
    task['updated'] = now_iso()

    new_content = format_task_file(task)
    atomic_write_file(filepath, new_content)

    output_toon(
        {
            'status': 'success',
            'plan_id': args.plan_id,
            'task_number': args.task,
            'step': new_step['number'],
            'step_title': new_step['title'],
            'message': f'Step added at position {new_step["number"]}',
        }
    )
    return 0


def cmd_remove_step(args) -> int:
    """Handle 'remove-step' subcommand."""
    task_dir = get_tasks_dir(args.plan_id)

    filepath = find_task_file(task_dir, args.task)
    if not filepath:
        output_error(f'Task TASK-{args.task} not found')
        return 1

    content = filepath.read_text(encoding='utf-8')
    task = parse_task_file(content)

    steps = task.get('steps', [])

    step_index = None
    removed_step = None
    for i, step in enumerate(steps):
        if step['number'] == args.step:
            step_index = i
            removed_step = step
            break

    if step_index is None:
        output_error(f'Step {args.step} not found in TASK-{args.task}')
        return 1

    if len(steps) <= 1:
        output_error('Cannot remove the last step - task must have at least one step')
        return 1

    steps.pop(step_index)
    for i, step in enumerate(steps):
        step['number'] = i + 1

    task['steps'] = steps
    task['updated'] = now_iso()

    if task.get('current_step', 1) > len(steps):
        task['current_step'] = len(steps)

    new_content = format_task_file(task)
    atomic_write_file(filepath, new_content)

    # removed_step is guaranteed to be set since step_index is not None
    assert removed_step is not None
    output_toon(
        {
            'status': 'success',
            'plan_id': args.plan_id,
            'task_number': args.task,
            'step': args.step,
            'step_title': removed_step['title'],
            'message': f'Step {args.step} removed',
        }
    )
    return 0

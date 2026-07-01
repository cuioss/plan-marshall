#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""
Step management command handlers for manage-tasks.py.

Contains: finalize-step, add-step, remove-step subcommands.
"""

from _tasks_core import (
    calculate_progress,
    find_task_file,
    format_task_file,
    get_tasks_dir,
    normalize_step_path,
    output_error,
    parse_task_file,
    validate_step_intent,
)
from file_ops import atomic_write_file  # type: ignore[import-not-found]
from plan_logging import log_entry  # type: ignore[import-not-found]


def cmd_finalize_step(args) -> dict:
    """Handle 'finalize-step' subcommand.

    Consolidates step-done, step-skip, and step-fail into a single command with --outcome parameter.
    Marks step with outcome (done/skipped/failed), auto-advances current_step, and
    auto-completes task if all steps are finished. Task status is 'failed' when any step failed.

    Returns structured output with:
    - finalized: details of the completed step
    - next_step: next pending step (or null)
    - task_complete: whether all steps are done
    - progress: "completed/total" string
    """
    task_dir = get_tasks_dir(args.plan_id)

    filepath = find_task_file(task_dir, args.task_number)
    if not filepath:
        return output_error(f'Task TASK-{args.task_number} not found')

    content = filepath.read_text(encoding='utf-8')
    task = parse_task_file(content)

    steps = task.get('steps', [])
    step_found = None
    for step in steps:
        if step['number'] == args.step:
            step_found = step
            break

    if not step_found:
        return output_error(f'Step {args.step} not found in TASK-{args.task_number}')

    # Mark step with outcome
    step_found['status'] = args.outcome
    task['status'] = 'in_progress'

    # Check if all steps are terminal (done, skipped, or failed)
    terminal_statuses = ('done', 'skipped', 'failed')
    all_terminal = all(s['status'] in terminal_statuses for s in steps)
    has_failed = any(s['status'] == 'failed' for s in steps)

    # Find next pending step
    next_step_info = None
    for step in steps:
        if step['status'] == 'pending':
            next_step_info = {'number': step['number'], 'target': step['target']}
            break

    # Update task state
    if all_terminal:
        task['status'] = 'failed' if has_failed else 'done'
        task['current_step'] = len(steps)
    elif next_step_info:
        task['current_step'] = next_step_info['number']

    new_content = format_task_file(task)
    atomic_write_file(filepath, new_content)

    # Logging
    if all_terminal and has_failed:
        log_entry(
            'work', args.plan_id, 'WARNING', f'[MANAGE-TASKS] TASK-{args.task_number:03d} failed (has failed steps)'
        )
    elif all_terminal:
        log_entry('work', args.plan_id, 'INFO', f'[MANAGE-TASKS] Completed TASK-{args.task_number:03d}')
    else:
        log_entry(
            'work', args.plan_id, 'INFO', f'[MANAGE-TASKS] TASK-{args.task_number:03d} step {args.step} {args.outcome}'
        )

    # Script-level [OUTCOME] guard: emit a single canonical [OUTCOME] work-log
    # entry whenever a finalize-step call closes a task as `done` via
    # `--outcome done`. This guard runs unconditionally inside the script
    # boundary so the line cannot be lost when an orchestrator skill
    # re-dispatches a phase-5-execute agent and the original agent's working
    # context is discarded before its own [OUTCOME] emission would fire.
    if args.outcome == 'done' and all_terminal and not has_failed:
        caller = getattr(args, 'outcome_caller', None) or 'plan-marshall:phase-5-execute'
        title = getattr(args, 'outcome_task_title', None) or task.get('title', '')
        step_count = getattr(args, 'outcome_step_count', None)
        if step_count is None:
            step_count = len(steps)
        log_entry(
            'work',
            args.plan_id,
            'INFO',
            f'[OUTCOME] ({caller}) Completed TASK-{args.task_number:03d}: {title} ({step_count} steps)',
        )

    # Calculate progress
    completed, total = calculate_progress(task)

    result = {
        'status': 'success',
        'plan_id': args.plan_id,
        'finalized': {
            'step_number': args.step,
            'step_target': step_found['target'],
            'outcome': args.outcome,
        },
        'next_step': next_step_info,
        'task_complete': all_terminal,
        'task_status': task['status'],
        'progress': f'{completed}/{total}',
    }

    # Include reason if provided (for skipped or failed steps)
    if getattr(args, 'reason', None):
        result['finalized']['reason'] = args.reason

    return result


def cmd_add_step(args) -> dict:
    """Handle 'add-step' subcommand."""
    task_dir = get_tasks_dir(args.plan_id)

    filepath = find_task_file(task_dir, args.task_number)
    if not filepath:
        return output_error(f'Task TASK-{args.task_number} not found')

    content = filepath.read_text(encoding='utf-8')
    task = parse_task_file(content)

    steps = task.get('steps', [])

    if args.after is not None:
        insert_pos = args.after
        if insert_pos < 0 or insert_pos > len(steps):
            return output_error(f'Invalid position: after step {insert_pos}')
    else:
        insert_pos = len(steps)

    try:
        step_intent = validate_step_intent(getattr(args, 'intent', None))
    except ValueError as e:
        return output_error(str(e))

    new_step = {
        'number': insert_pos + 1,
        'target': normalize_step_path(args.target),
        'status': 'pending',
        'intent': step_intent,
    }

    steps.insert(insert_pos, new_step)
    for i, step in enumerate(steps):
        step['number'] = i + 1

    task['steps'] = steps

    new_content = format_task_file(task)
    atomic_write_file(filepath, new_content)

    return {
        'status': 'success',
        'plan_id': args.plan_id,
        'task_number': args.task_number,
        'step': new_step['number'],
        'step_target': new_step['target'],
        'message': f'Step added at position {new_step["number"]}',
    }


def cmd_update_step(args) -> dict:
    """Handle 'update-step' subcommand — the sanctioned intent-override escape hatch.

    Mutates a single step's ``intent`` and appends a mandatory ``{from, to,
    reason}`` audit record (optionally carrying ``finding_id``) to the step's
    ``intent_override`` list. This is the ONLY sanctioned path to change a
    stored step intent post-authoring — hand-editing the JSON is a contract
    violation. The override may be triggered by execution-time divergence OR by
    a finding (PR review / Sonar / build-lint) resolved during verification or
    finalize; when triage-driven, ``--finding-id`` links the override back to
    its finding in manage-findings.
    """
    task_dir = get_tasks_dir(args.plan_id)

    filepath = find_task_file(task_dir, args.task_number)
    if not filepath:
        return output_error(f'Task TASK-{args.task_number} not found')

    reason = (getattr(args, 'reason', None) or '').strip()
    if not reason:
        return output_error('update-step requires a non-empty --reason for the intent override')

    try:
        new_intent = validate_step_intent(getattr(args, 'intent', None))
    except ValueError as e:
        return output_error(str(e))

    content = filepath.read_text(encoding='utf-8')
    task = parse_task_file(content)

    steps = task.get('steps', [])
    step_found = None
    for step in steps:
        if step['number'] == args.step_number:
            step_found = step
            break

    if not step_found:
        return output_error(f'Step {args.step_number} not found in TASK-{args.task_number}')

    old_intent = step_found.get('intent', '')
    override_record: dict[str, str] = {'from': old_intent, 'to': new_intent, 'reason': reason}
    finding_id = getattr(args, 'finding_id', None)
    if finding_id:
        override_record['finding_id'] = finding_id

    step_found['intent'] = new_intent
    step_found.setdefault('intent_override', []).append(override_record)

    new_content = format_task_file(task)
    atomic_write_file(filepath, new_content)

    return {
        'status': 'success',
        'plan_id': args.plan_id,
        'task_number': args.task_number,
        'step': args.step_number,
        'step_target': step_found.get('target', ''),
        'from_intent': old_intent,
        'to_intent': new_intent,
        'message': f'Step {args.step_number} intent updated {old_intent!r} -> {new_intent!r}',
    }


def cmd_remove_step(args) -> dict:
    """Handle 'remove-step' subcommand."""
    task_dir = get_tasks_dir(args.plan_id)

    filepath = find_task_file(task_dir, args.task_number)
    if not filepath:
        return output_error(f'Task TASK-{args.task_number} not found')

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
        return output_error(f'Step {args.step} not found in TASK-{args.task_number}')

    if len(steps) <= 1:
        return output_error('Cannot remove the last step - task must have at least one step')

    steps.pop(step_index)
    for i, step in enumerate(steps):
        step['number'] = i + 1

    task['steps'] = steps

    if task.get('current_step', 1) > len(steps):
        task['current_step'] = len(steps)

    new_content = format_task_file(task)
    atomic_write_file(filepath, new_content)

    # removed_step is guaranteed to be set since step_index is not None
    assert removed_step is not None
    return {
        'status': 'success',
        'plan_id': args.plan_id,
        'task_number': args.task_number,
        'step': args.step,
        'step_target': removed_step['target'],
        'message': f'Step {args.step} removed',
    }

#!/usr/bin/env python3
"""
Query command handlers for manage-tasks.py.

Contains: list, get, next, tasks-by-domain, tasks-by-profile, next-tasks subcommands.
"""

from _tasks_core import (
    calculate_progress,
    find_task_file,
    get_all_tasks,
    get_deliverable_context,
    get_tasks_dir,
    output_error,
    parse_task_file,
)


def _build_done_set(all_tasks: list) -> set[str]:
    """Build set of done task identifiers for dependency checking.

    Includes both zero-padded (TASK-001) and non-padded (TASK-1) formats
    to handle depends_on values stored in either format.
    """
    done = set()
    for _, t in all_tasks:
        if t.get('status') == 'done':
            n = t['number']
            done.add(f'TASK-{n:03d}')
            done.add(f'TASK-{n}')
    return done


def cmd_list(args) -> dict:
    """Handle 'list' subcommand."""
    task_dir = get_tasks_dir(args.plan_id)
    all_tasks = get_all_tasks(task_dir)

    # Build set of done task numbers for dependency checking
    done_tasks = _build_done_set(all_tasks)

    # Filter by deliverable if specified
    if args.deliverable:
        all_tasks = [(p, t) for p, t in all_tasks if args.deliverable == t.get('deliverable', 0)]

    # Filter by ready (dependencies satisfied) if specified
    if args.ready:
        all_tasks = [(p, t) for p, t in all_tasks if all(dep in done_tasks for dep in t.get('depends_on', []))]

    # Get filtered list for status filtering
    filtered_tasks = all_tasks
    if args.status and args.status != 'all':
        filtered_tasks = [(p, t) for p, t in all_tasks if t.get('status') == args.status]

    # Compute counts from filtered list
    pending = sum(1 for _, t in all_tasks if t.get('status') == 'pending')
    in_progress = sum(1 for _, t in all_tasks if t.get('status') == 'in_progress')
    done_count = sum(1 for _, t in all_tasks if t.get('status') == 'done')
    failed_count = sum(1 for _, t in all_tasks if t.get('status') == 'failed')
    blocked = sum(1 for _, t in all_tasks if t.get('status') == 'blocked')

    # Build table data
    table = []
    for _path, task in filtered_tasks:
        completed, total = calculate_progress(task)
        deliverable = task.get('deliverable', 0)
        table.append(
            {
                'number': task['number'],
                'title': task['title'],
                'domain': task.get('domain'),
                'profile': task.get('profile'),
                'deliverable': deliverable,
                'status': task['status'],
                'progress': f'{completed}/{total}',
            }
        )

    return {
        'status': 'success',
        'plan_id': args.plan_id,
        'counts': {
            'total': len(all_tasks),
            'pending': pending,
            'in_progress': in_progress,
            'done': done_count,
            'failed': failed_count,
            'blocked': blocked,
        },
        'tasks_table': table,
    }


def cmd_get(args) -> dict:
    """Handle 'get' subcommand."""
    task_dir = get_tasks_dir(args.plan_id)

    filepath = find_task_file(task_dir, args.task)
    if not filepath:
        return output_error(f'Task TASK-{args.task} not found')

    content = filepath.read_text(encoding='utf-8')
    task = parse_task_file(content)

    return {
        'status': 'success',
        'plan_id': args.plan_id,
        'file': filepath.name,
        'task': {
            'number': task['number'],
            'title': task['title'],
            'domain': task.get('domain'),
            'profile': task.get('profile'),
            'skills': task.get('skills', []),
            'origin': task.get('origin', 'plan'),
            'deliverable': task.get('deliverable', 0),
            'depends_on': task.get('depends_on', []),
            'status': task['status'],
            'current_step': task.get('current_step', 1),
            'description': task.get('description', ''),
            'steps': task.get('steps', []),
            'verification': task.get('verification', {}),
        },
    }


def cmd_next(args) -> dict:
    """Handle 'next' subcommand."""
    task_dir = get_tasks_dir(args.plan_id)
    all_tasks = get_all_tasks(task_dir)

    # Build set of done task numbers for dependency checking
    done_tasks = _build_done_set(all_tasks)

    filtered_tasks = all_tasks

    total_tasks = len(filtered_tasks)
    completed_tasks = sum(1 for _, t in filtered_tasks if t.get('status') == 'done')
    in_progress_count = sum(1 for _, t in filtered_tasks if t.get('status') == 'in_progress')

    # Helper to check if dependencies are satisfied
    def deps_satisfied(task):
        if getattr(args, 'ignore_deps', False):
            return True
        deps = task.get('depends_on', [])
        return all(dep in done_tasks for dep in deps)

    # Find first in_progress or pending task with satisfied dependencies
    next_task = None
    blocked_tasks = []

    # First, look for in_progress tasks
    for _path, task in filtered_tasks:
        if task.get('status') == 'in_progress':
            next_task = task
            break

    # If no in_progress, find first pending with satisfied deps
    if not next_task:
        for _path, task in filtered_tasks:
            if task.get('status') == 'pending':
                if deps_satisfied(task):
                    next_task = task
                    break
                else:
                    waiting_for = [dep for dep in task.get('depends_on', []) if dep not in done_tasks]
                    blocked_tasks.append(
                        {'number': task['number'], 'title': task['title'], 'waiting_for': ', '.join(waiting_for)}
                    )

    if not next_task:
        if blocked_tasks:
            return {
                'status': 'success',
                'plan_id': args.plan_id,
                'next': None,
                'blocked_tasks': blocked_tasks,
                'context': {
                    'total_tasks': total_tasks,
                    'completed_tasks': completed_tasks,
                    'in_progress': in_progress_count,
                    'blocked_by_deps': len(blocked_tasks),
                    'message': 'Waiting for in-progress tasks to complete',
                },
            }
        else:
            return {
                'status': 'success',
                'plan_id': args.plan_id,
                'next': None,
                'context': {
                    'total_tasks': total_tasks,
                    'completed_tasks': completed_tasks,
                    'message': 'All tasks completed',
                },
            }

    # Find next pending step in this task
    steps = next_task.get('steps', [])
    next_step = None
    completed_steps = 0

    for step in steps:
        if step['status'] in ('done', 'skipped'):
            completed_steps += 1
        elif step['status'] == 'in_progress':
            next_step = step
        elif step['status'] == 'pending' and not next_step:
            next_step = step

    remaining_steps = len(steps) - completed_steps

    if not next_step:
        return {
            'status': 'success',
            'plan_id': args.plan_id,
            'next': None,
            'context': {
                'total_tasks': total_tasks,
                'completed_tasks': completed_tasks,
                'message': 'All tasks completed',
            },
        }

    # Build base result
    result = {
        'status': 'success',
        'plan_id': args.plan_id,
        'next': {
            'task_number': next_task['number'],
            'task_title': next_task['title'],
            'domain': next_task.get('domain'),
            'profile': next_task.get('profile'),
            'skills': next_task.get('skills', []),
            'origin': next_task.get('origin', 'plan'),
            'deliverable': next_task.get('deliverable', 0),
            'step_number': next_step['number'],
            'step_target': next_step['target'],
        },
        'context': {
            'completed_steps': completed_steps,
            'remaining_steps': remaining_steps,
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
        },
    }

    # Include deliverable context if requested
    if getattr(args, 'include_context', False):
        deliverable = next_task.get('deliverable', 0)
        if deliverable:
            deliverable_context = get_deliverable_context(deliverable)
            result['next'].update(deliverable_context)

    return result


def cmd_tasks_by_domain(args) -> dict:
    """Handle 'tasks-by-domain' subcommand.

    Returns tasks filtered by domain.
    """
    task_dir = get_tasks_dir(args.plan_id)
    all_tasks = get_all_tasks(task_dir)

    # Filter by domain
    domain = args.domain
    filtered_tasks = [(p, t) for p, t in all_tasks if t.get('domain') == domain]

    # Build table data
    table = []
    for _path, task in filtered_tasks:
        completed, total = calculate_progress(task)
        table.append(
            {
                'number': task['number'],
                'title': task['title'],
                'domain': task.get('domain'),
                'profile': task.get('profile'),
                'status': task['status'],
                'progress': f'{completed}/{total}',
            }
        )

    # Compute counts
    pending = sum(1 for _, t in filtered_tasks if t.get('status') == 'pending')
    in_progress = sum(1 for _, t in filtered_tasks if t.get('status') == 'in_progress')
    done_count = sum(1 for _, t in filtered_tasks if t.get('status') == 'done')
    failed_count = sum(1 for _, t in filtered_tasks if t.get('status') == 'failed')
    blocked = sum(1 for _, t in filtered_tasks if t.get('status') == 'blocked')

    return {
        'status': 'success',
        'plan_id': args.plan_id,
        'domain_filter': domain,
        'counts': {
            'total': len(filtered_tasks),
            'pending': pending,
            'in_progress': in_progress,
            'done': done_count,
            'failed': failed_count,
            'blocked': blocked,
        },
        'tasks_table': table,
    }


def cmd_tasks_by_profile(args) -> dict:
    """Handle 'tasks-by-profile' subcommand.

    Returns tasks filtered by profile.
    """
    task_dir = get_tasks_dir(args.plan_id)
    all_tasks = get_all_tasks(task_dir)

    # Filter by profile
    profile = args.profile
    filtered_tasks = [(p, t) for p, t in all_tasks if t.get('profile') == profile]

    # Build table data
    table = []
    for _path, task in filtered_tasks:
        completed, total = calculate_progress(task)
        table.append(
            {
                'number': task['number'],
                'title': task['title'],
                'domain': task.get('domain'),
                'profile': task.get('profile'),
                'status': task['status'],
                'progress': f'{completed}/{total}',
            }
        )

    # Compute counts
    pending = sum(1 for _, t in filtered_tasks if t.get('status') == 'pending')
    in_progress = sum(1 for _, t in filtered_tasks if t.get('status') == 'in_progress')
    done_count = sum(1 for _, t in filtered_tasks if t.get('status') == 'done')
    failed_count = sum(1 for _, t in filtered_tasks if t.get('status') == 'failed')
    blocked = sum(1 for _, t in filtered_tasks if t.get('status') == 'blocked')

    return {
        'status': 'success',
        'plan_id': args.plan_id,
        'profile_filter': profile,
        'counts': {
            'total': len(filtered_tasks),
            'pending': pending,
            'in_progress': in_progress,
            'done': done_count,
            'failed': failed_count,
            'blocked': blocked,
        },
        'tasks_table': table,
    }


def cmd_next_tasks(args) -> dict:
    """Handle 'next-tasks' subcommand.

    Returns all tasks that are ready for parallel execution
    (all depends_on tasks are completed).
    """
    task_dir = get_tasks_dir(args.plan_id)
    all_tasks = get_all_tasks(task_dir)

    # Build set of done task numbers for dependency checking
    done_tasks = _build_done_set(all_tasks)

    # Find all pending tasks with satisfied dependencies
    ready_tasks = []
    blocked_tasks = []

    for _path, task in all_tasks:
        if task.get('status') != 'pending':
            continue

        deps = task.get('depends_on', [])
        unmet_deps = [dep for dep in deps if dep not in done_tasks]

        if not unmet_deps:
            # All dependencies satisfied - ready for execution
            completed, total = calculate_progress(task)
            ready_tasks.append(
                {
                    'number': task['number'],
                    'title': task['title'],
                    'domain': task.get('domain'),
                    'profile': task.get('profile'),
                    'skills': task.get('skills', []),
                    'deliverable': task.get('deliverable', 0),
                    'progress': f'{completed}/{total}',
                }
            )
        else:
            # Has unmet dependencies
            blocked_tasks.append({'number': task['number'], 'title': task['title'], 'waiting_for': unmet_deps})

    # Also include in_progress tasks
    in_progress_tasks = []
    for _path, task in all_tasks:
        if task.get('status') == 'in_progress':
            completed, total = calculate_progress(task)
            in_progress_tasks.append(
                {
                    'number': task['number'],
                    'title': task['title'],
                    'domain': task.get('domain'),
                    'profile': task.get('profile'),
                    'skills': task.get('skills', []),
                    'progress': f'{completed}/{total}',
                }
            )

    return {
        'status': 'success',
        'plan_id': args.plan_id,
        'ready_count': len(ready_tasks),
        'in_progress_count': len(in_progress_tasks),
        'blocked_count': len(blocked_tasks),
        'ready_tasks': ready_tasks,
        'in_progress_tasks': in_progress_tasks,
        'blocked_tasks': blocked_tasks,
    }

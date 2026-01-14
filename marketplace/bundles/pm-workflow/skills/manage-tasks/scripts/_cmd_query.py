#!/usr/bin/env python3
"""
Query command handlers for manage-tasks.py.

Contains: list, get, next, tasks-by-domain, tasks-by-profile, next-tasks subcommands.
"""

from _manage_tasks_shared import (
    calculate_progress,
    find_task_file,
    get_all_tasks,
    get_deliverable_context,
    get_tasks_dir,
    output_error,
    output_toon,
    parse_task_file,
)


def cmd_list(args) -> int:
    """Handle 'list' subcommand."""
    task_dir = get_tasks_dir(args.plan_id)
    all_tasks = get_all_tasks(task_dir)

    # Build set of done task numbers for dependency checking
    done_tasks = {f'TASK-{t["number"]}' for _, t in all_tasks if t.get('status') == 'done'}

    # Filter by phase if specified
    if args.phase:
        all_tasks = [(p, t) for p, t in all_tasks if t.get('phase', 'execute') == args.phase]

    # Filter by deliverable if specified
    if args.deliverable:
        all_tasks = [(p, t) for p, t in all_tasks if args.deliverable in t.get('deliverables', [])]

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
    blocked = sum(1 for _, t in all_tasks if t.get('status') == 'blocked')

    # Compute counts by phase
    by_phase: dict[str, int] = {}
    for _, t in all_tasks:
        phase = t.get('phase', 'execute')
        by_phase[phase] = by_phase.get(phase, 0) + 1

    # Build table data
    table = []
    for _path, task in filtered_tasks:
        completed, total = calculate_progress(task)
        deliverables = task.get('deliverables', [])
        table.append(
            {
                'number': task['number'],
                'title': task['title'],
                'domain': task.get('domain'),
                'profile': task.get('profile'),
                'phase': task.get('phase', 'execute'),
                'deliverables': deliverables,
                'status': task['status'],
                'progress': f'{completed}/{total}',
            }
        )

    result = {
        'status': 'success',
        'plan_id': args.plan_id,
        'phase_filter': args.phase if args.phase else 'all',
        'counts': {
            'total': len(all_tasks),
            'pending': pending,
            'in_progress': in_progress,
            'done': done_count,
            'blocked': blocked,
        },
        'tasks_table': table,
    }

    # Add by_phase counts if showing all phases
    if not args.phase and by_phase:
        result['counts']['by_phase'] = by_phase

    output_toon(result)
    return 0


def cmd_get(args) -> int:
    """Handle 'get' subcommand."""
    task_dir = get_tasks_dir(args.plan_id)

    filepath = find_task_file(task_dir, args.number)
    if not filepath:
        output_error(f'Task TASK-{args.number} not found')
        return 1

    content = filepath.read_text(encoding='utf-8')
    task = parse_task_file(content)

    output_toon(
        {
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
                'deliverables': task.get('deliverables', []),
                'depends_on': task.get('depends_on', []),
                'phase': task.get('phase', 'execute'),
                'status': task['status'],
                'current_step': task.get('current_step', 1),
                'created': task.get('created', ''),
                'updated': task.get('updated', ''),
                'description': task.get('description', ''),
                'delegation': task.get('delegation', {}),
                'steps': task.get('steps', []),
                'verification': task.get('verification', {}),
            },
        }
    )
    return 0


def cmd_next(args) -> int:
    """Handle 'next' subcommand."""
    task_dir = get_tasks_dir(args.plan_id)
    all_tasks = get_all_tasks(task_dir)

    # Build set of done task numbers for dependency checking
    done_tasks = {f'TASK-{t["number"]}' for _, t in all_tasks if t.get('status') == 'done'}

    # Filter by phase if specified
    filtered_tasks = all_tasks
    if args.phase:
        filtered_tasks = [(p, t) for p, t in all_tasks if t.get('phase', 'execute') == args.phase]

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
            output_toon(
                {
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
            )
        else:
            output_toon(
                {
                    'status': 'success',
                    'plan_id': args.plan_id,
                    'next': None,
                    'context': {
                        'total_tasks': total_tasks,
                        'completed_tasks': completed_tasks,
                        'message': 'All tasks completed',
                    },
                }
            )
        return 0

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
        output_toon(
            {
                'status': 'success',
                'plan_id': args.plan_id,
                'next': None,
                'context': {
                    'total_tasks': total_tasks,
                    'completed_tasks': completed_tasks,
                    'message': 'All tasks completed',
                },
            }
        )
        return 0

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
            'phase': next_task.get('phase', 'execute'),
            'deliverables': next_task.get('deliverables', []),
            'step_number': next_step['number'],
            'step_title': next_step['title'],
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
        deliverables = next_task.get('deliverables', [])
        if deliverables:
            deliverable_context = get_deliverable_context(deliverables)
            result['next'].update(deliverable_context)

    output_toon(result)
    return 0


def cmd_tasks_by_domain(args) -> int:
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
    blocked = sum(1 for _, t in filtered_tasks if t.get('status') == 'blocked')

    output_toon(
        {
            'status': 'success',
            'plan_id': args.plan_id,
            'domain_filter': domain,
            'counts': {
                'total': len(filtered_tasks),
                'pending': pending,
                'in_progress': in_progress,
                'done': done_count,
                'blocked': blocked,
            },
            'tasks_table': table,
        }
    )
    return 0


def cmd_tasks_by_profile(args) -> int:
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
    blocked = sum(1 for _, t in filtered_tasks if t.get('status') == 'blocked')

    output_toon(
        {
            'status': 'success',
            'plan_id': args.plan_id,
            'profile_filter': profile,
            'counts': {
                'total': len(filtered_tasks),
                'pending': pending,
                'in_progress': in_progress,
                'done': done_count,
                'blocked': blocked,
            },
            'tasks_table': table,
        }
    )
    return 0


def cmd_next_tasks(args) -> int:
    """Handle 'next-tasks' subcommand.

    Returns all tasks that are ready for parallel execution
    (all depends_on tasks are completed).
    """
    task_dir = get_tasks_dir(args.plan_id)
    all_tasks = get_all_tasks(task_dir)

    # Build set of done task numbers for dependency checking
    done_tasks = {f'TASK-{t["number"]}' for _, t in all_tasks if t.get('status') == 'done'}

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
                    'deliverables': task.get('deliverables', []),
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

    output_toon(
        {
            'status': 'success',
            'plan_id': args.plan_id,
            'ready_count': len(ready_tasks),
            'in_progress_count': len(in_progress_tasks),
            'blocked_count': len(blocked_tasks),
            'ready_tasks': ready_tasks,
            'in_progress_tasks': in_progress_tasks,
            'blocked_tasks': blocked_tasks,
        }
    )
    return 0

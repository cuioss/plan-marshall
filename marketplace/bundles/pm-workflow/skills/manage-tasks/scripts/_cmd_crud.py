#!/usr/bin/env python3
"""
CRUD command handlers for manage-tasks.py.

Contains: add, update, remove subcommands.
"""

import sys

from _manage_tasks_shared import (
    find_task_file,
    format_task_file,
    get_next_number,
    get_tasks_dir,
    now_iso,
    output_error,
    output_toon,
    parse_depends_on,
    parse_stdin_task,
    parse_task_file,
    validate_profile,
    validate_skills,
)
from file_ops import atomic_write_file  # type: ignore[import-not-found]
from plan_logging import log_entry  # type: ignore[import-not-found]


def cmd_add(args) -> int:
    """Handle 'add' subcommand.

    Reads task definition from stdin in TOON format.
    Only --plan-id is passed as CLI argument.
    """
    stdin_content = sys.stdin.read()
    if not stdin_content.strip():
        output_error("No task definition provided on stdin")
        return 1

    try:
        parsed = parse_stdin_task(stdin_content)
    except ValueError as e:
        output_error(str(e))
        return 1

    task_dir = get_tasks_dir(args.plan_id)

    number = get_next_number(task_dir)

    # Use type for filename (TASK-SEQ-TYPE format per target architecture)
    task_type = parsed['type']
    filename = f"TASK-{number:03d}-{task_type}.toon"
    filepath = task_dir / filename

    steps = []
    for i, step_title in enumerate(parsed['steps'], 1):
        steps.append({
            'number': i,
            'title': step_title,
            'status': 'pending'
        })

    now = now_iso()
    task = {
        'number': number,
        'title': parsed['title'],
        'status': 'pending',
        'phase': parsed['phase'],
        'domain': parsed['domain'],
        'profile': parsed['profile'],
        'type': parsed['type'],
        'skills': parsed['skills'],
        'origin': parsed['origin'],
        'priority': parsed.get('priority'),
        'finding': parsed.get('finding'),
        'created': now,
        'updated': now,
        'deliverables': parsed['deliverables'],
        'depends_on': parsed['depends_on'],
        'description': parsed['description'],
        'delegation': parsed['delegation'],
        'verification': parsed['verification'],
        'steps': steps,
        'current_step': 1
    }

    content = format_task_file(task)
    atomic_write_file(filepath, content)

    total = len(list(task_dir.glob("TASK-*.toon")))

    log_entry('work', args.plan_id, 'INFO', f'[MANAGE-TASKS] Added TASK-{number:03d} ({task_type}): {parsed["title"][:50]}')

    output_toon({
        'status': 'success',
        'plan_id': args.plan_id,
        'file': filename,
        'total_tasks': total,
        'task': {
            'number': number,
            'title': parsed['title'],
            'domain': parsed['domain'],
            'profile': parsed['profile'],
            'type': parsed['type'],
            'skills': parsed['skills'],
            'deliverables': parsed['deliverables'],
            'depends_on': parsed['depends_on'],
            'phase': parsed['phase'],
            'origin': parsed['origin'],
            'status': 'pending',
            'step_count': len(steps)
        }
    })
    return 0


def cmd_update(args) -> int:
    """Handle 'update' subcommand."""
    task_dir = get_tasks_dir(args.plan_id)

    filepath = find_task_file(task_dir, args.number)
    if not filepath:
        output_error(f"Task TASK-{args.number} not found")
        return 1

    content = filepath.read_text(encoding='utf-8')
    task = parse_task_file(content)

    if args.title:
        task['title'] = args.title
    if args.description:
        task['description'] = args.description
    if args.depends_on is not None:
        depends_on = []
        for dep in args.depends_on:
            if dep.lower() != 'none':
                depends_on.extend(parse_depends_on(dep))
        task['depends_on'] = depends_on
    if args.status:
        if args.status not in ('pending', 'in_progress', 'done', 'blocked'):
            output_error(f"Invalid status: {args.status}. Must be pending, in_progress, done, or blocked")
            return 1
        task['status'] = args.status

    # Handle new fields
    if getattr(args, 'domain', None):
        task['domain'] = args.domain
    if getattr(args, 'profile', None):
        try:
            task['profile'] = validate_profile(args.profile)
        except ValueError as e:
            output_error(str(e))
            return 1
    if getattr(args, 'skills', None):
        try:
            # Skills can be comma-separated or a list
            if isinstance(args.skills, str):
                skills_list = [s.strip() for s in args.skills.split(',') if s.strip()]
            else:
                skills_list = args.skills
            task['skills'] = validate_skills(skills_list)
        except ValueError as e:
            output_error(str(e))
            return 1
    if getattr(args, 'deliverables', None):
        try:
            # Deliverables can be comma-separated or a list
            if isinstance(args.deliverables, str):
                deliverables_list = [int(d.strip()) for d in args.deliverables.split(',') if d.strip()]
            else:
                deliverables_list = [int(d) for d in args.deliverables]
            task['deliverables'] = deliverables_list
        except ValueError:
            output_error("Deliverables must be comma-separated integers")
            return 1

    task['updated'] = now_iso()

    # Filename uses TASK-SEQ-TYPE format - doesn't change when title changes
    new_content = format_task_file(task)
    atomic_write_file(filepath, new_content)

    output_toon({
        'status': 'success',
        'plan_id': args.plan_id,
        'file': filepath.name,
        'task': {
            'number': task['number'],
            'title': task['title'],
            'domain': task.get('domain'),
            'profile': task.get('profile'),
            'type': task.get('type'),
            'skills': task.get('skills', []),
            'status': task['status']
        }
    })
    return 0


def cmd_remove(args) -> int:
    """Handle 'remove' subcommand."""
    task_dir = get_tasks_dir(args.plan_id)

    filepath = find_task_file(task_dir, args.number)
    if not filepath:
        output_error(f"Task TASK-{args.number} not found")
        return 1

    content = filepath.read_text(encoding='utf-8')
    task = parse_task_file(content)
    filename = filepath.name

    filepath.unlink()

    total = len(list(task_dir.glob("TASK-*.toon")))

    log_entry('work', args.plan_id, 'INFO', f'[MANAGE-TASKS] Removed TASK-{task["number"]:03d}: {task["title"][:50]}')

    output_toon({
        'status': 'success',
        'plan_id': args.plan_id,
        'total_tasks': total,
        'removed': {
            'number': task['number'],
            'title': task['title'],
            'file': filename
        }
    })
    return 0

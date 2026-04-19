#!/usr/bin/env python3
"""
CRUD command handlers for manage-tasks.py.

Contains: prepare-add, commit-add, update, remove subcommands.

Add flow (path-allocate pattern):
    1. `prepare-add` → script returns a scratch path under <plan>/work/pending-tasks/
    2. Main context writes the TOON task definition to that path with Write/Edit
    3. `commit-add` → script reads the file, validates it, and creates TASK-NNN.json

No multi-line content is marshalled through the shell boundary.
"""

import re

from _tasks_core import (
    find_task_file,
    format_task_file,
    get_next_number,
    get_plan_dir,
    get_tasks_dir,
    output_error,
    parse_depends_on,
    parse_stdin_task,
    parse_task_file,
    validate_profile,
    validate_skills,
)
from file_ops import atomic_write_file  # type: ignore[import-not-found]
from plan_logging import log_entry  # type: ignore[import-not-found]

_PENDING_DIR_NAME = 'pending-tasks'
_SLOT_RE = re.compile(r'^[a-z0-9][a-z0-9-]{0,63}$')


def _get_pending_dir(plan_id: str):
    """Return the script-owned scratch directory for pending task definitions."""
    return get_plan_dir(plan_id) / 'work' / _PENDING_DIR_NAME


def _resolve_slot(slot: str | None) -> str:
    """Validate an optional slot identifier; default to 'default'."""
    if slot is None or slot == '':
        return 'default'
    if not _SLOT_RE.match(slot):
        raise ValueError(
            f"Invalid slot '{slot}': must match [a-z0-9][a-z0-9-]{{0,63}}"
        )
    return slot


def _pending_path(plan_id: str, slot: str):
    """Return the scratch file path for a given plan_id + slot."""
    return _get_pending_dir(plan_id) / f'{slot}.toon'


def cmd_prepare_add(args) -> dict:
    """Allocate a script-owned scratch path for a pending task definition.

    Returns the absolute path the caller must write to before invoking
    `commit-add` with the same --plan-id (and --slot, if provided).
    """
    try:
        slot = _resolve_slot(getattr(args, 'slot', None))
    except ValueError as e:
        return output_error(str(e))

    pending_dir = _get_pending_dir(args.plan_id)
    pending_dir.mkdir(parents=True, exist_ok=True)

    path = _pending_path(args.plan_id, slot)

    return {
        'status': 'success',
        'plan_id': args.plan_id,
        'slot': slot,
        'path': str(path.resolve()) if path.exists() else str(path),
        'exists': path.exists(),
        'note': 'Write the TOON task definition to this path, then call commit-add.',
    }


def cmd_commit_add(args) -> dict:
    """Read a prepared task file, validate it, and create TASK-NNN.json.

    Consumes the scratch file bound to --plan-id (and --slot). The file must
    have been written by the main context between `prepare-add` and this call.
    The scratch file is deleted on success.
    """
    try:
        slot = _resolve_slot(getattr(args, 'slot', None))
    except ValueError as e:
        return output_error(str(e))

    path = _pending_path(args.plan_id, slot)
    if not path.exists():
        return output_error(
            f"No prepared task for plan '{args.plan_id}' slot '{slot}'. "
            f'Call prepare-add first and write the TOON definition to the returned path.'
        )

    content = path.read_text(encoding='utf-8')
    if not content.strip():
        return output_error(
            f"Prepared task file is empty: {path}. Write the TOON definition before commit-add."
        )

    try:
        parsed = parse_stdin_task(content)
    except ValueError as e:
        return output_error(str(e))

    task_dir = get_tasks_dir(args.plan_id)

    number = get_next_number(task_dir)

    filename = f'TASK-{number:03d}.json'
    filepath = task_dir / filename

    steps = []
    for i, step_target in enumerate(parsed['steps'], 1):
        steps.append({'number': i, 'target': step_target, 'status': 'pending'})

    task = {
        'number': number,
        'title': parsed['title'],
        'status': 'pending',
        'domain': parsed['domain'],
        'profile': parsed['profile'],
        'skills': parsed['skills'],
        'origin': parsed['origin'],
        'deliverable': parsed['deliverable'],
        'depends_on': parsed['depends_on'],
        'description': parsed['description'],
        'verification': parsed['verification'],
        'steps': steps,
        'current_step': 1,
    }

    content = format_task_file(task)
    atomic_write_file(filepath, content)

    # Consume the scratch file — success means it is no longer pending.
    try:
        path.unlink()
    except OSError:
        pass

    total = len(list(task_dir.glob('TASK-*.json')))

    log_entry(
        'work',
        args.plan_id,
        'INFO',
        f'[MANAGE-TASKS] Added TASK-{number:03d} ({parsed["origin"]}): {parsed["title"][:50]}',
    )

    return {
        'status': 'success',
        'plan_id': args.plan_id,
        'file': filename,
        'slot': slot,
        'total_tasks': total,
        'task': {
            'number': number,
            'title': parsed['title'],
            'domain': parsed['domain'],
            'profile': parsed['profile'],
            'skills': parsed['skills'],
            'deliverable': parsed['deliverable'],
            'depends_on': parsed['depends_on'],
            'origin': parsed['origin'],
            'status': 'pending',
            'step_count': len(steps),
        },
    }


def cmd_update(args) -> dict:
    """Handle 'update' subcommand."""
    task_dir = get_tasks_dir(args.plan_id)

    filepath = find_task_file(task_dir, args.task)
    if not filepath:
        return output_error(f'Task TASK-{args.task} not found')

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
            return output_error(f'Invalid status: {args.status}. Must be pending, in_progress, done, or blocked')
        task['status'] = args.status

    # Handle new fields
    if getattr(args, 'domain', None):
        task['domain'] = args.domain
    if getattr(args, 'profile', None):
        try:
            task['profile'] = validate_profile(args.profile)
        except ValueError as e:
            return output_error(str(e))
    if getattr(args, 'skills', None):
        try:
            # Skills can be comma-separated or a list
            if isinstance(args.skills, str):
                skills_list = [s.strip() for s in args.skills.split(',') if s.strip()]
            else:
                skills_list = args.skills
            task['skills'] = validate_skills(skills_list)
        except ValueError as e:
            return output_error(str(e))
    if getattr(args, 'deliverable', None):
        try:
            task['deliverable'] = int(args.deliverable)
        except ValueError:
            return output_error('Deliverable must be a positive integer')

    # Filename uses TASK-NNN format - doesn't change when title changes
    new_content = format_task_file(task)
    atomic_write_file(filepath, new_content)

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
            'status': task['status'],
        },
    }


def cmd_remove(args) -> dict:
    """Handle 'remove' subcommand."""
    task_dir = get_tasks_dir(args.plan_id)

    filepath = find_task_file(task_dir, args.task)
    if not filepath:
        return output_error(f'Task TASK-{args.task} not found')

    content = filepath.read_text(encoding='utf-8')
    task = parse_task_file(content)
    filename = filepath.name

    filepath.unlink()

    total = len(list(task_dir.glob('TASK-*.json')))

    log_entry('work', args.plan_id, 'INFO', f'[MANAGE-TASKS] Removed TASK-{task["number"]:03d}: {task["title"][:50]}')

    return {
        'status': 'success',
        'plan_id': args.plan_id,
        'total_tasks': total,
        'removed': {'number': task['number'], 'title': task['title'], 'file': filename},
    }

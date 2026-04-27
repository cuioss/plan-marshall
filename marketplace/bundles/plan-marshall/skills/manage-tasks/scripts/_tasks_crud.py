#!/usr/bin/env python3
"""
CRUD command handlers for manage-tasks.py.

Contains: prepare-add, commit-add, batch-add, update, remove subcommands.

Add flow (path-allocate pattern):
    1. `prepare-add` → script returns a scratch path under <plan>/work/pending-tasks/
    2. Main context writes the TOON task definition to that path with Write/Edit
    3. `commit-add` → script reads the file, validates it, and creates TASK-NNN.json

Batch add (atomic many-task insertion):
    `batch-add` accepts a JSON array of task records via three mutually
    exclusive inputs: `--tasks-json` (raw JSON string), `--tasks-file PATH`
    (read JSON from a file on disk), or stdin (when neither flag is given).
    It atomically appends every task in a single transaction. Either every
    task is created or none is — on any validation failure the entire batch
    is rejected and no TASK-NNN.json files are written.

No multi-line content is marshalled through the shell boundary for the
single-task add flow. The batch flow accepts JSON to keep the multi-task
array structured and parsable in one call. `--tasks-file PATH` exists for
callers that want to avoid quoting large JSON arrays through the shell.
"""

import json
import re
import sys
from pathlib import Path

from _tasks_core import (
    find_task_file,
    format_task_file,
    get_next_number,
    get_plan_dir,
    get_tasks_dir,
    normalize_step_path,
    output_error,
    parse_depends_on,
    parse_stdin_task,
    parse_task_file,
    validate_deliverable,
    validate_domain,
    validate_origin,
    validate_profile,
    validate_skills,
    validate_steps_are_file_paths,
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


def _validate_batch_entry(entry: dict, index: int) -> dict:
    """Validate a single batch entry from a JSON array and return a normalized
    task dict ready for persistence.

    Reuses the same validation surface as the single-task add flow (TOON path)
    so the contracts stay aligned: required fields, file-path step contract
    (skipped for verification profile), domain/profile/skills/origin checks.
    """
    if not isinstance(entry, dict):
        raise ValueError(f'batch entry [{index}]: expected JSON object, got {type(entry).__name__}')

    # Defaults match parse_stdin_task() so single and batch flows agree.
    title = entry.get('title', '')
    if not isinstance(title, str) or not title.strip():
        raise ValueError(f'batch entry [{index}]: missing required field: title')

    description = entry.get('description', '')
    if not isinstance(description, str):
        raise ValueError(f'batch entry [{index}]: description must be a string')

    domain_raw = entry.get('domain', '')
    if not isinstance(domain_raw, str) or not domain_raw.strip():
        raise ValueError(f'batch entry [{index}]: missing required field: domain')

    profile_raw = entry.get('profile', 'implementation')
    if not isinstance(profile_raw, str) or not profile_raw.strip():
        raise ValueError(f'batch entry [{index}]: profile must be a non-empty string')

    origin_raw = entry.get('origin', 'plan')
    if not isinstance(origin_raw, str):
        raise ValueError(f'batch entry [{index}]: origin must be a string')

    deliverable_raw = entry.get('deliverable')
    if deliverable_raw is None:
        # 0 is valid only for holistic tasks; defer to per-field validation.
        deliverable_raw = 0

    raw_steps = entry.get('steps', [])
    if not isinstance(raw_steps, list):
        raise ValueError(f'batch entry [{index}]: steps must be a JSON array of strings')
    steps: list[str] = []
    for s in raw_steps:
        if not isinstance(s, str):
            raise ValueError(f'batch entry [{index}]: every step must be a string, got {type(s).__name__}')
        normalized = normalize_step_path(s)
        if normalized:
            steps.append(normalized)
    if not steps:
        raise ValueError(f'batch entry [{index}]: missing required field: steps (at least one step required)')

    raw_skills = entry.get('skills', [])
    if not isinstance(raw_skills, list):
        raise ValueError(f'batch entry [{index}]: skills must be a JSON array of strings')

    raw_depends_on = entry.get('depends_on', [])
    if isinstance(raw_depends_on, str):
        depends_on = parse_depends_on(raw_depends_on)
    elif isinstance(raw_depends_on, list):
        depends_on = []
        for dep in raw_depends_on:
            if not isinstance(dep, str):
                raise ValueError(
                    f'batch entry [{index}]: depends_on entries must be strings (e.g. "TASK-1")'
                )
            if dep.lower() == 'none' or not dep.strip():
                continue
            if dep.startswith('TASK-'):
                depends_on.append(dep)
            elif dep.isdigit():
                depends_on.append(f'TASK-{int(dep)}')
            else:
                raise ValueError(
                    f'batch entry [{index}]: invalid depends_on entry: {dep!r} '
                    f"(expected 'TASK-N', integer, or 'none')"
                )
    else:
        raise ValueError(
            f'batch entry [{index}]: depends_on must be an array, a comma-separated string, or "none"'
        )

    raw_verification = entry.get('verification', {})
    if not isinstance(raw_verification, dict):
        raise ValueError(f'batch entry [{index}]: verification must be a JSON object')
    verification_commands = raw_verification.get('commands', []) or []
    if not isinstance(verification_commands, list):
        raise ValueError(f'batch entry [{index}]: verification.commands must be an array')
    for cmd in verification_commands:
        if not isinstance(cmd, str):
            raise ValueError(f'batch entry [{index}]: verification.commands entries must be strings')
    verification = {
        'commands': list(verification_commands),
        'criteria': raw_verification.get('criteria', '') or '',
        'manual': bool(raw_verification.get('manual', False)),
    }

    # Apply the same final validators the single-task path uses. Wrap each
    # call so the underlying ValueError is annotated with the batch index —
    # otherwise the caller can't tell which entry failed.
    try:
        domain = validate_domain(domain_raw)
        profile = validate_profile(profile_raw)
        deliverable = validate_deliverable(deliverable_raw)
        skills = validate_skills([s for s in raw_skills if isinstance(s, str)])
        if origin_raw:
            validate_origin(origin_raw)
    except ValueError as e:
        raise ValueError(f'batch entry [{index}]: {e}') from e

    if profile != 'verification':
        step_errors, _ = validate_steps_are_file_paths(steps)
        if step_errors:
            raise ValueError(
                f'batch entry [{index}]: task contract violation - steps must be file paths:\n'
                + '\n'.join(step_errors)
            )

    if deliverable == 0 and origin_raw != 'holistic':
        raise ValueError(f'batch entry [{index}]: missing required field: deliverable')

    return {
        'title': title.strip(),
        'description': description,
        'domain': domain,
        'profile': profile,
        'origin': origin_raw,
        'deliverable': deliverable,
        'depends_on': depends_on,
        'skills': skills,
        'steps': steps,
        'verification': verification,
    }


def cmd_batch_add(args) -> dict:
    """Atomically add multiple tasks from a JSON array.

    Accepts the array via three mutually exclusive inputs:

    - ``--tasks-json`` argument (raw JSON string)
    - ``--tasks-file PATH`` (read JSON from a file on disk)
    - stdin (when neither flag is given)

    Mutual exclusion between ``--tasks-json`` and ``--tasks-file`` is enforced
    at the CLI layer (argparse mutually-exclusive group). This handler keeps
    a defensive check for callers that bypass the CLI parser.

    Validates EVERY entry before writing ANY file. On any validation failure,
    no TASK-NNN.json files are created — the whole batch is rejected with a
    descriptive error. On success, every task is written and a single result
    summarizes the created tasks.
    """
    # Pull the JSON payload from --tasks-json, --tasks-file, or stdin.
    tasks_json_arg = getattr(args, 'tasks_json', None)
    tasks_file_arg = getattr(args, 'tasks_file', None)

    # Defensive: argparse already enforces mutual exclusion, but guard against
    # callers constructing args namespaces directly.
    if tasks_json_arg and tasks_file_arg:
        return output_error(
            '--tasks-json and --tasks-file are mutually exclusive; pass exactly one',
            error_code='invalid_input',
        )

    if tasks_file_arg:
        path = Path(tasks_file_arg)
        if not path.is_file():
            return output_error(
                f'--tasks-file path does not exist or is not a regular file: {tasks_file_arg}',
                error_code='file_not_found',
            )
        try:
            payload = path.read_text(encoding='utf-8')
        except OSError as e:
            return output_error(f'Cannot read --tasks-file {tasks_file_arg}: {e}')
    elif tasks_json_arg:
        payload = tasks_json_arg
    else:
        try:
            payload = sys.stdin.read()
        except OSError as e:
            return output_error(f'Cannot read tasks array from stdin: {e}')

    if not payload or not payload.strip():
        return output_error(
            'batch-add requires a JSON array via --tasks-json, --tasks-file, or stdin '
            '(use --tasks-json "[]" to explicitly request a no-op)'
        )

    try:
        parsed_payload = json.loads(payload)
    except json.JSONDecodeError as e:
        return output_error(f'Invalid JSON for batch-add: {e.msg} at line {e.lineno} col {e.colno}')

    if not isinstance(parsed_payload, list):
        return output_error(
            f'batch-add expects a JSON array of task records, got {type(parsed_payload).__name__}'
        )

    # Empty array is a documented no-op (lets callers compose the array
    # programmatically without special-casing the zero-task path).
    if not parsed_payload:
        return {
            'status': 'success',
            'plan_id': args.plan_id,
            'tasks_created': 0,
            'tasks': [],
            'note': 'Empty batch — no tasks created.',
        }

    # Validate every entry first; collect normalized records.
    normalized: list[dict] = []
    for i, entry in enumerate(parsed_payload):
        try:
            normalized.append(_validate_batch_entry(entry, i))
        except ValueError as e:
            # Atomic semantics: nothing has been written yet, so rejecting
            # here leaves the on-disk state untouched.
            return output_error(str(e))

    # Persist atomically: assign sequential numbers up front, then write each
    # file. Filename collisions are impossible because get_next_number() is
    # called once and we increment from there.
    task_dir = get_tasks_dir(args.plan_id)
    starting_number = get_next_number(task_dir)

    created: list[dict] = []
    written_paths = []
    try:
        for offset, parsed in enumerate(normalized):
            number = starting_number + offset
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
            written_paths.append(filepath)

            created.append(
                {
                    'number': number,
                    'title': parsed['title'],
                    'file': filename,
                    'domain': parsed['domain'],
                    'profile': parsed['profile'],
                    'deliverable': parsed['deliverable'],
                    'depends_on': parsed['depends_on'],
                    'origin': parsed['origin'],
                    'step_count': len(steps),
                }
            )
    except OSError as e:
        # Rollback: a write failed mid-batch. Remove anything we already wrote
        # so the on-disk view stays consistent with "all-or-nothing".
        for written in written_paths:
            try:
                written.unlink()
            except OSError:
                pass
        return output_error(f'batch-add aborted while writing tasks: {e}')

    total = len(list(task_dir.glob('TASK-*.json')))

    log_entry(
        'work',
        args.plan_id,
        'INFO',
        f'[MANAGE-TASKS] batch-add created {len(created)} tasks (TASK-{starting_number:03d}..TASK-{starting_number + len(created) - 1:03d})',
    )

    return {
        'status': 'success',
        'plan_id': args.plan_id,
        'tasks_created': len(created),
        'starting_task_number': starting_number,
        'total_tasks': total,
        'tasks': created,
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

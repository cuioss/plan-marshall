#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""
Rename path mapping command handler for manage-tasks.py.

Records old→new path mappings in work/rename_mapping.toon so that
subsequent tasks can have their step targets auto-rewritten.
"""

from pathlib import Path

from _tasks_core import format_task_file, get_tasks_dir, output_error, parse_task_file
from constants import DIR_WORK
from file_ops import atomic_write_file, get_plan_dir
from plan_logging import log_entry
from toon_parser import parse_toon

RENAME_MAPPING_FILE = 'rename_mapping.toon'


def _get_rename_mapping_path(plan_id: str) -> Path:
    """Get path to the rename mapping file."""
    plan_dir = get_plan_dir(plan_id)
    work_dir = plan_dir / DIR_WORK
    work_dir.mkdir(parents=True, exist_ok=True)
    return work_dir / RENAME_MAPPING_FILE


def _read_mappings(path: Path) -> list[dict]:
    """Read existing mappings from TOON file."""
    if not path.exists():
        return []
    content = path.read_text(encoding='utf-8')
    result = parse_toon(content)
    mappings: list[dict] = result.get('mappings', [])
    return mappings


def _write_mappings(path: Path, mappings: list[dict]) -> None:
    """Write mappings to TOON file."""
    lines = [f'mapping_count: {len(mappings)}', '']
    if mappings:
        lines.append(f'mappings[{len(mappings)}]{{old_path,new_path}}:')
        for m in mappings:
            lines.append(f'  {m["old_path"]},{m["new_path"]}')
    else:
        lines.append('mappings[0]:')
    lines.append('')
    atomic_write_file(path, '\n'.join(lines))


def _apply_mappings_to_tasks(
    plan_id: str, old_path: str, new_path: str, include_completed: bool = False
) -> list[dict]:
    """Rewrite step targets that match old_path.

    By default only unfinished work is rewritten: a task whose status is ``done``
    is skipped whole, and within every other task only ``pending`` steps are
    touched. That default keeps a finished task's record a faithful account of
    the paths it actually edited.

    With ``include_completed`` both guards are lifted, so finished tasks and
    non-pending steps are rewritten too. The case it exists for is an upstream
    rename landing mid-plan: the file a completed step named no longer exists, so
    leaving the step alone does not preserve a true record — it strands the task
    on a dead path that the declared-set closure check then flags for the rest of
    the plan's life, with no sanctioned way to correct it.
    """
    tasks_dir = get_tasks_dir(plan_id)
    if not tasks_dir.exists():
        return []

    rewritten = []
    for task_file in sorted(tasks_dir.glob('TASK-*.json')):
        content = task_file.read_text(encoding='utf-8')
        task = parse_task_file(content)

        if not include_completed and task.get('status') == 'done':
            continue

        changed = False
        for step in task.get('steps', []):
            if not include_completed and step.get('status') != 'pending':
                continue
            target = step.get('target', '')
            if target == old_path or target.startswith(old_path + '/'):
                new_target = new_path + target[len(old_path) :]
                rewritten.append(
                    {
                        'task': task['number'],
                        'step': step['number'],
                        'old_target': target,
                        'new_target': new_target,
                        # The step's status BEFORE the rewrite. A rewrite of an
                        # already-finished step edits the record of work that is
                        # done, so the audit trail must say which entries did
                        # that rather than leaving it inferable only from the
                        # flag that was passed.
                        'step_status': step.get('status', 'pending'),
                    }
                )
                step['target'] = new_target
                changed = True

        if changed:
            new_content = format_task_file(task)
            atomic_write_file(task_file, new_content)

    return rewritten


def cmd_rename_path(args) -> dict:
    """Handle 'rename-path' subcommand.

    Records old→new path mapping and rewrites matching step targets. Only
    unfinished work is rewritten unless ``--include-completed`` is passed; see
    ``_apply_mappings_to_tasks`` for what that flag lifts and why.
    """
    old_path = args.old_path.rstrip('/')
    new_path = args.new_path.rstrip('/')

    if old_path == new_path:
        return output_error('Old path and new path are identical')

    include_completed = bool(getattr(args, 'include_completed', False))

    # Record mapping
    mapping_path = _get_rename_mapping_path(args.plan_id)
    mappings = _read_mappings(mapping_path)
    mappings.append({'old_path': old_path, 'new_path': new_path})
    _write_mappings(mapping_path, mappings)

    rewritten = _apply_mappings_to_tasks(
        args.plan_id, old_path, new_path, include_completed=include_completed
    )
    completed_rewritten = [r for r in rewritten if r['step_status'] != 'pending']

    # A rewrite that edited finished work says so in the log line — the count
    # alone would not distinguish it from an ordinary pending-only rewrite.
    completed_note = (
        f' ({len(completed_rewritten)} on already-completed steps)' if completed_rewritten else ''
    )
    log_entry(
        'work',
        args.plan_id,
        'INFO',
        f'[MANAGE-TASKS] Recorded rename: {old_path} -> {new_path}, '
        f'rewritten {len(rewritten)} step targets{completed_note}',
    )

    return {
        'status': 'success',
        'plan_id': args.plan_id,
        'mapping': {
            'old_path': old_path,
            'new_path': new_path,
        },
        'mapping_count': len(mappings),
        'rewritten_count': len(rewritten),
        'rewritten_completed_count': len(completed_rewritten),
        'rewritten': rewritten,
    }

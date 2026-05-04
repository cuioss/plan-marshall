#!/usr/bin/env python3
"""
Rename path mapping command handler for manage-tasks.py.

Records old→new path mappings in work/rename_mapping.toon so that
subsequent tasks can have their step targets auto-rewritten.
"""

from pathlib import Path

from _tasks_core import format_task_file, get_tasks_dir, output_error, parse_task_file
from constants import DIR_WORK  # type: ignore[import-not-found]
from file_ops import atomic_write_file, get_plan_dir  # type: ignore[import-not-found]
from plan_logging import log_entry  # type: ignore[import-not-found]
from toon_parser import parse_toon  # type: ignore[import-not-found]

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


def _apply_mappings_to_tasks(plan_id: str, old_path: str, new_path: str) -> list[dict]:
    """Rewrite step targets in all pending tasks that match old_path."""
    tasks_dir = get_tasks_dir(plan_id)
    if not tasks_dir.exists():
        return []

    rewritten = []
    for task_file in sorted(tasks_dir.glob('TASK-*.json')):
        content = task_file.read_text(encoding='utf-8')
        task = parse_task_file(content)

        if task.get('status') == 'done':
            continue

        changed = False
        for step in task.get('steps', []):
            if step.get('status') != 'pending':
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

    Records old→new path mapping and rewrites step targets in pending tasks.
    """
    old_path = args.old_path.rstrip('/')
    new_path = args.new_path.rstrip('/')

    if old_path == new_path:
        return output_error('Old path and new path are identical')

    # Record mapping
    mapping_path = _get_rename_mapping_path(args.plan_id)
    mappings = _read_mappings(mapping_path)
    mappings.append({'old_path': old_path, 'new_path': new_path})
    _write_mappings(mapping_path, mappings)

    # Rewrite step targets in pending tasks
    rewritten = _apply_mappings_to_tasks(args.plan_id, old_path, new_path)

    log_entry(
        'work',
        args.plan_id,
        'INFO',
        f'[MANAGE-TASKS] Recorded rename: {old_path} -> {new_path}, rewritten {len(rewritten)} step targets',
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
        'rewritten': rewritten,
    }

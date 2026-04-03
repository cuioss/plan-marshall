#!/usr/bin/env python3
"""
Generic file I/O operations for plan directories.

Provides basic CRUD operations for any file within a plan directory.
Uses file_ops for consistent path handling and atomic writes.

NOTE: For typed documents (request.md, solution_outline.md), prefer using
manage-plan-documents skill which provides validation and templating.

Usage:
    python3 manage-files.py read --plan-id my-plan --file notes.md
    python3 manage-files.py write --plan-id my-plan --file notes.md --content "..."
    python3 manage-files.py list --plan-id my-plan
    python3 manage-files.py exists --plan-id my-plan --file config.toon
    python3 manage-files.py remove --plan-id my-plan --file old-file.md
    python3 manage-files.py mkdir --plan-id my-plan --dir goals
"""

import argparse
import sys
from pathlib import Path
from typing import cast

from file_ops import atomic_write_file, base_path, output_toon, safe_main  # type: ignore[import-not-found]
from input_validation import is_valid_relative_path, require_valid_plan_id  # type: ignore[import-not-found]
from plan_logging import log_entry  # type: ignore[import-not-found]


def get_plan_dir(plan_id: str) -> Path:
    """Get the plan directory path."""
    return cast(Path, base_path('plans', plan_id))


def cmd_read(args: argparse.Namespace) -> None:
    """Read file content from plan directory."""
    require_valid_plan_id(args)

    if not is_valid_relative_path(args.file):
        output_toon({'status': 'error', 'error': 'invalid_path', 'message': f'Invalid file path: {args.file}'})
        sys.exit(1)

    plan_dir = get_plan_dir(args.plan_id)
    file_path = plan_dir / args.file

    if not file_path.exists():
        output_toon({'status': 'error', 'error': 'file_not_found', 'message': f'File not found: {file_path}'})
        sys.exit(1)

    print(file_path.read_text(encoding='utf-8'), end='')


def cmd_write(args: argparse.Namespace) -> None:
    """Write content to file in plan directory."""
    require_valid_plan_id(args)

    if not is_valid_relative_path(args.file):
        output_toon({'status': 'error', 'error': 'invalid_path', 'message': f'Invalid file path: {args.file}'})
        sys.exit(1)

    plan_dir = get_plan_dir(args.plan_id)
    file_path = plan_dir / args.file

    # Get content from stdin or --content
    if args.stdin:
        content = sys.stdin.read()
    elif args.content:
        content = args.content
    else:
        output_toon({'status': 'error', 'error': 'missing_content', 'message': 'Must provide --content or --stdin'})
        sys.exit(1)

    if not content:
        output_toon({'status': 'error', 'error': 'empty_content', 'message': 'Content cannot be empty'})
        sys.exit(1)

    # Ensure plan directory exists
    plan_dir.mkdir(parents=True, exist_ok=True)

    # Write atomically
    atomic_write_file(file_path, content)
    log_entry('work', args.plan_id, 'INFO', f'[MANAGE-FILES] Created {args.file}')
    output_toon({'status': 'success', 'action': 'created', 'file': args.file, 'path': str(file_path)})


def cmd_remove(args: argparse.Namespace) -> None:
    """Remove file from plan directory."""
    require_valid_plan_id(args)

    if not is_valid_relative_path(args.file):
        output_toon({'status': 'error', 'error': 'invalid_path', 'message': f'Invalid file path: {args.file}'})
        sys.exit(1)

    plan_dir = get_plan_dir(args.plan_id)
    file_path = plan_dir / args.file

    if not file_path.exists():
        output_toon({'status': 'error', 'error': 'file_not_found', 'message': f'File not found: {file_path}'})
        sys.exit(1)

    file_path.unlink()
    log_entry('work', args.plan_id, 'INFO', f'[MANAGE-FILES] Removed {args.file}')
    output_toon({'status': 'success', 'action': 'removed', 'file': args.file, 'path': str(file_path)})


def cmd_list(args: argparse.Namespace) -> None:
    """List files in plan directory."""
    require_valid_plan_id(args)

    plan_dir = get_plan_dir(args.plan_id)

    if args.dir:
        if not is_valid_relative_path(args.dir):
            output_toon({'status': 'error', 'error': 'invalid_path', 'message': f'Invalid directory path: {args.dir}'})
            sys.exit(1)
        target_dir = plan_dir / args.dir
    else:
        target_dir = plan_dir

    if not target_dir.exists():
        output_toon({'status': 'error', 'error': 'dir_not_found', 'message': f'Directory not found: {target_dir}'})
        sys.exit(1)

    files = []
    for item in sorted(target_dir.iterdir()):
        if item.is_dir():
            files.append(f'{item.name}/')
        else:
            files.append(item.name)

    output_toon({'status': 'success', 'plan_id': args.plan_id, 'files': files})


def cmd_exists(args):
    """Check if file exists in plan directory.

    Returns TOON output with exists: true/false.
    Exits 0 for both found and not-found outcomes.
    Exits 1 for validation errors (invalid plan_id or path).
    """
    require_valid_plan_id(args)

    if not is_valid_relative_path(args.file):
        output_toon({
            'status': 'error',
            'plan_id': args.plan_id,
            'file': args.file,
            'error': 'invalid_path',
            'message': f'Invalid file path: {args.file}',
        })
        sys.exit(1)

    plan_dir = get_plan_dir(args.plan_id)
    file_path = plan_dir / args.file

    output_toon({
        'status': 'success',
        'plan_id': args.plan_id,
        'file': args.file,
        'exists': file_path.exists(),
        'path': str(file_path),
    })


def cmd_mkdir(args):
    """Create subdirectory in plan directory.

    Returns TOON output with the created directory path.
    """
    require_valid_plan_id(args)

    if not is_valid_relative_path(args.dir):
        output_toon({
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'invalid_path',
            'message': f'Invalid directory path: {args.dir}',
        })
        sys.exit(1)

    plan_dir = get_plan_dir(args.plan_id)
    target_dir = plan_dir / args.dir

    already_exists = target_dir.exists()
    target_dir.mkdir(parents=True, exist_ok=True)

    output_toon({
        'status': 'success',
        'plan_id': args.plan_id,
        'action': 'exists' if already_exists else 'created',
        'dir': args.dir,
        'path': str(target_dir),
    })


def cmd_create_or_reference(args):
    """Create plan directory if it doesn't exist, or reference existing one.

    Returns TOON output indicating whether the plan was created or already exists.
    This replaces the two-step list+check pattern in plan-init.
    """
    require_valid_plan_id(args)

    plan_dir = get_plan_dir(args.plan_id)

    if plan_dir.exists():
        # Plan already exists - gather info about it
        result = {'status': 'success', 'plan_id': args.plan_id, 'action': 'exists', 'path': str(plan_dir)}

        # Check if status.json exists to get phase info
        status_path = plan_dir / 'status.json'
        if status_path.exists():
            try:
                import json

                status = json.loads(status_path.read_text(encoding='utf-8'))
                result['current_phase'] = status.get('current_phase', 'unknown')
            except (ValueError, KeyError, OSError):
                # Parse error or read error - just note file exists
                result['has_status'] = True

        output_toon(result)
    else:
        # Create the plan directory
        plan_dir.mkdir(parents=True, exist_ok=True)

        result = {'status': 'success', 'plan_id': args.plan_id, 'action': 'created', 'path': str(plan_dir)}
        output_toon(result)


def cmd_delete_plan(args):
    """Delete an entire plan directory.

    Returns TOON output indicating the deletion result.
    Used by plan-init when user selects 'Replace' for an existing plan.

    See: standards/plan-overwrite.md for the full workflow.
    """
    import shutil

    require_valid_plan_id(args)

    plan_dir = get_plan_dir(args.plan_id)

    if not plan_dir.exists():
        output_toon({
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'plan_not_found',
            'message': f'Plan directory does not exist: {plan_dir}',
        })
        sys.exit(1)

    # Count files before deletion for audit trail
    files_removed = sum(1 for _ in plan_dir.rglob('*') if _.is_file())

    try:
        shutil.rmtree(plan_dir)
        log_entry('work', args.plan_id, 'INFO', f'[MANAGE-FILES] Deleted plan ({files_removed} files)')
        output_toon({
            'status': 'success',
            'plan_id': args.plan_id,
            'action': 'deleted',
            'path': str(plan_dir),
            'files_removed': files_removed,
        })
    except PermissionError as e:
        output_toon({
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'permission_denied',
            'message': f'Permission denied: {e}',
        })
        sys.exit(1)
    except Exception as e:
        output_toon({
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'delete_failed',
            'message': f'Failed to delete plan directory: {e}',
        })
        sys.exit(1)


@safe_main
def main() -> int:
    parser = argparse.ArgumentParser(description='Generic file I/O operations for plan directories')
    subparsers = parser.add_subparsers(dest='command', required=True)

    # read
    read_parser = subparsers.add_parser('read', help='Read file content')
    read_parser.add_argument('--plan-id', required=True, help='Plan identifier')
    read_parser.add_argument('--file', required=True, help='Relative file path')
    read_parser.set_defaults(func=cmd_read)

    # write
    write_parser = subparsers.add_parser('write', help='Write file content')
    write_parser.add_argument('--plan-id', required=True, help='Plan identifier')
    write_parser.add_argument('--file', required=True, help='Relative file path')
    write_parser.add_argument('--content', help='Content to write')
    write_parser.add_argument('--stdin', action='store_true', help='Read content from stdin')
    write_parser.set_defaults(func=cmd_write)

    # remove
    remove_parser = subparsers.add_parser('remove', help='Remove file')
    remove_parser.add_argument('--plan-id', required=True, help='Plan identifier')
    remove_parser.add_argument('--file', required=True, help='Relative file path')
    remove_parser.set_defaults(func=cmd_remove)

    # list
    list_parser = subparsers.add_parser('list', help='List files')
    list_parser.add_argument('--plan-id', required=True, help='Plan identifier')
    list_parser.add_argument('--dir', help='Subdirectory to list')
    list_parser.set_defaults(func=cmd_list)

    # exists
    exists_parser = subparsers.add_parser('exists', help='Check if file exists')
    exists_parser.add_argument('--plan-id', required=True, help='Plan identifier')
    exists_parser.add_argument('--file', required=True, help='Relative file path')
    exists_parser.set_defaults(func=cmd_exists)

    # mkdir
    mkdir_parser = subparsers.add_parser('mkdir', help='Create subdirectory')
    mkdir_parser.add_argument('--plan-id', required=True, help='Plan identifier')
    mkdir_parser.add_argument('--dir', required=True, help='Directory to create')
    mkdir_parser.set_defaults(func=cmd_mkdir)

    # create-or-reference
    create_ref_parser = subparsers.add_parser(
        'create-or-reference', help='Create plan directory or reference existing one'
    )
    create_ref_parser.add_argument('--plan-id', required=True, help='Plan identifier')
    create_ref_parser.set_defaults(func=cmd_create_or_reference)

    # delete-plan
    delete_plan_parser = subparsers.add_parser('delete-plan', help='Delete entire plan directory')
    delete_plan_parser.add_argument('--plan-id', required=True, help='Plan identifier')
    delete_plan_parser.set_defaults(func=cmd_delete_plan)

    args = parser.parse_args()
    args.func(args)
    return 0


if __name__ == '__main__':
    main()

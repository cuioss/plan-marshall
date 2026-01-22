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
import re
import sys
from pathlib import Path
from typing import cast

from file_ops import atomic_write_file, base_path  # type: ignore[import-not-found]
from plan_logging import log_entry  # type: ignore[import-not-found]
from toon_parser import parse_toon, serialize_toon  # type: ignore[import-not-found]


def validate_plan_id(plan_id: str) -> bool:
    """Validate plan_id is kebab-case with no special characters."""
    return bool(re.match(r'^[a-z][a-z0-9-]*$', plan_id))


def validate_file_path(file_path: str) -> bool:
    """Validate file path has no directory traversal or absolute paths."""
    if file_path.startswith('/'):
        return False
    if '..' in file_path:
        return False
    return True


def get_plan_dir(plan_id: str) -> Path:
    """Get the plan directory path."""
    return cast(Path, base_path('plans', plan_id))


def cmd_read(args):
    """Read file content from plan directory."""
    if not validate_plan_id(args.plan_id):
        print(f'Error: Invalid plan_id format: {args.plan_id}', file=sys.stderr)
        sys.exit(1)

    if not validate_file_path(args.file):
        print(f'Error: Invalid file path: {args.file}', file=sys.stderr)
        sys.exit(1)

    plan_dir = get_plan_dir(args.plan_id)
    file_path = plan_dir / args.file

    if not file_path.exists():
        print(f'Error: File not found: {file_path}', file=sys.stderr)
        sys.exit(1)

    print(file_path.read_text(encoding='utf-8'), end='')


def cmd_write(args):
    """Write content to file in plan directory."""
    if not validate_plan_id(args.plan_id):
        print(f'Error: Invalid plan_id format: {args.plan_id}', file=sys.stderr)
        sys.exit(1)

    if not validate_file_path(args.file):
        print(f'Error: Invalid file path: {args.file}', file=sys.stderr)
        sys.exit(1)

    plan_dir = get_plan_dir(args.plan_id)
    file_path = plan_dir / args.file

    # Get content from stdin or --content
    if args.stdin:
        content = sys.stdin.read()
    elif args.content:
        content = args.content
    else:
        print('Error: Must provide --content or --stdin', file=sys.stderr)
        sys.exit(1)

    if not content:
        print('Error: Content cannot be empty', file=sys.stderr)
        sys.exit(1)

    # Ensure plan directory exists
    plan_dir.mkdir(parents=True, exist_ok=True)

    # Write atomically
    atomic_write_file(file_path, content)
    log_entry('work', args.plan_id, 'INFO', f'[MANAGE-FILES] Created {args.file}')
    print(f'Created: {file_path}', file=sys.stderr)


def cmd_remove(args):
    """Remove file from plan directory."""
    if not validate_plan_id(args.plan_id):
        print(f'Error: Invalid plan_id format: {args.plan_id}', file=sys.stderr)
        sys.exit(1)

    if not validate_file_path(args.file):
        print(f'Error: Invalid file path: {args.file}', file=sys.stderr)
        sys.exit(1)

    plan_dir = get_plan_dir(args.plan_id)
    file_path = plan_dir / args.file

    if not file_path.exists():
        print(f'Error: File not found: {file_path}', file=sys.stderr)
        sys.exit(1)

    file_path.unlink()
    log_entry('work', args.plan_id, 'INFO', f'[MANAGE-FILES] Removed {args.file}')
    print(f'Removed: {file_path}', file=sys.stderr)


def cmd_list(args):
    """List files in plan directory."""
    if not validate_plan_id(args.plan_id):
        print(f'Error: Invalid plan_id format: {args.plan_id}', file=sys.stderr)
        sys.exit(1)

    plan_dir = get_plan_dir(args.plan_id)

    if args.dir:
        if not validate_file_path(args.dir):
            print(f'Error: Invalid directory path: {args.dir}', file=sys.stderr)
            sys.exit(1)
        target_dir = plan_dir / args.dir
    else:
        target_dir = plan_dir

    if not target_dir.exists():
        print(f'Error: Directory not found: {target_dir}', file=sys.stderr)
        sys.exit(1)

    for item in sorted(target_dir.iterdir()):
        if item.is_dir():
            print(f'{item.name}/')
        else:
            print(item.name)


def cmd_exists(args):
    """Check if file exists in plan directory.

    Returns TOON output with exists: true/false.
    Always exits 0 for expected outcomes (exists, not exists, validation errors).
    Only exits non-zero for unexpected runtime errors.
    """
    if not validate_plan_id(args.plan_id):
        result = {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'invalid_plan_id',
            'message': f'Invalid plan_id format: {args.plan_id}',
        }
        print(serialize_toon(result))
        return

    if not validate_file_path(args.file):
        result = {
            'status': 'error',
            'plan_id': args.plan_id,
            'file': args.file,
            'error': 'invalid_path',
            'message': f'Invalid file path: {args.file}',
        }
        print(serialize_toon(result))
        return

    plan_dir = get_plan_dir(args.plan_id)
    file_path = plan_dir / args.file

    result = {
        'status': 'success',
        'plan_id': args.plan_id,
        'file': args.file,
        'exists': file_path.exists(),
        'path': str(file_path),
    }
    print(serialize_toon(result))


def cmd_mkdir(args):
    """Create subdirectory in plan directory.

    Returns TOON output with the created directory path.
    """
    if not validate_plan_id(args.plan_id):
        result = {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'invalid_plan_id',
            'message': f'Invalid plan_id format: {args.plan_id}',
        }
        print(serialize_toon(result))
        sys.exit(1)

    if not validate_file_path(args.dir):
        result = {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'invalid_path',
            'message': f'Invalid directory path: {args.dir}',
        }
        print(serialize_toon(result))
        sys.exit(1)

    plan_dir = get_plan_dir(args.plan_id)
    target_dir = plan_dir / args.dir

    already_exists = target_dir.exists()
    target_dir.mkdir(parents=True, exist_ok=True)

    result = {
        'status': 'success',
        'plan_id': args.plan_id,
        'action': 'exists' if already_exists else 'created',
        'dir': args.dir,
        'path': str(target_dir),
    }
    print(serialize_toon(result))


def cmd_create_or_reference(args):
    """Create plan directory if it doesn't exist, or reference existing one.

    Returns TOON output indicating whether the plan was created or already exists.
    This replaces the two-step list+check pattern in plan-init.
    """
    if not validate_plan_id(args.plan_id):
        result = {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'invalid_plan_id',
            'message': f'Invalid plan_id format: {args.plan_id}',
        }
        print(serialize_toon(result))
        sys.exit(1)

    plan_dir = get_plan_dir(args.plan_id)

    if plan_dir.exists():
        # Plan already exists - gather info about it
        result = {'status': 'success', 'plan_id': args.plan_id, 'action': 'exists', 'path': str(plan_dir)}

        # Check if status.toon exists to get phase info
        status_path = plan_dir / 'status.toon'
        if status_path.exists():
            try:
                status = parse_toon(status_path.read_text(encoding='utf-8'))
                result['current_phase'] = status.get('current_phase', 'unknown')
            except (ValueError, KeyError, OSError):
                # Parse error or read error - just note file exists
                result['has_status'] = True

        print(serialize_toon(result))
    else:
        # Create the plan directory
        plan_dir.mkdir(parents=True, exist_ok=True)

        result = {'status': 'success', 'plan_id': args.plan_id, 'action': 'created', 'path': str(plan_dir)}
        print(serialize_toon(result))


def cmd_delete_plan(args):
    """Delete an entire plan directory.

    Returns TOON output indicating the deletion result.
    Used by plan-init when user selects 'Replace' for an existing plan.

    See: standards/plan-overwrite.md for the full workflow.
    """
    import shutil

    if not validate_plan_id(args.plan_id):
        result = {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'invalid_plan_id',
            'message': f'Invalid plan_id format: {args.plan_id}',
        }
        print(serialize_toon(result))
        sys.exit(1)

    plan_dir = get_plan_dir(args.plan_id)

    if not plan_dir.exists():
        result = {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'plan_not_found',
            'message': f'Plan directory does not exist: {plan_dir}',
        }
        print(serialize_toon(result))
        sys.exit(1)

    # Count files before deletion for audit trail
    files_removed = sum(1 for _ in plan_dir.rglob('*') if _.is_file())

    try:
        shutil.rmtree(plan_dir)
        log_entry('work', args.plan_id, 'INFO', f'[MANAGE-FILES] Deleted plan ({files_removed} files)')
        result = {
            'status': 'success',
            'plan_id': args.plan_id,
            'action': 'deleted',
            'path': str(plan_dir),
            'files_removed': files_removed,
        }
        print(serialize_toon(result))
    except PermissionError as e:
        result = {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'permission_denied',
            'message': f'Permission denied: {e}',
        }
        print(serialize_toon(result))
        sys.exit(1)
    except Exception as e:
        result = {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'delete_failed',
            'message': f'Failed to delete plan directory: {e}',
        }
        print(serialize_toon(result))
        sys.exit(1)


def main():
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


if __name__ == '__main__':
    main()

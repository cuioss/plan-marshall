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

from file_ops import atomic_write_file, get_plan_dir, output_toon, safe_main  # type: ignore[import-not-found]
from input_validation import (  # type: ignore[import-not-found]
    add_plan_id_arg,
    is_valid_relative_path,
    require_valid_plan_id,
)
from plan_logging import log_entry  # type: ignore[import-not-found]

# get_plan_dir imported from file_ops


def cmd_read(args: argparse.Namespace) -> dict | None:
    """Read file content from plan directory."""
    require_valid_plan_id(args)

    if not is_valid_relative_path(args.file):
        return {'status': 'error', 'error': 'invalid_path', 'message': f'Invalid file path: {args.file}'}

    plan_dir = get_plan_dir(args.plan_id)
    file_path = plan_dir / args.file

    if not file_path.exists():
        return {'status': 'error', 'error': 'file_not_found', 'message': f'File not found: {file_path}'}

    # Raw content output (not TOON) - print directly and return None
    print(file_path.read_text(encoding='utf-8'), end='')
    return None


def cmd_write(args: argparse.Namespace) -> dict:
    """Write content to file in plan directory."""
    require_valid_plan_id(args)

    if not is_valid_relative_path(args.file):
        return {'status': 'error', 'error': 'invalid_path', 'message': f'Invalid file path: {args.file}'}

    plan_dir = get_plan_dir(args.plan_id)
    file_path = plan_dir / args.file

    # Get content from stdin or --content
    if args.stdin:
        content = sys.stdin.read()
    elif args.content:
        content = args.content
    else:
        return {'status': 'error', 'error': 'missing_content', 'message': 'Must provide --content or --stdin'}

    if not content:
        return {'status': 'error', 'error': 'empty_content', 'message': 'Content cannot be empty'}

    # Ensure plan directory exists
    plan_dir.mkdir(parents=True, exist_ok=True)

    # Write atomically
    atomic_write_file(file_path, content)
    log_entry('work', args.plan_id, 'INFO', f'[MANAGE-FILES] Created {args.file}')
    return {'status': 'success', 'action': 'created', 'file': args.file, 'path': str(file_path)}


def cmd_remove(args: argparse.Namespace) -> dict:
    """Remove file from plan directory."""
    require_valid_plan_id(args)

    if not is_valid_relative_path(args.file):
        return {'status': 'error', 'error': 'invalid_path', 'message': f'Invalid file path: {args.file}'}

    plan_dir = get_plan_dir(args.plan_id)
    file_path = plan_dir / args.file

    if not file_path.exists():
        return {'status': 'error', 'error': 'file_not_found', 'message': f'File not found: {file_path}'}

    file_path.unlink()
    log_entry('work', args.plan_id, 'INFO', f'[MANAGE-FILES] Removed {args.file}')
    return {'status': 'success', 'action': 'removed', 'file': args.file, 'path': str(file_path)}


def cmd_list(args: argparse.Namespace) -> dict:
    """List files in plan directory."""
    require_valid_plan_id(args)

    plan_dir = get_plan_dir(args.plan_id)

    if args.dir:
        if not is_valid_relative_path(args.dir):
            return {'status': 'error', 'error': 'invalid_path', 'message': f'Invalid directory path: {args.dir}'}
        target_dir = plan_dir / args.dir
    else:
        target_dir = plan_dir

    if not target_dir.exists():
        return {'status': 'error', 'error': 'dir_not_found', 'message': f'Directory not found: {target_dir}'}

    files = []
    for item in sorted(target_dir.iterdir()):
        if item.is_dir():
            files.append(f'{item.name}/')
        else:
            files.append(item.name)

    return {'status': 'success', 'plan_id': args.plan_id, 'files': files}


def cmd_exists(args) -> dict:
    """Check if file exists in plan directory.

    Returns dict with exists: true/false.
    """
    require_valid_plan_id(args)

    if not is_valid_relative_path(args.file):
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'file': args.file,
            'error': 'invalid_path',
            'message': f'Invalid file path: {args.file}',
        }

    plan_dir = get_plan_dir(args.plan_id)
    file_path = plan_dir / args.file

    return {
        'status': 'success',
        'plan_id': args.plan_id,
        'file': args.file,
        'exists': file_path.exists(),
        'path': str(file_path),
    }


def cmd_mkdir(args) -> dict:
    """Create subdirectory in plan directory.

    Returns dict with the created directory path.
    """
    require_valid_plan_id(args)

    if not is_valid_relative_path(args.dir):
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'invalid_path',
            'message': f'Invalid directory path: {args.dir}',
        }

    plan_dir = get_plan_dir(args.plan_id)
    target_dir = plan_dir / args.dir

    already_exists = target_dir.exists()
    target_dir.mkdir(parents=True, exist_ok=True)

    return {
        'status': 'success',
        'plan_id': args.plan_id,
        'action': 'exists' if already_exists else 'created',
        'dir': args.dir,
        'path': str(target_dir),
    }


def cmd_create_or_reference(args) -> dict:
    """Create plan directory if it doesn't exist, or reference existing one.

    Returns dict indicating whether the plan was created or already exists.
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

        return result
    else:
        # Create the plan directory
        plan_dir.mkdir(parents=True, exist_ok=True)

        return {'status': 'success', 'plan_id': args.plan_id, 'action': 'created', 'path': str(plan_dir)}


@safe_main
def main() -> int:
    parser = argparse.ArgumentParser(
        description='Generic file I/O operations for plan directories', allow_abbrev=False
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    # read
    read_parser = subparsers.add_parser('read', help='Read file content', allow_abbrev=False)
    add_plan_id_arg(read_parser)
    read_parser.add_argument('--file', required=True, help='Relative file path')
    read_parser.set_defaults(func=cmd_read)

    # write
    write_parser = subparsers.add_parser('write', help='Write file content', allow_abbrev=False)
    add_plan_id_arg(write_parser)
    write_parser.add_argument('--file', required=True, help='Relative file path')
    write_parser.add_argument('--content', help='Content to write')
    write_parser.add_argument('--stdin', action='store_true', help='Read content from stdin')
    write_parser.set_defaults(func=cmd_write)

    # remove
    remove_parser = subparsers.add_parser('remove', help='Remove file', allow_abbrev=False)
    add_plan_id_arg(remove_parser)
    remove_parser.add_argument('--file', required=True, help='Relative file path')
    remove_parser.set_defaults(func=cmd_remove)

    # list
    list_parser = subparsers.add_parser('list', help='List files', allow_abbrev=False)
    add_plan_id_arg(list_parser)
    list_parser.add_argument('--dir', help='Subdirectory to list')
    list_parser.set_defaults(func=cmd_list)

    # exists
    exists_parser = subparsers.add_parser('exists', help='Check if file exists', allow_abbrev=False)
    add_plan_id_arg(exists_parser)
    exists_parser.add_argument('--file', required=True, help='Relative file path')
    exists_parser.set_defaults(func=cmd_exists)

    # mkdir
    mkdir_parser = subparsers.add_parser('mkdir', help='Create subdirectory', allow_abbrev=False)
    add_plan_id_arg(mkdir_parser)
    mkdir_parser.add_argument('--dir', required=True, help='Directory to create')
    mkdir_parser.set_defaults(func=cmd_mkdir)

    # create-or-reference
    create_ref_parser = subparsers.add_parser(
        'create-or-reference',
        help='Create plan directory or reference existing one',
        allow_abbrev=False,
    )
    add_plan_id_arg(create_ref_parser)
    create_ref_parser.set_defaults(func=cmd_create_or_reference)

    args = parser.parse_args()
    result = args.func(args)
    if result is not None:
        output_toon(result)
    return 0


if __name__ == '__main__':
    main()

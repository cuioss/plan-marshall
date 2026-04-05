#!/usr/bin/env python3
"""List management command handlers for manage-references.

Handles: add-file, remove-file, add-list, set-list
"""

from _references_core import (
    read_references,
    require_references,
    write_references,
)
from input_validation import require_valid_plan_id  # type: ignore[import-not-found]


def cmd_add_file(args) -> dict:
    """Add a file to modified_files list."""
    require_valid_plan_id(args)

    refs = read_references(args.plan_id)
    if 'modified_files' not in refs:
        refs['modified_files'] = []

    if args.file not in refs['modified_files']:
        refs['modified_files'].append(args.file)
        write_references(args.plan_id, refs)

    return {
        'status': 'success',
        'plan_id': args.plan_id,
        'section': 'modified_files',
        'added': args.file,
        'total': len(refs['modified_files']),
    }


def cmd_remove_file(args) -> dict:
    """Remove a file from modified_files list."""
    require_valid_plan_id(args)

    refs = read_references(args.plan_id)
    if 'modified_files' not in refs or args.file not in refs['modified_files']:
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'not_found',
            'message': f"File '{args.file}' not in modified_files",
        }

    refs['modified_files'].remove(args.file)
    write_references(args.plan_id, refs)

    return {
        'status': 'success',
        'plan_id': args.plan_id,
        'section': 'modified_files',
        'removed': args.file,
        'total': len(refs['modified_files']),
    }


def cmd_add_list(args) -> dict:
    """Add multiple values to a list field."""
    require_valid_plan_id(args)

    refs = read_references(args.plan_id)

    # Initialize field as list if not exists
    if args.field not in refs:
        refs[args.field] = []
    elif not isinstance(refs[args.field], list):
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'field': args.field,
            'error': 'not_a_list',
            'message': f"Field '{args.field}' is not a list",
        }

    # Parse comma-separated values
    values = [v.strip() for v in args.values.split(',') if v.strip()]
    added = []
    for value in values:
        if value not in refs[args.field]:
            refs[args.field].append(value)
            added.append(value)

    write_references(args.plan_id, refs)

    return {
        'status': 'success',
        'plan_id': args.plan_id,
        'field': args.field,
        'added_count': len(added),
        'total': len(refs[args.field]),
    }


def cmd_set_list(args) -> dict:
    """Set a list field to new values (replaces existing list)."""
    require_valid_plan_id(args)

    refs = require_references(args.plan_id)

    # Get previous count if field exists
    previous_count = 0
    if args.field in refs and isinstance(refs[args.field], list):
        previous_count = len(refs[args.field])

    # Parse comma-separated values
    values = [v.strip() for v in args.values.split(',') if v.strip()]

    # Set the field to the new list (replaces existing)
    refs[args.field] = values
    write_references(args.plan_id, refs)

    return {
        'status': 'success',
        'plan_id': args.plan_id,
        'field': args.field,
        'previous_count': previous_count,
        'count': len(values),
    }

#!/usr/bin/env python3
"""List management command handlers for manage-references.

Handles: add-list, set-list
"""

import argparse

from _references_core import (
    read_references,
    require_references,
    write_references,
)
from input_validation import require_valid_plan_id  # type: ignore[import-not-found]


def cmd_add_list(args: argparse.Namespace) -> dict:
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


def cmd_set_list(args: argparse.Namespace) -> dict:
    """Set a list field to new values (replaces existing list)."""
    require_valid_plan_id(args)

    refs = require_references(args.plan_id)
    if refs.get('status') == 'error':
        return refs

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

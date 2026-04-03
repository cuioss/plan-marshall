#!/usr/bin/env python3
"""CRUD command handlers for manage-references.

Handles: create, read, get, set
"""

import sys

from _ref_core import (
    get_references_path,
    output_toon,
    read_references,
    require_references,
    require_valid_plan_id,
    write_references,
)


def cmd_create(args):
    """Create references.json with basic fields."""
    require_valid_plan_id(args)

    path = get_references_path(args.plan_id)
    if path.exists():
        output_toon(
            {
                'status': 'error',
                'plan_id': args.plan_id,
                'error': 'already_exists',
                'message': 'references.json already exists',
            }
        )
        sys.exit(1)

    # Build base references
    refs = {'branch': args.branch, 'base_branch': 'main', 'modified_files': []}

    # Add optional fields
    if args.issue_url:
        refs['issue_url'] = args.issue_url
    if args.build_system:
        refs['build_system'] = args.build_system
    if args.domains:
        refs['domains'] = [d.strip() for d in args.domains.split(',') if d.strip()]

    write_references(args.plan_id, refs)

    output_toon(
        {
            'status': 'success',
            'plan_id': args.plan_id,
            'file': 'references.json',
            'created': True,
            'fields': list(refs.keys()),
        }
    )


def cmd_read(args):
    """Read entire references.json."""
    require_valid_plan_id(args)

    refs = require_references(args.plan_id)

    # Summarize lists
    summary = {}
    for key, value in refs.items():
        if isinstance(value, list):
            summary[key] = f'{len(value)} items'
        else:
            summary[key] = value

    output_toon({'status': 'success', 'plan_id': args.plan_id, 'references': summary})


def cmd_get(args):
    """Get a specific field value."""
    require_valid_plan_id(args)

    refs = require_references(args.plan_id)

    value = refs.get(args.field)
    if value is None:
        output_toon(
            {
                'status': 'error',
                'plan_id': args.plan_id,
                'field': args.field,
                'error': 'field_not_found',
                'message': f"Field '{args.field}' not found",
            }
        )
        sys.exit(1)

    output_toon({'status': 'success', 'plan_id': args.plan_id, 'field': args.field, 'value': value})


def cmd_set(args):
    """Set a specific field value."""
    require_valid_plan_id(args)

    refs = read_references(args.plan_id)
    previous = refs.get(args.field)
    refs[args.field] = args.value
    write_references(args.plan_id, refs)

    result = {'status': 'success', 'plan_id': args.plan_id, 'field': args.field, 'value': args.value}
    if previous is not None:
        result['previous'] = previous
    output_toon(result)

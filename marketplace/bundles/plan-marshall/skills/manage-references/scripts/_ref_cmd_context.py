#!/usr/bin/env python3
"""Context retrieval command handler for manage-references.

Handles: get-context
"""

from _ref_core import (
    output_toon,
    require_references,
    validate_plan_id,
)


def cmd_get_context(args):
    """Get all references context in one call."""
    validate_plan_id(args.plan_id)

    refs = require_references(args.plan_id)

    # Build comprehensive context
    context = {
        'status': 'success',
        'plan_id': args.plan_id,
        'branch': refs.get('branch', ''),
        'base_branch': refs.get('base_branch', 'main'),
        'modified_files_count': len(refs.get('modified_files', [])),
    }

    # Include optional fields if present
    if refs.get('issue_url'):
        context['issue_url'] = refs['issue_url']
    if refs.get('build_system'):
        context['build_system'] = refs['build_system']

    # Include file lists if requested
    if args.include_files:
        context['modified_files'] = refs.get('modified_files', [])

    output_toon(context)

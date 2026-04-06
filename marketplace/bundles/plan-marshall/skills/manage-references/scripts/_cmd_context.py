#!/usr/bin/env python3
"""Context retrieval command handler for manage-references.

Handles: get-context
"""

from _references_core import (
    require_references,
)
from input_validation import require_valid_plan_id  # type: ignore[import-not-found]


def cmd_get_context(args) -> dict | None:
    """Get all references context in one call."""
    require_valid_plan_id(args)

    refs = require_references(args.plan_id)
    if refs is None:
        return None

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

    return context

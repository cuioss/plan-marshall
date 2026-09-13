#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Context retrieval command handler for manage-references.

Handles: get-context
"""

import argparse

from _references_core import (
    require_references,
)
from input_validation import require_valid_plan_id


def cmd_get_context(args: argparse.Namespace) -> dict:
    """Get all references context in one call."""
    require_valid_plan_id(args)

    refs = require_references(args.plan_id)
    if refs.get('status') == 'error':
        return refs

    # Build comprehensive context
    context = {
        'status': 'success',
        'plan_id': args.plan_id,
        'branch': refs.get('branch', ''),
        'base_branch': refs.get('base_branch', 'main'),
    }

    # Include optional fields if present
    if refs.get('issue_url'):
        context['issue_url'] = refs['issue_url']
    if refs.get('build_system'):
        context['build_system'] = refs['build_system']

    return context

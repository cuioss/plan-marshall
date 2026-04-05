#!/usr/bin/env python3
"""
Routing and diagnostics command handlers for manage-status: route, get-routing-context, self-test.
"""

import argparse
from typing import Any

from _status_core import (
    PHASE_ROUTING,
    require_status,
)
from constants import PHASE_STATUS_DONE, PHASES  # type: ignore[import-not-found]


def cmd_route(args: argparse.Namespace) -> dict:
    """Get skill for a phase."""
    if args.phase not in PHASE_ROUTING:
        return {
            'status': 'error',
            'phase': args.phase,
            'error': 'unknown_phase',
            'message': f'Unknown phase: {args.phase}',
            'valid_phases': list(PHASE_ROUTING.keys()),
        }

    skill, description = PHASE_ROUTING[args.phase]

    return {'status': 'success', 'phase': args.phase, 'skill': skill, 'description': description}


def cmd_get_routing_context(args: argparse.Namespace) -> dict:
    """Get combined routing context: phase, skill, and progress in one call."""
    status = require_status(args)

    current_phase = status.get('current_phase', 'unknown')
    phases = status.get('phases', [])

    # Calculate progress
    total = len(phases)
    completed = sum(1 for p in phases if p.get('status') == PHASE_STATUS_DONE)

    # Get skill routing
    skill = 'unknown'
    description = 'Unknown phase'
    if current_phase in PHASE_ROUTING:
        skill, description = PHASE_ROUTING[current_phase]

    return {
        'status': 'success',
        'plan_id': args.plan_id,
        'title': status.get('title', ''),
        'current_phase': current_phase,
        'skill': skill,
        'skill_description': description,
        'total_phases': total,
        'completed_phases': completed,
        'phases': [{'name': p['name'], 'status': p['status']} for p in phases],
    }


def cmd_self_test(_args: argparse.Namespace) -> dict:
    """Verify manage-status health: imports, routing, and directory access."""
    from _status_core import get_plans_dir

    checks: list[tuple[str, bool]] = []

    # Check imports
    try:
        from file_ops import base_path as _bp  # noqa: F401

        checks.append(('import_file_ops', True))
    except ImportError:
        checks.append(('import_file_ops', False))

    try:
        from toon_parser import serialize_toon as _st  # noqa: F401

        checks.append(('import_toon_parser', True))
    except ImportError:
        checks.append(('import_toon_parser', False))

    # Check phase routing completeness
    expected = set(PHASES)
    checks.append(('phase_routing_complete', expected.issubset(PHASE_ROUTING.keys())))

    # Check plans directory is writable
    plans_dir = get_plans_dir()
    plans_dir.mkdir(parents=True, exist_ok=True)
    checks.append(('plans_dir_writable', plans_dir.exists()))

    passed = sum(1 for _, ok in checks if ok)
    failed = sum(1 for _, ok in checks if not ok)
    failures = [name for name, ok in checks if not ok]

    result: dict[str, Any] = {
        'status': 'success' if failed == 0 else 'error',
        'passed': passed,
        'failed': failed,
    }
    if failures:
        result['failures'] = ','.join(failures)

    return result

#!/usr/bin/env python3
"""
Query command handlers for manage-status: read, progress, metadata, get-context, list.
"""

import argparse
from typing import Any

from _status_core import (
    _try_read_status_json,
    get_plans_dir,
    log_entry,
    output_toon,
    require_status,
    write_status,
)
from constants import PHASE_STATUS_DONE, PHASE_STATUS_IN_PROGRESS  # type: ignore[import-not-found]


def cmd_read(args: argparse.Namespace) -> int:
    """Read plan status."""
    status = require_status(args)
    output_toon({'status': 'success', 'plan_id': args.plan_id, 'plan': status})
    return 0


def cmd_set_phase(args: argparse.Namespace) -> int:
    """Set current phase."""
    status = require_status(args)

    phase_names = [p['name'] for p in status.get('phases', [])]
    if args.phase not in phase_names:
        output_toon(
            {
                'status': 'error',
                'plan_id': args.plan_id,
                'error': 'invalid_phase',
                'message': f'Invalid phase: {args.phase}',
                'valid_phases': phase_names,
            }
        )
        return 1

    previous = status.get('current_phase')
    status['current_phase'] = args.phase

    # Update phase statuses
    for phase in status['phases']:
        if phase['name'] == args.phase:
            phase['status'] = PHASE_STATUS_IN_PROGRESS

    write_status(args.plan_id, status)
    log_entry('work', args.plan_id, 'INFO', f'[MANAGE-STATUS] Phase: {previous} -> {args.phase}')

    output_toon({'status': 'success', 'plan_id': args.plan_id, 'current_phase': args.phase, 'previous_phase': previous})
    return 0


def cmd_update_phase(args: argparse.Namespace) -> int:
    """Update a specific phase status."""
    status = require_status(args)

    found = False
    for phase in status.get('phases', []):
        if phase['name'] == args.phase:
            phase['status'] = args.status
            found = True
            break

    if not found:
        output_toon(
            {
                'status': 'error',
                'plan_id': args.plan_id,
                'error': 'phase_not_found',
                'message': f"Phase '{args.phase}' not found",
            }
        )
        return 1

    write_status(args.plan_id, status)

    output_toon({'status': 'success', 'plan_id': args.plan_id, 'phase': args.phase, 'phase_status': args.status})
    return 0


def cmd_progress(args: argparse.Namespace) -> int:
    """Calculate plan progress."""
    status = require_status(args)

    phases = status.get('phases', [])
    total = len(phases)
    completed = sum(1 for p in phases if p.get('status') == PHASE_STATUS_DONE)
    percent = int((completed / total) * 100) if total > 0 else 0

    output_toon(
        {
            'status': 'success',
            'plan_id': args.plan_id,
            'progress': {
                'total_phases': total,
                'completed_phases': completed,
                'current_phase': status.get('current_phase'),
                'percent': percent,
            },
        }
    )
    return 0


def cmd_metadata(args: argparse.Namespace) -> int:
    """Get or set a metadata field in status.json."""
    status = require_status(args)

    if args.set:
        # Set metadata
        if 'metadata' not in status:
            status['metadata'] = {}

        previous_value = status['metadata'].get(args.field)
        status['metadata'][args.field] = args.value

        write_status(args.plan_id, status)
        log_entry('work', args.plan_id, 'INFO', f'[MANAGE-STATUS] Metadata: {args.field}={args.value}')

        result: dict[str, Any] = {
            'status': 'success',
            'plan_id': args.plan_id,
            'field': args.field,
            'value': args.value,
        }
        if previous_value is not None:
            result['previous_value'] = previous_value
        output_toon(result)
        return 0

    elif args.get:
        # Get metadata
        metadata = status.get('metadata', {})
        value = metadata.get(args.field)

        if value is None:
            output_toon(
                {
                    'status': 'not_found',
                    'plan_id': args.plan_id,
                    'field': args.field,
                    'message': f"Metadata field '{args.field}' not found",
                    'available_fields': list(metadata.keys()),
                }
            )
            return 0

        output_toon(
            {
                'status': 'success',
                'plan_id': args.plan_id,
                'field': args.field,
                'value': value,
            }
        )
        return 0

    else:
        output_toon(
            {
                'status': 'error',
                'plan_id': args.plan_id,
                'error': 'missing_operation',
                'message': 'Either --get or --set is required',
            }
        )
        return 1


def cmd_get_context(args: argparse.Namespace) -> int:
    """Get combined status context (phase, progress, metadata)."""
    status = require_status(args)

    phases = status.get('phases', [])
    total = len(phases)
    completed = sum(1 for p in phases if p.get('status') == PHASE_STATUS_DONE)

    # Build context
    context: dict[str, Any] = {
        'status': 'success',
        'plan_id': args.plan_id,
        'title': status.get('title', ''),
        'current_phase': status.get('current_phase', 'unknown'),
        'total_phases': total,
        'completed_phases': completed,
    }

    # Include metadata fields at top level for convenience
    metadata = status.get('metadata', {})
    for key, value in metadata.items():
        context[key] = value

    output_toon(context)
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    """Discover all plans."""
    plans_dir = get_plans_dir()
    if not plans_dir.exists():
        output_toon({'status': 'success', 'total': 0, 'plans': []})
        return 0

    plans = []
    for plan_dir in sorted(plans_dir.iterdir()):
        if not plan_dir.is_dir():
            continue

        # Try status.json first (new format)
        status = _try_read_status_json(plan_dir)
        if not status:
            continue

        try:
            current_phase = status.get('current_phase', 'unknown')

            # Apply filter if provided
            if args.filter:
                filter_phases = [p.strip() for p in args.filter.split(',')]
                if current_phase not in filter_phases:
                    continue

            plans.append({'id': plan_dir.name, 'current_phase': current_phase, 'status': PHASE_STATUS_IN_PROGRESS})
        except (KeyError, TypeError):
            # Skip plans with corrupted status
            continue

    output_toon({'status': 'success', 'total': len(plans), 'plans': plans})
    return 0

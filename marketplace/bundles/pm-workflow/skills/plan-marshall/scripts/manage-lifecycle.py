#!/usr/bin/env python3
"""
Manage plan lifecycle with phase routing and transitions.

Handles plan discovery, phase transitions, archiving, and routing.
Status operations are delegated to manage-status.

Usage:
    python3 manage-lifecycle.py list
    python3 manage-lifecycle.py transition --plan-id my-plan --completed 1-init
    python3 manage-lifecycle.py archive --plan-id my-plan
    python3 manage-lifecycle.py route --phase 1-init
    python3 manage-lifecycle.py get-routing-context --plan-id my-plan
"""

import argparse
import json
import re
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from file_ops import base_path  # type: ignore[import-not-found]

# Import from manage-status for shared functionality
from manage_status import read_status as read_status_json
from manage_status import write_status as write_status_json
from toon_parser import serialize_toon  # type: ignore[import-not-found]

# Phase routing maps phase names to skills (for route command)
PHASE_ROUTING = {
    '1-init': ('plan-init', 'Initialize plan structure'),
    '2-refine': ('request-refine', 'Clarify request until confident'),
    '3-outline': ('solution-outline', 'Create solution outline with deliverables'),
    '4-plan': ('task-plan', 'Create tasks from deliverables'),
    '5-execute': ('plan-execute', 'Execute implementation tasks'),
    '6-verify': ('plan-verify', 'Verify implementation quality'),
    '7-finalize': ('plan-finalize', 'Finalize with commit/PR'),
}


def validate_plan_id(plan_id: str) -> bool:
    """Validate plan_id is kebab-case with no special characters."""
    return bool(re.match(r'^[a-z][a-z0-9-]*$', plan_id))


def get_plans_dir() -> Path:
    """Get the plans directory."""
    return cast(Path, base_path('plans'))


def get_archive_dir() -> Path:
    """Get the archived plans directory."""
    return cast(Path, base_path('archived-plans'))


def output_toon(data: dict) -> None:
    """Output TOON format to stdout."""
    print(serialize_toon(data))


def _try_read_status_json(plan_dir: Path) -> dict[Any, Any] | None:
    """Try to read status.json from a plan directory."""
    status_file = plan_dir / 'status.json'
    if status_file.exists():
        try:
            return cast(dict[Any, Any], json.loads(status_file.read_text(encoding='utf-8')))
        except (ValueError, OSError):
            return None
    return None


# =============================================================================
# Command: List
# =============================================================================


def cmd_list(args) -> None:
    """Discover all plans."""
    plans_dir = get_plans_dir()
    if not plans_dir.exists():
        output_toon({'status': 'success', 'total': 0, 'plans': []})
        return

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

            plans.append({'id': plan_dir.name, 'current_phase': current_phase, 'status': 'in_progress'})
        except (KeyError, TypeError):
            # Skip plans with corrupted status
            continue

    output_toon({'status': 'success', 'total': len(plans), 'plans': plans})


# =============================================================================
# Command: Transition
# =============================================================================


def cmd_transition(args) -> None:
    """Transition to next phase."""
    if not validate_plan_id(args.plan_id):
        output_toon(
            {
                'status': 'error',
                'plan_id': args.plan_id,
                'error': 'invalid_plan_id',
                'message': f'Invalid plan_id format: {args.plan_id}',
            }
        )
        sys.exit(1)

    status = read_status_json(args.plan_id)
    if not status:
        output_toon(
            {'status': 'error', 'plan_id': args.plan_id, 'error': 'file_not_found', 'message': 'status.json not found'}
        )
        sys.exit(1)

    phases = status.get('phases', [])
    phase_names = [p['name'] for p in phases]

    if args.completed not in phase_names:
        output_toon(
            {
                'status': 'error',
                'plan_id': args.plan_id,
                'error': 'invalid_phase',
                'message': f'Invalid phase: {args.completed}',
            }
        )
        sys.exit(1)

    completed_idx = phase_names.index(args.completed)

    # Mark completed phase as done
    phases[completed_idx]['status'] = 'done'

    # Determine next phase
    if completed_idx + 1 < len(phases):
        next_phase = phase_names[completed_idx + 1]
        phases[completed_idx + 1]['status'] = 'in_progress'
        status['current_phase'] = next_phase
    else:
        next_phase = None

    write_status_json(args.plan_id, status)

    result: dict[str, Any] = {'status': 'success', 'plan_id': args.plan_id, 'completed_phase': args.completed}
    if next_phase:
        result['next_phase'] = next_phase
    else:
        result['message'] = 'All phases completed'

    output_toon(result)


# =============================================================================
# Command: Archive
# =============================================================================


def cmd_archive(args) -> None:
    """Archive a completed plan."""
    if not validate_plan_id(args.plan_id):
        output_toon(
            {
                'status': 'error',
                'plan_id': args.plan_id,
                'error': 'invalid_plan_id',
                'message': f'Invalid plan_id format: {args.plan_id}',
            }
        )
        sys.exit(1)

    plan_dir = base_path('plans', args.plan_id)
    if not plan_dir.exists():
        output_toon(
            {'status': 'error', 'plan_id': args.plan_id, 'error': 'not_found', 'message': 'Plan directory not found'}
        )
        sys.exit(1)

    date_prefix = datetime.now(UTC).strftime('%Y-%m-%d')
    archive_name = f'{date_prefix}-{args.plan_id}'
    archive_dir = get_archive_dir()
    archive_path = archive_dir / archive_name

    if args.dry_run:
        output_toon(
            {'status': 'success', 'plan_id': args.plan_id, 'dry_run': True, 'would_archive_to': str(archive_path)}
        )
        return

    archive_dir.mkdir(parents=True, exist_ok=True)
    shutil.move(str(plan_dir), str(archive_path))

    output_toon({'status': 'success', 'plan_id': args.plan_id, 'archived_to': str(archive_path)})


# =============================================================================
# Command: Route
# =============================================================================


def cmd_route(args) -> None:
    """Get skill for a phase."""
    if args.phase not in PHASE_ROUTING:
        output_toon(
            {
                'status': 'error',
                'phase': args.phase,
                'error': 'unknown_phase',
                'message': f'Unknown phase: {args.phase}',
                'valid_phases': list(PHASE_ROUTING.keys()),
            }
        )
        sys.exit(1)

    skill, description = PHASE_ROUTING[args.phase]

    output_toon({'status': 'success', 'phase': args.phase, 'skill': skill, 'description': description})


# =============================================================================
# Command: Get Routing Context
# =============================================================================


def cmd_get_routing_context(args) -> None:
    """Get combined routing context: phase, skill, and progress in one call."""
    if not validate_plan_id(args.plan_id):
        output_toon(
            {
                'status': 'error',
                'plan_id': args.plan_id,
                'error': 'invalid_plan_id',
                'message': f'Invalid plan_id format: {args.plan_id}',
            }
        )
        sys.exit(1)

    status = read_status_json(args.plan_id)
    if not status:
        output_toon(
            {'status': 'error', 'plan_id': args.plan_id, 'error': 'file_not_found', 'message': 'status.json not found'}
        )
        sys.exit(1)

    current_phase = status.get('current_phase', 'unknown')
    phases = status.get('phases', [])

    # Calculate progress
    total = len(phases)
    completed = sum(1 for p in phases if p.get('status') == 'done')

    # Get skill routing
    skill = 'unknown'
    description = 'Unknown phase'
    if current_phase in PHASE_ROUTING:
        skill, description = PHASE_ROUTING[current_phase]

    output_toon(
        {
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
    )


# =============================================================================
# Main
# =============================================================================


def main() -> None:
    parser = argparse.ArgumentParser(description='Manage plan lifecycle with phase routing and transitions')
    subparsers = parser.add_subparsers(dest='command', required=True)

    # list
    list_parser = subparsers.add_parser('list', help='Discover all plans')
    list_parser.add_argument('--filter', help='Filter by phases (comma-separated)')
    list_parser.set_defaults(func=cmd_list)

    # transition
    transition_parser = subparsers.add_parser('transition', help='Transition to next phase')
    transition_parser.add_argument('--plan-id', required=True, help='Plan identifier')
    transition_parser.add_argument('--completed', required=True, help='Completed phase')
    transition_parser.set_defaults(func=cmd_transition)

    # archive
    archive_parser = subparsers.add_parser('archive', help='Archive completed plan')
    archive_parser.add_argument('--plan-id', required=True, help='Plan identifier')
    archive_parser.add_argument('--dry-run', action='store_true', help='Show what would be done')
    archive_parser.set_defaults(func=cmd_archive)

    # route
    route_parser = subparsers.add_parser('route', help='Get skill for phase')
    route_parser.add_argument('--phase', required=True, help='Phase name')
    route_parser.set_defaults(func=cmd_route)

    # get-routing-context
    routing_context_parser = subparsers.add_parser(
        'get-routing-context', help='Get combined routing context (phase, skill, progress)'
    )
    routing_context_parser.add_argument('--plan-id', required=True, help='Plan identifier')
    routing_context_parser.set_defaults(func=cmd_get_routing_context)

    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()

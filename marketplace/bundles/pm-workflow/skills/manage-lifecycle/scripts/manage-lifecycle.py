#!/usr/bin/env python3
"""
Manage plan lifecycle with status.toon and phase operations.

Replaces plan.md and absorbs phase-management functionality.

Usage:
    python3 manage-lifecycle.py read --plan-id my-plan
    python3 manage-lifecycle.py create --plan-id my-plan --title "Title" --phases 1-init,2-outline,3-plan,4-execute,5-finalize
    python3 manage-lifecycle.py set-phase --plan-id my-plan --phase execute
    python3 manage-lifecycle.py list
    python3 manage-lifecycle.py transition --plan-id my-plan --completed init
"""

import argparse
import re
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path

from file_ops import atomic_write_file, base_path  # type: ignore[import-not-found]
from plan_logging import log_entry  # type: ignore[import-not-found]
from toon_parser import parse_toon, serialize_toon  # type: ignore[import-not-found]

# Phase routing maps phase names to skills (for route command)
PHASE_ROUTING = {
    '1-init': ('plan-init', 'Initialize plan structure'),
    '2-outline': ('solution-outline', 'Create solution outline with deliverables'),
    '3-plan': ('task-plan', 'Create tasks from deliverables'),
    '4-execute': ('plan-execute', 'Execute implementation tasks'),
    '5-finalize': ('plan-finalize', 'Finalize with commit/PR'),
}


def validate_plan_id(plan_id: str) -> bool:
    """Validate plan_id is kebab-case with no special characters."""
    return bool(re.match(r'^[a-z][a-z0-9-]*$', plan_id))


def get_status_path(plan_id: str) -> Path:
    """Get the status.toon file path."""
    return base_path('plans', plan_id, 'status.toon')


def get_plans_dir() -> Path:
    """Get the plans directory."""
    return base_path('plans')


def get_archive_dir() -> Path:
    """Get the archived plans directory."""
    return base_path('archived-plans')


def now_iso() -> str:
    """Get current time in ISO format."""
    return datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')


def read_status(plan_id: str) -> dict:
    """Read status.toon for a plan."""
    path = get_status_path(plan_id)
    if not path.exists():
        return {}
    return parse_toon(path.read_text(encoding='utf-8'))


def write_status(plan_id: str, status: dict):
    """Write status.toon for a plan."""
    path = get_status_path(plan_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    status['updated'] = now_iso()
    atomic_write_file(path, serialize_toon(status))


def output_toon(data: dict):
    """Output TOON format to stdout."""
    print(serialize_toon(data))


def cmd_read(args):
    """Read plan status."""
    if not validate_plan_id(args.plan_id):
        output_toon({
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'invalid_plan_id',
            'message': f"Invalid plan_id format: {args.plan_id}"
        })
        sys.exit(1)

    status = read_status(args.plan_id)
    if not status:
        output_toon({
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'file_not_found',
            'message': 'status.toon not found'
        })
        sys.exit(1)

    output_toon({
        'status': 'success',
        'plan_id': args.plan_id,
        'plan': status
    })


def cmd_create(args):
    """Create status.toon for a new plan."""
    if not validate_plan_id(args.plan_id):
        output_toon({
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'invalid_plan_id',
            'message': f"Invalid plan_id format: {args.plan_id}"
        })
        sys.exit(1)

    path = get_status_path(args.plan_id)
    if path.exists() and not args.force:
        output_toon({
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'file_exists',
            'message': 'status.toon already exists. Use --force to overwrite.'
        })
        sys.exit(1)

    # Parse phases from comma-separated argument
    phases = [p.strip() for p in args.phases.split(',') if p.strip()]
    if not phases:
        output_toon({
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'invalid_phases',
            'message': 'At least one phase is required'
        })
        sys.exit(1)

    now = now_iso()

    status = {
        'title': args.title,
        'current_phase': phases[0],
        'phases': [{'name': p, 'status': 'pending'} for p in phases],
        'created': now,
        'updated': now
    }
    # Mark first phase as in_progress
    status['phases'][0]['status'] = 'in_progress'

    write_status(args.plan_id, status)

    output_toon({
        'status': 'success',
        'plan_id': args.plan_id,
        'file': 'status.toon',
        'created': True,
        'plan': {
            'title': args.title,
            'current_phase': phases[0]
        }
    })


def cmd_set_phase(args):
    """Set current phase."""
    if not validate_plan_id(args.plan_id):
        output_toon({
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'invalid_plan_id',
            'message': f"Invalid plan_id format: {args.plan_id}"
        })
        sys.exit(1)

    status = read_status(args.plan_id)
    if not status:
        output_toon({
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'file_not_found',
            'message': 'status.toon not found'
        })
        sys.exit(1)

    phase_names = [p['name'] for p in status.get('phases', [])]
    if args.phase not in phase_names:
        output_toon({
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'invalid_phase',
            'message': f"Invalid phase: {args.phase}",
            'valid_phases': phase_names
        })
        sys.exit(1)

    previous = status.get('current_phase')
    status['current_phase'] = args.phase

    # Update phase statuses
    for phase in status['phases']:
        if phase['name'] == args.phase:
            phase['status'] = 'in_progress'

    write_status(args.plan_id, status)
    log_entry('work', args.plan_id, 'INFO', f'[MANAGE-LIFECYCLE] Phase: {previous} -> {args.phase}')

    output_toon({
        'status': 'success',
        'plan_id': args.plan_id,
        'current_phase': args.phase,
        'previous_phase': previous
    })


def cmd_update_phase(args):
    """Update a specific phase status."""
    if not validate_plan_id(args.plan_id):
        output_toon({
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'invalid_plan_id',
            'message': f"Invalid plan_id format: {args.plan_id}"
        })
        sys.exit(1)

    status = read_status(args.plan_id)
    if not status:
        output_toon({
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'file_not_found',
            'message': 'status.toon not found'
        })
        sys.exit(1)

    found = False
    for phase in status.get('phases', []):
        if phase['name'] == args.phase:
            phase['status'] = args.status
            found = True
            break

    if not found:
        output_toon({
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'phase_not_found',
            'message': f"Phase '{args.phase}' not found"
        })
        sys.exit(1)

    write_status(args.plan_id, status)

    output_toon({
        'status': 'success',
        'plan_id': args.plan_id,
        'phase': args.phase,
        'phase_status': args.status
    })


def cmd_progress(args):
    """Calculate plan progress."""
    if not validate_plan_id(args.plan_id):
        output_toon({
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'invalid_plan_id',
            'message': f"Invalid plan_id format: {args.plan_id}"
        })
        sys.exit(1)

    status = read_status(args.plan_id)
    if not status:
        output_toon({
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'file_not_found',
            'message': 'status.toon not found'
        })
        sys.exit(1)

    phases = status.get('phases', [])
    total = len(phases)
    completed = sum(1 for p in phases if p.get('status') == 'done')
    percent = int((completed / total) * 100) if total > 0 else 0

    output_toon({
        'status': 'success',
        'plan_id': args.plan_id,
        'progress': {
            'total_phases': total,
            'completed_phases': completed,
            'current_phase': status.get('current_phase'),
            'percent': percent
        }
    })


def cmd_list(args):
    """Discover all plans."""
    plans_dir = get_plans_dir()
    if not plans_dir.exists():
        output_toon({
            'status': 'success',
            'total': 0,
            'plans': []
        })
        return

    plans = []
    for plan_dir in sorted(plans_dir.iterdir()):
        if not plan_dir.is_dir():
            continue

        status_file = plan_dir / 'status.toon'
        if not status_file.exists():
            continue

        try:
            status = parse_toon(status_file.read_text(encoding='utf-8'))
            current_phase = status.get('current_phase', 'unknown')

            # Apply filter if provided
            if args.filter:
                filter_phases = [p.strip() for p in args.filter.split(',')]
                if current_phase not in filter_phases:
                    continue

            plans.append({
                'id': plan_dir.name,
                'current_phase': current_phase,
                'status': 'in_progress'
            })
        except (ValueError, KeyError, OSError):
            # Skip plans with corrupted or unreadable status files
            continue

    output_toon({
        'status': 'success',
        'total': len(plans),
        'plans': plans
    })


def cmd_transition(args):
    """Transition to next phase."""
    if not validate_plan_id(args.plan_id):
        output_toon({
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'invalid_plan_id',
            'message': f"Invalid plan_id format: {args.plan_id}"
        })
        sys.exit(1)

    status = read_status(args.plan_id)
    if not status:
        output_toon({
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'file_not_found',
            'message': 'status.toon not found'
        })
        sys.exit(1)

    phases = status.get('phases', [])
    phase_names = [p['name'] for p in phases]

    if args.completed not in phase_names:
        output_toon({
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'invalid_phase',
            'message': f"Invalid phase: {args.completed}"
        })
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

    write_status(args.plan_id, status)

    result = {
        'status': 'success',
        'plan_id': args.plan_id,
        'completed_phase': args.completed
    }
    if next_phase:
        result['next_phase'] = next_phase
    else:
        result['message'] = 'All phases completed'

    output_toon(result)


def cmd_archive(args):
    """Archive a completed plan."""
    if not validate_plan_id(args.plan_id):
        output_toon({
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'invalid_plan_id',
            'message': f"Invalid plan_id format: {args.plan_id}"
        })
        sys.exit(1)

    plan_dir = base_path('plans', args.plan_id)
    if not plan_dir.exists():
        output_toon({
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'not_found',
            'message': 'Plan directory not found'
        })
        sys.exit(1)

    date_prefix = datetime.utcnow().strftime('%Y-%m-%d')
    archive_name = f"{date_prefix}-{args.plan_id}"
    archive_dir = get_archive_dir()
    archive_path = archive_dir / archive_name

    if args.dry_run:
        output_toon({
            'status': 'success',
            'plan_id': args.plan_id,
            'dry_run': True,
            'would_archive_to': str(archive_path)
        })
        return

    archive_dir.mkdir(parents=True, exist_ok=True)
    shutil.move(str(plan_dir), str(archive_path))

    output_toon({
        'status': 'success',
        'plan_id': args.plan_id,
        'archived_to': str(archive_path)
    })


def cmd_route(args):
    """Get skill for a phase."""
    if args.phase not in PHASE_ROUTING:
        output_toon({
            'status': 'error',
            'phase': args.phase,
            'error': 'unknown_phase',
            'message': f"Unknown phase: {args.phase}",
            'valid_phases': list(PHASE_ROUTING.keys())
        })
        sys.exit(1)

    skill, description = PHASE_ROUTING[args.phase]

    output_toon({
        'status': 'success',
        'phase': args.phase,
        'skill': skill,
        'description': description
    })


def cmd_get_routing_context(args):
    """Get combined routing context: phase, skill, and progress in one call."""
    if not validate_plan_id(args.plan_id):
        output_toon({
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'invalid_plan_id',
            'message': f"Invalid plan_id format: {args.plan_id}"
        })
        sys.exit(1)

    status = read_status(args.plan_id)
    if not status:
        output_toon({
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'file_not_found',
            'message': 'status.toon not found'
        })
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

    output_toon({
        'status': 'success',
        'plan_id': args.plan_id,
        'title': status.get('title', ''),
        'current_phase': current_phase,
        'skill': skill,
        'skill_description': description,
        'total_phases': total,
        'completed_phases': completed,
        'phases': [{'name': p['name'], 'status': p['status']} for p in phases]
    })


def main():
    parser = argparse.ArgumentParser(
        description='Manage plan lifecycle with status.toon and phase operations'
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    # read
    read_parser = subparsers.add_parser('read', help='Read plan status')
    read_parser.add_argument('--plan-id', required=True, help='Plan identifier')
    read_parser.set_defaults(func=cmd_read)

    # create
    create_parser = subparsers.add_parser('create', help='Create status.toon')
    create_parser.add_argument('--plan-id', required=True, help='Plan identifier')
    create_parser.add_argument('--title', required=True, help='Plan title')
    create_parser.add_argument('--phases', required=True,
                               help='Comma-separated phase names (e.g., 1-init,2-outline,3-plan,4-execute,5-finalize)')
    create_parser.add_argument('--force', action='store_true',
                               help='Overwrite existing status')
    create_parser.set_defaults(func=cmd_create)

    # set-phase
    set_phase_parser = subparsers.add_parser('set-phase', help='Set current phase')
    set_phase_parser.add_argument('--plan-id', required=True, help='Plan identifier')
    set_phase_parser.add_argument('--phase', required=True, help='Phase name')
    set_phase_parser.set_defaults(func=cmd_set_phase)

    # update-phase
    update_phase_parser = subparsers.add_parser('update-phase', help='Update phase status')
    update_phase_parser.add_argument('--plan-id', required=True, help='Plan identifier')
    update_phase_parser.add_argument('--phase', required=True, help='Phase name')
    update_phase_parser.add_argument('--status', required=True,
                                     choices=['pending', 'in_progress', 'done'],
                                     help='Phase status')
    update_phase_parser.set_defaults(func=cmd_update_phase)

    # progress
    progress_parser = subparsers.add_parser('progress', help='Calculate progress')
    progress_parser.add_argument('--plan-id', required=True, help='Plan identifier')
    progress_parser.set_defaults(func=cmd_progress)

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
    routing_context_parser = subparsers.add_parser('get-routing-context',
        help='Get combined routing context (phase, skill, progress)')
    routing_context_parser.add_argument('--plan-id', required=True, help='Plan identifier')
    routing_context_parser.set_defaults(func=cmd_get_routing_context)

    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()

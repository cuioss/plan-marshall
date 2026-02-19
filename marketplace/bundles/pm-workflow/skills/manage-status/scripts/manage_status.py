#!/usr/bin/env python3
"""
Manage status.json files with phase tracking and metadata.

Handles plan status storage (JSON), phase operations, and metadata management.
Storage: JSON format (.plan/plans/{plan_id}/status.json)
Output: TOON format for API responses

Usage:
    python3 manage-status.py create --plan-id my-plan --title "Title" --phases 1-init,2-refine,3-outline
    python3 manage-status.py read --plan-id my-plan
    python3 manage-status.py set-phase --plan-id my-plan --phase 2-refine
    python3 manage-status.py update-phase --plan-id my-plan --phase 1-init --status done
    python3 manage-status.py progress --plan-id my-plan
    python3 manage-status.py metadata --plan-id my-plan --set --field change_type --value feature
    python3 manage-status.py metadata --plan-id my-plan --get --field change_type
    python3 manage-status.py get-context --plan-id my-plan
"""

import argparse
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, NotRequired, TypedDict, cast

from file_ops import atomic_write_file, base_path  # type: ignore[import-not-found]
from plan_logging import log_entry  # type: ignore[import-not-found]
from toon_parser import serialize_toon  # type: ignore[import-not-found]

# =============================================================================
# TypedDict Definitions
# =============================================================================


class PhaseData(TypedDict):
    """Type definition for phase data."""

    name: str
    status: str  # pending | in_progress | done


class StatusData(TypedDict):
    """Type definition for status data structure."""

    title: str
    current_phase: str
    phases: list[PhaseData]
    metadata: NotRequired[dict[str, Any]]
    created: str
    updated: str


# =============================================================================
# Core Functions
# =============================================================================


def validate_plan_id(plan_id: str) -> bool:
    """Validate plan_id is kebab-case with no special characters."""
    return bool(re.match(r'^[a-z][a-z0-9-]*$', plan_id))


def get_status_path(plan_id: str) -> Path:
    """Get the status.json file path."""
    return cast(Path, base_path('plans', plan_id, 'status.json'))


def now_iso() -> str:
    """Get current time in ISO format."""
    return datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')


def read_status(plan_id: str) -> dict[Any, Any]:
    """Read status.json for a plan."""
    path = get_status_path(plan_id)
    if not path.exists():
        return {}
    return cast(dict[Any, Any], json.loads(path.read_text(encoding='utf-8')))


def write_status(plan_id: str, status: dict) -> None:
    """Write status.json for a plan."""
    path = get_status_path(plan_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    status['updated'] = now_iso()
    content = json.dumps(status, indent=2)
    atomic_write_file(path, content)


def output_toon(data: dict) -> None:
    """Output TOON format to stdout."""
    print(serialize_toon(data))


# =============================================================================
# Command: Create
# =============================================================================


def cmd_create(args) -> None:
    """Create status.json for a new plan."""
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

    path = get_status_path(args.plan_id)
    if path.exists() and not args.force:
        output_toon(
            {
                'status': 'error',
                'plan_id': args.plan_id,
                'error': 'file_exists',
                'message': 'status.json already exists. Use --force to overwrite.',
            }
        )
        sys.exit(1)

    # Parse phases from comma-separated argument
    phases = [p.strip() for p in args.phases.split(',') if p.strip()]
    if not phases:
        output_toon(
            {
                'status': 'error',
                'plan_id': args.plan_id,
                'error': 'invalid_phases',
                'message': 'At least one phase is required',
            }
        )
        sys.exit(1)

    now = now_iso()

    status: dict[str, Any] = {
        'title': args.title,
        'current_phase': phases[0],
        'phases': [{'name': p, 'status': 'pending'} for p in phases],
        'created': now,
        'updated': now,
    }
    # Mark first phase as in_progress
    status['phases'][0]['status'] = 'in_progress'

    write_status(args.plan_id, status)

    output_toon(
        {
            'status': 'success',
            'plan_id': args.plan_id,
            'file': 'status.json',
            'created': True,
            'plan': {'title': args.title, 'current_phase': phases[0]},
        }
    )


# =============================================================================
# Command: Read
# =============================================================================


def cmd_read(args) -> None:
    """Read plan status."""
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

    status = read_status(args.plan_id)
    if not status:
        output_toon(
            {'status': 'error', 'plan_id': args.plan_id, 'error': 'file_not_found', 'message': 'status.json not found'}
        )
        sys.exit(1)

    output_toon({'status': 'success', 'plan_id': args.plan_id, 'plan': status})


# =============================================================================
# Command: Set-Phase
# =============================================================================


def cmd_set_phase(args) -> None:
    """Set current phase."""
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

    status = read_status(args.plan_id)
    if not status:
        output_toon(
            {'status': 'error', 'plan_id': args.plan_id, 'error': 'file_not_found', 'message': 'status.json not found'}
        )
        sys.exit(1)

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
        sys.exit(1)

    previous = status.get('current_phase')
    status['current_phase'] = args.phase

    # Update phase statuses
    for phase in status['phases']:
        if phase['name'] == args.phase:
            phase['status'] = 'in_progress'

    write_status(args.plan_id, status)
    log_entry('work', args.plan_id, 'INFO', f'[MANAGE-STATUS] Phase: {previous} -> {args.phase}')

    output_toon({'status': 'success', 'plan_id': args.plan_id, 'current_phase': args.phase, 'previous_phase': previous})


# =============================================================================
# Command: Update-Phase
# =============================================================================


def cmd_update_phase(args) -> None:
    """Update a specific phase status."""
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

    status = read_status(args.plan_id)
    if not status:
        output_toon(
            {'status': 'error', 'plan_id': args.plan_id, 'error': 'file_not_found', 'message': 'status.json not found'}
        )
        sys.exit(1)

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
        sys.exit(1)

    write_status(args.plan_id, status)

    output_toon({'status': 'success', 'plan_id': args.plan_id, 'phase': args.phase, 'phase_status': args.status})


# =============================================================================
# Command: Progress
# =============================================================================


def cmd_progress(args) -> None:
    """Calculate plan progress."""
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

    status = read_status(args.plan_id)
    if not status:
        output_toon(
            {'status': 'error', 'plan_id': args.plan_id, 'error': 'file_not_found', 'message': 'status.json not found'}
        )
        sys.exit(1)

    phases = status.get('phases', [])
    total = len(phases)
    completed = sum(1 for p in phases if p.get('status') == 'done')
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


# =============================================================================
# Command: Metadata
# =============================================================================


def cmd_metadata(args) -> None:
    """Get or set a metadata field in status.json."""
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

    status = read_status(args.plan_id)
    if not status:
        output_toon(
            {'status': 'error', 'plan_id': args.plan_id, 'error': 'file_not_found', 'message': 'status.json not found'}
        )
        sys.exit(1)

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

    elif args.get:
        # Get metadata
        metadata = status.get('metadata', {})
        value = metadata.get(args.field)

        if value is None:
            output_toon(
                {
                    'status': 'error',
                    'plan_id': args.plan_id,
                    'error': 'field_not_found',
                    'message': f"Metadata field '{args.field}' not found",
                    'available_fields': list(metadata.keys()),
                }
            )
            sys.exit(1)

        output_toon(
            {
                'status': 'success',
                'plan_id': args.plan_id,
                'field': args.field,
                'value': value,
            }
        )

    else:
        output_toon(
            {
                'status': 'error',
                'plan_id': args.plan_id,
                'error': 'missing_operation',
                'message': 'Either --get or --set is required',
            }
        )
        sys.exit(1)


# =============================================================================
# Command: Get-Context
# =============================================================================


def cmd_get_context(args) -> None:
    """Get combined status context (phase, progress, metadata)."""
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

    status = read_status(args.plan_id)
    if not status:
        output_toon(
            {'status': 'error', 'plan_id': args.plan_id, 'error': 'file_not_found', 'message': 'status.json not found'}
        )
        sys.exit(1)

    phases = status.get('phases', [])
    total = len(phases)
    completed = sum(1 for p in phases if p.get('status') == 'done')

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


# =============================================================================
# Main
# =============================================================================


def main() -> None:
    parser = argparse.ArgumentParser(description='Manage status.json files with phase tracking and metadata')
    subparsers = parser.add_subparsers(dest='command', required=True)

    # create
    create_parser = subparsers.add_parser('create', help='Create status.json')
    create_parser.add_argument('--plan-id', required=True, help='Plan identifier')
    create_parser.add_argument('--title', required=True, help='Plan title')
    create_parser.add_argument(
        '--phases',
        required=True,
        help='Comma-separated phase names (e.g., 1-init,2-refine,3-outline,4-plan,5-execute,6-finalize)',
    )
    create_parser.add_argument('--force', action='store_true', help='Overwrite existing status')
    create_parser.set_defaults(func=cmd_create)

    # read
    read_parser = subparsers.add_parser('read', help='Read plan status')
    read_parser.add_argument('--plan-id', required=True, help='Plan identifier')
    read_parser.set_defaults(func=cmd_read)

    # set-phase
    set_phase_parser = subparsers.add_parser('set-phase', help='Set current phase')
    set_phase_parser.add_argument('--plan-id', required=True, help='Plan identifier')
    set_phase_parser.add_argument('--phase', required=True, help='Phase name')
    set_phase_parser.set_defaults(func=cmd_set_phase)

    # update-phase
    update_phase_parser = subparsers.add_parser('update-phase', help='Update phase status')
    update_phase_parser.add_argument('--plan-id', required=True, help='Plan identifier')
    update_phase_parser.add_argument('--phase', required=True, help='Phase name')
    update_phase_parser.add_argument(
        '--status', required=True, choices=['pending', 'in_progress', 'done'], help='Phase status'
    )
    update_phase_parser.set_defaults(func=cmd_update_phase)

    # progress
    progress_parser = subparsers.add_parser('progress', help='Calculate progress')
    progress_parser.add_argument('--plan-id', required=True, help='Plan identifier')
    progress_parser.set_defaults(func=cmd_progress)

    # metadata
    metadata_parser = subparsers.add_parser('metadata', help='Get or set metadata fields')
    metadata_parser.add_argument('--plan-id', required=True, help='Plan identifier')
    metadata_parser.add_argument('--get', action='store_true', help='Get metadata field')
    metadata_parser.add_argument('--set', action='store_true', help='Set metadata field')
    metadata_parser.add_argument('--field', required=True, help='Metadata field name')
    metadata_parser.add_argument('--value', help='Metadata field value (required for --set)')
    metadata_parser.set_defaults(func=cmd_metadata)

    # get-context
    get_context_parser = subparsers.add_parser('get-context', help='Get combined status context')
    get_context_parser.add_argument('--plan-id', required=True, help='Plan identifier')
    get_context_parser.set_defaults(func=cmd_get_context)

    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()

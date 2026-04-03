#!/usr/bin/env python3
"""
Manage status.json files with phase tracking, metadata, and lifecycle operations.

Handles plan status storage (JSON), phase operations, metadata management,
plan discovery, phase transitions, archiving, and routing.
Storage: JSON format (.plan/plans/{plan_id}/status.json)
Output: TOON format for API responses

Usage:
    python3 manage_status.py create --plan-id my-plan --title "Title" --phases 1-init,2-refine,3-outline
    python3 manage_status.py read --plan-id my-plan
    python3 manage_status.py set-phase --plan-id my-plan --phase 2-refine
    python3 manage_status.py update-phase --plan-id my-plan --phase 1-init --status done
    python3 manage_status.py progress --plan-id my-plan
    python3 manage_status.py metadata --plan-id my-plan --set --field change_type --value feature
    python3 manage_status.py metadata --plan-id my-plan --get --field change_type
    python3 manage_status.py get-context --plan-id my-plan
    python3 manage_status.py list
    python3 manage_status.py transition --plan-id my-plan --completed 1-init
    python3 manage_status.py archive --plan-id my-plan
    python3 manage_status.py route --phase 1-init
    python3 manage_status.py get-routing-context --plan-id my-plan
"""

import argparse
import json
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, NotRequired, TypedDict, cast

from constants import PHASES  # type: ignore[import-not-found]
from file_ops import atomic_write_file, base_path, now_utc_iso, output_toon, safe_main  # type: ignore[import-not-found]
from input_validation import require_valid_plan_id  # type: ignore[import-not-found]
from plan_logging import log_entry  # type: ignore[import-not-found]

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


def get_status_path(plan_id: str) -> Path:
    """Get the status.json file path."""
    return cast(Path, base_path('plans', plan_id, 'status.json'))


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
    status['updated'] = now_utc_iso()
    content = json.dumps(status, indent=2)
    atomic_write_file(path, content)


# Phase routing maps phase names to skills (for route command)
PHASE_ROUTING = {
    '1-init': ('plan-init', 'Initialize plan structure'),
    '2-refine': ('request-refine', 'Clarify request until confident'),
    '3-outline': ('solution-outline', 'Create solution outline with deliverables'),
    '4-plan': ('task-plan', 'Create tasks from deliverables'),
    '5-execute': ('plan-execute', 'Execute implementation tasks'),
    '6-finalize': ('plan-finalize', 'Finalize with commit/PR'),
}


def get_plans_dir() -> Path:
    """Get the plans directory."""
    return cast(Path, base_path('plans'))


def get_archive_dir() -> Path:
    """Get the archived plans directory."""
    return cast(Path, base_path('archived-plans'))


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
# Command: Create
# =============================================================================


def cmd_create(args: argparse.Namespace) -> None:
    """Create status.json for a new plan."""
    require_valid_plan_id(args)

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

    now = now_utc_iso()

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


def cmd_read(args: argparse.Namespace) -> None:
    """Read plan status."""
    require_valid_plan_id(args)

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


def cmd_set_phase(args: argparse.Namespace) -> None:
    """Set current phase."""
    require_valid_plan_id(args)

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


def cmd_update_phase(args: argparse.Namespace) -> None:
    """Update a specific phase status."""
    require_valid_plan_id(args)

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


def cmd_progress(args: argparse.Namespace) -> None:
    """Calculate plan progress."""
    require_valid_plan_id(args)

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


def cmd_metadata(args: argparse.Namespace) -> None:
    """Get or set a metadata field in status.json."""
    require_valid_plan_id(args)

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
                    'status': 'not_found',
                    'plan_id': args.plan_id,
                    'field': args.field,
                    'message': f"Metadata field '{args.field}' not found",
                    'available_fields': list(metadata.keys()),
                }
            )
            return

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


def cmd_get_context(args: argparse.Namespace) -> None:
    """Get combined status context (phase, progress, metadata)."""
    require_valid_plan_id(args)

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
# Command: List
# =============================================================================


def cmd_list(args: argparse.Namespace) -> None:
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


def cmd_transition(args: argparse.Namespace) -> None:
    """Transition to next phase."""
    require_valid_plan_id(args)

    status = read_status(args.plan_id)
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

    write_status(args.plan_id, status)

    result: dict[str, Any] = {'status': 'success', 'plan_id': args.plan_id, 'completed_phase': args.completed}
    if next_phase:
        result['next_phase'] = next_phase
    else:
        result['message'] = 'All phases completed'

    output_toon(result)


# =============================================================================
# Command: Archive
# =============================================================================


def cmd_archive(args: argparse.Namespace) -> None:
    """Archive a completed plan."""
    require_valid_plan_id(args)

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


def cmd_route(args: argparse.Namespace) -> None:
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


def cmd_get_routing_context(args: argparse.Namespace) -> None:
    """Get combined routing context: phase, skill, and progress in one call."""
    require_valid_plan_id(args)

    status = read_status(args.plan_id)
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
# Command: Delete Plan
# =============================================================================


def cmd_delete_plan(args: argparse.Namespace) -> None:
    """Delete an entire plan directory.

    Returns TOON output indicating the deletion result.
    Used by plan-init when user selects 'Replace' for an existing plan.

    See: standards/plan-overwrite.md for the full workflow.
    """
    require_valid_plan_id(args)

    plan_dir = cast(Path, base_path('plans', args.plan_id))

    if not plan_dir.exists():
        output_toon({
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'plan_not_found',
            'message': f'Plan directory does not exist: {plan_dir}',
        })
        sys.exit(1)

    # Count files before deletion for audit trail
    files_removed = sum(1 for _ in plan_dir.rglob('*') if _.is_file())

    try:
        shutil.rmtree(plan_dir)
        log_entry('work', args.plan_id, 'INFO', f'[MANAGE-STATUS] Deleted plan ({files_removed} files)')
        output_toon({
            'status': 'success',
            'plan_id': args.plan_id,
            'action': 'deleted',
            'path': str(plan_dir),
            'files_removed': files_removed,
        })
    except PermissionError as e:
        output_toon({
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'permission_denied',
            'message': f'Permission denied: {e}',
        })
        sys.exit(1)
    except Exception as e:
        output_toon({
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'delete_failed',
            'message': f'Failed to delete plan directory: {e}',
        })
        sys.exit(1)


# =============================================================================
# Command: Self-Test
# =============================================================================


def cmd_self_test(_args) -> None:
    """Verify manage-status health: imports, routing, and directory access."""
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

    output_toon(result)
    if failed > 0:
        sys.exit(1)


# =============================================================================
# Main
# =============================================================================


@safe_main
def main() -> int:
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

    # delete-plan
    delete_plan_parser = subparsers.add_parser('delete-plan', help='Delete entire plan directory')
    delete_plan_parser.add_argument('--plan-id', required=True, help='Plan identifier')
    delete_plan_parser.set_defaults(func=cmd_delete_plan)

    # self-test
    self_test_parser = subparsers.add_parser('self-test', help='Verify manage-status health')
    self_test_parser.set_defaults(func=cmd_self_test)

    args = parser.parse_args()
    args.func(args)
    return 0


if __name__ == '__main__':
    main()

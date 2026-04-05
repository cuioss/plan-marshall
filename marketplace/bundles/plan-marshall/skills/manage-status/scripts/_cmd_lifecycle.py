#!/usr/bin/env python3
"""
Lifecycle command handlers for manage-status: create, transition, archive, delete-plan.
"""

import argparse
import shutil
from typing import Any

from _status_core import (
    get_archive_dir,
    get_status_path,
    log_entry,
    now_utc_iso,
    require_status,
    require_valid_plan_id,
    write_status,
)
from constants import (  # type: ignore[import-not-found]
    PHASE_STATUS_DONE,
    PHASE_STATUS_IN_PROGRESS,
    PHASE_STATUS_PENDING,
)
from file_ops import get_plan_dir  # type: ignore[import-not-found]


def cmd_create(args: argparse.Namespace) -> dict:
    """Create status.json for a new plan."""
    require_valid_plan_id(args)

    path = get_status_path(args.plan_id)
    if path.exists() and not args.force:
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'file_exists',
            'message': 'status.json already exists. Use --force to overwrite.',
        }

    # Parse phases from comma-separated argument
    phases = [p.strip() for p in args.phases.split(',') if p.strip()]
    if not phases:
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'invalid_phases',
            'message': 'At least one phase is required',
        }

    now = now_utc_iso()

    status: dict[str, Any] = {
        'title': args.title,
        'current_phase': phases[0],
        'phases': [{'name': p, 'status': PHASE_STATUS_PENDING} for p in phases],
        'created': now,
        'updated': now,
    }
    # Mark first phase as in_progress
    status['phases'][0]['status'] = PHASE_STATUS_IN_PROGRESS

    write_status(args.plan_id, status)

    return {
        'status': 'success',
        'plan_id': args.plan_id,
        'file': 'status.json',
        'created': True,
        'plan': {'title': args.title, 'current_phase': phases[0]},
    }


def cmd_transition(args: argparse.Namespace) -> dict:
    """Transition to next phase."""
    status = require_status(args)

    phases = status.get('phases', [])
    phase_names = [p['name'] for p in phases]

    if args.completed not in phase_names:
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'invalid_phase',
            'message': f'Invalid phase: {args.completed}',
        }

    completed_idx = phase_names.index(args.completed)

    # Mark completed phase as done
    phases[completed_idx]['status'] = PHASE_STATUS_DONE

    # Determine next phase
    if completed_idx + 1 < len(phases):
        next_phase = phase_names[completed_idx + 1]
        phases[completed_idx + 1]['status'] = PHASE_STATUS_IN_PROGRESS
        status['current_phase'] = next_phase
    else:
        next_phase = None

    write_status(args.plan_id, status)

    result: dict[str, Any] = {'status': 'success', 'plan_id': args.plan_id, 'completed_phase': args.completed}
    if next_phase:
        result['next_phase'] = next_phase
    else:
        result['message'] = 'All phases completed'

    return result


def cmd_archive(args: argparse.Namespace) -> dict:
    """Archive a completed plan."""
    require_valid_plan_id(args)

    plan_dir = get_plan_dir(args.plan_id)
    if not plan_dir.exists():
        return {'status': 'error', 'plan_id': args.plan_id, 'error': 'not_found', 'message': 'Plan directory not found'}

    date_prefix = now_utc_iso()[:10]  # YYYY-MM-DD
    archive_name = f'{date_prefix}-{args.plan_id}'
    archive_dir = get_archive_dir()
    archive_path = archive_dir / archive_name

    if args.dry_run:
        return {'status': 'success', 'plan_id': args.plan_id, 'dry_run': True, 'would_archive_to': str(archive_path)}

    archive_dir.mkdir(parents=True, exist_ok=True)
    shutil.move(str(plan_dir), str(archive_path))

    return {'status': 'success', 'plan_id': args.plan_id, 'archived_to': str(archive_path)}


def cmd_delete_plan(args: argparse.Namespace) -> dict:
    """Delete an entire plan directory."""
    require_valid_plan_id(args)

    plan_dir = get_plan_dir(args.plan_id)

    if not plan_dir.exists():
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'plan_not_found',
            'message': f'Plan directory does not exist: {plan_dir}',
        }

    # Count files before deletion for audit trail
    files_removed = sum(1 for _ in plan_dir.rglob('*') if _.is_file())

    try:
        shutil.rmtree(plan_dir)
        log_entry('work', args.plan_id, 'INFO', f'[MANAGE-STATUS] Deleted plan ({files_removed} files)')
        return {
            'status': 'success',
            'plan_id': args.plan_id,
            'action': 'deleted',
            'path': str(plan_dir),
            'files_removed': files_removed,
        }
    except PermissionError as e:
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'permission_denied',
            'message': f'Permission denied: {e}',
        }
    except Exception as e:
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'delete_failed',
            'message': f'Failed to delete plan directory: {e}',
        }

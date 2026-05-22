#!/usr/bin/env python3
"""
Query command handlers for manage-status: read, progress, metadata, get-context, list.
"""

import argparse
from typing import Any

from _status_core import (
    TITLE_BODY_FILENAME,
    TITLE_BODY_TERMINAL_PHASES,
    _publish_title_body,
    _try_read_status_json,
    get_plans_dir,
    log_entry,
    require_status,
    write_status,
)
from constants import PHASE_STATUS_DONE, PHASE_STATUS_IN_PROGRESS  # type: ignore[import-not-found]
from file_ops import get_plan_dir  # type: ignore[import-not-found]

# Metadata fields that are semantically boolean. The ``metadata --set`` CLI
# receives every value as a raw string; for these keys the raw string is
# coerced to a JSON boolean before storage so downstream consumers
# (e.g. phase_handshake worktree drift checks) see ``true``/``false`` rather
# than the string ``"true"``/``"false"``. Non-allowlisted fields keep
# verbatim string storage.
BOOLEAN_METADATA_FIELDS = frozenset({'use_worktree'})


def _coerce_metadata_value(field: str, raw_value: str) -> Any:
    """Coerce a raw ``--set`` value string for typed metadata fields.

    Boolean-typed fields (see ``BOOLEAN_METADATA_FIELDS``) map the
    case-insensitive strings ``"true"``/``"false"`` to JSON booleans. Any
    other value for a boolean field, and every value for a non-boolean
    field, is returned verbatim as a string.
    """
    if field in BOOLEAN_METADATA_FIELDS:
        lowered = raw_value.strip().lower()
        if lowered == 'true':
            return True
        if lowered == 'false':
            return False
    return raw_value


def cmd_read(args: argparse.Namespace) -> dict | None:
    """Read plan status.

    Cold-bootstrap branch: when ``title-body.txt`` is absent for an active
    (non-terminal) plan, the read handler republishes it from the in-memory
    status dict. This covers fresh tabs / processes that opened after the
    writer's last successful publish — the next read self-heals the
    artifact without requiring a state mutation.
    """
    status = require_status(args)
    if status is None:
        return None

    current_phase = status.get('current_phase')
    if current_phase and current_phase not in TITLE_BODY_TERMINAL_PHASES:
        plan_dir = get_plan_dir(args.plan_id)
        title_body_path = plan_dir / TITLE_BODY_FILENAME
        if not title_body_path.is_file():
            _publish_title_body(plan_dir, status)

    return {'status': 'success', 'plan_id': args.plan_id, 'plan': status}


def cmd_set_phase(args: argparse.Namespace) -> dict | None:
    """Set current phase."""
    status = require_status(args)
    if status is None:
        return None

    phase_names = [p['name'] for p in status.get('phases', [])]
    if args.phase not in phase_names:
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'invalid_phase',
            'message': f'Invalid phase: {args.phase}',
            'valid_phases': phase_names,
        }

    previous = status.get('current_phase')
    status['current_phase'] = args.phase

    # Update phase statuses
    for phase in status['phases']:
        if phase['name'] == args.phase:
            phase['status'] = PHASE_STATUS_IN_PROGRESS

    write_status(args.plan_id, status)
    # Title-body publication hook — set-phase is a phase mutator and must
    # republish the writer-side title-body artifact so per-target session
    # renderers see the new phase without re-reading status.json.
    _publish_title_body(get_plan_dir(args.plan_id), status)
    log_entry('work', args.plan_id, 'INFO', f'[MANAGE-STATUS] Phase: {previous} -> {args.phase}')

    return {'status': 'success', 'plan_id': args.plan_id, 'current_phase': args.phase, 'previous_phase': previous}


def cmd_update_phase(args: argparse.Namespace) -> dict | None:
    """Update a specific phase status."""
    status = require_status(args)
    if status is None:
        return None

    found = False
    for phase in status.get('phases', []):
        if phase['name'] == args.phase:
            phase['status'] = args.status
            found = True
            break

    if not found:
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'phase_not_found',
            'message': f"Phase '{args.phase}' not found",
        }

    write_status(args.plan_id, status)

    return {'status': 'success', 'plan_id': args.plan_id, 'phase': args.phase, 'phase_status': args.status}


def cmd_progress(args: argparse.Namespace) -> dict | None:
    """Calculate plan progress."""
    status = require_status(args)
    if status is None:
        return None

    phases = status.get('phases', [])
    total = len(phases)
    completed = sum(1 for p in phases if p.get('status') == PHASE_STATUS_DONE)
    percent = int((completed / total) * 100) if total > 0 else 0

    return {
        'status': 'success',
        'plan_id': args.plan_id,
        'progress': {
            'total_phases': total,
            'completed_phases': completed,
            'current_phase': status.get('current_phase'),
            'percent': percent,
        },
    }


def cmd_metadata(args: argparse.Namespace) -> dict | None:
    """Get or set a metadata field in status.json."""
    status = require_status(args)
    if status is None:
        return None

    if args.set:
        # Set metadata
        if 'metadata' not in status:
            status['metadata'] = {}

        previous_value = status['metadata'].get(args.field)
        coerced_value = _coerce_metadata_value(args.field, args.value)
        status['metadata'][args.field] = coerced_value

        write_status(args.plan_id, status)
        log_entry('work', args.plan_id, 'INFO', f'[MANAGE-STATUS] Metadata: {args.field}={coerced_value}')

        result: dict[str, Any] = {
            'status': 'success',
            'plan_id': args.plan_id,
            'field': args.field,
            'value': coerced_value,
        }
        if previous_value is not None:
            result['previous_value'] = previous_value
        return result

    elif args.get:
        # Get metadata
        metadata = status.get('metadata', {})
        value = metadata.get(args.field)

        if value is None:
            return {
                'status': 'not_found',
                'plan_id': args.plan_id,
                'field': args.field,
                'message': f"Metadata field '{args.field}' not found",
                'available_fields': list(metadata.keys()),
            }

        return {
            'status': 'success',
            'plan_id': args.plan_id,
            'field': args.field,
            'value': value,
        }

    else:
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'missing_operation',
            'message': 'Either --get or --set is required',
        }


def cmd_get_context(args: argparse.Namespace) -> dict | None:
    """Get combined status context (phase, progress, metadata)."""
    status = require_status(args)
    if status is None:
        return None

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

    return context


def cmd_get_worktree_path(args: argparse.Namespace) -> dict | None:
    """Return the persisted worktree path for a plan as a tri-state response.

    Reads ``status.metadata.use_worktree`` and ``status.metadata.worktree_path``
    and returns the path so that callers (build wrappers, git_workflow,
    phase-entry assertions) can resolve the active worktree from a
    plan-id alone — no ``--project-dir``, no filesystem layout
    re-derivation.

    Output contract (tri-state, discriminated by ``worktree_state``):

    - ``use_worktree == false`` (or metadata absent) →
      ``worktree_state: disabled``, ``worktree_path: ''``. The plan runs
      against the main checkout.
    - ``use_worktree == true`` and ``worktree_path`` is empty/missing →
      ``worktree_state: pending``, ``worktree_path: ''``,
      ``not_yet_materialized: true``. The plan opted into a worktree but
      it has not been materialized yet (pre-materialization). Callers
      MUST fall back to the main checkout cwd.
    - ``use_worktree == true`` and ``worktree_path`` is set →
      ``worktree_state: materialized``, ``worktree_path: <abs>``. The
      worktree is materialized and the path is authoritative.
    """
    status = require_status(args)
    if status is None:
        return None

    metadata = status.get('metadata') or {}
    use_worktree = bool(metadata.get('use_worktree', False))

    if not use_worktree:
        return {
            'status': 'success',
            'plan_id': args.plan_id,
            'use_worktree': False,
            'worktree_state': 'disabled',
            'worktree_path': '',
        }

    worktree_path = metadata.get('worktree_path')
    if not worktree_path:
        pending: dict[str, Any] = {
            'status': 'success',
            'plan_id': args.plan_id,
            'use_worktree': True,
            'worktree_state': 'pending',
            'worktree_path': '',
            'not_yet_materialized': True,
        }
        worktree_branch = metadata.get('worktree_branch')
        if worktree_branch:
            pending['worktree_branch'] = worktree_branch
        return pending

    result: dict[str, Any] = {
        'status': 'success',
        'plan_id': args.plan_id,
        'use_worktree': True,
        'worktree_state': 'materialized',
        'worktree_path': worktree_path,
    }
    worktree_branch = metadata.get('worktree_branch')
    if worktree_branch:
        result['worktree_branch'] = worktree_branch
    return result


def cmd_list(args: argparse.Namespace) -> dict:
    """Discover all plans."""
    plans_dir = get_plans_dir()
    if not plans_dir.exists():
        return {'status': 'success', 'total': 0, 'plans': []}

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

    return {'status': 'success', 'total': len(plans), 'plans': plans}


def cmd_list_orphans(args: argparse.Namespace) -> dict:  # noqa: ARG001
    """Discover orphan plan directories (directories without a readable status.json).

    Inverse of ``cmd_list``: walks ``plans_dir.iterdir()`` and collects directory
    entries that do NOT have a readable ``status.json`` file. Plans with a
    readable status.json are skipped. The ``archived-plans`` directory (if
    present as a sibling) is excluded — orphan scanning operates only on the
    active plans directory returned by ``get_plans_dir()``.

    Output contract:
        status: success
        total: N
        orphans: [{id, path, contents}]

    Each orphan entry includes:
        - ``id``: directory name
        - ``path``: absolute filesystem path
        - ``contents``: sorted list of top-level entry names inside the orphan
          directory (files and subdirectories). Empty list when the directory
          has no entries.
    """
    plans_dir = get_plans_dir()
    # Use is_dir() rather than exists() so a stray file at the plans_dir path
    # returns total=0 cleanly instead of raising NotADirectoryError from iterdir().
    if not plans_dir.is_dir():
        return {'status': 'success', 'total': 0, 'orphans': []}

    orphans = []
    for plan_dir in sorted(plans_dir.iterdir()):
        if not plan_dir.is_dir():
            continue

        # Skip plans whose status.json FILE is present — matches the
        # require_plan_exists guard in tools-file-ops/file_ops.py. An empty
        # ``{}`` status.json is a valid plan file and must NOT be flagged as
        # orphan; only directories with no status.json file at all are orphans.
        if (plan_dir / 'status.json').is_file():
            continue

        # Collect top-level contents for caller-side decision making. On
        # OSError (e.g., permission denied) emit a single '<unreadable>'
        # sentinel rather than an empty list — an empty list would trigger
        # silent deletion under planning.md Step 3b. The sentinel forces a
        # user prompt instead.
        try:
            contents = sorted(entry.name for entry in plan_dir.iterdir())
        except OSError:
            contents = ['<unreadable>']

        orphans.append({'id': plan_dir.name, 'path': str(plan_dir), 'contents': contents})

    return {'status': 'success', 'total': len(orphans), 'orphans': orphans}

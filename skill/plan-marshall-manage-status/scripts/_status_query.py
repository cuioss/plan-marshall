#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""
Query command handlers for manage-status: read, progress, metadata, get-context, list.
"""

import argparse
from typing import Any

from _status_core import (
    TITLE_TOKEN_STATES,
    _try_read_status_json,
    get_plans_dir,
    log_entry,
    require_status,
    write_status,
)
from constants import (  # type: ignore[import-not-found]
    DIR_PLANS,
    PHASE_STATUS_DONE,
    PHASE_STATUS_IN_PROGRESS,
)
from file_ops import get_worktree_root  # type: ignore[import-not-found]
from marketplace_paths import PLAN_DIR_NAME  # type: ignore[import-not-found]

# Metadata fields that are semantically boolean. The ``metadata --set`` CLI
# receives every value as a raw string; for these keys the raw string is
# coerced to a JSON boolean before storage so downstream consumers
# (e.g. phase_handshake worktree drift checks) see ``true``/``false`` rather
# than the string ``"true"``/``"false"``. Non-allowlisted fields keep
# verbatim string storage.
BOOLEAN_METADATA_FIELDS = frozenset({'use_worktree'})


def _coerce_metadata_value(field: str, raw_value: Any) -> Any:
    """Coerce a raw ``--set`` value string for typed metadata fields.

    Boolean-typed fields (see ``BOOLEAN_METADATA_FIELDS``) map the
    case-insensitive strings ``"true"``/``"false"`` to JSON booleans. Any
    other value for a boolean field, and every value for a non-boolean
    field, is returned verbatim.
    """
    if field in BOOLEAN_METADATA_FIELDS and isinstance(raw_value, str):
        lowered = raw_value.strip().lower()
        if lowered == 'true':
            return True
        if lowered == 'false':
            return False
    return raw_value


def cmd_read(args: argparse.Namespace) -> dict[str, Any] | None:
    """Read plan status."""
    status = require_status(args)
    if status is None:
        return None

    return {'status': 'success', 'plan_id': args.plan_id, 'plan': status}


def cmd_set_phase(args: argparse.Namespace) -> dict[str, Any] | None:
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
    log_entry('work', args.plan_id, 'INFO', f'[MANAGE-STATUS] Phase: {previous} -> {args.phase}')

    return {'status': 'success', 'plan_id': args.plan_id, 'current_phase': args.phase, 'previous_phase': previous}


def cmd_update_phase(args: argparse.Namespace) -> dict[str, Any] | None:
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


def cmd_progress(args: argparse.Namespace) -> dict[str, Any] | None:
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


def cmd_metadata(args: argparse.Namespace) -> dict[str, Any] | None:
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


def cmd_title_token(args: argparse.Namespace) -> dict[str, Any] | None:
    """Set or clear the field-only ``title_token`` marker in status.json.

    The title token is a bare state string (one of ``TITLE_TOKEN_STATES``)
    written into ``status.title_token``. manage-status performs NO rendering
    — the composition (glyph vocabulary + ``{icon} {body}`` assembly) lives in
    ``manage-terminal-title``. This verb only persists the state so the
    per-target renderer can read it.

    - ``set`` writes ``status.title_token = {state}`` (``--state`` required,
      validated against ``TITLE_TOKEN_STATES``).
    - ``clear`` removes the ``title_token`` field when present (idempotent —
      a no-op when already absent).
    """
    status = require_status(args)
    if status is None:
        return None

    if args.token_verb == 'set':
        state = args.state
        if state not in TITLE_TOKEN_STATES:
            return {
                'status': 'error',
                'plan_id': args.plan_id,
                'error': 'invalid_title_token_state',
                'message': f'Invalid title-token state: {state}',
                'valid_states': sorted(TITLE_TOKEN_STATES),
            }
        status['title_token'] = state
        write_status(args.plan_id, status)
        log_entry('work', args.plan_id, 'INFO', f'[MANAGE-STATUS] Title token: {state}')
        return {
            'status': 'success',
            'plan_id': args.plan_id,
            'title_token': state,
        }

    # clear
    previous = status.pop('title_token', None)
    if previous is not None:
        write_status(args.plan_id, status)
        log_entry('work', args.plan_id, 'INFO', f'[MANAGE-STATUS] Title token cleared (was: {previous})')
    return {
        'status': 'success',
        'plan_id': args.plan_id,
        'title_token': None,
        'cleared': previous is not None,
    }


def cmd_get_context(args: argparse.Namespace) -> dict[str, Any] | None:
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


def cmd_get_worktree_path(args: argparse.Namespace) -> dict[str, Any] | None:
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


def _passes_phase_filter(current_phase: str, filter_arg: str | None) -> bool:
    """Return whether ``current_phase`` survives the ``--filter`` phase filter.

    ``filter_arg`` is the raw comma-separated ``args.filter`` value (or
    ``None`` when no filter was supplied, in which case every plan passes).
    Shared by the main-checkout enumeration and the worktree scan so both
    paths honour the same filter semantics.
    """
    if not filter_arg:
        return True
    filter_phases = [p.strip() for p in filter_arg.split(',')]
    return current_phase in filter_phases


def cmd_list(args: argparse.Namespace) -> dict[str, Any]:
    """Discover all plans across the main checkout AND its worktrees.

    Enumerates two sources and merges them deduped by plan id:

    - **Main checkout** (``get_plans_dir()``): plans whose directory lives on
      the current checkout. Each is tagged ``location: 'current'``.
    - **Worktrees** (``get_worktree_root()`` children): a phase-5+ plan whose
      directory was MOVED into its worktree at execute entry (ADR-002) is no
      longer present under ``get_plans_dir()``, so a plain main-only walk is
      blind to it. The worktree scan probes each worktree's
      ``{wt}/.plan/local/plans`` for plan dirs with a readable ``status.json``
      and surfaces them tagged ``location: 'worktree'``. The probed layout is
      the exact ``get_worktree_root() / {id} / .plan/local/plans/{id}`` path
      that ``worktree-create`` materializes and ``cmd_locate_plan_checkout``
      probes — single-sourced via ``PLAN_DIR_NAME`` / ``DIR_PLANS``.

    Each entry carries ``{id, current_phase, status, location}``. The merged
    list is deduped by id (a moved-in plan appears exactly once — main never
    holds it post-move; dedup is defensive against the transient both-present
    window) and sorted by id for stable ordering regardless of checkout. The
    worktree scan is guarded against the outside-git-repo ``RuntimeError`` from
    ``get_worktree_root()`` — on that error the main-only result is returned.
    """
    plans: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    # Source 1: main-checkout plans. Tolerate a missing plans dir so a fresh
    # main checkout with no plans/ dir but an active worktree still reaches the
    # worktree scan below.
    plans_dir = get_plans_dir()
    if plans_dir.is_dir():
        for plan_dir in sorted(plans_dir.iterdir()):
            if not plan_dir.is_dir():
                continue

            status = _try_read_status_json(plan_dir)
            if not isinstance(status, dict) or not status:
                continue

            try:
                current_phase = status.get('current_phase', 'unknown')
                if not _passes_phase_filter(current_phase, args.filter):
                    continue
                plans.append(
                    {
                        'id': plan_dir.name,
                        'current_phase': current_phase,
                        'status': PHASE_STATUS_IN_PROGRESS,
                        'location': 'current',
                    }
                )
                seen_ids.add(plan_dir.name)
            except (KeyError, TypeError):
                # Skip plans with corrupted status
                continue

    # Source 2: worktree-resident plans. Outside a git repo get_worktree_root()
    # raises RuntimeError — skip the scan entirely and return the main-only
    # result rather than crashing.
    try:
        worktree_root = get_worktree_root()
    except RuntimeError:
        worktree_root = None

    if worktree_root is not None and worktree_root.is_dir():
        for worktree_dir in sorted(worktree_root.iterdir()):
            if not worktree_dir.is_dir():
                continue

            wt_plans_dir = worktree_dir / PLAN_DIR_NAME / 'local' / DIR_PLANS
            if not wt_plans_dir.is_dir():
                continue

            try:
                plan_dirs = sorted(wt_plans_dir.iterdir())
            except OSError:
                continue

            for plan_dir in plan_dirs:
                if not plan_dir.is_dir() or plan_dir.name in seen_ids:
                    continue

                status = _try_read_status_json(plan_dir)
                if not isinstance(status, dict) or not status:
                    continue

                try:
                    current_phase = status.get('current_phase', 'unknown')
                    if not _passes_phase_filter(current_phase, args.filter):
                        continue
                    plans.append(
                        {
                            'id': plan_dir.name,
                            'current_phase': current_phase,
                            'status': PHASE_STATUS_IN_PROGRESS,
                            'location': 'worktree',
                        }
                    )
                    seen_ids.add(plan_dir.name)
                except (KeyError, TypeError):
                    continue

    plans.sort(key=lambda p: p['id'])

    return {'status': 'success', 'total': len(plans), 'plans': plans}


def cmd_list_orphans(args: argparse.Namespace) -> dict[str, Any]:  # noqa: ARG001
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

    orphans: list[dict[str, Any]] = []
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

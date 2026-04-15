#!/usr/bin/env python3
"""
mark-step-done command handler for manage-status.

Persists phase step completion state into status.metadata.phase_steps so that
phase skills can record which intra-phase steps have finished. Outcomes are
``done`` or ``skipped``. The operation is idempotent on identical outcome and
returns a ``conflict`` error when a step already has a different outcome unless
``--force`` is supplied.
"""

import argparse
from typing import Any

from _status_core import require_status, write_status

VALID_OUTCOMES = ('done', 'skipped')


def cmd_mark_step_done(args: argparse.Namespace) -> dict | None:
    """Mark a phase step with an outcome inside status.metadata.phase_steps."""
    status = require_status(args)
    if status is None:
        return None

    outcome = args.outcome
    if outcome not in VALID_OUTCOMES:
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'invalid_outcome',
            'message': f'Outcome must be one of {list(VALID_OUTCOMES)}, got: {outcome}',
        }

    phase = args.phase
    step = args.step
    if not phase or not step:
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'invalid_argument',
            'message': '--phase and --step are required and must be non-empty',
        }

    metadata: dict[str, Any] = status.setdefault('metadata', {})
    phase_steps: dict[str, Any] = metadata.setdefault('phase_steps', {})
    phase_entry: dict[str, Any] = phase_steps.setdefault(phase, {})

    existing = phase_entry.get(step)

    if existing == outcome:
        # Idempotent: nothing to persist.
        return {
            'status': 'success',
            'plan_id': args.plan_id,
            'phase': phase,
            'step': step,
            'outcome': outcome,
            'changed': False,
        }

    if existing is not None and existing != outcome and not args.force:
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'conflict',
            'phase': phase,
            'step': step,
            'existing_outcome': existing,
            'requested_outcome': outcome,
            'message': (
                f'Step {step!r} in phase {phase!r} already marked as '
                f'{existing!r}; use --force to overwrite with {outcome!r}'
            ),
        }

    phase_entry[step] = outcome
    write_status(args.plan_id, status)

    return {
        'status': 'success',
        'plan_id': args.plan_id,
        'phase': phase,
        'step': step,
        'outcome': outcome,
        'changed': True,
        'previous_outcome': existing,
    }

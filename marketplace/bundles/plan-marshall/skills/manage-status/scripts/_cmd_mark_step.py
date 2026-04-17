#!/usr/bin/env python3
"""
mark-step-done command handler for manage-status.

Persists phase step completion state into status.metadata.phase_steps so that
phase skills can record which intra-phase steps have finished. Outcomes are
``done`` or ``skipped``. The operation is idempotent when both outcome and
display_detail match and returns a ``conflict`` error when a step already has a
different outcome unless ``--force`` is supplied. An optional
``--display-detail`` one-line string is persisted alongside the outcome so
downstream renderers (e.g., phase-6-finalize vertical-steps block) can surface
user-facing step summaries.
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

    display_detail = getattr(args, 'display_detail', None)

    metadata: dict[str, Any] = status.setdefault('metadata', {})
    phase_steps: dict[str, Any] = metadata.setdefault('phase_steps', {})
    phase_entry: dict[str, Any] = phase_steps.setdefault(phase, {})

    existing = phase_entry.get(step)

    if isinstance(existing, str):
        # Breaking migration: old bare-string shape is drift — caller must
        # resolve manually (re-run the phase step or patch status.json).
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'legacy_string_entry',
            'phase': phase,
            'step': step,
            'existing_outcome': existing,
            'requested_outcome': outcome,
            'message': (
                f'Step {step!r} in phase {phase!r} has legacy bare-string storage '
                f'({existing!r}); migrate status.metadata.phase_steps to the dict '
                'shape {"outcome": ..., "display_detail": ...} before retrying.'
            ),
        }

    if isinstance(existing, dict):
        existing_outcome = existing.get('outcome')
        existing_detail = existing.get('display_detail')
        if existing_outcome == outcome and existing_detail == display_detail:
            return {
                'status': 'success',
                'plan_id': args.plan_id,
                'phase': phase,
                'step': step,
                'outcome': outcome,
                'display_detail': display_detail,
                'changed': False,
            }
        if existing_outcome == outcome and existing_detail != display_detail:
            phase_entry[step] = {'outcome': outcome, 'display_detail': display_detail}
            write_status(args.plan_id, status)
            return {
                'status': 'success',
                'plan_id': args.plan_id,
                'phase': phase,
                'step': step,
                'outcome': outcome,
                'display_detail': display_detail,
                'changed': True,
                'previous_outcome': existing_outcome,
                'previous_display_detail': existing_detail,
            }
        if existing_outcome != outcome and not args.force:
            return {
                'status': 'error',
                'plan_id': args.plan_id,
                'error': 'conflict',
                'phase': phase,
                'step': step,
                'existing_outcome': existing_outcome,
                'requested_outcome': outcome,
                'message': (
                    f'Step {step!r} in phase {phase!r} already marked as '
                    f'{existing_outcome!r}; use --force to overwrite with {outcome!r}'
                ),
            }

    previous_outcome = None
    previous_detail = None
    if isinstance(existing, dict):
        previous_outcome = existing.get('outcome')
        previous_detail = existing.get('display_detail')

    phase_entry[step] = {'outcome': outcome, 'display_detail': display_detail}
    write_status(args.plan_id, status)

    return {
        'status': 'success',
        'plan_id': args.plan_id,
        'phase': phase,
        'step': step,
        'outcome': outcome,
        'display_detail': display_detail,
        'changed': True,
        'previous_outcome': previous_outcome,
        'previous_display_detail': previous_detail,
    }

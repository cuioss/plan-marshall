#!/usr/bin/env python3
"""
mark-step-done command handler for manage-status.

Persists phase step completion state into status.metadata.phase_steps so that
phase skills can record which intra-phase steps have finished. Outcomes are
``done`` or ``skipped``. The operation is idempotent when outcome,
display_detail, and head_at_completion all match and returns a ``conflict``
error when a step already has a different outcome unless ``--force`` is
supplied. An optional ``--display-detail`` one-line string is persisted
alongside the outcome so downstream renderers (e.g., phase-6-finalize
vertical-steps block) can surface user-facing step summaries. An optional
``--head-at-completion`` SHA is persisted alongside the outcome so resumable
phase dispatchers (e.g., phase-6-finalize Step 3 for ``pre-push-quality-gate``)
can detect when the worktree HEAD has advanced past the SHA at which the
previous run completed and re-fire the gate accordingly. The SHA is treated as
informational metadata: re-call with same outcome+display_detail but a
different head_at_completion is a "changed" overwrite without requiring
``--force``.
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
    head_at_completion = getattr(args, 'head_at_completion', None)

    metadata: dict[str, Any] = status.setdefault('metadata', {})
    phase_steps: dict[str, Any] = metadata.setdefault('phase_steps', {})
    phase_entry: dict[str, Any] = phase_steps.setdefault(phase, {})

    existing = phase_entry.get(step)

    if isinstance(existing, str) and not args.force:
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
                f'({existing!r}); re-run with --force to migrate the entry to the '
                'dict shape {"outcome": ..., "display_detail": ...}.'
            ),
        }

    new_entry = _build_entry(outcome, display_detail, head_at_completion)

    if isinstance(existing, dict):
        existing_outcome = existing.get('outcome')
        existing_detail = existing.get('display_detail')
        existing_head = existing.get('head_at_completion')
        if (
            existing_outcome == outcome
            and existing_detail == display_detail
            and existing_head == head_at_completion
        ):
            return {
                'status': 'success',
                'plan_id': args.plan_id,
                'phase': phase,
                'step': step,
                'outcome': outcome,
                'display_detail': display_detail,
                'head_at_completion': head_at_completion,
                'changed': False,
            }
        if existing_outcome == outcome and (
            existing_detail != display_detail or existing_head != head_at_completion
        ):
            phase_entry[step] = new_entry
            write_status(args.plan_id, status)
            return {
                'status': 'success',
                'plan_id': args.plan_id,
                'phase': phase,
                'step': step,
                'outcome': outcome,
                'display_detail': display_detail,
                'head_at_completion': head_at_completion,
                'changed': True,
                'previous_outcome': existing_outcome,
                'previous_display_detail': existing_detail,
                'previous_head_at_completion': existing_head,
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
    previous_head = None
    if isinstance(existing, dict):
        previous_outcome = existing.get('outcome')
        previous_detail = existing.get('display_detail')
        previous_head = existing.get('head_at_completion')

    phase_entry[step] = new_entry
    write_status(args.plan_id, status)

    return {
        'status': 'success',
        'plan_id': args.plan_id,
        'phase': phase,
        'step': step,
        'outcome': outcome,
        'display_detail': display_detail,
        'head_at_completion': head_at_completion,
        'changed': True,
        'previous_outcome': previous_outcome,
        'previous_display_detail': previous_detail,
        'previous_head_at_completion': previous_head,
    }


def _build_entry(
    outcome: str, display_detail: str | None, head_at_completion: str | None
) -> dict[str, Any]:
    """Build the phase_entry[step] dict, omitting head_at_completion when None.

    Legacy compatibility: callers that omit ``--head-at-completion`` produce
    the historical two-key shape ``{"outcome": ..., "display_detail": ...}``.
    Only when a SHA is supplied does the third key appear in the persisted
    record.
    """
    entry: dict[str, Any] = {'outcome': outcome, 'display_detail': display_detail}
    if head_at_completion is not None:
        entry['head_at_completion'] = head_at_completion
    return entry

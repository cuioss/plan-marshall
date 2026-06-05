#!/usr/bin/env python3
"""
assert-step-recorded command handler for manage-status.

Read-only verdict over ``status.metadata.phase_steps[phase][step]``: does a
terminal step record exist for the named phase step? A record counts as
*recorded* iff a dict entry with a terminal ``outcome`` in
``{done, skipped, loop_back, failed}`` is present. The verb performs zero
writes to ``status.json`` — it is the deterministic post-dispatch guard the
phase-6-finalize dispatcher calls after every dispatched-step return to detect
the silent "agent returned ``status: success`` but skipped its mandated
``mark-step-done`` side-effect" gap.

Without ``--require-terminal`` the verb always returns ``status: success`` and
reports the boolean ``recorded`` (plus the matched ``outcome`` or ``null``).
With ``--require-terminal`` a missing terminal record is escalated to
``status: error, error: step_record_missing`` so the dispatcher gets a verdict
it can branch on directly.
"""

import argparse
from typing import Any

from _cmd_mark_step import VALID_OUTCOMES
from _status_core import require_status


def cmd_assert_step_recorded(args: argparse.Namespace) -> dict | None:
    """Return a read-only verdict on whether a phase step has a terminal record."""
    status = require_status(args)
    if status is None:
        return None

    phase = args.phase
    step = args.step
    if not phase or not step:
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'invalid_argument',
            'message': '--phase and --step are required and must be non-empty',
        }

    metadata: dict[str, Any] = status.get('metadata') or {}
    phase_steps: dict[str, Any] = metadata.get('phase_steps') or {}
    phase_entry: dict[str, Any] = phase_steps.get(phase) or {}
    existing = phase_entry.get(step)

    outcome: str | None = None
    if isinstance(existing, dict):
        candidate = existing.get('outcome')
        if candidate in VALID_OUTCOMES:
            outcome = candidate

    recorded = outcome is not None

    if args.require_terminal and not recorded:
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'step_record_missing',
            'phase': phase,
            'step': step,
            'recorded': False,
            'outcome': None,
            'message': (
                f'No terminal record for step {step!r} in phase {phase!r}: the '
                'dispatched step returned without recording a mark-step-done '
                f'outcome (expected one of {list(VALID_OUTCOMES)}).'
            ),
        }

    return {
        'status': 'success',
        'plan_id': args.plan_id,
        'phase': phase,
        'step': step,
        'recorded': recorded,
        'outcome': outcome,
    }

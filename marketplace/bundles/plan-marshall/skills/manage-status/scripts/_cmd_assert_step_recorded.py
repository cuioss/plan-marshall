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

With ``--require-terminal`` a missing terminal record is escalated to an error
verdict the dispatcher can branch on directly. Two error branches are
distinguished by whether a *near-miss* orphan record exists in the same phase:

- ``step_record_mismatched_key``: the queried ``step`` key has no terminal
  record, BUT another key in the same ``phase_entry`` carries a terminal
  ``outcome`` (a bare/mis-keyed orphan — e.g. a dispatched skill that recorded
  under its bare name instead of its fully-qualified manifest ``step_id``).
  The verdict carries the ``orphan_key`` and its ``outcome`` so the dispatcher
  can report the mis-keying instead of an infinite "record under the wrong key,
  re-enter, record under the wrong key again" recovery loop.
- ``step_record_missing``: no terminal record exists under any key in the phase
  — a truly-absent record. This is the original behavior, retained unchanged.
"""

import argparse
from typing import Any

from _cmd_mark_step import VALID_OUTCOMES
from _status_core import require_status


def _terminal_outcome(entry: Any) -> str | None:
    """Return the terminal ``outcome`` of a phase-step entry, or ``None``."""
    if isinstance(entry, dict):
        candidate = entry.get('outcome')
        if isinstance(candidate, str) and candidate in VALID_OUTCOMES:
            return candidate
    return None


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

    outcome = _terminal_outcome(phase_entry.get(step))
    recorded = outcome is not None

    if args.require_terminal and not recorded:
        # Near-miss detection: scan the same phase for an orphan terminal record
        # under a different key before declaring the record truly absent.
        for other_key, other_entry in phase_entry.items():
            if other_key == step:
                continue
            orphan_outcome = _terminal_outcome(other_entry)
            if orphan_outcome is not None:
                return {
                    'status': 'error',
                    'plan_id': args.plan_id,
                    'error': 'step_record_mismatched_key',
                    'phase': phase,
                    'step': step,
                    'recorded': False,
                    'outcome': None,
                    'orphan_key': other_key,
                    'orphan_outcome': orphan_outcome,
                    'message': (
                        f'No terminal record for step {step!r} in phase {phase!r}, '
                        f'but a terminal record exists under the near-miss key '
                        f'{other_key!r} (outcome {orphan_outcome!r}). The dispatched '
                        'step recorded its mark-step-done outcome under the wrong '
                        f'key — expected the queried step name {step!r}.'
                    ),
                }

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

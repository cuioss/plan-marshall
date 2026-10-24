#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""
halt state handlers for manage-status.

A **halt** is the record that a dispatch guard or a step gate ended a phase step
without a completion: the post-dispatch completion guard recording
``outcome: failed`` for a leaf that returned without a terminal record, a step's
own ``mark-step-done --outcome failed``, or an ``escalate_ask`` return that
hands the decision to the operator. The record lives in
``status.metadata.halts[phase][step]`` beside ``phase_steps`` — and beside it
deliberately, NOT inside it: a halt is the step's CONTROL state (why the step
stopped and what may follow), while ``phase_steps`` is the roster the
``phase_steps_complete`` handshake counts. Writing a halt into ``phase_steps``
would make a step look fired-terminally when it had only stopped.

The record shape is::

    halts[phase][step] = {
        "outcome":      "failed" | "halted",
        "reason":       "<why the step stopped>",
        "escalate_ask": true | false,
        "recorded_at":  "<iso-8601 UTC>",
        "answer":       null | {"selected": "<option label>", "answered_at": "<iso>"},
    }

``outcome`` is the two-value halt vocabulary, distinct from
:data:`_cmd_mark_step.VALID_OUTCOMES` because ``halted`` is not a step outcome
this skill records — it names a stop that produced no phase-steps write at all
(an ``escalate_ask`` return, or a harness cancellation).

Three verbs, and one read seam the rest of the tree consumes:

* ``record`` — the dispatch guard or step gate writes the halt. A new record
  REPLACES the previous one wholesale, so a re-halt is a fresh, unanswered stop
  rather than a stale escalation carried forward.
* ``answer`` — records the operator's selected option on an ``escalate_ask``
  halt. This is the ONLY writer of ``answer``, and it refuses a halt that
  raised no escalation: an answer to a question nobody asked would read as
  consent for a decision the operator never saw.
* ``read`` — reports one halt record, or every record in the plan.
* :func:`unanswered_escalation` — the read seam ``mark-step-done`` and the
  phase-6-finalize continuation check consume. A halt whose
  ``escalate_ask`` is true and whose ``answer`` is null is an operator
  decision that has not been made yet.

**Why the store exists.** A strategist reading only prose could record
``failed``, log "halted", and then improvise a recovery the workflow does not
name — the observed failure this seam closes. Persisting the halt makes the
stop a fact, and :func:`unanswered_escalation` makes the escalation a gate:
``mark-step-done`` refuses a resolution recorded over an unanswered escalation
(``error: escalation_unanswered``), so no step can be marked complete on the
strength of a decision the operator never made.

Every verb exits 0 on every verdict — the verdict travels in the TOON per this
skill's output contract. A non-zero exit is reserved for a genuine crash.
"""

import argparse
from typing import Any

from _status_core import require_status, write_status
from file_ops import now_utc_iso

#: The metadata key holding the halt store, beside ``phase_steps``.
HALTS_KEY = 'halts'

#: The two halt outcomes. Deliberately NOT ``_cmd_mark_step.VALID_OUTCOMES``:
#: ``halted`` names a stop that produced no phase-steps record, so importing the
#: step-outcome vocabulary here would admit values this store cannot mean.
HALT_OUTCOMES: tuple[str, ...] = ('failed', 'halted')

#: The step outcome that is an operator RESOLUTION — a claim the step is
#: finished. ``failed`` and ``loop_back`` are progress, not resolution, so they
#: never consult an open escalation.
RESOLUTION_OUTCOMES: tuple[str, ...] = ('done', 'skipped')


def _phase_entry(status: dict[str, Any], phase: str, *, create: bool) -> dict[str, Any]:
    """Return ``metadata.halts[phase]``, creating it only when asked."""
    metadata = status.get('metadata')
    if not isinstance(metadata, dict):
        if not create:
            return {}
        metadata = {}
        status['metadata'] = metadata
    halts = metadata.get(HALTS_KEY)
    if not isinstance(halts, dict):
        if not create:
            return {}
        halts = {}
        metadata[HALTS_KEY] = halts
    entry = halts.get(phase)
    if not isinstance(entry, dict):
        if not create:
            return {}
        entry = {}
        halts[phase] = entry
    return entry


def read_halt_record(status: dict[str, Any], phase: str, step: str) -> dict[str, Any] | None:
    """Return the halt record for ``(phase, step)``, or ``None`` when absent.

    Read-only, and tolerant of a malformed store: a phase entry that is not a
    mapping, or a step entry that is not one, reads as "no halt" rather than
    raising. A malformed record is not a halt anyone can act on, and inventing
    one would make the continuation check answer for a state nobody wrote.
    """
    if not isinstance(status, dict):
        return None
    phase_entry = _phase_entry(status, phase, create=False)
    record = phase_entry.get(step)
    return record if isinstance(record, dict) else None


def unanswered_escalation(status: dict[str, Any], phase: str, step: str) -> dict[str, Any] | None:
    """Return the halt record when it escalated and no operator answer is logged.

    This is the read seam every resolution path consumes. ``None`` means either
    there is no halt, the halt raised no escalation, or the escalation has been
    answered — all three are states in which a resolution may be recorded.
    """
    record = read_halt_record(status, phase, step)
    if record is None:
        return None
    if not record.get('escalate_ask'):
        return None
    if isinstance(record.get('answer'), dict):
        return None
    return record


def _invalid(plan_id: str, message: str) -> dict[str, Any]:
    return {
        'status': 'error',
        'plan_id': plan_id,
        'error': 'invalid_argument',
        'message': message,
    }


def cmd_halt_record(args: argparse.Namespace) -> dict[str, Any] | None:
    """Persist a halt for one phase step, replacing any previous halt."""
    status = require_status(args)
    if status is None:
        return None

    phase = args.phase
    step = args.step
    outcome = args.outcome
    reason = (args.reason or '').strip()
    if not phase or not step:
        return _invalid(args.plan_id, '--phase and --step are required and must be non-empty')
    if outcome not in HALT_OUTCOMES:
        return _invalid(args.plan_id, f'--outcome must be one of {list(HALT_OUTCOMES)}, got: {outcome!r}')
    if not reason:
        return _invalid(
            args.plan_id,
            '--reason is required and must be non-empty: a halt nobody can explain is '
            'indistinguishable from an ordinary skip',
        )

    phase_entry = _phase_entry(status, phase, create=True)
    previous = phase_entry.get(step) if isinstance(phase_entry.get(step), dict) else None
    record: dict[str, Any] = {
        'outcome': outcome,
        'reason': reason,
        'escalate_ask': bool(getattr(args, 'escalate_ask', False)),
        'recorded_at': now_utc_iso(),
        'answer': None,
    }
    phase_entry[step] = record
    write_status(args.plan_id, status)

    result: dict[str, Any] = {
        'status': 'success',
        'plan_id': args.plan_id,
        'phase': phase,
        'step': step,
        'halted': True,
        'outcome': outcome,
        'reason': reason,
        'escalate_ask': record['escalate_ask'],
        'recorded_at': record['recorded_at'],
    }
    if previous is not None:
        result['previous_outcome'] = previous.get('outcome')
    return result


def cmd_halt_answer(args: argparse.Namespace) -> dict[str, Any] | None:
    """Record the operator's selected option on an escalated halt."""
    status = require_status(args)
    if status is None:
        return None

    phase = args.phase
    step = args.step
    selected = (args.selected or '').strip()
    if not phase or not step:
        return _invalid(args.plan_id, '--phase and --step are required and must be non-empty')
    if not selected:
        return _invalid(
            args.plan_id,
            '--selected is required and must be non-empty: the answer is the option the '
            'operator chose, and an empty one records no decision',
        )

    record = read_halt_record(status, phase, step)
    if record is None:
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'no_halt_record',
            'phase': phase,
            'step': step,
            'message': (
                f'No halt is recorded for step {step!r} in phase {phase!r}, so there is no '
                'escalation to answer. Record the halt first (`halt record --escalate-ask`).'
            ),
        }
    if not record.get('escalate_ask'):
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'no_escalation',
            'phase': phase,
            'step': step,
            'halt_outcome': record.get('outcome'),
            'message': (
                f'The recorded halt for step {step!r} in phase {phase!r} raised no operator '
                'escalation. An answer here would record consent for a question nobody '
                'asked, so nothing was written.'
            ),
        }

    record['answer'] = {'selected': selected, 'answered_at': now_utc_iso()}
    write_status(args.plan_id, status)
    return {
        'status': 'success',
        'plan_id': args.plan_id,
        'phase': phase,
        'step': step,
        'halted': True,
        'escalate_ask': True,
        'selected': selected,
        'answered_at': record['answer']['answered_at'],
    }


def cmd_halt_read(args: argparse.Namespace) -> dict[str, Any] | None:
    """Report one halt record, or every halt record in the plan (read-only)."""
    status = require_status(args)
    if status is None:
        return None

    phase = getattr(args, 'phase', None)
    step = getattr(args, 'step', None)
    if bool(phase) != bool(step):
        return _invalid(args.plan_id, '--phase and --step must be supplied together, or neither for a full read')

    metadata = status.get('metadata') if isinstance(status.get('metadata'), dict) else {}
    halts = metadata.get(HALTS_KEY) if isinstance(metadata, dict) else None
    store: dict[str, Any] = halts if isinstance(halts, dict) else {}

    if phase and step:
        record = read_halt_record(status, phase, step)
        return {
            'status': 'success',
            'plan_id': args.plan_id,
            'phase': phase,
            'step': step,
            'recorded': record is not None,
            'record': record,
            'escalation_unanswered': unanswered_escalation(status, phase, step) is not None,
        }

    rows: list[dict[str, Any]] = []
    for stored_phase in sorted(store):
        phase_entry = store[stored_phase]
        if not isinstance(phase_entry, dict):
            continue
        for stored_step in sorted(phase_entry):
            record = phase_entry[stored_step]
            if not isinstance(record, dict):
                continue
            rows.append(
                {
                    'phase': stored_phase,
                    'step': stored_step,
                    'outcome': record.get('outcome'),
                    'escalate_ask': bool(record.get('escalate_ask')),
                    'escalation_unanswered': unanswered_escalation(status, stored_phase, stored_step) is not None,
                    'recorded_at': record.get('recorded_at'),
                }
            )
    return {
        'status': 'success',
        'plan_id': args.plan_id,
        'count': len(rows),
        'records': rows,
    }

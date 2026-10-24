#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Decide which continuation a halted phase-6-finalize step may take.

The post-dispatch completion guard and every step gate record a stop — the halt
state ``manage-status halt record`` persists under
``status.metadata.halts[phase][step]``. This script answers the ONE question that
has to be answered after such a stop: *is the continuation the dispatcher is
about to take one the workflow names for this outcome?*

The named continuations are a CLOSED set — :data:`NAMED_CONTINUATIONS`, whose
roster is declared in ``phase-6-finalize/SKILL.md`` § "Halt continuation
roster" and mirrored here for the decision:

* ``retry`` — the resumable re-entry check re-runs a ``failed`` step. Bounded:
  the dispatcher retries a failed step **exactly once per finalize invocation**
  (SKILL.md Step 3 item 1), so the caller must state which attempt this is, the
  bound is :data:`DOCUMENTED_RETRY_BOUND`, and a bound wider than the documented
  one is refused with ``retry_bound_not_documented`` — a bound the party it binds
  can widen is no bound. An attempt past it is ``retry_bound_exhausted``.
* ``loop_back`` — the step handed control to an upstream phase through
  ``mark-step-done --outcome loop_back`` and its recorded ``loop_back_target``.
* ``operator_question`` — the operator is asked, and their selected option is
  executed as worded.

Everything else is refused with ``error: halt_continuation_refused``, and the
refusal names the named set. That is deliberate and closed rather than a
blocklist: an undocumented harness recovery verb (OpenCode ``session_move``, a
``resume``, an ad-hoc re-dispatch) is refused because it is not one of the three,
not because a list of forbidden names happened to include it. The observed
failure this closes improvised exactly such a verb after logging "halted".

One further refusal sits before the retry decision: a halt that raised an
operator escalation with no recorded ``halt answer`` admits ONLY
``operator_question``. Until the operator answers, the dispatcher cannot retry
past the decision or loop back around it — the escalation is the step's own
statement that the next move is the operator's. (``manage-status
mark-step-done`` enforces the same fact at the write boundary, refusing a
``done``/``skipped`` resolution outright.) A stored halt that cannot be read is
refused with ``halt_unreadable`` rather than answered for.

Return shape (CLI emits TOON; programmatic callers consume the dict directly)::

    status: success
    plan_id: <echo>
    phase: <echo>
    step: <echo>
    halted: true | false
    escalate_ask: true | false
    continuation: <echo>
    allowed: true
    reason: no_halt_record | continuation_named

A refusal is ``status: error`` carrying its ``error`` code, ``halted``,
``allowed: false``, ``allowed_continuations[]`` (the set that WOULD be admitted
for this halt, empty on a failed READ), and a ``message`` naming them. Exit code
is ``0`` on every verdict: the verdict travels in the TOON, so a caller branches
on ``error`` rather than on an exit code an "unexpected" refusal would also
produce.

The script is registered through ``generate_executor.py`` and consumed via the
executor proxy::

    python3 .plan/execute-script.py plan-marshall:phase-6-finalize:halt_continuation \\
      check --plan-id {plan_id} --phase 6-finalize --step create-pr \\
      --continuation retry --attempt 1 --max-attempts 1
"""

from __future__ import annotations

import argparse
import sys
from typing import Any

from toon_parser import serialize_toon

#: The CLOSED set of continuations a halted step may take. Every other token is
#: refused by construction, so an undocumented recovery verb cannot be admitted
#: by being absent from a blocklist.
NAMED_CONTINUATIONS: tuple[str, ...] = ('loop_back', 'operator_question', 'retry')

#: The re-run continuation. It is the only one that carries a bound.
RETRY = 'retry'

#: The continuation that hands the decision to the operator.
OPERATOR_QUESTION = 'operator_question'

#: The documented number of retries a failed finalize step gets per invocation
#: (``phase-6-finalize/SKILL.md`` Step 3 item 1: "failed steps get exactly one
#: retry per invocation"). It is a CONSTANT rather than a caller parameter on
#: purpose — a bound the party it binds can widen is not a bound.
DOCUMENTED_RETRY_BOUND = 1

#: Why a continuation was admitted — the two success reasons.
REASON_NO_HALT = 'no_halt_record'
REASON_NAMED = 'continuation_named'

# Error codes. One per refusal shape, so a caller routes on the code.
ERROR_STATUS_UNAVAILABLE = 'status_unavailable'
ERROR_PLAN_NOT_FOUND = 'plan_not_found'
ERROR_HALT_UNREADABLE = 'halt_unreadable'
ERROR_CONTINUATION_REFUSED = 'halt_continuation_refused'
ERROR_ESCALATION_UNANSWERED = 'escalation_unanswered'
ERROR_RETRY_BOUND_REQUIRED = 'retry_bound_required'
ERROR_RETRY_BOUND_NOT_DOCUMENTED = 'retry_bound_not_documented'
ERROR_RETRY_BOUND_EXHAUSTED = 'retry_bound_exhausted'

#: The phase this decision is recorded for. The halt store is phase-keyed and
#: this seam is the finalize dispatcher's, so a cross-phase claim is refused
#: rather than silently answered against a store it does not own.
FINALIZE_PHASE = '6-finalize'


def _base(plan_id: str, phase: str, step: str, continuation: str) -> dict[str, Any]:
    """The fields every payload carries, so a refusal and an admission compare."""
    return {
        'plan_id': plan_id,
        'phase': phase,
        'step': step,
        'continuation': continuation,
    }


def _allowed(payload: dict[str, Any], allowed: list[str], reason: str) -> dict[str, Any]:
    return {**payload, 'status': 'success', 'allowed': True, 'allowed_continuations': allowed, 'reason': reason}


def _refused(
    payload: dict[str, Any],
    error: str,
    message: str,
    allowed: list[str],
    **extra: Any,
) -> dict[str, Any]:
    return {
        **payload,
        'status': 'error',
        'error': error,
        'allowed': False,
        'allowed_continuations': allowed,
        'message': message,
        **extra,
    }


def decide(
    record: dict[str, Any] | None,
    continuation: str,
    attempt: int | None,
    max_attempts: int | None,
    step: str = '',
) -> dict[str, Any]:
    """Decide one continuation against one halt record.

    Pure: no store, no filesystem. ``record`` is ``None`` when the step carries
    no halt, which admits every continuation — a step that never halted has
    nothing for this gate to constrain. ``step`` is carried only so a refusal can
    name the step it is about; the decision never depends on it.

    Order of the refusals is load-bearing. An unreadable record is refused FIRST,
    because every question below it is a question about a record nobody can read.
    Membership comes next, so an undocumented recovery verb is refused as such
    even on an escalated halt (naming the named set is the more useful fact). The
    unresolved escalation is checked third, because it narrows an otherwise-named
    continuation to ``operator_question`` alone. The retry bound is checked last,
    inside the retry branch the earlier checks have already admitted.
    """
    payload = _base('', '', step, continuation)
    if record is None:
        return {**_allowed(payload, list(NAMED_CONTINUATIONS), REASON_NO_HALT), 'halted': False, 'escalate_ask': False}

    if record.get('malformed'):
        return _refused(
            {**payload, 'halted': False, 'escalate_ask': False},
            ERROR_HALT_UNREADABLE,
            (
                f'The halt recorded for step {step!r} cannot be read, so no continuation can be '
                'admitted for it. Repair `status.metadata.halts` and re-record the halt — an '
                'unreadable store is a failed read, never a clean bill of health.'
            ),
            [],
        )

    escalate = bool(record.get('escalate_ask'))
    answer = record.get('answer')
    escalated_unanswered = escalate and not isinstance(answer, dict)
    admitted = list(NAMED_CONTINUATIONS) if not escalated_unanswered else [OPERATOR_QUESTION]
    narrowed = {'halted': True, 'escalate_ask': escalate, 'halt_outcome': record.get('outcome')}

    if continuation not in NAMED_CONTINUATIONS:
        return _refused(
            {**payload, **narrowed},
            ERROR_CONTINUATION_REFUSED,
            (
                f'Continuation {continuation!r} is not a named continuation for a halted step. '
                f'The workflow names exactly {list(NAMED_CONTINUATIONS)}: retry (the resumable '
                're-entry check, once per finalize invocation), loop_back (the step recorded a '
                'loop_back outcome with its own target), or operator_question (ask the operator '
                'and execute the selected option as worded). An undocumented harness recovery '
                'verb is none of these, so it is refused. Record the halt, then take one of the '
                'named continuations.'
            ),
            admitted,
        )

    if escalated_unanswered and continuation != OPERATOR_QUESTION:
        return _refused(
            {**payload, **narrowed},
            ERROR_ESCALATION_UNANSWERED,
            (
                f'Step {step!r} halted with an operator escalation '
                f'({record.get("outcome")!r}: {record.get("reason")!r}) and no operator answer '
                f'is recorded, so {continuation!r} was refused. Only operator_question is '
                'admitted: ask the operator, record the selected option with '
                '`manage-status halt answer`, and then take the continuation the answer names.'
            ),
            admitted,
        )

    if continuation == RETRY:
        if attempt is None:
            return _refused(
                {**payload, **narrowed},
                ERROR_RETRY_BOUND_REQUIRED,
                (
                    'retry requires --attempt: a failed step is retried exactly once per finalize '
                    'invocation (phase-6-finalize SKILL.md Step 3 item 1), so the caller states '
                    'which attempt this is.'
                ),
                admitted,
            )
        if max_attempts is None:
            max_attempts = DOCUMENTED_RETRY_BOUND
        if max_attempts > DOCUMENTED_RETRY_BOUND:
            return _refused(
                {**payload, **narrowed, 'attempt': attempt, 'max_attempts': max_attempts},
                ERROR_RETRY_BOUND_NOT_DOCUMENTED,
                (
                    f'--max-attempts {max_attempts} claims a bound wider than the documented '
                    f'{DOCUMENTED_RETRY_BOUND}. The bound belongs to the workflow, not to the '
                    'caller: a bound the party it binds can widen is no bound. Pass --attempt and '
                    f'at most --max-attempts {DOCUMENTED_RETRY_BOUND}.'
                ),
                admitted,
            )
        if attempt > max_attempts:
            return _refused(
                {**payload, **narrowed, 'attempt': attempt, 'max_attempts': max_attempts},
                ERROR_RETRY_BOUND_EXHAUSTED,
                (
                    f'retry attempt {attempt} exceeds the documented bound of {max_attempts}. The '
                    'bound is spent: report the step as still failed and stop, rather than granting '
                    'the step another round it was never allowed.'
                ),
                admitted,
            )
        return {
            **_allowed(payload, admitted, REASON_NAMED),
            **narrowed,
            'attempt': attempt,
            'max_attempts': max_attempts,
        }

    return {**_allowed(payload, admitted, REASON_NAMED), **narrowed}


def resolve_record(plan_id: str, phase: str, step: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Read the step's halt record, or return the error payload that prevented it.

    Distinguishes "looked, and the step never halted" (``(None, None)``) from
    "could not look" (an error payload): the first admits every continuation, and
    collapsing the second into it would let an unreadable store read as a clean
    bill of health.
    """
    try:
        from _cmd_halt import read_halt_record
        from _status_core import read_status
    except ImportError as exc:  # a missing reader is reported, never swallowed
        return None, {
            'status': 'error',
            'error': ERROR_STATUS_UNAVAILABLE,
            'message': f'the manage-status readers are not importable ({exc}), so the halt state could not be read',
        }

    try:
        status = read_status(plan_id)
    except Exception as exc:  # an unreadable status is a failed read, not an empty store
        return None, {
            'status': 'error',
            'error': ERROR_STATUS_UNAVAILABLE,
            'message': f'status.json for plan {plan_id!r} could not be read ({exc})',
        }
    if not isinstance(status, dict) or not status:
        return None, {
            'status': 'error',
            'error': ERROR_PLAN_NOT_FOUND,
            'message': f'no status.json is visible for plan {plan_id!r} from this checkout',
        }
    return read_halt_record(status, phase, step), None


def check_continuation(
    plan_id: str,
    phase: str,
    step: str,
    continuation: str,
    attempt: int | None = None,
    max_attempts: int | None = None,
) -> dict[str, Any]:
    """Resolve the halt state, then decide the continuation against it."""
    payload = _base(plan_id, phase, step, continuation)
    if phase != FINALIZE_PHASE:
        return _refused(
            payload,
            ERROR_CONTINUATION_REFUSED,
            (
                f'This seam decides the {FINALIZE_PHASE} dispatcher\u2019s continuations; phase '
                f'{phase!r} has no halt continuation roster here. Ask for {FINALIZE_PHASE} or read '
                'the halt state with `manage-status halt read`.'
            ),
            [],
        )
    record, error = resolve_record(plan_id, phase, step)
    if error is not None:
        # A failed READ answers the same three fields a refusal does, so a caller
        # branching on `allowed_continuations` never has to special-case it.
        return {**error, **payload, 'halted': False, 'allowed': False, 'allowed_continuations': []}
    decision = decide(record, continuation, attempt, max_attempts, step=step)
    return {**decision, **payload}


def cmd_check(args: argparse.Namespace) -> int:
    """CLI wrapper around :func:`check_continuation` — emits TOON, always returns 0."""
    payload = check_continuation(
        plan_id=args.plan_id,
        phase=args.phase,
        step=args.step,
        continuation=args.continuation,
        attempt=args.attempt,
        max_attempts=args.max_attempts,
    )
    print(serialize_toon(payload))
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the parser for the ``check`` verb."""
    parser = argparse.ArgumentParser(
        description=(
            'Decide whether a continuation a halted phase-6-finalize step is about to take is '
            'one the workflow names for that outcome. The named set is closed: retry (bounded, '
            'once per finalize invocation), loop_back, operator_question. Anything else — an '
            'undocumented harness recovery verb included — is refused with the named set echoed.'
        ),
        allow_abbrev=False,
    )
    sub = parser.add_subparsers(dest='command_name', required=True)

    check_parser = sub.add_parser('check', help='Admit or refuse one continuation after a halt', allow_abbrev=False)
    check_parser.add_argument(
        '--plan-id', required=True, dest='plan_id', help='Plan whose status holds the halt state.'
    )
    check_parser.add_argument(
        '--phase',
        required=True,
        help=f'The phase the step belongs to ({FINALIZE_PHASE} is the only one with a roster here).',
    )
    check_parser.add_argument('--step', required=True, help='Step identifier the halt was recorded under.')
    check_parser.add_argument(
        '--continuation',
        required=True,
        help=(
            'The continuation about to be taken. Admitted values: '
            f'{", ".join(NAMED_CONTINUATIONS)}. Any other token is refused.'
        ),
    )
    check_parser.add_argument(
        '--attempt',
        type=int,
        default=None,
        help='For retry: which attempt this is (1 for the first). Required with retry.',
    )
    check_parser.add_argument(
        '--max-attempts',
        dest='max_attempts',
        type=int,
        default=None,
        help='For retry: the documented bound this attempt is measured against. Required with retry.',
    )
    check_parser.set_defaults(func=cmd_check)
    return parser


def main() -> int:
    """Parse args and dispatch to the selected subcommand handler."""
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == '__main__':
    sys.exit(main())


__all__ = [
    'DOCUMENTED_RETRY_BOUND',
    'ERROR_CONTINUATION_REFUSED',
    'ERROR_ESCALATION_UNANSWERED',
    'ERROR_HALT_UNREADABLE',
    'ERROR_RETRY_BOUND_EXHAUSTED',
    'ERROR_RETRY_BOUND_NOT_DOCUMENTED',
    'ERROR_RETRY_BOUND_REQUIRED',
    'NAMED_CONTINUATIONS',
    'OPERATOR_QUESTION',
    'RETRY',
    'check_continuation',
    'decide',
    'resolve_record',
]

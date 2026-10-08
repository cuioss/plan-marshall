#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""
loop-back command handlers for manage-status.

Budgets finalize loop-back rounds PER REQUESTING SOURCE. Every source that can
request a loop-back — a finalize step, or the dispatcher-owned unified triage —
spends rounds from its own count, so one source exhausting its rounds cannot
starve another of the rounds it never used.

The store lives in ``status.metadata.loop_back_budgets``, keyed by source, beside
the ``phase_steps`` and ``merge_authorizations`` maps the same skill already
owns::

    loop_back_budgets[source] = {
        "spent": <int>,
        "granted": <int>,
        "grants": [{rounds, reason, granted_by, granted_at, spent_at_grant}, ...]
    }

``spent`` is how many rounds the source has been admitted for; ``granted`` is how
many rounds beyond the configured ceiling it has been given. A source with no
entry has spent nothing and been granted nothing. ``grants`` is present only once
a round has been granted, and holds one record per grant, oldest first.

``admit`` is the admission gate. It takes the plan, a source and the configured
ceiling, and admits the next round when ``spent + 1 <= ceiling + granted``. An
admission persists the increment in the same call, so the count cannot be lost
between the decision and the write. A refusal writes nothing.

``grant`` is the one way past a ceiling refusal. It adds rounds to a named
source's ``granted`` total and appends the record of who granted them, why, when,
and how many rounds the source had spent at that moment. A grant with a blank
reason or fewer than one round is refused and writes nothing, so every round
beyond the configured ceiling is traceable to a stated reason. Once the grant is
persisted, one decision-log line names the source, the rounds, the reason and who
granted them. A line that could not be written leaves the grant in place; the
return carries ``decision_logged`` either way, and ``decision_log_error`` when the
line did not land.

The retired scalar ``status.metadata.loop_back_iteration`` is never read. A status
document still carrying it is treated as carrying no budget at all: the scalar is
attributed to no source, and every source starts at zero.

``close`` is the other way forward from a ceiling refusal. Where ``grant`` buys
the source another round, ``close`` ends the loop: the operator closes a finalize
step on named residual findings, and the close is recorded as an override rather
than as a verdict the step reached. It touches no budget. In one call it records
the step ``done`` at the closing HEAD with the facts
``may_close=operator_override`` / ``acceptance=operator_override``, resolves
exactly the named findings as ``accepted`` with the operator's rationale,
resolves the step's own pending state findings by their rule key, and stamps a
re-fire waiver on each head-dependent step the operator names. Every input is
validated before the first write — a named finding that is not pending in the
``6-finalize`` Q-Gate store stops the call with nothing written.

The verdict travels in the TOON per the output contract — every verb exits 0 on
every verdict. A store this module cannot interpret is reported as an error
rather than read as an empty budget: reading it as empty would hand the source
rounds it may already have spent.
"""

import argparse
import re
from typing import Any

from _cmd_mark_step import cmd_mark_step_done, find_step_record, write_refire_waiver
from _locks_core import rmw_json
from _status_core import get_status_path, require_status, write_status
from _step_key_canonical import canonicalize_step_key
from file_ops import now_utc_iso
from plan_logging import log_decision

BUDGETS_KEY = 'loop_back_budgets'
SPENT_KEY = 'spent'
GRANTED_KEY = 'granted'
GRANTS_KEY = 'grants'

#: The phase whose steps ``close`` closes and whose Q-Gate store it resolves in.
CLOSE_PHASE = '6-finalize'

#: The value ``close`` records for both the ``may_close`` and the ``acceptance``
#: fact. It is what tells an operator close apart from a close the step's own
#: verifier granted (``may_close=yes`` / ``acceptance=accepted``).
OPERATOR_OVERRIDE = 'operator_override'

#: A full object id — 40 hex characters, or 64 in a SHA-256 repository. An
#: abbreviation is refused: the closing HEAD is compared for equality against the
#: live HEAD by the re-fire waiver's reader, and an abbreviation never equals it.
_FULL_SHA_RE = re.compile(r'^(?:[0-9a-f]{40}|[0-9a-f]{64})$')


def state_rule_key(step: str) -> str:
    """Return the rule key a step files its own state findings under.

    A step's state findings describe the step's situation rather than a defect
    in a file, so they are filed under one fixed rule key and resolved by it.
    The key is derived from the step name, so ``close`` needs no per-step table
    to find them: the findings of ``pre-submission-self-review`` carry
    ``pre-submission-self-review-state``.
    """
    return f'{step}-state'


def _is_count(value: Any) -> bool:
    """True for a non-negative integer that is not a bool."""
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _error(plan_id: str, error: str, source: str, message: str) -> dict[str, Any]:
    return {
        'status': 'error',
        'plan_id': plan_id,
        'error': error,
        'source': source,
        'message': f'{message} Nothing was written.',
    }


def _load_entry(status: dict[str, Any], plan_id: str, source: str) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Return ``(entry, error)`` for one source's budget record.

    ``entry`` is a copy of the stored record (empty when the source has none), so
    a caller can modify it and store it back without disturbing keys it does not
    own. ``error`` is the ``invalid_budget_store`` payload when the store, the
    record, or one of its counts does not have the documented shape.
    """
    metadata = status.get('metadata') or {}
    budgets = metadata.get(BUDGETS_KEY)
    if budgets is None:
        return {}, None
    if not isinstance(budgets, dict):
        return {}, _error(
            plan_id, 'invalid_budget_store', source, f'status.metadata.{BUDGETS_KEY} is not a map keyed by source.'
        )

    stored = budgets.get(source)
    if stored is None:
        return {}, None
    record = f"status.metadata.{BUDGETS_KEY}['{source}']"
    if not isinstance(stored, dict):
        return {}, _error(plan_id, 'invalid_budget_store', source, f'{record} is not a budget record.')
    if not _is_count(stored.get(SPENT_KEY, 0)) or not _is_count(stored.get(GRANTED_KEY, 0)):
        return {}, _error(
            plan_id,
            'invalid_budget_store',
            source,
            f'{record} carries a {SPENT_KEY} or {GRANTED_KEY} value that is not a non-negative integer.',
        )
    if not isinstance(stored.get(GRANTS_KEY, []), list):
        return {}, _error(
            plan_id, 'invalid_budget_store', source, f'{record} carries a {GRANTS_KEY} value that is not a list.'
        )
    return dict(stored), None


def _store_entry(status: dict[str, Any], plan_id: str, source: str, entry: dict[str, Any]) -> None:
    metadata: dict[str, Any] = status.setdefault('metadata', {})
    budgets: dict[str, Any] = metadata.setdefault(BUDGETS_KEY, {})
    budgets[source] = entry
    write_status(plan_id, status)


def cmd_loop_back_admit(args: argparse.Namespace) -> dict | None:
    """Admit or refuse the next loop-back round for one requesting source."""
    status = require_status(args)
    if status is None:
        return None

    source = args.source
    ceiling = args.ceiling
    if not source or not _is_count(ceiling):
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'invalid_argument',
            'message': '--source must be non-empty and --ceiling must be a non-negative integer',
        }

    entry, error = _load_entry(status, args.plan_id, source)
    if error is not None:
        return error

    granted = entry.get(GRANTED_KEY, 0)
    iteration = entry.get(SPENT_KEY, 0) + 1
    effective_ceiling = ceiling + granted
    admitted = iteration <= effective_ceiling

    if admitted:
        entry[SPENT_KEY] = iteration
        entry[GRANTED_KEY] = granted
        _store_entry(status, args.plan_id, source, entry)

    return {
        'status': 'success',
        'plan_id': args.plan_id,
        'admitted': admitted,
        'source': source,
        'iteration': iteration,
        'effective_ceiling': effective_ceiling,
        'ceiling': ceiling,
        'granted': granted,
    }


def cmd_loop_back_grant(args: argparse.Namespace) -> dict | None:
    """Add rounds to one source's budget and record who granted them and why."""
    status = require_status(args)
    if status is None:
        return None

    source = args.source
    rounds = args.rounds
    reason = (args.reason or '').strip()
    granted_by = (args.granted_by or '').strip()
    if not source or not granted_by:
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'invalid_argument',
            'message': '--source and --granted-by must be non-empty',
        }
    if not reason:
        return _error(
            args.plan_id,
            'blank_reason',
            source,
            '--reason must state why the rounds are granted; a blank reason is refused.',
        )
    if not _is_count(rounds) or rounds < 1:
        return _error(args.plan_id, 'invalid_rounds', source, '--rounds must be an integer of at least one.')

    entry, error = _load_entry(status, args.plan_id, source)
    if error is not None:
        return error

    spent = entry.get(SPENT_KEY, 0)
    granted = entry.get(GRANTED_KEY, 0) + rounds
    record: dict[str, Any] = {
        'rounds': rounds,
        'reason': reason,
        'granted_by': granted_by,
        'granted_at': now_utc_iso(),
        'spent_at_grant': spent,
    }
    grants = [*entry.get(GRANTS_KEY, []), record]
    entry[SPENT_KEY] = spent
    entry[GRANTED_KEY] = granted
    entry[GRANTS_KEY] = grants
    _store_entry(status, args.plan_id, source, entry)

    # The grant is persisted above. The decision line is written after it and
    # cannot undo it: a line that did not land is reported, never raised.
    log_error = _log_grant_decision(args.plan_id, source, rounds, reason, granted_by)

    result: dict[str, Any] = {
        'status': 'success',
        'plan_id': args.plan_id,
        'source': source,
        'rounds': rounds,
        'granted': granted,
        'spent': spent,
        'reason': reason,
        'granted_by': granted_by,
        'granted_at': record['granted_at'],
        'grant_count': len(grants),
        'decision_logged': log_error is None,
    }
    if log_error is not None:
        result['decision_log_error'] = log_error
    return result


def _log_grant_decision(plan_id: str, source: str, rounds: int, reason: str, granted_by: str) -> str | None:
    """Write the decision-log line for one persisted grant.

    Returns ``None`` when the line was written, or the reason it was not. Never
    raises: the grant this line describes is already in the status document, so
    a failure here is a missing log line and nothing more.
    """
    message = (
        f'(plan-marshall:manage-status:loop-back-grant) Granted {rounds} loop-back round(s) '
        f'to {source}: {reason} (granted_by={granted_by})'
    )
    try:
        logged = log_decision(plan_id, message, CLOSE_PHASE)
    except Exception as exc:  # a failed log write must not fail the persisted grant
        return f'{type(exc).__name__}: {exc}'
    if logged.get('status') != 'success':
        return str(logged.get('message') or logged.get('error') or 'decision log write failed')
    return None


def _close_error(plan_id: str, error: str, step: str, message: str, **extra: Any) -> dict[str, Any]:
    """Build a ``close`` refusal raised BEFORE the first write."""
    return {
        'status': 'error',
        'plan_id': plan_id,
        'error': error,
        'step': step,
        'message': f'{message} Nothing was written.',
        **extra,
    }


def _unique(values: list[str] | None) -> list[str]:
    """Return ``values`` with repeats dropped, first occurrence kept, order kept."""
    return list(dict.fromkeys(values or []))


def _load_findings_core() -> Any:
    """Return the findings storage module, or ``None`` when it cannot be imported.

    Imported lazily, as the manifest reader is in ``_cmd_mark_step``: the two
    budget verbs in this module need no findings store, and must keep working in
    an environment where it is not importable.
    """
    try:
        import _findings_core
    except ImportError:
        return None
    return _findings_core


def _holds_done_record(status: dict[str, Any], step: str) -> bool:
    """True when ``step`` already holds a ``done`` record in the close phase."""
    record = find_step_record(status, CLOSE_PHASE, step)
    return isinstance(record, dict) and record.get('outcome') == 'done'


class _NoWaiverStamped(Exception):
    """Raised inside the waiver critical section so the document is not committed."""


def _stamp_refire_waivers(
    plan_id: str, waived: list[str], closing_head: str, basis: str
) -> tuple[list[str], list[str]]:
    """Stamp the re-fire waivers onto the current status document in one locked update.

    The read, the stamps and the commit are one ``rmw_json`` critical section on
    the guard ``write_status`` commits through, so the waivers land on the
    document as it is at that moment and a change another writer committed
    beforehand is kept.

    The document is committed only when at least one waiver was stamped.
    ``rmw_json`` commits whatever its callback returns, so the callback raises
    to leave the file untouched when every waiver was refused. A status document
    that is missing or unreadable is read as empty, which refuses every waiver
    and therefore writes nothing.

    Returns ``(waived_steps, waiver_refusals)``.
    """
    waived_steps: list[str] = []
    waiver_refusals: list[str] = []

    def _apply(current: dict[str, Any]) -> dict[str, Any]:
        for name in waived:
            refusal = write_refire_waiver(current, CLOSE_PHASE, name, closing_head, basis)
            if refusal is None:
                waived_steps.append(name)
            else:
                waiver_refusals.append(refusal)
        if not waived_steps:
            raise _NoWaiverStamped
        current['updated'] = now_utc_iso()
        return current

    try:
        rmw_json(get_status_path(plan_id), _apply)
    except _NoWaiverStamped:
        pass
    return waived_steps, waiver_refusals


def cmd_loop_back_close(args: argparse.Namespace) -> dict | None:
    """Close a finalize step on named residual findings, recorded as an operator override."""
    status = require_status(args)
    if status is None:
        return None

    plan_id = args.plan_id
    step = canonicalize_step_key(args.step) if args.step else ''
    rationale = (args.rationale or '').strip()
    head = (args.head or '').strip()
    accept = _unique(args.accept)
    waived = _unique([canonicalize_step_key(name) for name in (args.waive_refire or [])])

    if not step:
        return _close_error(plan_id, 'invalid_argument', step, '--step must be non-empty.')
    if not rationale:
        return _close_error(
            plan_id,
            'blank_rationale',
            step,
            '--rationale must state why the step is closed on these findings; a blank rationale is refused.',
        )
    if not _FULL_SHA_RE.match(head):
        return _close_error(
            plan_id,
            'invalid_head',
            step,
            f'--head {head!r} is not a full commit SHA. Resolve it with git rev-parse HEAD; an abbreviation is refused.',
        )

    # A waiver answers for a completion that already happened, so each waived
    # step must already hold a done record. The step being closed is recorded
    # done at --head by this very call, so it has no re-fire to waive.
    not_waivable = [name for name in waived if name == step or not _holds_done_record(status, name)]
    if not_waivable:
        return _close_error(
            plan_id,
            'step_not_waivable',
            step,
            'Each --waive-refire step must be another step that already holds a done record; '
            f'these do not: {", ".join(not_waivable)}.',
            not_waivable=not_waivable,
        )

    findings_core = _load_findings_core()
    if findings_core is None:
        return _close_error(plan_id, 'findings_store_unavailable', step, 'The findings store module is not importable.')
    pending = findings_core.query_qgate_findings(plan_id, CLOSE_PHASE, resolution='pending')
    if pending.get('status') != 'success':
        return _close_error(
            plan_id,
            'findings_store_unreadable',
            step,
            f'The {CLOSE_PHASE} Q-Gate store could not be read: {pending.get("message", "")}',
            store_error=pending.get('error'),
        )
    pending_ids = {finding.get('hash_id') for finding in pending['findings']}
    not_pending = [hash_id for hash_id in accept if hash_id not in pending_ids]
    if not_pending:
        return _close_error(
            plan_id,
            'finding_not_pending',
            step,
            f'Each --accept hash id must name a pending finding of the {CLOSE_PHASE} Q-Gate store; '
            f'these do not: {", ".join(not_pending)}.',
            not_pending=not_pending,
        )

    marked = cmd_mark_step_done(
        argparse.Namespace(
            plan_id=plan_id,
            phase=CLOSE_PHASE,
            step=step,
            outcome='done',
            display_detail=f'operator close: {len(accept)} finding(s) accepted',
            head_at_completion=head,
            loop_back_target=None,
            fact=[
                f'may_close={OPERATOR_OVERRIDE}',
                f'acceptance={OPERATOR_OVERRIDE}',
                'work_performed=true',
            ],
            force=False,
            no_completion_log=False,
        )
    )
    if marked is None:
        return None
    if marked.get('status') != 'success':
        return _close_error(
            plan_id,
            'step_not_recorded',
            step,
            f'The step could not be recorded done: {marked.get("message", "")}',
            mark_error=marked.get('error'),
        )
    closing_head = str(marked.get('head_at_completion') or head)

    # From here on the step IS recorded done, so a failure below is reported as
    # an incomplete close naming what did and did not land — never as a refusal.
    accepted: list[str] = []
    not_accepted: list[str] = []
    for hash_id in accept:
        resolved = findings_core.resolve_qgate_finding(plan_id, CLOSE_PHASE, hash_id, 'accepted', detail=rationale)
        (accepted if resolved.get('status') == 'success' else not_accepted).append(hash_id)

    rule = state_rule_key(step)
    state = findings_core.resolve_qgate_findings_by_rule(
        plan_id,
        CLOSE_PHASE,
        rule,
        'accepted',
        f'operator close of {step} at {closing_head}: {rationale}',
    )
    state_resolved = state.get('status') == 'success'

    # The mark above committed its own copy of the document, so the waivers are
    # stamped onto the document as it is now, not onto the snapshot taken at entry.
    waived_steps: list[str] = []
    waiver_refusals: list[str] = []
    if waived:
        waived_steps, waiver_refusals = _stamp_refire_waivers(
            plan_id, waived, closing_head, f'operator close of {step}: {rationale}'
        )

    result: dict[str, Any] = {
        'status': 'success',
        'plan_id': plan_id,
        'step': step,
        'outcome': 'done',
        'head': closing_head,
        'may_close': OPERATOR_OVERRIDE,
        'acceptance': OPERATOR_OVERRIDE,
        'rationale': rationale,
        'accepted_count': len(accepted),
        'accepted': accepted,
        'state_rule': rule,
        'state_findings_resolved': len(state.get('resolved', [])) if state_resolved else 0,
        'waived_steps': waived_steps,
    }
    if not_accepted or not state_resolved or waiver_refusals:
        result['status'] = 'error'
        result['error'] = 'close_incomplete'
        result['not_accepted'] = not_accepted
        result['state_error'] = None if state_resolved else state.get('message', '')
        result['waiver_refusals'] = waiver_refusals
        result['message'] = (
            f'Step {step!r} was recorded done at {closing_head}, but the close did not complete: '
            'see not_accepted, state_error and waiver_refusals for what did not land.'
        )
    return result

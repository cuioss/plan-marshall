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
beyond the configured ceiling is traceable to a stated reason.

The retired scalar ``status.metadata.loop_back_iteration`` is never read. A status
document still carrying it is treated as carrying no budget at all: the scalar is
attributed to no source, and every source starts at zero.

The verdict travels in the TOON per the output contract — both verbs exit 0 on
every verdict. A store this module cannot interpret is reported as an error
rather than read as an empty budget: reading it as empty would hand the source
rounds it may already have spent.
"""

import argparse
from typing import Any

from _status_core import require_status, write_status
from file_ops import now_utc_iso

BUDGETS_KEY = 'loop_back_budgets'
SPENT_KEY = 'spent'
GRANTED_KEY = 'granted'
GRANTS_KEY = 'grants'


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

    return {
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
    }

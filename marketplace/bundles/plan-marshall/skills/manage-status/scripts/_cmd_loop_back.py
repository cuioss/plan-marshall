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

    loop_back_budgets[source] = {"spent": <int>, "granted": <int>}

``spent`` is how many rounds the source has been admitted for; ``granted`` is how
many rounds beyond the configured ceiling it has been given. A source with no
entry has spent nothing and been granted nothing.

``admit`` is the admission gate. It takes the plan, a source and the configured
ceiling, and admits the next round when ``spent + 1 <= ceiling + granted``. An
admission persists the increment in the same call, so the count cannot be lost
between the decision and the write. A refusal writes nothing.

The retired scalar ``status.metadata.loop_back_iteration`` is never read. A status
document still carrying it is treated as carrying no budget at all: the scalar is
attributed to no source, and every source starts at zero.

The verdict travels in the TOON per the output contract — ``admit`` exits 0 on
both an admission and a refusal. A store this module cannot interpret is reported
as an error rather than read as an empty budget: reading it as empty would hand
the source rounds it may already have spent.
"""

import argparse
from typing import Any

from _status_core import require_status, write_status

BUDGETS_KEY = 'loop_back_budgets'
SPENT_KEY = 'spent'
GRANTED_KEY = 'granted'


def _is_count(value: Any) -> bool:
    """True for a non-negative integer that is not a bool."""
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _invalid_store(plan_id: str, source: str, message: str) -> dict[str, Any]:
    return {
        'status': 'error',
        'plan_id': plan_id,
        'error': 'invalid_budget_store',
        'source': source,
        'message': f'{message} Nothing was written.',
    }


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

    metadata: dict[str, Any] = status.setdefault('metadata', {})
    budgets = metadata.get(BUDGETS_KEY)
    if budgets is None:
        budgets = {}
    elif not isinstance(budgets, dict):
        return _invalid_store(args.plan_id, source, f'status.metadata.{BUDGETS_KEY} is not a map keyed by source.')

    entry = budgets.get(source)
    if entry is None:
        entry = {}
    elif not isinstance(entry, dict):
        return _invalid_store(
            args.plan_id, source, f"status.metadata.{BUDGETS_KEY}['{source}'] is not a budget record."
        )

    spent = entry.get(SPENT_KEY, 0)
    granted = entry.get(GRANTED_KEY, 0)
    if not _is_count(spent) or not _is_count(granted):
        return _invalid_store(
            args.plan_id,
            source,
            f"status.metadata.{BUDGETS_KEY}['{source}'] carries a {SPENT_KEY} or {GRANTED_KEY} "
            'value that is not a non-negative integer.',
        )

    iteration = spent + 1
    effective_ceiling = ceiling + granted
    admitted = iteration <= effective_ceiling

    if admitted:
        budgets[source] = {SPENT_KEY: iteration, GRANTED_KEY: granted}
        metadata[BUDGETS_KEY] = budgets
        write_status(args.plan_id, status)

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

#!/usr/bin/env python3
"""Deterministic plan-time bin-packer for manage-tasks.

This module packs already-sized tasks into execution *envelope groups* bounded
by a per-envelope token budget. It is a pure, deterministic, total function over
the ordered task list and the budget parameter — no LLM judgement, no I/O, no
globals, no side effects — so it can be unit-tested in isolation.

Each task carries a ``predicted_cost_tokens`` magnitude stamped at phase-4-plan
by the cost-sizing deriver (``_tasks_cost.derive_cost_size`` / the
``derive-cost-size`` subcommand). The size→token mapping and the four signals
that produce ``predicted_cost_tokens`` are owned by the central rubric in
``marketplace/bundles/plan-marshall/skills/phase-4-plan/standards/cost-sizing.md``
— this packer never re-derives a task's cost; it only sums the pre-stamped
``predicted_cost_tokens`` values, so the token table is NOT inlined here.

Packing strategy — *Next-Fit in task order*
--------------------------------------------
The phase-5-execute task loop runs tasks sequentially, honouring ``depends_on``
ordering, and an envelope is a contiguous run of tasks the orchestrator drives
inside one ``execution-context`` dispatch. The packer therefore walks the task
list in the order given and accumulates each task's ``predicted_cost_tokens``
into the current open envelope; when adding the next task would push the running
sum past the budget, the current envelope is closed and a fresh one is opened
for that task. This keeps every envelope a contiguous, order-preserving slice of
the task list (so any dependency ordering already present in the input is
preserved), and is fully deterministic.

A single task whose ``predicted_cost_tokens`` exceeds the budget on its own is
placed alone in its envelope — it cannot fit anywhere, so it never blocks a
later task from opening a fresh envelope. This realises the rubric's "an XL task
legitimately packs ~1 per envelope" note.

The packer assigns each task a 1-based ``envelope_id``; the result is a list of
``(task, envelope_id)`` pairs in the input order plus the per-envelope summary
the ``pack-envelopes`` subcommand surfaces. Callers (phase-4-plan) write the
returned ``envelope_id`` back onto each task record; phase-5-execute reads it to
run only its assigned envelope group.
"""

from __future__ import annotations

from typing import Any


def _task_cost(task: dict[str, Any]) -> int:
    """Return a task's stamped ``predicted_cost_tokens`` as a non-negative int.

    Args:
        task: A task record dict carrying a ``predicted_cost_tokens`` field.

    Raises:
        ValueError: when ``predicted_cost_tokens`` is missing, not an integer
            magnitude, or negative.
    """
    if 'predicted_cost_tokens' not in task:
        raise ValueError('task is missing required field: predicted_cost_tokens')
    raw = task['predicted_cost_tokens']
    try:
        cost = int(raw)
    except (TypeError, ValueError):
        raise ValueError(f'predicted_cost_tokens must be an integer, got {raw!r}') from None
    if cost < 0:
        raise ValueError(f'predicted_cost_tokens must be non-negative, got {cost!r}')
    return cost


def pack_envelopes(
    tasks: list[dict[str, Any]],
    per_envelope_budget_tokens: int,
) -> tuple[list[tuple[dict[str, Any], int]], list[dict[str, Any]]]:
    """Pack ordered, sized tasks into budget-bounded envelope groups.

    Deterministic and total: the same ``tasks`` list and budget always yield the
    same grouping. Uses Next-Fit in task order (see the module docstring) so each
    envelope is a contiguous, order-preserving slice of the input.

    Args:
        tasks: The ordered task records to pack. Each MUST carry a non-negative
            integer ``predicted_cost_tokens`` (stamped by the cost-sizing
            deriver). The list is consumed in the order given; the packer does
            NOT reorder it.
        per_envelope_budget_tokens: The token ceiling for one envelope. A task
            whose cost alone exceeds this budget is placed alone in its envelope.

    Returns:
        A ``(assignments, envelopes)`` tuple:

        * ``assignments`` — a list of ``(task, envelope_id)`` pairs in the input
          order, where ``envelope_id`` is the 1-based group the task belongs to.
        * ``envelopes`` — a per-envelope summary list, one dict per envelope in
          ascending ``envelope_id`` order, each
          ``{envelope_id, task_count, total_cost_tokens}``.

        An empty ``tasks`` list returns ``([], [])``.

    Raises:
        ValueError: when ``per_envelope_budget_tokens`` is not positive, or when
            any task is missing / carries a malformed ``predicted_cost_tokens``.
    """
    if per_envelope_budget_tokens <= 0:
        raise ValueError(
            f'per_envelope_budget_tokens must be positive, got {per_envelope_budget_tokens!r}'
        )

    assignments: list[tuple[dict[str, Any], int]] = []
    envelopes: list[dict[str, Any]] = []

    current_id = 0
    current_total = 0
    current_count = 0

    for task in tasks:
        cost = _task_cost(task)

        # Open the first envelope, or roll to a new one when this task would push
        # the current (non-empty) envelope past its budget. A task that already
        # sits alone in a fresh envelope is never rolled again, so an
        # over-budget task lands alone instead of forcing an empty envelope.
        if current_id == 0 or (current_count > 0 and current_total + cost > per_envelope_budget_tokens):
            if current_id > 0:
                envelopes.append(
                    {
                        'envelope_id': current_id,
                        'task_count': current_count,
                        'total_cost_tokens': current_total,
                    }
                )
            current_id += 1
            current_total = 0
            current_count = 0

        current_total += cost
        current_count += 1
        assignments.append((task, current_id))

    if current_id > 0:
        envelopes.append(
            {
                'envelope_id': current_id,
                'task_count': current_count,
                'total_cost_tokens': current_total,
            }
        )

    return assignments, envelopes

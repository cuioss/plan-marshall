#!/usr/bin/env python3
"""Envelope bin-packing command handler for manage-tasks.py.

Thin CLI wrapper over the pure packer in ``_tasks_envelope.py``. Implements the
``pack-envelopes`` subcommand: it loads the plan's tasks in number order, packs
them into budget-bounded envelope groups under ``--per-envelope-budget-tokens``,
and reports each task's assigned ``envelope_id`` alongside a per-envelope
summary.

The budget is injected via ``--per-envelope-budget-tokens`` (config-sourced from
``plan.phase-5-execute.per_envelope_budget_tokens`` by the caller, phase-4-plan),
keeping the pure packer free of config I/O. Each task must already carry a
``predicted_cost_tokens`` magnitude stamped by ``derive-cost-size``; the packer
sums those values and never re-derives a task's cost — the size→token mapping is
owned by the rubric in ``phase-4-plan/standards/cost-sizing.md``.
"""

from __future__ import annotations

from _tasks_core import get_all_tasks, get_tasks_dir, output_error
from _tasks_envelope import pack_envelopes


def cmd_pack_envelopes(args) -> dict:
    """Handle 'pack-envelopes' subcommand.

    Loads the plan's tasks (number order), packs them under the supplied budget,
    and returns ``{status, plan_id, per_envelope_budget_tokens, envelope_count,
    assignments_table, envelopes_table}``. Reports ``status: error`` (exit 0) on
    a non-positive budget or a task missing / carrying a malformed
    ``predicted_cost_tokens``.
    """
    task_dir = get_tasks_dir(args.plan_id)
    all_tasks = [task for _path, task in get_all_tasks(task_dir)]

    try:
        assignments, envelopes = pack_envelopes(
            all_tasks,
            per_envelope_budget_tokens=args.per_envelope_budget_tokens,
        )
    except ValueError as exc:
        return output_error(str(exc))

    assignments_table = [
        {
            'number': task['number'],
            'predicted_cost_tokens': int(task['predicted_cost_tokens']),
            'envelope_id': envelope_id,
        }
        for task, envelope_id in assignments
    ]

    return {
        'status': 'success',
        'plan_id': args.plan_id,
        'per_envelope_budget_tokens': args.per_envelope_budget_tokens,
        'envelope_count': len(envelopes),
        'assignments_table': assignments_table,
        'envelopes_table': envelopes,
    }

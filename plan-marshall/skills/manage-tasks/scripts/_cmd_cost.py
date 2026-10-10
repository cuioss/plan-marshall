#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Cost-sizing command handler for manage-tasks.py.

Thin CLI wrapper over the pure deriver in ``_tasks_cost.py``. Implements the
``derive-cost-size`` subcommand: given the plan-time signals of a task
(``--step-count``, ``--profile``, ``--skills-count``, ``--target-file-count``),
it returns the derived ``cost_size`` and ``predicted_cost_tokens`` per the rubric
in ``phase-4-plan/standards/cost-sizing.md``.

The size→token table may be injected via ``--size-table`` (a JSON object mapping
``S``/``M``/``L``/``XL`` → magnitude); when omitted the canonical rubric default
(``_tasks_cost.DEFAULT_SIZE_TABLE``) is used. Injecting the table keeps the
deriver a pure function and lets phase-4-plan forward the config-sourced
``cost_size_token_table`` value.
"""

from __future__ import annotations

import json

from _tasks_core import output_error
from _tasks_cost import derive_cost_size


def cmd_derive_cost_size(args) -> dict:
    """Handle 'derive-cost-size' subcommand.

    Returns ``{status, cost_size, predicted_cost_tokens}``. Reports
    ``status: error`` (exit 0) on malformed ``--size-table`` JSON or on a
    deriver validation failure (negative count, malformed table).
    """
    size_table = None
    if args.size_table is not None:
        try:
            parsed = json.loads(args.size_table)
        except (json.JSONDecodeError, ValueError) as exc:
            return output_error(f'Invalid --size-table JSON: {exc}')
        if not isinstance(parsed, dict):
            return output_error('--size-table must be a JSON object mapping size label to magnitude')
        size_table = parsed

    try:
        cost_size, predicted_cost_tokens = derive_cost_size(
            step_count=args.step_count,
            profile=args.profile,
            skills_count=args.skills_count,
            target_file_count=args.target_file_count,
            size_table=size_table,
        )
    except ValueError as exc:
        return output_error(str(exc))

    return {
        'status': 'success',
        'cost_size': cost_size,
        'predicted_cost_tokens': predicted_cost_tokens,
    }

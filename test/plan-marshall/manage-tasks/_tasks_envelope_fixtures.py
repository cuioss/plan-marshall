#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared preamble for the ``tasks envelope`` test modules.

Holds the module-level loads, constants and helpers the modules beside it
import. Below, verbatim, is the docstring of the module they were split from:

Tests for the deterministic envelope bin-packer (_tasks_envelope.py).

The pure packer in ``_tasks_envelope.py`` groups already-sized tasks into
budget-bounded execution *envelope groups* using Next-Fit in task order. It is a
pure, deterministic, total function — no LLM judgement, no I/O, no globals — so
these tests pin its behaviour by direct import:

* the private ``_task_cost`` extractor (presence / type / sign validation);
* ``pack_envelopes`` over the full envelope-packing surface: single-task
  envelopes, multi-task packing within budget, overflow into a second envelope,
  the over-budget-task-lands-alone rule, contiguity / order preservation, the
  per-envelope summary shape, and determinism (same input → same grouping);
* the empty-list and single-oversized-task edge cases the task contract calls
  out.

Tier 2 (direct import) tests cover the pure functions; Tier 3 subprocess tests
exercise the ``pack-envelopes`` CLI plumbing in ``manage-tasks`` against
on-disk task files seeded into the plan's ``tasks/`` directory.
"""


import json

from conftest import get_script_path, load_script_module

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-tasks', 'manage-tasks.py')


_envelope = load_script_module(
    'plan-marshall', 'manage-tasks', '_tasks_envelope.py', '_tasks_envelope_under_test'
)


pack_envelopes = _envelope.pack_envelopes


_task_cost = _envelope._task_cost


def _task(number, cost):
    """Build a minimal sized task record carrying ``predicted_cost_tokens``."""
    return {'number': number, 'predicted_cost_tokens': cost}


# =============================================================================
# pack-envelopes — CLI plumbing (Tier 3, on-disk task files)
# =============================================================================


def _seed_task_file(plan_dir, number, cost):
    """Write a minimal TASK-NNN.json carrying predicted_cost_tokens."""
    tasks_dir = plan_dir / 'tasks'
    tasks_dir.mkdir(parents=True, exist_ok=True)
    task = {
        'number': number,
        'title': f'task {number}',
        'predicted_cost_tokens': cost,
        'steps': [],
    }
    (tasks_dir / f'TASK-{number:03d}.json').write_text(
        json.dumps(task, indent=2), encoding='utf-8'
    )

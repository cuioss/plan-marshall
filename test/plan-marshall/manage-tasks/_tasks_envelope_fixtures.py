#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared preamble for the ``tasks envelope`` test modules.

Holds the module-level loads, constants and helpers those modules
share, so each of them carries the import and not the preamble.
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

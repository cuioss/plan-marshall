#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_manage_execution_manifest_compose_fixtures import Path, json

# =============================================================================
# execution_tier Routing Tests
# =============================================================================
#
# The composer walks plan tasks and classifies each ``verification.commands``
# entry via ``architecture resolve``. The tests below monkeypatch
# ``_resolve_command_tier`` to return a synthetic resolve TOON so the routing
# logic is exercised deterministically without depending on a live
# ``run-configuration.json`` or the persisted timeout state.


def _write_task(plans_root: Path, plan_id: str, number: int, commands: list[str]) -> Path:
    """Write a minimal TASK-*.json with the supplied verification commands.

    The shape mirrors what phase-4-plan emits: a ``verification`` dict with a
    ``commands`` list plus the structural ``steps`` array. Only the fields
    the composer's routing pass reads are populated.
    """
    task = {
        'number': number,
        'title': f'Task {number}',
        'status': 'pending',
        'verification': {'commands': list(commands), 'manual': False},
        'steps': [],
    }
    tasks_dir = plans_root / plan_id / 'tasks'
    tasks_dir.mkdir(parents=True, exist_ok=True)
    task_path = tasks_dir / f'TASK-{number:03d}.json'
    task_path.write_text(json.dumps(task, indent=2) + '\n', encoding='utf-8')
    return task_path
